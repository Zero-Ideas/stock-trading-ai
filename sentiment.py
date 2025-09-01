#!/usr/bin/env python3
"""
Stock Sentiment Analyzer - Modular Interface
A web scraper that analyzes public sentiment for stock symbols using news and social media data.
"""

import warnings
from typing import List, Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from textblob import TextBlob
import yfinance as yf
import re
import json
import csv
import os
import pandas as pd

# Import modular scrapers
from scrapers import (
    SentimentData, GoogleNewsScraper, NewsAPIScraper, YahooFinanceScraper,
    MarketWatchScraper, SeekingAlphaScraper, BenzingaScraper,
    FinancialTimesScraper, BloombergScraper, ReutersScraper
)

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

# Global debug flag
debug = False

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
    """Main interface for stock sentiment analysis using modular scrapers"""
    
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
                print("FINBERT VARIABLE:", self.finbert_pipeline)
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
        
        # Initialize all improved scrapers (including previously disabled ones)
        all_scrapers = {
            # High-performance scrapers (now with newspaper3k enhancement)
            'newsapi': NewsAPIScraper(symbol, debug),  # Re-enabled - now works great with newspaper3k
            'google_news': GoogleNewsScraper(symbol, debug),
            'yahoo_finance': YahooFinanceScraper(symbol, debug),
            
            # Improved scrapers with anti-bot protection
            'bloomberg': BloombergScraper(symbol, debug),  # Re-enabled - improved with fallbacks
            '#seeking_alpha': SeekingAlphaScraper(symbol, debug),
            'marketwatch': MarketWatchScraper(symbol, debug),
            #'reuters': ReutersScraper(symbol, debug),
            
            # Additional sources
            #'benzinga': BenzingaScraper(symbol, debug),
            #'financial_times': FinancialTimesScraper(symbol, debug),
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
        
        # Cache for performance optimization
        self._sentiment_cache = {}
        self._company_name_cache = None
        
        # Get company name for better analysis (with caching)
        self.company_name = self._get_company_name_from_yfinance()

    def _get_company_name_from_yfinance(self) -> str:
        """Get company name using yfinance with caching"""
        if self._company_name_cache is not None:
            return self._company_name_cache
        
        try:
            ticker = yf.Ticker(self.symbol)
            info = ticker.info
            
            # Try different fields that might contain the company name
            for field in ['longName', 'shortName', 'companyName']:
                if field in info and info[field]:
                    self._company_name_cache = info[field]
                    return self._company_name_cache
                    
        except Exception as e:
            if debug:
                print(f"Could not fetch company name: {e}")
        
        self._company_name_cache = self.symbol  # Fallback to symbol
        return self._company_name_cache

    def _run_scraper_with_retry(self, scraper, max_articles: int) -> List[SentimentData]:
        """Run a scraper with retry logic, error handling, and performance optimization"""
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                results = scraper.scrape(max_articles)
                
                # Enhanced post-processing with caching and batching
                if results:
                    results = self._post_process_scraper_results(results, scraper.source_name)
                
                return results
            except Exception as e:
                if debug:
                    print(f"    Attempt {attempt + 1} failed for {scraper.source_name}: {e}")
                if attempt == max_retries - 1:
                    print(f"    {scraper.source_name}: All attempts failed - {str(e)}")
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
        """Gather sentiment data from multiple sources using multithreading"""
        all_sentiments = []
        
        # Prepare scraper tasks
        scraper_tasks = []
        articles_per_source = max(10, target_articles // len(self.scrapers) + 5)
        
        for name, scraper in self.scrapers.items():
            scraper_tasks.append((scraper, articles_per_source))
        
        print(f"Target: {target_articles} articles")
        print(f"Running {len(scraper_tasks)} scrapers in parallel...")
        
        # Use ThreadPoolExecutor with optimized worker count for better performance
        optimal_workers = min(len(scraper_tasks), 6)  # Limit concurrent connections
        with ThreadPoolExecutor(max_workers=optimal_workers, thread_name_prefix="scraper") as executor:
            # Submit all scraper tasks
            future_to_scraper = {}
            for scraper, max_articles in scraper_tasks:
                future = executor.submit(self._run_scraper_with_retry, scraper, max_articles)
                future_to_scraper[future] = scraper.source_name
            
            # Collect results as they complete with enhanced error handling
            scraper_stats = {}
            for future in as_completed(future_to_scraper):
                source_name = future_to_scraper[future]
                try:
                    source_sentiments = future.result(timeout=45)  # Increased timeout for enhanced scrapers
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
        
        print(f"Total unique articles collected: {len(unique_sentiments)}")
        return unique_sentiments

    def _analyze_text(self, text: str) -> Dict:
        """Analyze sentiment of text using available methods"""
        try:
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
        """Save analysis results to JSON and CSV files in ./Data directory"""
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
        
        # Save analysis data to ./Data directory
        self._save_analysis_data(results, all_sentiments)
        
        # Clean up Selenium driver to prevent hanging
        try:
            from scrapers.base_scraper import BaseScraper
            BaseScraper.cleanup_selenium_driver()
        except Exception as e:
            print(f"Warning: Selenium cleanup failed: {e}")
        
        return results


if __name__ == "__main__":
    # Example usage
    analyzer = StockSentimentAnalyzer("AAPL")
    results = analyzer.analyze_sentiment(target_articles=100)
    
    import json
    print(json.dumps(results, indent=2, default=str))