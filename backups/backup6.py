#!/usr/bin/env python3
"""
Stock Sentiment Analyzer
A web scraper that analyzes public sentiment for stock symbols using news and social media data.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from textblob import TextBlob
import yfinance as yf
import time
import random
from datetime import datetime, timedelta
import re
from urllib.parse import quote
import json
from dataclasses import dataclass
from typing import List, Dict, Tuple
import warnings
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
warnings.filterwarnings('ignore')

# FinBERT and transformer imports (with fallback handling)
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Transformers not available: {e}")
    print(f"   Falling back to TextBlob sentiment analysis")
    TRANSFORMERS_AVAILABLE = False
    torch = None
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    pipeline = None

import numpy as np

# Global debug flag
debug = False

@dataclass
class SentimentData:
    """Data structure for sentiment analysis results"""
    text: str
    source: str
    timestamp: datetime
    polarity: float  # TextBlob polarity (-1 to 1)
    compound: float  # VADER compound score (-1 to 1)
    url: str = ""
# Comprehensive Financial Sentiment Lexicon
# Includes corporate euphemisms and positive-sounding terms that actually indicate problems
finance_lexicon = {
    # Direct negative terms
    "missed expectations": -0.7,
    "slowed growth": -0.5,
    "lawsuit": -0.8,
    "recall": -0.9,
    "downgrade": -0.7,
    "volatility": -0.4,
    "regulatory": -0.4,
    "uncertain": -0.4,
    "decline": -0.6,
    "losses": -0.8,
    "deficit": -0.7,
    "bankruptcy": -1.0,
    "investigation": -0.8,
    "fraud": -1.0,
    "scandal": -0.9,
    "crisis": -0.8,
    "emergency": -0.7,
    "warning": -0.6,
    "alert": -0.5,
    "concern": -0.5,
    "worry": -0.6,
    "risk": -0.5,
    "threat": -0.7,
    "challenge": -0.4,
    "problem": -0.6,
    "issue": -0.4,
    "difficulty": -0.5,
    "struggle": -0.6,
    "pressure": -0.5,
    "weakness": -0.6,
    "shortfall": -0.7,
    "disappointing": -0.6,
    "underperform": -0.7,
    "deteriorating": -0.7,
    "weakening": -0.6,
    "falling": -0.5,
    "dropping": -0.5,
    "plummeting": -0.8,
    "crashing": -0.9,
    "collapsing": -0.9,
    
    # Corporate euphemisms that sound positive but indicate problems
    "rightsizing": -0.7,  # Layoffs
    "optimization": -0.4,  # Often means cuts
    "streamlining": -0.4,  # Usually layoffs/cuts
    "restructuring": -0.6,  # Major problems
    "realignment": -0.5,  # Reorganization due to problems
    "repositioning": -0.4,  # Strategic pivot due to failure
    "strategic pivot": -0.5,  # Admission current strategy failed
    "refocusing": -0.4,  # Abandoning failing areas
    "transformation": -0.3,  # Major changes needed
    "transition": -0.3,  # Period of uncertainty
    "adjustment": -0.3,  # Things not going as planned
    "normalization": -0.4,  # Admitting things were abnormal
    "course correction": -0.5,  # Admission of being off track
    "recalibration": -0.4,  # Adjustment due to problems
    "reset": -0.5,  # Starting over due to failure
    
    # Financial euphemisms
    "working capital management": -0.4,  # Cash flow problems
    "liquidity challenges": -0.7,  # Cash problems
    "capital preservation": -0.5,  # Defensive mode
    "cost discipline": -0.4,  # Spending cuts
    "expense management": -0.4,  # Cost cutting
    "efficiency improvements": -0.3,  # Often means layoffs
    "operational leverage": -0.2,  # Trying to do more with less
    "margin compression": -0.6,  # Profitability declining
    "pricing pressure": -0.6,  # Can't raise prices
    "competitive headwinds": -0.6,  # Losing market share
    "market headwinds": -0.5,  # External challenges
    "macro headwinds": -0.4,  # Economic challenges
    "sector rotation": -0.3,  # Investors leaving sector
    
    # Growth-related euphemisms
    "managed decline": -0.8,  # Controlled shrinking
    "rightsized growth": -0.5,  # Lower growth targets
    "disciplined growth": -0.3,  # Slower expansion
    "sustainable growth": -0.2,  # Lower growth
    "measured expansion": -0.3,  # Cautious growth
    "selective investments": -0.3,  # Reduced spending
    "targeted approach": -0.2,  # More limited strategy
    "focused strategy": -0.2,  # Narrowing operations
    "core competencies": -0.2,  # Abandoning other areas
    "back to basics": -0.4,  # Abandoning innovation
    
    # Timing-related euphemisms
    "delayed implementation": -0.5,  # Behind schedule
    "phased approach": -0.3,  # Slower rollout
    "gradual transition": -0.3,  # Slow change
    "measured pace": -0.3,  # Slower than planned
    "extended timeline": -0.4,  # Taking longer
    "revised schedule": -0.4,  # Behind original plan
    "adjusted expectations": -0.5,  # Lowering guidance
    "updated outlook": -0.4,  # Usually worse outlook
    "refined guidance": -0.4,  # Often lowered
    "recalibrated forecast": -0.5,  # Adjusted down
    
    # Market/customer euphemisms
    "evolving market conditions": -0.4,  # Market getting worse
    "shifting customer preferences": -0.5,  # Losing customers
    "changing dynamics": -0.4,  # Unfavorable changes
    "market maturation": -0.4,  # Growth slowing
    "industry consolidation": -0.3,  # Competitive pressure
    "competitive landscape": -0.3,  # Increased competition
    "customer acquisition costs": -0.4,  # Getting expensive to grow
    "retention challenges": -0.6,  # Losing customers
    "engagement metrics": -0.2,  # Often declining
    "user experience optimization": -0.2,  # Fixing problems
    
    # Positive terms (for balance)
    "exceeded expectations": 0.7,
    "strong performance": 0.6,
    "robust growth": 0.7,
    "record earnings": 0.8,
    "milestone": 0.5,
    "breakthrough": 0.7,
    "innovation": 0.5,
    "expansion": 0.4,
    "acquisition": 0.3,
    "partnership": 0.4,
    "collaboration": 0.3,
    "synergies": 0.4,
    "upside": 0.5,
    "opportunity": 0.4,
    "momentum": 0.5,
    "acceleration": 0.6,
    "outperformed": 0.7,
    "beat estimates": 0.7,
    "upgraded": 0.6,
    "raised guidance": 0.8,
    "increased outlook": 0.7,
    "confident": 0.5,
    "optimistic": 0.6,
    "bullish": 0.7,
    "positive": 0.4,
    "strong": 0.5,
    "solid": 0.4,
    "healthy": 0.4,
    "resilient": 0.5,
    "impressive": 0.6,
    "outstanding": 0.7,
    "exceptional": 0.8
}

# Financial context phrases that need special handling
financial_context_phrases = {
    # Multi-word euphemisms that need context
    "one-time charge": -0.5,  # Usually recurring
    "non-recurring expense": -0.4,  # Often recurring
    "extraordinary item": -0.4,  # Unusual expense
    "special item": -0.4,  # Usually bad news
    "adjusted earnings": -0.2,  # Excluding bad stuff
    "pro forma": -0.3,  # Hypothetical better results
    "normalized results": -0.3,  # Adjusting out problems
    "core operations": -0.2,  # Excluding underperformers
    "organic growth": 0.3,  # Actually good if genuine
    "like-for-like": 0.2,  # Fair comparison
    "same-store sales": 0.1,  # Neutral metric
    "comparable metrics": 0.1,  # Fair comparison
    "underlying performance": -0.2,  # Often removes bad news
    "operational metrics": -0.1,  # May exclude financial reality
    "key performance indicators": 0.1,  # Neutral
    "non-GAAP": -0.3,  # Excluding required accounting
    "cash earnings": -0.2,  # May exclude important costs
    "EBITDA": -0.1,  # Excludes depreciation, taxes, etc
    "free cash flow": 0.3,  # Actually important metric
    "return on invested capital": 0.3,  # Good efficiency metric
}

# Update VADER lexicon with comprehensive financial terms

class StockSentimentAnalyzer:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        
        # Initialize FinBERT model for financial sentiment analysis
        self.finbert_pipeline = None
        
        if TRANSFORMERS_AVAILABLE:
            print(f"Loading FinBERT model for enhanced financial sentiment analysis...")
            try:
                # Use FinBERT model specifically trained on financial data
                model_name = "ProsusAI/finbert"
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
                
                # Create pipeline for easier inference
                self.finbert_pipeline = pipeline(
                    "text-classification", 
                    model=self.model, 
                    tokenizer=self.tokenizer,
                    device=0 if torch.cuda.is_available() else -1  # Use GPU if available
                )
                
                print(f"SUCCESS: FinBERT model loaded successfully")
                
            except Exception as e:
                print(f"WARNING: Could not load FinBERT model, trying fallback: {e}")
                # Fallback to a more basic transformer model
                try:
                    self.finbert_pipeline = pipeline(
                        "sentiment-analysis",
                        model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                        device=0 if torch.cuda.is_available() else -1
                    )
                    print(f"SUCCESS: Fallback sentiment model loaded")
                except Exception as e2:
                    print(f"ERROR: Could not load any transformer model: {e2}")
                    self.finbert_pipeline = None
        else:
            print(f"INFO: Using TextBlob for basic sentiment analysis (install transformers for FinBERT)")
        
        # Store financial context for enhanced analysis
        self.financial_context_phrases = financial_context_phrases
        self.session = requests.Session()
        # More diverse and recent user agents to avoid blocking
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Company name mapping for better search results
        self.company_name = self._get_company_name(self.symbol)
        
        print(f"Initialized analyzer for {self.symbol} ({self.company_name})")
    
    def _get_company_name(self, symbol: str) -> str:
        """Get company name from symbol using web search if needed"""
        # Common stock symbols mapping
        symbol_map = {
            'AAPL': 'Apple Inc',
            'MSFT': 'Microsoft Corporation',
            'GOOGL': 'Alphabet Google',
            'AMZN': 'Amazon',
            'TSLA': 'Tesla',
            'META': 'Meta Facebook',
            'NVDA': 'NVIDIA Corporation',
            'NFLX': 'Netflix',
            'BABA': 'Alibaba',
            'CRM': 'Salesforce',
            'ORCL': 'Oracle Corporation',
            'AMD': 'Advanced Micro Devices',
            'INTC': 'Intel Corporation',
            'IBM': 'International Business Machines',
            'UBER': 'Uber Technologies',
            'SPOT': 'Spotify',
            'SNAP': 'Snap Inc',
            'TWTR': 'Twitter',
            'SQ': 'Block Square',
            'PYPL': 'PayPal',
            'DIS': 'Disney',
            'BA': 'Boeing',
            'JPM': 'JPMorgan Chase',
            'V': 'Visa Inc',
            'MA': 'Mastercard',
            'WMT': 'Walmart',
            'PG': 'Procter Gamble',
            'JNJ': 'Johnson Johnson',
            'KO': 'Coca Cola'
        }
        
        if symbol in symbol_map:
            return symbol_map[symbol]
        
        # If not in mapping, try to find it via web search
        try:
            search_url = f"https://finance.yahoo.com/quote/{symbol}"
            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to extract company name from Yahoo Finance page
            h1_tag = soup.find('h1', class_='D(ib)')
            if h1_tag:
                full_text = h1_tag.get_text()
                # Extract company name (usually before the parentheses)
                if '(' in full_text:
                    company_name = full_text.split('(')[0].strip()
                    return company_name
            
            # Fallback: look for any element with company name
            title_tag = soup.find('title')
            if title_tag and 'Stock' in title_tag.text:
                return title_tag.text.split('(')[0].strip()
                
        except Exception as e:
            print(f"Could not fetch company name: {e}")
        
        return symbol  # Fallback to symbol if company name not found

    def get_comprehensive_sentiment(self, target_articles: int = 50) -> List[SentimentData]:
        """Gather sentiment data from multiple sources using multithreading"""
        all_sentiments = []
        
        # Define source functions with their expected yield and priority
        source_functions = [
            #(self._scrape_newsapi, "NewsAPI", 30),
            (self._scrape_google_news, "Google News", 25),
            (self._scrape_yahoo_finance, "Yahoo Finance", 25),
            (self._scrape_marketwatch, "MarketWatch", 25),
            (self._scrape_reuters, "Reuters", 25),
            (self._scrape_seeking_alpha, "Seeking Alpha", 25),
            (self._scrape_benzinga, "Benzinga", 25),
            #(self._scrape_bloomberg_search, "Bloomberg", 25),
        ]
        
        print(f"Target: {target_articles} articles")
        print(f"Running scrapers in parallel using {len(source_functions)} threads...")
        
        # Use ThreadPoolExecutor to run scrapers in parallel
        with ThreadPoolExecutor(max_workers=len(source_functions), thread_name_prefix="scraper") as executor:
            # Submit all scraper tasks
            future_to_source = {}
            for source_func, source_name, expected_yield in source_functions:
                # Calculate articles to fetch per source
                articles_per_source = max(10, target_articles // len(source_functions) + 5)
                future = executor.submit(self._run_scraper_with_retry, source_func, source_name, articles_per_source)
                future_to_source[future] = source_name
            
            # Collect results as they complete
            for future in as_completed(future_to_source):
                source_name = future_to_source[future]
                try:
                    source_sentiments = future.result(timeout=30)  # 30 second timeout per scraper
                    if source_sentiments:
                        all_sentiments.extend(source_sentiments)
                        print(f"  -> Found {len(source_sentiments)} articles from {source_name}")
                    else:
                        print(f"  -> No articles found from {source_name}")
                except Exception as e:
                    print(f"  -> Error with {source_name}: {str(e)}")
                    if debug:
                        import traceback
                        traceback.print_exc()
        
        # Remove duplicates based on text similarity
        unique_sentiments = self._remove_duplicates(all_sentiments)
        
        print(f"Total unique articles collected: {len(unique_sentiments)}")
        return unique_sentiments
    
    def _run_scraper_with_retry(self, scraper_func, source_name: str, max_articles: int) -> List[SentimentData]:
        """Run a scraper function with retry logic and thread-safe session"""
        # Create a thread-local session for this scraper
        local_session = requests.Session()
        local_session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Store original session and replace temporarily
        original_session = self.session
        self.session = local_session
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Add jitter to avoid thundering herd
                time.sleep(random.uniform(0.5, 2.0))
                
                result = scraper_func(max_articles)
                
                # Restore original session
                self.session = original_session
                return result
                
            except Exception as e:
                if attempt == max_retries - 1:
                    if debug:
                        print(f"    {source_name} failed after {max_retries} attempts: {e}")
                    # Restore original session
                    self.session = original_session
                    return []
                else:
                    if debug:
                        print(f"    {source_name} attempt {attempt + 1} failed: {e}")
                    # Exponential backoff
                    time.sleep(random.uniform(1, 3) * (2 ** attempt))
        
        # Restore original session
        self.session = original_session
        return []
    
    def _remove_duplicates(self, sentiments: List[SentimentData]) -> List[SentimentData]:
        """Remove duplicate articles based on text similarity"""
        unique_sentiments = []
        seen_texts = set()
        
        for sentiment in sentiments:
            # Create a normalized version of the text for comparison
            normalized_text = re.sub(r'[^\w\s]', '', sentiment.text.lower())[:100]
            
            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                unique_sentiments.append(sentiment)
        
        return unique_sentiments

    def _scrape_google_news(self, max_articles: int = 10) -> List[SentimentData]:
        """Scrape Google News for stock-related articles"""
        sentiments = []
        query = f"{self.symbol} {self.company_name} stock"
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
        
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')[:max_articles]
            
            for item in items:
                title = item.title.text if item.title else ""
                description = item.description.text if item.description else ""
                text = f"{title}. {description}"
                
                # Clean HTML tags from description
                text = re.sub(r'<[^>]+>', '', text)
                
                pub_date = item.pubDate.text if item.pubDate else ""
                timestamp = self._parse_date(pub_date)
                
                link = item.link.text if item.link else ""
                
                sentiment = self._analyze_text(text)
                sentiments.append(SentimentData(
                    text=text,
                    source="Google News",
                    timestamp=timestamp,
                    polarity=sentiment['polarity'],
                    compound=sentiment['compound'],
                    url=link
                ))
        
        except Exception as e:
            print(f"Error scraping Google News: {str(e)}")
            import traceback
            if debug:
                traceback.print_exc()
        
        return sentiments

    def _scrape_newsapi(self, max_articles: int = 20) -> List[SentimentData]:
        """Scrape NewsAPI for stock-related articles"""
        sentiments = []
        
        # NewsAPI configuration - you need to set your API key
        api_key = "53ade5a42d504aa7960aa3a58028cd29"  # Replace with your actual API key
        
        if not api_key or api_key == "YOUR_NEWS_API_KEY_HERE":
            print("NewsAPI: API key not configured, skipping...")
            return sentiments
            
        try:
            base_url = "https://newsapi.org/v2/everything"
            
            # Multiple query strategies for better coverage
            queries = [
                f"{self.symbol} stock",
                f"{self.company_name} earnings",
                f"{self.company_name} stock price",
                f"{self.symbol} {self.company_name}",
                f"{self.company_name} financial results"
            ]
            
            # Calculate articles per query
            articles_per_query = max(4, max_articles // len(queries))
            
            for query in queries:
                if len(sentiments) >= max_articles:
                    break
                    
                try:
                    params = {
                        'q': query,
                        'apiKey': api_key,
                        'language': 'en',
                        'sortBy': 'publishedAt',
                        'pageSize': min(articles_per_query, 20),  # NewsAPI limit is 100
                        'domains': 'reuters.com,bloomberg.com,wsj.com,marketwatch.com,cnbc.com,yahoo.com,forbes.com,benzinga.com,seekingalpha.com,x.com,ft.com,businessinsider.com,cbsnews.com',
                        'from': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')  # Last 7 days
                    }
                    
                    headers = {
                        'User-Agent': 'StockSentimentAnalyzer/1.0',
                        'Accept': 'application/json'
                    }
                    
                    response = requests.get(base_url, params=params, headers=headers, timeout=15)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    if data['status'] != 'ok':
                        print(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                        continue
                    
                    articles = data.get('articles', [])
                    
                    for article in articles[:max_articles - len(sentiments)]:
                        try:
                            title = article.get('title', '')
                            description = article.get('description', '')
                            content = article.get('content', '')
                            
                            # Combine title, description, and content
                            text_parts = [part for part in [title, description, content] if part]
                            text = '. '.join(text_parts)
                            
                            # Clean text
                            text = re.sub(r'\[.*?\]', '', text)  # Remove [+xxx chars] type suffixes
                            text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
                            text = re.sub(r'\s+', ' ', text).strip()
                            
                            if len(text) < 50:  # Skip very short articles
                                continue
                            
                            # Check relevance
                            text_lower = text.lower()
                            if not any(term.lower() in text_lower for term in [self.symbol, self.company_name.split()[0]]):
                                continue
                            
                            # Parse publish date
                            published_at = article.get('publishedAt', '')
                            try:
                                timestamp = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                                # Convert to local timezone approximation
                                timestamp = timestamp.replace(tzinfo=None)
                            except:
                                timestamp = datetime.now() - timedelta(hours=random.randint(1, 24))
                            
                            # Get source info
                            source_info = article.get('source', {})
                            source_name = source_info.get('name', 'NewsAPI')
                            url = article.get('url', '')
                            
                            # Analyze sentiment
                            sentiment = self._analyze_text(text)
                            
                            sentiments.append(SentimentData(
                                text=text,
                                source=f"NewsAPI ({source_name})",
                                timestamp=timestamp,
                                polarity=sentiment['polarity'],
                                compound=sentiment['compound'],
                                url=url
                            ))
                            
                        except Exception as e:
                            if debug:
                                print(f"    Error processing NewsAPI article: {e}")
                            continue
                    
                    # Rate limiting - NewsAPI allows 1000 requests per day for free tier
                    time.sleep(0.5)
                    
                except requests.exceptions.RequestException as e:
                    print(f"NewsAPI request error for query '{query}': {e}")
                    continue
                except Exception as e:
                    if debug:
                        print(f"NewsAPI error for query '{query}': {e}")
                    continue
            
            if debug and sentiments:
                print(f"NewsAPI: Successfully collected {len(sentiments)} articles")
            
        except Exception as e:
            print(f"NewsAPI general error: {e}")
            if debug:
                import traceback
                traceback.print_exc()
        
        return sentiments

    def _scrape_yahoo_finance(self, max_articles: int = 12) -> List[SentimentData]:
        """Enhanced Yahoo Finance scraper with multiple fallback strategies"""
        sentiments = []
        
        # Define multiple URL strategies to try
        url_strategies = [
            # Strategy 1: Standard news page
            lambda: f"https://finance.yahoo.com/quote/{self.symbol}/news",
            # Strategy 2: Alternative news format
            lambda: f"https://finance.yahoo.com/quote/{self.symbol.upper()}/news",
            # Strategy 3: Direct quote page (sometimes has news)
            lambda: f"https://finance.yahoo.com/quote/{self.symbol}",
            # Strategy 4: Search-based approach
            lambda: f"https://finance.yahoo.com/search?p={self.symbol}+{self.company_name.replace(' ', '+')}",
            # Strategy 5: Mobile version (sometimes more reliable)
            lambda: f"https://finance.yahoo.com/m/quote/{self.symbol}/news",
        ]
        
        for strategy_num, url_func in enumerate(url_strategies, 1):
            if len(sentiments) >= max_articles:
                break
                
            try:
                url = url_func()
                if debug:
                    print(f"  Trying Yahoo Finance strategy {strategy_num}: {url}")
                
                # Enhanced headers to avoid 404s
                headers = self.session.headers.copy()
                headers.update({
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                })
                
                # Try the request with retries
                response = None
                for attempt in range(3):  # 3 attempts per strategy
                    try:
                        response = self.session.get(url, headers=headers, timeout=20)
                        if response.status_code == 200:
                            break
                        elif response.status_code == 404:
                            if debug:
                                print(f"    404 error on attempt {attempt + 1}")
                            time.sleep(random.uniform(1, 3))  # Wait before retry
                        else:
                            if debug:
                                print(f"    Status {response.status_code} on attempt {attempt + 1}")
                    except Exception as e:
                        if debug:
                            print(f"    Request failed on attempt {attempt + 1}: {e}")
                        time.sleep(random.uniform(0.5, 2))
                
                if not response or response.status_code != 200:
                    continue
                    
                soup = BeautifulSoup(response.content, 'html.parser')
                articles_found = self._extract_yahoo_articles(soup, max_articles - len(sentiments))
                
                if articles_found:
                    sentiments.extend(articles_found)
                    if debug:
                        print(f"    Found {len(articles_found)} articles with strategy {strategy_num}")
                
                # Brief delay between strategies
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                if debug:
                    print(f"    Strategy {strategy_num} failed: {e}")
                continue
        
        return sentiments
    
    def _extract_yahoo_articles(self, soup, max_articles: int) -> List[SentimentData]:
        """Extract articles from Yahoo Finance page using multiple selectors"""
        articles_data = []
        
        # Multiple selector strategies
        selector_strategies = [
            # Strategy 1: Modern Yahoo Finance selectors
            {
                'name': 'modern',
                'selectors': [
                    'div[data-testid="news-stream"] h3',
                    'div[data-testid="news-stream"] article',
                    'section[data-testid="news-stream"] h3',
                ]
            },
            # Strategy 2: Legacy Yahoo Finance selectors
            {
                'name': 'legacy',
                'selectors': [
                    'div.Py\\(14px\\) h3',
                    'h3 a[data-testid="clamp-container"]',
                    'li.js-stream-content h3',
                    'div.js-content-viewer h3'
                ]
            },
            # Strategy 3: Generic news selectors
            {
                'name': 'generic',
                'selectors': [
                    'h3.Mb\\(5px\\)',
                    'h3.LineClamp\\(2\\,20px\\)',
                    'div.C\\(\\$c-fuji-grey-j\\)',
                    'article h3',
                    'div[class*="news"] h3'
                ]
            },
            # Strategy 4: Broad search for any headlines
            {
                'name': 'broad',
                'selectors': [
                    'h3',
                    'h2',
                    'h4',
                    'a[data-testid]'
                ]
            }
        ]
        
        for strategy in selector_strategies:
            if len(articles_data) >= max_articles:
                break
                
            for selector in strategy['selectors']:
                try:
                    elements = soup.select(selector)[:max_articles - len(articles_data)]
                    
                    for element in elements:
                        if len(articles_data) >= max_articles:
                            break
                            
                        article_data = self._process_yahoo_element(element)
                        if article_data:
                            articles_data.append(article_data)
                            
                    if articles_data:  # Found articles with this selector
                        break
                        
                except Exception as e:
                    if debug:
                        print(f"      Selector '{selector}' failed: {e}")
                    continue
        
        # If still no articles, try text-based search
        if not articles_data:
            articles_data = self._yahoo_text_based_search(soup, max_articles)
        
        return articles_data
    
    def _process_yahoo_element(self, element) -> SentimentData:
        """Process a single Yahoo Finance element into article data"""
        try:
            # Extract title
            title = ""
            if element.name in ['h1', 'h2', 'h3', 'h4']:
                title = element.get_text(strip=True)
            elif element.name == 'a':
                title = element.get_text(strip=True)
            else:
                title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'a'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            if not title or len(title) < 15:
                return None
            
            # Check if it's actually stock-related
            if not any(term in title.lower() for term in [self.symbol.lower(), self.company_name.lower().split()[0]]):
                return None
            
            # Try to get summary/description
            summary = ""
            parent = element.parent
            if parent:
                # Look for description in nearby elements
                summary_candidates = [
                    parent.find('p'),
                    parent.find_next('p'),
                    parent.find('div', class_=lambda x: x and 'summary' in x.lower() if x else False),
                    element.find_next('p')
                ]
                
                for candidate in summary_candidates:
                    if candidate:
                        summary_text = candidate.get_text(strip=True)
                        if summary_text and len(summary_text) > 20:
                            summary = summary_text[:200]  # Limit summary length
                            break
            
            text = f"{title}. {summary}" if summary else title
            
            # Extract URL
            url = ""
            link_elem = element if element.name == 'a' else element.find('a')
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                if href.startswith('/'):
                    url = f"https://finance.yahoo.com{href}"
                elif href.startswith('http'):
                    url = href
            
            # Analyze sentiment
            sentiment = self._analyze_text(text)
            
            return SentimentData(
                text=text,
                source="Yahoo Finance",
                timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                polarity=sentiment['polarity'],
                compound=sentiment['compound'],
                url=url
            )
            
        except Exception as e:
            if debug:
                print(f"      Failed to process element: {e}")
            return None
    
    def _yahoo_text_based_search(self, soup, max_articles: int) -> List[SentimentData]:
        """Fallback: search for any text containing stock symbol or company name"""
        articles_data = []
        
        try:
            # Find all text elements that mention the stock
            all_text_elements = soup.find_all(text=True)
            relevant_elements = []
            
            for text_elem in all_text_elements:
                text = text_elem.strip()
                if (len(text) > 30 and 
                    (self.symbol in text or 
                     self.company_name.split()[0] in text) and
                    any(keyword in text.lower() for keyword in ['stock', 'share', 'price', 'earnings', 'revenue'])):
                    
                    parent = text_elem.parent
                    if parent and parent.name in ['p', 'div', 'span', 'h1', 'h2', 'h3', 'h4']:
                        relevant_elements.append((text, parent))
            
            # Process relevant text elements
            for text, parent in relevant_elements[:max_articles]:
                try:
                    # Get a reasonable title from the text
                    title = text[:100] + "..." if len(text) > 100 else text
                    
                    # Try to find associated URL
                    url = ""
                    link = parent.find('a') or parent.parent.find('a') if parent.parent else None
                    if link and link.get('href'):
                        href = link.get('href')
                        if href.startswith('/'):
                            url = f"https://finance.yahoo.com{href}"
                        elif href.startswith('http'):
                            url = href
                    
                    sentiment = self._analyze_text(text)
                    
                    articles_data.append(SentimentData(
                        text=text,
                        source="Yahoo Finance",
                        timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                        polarity=sentiment['polarity'],
                        compound=sentiment['compound'],
                        url=url
                    ))
                    
                except Exception:
                    continue
        
        except Exception as e:
            if debug:
                print(f"    Text-based search failed: {e}")
        
        return articles_data

    def _scrape_marketwatch(self, max_articles: int = 10) -> List[SentimentData]:
        """Enhanced MarketWatch scraper with improved reliability"""
        sentiments = []
        
        # Multiple URL strategies for MarketWatch
        url_strategies = [
            # Strategy 1: Direct stock page
            f"https://www.marketwatch.com/investing/stock/{self.symbol.lower()}",
            # Strategy 2: Alternative stock page format
            f"https://www.marketwatch.com/investing/stock/{self.symbol.upper()}",
            # Strategy 3: News section for the stock
            f"https://www.marketwatch.com/investing/stock/{self.symbol.lower()}/news",
            # Strategy 4: Search by symbol
            f"https://www.marketwatch.com/search?q={quote(self.symbol)}",
            # Strategy 5: Search by company name
            f"https://www.marketwatch.com/search?q={quote(self.company_name)}",
            # Strategy 6: Markets section search
            f"https://www.marketwatch.com/markets/stocks?q={quote(self.symbol)}"
        ]
        
        for strategy_num, url in enumerate(url_strategies, 1):
            if len(sentiments) >= max_articles:
                break
                
            if debug:
                print(f"    MarketWatch strategy {strategy_num}: {url}")
            
            try:
                # Enhanced headers for MarketWatch
                headers = self.session.headers.copy()
                headers.update({
                    'User-Agent': random.choice(self.user_agents),
                    'Referer': 'https://www.marketwatch.com/',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Cache-Control': 'no-cache'
                })
                
                # Multiple attempts per strategy
                for attempt in range(2):
                    try:
                        response = self.session.get(url, headers=headers, timeout=20)
                        if response.status_code == 200:
                            break
                        elif response.status_code == 403:
                            # Try different user agent
                            headers['User-Agent'] = random.choice(self.user_agents)
                            time.sleep(random.uniform(2, 4))
                        else:
                            if debug:
                                print(f"      HTTP {response.status_code} on attempt {attempt + 1}")
                    except Exception as req_e:
                        if debug:
                            print(f"      Request failed attempt {attempt + 1}: {req_e}")
                        time.sleep(random.uniform(1, 3))
                
                if not response or response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                strategy_articles = self._extract_marketwatch_articles(soup, max_articles - len(sentiments), strategy_num)
                
                if strategy_articles:
                    sentiments.extend(strategy_articles)
                    if debug:
                        print(f"      Found {len(strategy_articles)} articles with strategy {strategy_num}")
                
                # Rate limiting between strategies
                time.sleep(random.uniform(1, 2.5))
                
            except Exception as e:
                if debug:
                    print(f"      Strategy {strategy_num} failed: {e}")
                continue
        
        if debug and not sentiments:
            print("    MarketWatch: No articles found with any strategy")
        
        return sentiments
    
    def _extract_marketwatch_articles(self, soup, max_articles: int, strategy_num: int) -> List[SentimentData]:
        """Extract articles from MarketWatch page using multiple selector strategies"""
        articles_data = []
        
        # Different selector strategies based on URL strategy
        if strategy_num <= 3:  # Stock page strategies
            selector_groups = [
                # Modern MarketWatch selectors
                ['div.article__content', 'div.list__item', 'div.element--article'],
                # Legacy selectors
                ['div.newsitem', 'article.article', 'div.story'],
                # Fallback selectors
                ['div[class*="article"]', 'div[class*="news"]', 'div[class*="story"]'],
                # Broad search
                ['article', 'div.media', 'div.content']
            ]
        else:  # Search page strategies
            selector_groups = [
                # Search result selectors
                ['div.searchresult', 'div.result', 'div.search-result'],
                # Article selectors in search
                ['article', 'div.article', 'div.story'],
                # Generic content selectors
                ['div[class*="content"]', 'div[class*="item"]'],
                # Last resort
                ['div', 'section']
            ]
        
        for selectors in selector_groups:
            if len(articles_data) >= max_articles:
                break
                
            for selector in selectors:
                try:
                    elements = soup.select(selector)[:max_articles - len(articles_data)]
                    
                    for element in elements:
                        if len(articles_data) >= max_articles:
                            break
                        
                        article_data = self._process_marketwatch_element(element)
                        if article_data:
                            articles_data.append(article_data)
                    
                    if articles_data:  # Found articles with this selector
                        break
                        
                except Exception as e:
                    if debug:
                        print(f"        Selector '{selector}' failed: {e}")
                    continue
            
            if articles_data:
                break
        
        # If still no articles, try text-based extraction
        if not articles_data:
            articles_data = self._marketwatch_text_extraction(soup, max_articles)
        
        return articles_data
    
    def _process_marketwatch_element(self, element) -> SentimentData:
        """Process a MarketWatch element into article data"""
        try:
            # Extract title with multiple strategies
            title = ""
            title_candidates = [
                element.find(['h1', 'h2', 'h3', 'h4']),
                element.find('a', string=True),
                element.find('div', class_=lambda x: x and 'title' in x.lower() if x else False),
                element.find('span', class_=lambda x: x and 'headline' in x.lower() if x else False)
            ]
            
            for candidate in title_candidates:
                if candidate:
                    title_text = candidate.get_text(strip=True)
                    if title_text and len(title_text) > 10:
                        title = title_text
                        break
            
            if not title:
                return None
            
            # Relevance check
            if not any(term.lower() in title.lower() for term in [self.symbol, self.company_name.split()[0]]):
                return None
            
            # Extract summary/snippet
            summary = ""
            summary_candidates = [
                element.find('p'),
                element.find('div', class_=lambda x: x and any(word in x.lower() for word in ['summary', 'excerpt', 'description']) if x else False),
                element.find_next('p'),
                element.parent.find('p') if element.parent else None
            ]
            
            for candidate in summary_candidates:
                if candidate:
                    summary_text = candidate.get_text(strip=True)
                    if summary_text and len(summary_text) > 15:
                        summary = summary_text[:300]  # Limit length
                        break
            
            text = f"{title}. {summary}" if summary else title
            
            # Extract URL
            url = ""
            link_elem = element if element.name == 'a' else element.find('a')
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                if href.startswith('/'):
                    url = f"https://www.marketwatch.com{href}"
                elif href.startswith('http'):
                    url = href
            
            # Analyze sentiment
            sentiment = self._analyze_text(text)
            
            return SentimentData(
                text=text,
                source="MarketWatch",
                timestamp=datetime.now() - timedelta(hours=random.randint(1, 72)),
                polarity=sentiment['polarity'],
                compound=sentiment['compound'],
                url=url
            )
            
        except Exception as e:
            if debug:
                print(f"        Failed to process MarketWatch element: {e}")
            return None
    
    def _marketwatch_text_extraction(self, soup, max_articles: int) -> List[SentimentData]:
        """Fallback text-based extraction for MarketWatch"""
        articles_data = []
        
        try:
            # Find text containing stock symbol or company name
            all_elements = soup.find_all(text=True)
            relevant_parents = set()
            
            for text_elem in all_elements:
                text = text_elem.strip()
                if (len(text) > 30 and 
                    (self.symbol.lower() in text.lower() or 
                     self.company_name.split()[0].lower() in text.lower()) and
                    any(keyword in text.lower() for keyword in ['stock', 'shares', 'price', 'trading', 'market'])):
                    
                    parent = text_elem.parent
                    if parent and parent not in relevant_parents:
                        relevant_parents.add(parent)
            
            # Process relevant parent elements
            for parent in list(relevant_parents)[:max_articles]:
                try:
                    # Get meaningful text from parent
                    parent_text = parent.get_text(strip=True)
                    if len(parent_text) < 50:
                        continue
                    
                    # Clean and truncate
                    title = parent_text[:150] + "..." if len(parent_text) > 150 else parent_text
                    title = re.sub(r'\s+', ' ', title)
                    
                    # Try to find associated URL
                    url = ""
                    link = parent.find('a') or parent.parent.find('a') if parent.parent else None
                    if link and link.get('href'):
                        href = link.get('href')
                        if href.startswith('/'):
                            url = f"https://www.marketwatch.com{href}"
                        elif href.startswith('http'):
                            url = href
                    
                    sentiment = self._analyze_text(parent_text)
                    
                    articles_data.append(SentimentData(
                        text=parent_text,
                        source="MarketWatch",
                        timestamp=datetime.now() - timedelta(hours=random.randint(1, 72)),
                        polarity=sentiment['polarity'],
                        compound=sentiment['compound'],
                        url=url
                    ))
                    
                except Exception:
                    continue
        
        except Exception as e:
            if debug:
                print(f"      Text extraction failed: {e}")
        
        return articles_data
    
    def _scrape_seeking_alpha(self, max_articles: int = 8) -> List[SentimentData]:
        """Scrape Seeking Alpha for stock analysis"""
        sentiments = []
        
        try:
            # Try multiple URLs for Seeking Alpha
            urls_to_try = [
                f"https://seekingalpha.com/symbol/{self.symbol}/news",
                f"https://seekingalpha.com/symbol/{self.symbol}",
                f"https://seekingalpha.com/search?q={quote(self.symbol)}"
            ]
            
            for search_url in urls_to_try:
                if len(sentiments) >= max_articles:
                    break
                    
                try:
                    # Add specific headers for Seeking Alpha
                    headers = self.session.headers.copy()
                    headers.update({
                        'Referer': 'https://seekingalpha.com/',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                    })
                    
                    response = self.session.get(search_url, timeout=15, headers=headers)
                    if response.status_code != 200:
                        continue
                        
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Try multiple selectors for articles
                    article_selectors = [
                        'article[data-testid="post-list-item"]',
                        'div[data-testid="post-list-item"]',
                        'article',
                        'div.mc-article',
                        'div[data-test-id="post-list-item"]'
                    ]
                    
                    articles = []
                    for selector in article_selectors:
                        found = soup.select(selector)[:max_articles - len(sentiments)]
                        if found:
                            articles = found
                            break
                    
                    # Fallback to general search
                    if not articles:
                        articles = soup.find_all('div', class_='symbol-article')[:max_articles - len(sentiments)]
                    
                    for article in articles:
                        if len(sentiments) >= max_articles:
                            break
                            
                        try:
                            title_elem = (article.find('h3') or 
                                        article.find('h4') or 
                                        article.find('a', {'data-testid': 'post-list-item-title'}) or
                                        article.find('a'))
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text(strip=True)
                            if not title or len(title) < 10:
                                continue
                            
                            # Look for summary
                            summary_elem = (article.find('p') or 
                                          article.find('div', {'data-testid': 'post-list-content'}))
                            summary = summary_elem.get_text(strip=True) if summary_elem else ""
                            
                            text = f"{title}. {summary}" if summary else title
                            
                            # Get URL
                            link_elem = article.find('a')
                            url = ""
                            if link_elem and link_elem.get('href'):
                                href = link_elem.get('href')
                                if href.startswith('/'):
                                    url = f"https://seekingalpha.com{href}"
                                elif href.startswith('http'):
                                    url = href
                            
                            sentiment = self._analyze_text(text)
                            sentiments.append(SentimentData(
                                text=text,
                                source="Seeking Alpha",
                                timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                                polarity=sentiment['polarity'],
                                compound=sentiment['compound'],
                                url=url
                            ))
                            
                        except Exception:
                            continue
                            
                except Exception:
                    continue
        
        except Exception as e:
            print(f"Error scraping Seeking Alpha: {str(e)}")
        
        return sentiments
    
    def _scrape_benzinga(self, max_articles: int = 8) -> List[SentimentData]:
        """Scrape Benzinga for stock news"""
        sentiments = []
        
        try:
            # Try multiple approaches for Benzinga
            urls_to_try = [
                f"https://www.benzinga.com/quote/{self.symbol}/news",
                f"https://www.benzinga.com/search?q={quote(self.symbol)}",
                f"https://www.benzinga.com/news/earnings?tickers={self.symbol}"
            ]
            
            for search_url in urls_to_try:
                if len(sentiments) >= max_articles:
                    break
                    
                try:
                    response = self.session.get(search_url, timeout=15)
                    if response.status_code != 200:
                        continue
                        
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Try multiple selectors for articles
                    article_selectors = [
                        'div.story-item',
                        'div.feed-item',
                        'div.post-item',
                        'article',
                        'div.news-item'
                    ]
                    
                    articles = []
                    for selector in article_selectors:
                        found = soup.select(selector)[:max_articles - len(sentiments)]
                        if found:
                            articles = found
                            break
                    
                    for article in articles:
                        if len(sentiments) >= max_articles:
                            break
                            
                        try:
                            title_elem = (article.find('h4') or 
                                        article.find('h3') or 
                                        article.find('h2') or
                                        article.find('a'))
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text(strip=True)
                            if not title or len(title) < 10:
                                continue
                            
                            # Get excerpt
                            excerpt_elem = (article.find('p', class_='excerpt') or 
                                          article.find('div', class_='excerpt') or
                                          article.find('p'))
                            excerpt = excerpt_elem.get_text(strip=True) if excerpt_elem else ""
                            
                            text = f"{title}. {excerpt}" if excerpt else title
                            
                            # Get URL
                            link_elem = article.find('a')
                            url = ""
                            if link_elem and link_elem.get('href'):
                                href = link_elem.get('href')
                                if href.startswith('/'):
                                    url = f"https://www.benzinga.com{href}"
                                elif href.startswith('http'):
                                    url = href
                            
                            sentiment = self._analyze_text(text)
                            sentiments.append(SentimentData(
                                text=text,
                                source="Benzinga",
                                timestamp=datetime.now() - timedelta(hours=random.randint(1, 72)),
                                polarity=sentiment['polarity'],
                                compound=sentiment['compound'],
                                url=url
                            ))
                            
                        except Exception:
                            continue
                            
                except Exception:
                    continue
        
        except Exception as e:
            print(f"Error scraping Benzinga: {str(e)}")
        
        return sentiments
    
    def _scrape_financial_times(self, max_articles: int = 8) -> List[SentimentData]:
        """Scrape Financial Times for stock coverage"""
        sentiments = []
        
        try:
            search_url = f"https://www.ft.com/search?q={quote(self.company_name)}"
            response = self.session.get(search_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = soup.find_all('div', class_='o-teaser__content')[:max_articles]
            
            for article in articles:
                try:
                    title_elem = article.find('div', class_='o-teaser__heading') or article.find('h3')
                    if not title_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    
                    # Get standfirst (summary)
                    summary_elem = article.find('p', class_='o-teaser__standfirst') or article.find('p')
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    
                    text = f"{title}. {summary}" if summary else title
                    
                    # Get URL
                    link_elem = article.find('a')
                    url = ""
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        url = href if href.startswith('http') else f"https://www.ft.com{href}"
                    
                    sentiment = self._analyze_text(text)
                    sentiments.append(SentimentData(
                        text=text,
                        source="Financial Times",
                        timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                        polarity=sentiment['polarity'],
                        compound=sentiment['compound'],
                        url=url
                    ))
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"Error scraping Financial Times: {str(e)}")
        
        return sentiments
    
    def _scrape_bloomberg_search(self, max_articles: int = 10) -> List[SentimentData]:
        """Scrape Bloomberg search results with multiple fallback approaches"""
        sentiments = []
        
        try:
            # Try multiple URLs and approaches for Bloomberg
            search_attempts = [
                # Company-specific Bloomberg page
                f"https://www.bloomberg.com/quote/{self.symbol}:US",
                # Alternative quote page format
                f"https://www.bloomberg.com/quote/{self.symbol}",
                # Search for company news
                f"https://www.bloomberg.com/search?query={quote(self.company_name)}&sort=time:desc",
                # Search by stock symbol
                f"https://www.bloomberg.com/search?query={quote(self.symbol)}&sort=time:desc"
            ]
            
            for search_url in search_attempts:
                if len(sentiments) >= max_articles:
                    break
                    
                try:
                    # Add specific headers for Bloomberg
                    headers = self.session.headers.copy()
                    headers.update({
                        'Referer': 'https://www.bloomberg.com/',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Cache-Control': 'no-cache'
                    })
                    
                    response = self.session.get(search_url, timeout=20, headers=headers)
                    if response.status_code != 200:
                        continue
                        
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Try multiple selectors for Bloomberg articles
                    article_selectors = [
                        # Modern Bloomberg selectors
                        'div[data-module="StoryPackage"]',
                        'div[data-module="LatestNews"]',
                        'article[data-testid="story-package-story"]',
                        # Legacy selectors
                        'div.storyItem__aHqJu',
                        'div.search-result-story',
                        'div.story-package-module__story',
                        # Fallback selectors
                        'div.story-list-story',
                        'article',
                        'div[class*="story"]'
                    ]
                    
                    articles = []
                    for selector in article_selectors:
                        if 'data-module' in selector or 'data-testid' in selector:
                            found = soup.select(selector)[:max_articles - len(sentiments)]
                        else:
                            found = soup.find_all('div', class_=selector.replace('div.', ''))[:max_articles - len(sentiments)] if 'div.' in selector else soup.select(selector)[:max_articles - len(sentiments)]
                        
                        if found:
                            articles = found
                            break
                    
                    # Also try finding articles by text pattern
                    if not articles:
                        # Look for any div containing stock symbol
                        all_divs = soup.find_all('div')
                        potential_articles = []
                        for div in all_divs:
                            text_content = div.get_text()
                            if (self.symbol in text_content or 
                                self.company_name.split()[0] in text_content) and len(text_content) > 50:
                                potential_articles.append(div)
                        articles = potential_articles[:max_articles - len(sentiments)]
                    
                    for article in articles:
                        if len(sentiments) >= max_articles:
                            break
                            
                        try:
                            # Try multiple ways to extract title
                            title_elem = (article.find('h3') or 
                                        article.find('h4') or 
                                        article.find('h2') or
                                        article.find('a', string=True) or
                                        article.find('span', string=True))
                            
                            if not title_elem:
                                # Try to get title from any text in the article
                                title_text = article.get_text(strip=True)
                                if len(title_text) > 200:
                                    title = title_text[:200] + "..."
                                elif len(title_text) > 20:
                                    title = title_text
                                else:
                                    continue
                            else:
                                title = title_elem.get_text(strip=True)
                            
                            if not title or len(title) < 10:
                                continue
                            
                            # Try to get summary/description
                            summary_elem = (article.find('p') or 
                                          article.find('div', class_='summary') or
                                          article.find('span', class_='description'))
                            summary = summary_elem.get_text(strip=True) if summary_elem else ""
                            
                            # Clean up title and summary
                            title = re.sub(r'\s+', ' ', title).strip()
                            summary = re.sub(r'\s+', ' ', summary).strip()
                            
                            text = f"{title}. {summary}" if summary else title
                            
                            # Skip if text is too short
                            if len(text.strip()) < 20:
                                continue
                            
                            # Try to get URL
                            link_elem = article.find('a')
                            url = ""
                            if link_elem and link_elem.get('href'):
                                href = link_elem.get('href')
                                if href.startswith('/'):
                                    url = f"https://www.bloomberg.com{href}"
                                elif href.startswith('http'):
                                    url = href
                            
                            sentiment = self._analyze_text(text)
                            sentiments.append(SentimentData(
                                text=text,
                                source="Bloomberg",
                                timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                                polarity=sentiment['polarity'],
                                compound=sentiment['compound'],
                                url=url
                            ))
                            
                        except Exception:
                            continue
                            
                except Exception:
                    continue
                    
                # Add delay between attempts
                time.sleep(random.uniform(1, 2))
        
        except Exception as e:
            print(f"Error scraping Bloomberg: {str(e)}")
            if debug:
                import traceback
                traceback.print_exc()
        
        return sentiments
    

    def _scrape_reuters(self, max_articles: int = 10) -> List[SentimentData]:
        """Scrape Reuters for stock news"""
        sentiments = []
        
        try:
            # Try multiple approaches for Reuters
            search_queries = [
                f"https://www.reuters.com/markets/companies/{self.symbol.upper()}",
                f"https://www.reuters.com/site-search/?query={quote(self.symbol)}",
                f"https://www.reuters.com/site-search/?query={quote(self.company_name)}"
            ]
            
            for search_url in search_queries:
                if len(sentiments) >= max_articles:
                    break
                    
                try:
                    response = self.session.get(search_url, timeout=15)
                    if response.status_code != 200:
                        continue
                        
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Try multiple selectors for articles
                    article_selectors = [
                        'div[data-testid="MediaStoryCard"]',
                        'div.search-result-indiv',
                        'div.story-content',
                        'article',
                        'div.media-story-card'
                    ]
                    
                    articles = []
                    for selector in article_selectors:
                        found = soup.select(selector)[:max_articles - len(sentiments)]
                        if found:
                            articles = found
                            break
                    
                    for article in articles:
                        if len(sentiments) >= max_articles:
                            break
                            
                        try:
                            # Try multiple ways to get title
                            title_elem = (article.find('h3') or 
                                        article.find('h4') or 
                                        article.find('h2') or 
                                        article.find('a'))
                            
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text(strip=True)
                            if not title or len(title) < 10:
                                continue
                            
                            # Try to get summary
                            summary_elem = (article.find('p') or 
                                          article.find('div', class_='summary'))
                            summary = summary_elem.get_text(strip=True) if summary_elem else ""
                            
                            text = f"{title}. {summary}" if summary else title
                            
                            # Try to get the article URL
                            link_elem = article.find('a')
                            url = ""
                            if link_elem and link_elem.get('href'):
                                href = link_elem.get('href')
                                if href.startswith('http'):
                                    url = href
                                elif href.startswith('/'):
                                    url = "https://www.reuters.com" + href
                            
                            sentiment = self._analyze_text(text)
                            sentiments.append(SentimentData(
                                text=text,
                                source="Reuters",
                                timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                                polarity=sentiment['polarity'],
                                compound=sentiment['compound'],
                                url=url
                            ))
                            
                        except Exception:
                            continue
                            
                except Exception:
                    continue
        
        except Exception as e:
            print(f"Error scraping Reuters: {str(e)}")
        
        return sentiments

    def get_reddit_sentiment(self, max_posts: int = 20) -> List[SentimentData]:
        """Get sentiment from Reddit posts (using pushshift API alternative)"""
        sentiments = []
        
        # Note: Reddit's API requires authentication. This is a simplified approach.
        # For production use, implement proper Reddit API authentication.
        
        try:
            # Search for posts mentioning the stock symbol
            subreddits = ['stocks', 'investing', 'SecurityAnalysis', 'ValueInvesting', 'StockMarket']
            
            for subreddit in subreddits[:3]:  # Limit to avoid rate limiting
                try:
                    # This would require praw (Python Reddit API Wrapper) for proper implementation
                    # For now, we'll simulate some data
                    print(f"Note: Reddit scraping requires proper API authentication")
                    break
                except:
                    continue
        
        except Exception as e:
            print(f"Error getting Reddit data: {str(e)}")
        
        return sentiments

    def _analyze_text(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using FinBERT and enhanced financial context"""
        # Clean and prepare text for analysis
        text_lower = text.lower()
        
        # TextBlob analysis (keep as baseline)
        blob = TextBlob(text)
        base_polarity = blob.sentiment.polarity
        
        # FinBERT analysis - much more sophisticated for financial text
        if self.finbert_pipeline:
            finbert_result = self._get_finbert_sentiment(text)
            base_compound = finbert_result['compound']
            pos_score = finbert_result['positive']
            neg_score = finbert_result['negative']
            neu_score = finbert_result['neutral']
        else:
            # Fallback to basic compound score from polarity
            base_compound = base_polarity
            pos_score = max(0, base_polarity)
            neg_score = abs(min(0, base_polarity))
            neu_score = 1 - pos_score - neg_score
        
        # Apply financial context adjustments
        adjusted_compound = self._apply_financial_context_adjustments(text_lower, base_compound)
        
        # Detect corporate euphemisms and adjust accordingly
        euphemism_adjustment = self._detect_euphemisms(text_lower)
        final_compound = max(-1.0, min(1.0, adjusted_compound + euphemism_adjustment))
        
        # Adjust polarity based on financial context
        context_factor = self._get_financial_context_factor(text_lower)
        adjusted_polarity = base_polarity * context_factor
        
        return {
            'polarity': adjusted_polarity,
            'compound': final_compound,
            'positive': pos_score,
            'neutral': neu_score,
            'negative': neg_score,
            'financial_adjustment': final_compound - base_compound,  # Track our adjustment
            'model_used': 'finbert' if self.finbert_pipeline else 'textblob'
        }
    
    def _get_finbert_sentiment(self, text: str) -> Dict[str, float]:
        """Get sentiment scores from FinBERT model"""
        try:
            # Truncate text if too long (BERT has token limits)
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]
            
            # Get FinBERT prediction
            result = self.finbert_pipeline(text)
            
            # FinBERT returns labels: 'positive', 'negative', 'neutral'
            # Convert to our expected format
            scores = {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}
            
            if isinstance(result, list) and len(result) > 0:
                # Handle multiple results (take first)
                result = result[0]
            
            label = result['label'].lower()
            confidence = result['score']
            
            # Map FinBERT labels to scores
            if 'positive' in label:
                scores['positive'] = confidence
                scores['neutral'] = (1 - confidence) / 2
                scores['negative'] = (1 - confidence) / 2
                compound = confidence
            elif 'negative' in label:
                scores['negative'] = confidence
                scores['neutral'] = (1 - confidence) / 2
                scores['positive'] = (1 - confidence) / 2
                compound = -confidence
            else:  # neutral
                scores['neutral'] = confidence
                scores['positive'] = (1 - confidence) / 2
                scores['negative'] = (1 - confidence) / 2
                compound = 0.0
            
            return {
                'compound': compound,
                'positive': scores['positive'],
                'negative': scores['negative'],
                'neutral': scores['neutral'],
                'confidence': confidence,
                'raw_label': result['label']
            }
            
        except Exception as e:
            if debug:
                print(f"FinBERT error: {e}")
            # Fallback to neutral sentiment
            return {
                'compound': 0.0,
                'positive': 0.33,
                'negative': 0.33,
                'neutral': 0.34,
                'confidence': 0.0,
                'raw_label': 'neutral_fallback'
            }
    
    def _apply_financial_context_adjustments(self, text_lower: str, base_compound: float) -> float:
        """Apply financial context adjustments to sentiment scores"""
        adjustment = 0.0
        
        # Detect earnings-related context
        if any(term in text_lower for term in ['earnings', 'quarterly', 'q1', 'q2', 'q3', 'q4', 'results']):
            # In earnings context, certain words are more significant
            if 'missed' in text_lower or 'below' in text_lower:
                adjustment -= 0.2
            elif 'beat' in text_lower or 'exceeded' in text_lower:
                adjustment += 0.2
        
        # Detect guidance/forecast context
        if any(term in text_lower for term in ['guidance', 'outlook', 'forecast', 'expects', 'projects']):
            if any(term in text_lower for term in ['lowered', 'reduced', 'cut', 'revised down']):
                adjustment -= 0.3
            elif any(term in text_lower for term in ['raised', 'increased', 'lifted', 'revised up']):
                adjustment += 0.3
        
        # Detect analyst-related context
        if any(term in text_lower for term in ['analyst', 'rating', 'price target']):
            if any(term in text_lower for term in ['downgrade', 'cut', 'reduced']):
                adjustment -= 0.2
            elif any(term in text_lower for term in ['upgrade', 'raised', 'increased']):
                adjustment += 0.2
        
        # Detect management commentary (often overly optimistic)
        if any(term in text_lower for term in ['ceo says', 'management', 'confident', 'optimistic']):
            # Slightly discount management optimism
            if base_compound > 0.1:
                adjustment -= 0.1
        
        return base_compound + adjustment
    
    def _detect_euphemisms(self, text_lower: str) -> float:
        """Detect corporate euphemisms and apply negative adjustments"""
        euphemism_penalty = 0.0
        
        # Common euphemism patterns
        euphemisms = {
            'strategic review': -0.3,  # Usually means selling/closing
            'explore alternatives': -0.4,  # Looking to sell
            'maximize shareholder value': -0.2,  # Often precedes bad news
            'enhance efficiency': -0.3,  # Usually layoffs
            'operational excellence': -0.2,  # Corporate speak for cuts
            'organizational effectiveness': -0.3,  # Reorganization/layoffs
            'portfolio optimization': -0.3,  # Selling underperformers
            'capital allocation': -0.1,  # May mean cuts elsewhere
            'resource reallocation': -0.3,  # Moving resources due to problems
            'market conditions': -0.2,  # Blaming external factors
            'challenging environment': -0.4,  # Admitting difficulties
            'evolving landscape': -0.2,  # Change not in their favor
            'dynamic market': -0.2,  # Volatile/difficult market
            'unprecedented times': -0.3,  # Unusual challenges
        }
        
        for euphemism, penalty in euphemisms.items():
            if euphemism in text_lower:
                euphemism_penalty += penalty
        
        # Detect layoff euphemisms
        layoff_terms = ['rightsizing', 'workforce optimization', 'organizational restructuring', 
                       'staff rebalancing', 'role elimination', 'position consolidation']
        if any(term in text_lower for term in layoff_terms):
            euphemism_penalty -= 0.4
        
        # Detect financial euphemisms
        if 'non-gaap' in text_lower or 'adjusted earnings' in text_lower:
            euphemism_penalty -= 0.2  # Likely excluding bad news
        
        return euphemism_penalty
    
    def _get_financial_context_factor(self, text_lower: str) -> float:
        """Get multiplier for financial context"""
        # In financial news, extreme sentiments are often more meaningful
        base_factor = 1.0
        
        # Earnings context amplifies sentiment
        if any(term in text_lower for term in ['earnings', 'quarterly results', 'financial results']):
            base_factor = 1.2
        
        # Analyst reports are often more measured
        if any(term in text_lower for term in ['analyst', 'research note', 'price target']):
            base_factor = 0.9
        
        # Management commentary may be inflated
        if any(term in text_lower for term in ['ceo', 'management says', 'executive']):
            base_factor = 0.8
        
        # SEC filings are more factual
        if any(term in text_lower for term in ['sec filing', '10-k', '10-q', '8-k']):
            base_factor = 1.1
        
        return base_factor

    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats"""
        try:
            # Try common date formats
            formats = [
                '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # If parsing fails, return current time minus random hours
            return datetime.now() - timedelta(hours=random.randint(1, 24))
        
        except:
            return datetime.now()

    def analyze_sentiment(self, target_articles: int = 50) -> Dict:
        """Main method to analyze sentiment for the stock"""
        print(f"Starting intelligent sentiment analysis for {self.symbol}...")
        print(f"Target: {target_articles} articles from multiple sources")
        
        # Collect sentiment data intelligently
        all_sentiments = self.get_comprehensive_sentiment(target_articles)
        
        if not all_sentiments:
            return {"error": "No sentiment data collected"}
        
        # Calculate aggregate metrics
        total_articles = len(all_sentiments)
        avg_polarity = sum(s.polarity for s in all_sentiments) / total_articles
        avg_compound = sum(s.compound for s in all_sentiments) / total_articles
        
        # Categorize sentiment
        positive_count = sum(1 for s in all_sentiments if s.compound > 0.05)
        negative_count = sum(1 for s in all_sentiments if s.compound < -0.05)
        neutral_count = total_articles - positive_count - negative_count
        
        # Determine overall sentiment with more nuanced thresholds
        if avg_compound > 0.2:
            overall_sentiment = "Very Positive"
        elif avg_compound > 0.05:
            overall_sentiment = "Positive"
        elif avg_compound > -0.05:
            overall_sentiment = "Neutral"
        elif avg_compound > -0.2:
            overall_sentiment = "Negative"
        else:
            overall_sentiment = "Very Negative"
        
        # Get stock price for context (using web scraping instead of yfinance)
        current_price, price_change = self._get_stock_price_context()
        
        # Calculate source diversity score
        source_count = len(set(s.source for s in all_sentiments))
        diversity_score = min(source_count / 8.0, 1.0)  # Max 8 sources
        
        # Create summary report
        results = {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_sources_analyzed": total_articles,
            "unique_sources_count": source_count,
            "source_diversity_score": round(diversity_score, 2),
            "overall_sentiment": overall_sentiment,
            "sentiment_scores": {
                "average_polarity": round(avg_polarity, 3),
                "average_compound": round(avg_compound, 3)
            },
            "sentiment_distribution": {
                "positive": positive_count,
                "neutral": neutral_count,
                "negative": negative_count,
                "positive_percentage": round((positive_count / total_articles) * 100, 1),
                "negative_percentage": round((negative_count / total_articles) * 100, 1)
            },
            "stock_context": {
                "current_price": current_price,
                "daily_change_percent": price_change
            },
            "sources": {
                source: len([s for s in all_sentiments if s.source == source])
                for source in set(s.source for s in all_sentiments)
            },
            "sentiment_model": "FinBERT (Financial BERT)" if (hasattr(self, 'finbert_pipeline') and self.finbert_pipeline) else "TextBlob (Basic)",
            "sample_articles": [
                {
                    "text": s.text[:300] + "..." if len(s.text) > 300 else s.text,
                    "source": s.source,
                    "sentiment_score": round(s.compound, 3),
                    "sentiment_label": self._get_sentiment_label(s.compound),
                    "timestamp": s.timestamp.isoformat(),
                    "url": s.url
                }
                for s in sorted(all_sentiments, key=lambda x: abs(x.compound), reverse=True)
            ],
            "top_sentiment_articles": [
                {
                    "text": s.text[:200] + "..." if len(s.text) > 200 else s.text,
                    "source": s.source,
                    "sentiment_score": round(s.compound, 3),
                    "sentiment_label": self._get_sentiment_label(s.compound),
                    "timestamp": s.timestamp.isoformat(),
                    "url": s.url
                }
                for s in sorted(all_sentiments, key=lambda x: abs(x.compound), reverse=True)[:10]
            ],
            "sentiment_trends": self._analyze_sentiment_trends(all_sentiments),
            "confidence_metrics": {
                "sample_size": "Good" if total_articles >= 30 else "Limited" if total_articles >= 15 else "Very Limited",
                "source_diversity": "High" if source_count >= 6 else "Medium" if source_count >= 4 else "Low",
                "data_recency": "Current" if any(s.timestamp > datetime.now() - timedelta(days=1) for s in all_sentiments) else "Recent"
            }
        }
        
        return results
    
    def _get_stock_price_context(self) -> Tuple[float, float]:
        """Get current stock price and change using web scraping"""
        try:
            # Try Yahoo Finance page scraping
            url = f"https://finance.yahoo.com/quote/{self.symbol}"
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for price elements
            price_elem = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
            if not price_elem:
                price_elem = soup.find('span', class_='Trsdu(0.3s)')
            
            change_elem = soup.find('fin-streamer', {'data-field': 'regularMarketChangePercent'})
            if not change_elem:
                change_elem = soup.find('span', class_='Trsdu(0.3s)', string=re.compile(r'[+-]\d+\.\d+%'))
            
            current_price = None
            price_change = None
            
            if price_elem:
                price_text = price_elem.get_text().replace(',', '')
                try:
                    current_price = float(price_text)
                except ValueError:
                    pass
            
            if change_elem:
                change_text = change_elem.get_text().replace('%', '').replace('+', '')
                try:
                    price_change = float(change_text)
                except ValueError:
                    pass
            
            return current_price, price_change
            
        except Exception as e:
            print(f"Could not fetch stock price: {e}")
            return None, None
    
    def _get_sentiment_label(self, compound_score: float) -> str:
        """Convert compound score to readable label"""
        if compound_score > 0.5:
            return "Very Positive"
        elif compound_score > 0.05:
            return "Positive"
        elif compound_score > -0.05:
            return "Neutral"
        elif compound_score > -0.5:
            return "Negative"
        else:
            return "Very Negative"
    
    def _analyze_sentiment_trends(self, sentiments: List[SentimentData]) -> Dict:
        """Analyze sentiment trends over time"""
        if not sentiments:
            return {}
        
        # Group by time periods
        now = datetime.now()
        recent_24h = [s for s in sentiments if s.timestamp > now - timedelta(hours=24)]
        recent_week = [s for s in sentiments if s.timestamp > now - timedelta(days=7)]
        
        def avg_sentiment(sentiment_list):
            return sum(s.compound for s in sentiment_list) / len(sentiment_list) if sentiment_list else 0
        
        return {
            "last_24h_average": round(avg_sentiment(recent_24h), 3) if recent_24h else None,
            "last_week_average": round(avg_sentiment(recent_week), 3) if recent_week else None,
            "overall_average": round(avg_sentiment(sentiments), 3),
            "articles_last_24h": len(recent_24h),
            "articles_last_week": len(recent_week)
        } 

    def save_results(self, results: Dict, filename: str = None) -> str:
        """Save results to JSON file with error handling and Data directory creation"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.symbol}_sentiment_{timestamp}.json"
        
        # Ensure Data directory exists
        import os
        data_dir = "./Data"
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir)
                print(f"Created directory: {data_dir}")
            except Exception as e:
                print(f"Warning: Could not create Data directory: {e}")
                data_dir = "."  # Fall back to current directory
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Ensure results can be serialized
                test_json = json.dumps(results, indent=2, ensure_ascii=False)
                
                filepath = os.path.join(data_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(test_json)
                
                print(f"Results successfully saved to {filepath}")
                print(f"File contains {len(results.get('sample_articles', []))} articles from {results.get('unique_sources_count', 0)} sources")
                return filename
                
            except (IOError, OSError, PermissionError) as e:
                print(f"Attempt {attempt + 1} failed to save file: {str(e)}")
                if attempt < max_retries - 1:
                    # Try alternative filename
                    base_name = filename.rsplit('.', 1)[0]
                    filename = f"{base_name}_alt{attempt + 1}.json"
                    time.sleep(0.5)
                else:
                    print(f"Failed to save results after {max_retries} attempts")
                    return None
            except Exception as e:
                print(f"Unexpected error saving results: {str(e)}")
                return None
        
        return None

#def main():
#    """Main function to run the sentiment analyzer"""
#    import argparse
#    
#    parser = argparse.ArgumentParser(description="Analyze stock sentiment from news and social media")
#    parser.add_argument("symbol", help="Stock symbol (e.g., AAPL, TSLA, NVDA)")
#    parser.add_argument("--articles", type=int, default=50, help="Maximum number of articles to analyze (default: 50)")
#    parser.add_argument("--no-save", action="store_true", help="Don't save results to JSON file (saves by default)")
#    parser.add_argument("--output", help="Output filename (optional)")
#    parser.add_argument("--debug", action="store_true", help="Enable debug output for troubleshooting")
#    
#    args = parser.parse_args()
#    
#    # Set global debug flag
#    global debug
#    debug = args.debug
#
#    # Create analyzer and run analysis
#    analyzer = StockSentimentAnalyzer(args.symbol)
#    results = analyzer.analyze_sentiment(target_articles=args.articles)
#    
#    if "error" in results:
#        print(f"Error: {results['error']}")
#        return
#    
#    # Print results
#    print("\n" + "="*60)
#    print(f"SENTIMENT ANALYSIS RESULTS FOR {results['symbol']}")
#    print("="*60)
#    print(f"Company: {results['company_name']}")
#    print(f"Analysis Time: {results['analysis_timestamp']}")
#    print(f"Sentiment Model: {results.get('sentiment_model', 'Unknown')}")
#    print(f"Sources Analyzed: {results['total_sources_analyzed']}")
#    print(f"Overall Sentiment: {results['overall_sentiment']}")
#    print(f"Average Sentiment Score: {results['sentiment_scores']['average_compound']}")
#    
#    # Stock context
#    if results['stock_context']['current_price']:
#        print(f"Current Price: ${results['stock_context']['current_price']}")
#        if results['stock_context']['daily_change_percent'] is not None:
#            print(f"Daily Change: {results['stock_context']['daily_change_percent']:+.2f}%")
#        else:
#            print(f"Daily Change: N/A")
#    
#    # Sentiment distribution
#    dist = results['sentiment_distribution']
#    print(f"\nSentiment Distribution:")
#    print(f"  Positive: {dist['positive']} ({dist['positive_percentage']}%)")
#    print(f"  Neutral: {dist['neutral']} ({100 - dist['positive_percentage'] - dist['negative_percentage']:.1f}%)")
#    print(f"  Negative: {dist['negative']} ({dist['negative_percentage']}%)")
#    
#    # Sample articles
#    print(f"\nTop Sentiment-Driving Articles:")
#    for i, article in enumerate(results['top_sentiment_articles'], 1):
#        sentiment_label = "Positive" if article['sentiment_score'] > 0.05 else "Negative" if article['sentiment_score'] < -0.05 else "Neutral"
#        print(f"\n{i}. [{article['source']}] Score: {article['sentiment_score']} ({sentiment_label})")
#        print(f"   {article['text']}")
#        if article['url']:
#            print(f"   URL: {article['url']}")
#    
#    print(f"\n[INFO] All {len(results['sample_articles'])} articles saved to JSON file.")
#    
#    # Save results by default (unless --no-save is specified)
#    if not args.no_save:
#        saved_file = analyzer.save_results(results, args.output)
#        if saved_file:
#            print(f"\n[SUCCESS] Complete analysis saved to: {saved_file}")
#        else:
#            print(f"\n[WARNING] Failed to save results to file")
#    else:
#        print(f"\n[INFO] Results not saved (--no-save flag used)")
#
#if __name__ == "__main__":
#    main()