#!/usr/bin/env python3
"""
Unified Google Gemini API Client
Provides a centralized interface for all Gemini API interactions across the application
"""

import os
import sys
from typing import Optional, Dict, List, Any
import requests
import json
import time
from datetime import datetime


class GeminiClient:
    """Centralized Google Gemini API client for multiple use cases"""
    
    def __init__(self, api_key: str = None):
        """Initialize the Gemini client with API key"""
        self.api_key = api_key or self._get_api_key()
        if not self.api_key:
            self._show_api_key_help()
            raise Exception("Google Gemini API key required. Please check the configuration instructions above.")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        self.request_count = 0
        self.last_request_time = 0
        
    def _get_api_key(self) -> Optional[str]:
        """Get API key from various sources"""
        # Try environment variable first
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            return api_key
            
        # Try to load from config file
        try:
            current_dir = os.path.dirname(os.path.dirname(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            import api_config
            if hasattr(api_config, 'GEMINI_API_KEY'):
                return api_config.GEMINI_API_KEY
        except ImportError:
            pass
        except Exception as e:
            print(f"[WARNING] Error loading api_config.py: {e}")
        
        return None
    
    def _show_api_key_help(self):
        """Show API key configuration help"""
        print("\n" + "="*60)
        print("GOOGLE GEMINI API KEY REQUIRED")
        print("="*60)
        print("To use Gemini AI features, you need a Google Gemini API key.")
        print("\nTo fix this, please choose one of these options:")
        print()
        print("OPTION 1: Set environment variable")
        print("  set GEMINI_API_KEY=your_gemini_api_key")
        print()
        print("OPTION 2: Create api_config.py file")
        print("  1. Create api_config.py in the project root")
        print("  2. Add: GEMINI_API_KEY = 'your_api_key_here'")
        print()
        print("Get your free API key at: https://makersuite.google.com/app/apikey")
        print("="*60 + "\n")
    
    def _make_request(self, prompt: str, temperature: float = 0.1, max_tokens: int = 100) -> Optional[str]:
        """Make a request to Gemini API with rate limiting"""
        
        # Rate limiting - max 60 requests per minute (1 per second)
        current_time = time.time()
        if current_time - self.last_request_time < 1.0:
            time.sleep(1.0 - (current_time - self.last_request_time))
        
        try:
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "topK": 1,
                    "topP": 0.8,
                    "maxOutputTokens": max_tokens
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            self.last_request_time = time.time()
            self.request_count += 1
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        return candidate['content']['parts'][0]['text'].strip()
            else:
                print(f"[WARNING] Gemini API request failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"[WARNING] Gemini API timeout")
        except requests.exceptions.RequestException as e:
            print(f"[WARNING] Gemini API request error: {e}")
        except Exception as e:
            print(f"[WARNING] Error making Gemini request: {e}")
        
        return None
    
    def resolve_company_info(self, symbol: str) -> Dict[str, Optional[str]]:
        """
        Resolve comprehensive company information for a stock symbol
        
        Args:
            symbol: Stock symbol (e.g., 'NVDA', 'AAPL')
            
        Returns:
            Dictionary with company_name, common_name, and industry
        """
        symbol = symbol.upper().strip()
        
        prompt = f"""For the stock symbol "{symbol}", provide the following information in exactly this format:

COMPANY_NAME: [Full official company name]
COMMON_NAME: [Short/common name people use in conversation]
INDUSTRY: [Primary industry classification]

Examples:
For NVDA:
COMPANY_NAME: NVIDIA Corporation
COMMON_NAME: NVIDIA
INDUSTRY: Semiconductors

For AAPL:
COMPANY_NAME: Apple Inc.
COMMON_NAME: Apple
INDUSTRY: Consumer Electronics

For TSLA:
COMPANY_NAME: Tesla, Inc.
COMMON_NAME: Tesla
INDUSTRY: Electric Vehicles

For JPM:
COMPANY_NAME: JPMorgan Chase & Co.
COMMON_NAME: JPMorgan
INDUSTRY: Banking

Now provide the information for {symbol}:"""

        response_text = self._make_request(prompt, temperature=0.1, max_tokens=150)
        
        result = {
            'company_name': None,
            'common_name': None,
            'industry': None
        }
        
        if response_text:
            try:
                lines = response_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('COMPANY_NAME:'):
                        result['company_name'] = line.split(':', 1)[1].strip()
                    elif line.startswith('COMMON_NAME:'):
                        result['common_name'] = line.split(':', 1)[1].strip()
                    elif line.startswith('INDUSTRY:'):
                        result['industry'] = line.split(':', 1)[1].strip()
                
                print(f"[GEMINI] Resolved {symbol} -> Company: {result['company_name']}, Common: {result['common_name']}, Industry: {result['industry']}")
                
            except Exception as e:
                print(f"[WARNING] Failed to parse Gemini response for {symbol}: {e}")
        
        return result
    
    def classify_industry_sentiment(self, text: str, industry: str) -> Dict[str, Any]:
        """
        Classify text sentiment with industry-specific context
        
        Args:
            text: Text to analyze
            industry: Industry context for better sentiment analysis
            
        Returns:
            Dictionary with sentiment analysis results
        """
        prompt = f"""Analyze the sentiment of the following text with specific context for the {industry} industry.

Text: "{text}"

Industry Context: {industry}

Provide sentiment analysis in this exact format:
SENTIMENT: [Positive/Negative/Neutral]
CONFIDENCE: [0.0-1.0]
INDUSTRY_IMPACT: [High/Medium/Low]
REASONING: [Brief explanation of why this sentiment applies to the {industry} industry]

Consider industry-specific factors, market conditions, and terminology relevant to {industry}."""

        response_text = self._make_request(prompt, temperature=0.2, max_tokens=200)
        
        result = {
            'sentiment': 'Neutral',
            'confidence': 0.5,
            'industry_impact': 'Medium',
            'reasoning': 'Unable to analyze'
        }
        
        if response_text:
            try:
                lines = response_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('SENTIMENT:'):
                        result['sentiment'] = line.split(':', 1)[1].strip()
                    elif line.startswith('CONFIDENCE:'):
                        confidence_str = line.split(':', 1)[1].strip()
                        try:
                            result['confidence'] = float(confidence_str)
                        except ValueError:
                            result['confidence'] = 0.5
                    elif line.startswith('INDUSTRY_IMPACT:'):
                        result['industry_impact'] = line.split(':', 1)[1].strip()
                    elif line.startswith('REASONING:'):
                        result['reasoning'] = line.split(':', 1)[1].strip()
                        
            except Exception as e:
                print(f"[WARNING] Failed to parse industry sentiment response: {e}")
        
        return result
    
    def get_industry_trends(self, industry: str, timeframe: str = "current") -> Dict[str, Any]:
        """
        Get current trends and outlook for a specific industry
        
        Args:
            industry: Industry to analyze
            timeframe: 'current', 'short_term', or 'long_term'
            
        Returns:
            Dictionary with industry trend information
        """
        timeframe_context = {
            'current': 'current market conditions and recent developments',
            'short_term': 'next 3-6 months outlook and trends',
            'long_term': 'next 1-3 years strategic outlook and mega-trends'
        }
        
        context = timeframe_context.get(timeframe, 'current market conditions')
        
        prompt = f"""Provide a {timeframe} analysis of the {industry} industry focusing on {context}.

Format your response as:
TREND_DIRECTION: [Positive/Negative/Stable/Mixed]
KEY_FACTORS: [3-5 main factors affecting the industry]
OUTLOOK: [Brief outlook summary]
CONFIDENCE: [High/Medium/Low]

Focus on factual, data-driven insights relevant to investment and business decisions."""

        response_text = self._make_request(prompt, temperature=0.3, max_tokens=300)
        
        result = {
            'trend_direction': 'Mixed',
            'key_factors': [],
            'outlook': 'Unable to determine',
            'confidence': 'Medium'
        }
        
        if response_text:
            try:
                lines = response_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('TREND_DIRECTION:'):
                        result['trend_direction'] = line.split(':', 1)[1].strip()
                    elif line.startswith('KEY_FACTORS:'):
                        factors_text = line.split(':', 1)[1].strip()
                        # Simple parsing - could be enhanced
                        result['key_factors'] = [f.strip() for f in factors_text.split(',')]
                    elif line.startswith('OUTLOOK:'):
                        result['outlook'] = line.split(':', 1)[1].strip()
                    elif line.startswith('CONFIDENCE:'):
                        result['confidence'] = line.split(':', 1)[1].strip()
                        
            except Exception as e:
                print(f"[WARNING] Failed to parse industry trends response: {e}")
        
        return result
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for the current session"""
        return {
            'total_requests': self.request_count,
            'last_request_time': self.last_request_time,
            'api_key_configured': bool(self.api_key)
        }


# Convenience functions for backward compatibility
def resolve_company_name(symbol: str) -> Optional[str]:
    """Legacy function - use resolve_company_info instead"""
    try:
        client = GeminiClient()
        info = client.resolve_company_info(symbol)
        return info.get('common_name')
    except Exception:
        return None


if __name__ == "__main__":
    """Test the Gemini client"""
    try:
        client = GeminiClient()
        
        # Test company info resolution
        test_symbols = ['NVDA', 'AAPL', 'TSLA']
        
        print("Testing company info resolution:")
        for symbol in test_symbols:
            info = client.resolve_company_info(symbol)
            print(f"{symbol}: {info}")
            time.sleep(1)  # Rate limiting
            
        # Test industry sentiment analysis
        print("\nTesting industry sentiment analysis:")
        test_text = "Strong quarterly earnings beat expectations with record revenue growth"
        test_industry = "Technology"
        
        sentiment = client.classify_industry_sentiment(test_text, test_industry)
        print(f"Sentiment analysis: {sentiment}")
        
        # Test industry trends
        print("\nTesting industry trends:")
        trends = client.get_industry_trends("Electric Vehicles", "current")
        print(f"EV trends: {trends}")
        
        # Print usage stats
        print(f"\nUsage stats: {client.get_usage_stats()}")
        
    except Exception as e:
        print(f"Test failed: {e}")