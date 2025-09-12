#!/usr/bin/env python3
"""
Unified Google Gemini API Client (flash-2.5, official client)
Provides a centralized interface for all Gemini API interactions across the application
"""

import os
import sys
import time
from typing import Optional, Dict, Any

import google.genai as genai
from google.genai.types import GenerateContentConfig


class GeminiClient:
    """Centralized Google Gemini API client using the official google-genai library"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash-lite"):
        """Initialize the Gemini client with API key and model"""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            self._show_api_key_help()
            raise Exception("Google Gemini API key required. Please set GEMINI_API_KEY.")
        
        # Initialize official Gemini client
        self.client = genai.Client(api_key=self.api_key)
        self.model = model
        self.request_count = 0
        self.last_request_time = 0

    def _show_api_key_help(self):
        """Show API key configuration help"""
        print("\n" + "="*60)
        print("GOOGLE GEMINI API KEY REQUIRED")
        print("="*60)
        print("To use Gemini AI features, set your key as an environment variable:")
        print()
        print("  export GEMINI_API_KEY='your_api_key_here'   (Linux/macOS)")
        print("  setx GEMINI_API_KEY \"your_api_key_here\"     (Windows PowerShell)")
        print()
        print("Get your API key at: https://aistudio.google.com/app/apikey")
        print("="*60 + "\n")

    def _make_request(self, prompt: str, temperature: float = 0.1, max_tokens: int = 200) -> Optional[str]:
        """Make a request to Gemini API with rate limiting"""

        # Simple rate limiting (max ~1 request per second)
        current_time = time.time()
        if current_time - self.last_request_time < 1.0:
            time.sleep(1.0 - (current_time - self.last_request_time))

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )

            self.last_request_time = time.time()
            self.request_count += 1

            return response.text.strip() if response.text else None

        except Exception as e:
            print(f"[WARNING] Gemini API request error: {e}")
            return None

    # --- Your original higher-level helpers, now backed by the official client ---

    def resolve_company_info(self, symbol: str) -> Dict[str, Optional[str]]:
        """Resolve comprehensive company information for a stock symbol"""
        symbol = symbol.upper().strip()

        prompt = f"""For the stock symbol "{symbol}", provide the following information in exactly this format:

COMPANY_NAME: [Full official company name]
COMMON_NAME: [Short/common name people use in conversation]
INDUSTRY: [Primary industry classification]

Examples:
NVDA -> NVIDIA Corporation / NVIDIA / Semiconductors
AAPL -> Apple Inc. / Apple / Consumer Electronics
TSLA -> Tesla, Inc. / Tesla / Electric Vehicles
JPM -> JPMorgan Chase & Co. / JPMorgan / Banking

Now provide the information for {symbol}:"""

        response_text = self._make_request(prompt, temperature=0.1, max_tokens=150)

        result = {"company_name": None, "common_name": None, "industry": None}

        if response_text:
            try:
                for line in response_text.splitlines():
                    if line.startswith("COMPANY_NAME:"):
                        result["company_name"] = line.split(":", 1)[1].strip()
                    elif line.startswith("COMMON_NAME:"):
                        result["common_name"] = line.split(":", 1)[1].strip()
                    elif line.startswith("INDUSTRY:"):
                        result["industry"] = line.split(":", 1)[1].strip()
            except Exception as e:
                print(f"[WARNING] Failed to parse Gemini response for {symbol}: {e}")

        return result

    def classify_industry_sentiment(self, text: str, industry: str) -> Dict[str, Any]:
        """Classify text sentiment with industry-specific context"""
        prompt = f"""Analyze the sentiment of the following text with context for the {industry} industry:

Text: "{text}"

Respond in this format:
SENTIMENT: [Positive/Negative/Neutral]
CONFIDENCE: [0.0-1.0]
INDUSTRY_IMPACT: [High/Medium/Low]
REASONING: [Brief explanation]"""

        response_text = self._make_request(prompt, temperature=0.2, max_tokens=200)

        result = {"sentiment": "Neutral", "confidence": 0.5, "industry_impact": "Medium", "reasoning": "Unable to analyze"}

        if response_text:
            try:
                for line in response_text.splitlines():
                    if line.startswith("SENTIMENT:"):
                        result["sentiment"] = line.split(":", 1)[1].strip()
                    elif line.startswith("CONFIDENCE:"):
                        try:
                            result["confidence"] = float(line.split(":", 1)[1].strip())
                        except ValueError:
                            pass
                    elif line.startswith("INDUSTRY_IMPACT:"):
                        result["industry_impact"] = line.split(":", 1)[1].strip()
                    elif line.startswith("REASONING:"):
                        result["reasoning"] = line.split(":", 1)[1].strip()
            except Exception as e:
                print(f"[WARNING] Failed to parse sentiment response: {e}")

        return result

    def get_industry_trends(self, industry: str, timeframe: str = "current") -> Dict[str, Any]:
        """Get current trends and outlook for a specific industry"""
        timeframe_context = {
            "current": "current market conditions and recent developments",
            "short_term": "next 3-6 months outlook and trends",
            "long_term": "next 1-3 years strategic outlook and mega-trends"
        }
        context = timeframe_context.get(timeframe, "current market conditions")

        prompt = f"""Provide a {timeframe} analysis of the {industry} industry focusing on {context}.

Format:
TREND_DIRECTION: [Positive/Negative/Stable/Mixed]
KEY_FACTORS: [3-5 main factors]
OUTLOOK: [Brief outlook]
CONFIDENCE: [High/Medium/Low]"""

        response_text = self._make_request(prompt, temperature=0.3, max_tokens=300)

        result = {"trend_direction": "Mixed", "key_factors": [], "outlook": "Unable to determine", "confidence": "Medium"}

        if response_text:
            try:
                for line in response_text.splitlines():
                    if line.startswith("TREND_DIRECTION:"):
                        result["trend_direction"] = line.split(":", 1)[1].strip()
                    elif line.startswith("KEY_FACTORS:"):
                        result["key_factors"] = [f.strip() for f in line.split(":", 1)[1].split(",")]
                    elif line.startswith("OUTLOOK:"):
                        result["outlook"] = line.split(":", 1)[1].strip()
                    elif line.startswith("CONFIDENCE:"):
                        result["confidence"] = line.split(":", 1)[1].strip()
            except Exception as e:
                print(f"[WARNING] Failed to parse trends response: {e}")

        return result

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for the current session"""
        return {
            "total_requests": self.request_count,
            "last_request_time": self.last_request_time,
            "api_key_configured": bool(self.api_key),
            "model": self.model
        }


if __name__ == "__main__":
    try:
        client = GeminiClient()

        print("Testing company info resolution:")
        for symbol in ["NVDA", "AAPL", "TSLA"]:
            info = client.resolve_company_info(symbol)
            print(f"{symbol}: {info}")
            time.sleep(1)

        print("\nTesting sentiment analysis:")
        sentiment = client.classify_industry_sentiment("Strong quarterly earnings beat expectations", "Technology")
        print(sentiment)

        print("\nTesting industry trends:")
        trends = client.get_industry_trends("Electric Vehicles", "current")
        print(trends)

        print("\nUsage stats:")
        print(client.get_usage_stats())

    except Exception as e:
        print(f"Test failed: {e}")
