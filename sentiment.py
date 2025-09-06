#!/usr/bin/env python3
"""
Stock Sentiment Analyzer - Modular Interface
A web scraper that analyzes public sentiment for stock symbols using news and social media data.

PERFORMANCE OPTIMIZATIONS:
- Lazy loading: Scrapers and AI models only load when needed (improves database mode latency)
- Fast company names: Static mapping replaces yfinance API calls (eliminates 5s delays)
- Enhanced Selenium cleanup: Prevents hanging processes
"""
    
import warnings
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from textblob import TextBlob
# Removed yfinance import due to API issues - using static mapping instead
import re
import json
import csv
import os
import pandas as pd
import time  # Add time import for retry delays

# Import SentimentData immediately, but import scrapers lazily
from scrapers import SentimentData

# Import database functionality
try:
    from core.database import SentimentDatabase
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Database not available: {e}")
    print(f"   Falling back to file-based storage only")
    DATABASE_AVAILABLE = False
    SentimentDatabase = None

warnings.filterwarnings('ignore')

# FinBERT and transformer imports (lazy loading when needed)
TRANSFORMERS_AVAILABLE = None  # Will be checked when needed
_TRANSFORMERS_CHECKED = False
_torch = None
_AutoTokenizer = None
_AutoModelForSequenceClassification = None
_pipeline = None

def _check_transformers_availability():
    """Check if transformers are available (lazy check)"""
    global TRANSFORMERS_AVAILABLE, _TRANSFORMERS_CHECKED, _torch, _AutoTokenizer, _AutoModelForSequenceClassification, _pipeline
    
    if _TRANSFORMERS_CHECKED:
        return TRANSFORMERS_AVAILABLE
    
    _TRANSFORMERS_CHECKED = True
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
        TRANSFORMERS_AVAILABLE = True
        _torch = torch
        _AutoTokenizer = AutoTokenizer
        _AutoModelForSequenceClassification = AutoModelForSequenceClassification
        _pipeline = pipeline
    except ImportError as e:
        print(f"WARNING: Transformers not available: {e}")
        print(f"   Falling back to TextBlob sentiment analysis")
        TRANSFORMERS_AVAILABLE = False
        _torch = None
        _AutoTokenizer = None
        _AutoModelForSequenceClassification = None
        _pipeline = None
    
    return TRANSFORMERS_AVAILABLE

# Global debug flag
debug = False

# Static mapping of common stock symbols to company names
# This replaces yfinance to avoid API delays
STOCK_SYMBOL_TO_COMPANY = {
    # Major Tech Stocks
    'AAPL': 'Apple Inc.',
    'MSFT': 'Microsoft Corporation',
    'GOOGL': 'Alphabet Inc.',
    'GOOG': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.',
    'META': 'Meta Platforms Inc.',
    'TSLA': 'Tesla Inc.',
    'NVDA': 'NVIDIA Corporation',
    'NFLX': 'Netflix Inc.',
    'CRM': 'Salesforce Inc.',
    'ORCL': 'Oracle Corporation',
    'ADBE': 'Adobe Inc.',
    'INTC': 'Intel Corporation',
    'AMD': 'Advanced Micro Devices Inc.',
    'QCOM': 'QUALCOMM Incorporated',
    'AVGO': 'Broadcom Inc.',
    'TXN': 'Texas Instruments Incorporated',
    'CSCO': 'Cisco Systems Inc.',
    
    # Financial Stocks
    'JPM': 'JPMorgan Chase & Co.',
    'BAC': 'Bank of America Corporation',
    'WFC': 'Wells Fargo & Company',
    'GS': 'The Goldman Sachs Group Inc.',
    'MS': 'Morgan Stanley',
    'C': 'Citigroup Inc.',
    'V': 'Visa Inc.',
    'MA': 'Mastercard Incorporated',
    'AXP': 'American Express Company',
    'BRK.A': 'Berkshire Hathaway Inc.',
    'BRK.B': 'Berkshire Hathaway Inc.',
    
    # Healthcare & Pharma
    'JNJ': 'Johnson & Johnson',
    'PFE': 'Pfizer Inc.',
    'MRNA': 'Moderna Inc.',
    'BNTX': 'BioNTech SE',
    'UNH': 'UnitedHealth Group Incorporated',
    'CVS': 'CVS Health Corporation',
    'ABBV': 'AbbVie Inc.',
    'LLY': 'Eli Lilly and Company',
    'TMO': 'Thermo Fisher Scientific Inc.',
    'ABT': 'Abbott Laboratories',
    
    # Consumer & Retail
    'WMT': 'Walmart Inc.',
    'HD': 'The Home Depot Inc.',
    'PG': 'The Procter & Gamble Company',
    'KO': 'The Coca-Cola Company',
    'PEP': 'PepsiCo Inc.',
    'MCD': 'McDonald\'s Corporation',
    'SBUX': 'Starbucks Corporation',
    'NKE': 'NIKE Inc.',
    'DIS': 'The Walt Disney Company',
    'AMGN': 'Amgen Inc.',
    
    # Energy & Utilities
    'XOM': 'Exxon Mobil Corporation',
    'CVX': 'Chevron Corporation',
    'COP': 'ConocoPhillips',
    'NEE': 'NextEra Energy Inc.',
    
    # Industrial & Manufacturing
    'BA': 'The Boeing Company',
    'CAT': 'Caterpillar Inc.',
    'GE': 'General Electric Company',
    'MMM': '3M Company',
    'HON': 'Honeywell International Inc.',
    'UPS': 'United Parcel Service Inc.',
    'FDX': 'FedEx Corporation',
    
    # Real Estate & REITs
    'AMT': 'American Tower Corporation',
    'CCI': 'Crown Castle Inc.',
    'PLD': 'Prologis Inc.',
    
    # Telecom
    'T': 'AT&T Inc.',
    'VZ': 'Verizon Communications Inc.',
    'TMUS': 'T-Mobile US Inc.',
    
    # Other Popular Stocks
    'SPY': 'SPDR S&P 500 ETF Trust',
    'QQQ': 'Invesco QQQ Trust',
    'IWM': 'iShares Russell 2000 ETF',
    'VTI': 'Vanguard Total Stock Market ETF',
    'GME': 'GameStop Corp.',
    'AMC': 'AMC Entertainment Holdings Inc.',
    'BB': 'BlackBerry Limited',
    'NOK': 'Nokia Corporation',
    'PLTR': 'Palantir Technologies Inc.',
    'SNOW': 'Snowflake Inc.',
    'RBLX': 'Roblox Corporation',
    'COIN': 'Coinbase Global Inc.',
    'SQ': 'Block Inc.',
    'PYPL': 'PayPal Holdings Inc.',
    'ZM': 'Zoom Video Communications Inc.',
    'UBER': 'Uber Technologies Inc.',
    'LYFT': 'Lyft Inc.',
    'SNAP': 'Snap Inc.',
    'TWTR': 'Twitter Inc.',
    'PINS': 'Pinterest Inc.',
    'SPOT': 'Spotify Technology S.A.',
    'ROKU': 'Roku Inc.',
    'DOCU': 'DocuSign Inc.',
    'CRWD': 'CrowdStrike Holdings Inc.',
    'OKTA': 'Okta Inc.',
    'ZS': 'Zscaler Inc.',
    'PANW': 'Palo Alto Networks Inc.',
    'FTNT': 'Fortinet Inc.',
}

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
    "restructuring": -0.5,  # Usually means layoffs
    "streamlining": -0.4,  # Cost cutting
    "synergies": -0.3,  # Often precedes cuts
    "efficiency": -0.2,  # Can mean job cuts
    "strategic pivot": -0.4,  # Change due to failure
    "realignment": -0.3,  # Usually means cuts
    "transformation": -0.3,  # Often means trouble
    
    # Positive terms
    "beat expectations": 0.8,
    "exceeded": 0.7,
    "growth": 0.5,
    "profit": 0.6,
    "revenue": 0.4,
    "earnings": 0.4,
    "dividend": 0.5,
    "expansion": 0.6,
    "acquisition": 0.4,
    "merger": 0.3,
    "partnership": 0.4,
    "innovation": 0.5,
    "breakthrough": 0.7,
    "success": 0.6,
    "achievement": 0.5,
    "milestone": 0.5,
    "record high": 0.8,
    "strong": 0.5,
    "robust": 0.6,
    "solid": 0.4,
    "outstanding": 0.7,
    "excellent": 0.7,
    "upgrade": 0.6,
    "buy rating": 0.7,
    "outperform": 0.6,
    "bullish": 0.6,
    "positive": 0.4,
    "optimistic": 0.5,
    "confidence": 0.5,
    "momentum": 0.4,
    "rally": 0.6,
    "surge": 0.7,
    "soar": 0.8,
    "spike": 0.6,
    "jump": 0.5,
    "gain": 0.4,
    "rise": 0.4,
    "increase": 0.3,
    "improvement": 0.5,
    "recover": 0.5,
    "rebound": 0.6,
    
    # Additional financial terms for better detection
    "jumps": 0.5,  # Plural form
    "rises": 0.4,  # Plural form
    "gains": 0.4,  # Plural form
    "surges": 0.7, # Plural form
    "spikes": 0.6, # Plural form
    "soars": 0.8,  # Verb form
    "climbs": 0.4,
    "advances": 0.4,
    "up": 0.3,
    "higher": 0.3,
    "after hours": 0.2,  # Often indicates movement
    "trading": 0.1,  # Neutral but financial context
    "volume": 0.1,   # Neutral but indicates activity
    "breakout": 0.6,
    "bullish momentum": 0.7,
    "strong performance": 0.6,
    "beats estimates": 0.8,
    "exceeds expectations": 0.8
}

# Financial context phrases that indicate stock relevance
financial_context_phrases = [
    "stock price", "share price", "market cap", "trading volume", "earnings report",
    "quarterly results", "revenue growth", "profit margin", "dividend yield",
    "analyst rating", "price target", "buy recommendation", "sell recommendation",
    "financial performance", "market volatility", "investor sentiment", "stock market",
    "wall street", "nasdaq", "s&p 500", "dow jones", "financial news",
    "stock analysis", "investment", "portfolio", "hedge fund", "institutional investor"
]


class StockSentimentAnalyzer:
    """Main interface for stock sentiment analysis using modular scrapers with PostgreSQL caching"""
    
    def __init__(self, symbol: str, use_database: bool = True):
        self.symbol = symbol.upper()
        self.use_database = use_database and DATABASE_AVAILABLE
        
        # Always initialize database connection for saving articles
        self.db = None
        try:
            self.db = SentimentDatabase()
            if self.use_database:
                print(f"[SUCCESS] Database caching enabled for {self.symbol}")
            else:
                print(f"[SUCCESS] Database connection established for {self.symbol} (caching disabled, saving only)")
        except Exception as e:
            print(f"[WARNING] Database connection failed: {e}")
            print(f"[INFO] Will use file storage only")
            self.use_database = False
        
        # Initialize FinBERT model for financial sentiment analysis (lazy loading)
        self.finbert_pipeline = None
        self.tokenizer = None
        self.model = None
        self._sentiment_models_loaded = False
        
        # Lazy load sentiment analysis models only if not using database
        if not self.use_database:
            self._load_sentiment_models()
        else:
            print(f"[INFO] Database mode enabled - sentiment models will be loaded on demand to improve latency")
        
        # Store financial context for enhanced analysis
        self.financial_context_phrases = financial_context_phrases
        
        # Lazy initialize scrapers only if not using database
        self.scrapers = None
        self._scrapers_loaded = False
        
        if not self.use_database:
            self._load_scrapers()
        else:
            print(f"[INFO] Database mode enabled - scrapers will be loaded on demand to improve latency")
        
        # Cache for performance optimization
        self._sentiment_cache = {}
        self._company_name_cache = None
        
        # Get company name for better analysis (with caching)
        self.company_name = self._get_company_name_fast()
        
    def _load_sentiment_models(self):
        """Lazy load sentiment analysis models"""
        if self._sentiment_models_loaded:
            return
            
        self._sentiment_models_loaded = True
        print(f"[LAZY LOAD] Loading sentiment analysis models for {self.symbol}...")
        
        if _check_transformers_availability():
            print(f"Loading FinBERT model for enhanced financial sentiment analysis...")
            try:
                # Use FinBERT model specifically trained on financial data
                model_name = "ProsusAI/finbert"
                self.tokenizer = _AutoTokenizer.from_pretrained(model_name)
                self.model = _AutoModelForSequenceClassification.from_pretrained(model_name)
                
                # Create pipeline for easier inference
                self.finbert_pipeline = _pipeline(
                    "text-classification", 
                    model=self.model, 
                    tokenizer=self.tokenizer,
                    device=0 if _torch.cuda.is_available() else -1  # Use GPU if available
                )
                
                print(f"SUCCESS: FinBERT model loaded successfully")
                print("FINBERT VARIABLE:", self.finbert_pipeline)
            except Exception as e:
                print(f"WARNING: Could not load FinBERT model, trying fallback: {e}")
                # Fallback to a more basic transformer model
                try:
                    self.finbert_pipeline = _pipeline(
                        "sentiment-analysis",
                        model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                        device=0 if _torch.cuda.is_available() else -1
                    )
                    print(f"SUCCESS: Fallback sentiment model loaded")
                except Exception as e2:
                    print(f"ERROR: Could not load any transformer model: {e2}")
                    self.finbert_pipeline = None
        else:
            print(f"INFO: Using TextBlob for basic sentiment analysis (install transformers for FinBERT)")
    
    def _load_scrapers(self):
        """Lazy load scraper modules"""
        if self._scrapers_loaded:
            return
            
        self._scrapers_loaded = True
        print(f"[LAZY LOAD] Loading scrapers for {self.symbol}...")
        
        # Import scrapers only when needed
        from scrapers import (
            GoogleNewsScraper, NewsAPIScraper, YahooFinanceScraper,
            MarketWatchScraper, SeekingAlphaScraper, BenzingaScraper,
            FinancialTimesScraper, BloombergScraper, ReutersScraper
        )
        
        # Initialize all improved scrapers (including previously disabled ones)
        all_scrapers = {
            # High-performance scrapers (now with newspaper3k enhancement)
            'newsapi': NewsAPIScraper(self.symbol, debug),  # Re-enabled - now works great with newspaper3k
            'google_news': GoogleNewsScraper(self.symbol, debug),
            'yahoo_finance': YahooFinanceScraper(self.symbol, debug),
       # 
            # Improved scrapers with anti-bot protection
            'bloomberg': BloombergScraper(self.symbol, debug),  # Re-enabled - improved with fallbacks
            'seeking_alpha': SeekingAlphaScraper(self.symbol, debug),  # Re-enabled with enhanced Selenium support
            'marketwatch': MarketWatchScraper(self.symbol, debug),
            #'reuters': ReutersScraper(self.symbol, debug),
            
            # Additional sources
            #'benzinga': BenzingaScraper(self.symbol, debug),
            #'financial_times': FinancialTimesScraper(self.symbol, debug),
        }
        
        # Filter out disabled sources based on success rate tracking
        from scrapers.base_scraper import BaseScraper
        self.scrapers = {}
        disabled_count = 0
        
        for name, scraper in all_scrapers.items():
            if not BaseScraper.is_source_disabled(scraper.source_name):
                self.scrapers[name] = scraper
            else:
                disabled_count += 1
                if debug:
                    print(f"Skipping disabled source: {scraper.source_name}")
        
        if disabled_count > 0:
            print(f"INFO: {disabled_count} sources disabled due to low success rates")

    def _get_company_name_fast(self) -> str:
        """Get company name using static mapping (fast, no API calls)"""
        if self._company_name_cache is not None:
            return self._company_name_cache
        
        # Try direct lookup from static mapping
        company_name = STOCK_SYMBOL_TO_COMPANY.get(self.symbol.upper())
        
        if company_name:
            self._company_name_cache = company_name
            if debug:
                print(f"Found company name for {self.symbol}: {company_name}")
            return self._company_name_cache
        
        # Fallback: Try to create a reasonable company name from symbol
        # This handles cases not in our static mapping
        if len(self.symbol) <= 5:
            # For unknown symbols, create a generic name
            self._company_name_cache = f"{self.symbol} Corporation"
        else:
            # For longer symbols (like ETFs), just use the symbol
            self._company_name_cache = self.symbol
        
        if debug:
            print(f"Generated company name for {self.symbol}: {self._company_name_cache}")
        
        return self._company_name_cache
    
    @staticmethod
    def add_stock_symbol(symbol: str, company_name: str):
        """Add a new stock symbol to company name mapping"""
        STOCK_SYMBOL_TO_COMPANY[symbol.upper()] = company_name
        print(f"Added mapping: {symbol.upper()} -> {company_name}")
    
    @staticmethod  
    def get_supported_symbols():
        """Get list of all supported stock symbols with known company names"""
        return list(STOCK_SYMBOL_TO_COMPANY.keys())

    def _run_scraper_with_retry(self, scraper, max_articles: int) -> List[SentimentData]:
        """Run a scraper with retry logic, error handling, and performance optimization"""
        max_retries = 3  # Increased from 2 to 3
        base_delay = 2   # Base delay in seconds
        
        for attempt in range(max_retries):
            try:
                results = scraper.scrape(max_articles)
                
                # Enhanced post-processing with caching and batching
                if results:
                    results = self._post_process_scraper_results(results, scraper.source_name)
                
                return results
            except Exception as e:
                error_msg = str(e)
                
                # Handle different types of errors with appropriate delays
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    # Rate limited - longer delay
                    delay = base_delay * (3 ** attempt)  # Exponential backoff: 2s, 6s, 18s
                    if debug:
                        print(f"    {scraper.source_name}: Rate limited (attempt {attempt + 1}), waiting {delay}s")
                    time.sleep(delay)
                elif "503" in error_msg or "Service Unavailable" in error_msg:
                    # Service temporarily unavailable
                    delay = base_delay * (2 ** attempt)  # 2s, 4s, 8s
                    if debug:
                        print(f"    {scraper.source_name}: Service unavailable (attempt {attempt + 1}), waiting {delay}s")
                    time.sleep(delay)
                elif "timeout" in error_msg.lower():
                    # Timeout - moderate delay
                    delay = base_delay * (1.5 ** attempt)  # 2s, 3s, 4.5s
                    if debug:
                        print(f"    {scraper.source_name}: Timeout (attempt {attempt + 1}), waiting {delay}s")
                    time.sleep(delay)
                else:
                    # Other errors - small delay
                    delay = base_delay
                    if debug:
                        print(f"    {scraper.source_name}: Error (attempt {attempt + 1}): {error_msg[:100]}")
                    time.sleep(delay)
                
                if attempt == max_retries - 1:
                    # Final attempt failed - log detailed error
                    if "429" in error_msg:
                        print(f"    {scraper.source_name}: RATE LIMITED - All {max_retries} attempts failed")
                    elif "403" in error_msg or "Forbidden" in error_msg:
                        print(f"    {scraper.source_name}: BLOCKED - Anti-bot protection active")
                    elif "timeout" in error_msg.lower():
                        print(f"    {scraper.source_name}: TIMEOUT - Network too slow")
                    else:
                        print(f"    {scraper.source_name}: FAILED - {error_msg[:100]}")
                    return []
                    
        return []

    def _post_process_scraper_results(self, results: List[SentimentData], source_name: str) -> List[SentimentData]:
        """Enhanced post-processing with performance optimizations and newspaper3k integration reporting"""
        if not results:
            return results
        
        # Batch sentiment analysis for better performance
        texts_to_analyze = []
        results_needing_analysis = []
        
        enhanced_count = 0
        total_enhanced_chars = 0
        
        for result in results:
            # Check newspaper3k enhancement
            if hasattr(result, 'raw_extracted_text') and result.raw_extracted_text:
                enhanced_count += 1
                total_enhanced_chars += len(result.raw_extracted_text)
            
            # Only analyze if not already analyzed or cached
            text_hash = hash(result.text)
            if text_hash in self._sentiment_cache:
                cached_sentiment = self._sentiment_cache[text_hash]
                result.polarity = cached_sentiment['polarity']
                result.compound = cached_sentiment['compound']
            else:
                texts_to_analyze.append(result.text)
                results_needing_analysis.append((result, text_hash))
        
        # Batch analyze texts that aren't cached
        if texts_to_analyze:
            if self.finbert_pipeline and len(texts_to_analyze) > 3:
                # Use batch processing for FinBERT when we have multiple texts
                sentiments = self._batch_analyze_texts(texts_to_analyze)
            else:
                # Individual analysis for smaller batches or TextBlob
                sentiments = [self._analyze_text(text) for text in texts_to_analyze]
            
            # Apply results and cache them
            for (result, text_hash), sentiment in zip(results_needing_analysis, sentiments):
                result.polarity = sentiment['polarity']
                result.compound = sentiment['compound']
                self._sentiment_cache[text_hash] = sentiment
        
        # Report newspaper3k enhancement statistics
        if enhanced_count > 0:
            avg_enhancement_size = total_enhanced_chars // enhanced_count
            print(f"    {source_name}: newspaper3k enhanced {enhanced_count}/{len(results)} articles (avg +{avg_enhancement_size} chars)")
        
        return results
    
    def _batch_analyze_texts(self, texts: List[str]) -> List[Dict]:
        """Batch analyze texts for better FinBERT performance"""
        try:
            if not self.finbert_pipeline:
                return [self._analyze_text(text) for text in texts]
            
            # Clean texts for analysis
            cleaned_texts = [self._clean_text_for_analysis(text) for text in texts]
            
            # Separate short texts for keyword analysis and regular texts for FinBERT
            sentiments = [{'polarity': 0.0, 'compound': 0.0} for _ in texts]
            finbert_texts = []
            finbert_indices = []
            
            for i, cleaned_text in enumerate(cleaned_texts):
                if len(cleaned_text) <= 10:
                    continue  # Keep as 0.0 sentiment
                
                # Check if this text should use keyword analysis (same logic as _analyze_text)
                title_indicators = ['click \'accept all\'', 'consent framework', 'sign in to access', 'stock quote', 'marketwatch']
                has_consent_text = any(indicator in cleaned_text.lower() for indicator in title_indicators)
                
                if len(cleaned_text) < 300 or has_consent_text:
                    # Extract the likely title portion
                    title_text = cleaned_text.split('.')[0] if '.' in cleaned_text else cleaned_text
                    if has_consent_text:
                        title_text = cleaned_text[:100]
                    
                    keyword_result = self._analyze_title_with_keywords(title_text)
                    if abs(keyword_result['compound']) > 0.1:
                        if debug:
                            print(f">>> BATCH KEYWORD ANALYSIS for: {title_text[:80]}... -> {keyword_result['compound']}")
                        sentiments[i] = keyword_result
                        continue
                
                # This text will use regular FinBERT analysis
                finbert_texts.append(cleaned_text)
                finbert_indices.append(i)
            
            # Batch process remaining texts with FinBERT
            if finbert_texts:
                batch_results = self.finbert_pipeline(finbert_texts)
                
                for index, result in zip(finbert_indices, batch_results):
                    if isinstance(result, list) and len(result) > 0:
                        result = result[0]
                    
                    label = result['label'].lower()
                    score = result['score']
                    
                    # Convert FinBERT output to our format
                    if 'positive' in label:
                        sentiment_score = score * 0.8      # Raw sentiment direction
                        confidence_score = score * 1.0     # Full confidence score
                    elif 'negative' in label:
                        sentiment_score = -score * 0.8     # Raw sentiment direction
                        confidence_score = -score * 1.0    # Full confidence score  
                    else:
                        sentiment_score = 0.0
                        confidence_score = 0.0
                    
                    sentiments[index] = {'polarity': sentiment_score, 'compound': confidence_score}
            
            return sentiments
            
        except Exception as e:
            if debug:
                print(f"Batch analysis failed: {e}")
            return [self._analyze_text(text) for text in texts]

    def get_comprehensive_sentiment(self, target_articles: int = 50) -> List[SentimentData]:
        """Gather sentiment data from multiple sources using multithreading with database caching"""
        all_sentiments = []
        
        # Load scrapers and sentiment models if not using database
        if not self.use_database:
            self._load_scrapers()
            self._load_sentiment_models()
        
        # First, try to get recent articles from database if enabled
        if self.use_database and hasattr(self.db, 'get_recent_articles_from_db'):
            print(f"[DATABASE] Checking for recent articles in {self.symbol} table...")
            try:
                recent_from_db = self.db.get_recent_articles_from_db(self.symbol, target_articles, 2400)
                if recent_from_db and len(recent_from_db) >= target_articles // 2:  # If we have at least half the target
                    print(f"[DATABASE] Found {len(recent_from_db)} recent articles in database")
                    
                    # Convert database articles to SentimentData objects
                    for article in recent_from_db:
                        sentiment_obj = SentimentData(
                            text=article['text'],
                            polarity=article['polarity'],
                            compound=article['sentiment'],
                            source=article['source'],
                            url=article['url'],
                            timestamp=datetime.fromisoformat(article['timestamp'])
                        )
                        # Add extracted text if available
                        if article.get('raw_extracted_text'):
                            sentiment_obj.raw_extracted_text = article['raw_extracted_text']
                        all_sentiments.append(sentiment_obj)
                    
                    # Remove duplicates and return if we have enough
                    unique_sentiments = self._remove_duplicates(all_sentiments)
                    if len(unique_sentiments) >= target_articles // 2:
                        print(f"[DATABASE] Using {len(unique_sentiments)} cached articles from database")
                        return unique_sentiments
                    else:
                        print(f"[DATABASE] Not enough cached articles ({len(unique_sentiments)}), fetching more...")
                        all_sentiments = []  # Clear and fetch fresh
            except Exception as e:
                print(f"[WARNING] Failed to get articles from database: {e}")
        
        # Ensure scrapers are loaded before use
        if self.scrapers is None:
            self._load_scrapers()
        
        # Prepare scraper tasks
        scraper_tasks = []
        articles_per_source = max(15, target_articles // len(self.scrapers) + 10)  # Increased to get more articles per source
        
        for name, scraper in self.scrapers.items():
            scraper_tasks.append((scraper, articles_per_source))
        
        print(f"Target: {target_articles} articles")
        print(f"Running {len(scraper_tasks)} scrapers in parallel...")
        
        # Use ThreadPoolExecutor with optimized worker count for better performance
        optimal_workers = len(scraper_tasks)  # Match worker count to number of scrapers to prevent hanging
        with ThreadPoolExecutor(max_workers=optimal_workers, thread_name_prefix="scraper") as executor:
            # Submit all scraper tasks with staggered delays to avoid overwhelming servers
            future_to_scraper = {}
            for i, (scraper, max_articles) in enumerate(scraper_tasks):
                # Add small staggered delay between submissions
                if i > 0:
                    time.sleep(0.5)  # 0.5 second delay between each scraper start
                
                future = executor.submit(self._run_scraper_with_retry, scraper, max_articles)
                future_to_scraper[future] = scraper.source_name
            
            # Collect results as they complete with enhanced error handling
            scraper_stats = {}
            for future in as_completed(future_to_scraper):
                source_name = future_to_scraper[future]
                try:
                    source_sentiments = future.result(timeout=30)  # Increased timeout to 120s to handle stuck scrapers
                    if source_sentiments:
                        all_sentiments.extend(source_sentiments)
                        
                        # Calculate enhancement statistics
                        enhanced_articles = sum(1 for s in source_sentiments 
                                              if hasattr(s, 'raw_extracted_text') and s.raw_extracted_text)
                        avg_length = sum(len(s.text) for s in source_sentiments) // len(source_sentiments)
                        
                        scraper_stats[source_name] = {
                            'articles': len(source_sentiments),
                            'enhanced': enhanced_articles,
                            'avg_length': avg_length
                        }
                        
                        enhancement_info = f" ({enhanced_articles} enhanced)" if enhanced_articles > 0 else ""
                        print(f"  SUCCESS {source_name}: {len(source_sentiments)} articles (avg {avg_length} chars){enhancement_info}")
                    else:
                        print(f"  NO ARTICLES {source_name}: No articles found")
                        scraper_stats[source_name] = {'articles': 0, 'enhanced': 0, 'avg_length': 0}
                        
                except Exception as e:
                    error_msg = str(e)
                    if "403" in error_msg or "Forbidden" in error_msg:
                        print(f"  BLOCKED {source_name}: Anti-bot protection")
                    elif "timeout" in error_msg.lower():
                        print(f"  TIMEOUT {source_name}: Slow response")
                    elif "429" in error_msg or "Too Many Requests" in error_msg:
                        print(f"  RATE LIMITED {source_name}: Too many requests")
                    else:
                        print(f"  ERROR {source_name}: {error_msg[:100]}")
                    
                    scraper_stats[source_name] = {'articles': 0, 'enhanced': 0, 'avg_length': 0, 'error': error_msg}
                    
                    if debug:
                        import traceback
                        traceback.print_exc()
            
            # Print overall statistics
            total_enhanced = sum(stats.get('enhanced', 0) for stats in scraper_stats.values())
            working_scrapers = sum(1 for stats in scraper_stats.values() if stats.get('articles', 0) > 0)
            
            print(f"\nSCRAPER SUMMARY:")
            print(f"   Working scrapers: {working_scrapers}/{len(scraper_stats)}")
            print(f"   Enhanced articles: {total_enhanced}/{len(all_sentiments)} ({(total_enhanced/max(1,len(all_sentiments))*100):.1f}%)")
            if all_sentiments:
                overall_avg_length = sum(len(s.text) for s in all_sentiments) // len(all_sentiments)
                print(f"   Average article length: {overall_avg_length} characters")
            
            # Show URL resolution statistics
            from scrapers.base_scraper import BaseScraper
            url_stats = BaseScraper.get_url_resolution_stats()
            if url_stats:
                print(f"\nURL RESOLUTION STATS:")
                for source, stats in url_stats.items():
                    status = "DISABLED" if stats['disabled'] else "ACTIVE"
                    print(f"   {source}: {stats['success_rate']:.1f}% ({stats['successes']}/{stats['attempts']}) - {status}")
        
        # Remove duplicates based on text similarity
        unique_sentiments = self._remove_duplicates(all_sentiments)
        
        # Save all articles to database immediately (always, regardless of use_database setting)
        print(f"\n[DEBUG] DATABASE SAVE PROCESS - BEFORE PREPARING DATA")
        print(f"[DEBUG] unique_sentiments count: {len(unique_sentiments)}")
        print(f"[DEBUG] Symbol: {self.symbol}")
        
        if self.db and hasattr(self.db, 'save_articles_to_partitioned_table'):
            try:
                articles_data = []
                print(f"\n[DEBUG] Preparing articles for database save...")
                
                for i, sentiment in enumerate(unique_sentiments):
                    article_data = {
                        "title": sentiment.text.split('.')[0] if '.' in sentiment.text else sentiment.text[:100],
                        "text": sentiment.text,
                        "raw_extracted_text": getattr(sentiment, 'raw_extracted_text', ''),
                        "extraction_successful": hasattr(sentiment, 'raw_extracted_text') and sentiment.raw_extracted_text and len(sentiment.raw_extracted_text) > 100,
                        "source": sentiment.source,
                        "url": sentiment.url,
                        "timestamp": sentiment.timestamp.isoformat(),
                        "polarity": sentiment.polarity,
                        "sentiment": sentiment.compound,
                        "sentiment_label": self._get_sentiment_label(sentiment.compound),
                        "text_length": len(sentiment.text),
                        "extracted_length": len(getattr(sentiment, 'raw_extracted_text', '')),
                        "enhancement_ratio": round(len(getattr(sentiment, 'raw_extracted_text', '')) / max(1, len(sentiment.text)) * 100, 1) if hasattr(sentiment, 'raw_extracted_text') and sentiment.raw_extracted_text else 0.0
                    }
                    articles_data.append(article_data)
                    
                    # Debug first 3 articles being prepared
                    if i < 3:
                        print(f"[DEBUG] Article {i+1} prepared for save:")
                        print(f"[DEBUG]   Title: {article_data['title']}")
                        print(f"[DEBUG]   Source: {article_data['source']}")
                        print(f"[DEBUG]   URL: {article_data['url']}")
                        print(f"[DEBUG]   Text length: {article_data['text_length']}")
                        print(f"[DEBUG]   Sentiment: {article_data['sentiment']}")
                
                print(f"\n[DEBUG] TOTAL ARTICLES PREPARED FOR SAVE: {len(articles_data)}")
                print(f"[DEBUG] Articles data structure ready, calling save_articles_to_partitioned_table...")
                
                # Save to partitioned table
                new_articles_saved = self.db.save_articles_to_partitioned_table(self.symbol, articles_data)
                print(f"[DATABASE] SAVE COMPLETE: {new_articles_saved} new articles saved to partitioned table for {self.symbol}")
                
                # Verify what was actually saved
                print(f"\n[DEBUG] VERIFYING DATABASE SAVE...")
                try:
                    saved_articles = self.db.get_recent_articles_from_db(self.symbol, 50, 1)  # Last 1 hour
                    print(f"[DEBUG] VERIFICATION: {len(saved_articles)} articles found in {self.symbol} table")
                    
                    if len(saved_articles) != new_articles_saved:
                        print(f"[WARNING] MISMATCH: Expected {new_articles_saved} saved, but found {len(saved_articles)} in table")
                    else:
                        print(f"[SUCCESS] MATCH: Save count matches table count")
                        
                    # Show what was actually saved
                    if saved_articles:
                        print(f"[DEBUG] Sample saved articles:")
                        for i, article in enumerate(saved_articles[:3]):
                            print(f"[DEBUG]   Saved {i+1}: {article['title'][:50]}... ({article['source']})")
                            
                except Exception as ve:
                    print(f"[ERROR] Verification failed: {ve}")
                
            except Exception as e:
                print(f"[WARNING] Failed to save articles to partitioned table: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[WARNING] Database save skipped - db={self.db}, has_method={hasattr(self.db, 'save_articles_to_partitioned_table') if self.db else False}")
        
        print(f"\n[DEBUG] FINAL RETURN: Returning {len(unique_sentiments)} articles to caller")
        
        # Clean up Selenium driver after scraping to prevent hanging
        try:
            from scrapers.base_scraper import BaseScraper
            BaseScraper.cleanup_selenium_driver()
        except Exception as e:
            print(f"Warning: Selenium cleanup failed: {e}")
        
        return unique_sentiments

    def _analyze_text(self, text: str) -> Dict:
        """Analyze sentiment of text using available methods"""
        try:
            # Ensure sentiment models are loaded if needed
            if not self.use_database and not self._sentiment_models_loaded:
                self._load_sentiment_models()
                
            # Clean text
            cleaned_text = self._clean_text_for_analysis(text)
            
            # For texts that are likely titles only (with possible cookie/consent text), use keyword analysis
            title_indicators = ['click \'accept all\'', 'consent framework', 'sign in to access', 'stock quote', 'marketwatch']
            has_consent_text = any(indicator in cleaned_text.lower() for indicator in title_indicators)
            
            if debug:
                print(f">>> Analyzing text (len={len(cleaned_text)}): {cleaned_text[:120]}...")
                print(f"    Has consent text: {has_consent_text}")
            
            if len(cleaned_text) < 300 or has_consent_text:
                # Extract the likely title portion (before first sentence with consent/login text)
                title_text = cleaned_text.split('.')[0] if '.' in cleaned_text else cleaned_text
                if has_consent_text:
                    title_text = cleaned_text[:100]  # Take first 100 chars for title analysis
                
                keyword_result = self._analyze_title_with_keywords(title_text)
                # If keyword analysis found sentiment, use it; otherwise fall back to regular analysis
                if abs(keyword_result['compound']) > 0.1:
                    if debug:
                        print(f">>> USING KEYWORD ANALYSIS for title-like text: {title_text[:80]}...")
                        print(f"    Keyword sentiment: {keyword_result['compound']}")
                    return keyword_result
                elif debug:
                    print(f">>> Keyword analysis found no strong sentiment (score={keyword_result['compound']}), using regular analysis")
            
            # Use FinBERT if available, otherwise fall back to TextBlob
            if self.finbert_pipeline:
                return self._analyze_with_finbert(cleaned_text)
            else:
                return self._analyze_with_textblob(cleaned_text)
                
        except Exception as e:
            if debug:
                print(f"Sentiment analysis error: {e}")
            return {'polarity': 0.0, 'compound': 0.0}

    def _clean_text_for_analysis(self, text: str) -> str:
        """Clean text for sentiment analysis"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # For FinBERT, we can handle longer texts by chunking
        # Limit length but allow longer text for better analysis
        if len(text) > 1024 and self.finbert_pipeline:
            # For FinBERT, take first part which usually contains the most important info
            text = text[:1024]
        elif len(text) > 512 and not self.finbert_pipeline:
            # For TextBlob, keep shorter limit
            text = text[:512]
        
        return text.strip()

    def _analyze_with_finbert(self, text: str) -> Dict:
        """Analyze sentiment using FinBERT with enhanced post-processing and text chunking"""
        try:
            # For very long texts, analyze in chunks and average the results
            if len(text) > 800:
                print(f"\n>>> ANALYZING LONG TEXT WITH FINBERT (length: {len(text)} chars)")
                print(f"Text preview: {text[:200]}...")
                return self._analyze_long_text_with_finbert(text)
            else:
                print(f"\n>>> ANALYZING SHORT TEXT WITH FINBERT (length: {len(text)} chars)")
            
            results = self.finbert_pipeline(text)
            if debug:
                print("FINBERT RESULTS:", results)
                print("TEXT LENGTH:", len(text))
            # Convert FinBERT output to our format
            if isinstance(results, list) and len(results) > 0:
                result = results[0]
                label = result['label'].lower()
                score = result['score']
                
                # Map FinBERT labels to our polarity system
                if 'positive' in label:
                    base_polarity = score * 0.8
                    base_compound = score * 1.0  # Full confidence score
                elif 'negative' in label:
                    base_polarity = -score * 0.8
                    base_compound = -score * 1.0  # Full confidence score
                else:  # neutral
                    base_polarity = 0.0
                    base_compound = 0.0
                
                # Apply our enhanced financial context detection even to FinBERT results
                text_lower = text.lower()
                text_words = set(text_lower.split())
                
                # Financial context boost
                financial_boost = 0.0
                
                # Strong positive/negative indicators
                strong_positive = ['soar', 'surge', 'spike', 'rally', 'breakout', 'moon', 'explode']
                moderate_positive = ['jump', 'rise', 'gain', 'up', 'climb', 'advance', 'higher', 'beat', 'exceed']
                strong_negative = ['crash', 'plunge', 'collapse', 'tank', 'plummet', 'nosedive']
                moderate_negative = ['fall', 'drop', 'decline', 'sink', 'slide', 'slip', 'tumble']
                
                # Calculate boosts
                financial_boost += sum(0.4 for term in strong_positive 
                                     if any(term in word for word in text_words))
                financial_boost += sum(0.25 for term in moderate_positive 
                                     if any(term in word for word in text_words))
                financial_boost += sum(-0.4 for term in strong_negative 
                                     if any(term in word for word in text_words))
                financial_boost += sum(-0.25 for term in moderate_negative 
                                     if any(term in word for word in text_words))
                
                # Dollar amount context
                import re
                dollar_match = re.search(r'\$(\d+(?:\.\d+)?)', text_lower)
                if dollar_match:
                    if any(word in text_lower for word in ['jump', 'gain', 'rise', 'up', 'surge']):
                        financial_boost += 0.3
                    elif any(word in text_lower for word in ['drop', 'fall', 'down', 'loss', 'decline']):
                        financial_boost -= 0.3
                
                # If FinBERT says neutral but we have strong financial signals, override
                if 'neutral' in label and abs(financial_boost) > 0.2:
                    adjusted_polarity = financial_boost
                    adjusted_compound = financial_boost
                else:
                    adjusted_polarity = base_polarity + financial_boost * 0.5
                    adjusted_compound = base_compound + financial_boost * 0.3  # Less financial influence on compound
                
                # Clamp to [-1, 1] range
                adjusted_polarity = max(-1.0, min(1.0, adjusted_polarity))
                adjusted_compound = max(-1.0, min(1.0, adjusted_compound))
                
                return {'polarity': adjusted_polarity, 'compound': adjusted_compound}
                
        except Exception as e:
            if debug:
                print(f"FinBERT analysis error: {e}")
        
        # Fallback to TextBlob
        return self._analyze_with_textblob(text)
    
    def _analyze_long_text_with_finbert(self, text: str) -> Dict:
        """Analyze long text by breaking it into chunks and averaging results"""
        try:
            # Split into chunks of ~500 characters, trying to break at sentence boundaries
            chunks = self._split_text_into_chunks(text, max_chunk_size=1000)
            
            print(f">>> Split text into {len(chunks)} chunks for analysis")
            for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
                print(f"   Chunk {i+1}: {len(chunk)} chars - {chunk[:100]}...")
            
            if not chunks:
                return {'polarity': 0.0, 'compound': 0.0}
            
            chunk_results = []
            for chunk in chunks:
                try:
                    results = self.finbert_pipeline(chunk)
                    if isinstance(results, list) and len(results) > 0:
                        result = results[0]
                        label = result['label'].lower()
                        score = result['score']
                        
                        # Convert to polarity
                        if 'positive' in label:
                            polarity = score * 0.8
                        elif 'negative' in label:
                            polarity = -score * 0.8
                        else:  # neutral
                            polarity = 0.0
                        
                        chunk_results.append(polarity)
                except Exception as e:
                    if debug:
                        print(f"Chunk analysis failed: {e}")
                    continue
            
            if not chunk_results:
                return {'polarity': 0.0, 'compound': 0.0}
            
            # Average the results, but give more weight to stronger sentiments
            average_polarity = sum(chunk_results) / len(chunk_results)
            
            # Apply the same financial context enhancements
            text_lower = text.lower()
            text_words = set(text_lower.split())
            
            # Financial context boost
            financial_boost = 0.0
            
            # Strong positive/negative indicators
            strong_positive = ['soar', 'surge', 'spike', 'rally', 'breakout', 'moon', 'explode']
            moderate_positive = ['jump', 'rise', 'gain', 'up', 'climb', 'advance', 'higher', 'beat', 'exceed']
            strong_negative = ['crash', 'plunge', 'collapse', 'tank', 'plummet', 'nosedive']
            moderate_negative = ['fall', 'drop', 'decline', 'sink', 'slide', 'slip', 'tumble']
            
            # Calculate boosts
            financial_boost += sum(0.4 for term in strong_positive 
                                 if any(term in word for word in text_words))
            financial_boost += sum(0.25 for term in moderate_positive 
                                 if any(term in word for word in text_words))
            financial_boost += sum(-0.4 for term in strong_negative 
                                 if any(term in word for word in text_words))
            financial_boost += sum(-0.25 for term in moderate_negative 
                                 if any(term in word for word in text_words))
            
            # Dollar amount context
            dollar_match = re.search(r'\$(\d+(?:\.\d+)?)', text_lower)
            if dollar_match:
                if any(word in text_lower for word in ['jump', 'gain', 'rise', 'up', 'surge']):
                    financial_boost += 0.3
                elif any(word in text_lower for word in ['drop', 'fall', 'down', 'loss', 'decline']):
                    financial_boost -= 0.3
            
            # Combine results with different impacts
            adjusted_polarity = average_polarity + financial_boost * 0.3
            adjusted_compound = average_polarity + financial_boost * 0.2  # Less financial impact on compound
            
            # Clamp to [-1, 1] range
            adjusted_polarity = max(-1.0, min(1.0, adjusted_polarity))
            adjusted_compound = max(-1.0, min(1.0, adjusted_compound))
            
            return {'polarity': adjusted_polarity, 'compound': adjusted_compound}
            
        except Exception as e:
            if debug:
                print(f"Long text FinBERT analysis error: {e}")
            return self._analyze_with_textblob(text)
    
    def _split_text_into_chunks(self, text: str, max_chunk_size: int = 500) -> List[str]:
        """Split text into chunks, preferring sentence boundaries"""
        if len(text) <= max_chunk_size:
            return [text]
        
        # Try to split on sentences first
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # If adding this sentence would exceed the limit, start a new chunk
            if len(current_chunk) + len(sentence) + 1 > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If we still have chunks that are too long, split them by words
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= max_chunk_size:
                final_chunks.append(chunk)
            else:
                # Split long chunk by words
                words = chunk.split()
                word_chunk = ""
                for word in words:
                    if len(word_chunk) + len(word) + 1 > max_chunk_size and word_chunk:
                        final_chunks.append(word_chunk.strip())
                        word_chunk = word
                    else:
                        if word_chunk:
                            word_chunk += " " + word
                        else:
                            word_chunk = word
                if word_chunk:
                    final_chunks.append(word_chunk.strip())
        
        return final_chunks

    def _analyze_with_textblob(self, text: str) -> Dict:
        """Analyze sentiment using TextBlob with aggressive financial context detection"""
        try:
            blob = TextBlob(text)
            base_polarity = blob.sentiment.polarity
            
            # Apply financial lexicon adjustments with better word matching
            financial_adjustment = 0.0
            text_lower = text.lower()
            
            # Split text into words for better matching
            text_words = set(text_lower.split())
            
            # More aggressive lexicon matching
            for phrase, weight in finance_lexicon.items():
                # Exact phrase matching with higher weight
                if phrase in text_lower:
                    financial_adjustment += weight * 0.8  # Increased from 0.6
                
                # Word-based matching for single words (handles variations like jump/jumps)
                elif ' ' not in phrase:
                    # Check if any word starts with the phrase (handles jump -> jumps, rise -> rises)
                    for word in text_words:
                        if word.startswith(phrase) or phrase in word:
                            financial_adjustment += weight * 0.6  # Increased from 0.5
                            break
            
            # More comprehensive positive/negative indicators with higher weights
            strong_positive = ['soar', 'surge', 'spike', 'rally', 'breakout', 'moon', 'explode']
            moderate_positive = ['jump', 'rise', 'gain', 'up', 'climb', 'advance', 'higher', 'beat', 'exceed']
            weak_positive = ['increase', 'grow', 'improve', 'recover', '$', 'buy', 'bullish']
            
            strong_negative = ['crash', 'plunge', 'collapse', 'tank', 'plummet', 'nosedive']
            moderate_negative = ['fall', 'drop', 'decline', 'sink', 'slide', 'slip', 'tumble']
            weak_negative = ['down', 'lower', 'weak', 'miss', 'disappoint', 'concern', 'risk']
            
            # Calculate weighted sentiment scores
            sentiment_boost = 0.0
            
            # Strong indicators
            sentiment_boost += sum(0.5 for term in strong_positive 
                                 if any(term in word for word in text_words))
            sentiment_boost += sum(-0.5 for term in strong_negative 
                                 if any(term in word for word in text_words))
            
            # Moderate indicators  
            sentiment_boost += sum(0.3 for term in moderate_positive 
                                 if any(term in word for word in text_words))
            sentiment_boost += sum(-0.3 for term in moderate_negative 
                                 if any(term in word for word in text_words))
            
            # Weak indicators
            sentiment_boost += sum(0.15 for term in weak_positive 
                                 if any(term in word for word in text_words))
            sentiment_boost += sum(-0.15 for term in weak_negative 
                                 if any(term in word for word in text_words))
            
            # Special handling for institutional trading news (usually neutral but can indicate sentiment)
            if any(word in text_lower for word in ['acquired', 'buys', 'increases position', 'adds']):
                sentiment_boost += 0.1  # Slight positive for buying activity
            elif any(word in text_lower for word in ['sells', 'reduces', 'exits', 'dumps']):
                sentiment_boost -= 0.1  # Slight negative for selling activity
            
            # Earnings and performance context
            if 'earnings' in text_lower:
                if any(word in text_lower for word in ['beat', 'exceed', 'strong', 'solid']):
                    sentiment_boost += 0.4
                elif any(word in text_lower for word in ['miss', 'weak', 'disappointing']):
                    sentiment_boost -= 0.4
            
            # Price movement context with numbers
            import re
            # Look for percentage changes
            pct_match = re.search(r'(\d+(?:\.\d+)?%)', text_lower)
            if pct_match:
                pct_str = pct_match.group(1)
                try:
                    pct_value = float(pct_str.replace('%', ''))
                    if pct_value > 2:  # +2% is positive
                        sentiment_boost += 0.3
                    elif pct_value < -2:  # -2% is negative  
                        sentiment_boost -= 0.3
                except:
                    pass
            
            # Look for dollar amounts in context
            dollar_match = re.search(r'\$(\d+(?:\.\d+)?)', text_lower)
            if dollar_match and any(word in text_lower for word in ['jump', 'gain', 'rise', 'up']):
                sentiment_boost += 0.2  # Dollar gains are positive
            elif dollar_match and any(word in text_lower for word in ['drop', 'fall', 'down', 'loss']):
                sentiment_boost -= 0.2  # Dollar losses are negative
                
            # Combine all adjustments with higher base multiplier
            total_adjustment = financial_adjustment + sentiment_boost
            
            # If TextBlob gives neutral (0) but we have financial signals, boost the financial signals
            if abs(base_polarity) < 0.1 and abs(total_adjustment) > 0.1:
                adjusted_polarity = total_adjustment * 1.5  # Amplify when TextBlob is neutral
            else:
                adjusted_polarity = base_polarity + total_adjustment
            
            # Clamp to [-1, 1] range
            adjusted_polarity = max(-1.0, min(1.0, adjusted_polarity))
            
            # Create different compound score that considers TextBlob subjectivity
            blob = TextBlob(text)
            subjectivity = blob.sentiment.subjectivity
            compound_score = adjusted_polarity * subjectivity  # Weight by subjectivity
            
            return {
                'polarity': adjusted_polarity,
                'compound': compound_score
            }
            
        except Exception as e:
            if debug:
                print(f"TextBlob analysis error: {e}")
            return {'polarity': 0.0, 'compound': 0.0}

    def _analyze_title_with_keywords(self, title: str) -> Dict:
        """Analyze article title using keyword-based sentiment for better accuracy"""
        title_lower = title.lower()
        
        # Strong negative financial keywords/phrases
        strong_negative = [
            'pulled down', 'falls', 'drops', 'plunges', 'crashes', 'faces', 'downgrade', 'cut',
            'worst-performing', 'slips', 'declines', 'tumbles', 'sinks', 'probe', 'investigates',
            'challenges', 'struggles', 'disappoints', 'misses', 'below expectations', 'concerns',
            'risks', 'losses', 'credit rating downgrade', 'expenses soar', 'cost surge'
        ]
        
        # Strong positive financial keywords/phrases  
        strong_positive = [
            'no-brainer', 'soars', 'surging', 'rallies', 'climbs', 'gains', 'jumps', 'beats',
            'outperforms', 'buy recommendation', 'buy rating', 'overweight', 'bullish',
            'attractive entry', 'path to', 'double from here', 'upside', 'optimism'
        ]
        
        # Moderate negative
        moderate_negative = [
            'waiting for turnaround', 'held back', 'insufficient growth', 'mixed signals',
            'uncertainties', 'longer turnaround', 'shenanigans'
        ]
        
        # Moderate positive
        moderate_positive = [
            'analysts see', 'as a buy', 'wall street stays bullish', 'comeback', 'stabilized',
            'buffett', 'investing', 'attractive', 'potential upside'
        ]
        
        sentiment_score = 0.0
        
        # Check for strong signals first
        for phrase in strong_negative:
            if phrase in title_lower:
                sentiment_score -= 0.7
                break
                
        for phrase in strong_positive:
            if phrase in title_lower:
                sentiment_score += 0.7
                break
        
        # If no strong signal, check moderate signals
        if abs(sentiment_score) < 0.1:
            for phrase in moderate_negative:
                if phrase in title_lower:
                    sentiment_score -= 0.4
                    break
                    
            for phrase in moderate_positive:
                if phrase in title_lower:
                    sentiment_score += 0.4
                    break
        
        # Clamp to reasonable range
        sentiment_score = max(-0.8, min(0.8, sentiment_score))
        
        # For keyword analysis, use sentiment score as base but create different compound score
        compound_score = sentiment_score * 0.9  # Slightly lower confidence for keyword analysis
        return {'polarity': sentiment_score, 'compound': compound_score}

    def _remove_duplicates(self, sentiments: List[SentimentData]) -> List[SentimentData]:
        """Remove duplicate articles based on text similarity"""
        unique_sentiments = []
        seen_titles = set()
        
        for sentiment in sentiments:
            # Create a normalized title for comparison
            title = sentiment.text.split('.')[0]  # Get first sentence (usually the title)
            normalized_title = ' '.join(title.lower().split())
            
            # Skip if we've seen a very similar title
            if any(self._similarity(normalized_title, seen) > 0.8 for seen in seen_titles):
                continue
                
            seen_titles.add(normalized_title)
            unique_sentiments.append(sentiment)
        
        return unique_sentiments

    def _similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity between two text strings"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    def _save_analysis_data(self, results: Dict, all_sentiments: List[SentimentData]) -> None:
        """Save analysis results to JSON and CSV files in ./Data directory (backup/fallback storage)"""
        try:
            # Ensure Data directory exists
            data_dir = "./Data"
            os.makedirs(data_dir, exist_ok=True)
            
            # Generate timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            symbol = results["symbol"]
            
            # Save comprehensive JSON results
            json_filename = f"sentiment_analysis_{symbol}_{timestamp}.json"
            json_path = os.path.join(data_dir, json_filename)
            
            # Enhanced results with detailed newspaper3k integration data
            enhanced_results = results.copy()
            enhanced_results["raw_articles"] = []
            enhanced_results["newspaper3k_stats"] = {
                "total_articles": len(all_sentiments),
                "enhanced_articles": 0,
                "total_extracted_chars": 0,
                "avg_enhancement_ratio": 0.0,
                "sources_with_enhancement": []
            }
            
            source_enhancement_stats = {}
            
            for sentiment in all_sentiments:
                has_enhancement = hasattr(sentiment, 'raw_extracted_text') and sentiment.raw_extracted_text
                extracted_length = len(getattr(sentiment, 'raw_extracted_text', ''))
                
                if has_enhancement:
                    enhanced_results["newspaper3k_stats"]["enhanced_articles"] += 1
                    enhanced_results["newspaper3k_stats"]["total_extracted_chars"] += extracted_length
                    
                    # Track by source
                    source = sentiment.source
                    if source not in source_enhancement_stats:
                        source_enhancement_stats[source] = {"count": 0, "total_chars": 0}
                    source_enhancement_stats[source]["count"] += 1
                    source_enhancement_stats[source]["total_chars"] += extracted_length
                
                enhanced_results["raw_articles"].append({
                    "title": sentiment.text.split('.')[0] if '.' in sentiment.text else sentiment.text[:100],
                    "full_text": sentiment.text,
                    "raw_extracted_text": getattr(sentiment, 'raw_extracted_text', ''),
                    "extraction_successful": has_enhancement and extracted_length > 100,
                    "source": sentiment.source,
                    "url": sentiment.url,
                    "timestamp": sentiment.timestamp.isoformat(),
                    "polarity": round(sentiment.polarity, 4),
                    "compound": round(sentiment.compound, 4),
                    "sentiment_label": self._get_sentiment_label(sentiment.compound),
                    "text_length": len(sentiment.text),
                    "extracted_length": extracted_length,
                    "enhancement_ratio": round(extracted_length / max(1, len(sentiment.text)) * 100, 1) if has_enhancement else 0.0
                })
            
            # Calculate newspaper3k statistics
            if enhanced_results["newspaper3k_stats"]["enhanced_articles"] > 0:
                enhanced_results["newspaper3k_stats"]["avg_enhancement_ratio"] = round(
                    enhanced_results["newspaper3k_stats"]["total_extracted_chars"] / 
                    max(1, enhanced_results["newspaper3k_stats"]["enhanced_articles"]), 1
                )
            
            # Add source-level enhancement stats
            enhanced_results["newspaper3k_stats"]["sources_with_enhancement"] = [
                {"source": source, "enhanced_count": stats["count"], "avg_extracted_chars": round(stats["total_chars"] / stats["count"], 0)}
                for source, stats in source_enhancement_stats.items()
            ]
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(enhanced_results, f, indent=2, ensure_ascii=False)
            
            print(f"Saved detailed analysis to: {json_path}")
            
            # Save CSV summary for easy analysis
            csv_filename = f"sentiment_summary_{symbol}_{timestamp}.csv"
            csv_path = os.path.join(data_dir, csv_filename)
            
            # Create summary data for CSV
            summary_data = {
                'Symbol': [symbol],
                'Company_Name': [results["company_name"]],
                'Analysis_Timestamp': [results["analysis_timestamp"]],
                'Total_Articles': [results["total_articles"]],
                'Overall_Sentiment': [results["overall_sentiment"]],
                'Average_Sentiment': [results["sentiment_scores"]["average_sentiment"]],
                'Weighted_Avg_From_Sources': [results["sentiment_scores"]["weighted_avg_from_sources"]],
                'Positive_Count': [results["sentiment_distribution"]["positive"]],
                'Negative_Count': [results["sentiment_distribution"]["negative"]],
                'Neutral_Count': [results["sentiment_distribution"]["neutral"]],
                'Positive_Percentage': [results["sentiment_distribution"]["positive_percentage"]],
                'Negative_Percentage': [results["sentiment_distribution"]["negative_percentage"]],
                'Neutral_Percentage': [results["sentiment_distribution"]["neutral_percentage"]]
            }
            
            # Add source breakdown to CSV
            for source, data in results["source_breakdown"].items():
                safe_source = source.replace(" ", "_").replace("(", "").replace(")", "")
                summary_data[f'{safe_source}_Count'] = [data["count"]]
                summary_data[f'{safe_source}_Avg_Sentiment'] = [round(data["avg_sentiment"], 3)]
            
            df = pd.DataFrame(summary_data)
            df.to_csv(csv_path, index=False)
            
            print(f"Saved summary to: {csv_path}")
            
            # Save detailed articles CSV
            articles_csv_filename = f"articles_detail_{symbol}_{timestamp}.csv"
            articles_csv_path = os.path.join(data_dir, articles_csv_filename)
            
            articles_data = []
            for sentiment in all_sentiments:
                articles_data.append({
                    'Symbol': symbol,
                    'Title': sentiment.text.split('.')[0] if '.' in sentiment.text else sentiment.text[:100],
                    'Source': sentiment.source,
                    'URL': sentiment.url,
                    'Timestamp': sentiment.timestamp.isoformat(),
                    'Polarity': round(sentiment.polarity, 4),
                    'Compound': round(sentiment.compound, 4),
                    'Sentiment_Label': self._get_sentiment_label(sentiment.compound),
                    'Text_Length': len(sentiment.text),
                    'Full_Text': sentiment.text
                })
            
            articles_df = pd.DataFrame(articles_data)
            articles_df.to_csv(articles_csv_path, index=False, encoding='utf-8')
            
            print(f"Saved article details to: {articles_csv_path}")
            
        except Exception as e:
            print(f"Warning: Failed to save analysis data: {e}")
            if debug:
                import traceback
                traceback.print_exc()
    
    def _get_sentiment_label(self, compound: float) -> str:
        """Convert compound score to readable sentiment label with calibrated thresholds"""
        if compound > 0.75:
            return "Very Positive"
        elif compound > 0.05:  # Raised threshold for positive
            return "Positive"
        elif -0.05 < compound < 0.05:  # Wider neutral range for better accuracy
            return "Neutral"
        elif compound < -0.05:
            return "Negative"
        else:
            return "Very Negative"

    def analyze_sentiment(self, target_articles: int = 50, force_refresh: bool = False, max_cache_hours: float = 10000) -> Dict:
        """Main method to analyze sentiment for the stock with caching support
        
        Args:
            target_articles: Number of articles to target for analysis
            force_refresh: If True, bypass cache and perform fresh analysis
            max_cache_hours: Maximum age of cached data in hours (default 1.0)
            
        Returns:
            Dictionary containing sentiment analysis results
        """
        # Check cache first if not forcing refresh
        if self.use_database and not force_refresh:
            print(f"[CACHE] Checking cache for {self.symbol} (max age: {max_cache_hours}h)...")
            cached_result = self.db.get_cached_analysis(self.symbol, max_cache_hours)
            
            if cached_result:
                cache_age_minutes = cached_result.get('cache_age_minutes', 0)
                cached_articles = cached_result.get('raw_articles', [])
                
                # Check if cache has actual articles and sufficient count
                if cached_articles and len(cached_articles) >= target_articles:
                    print(f"[CACHE HIT] Found cached analysis for {self.symbol} (age: {cache_age_minutes:.1f}m)")
                    print(f"  - {len(cached_articles)} articles available")
                    print(f"  - Overall sentiment: {cached_result['overall_sentiment']}")
                    print(f"  - Average sentiment: {cached_result['sentiment_scores']['average_sentiment']:.3f}")
                    
                    # Limit articles to requested count
                    if len(cached_articles) > target_articles:
                        cached_result['raw_articles'] = cached_articles[:target_articles]
                        cached_result['recent_articles'] = cached_result.get('recent_articles', [])[:target_articles]
                        print(f"  - Limited to requested {target_articles} articles")
                    
                    return cached_result
                else:
                    print(f"[CACHE INSUFFICIENT] Found cached analysis but insufficient articles ({len(cached_articles)}/{target_articles})")
                    print(f"  - Performing fresh analysis to get {target_articles} articles...")
            else:
                print(f"[CACHE MISS] No recent cache found for {self.symbol}, performing fresh analysis...")
        elif force_refresh:
            print(f"[FORCE REFRESH] Force refresh requested for {self.symbol}, bypassing cache...")
        else:
            print(f"[NO DATABASE] Database caching disabled, using file storage only...")
        
        print(f"Starting intelligent sentiment analysis for {self.symbol}...")
        print(f"Target: {target_articles} articles from multiple sources")
        
        # Collect sentiment data intelligently
        all_sentiments = self.get_comprehensive_sentiment(target_articles)
        
        if not all_sentiments:
            return {"error": "No sentiment data collected"}
        
        # Calculate aggregate metrics
        total_articles = len(all_sentiments)
        avg_sentiment = sum(s.polarity for s in all_sentiments) / total_articles  # Keep using .polarity internally for now
        avg_compound = sum(s.compound for s in all_sentiments) / total_articles
        
        # Categorize sentiment with very sensitive thresholds
        positive_count = sum(1 for s in all_sentiments if s.compound > 0.01)  # Very sensitive
        negative_count = sum(1 for s in all_sentiments if s.compound < -0.01)  # Very sensitive  
        neutral_count = total_articles - positive_count - negative_count
        
        # Determine overall sentiment with very sensitive thresholds
        if avg_compound > 0.1:
            overall_sentiment = "Very Positive"
        elif avg_compound > 0.01:  # Very sensitive for positive
            overall_sentiment = "Positive"
        elif avg_compound > -0.01:  # Very narrow neutral range
            overall_sentiment = "Neutral"
        elif avg_compound > -0.1:
            overall_sentiment = "Negative"
        else:
            overall_sentiment = "Very Negative"
        
        # Source breakdown
        source_breakdown = {}
        for sentiment in all_sentiments:
            source = sentiment.source
            if source not in source_breakdown:
                source_breakdown[source] = {"count": 0, "avg_sentiment": 0.0}
            source_breakdown[source]["count"] += 1
            source_breakdown[source]["avg_sentiment"] += sentiment.compound
        
        # Calculate average sentiment per source
        for source in source_breakdown:
            if source_breakdown[source]["count"] > 0:
                source_breakdown[source]["avg_sentiment"] /= source_breakdown[source]["count"]
        
        # Calculate weighted average sentiment across all sources
        total_articles_from_sources = sum(data["count"] for data in source_breakdown.values())
        if total_articles_from_sources > 0:
            weighted_avg_sentiment = sum(
                data["avg_sentiment"] * data["count"] 
                for data in source_breakdown.values()
            ) / total_articles_from_sources
        else:
            weighted_avg_sentiment = 0.0
        
        # Recent articles (last few)
        recent_articles = []
        # Fix timezone issues by making all timestamps timezone-naive
        for sentiment in all_sentiments:
            if sentiment.timestamp.tzinfo is not None:
                sentiment.timestamp = sentiment.timestamp.replace(tzinfo=None)
        sorted_sentiments = sorted(all_sentiments, key=lambda x: x.timestamp, reverse=True)
        for sentiment in sorted_sentiments[:5]:  # Top 5 most recent
            recent_articles.append({
                "text": sentiment.text[:200] + "..." if len(sentiment.text) > 200 else sentiment.text,
                "sentiment": sentiment.compound,
                "source": sentiment.source,
                "url": sentiment.url,
                "timestamp": sentiment.timestamp.isoformat()
            })
        
        results = {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_articles": total_articles,
            "overall_sentiment": overall_sentiment,
            "sentiment_scores": {
                "average_sentiment": round(avg_sentiment, 3),
                "weighted_avg_from_sources": round(weighted_avg_sentiment, 3)
            },
            "sentiment_distribution": {
                "positive": positive_count,
                "negative": negative_count,
                "neutral": neutral_count,
                "positive_percentage": round((positive_count / total_articles) * 100, 1),
                "negative_percentage": round((negative_count / total_articles) * 100, 1),
                "neutral_percentage": round((neutral_count / total_articles) * 100, 1)
            },
            "source_breakdown": source_breakdown,
            "recent_articles": recent_articles
        }
        
        # Add raw_articles data to results before returning
        print(f"\n[DEBUG] BUILDING FINAL RESULTS - raw_articles section")
        results["raw_articles"] = []
        for sentiment in all_sentiments:
            results["raw_articles"].append({
                "text": sentiment.text,
                "sentiment": sentiment.compound,
                "source": sentiment.source,
                "url": sentiment.url,
                "timestamp": sentiment.timestamp.isoformat()
            })
        
        print(f"[DEBUG] FINAL RESULTS STRUCTURE:")
        print(f"[DEBUG]   total_articles: {results['total_articles']}")
        print(f"[DEBUG]   recent_articles count: {len(results['recent_articles'])}")
        print(f"[DEBUG]   raw_articles count: {len(results['raw_articles'])}")
        print(f"[DEBUG]   source_breakdown: {list(results['source_breakdown'].keys())}")
        
        # Save analysis data to database if available
        if self.use_database:
            try:
                # Prepare enhanced articles data for database (legacy format for analysis table)
                enhanced_articles_data = []
                for sentiment in all_sentiments:
                    enhanced_articles_data.append({
                        "title": sentiment.text.split('.')[0] if '.' in sentiment.text else sentiment.text[:100],
                        "text": sentiment.text,
                        "raw_extracted_text": getattr(sentiment, 'raw_extracted_text', ''),
                        "extraction_successful": hasattr(sentiment, 'raw_extracted_text') and sentiment.raw_extracted_text and len(sentiment.raw_extracted_text) > 100,
                        "source": sentiment.source,
                        "url": sentiment.url,
                        "timestamp": sentiment.timestamp.isoformat(),
                        "polarity": sentiment.polarity,
                        "sentiment": sentiment.compound,  # Map to compound for database
                        "sentiment_label": self._get_sentiment_label(sentiment.compound),
                        "text_length": len(sentiment.text),
                        "extracted_length": len(getattr(sentiment, 'raw_extracted_text', '')),
                        "enhancement_ratio": round(len(getattr(sentiment, 'raw_extracted_text', '')) / max(1, len(sentiment.text)) * 100, 1) if hasattr(sentiment, 'raw_extracted_text') and sentiment.raw_extracted_text else 0.0
                    })
                
                # Save summary analysis to main table
                analysis_id = self.db.save_analysis(results, enhanced_articles_data)
                print(f"[DATABASE] Saved analysis summary to database (ID: {analysis_id})")
                
            except Exception as e:
                print(f"[WARNING] Failed to save analysis to database: {e}")
                print(f"   Analysis will still be saved to file storage")
        
        # Save analysis data to ./Data directory (as backup or primary if no DB)
        self._save_analysis_data(results, all_sentiments)
        
        # Clean up Selenium driver to prevent hanging
        try:
            from scrapers.base_scraper import BaseScraper
            BaseScraper.cleanup_selenium_driver()
        except Exception as e:
            print(f"Warning: Selenium cleanup failed: {e}")
        
        return results


def main():
    
    """Main function with enhanced CLI interface"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Stock Sentiment Analysis with PostgreSQL Caching')
    parser.add_argument('symbol', help='Stock symbol to analyze (e.g., AAPL)')
    parser.add_argument('--articles', type=int, default=50, help='Number of articles to target (default: 50)')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh, bypass cache')
    parser.add_argument('--cache-hours', type=float, default=1.0, help='Max cache age in hours (default: 1.0)')
    parser.add_argument('--no-database', action='store_true', help='Disable database caching')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = StockSentimentAnalyzer(args.symbol, use_database=not args.no_database)
    
    # Run analysis
    results = analyzer.analyze_sentiment(
        target_articles=args.articles,
        force_refresh=args.force_refresh,
        max_cache_hours=args.cache_hours
    )
    
    if args.json:
        import json
        print(json.dumps(results, indent=2, default=str))
    else:
        # Pretty print summary
        print(f"\n=== SENTIMENT ANALYSIS SUMMARY ===")
        print(f"Symbol: {results['symbol']} ({results['company_name']})")
        print(f"Overall Sentiment: {results['overall_sentiment']}")
        print(f"Average Sentiment Score: {results['sentiment_scores']['average_sentiment']:.3f}")
        print(f"Total Articles: {results['total_articles']}")
        print(f"Positive: {results['sentiment_distribution']['positive_percentage']:.1f}%")
        print(f"Negative: {results['sentiment_distribution']['negative_percentage']:.1f}%")
        print(f"Neutral: {results['sentiment_distribution']['neutral_percentage']:.1f}%")
        
        if results.get('cached'):
            print(f"\n[INFO] Data from cache (age: {results.get('cache_age_minutes', 0):.1f}m)")
        
        print(f"\n=== SOURCE BREAKDOWN ===")
        for source, data in results['source_breakdown'].items():
            print(f"{source}: {data['count']} articles (avg: {data['avg_sentiment']:.3f})")


if __name__ == "__main__":
    main()