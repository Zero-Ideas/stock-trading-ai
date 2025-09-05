#!/usr/bin/env python3
"""
Google News scraper for stock sentiment analysis
"""

from typing import List
import re
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime
from .base_scraper import BaseScraper, SentimentData


class GoogleNewsScraper(BaseScraper):
    """Scraper for Google News RSS feeds"""
    
    @property
    def source_name(self) -> str:
        return "Google News"
    
    def __init__(self, symbol: str, debug: bool = False):
        super().__init__(symbol, debug)
        self.company_name = self._get_company_name()
        self.skip_enhancement = True  # Skip enhancement to prevent hanging during testing
    
    def _get_company_name(self) -> str:
        """Get company name for the stock symbol"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(self.symbol)
            info = ticker.info
            
            # Try different fields that might contain the company name
            for field in ['longName', 'shortName', 'companyName']:
                if field in info and info[field]:
                    return info[field]
                    
        except Exception as e:
            if self.debug:
                print(f"Could not fetch company name: {e}")
        
        return self.symbol  # Fallback to symbol if company name not found
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats to datetime"""
        try:
            from dateutil.parser import parse
            return parse(date_str)
        except:
            return datetime.now()
    
    def _analyze_text(self, text: str) -> dict:
        """Analyze text sentiment (placeholder - will be handled by main analyzer)"""
        # This is a placeholder - actual sentiment analysis will be done by the main StockSentimentAnalyzer
        return {'polarity': 0.0, 'compound': 0.0}
    
    def scrape(self, max_articles: int = 10) -> List[SentimentData]:
        """Scrape Google News for stock-related articles with multiple search strategies"""
        import time
        start_time = time.time()
        max_scrape_time = 120  # 2 minutes maximum scraping time
        
        sentiments = []
        
        # Multiple query strategies for better coverage
        queries = [
            f"{self.symbol} stock",
            f"{self.company_name}" if self.company_name != self.symbol else f"{self.symbol} company",
            f"{self.symbol} earnings",
            f"{self.symbol} news",
            f"{self.company_name} stock" if self.company_name != self.symbol else f"{self.symbol} market"
        ]
        
        # Remove duplicates while preserving order
        unique_queries = []
        for query in queries:
            if query not in unique_queries:
                unique_queries.append(query)
        
        articles_per_query = max(3, max_articles // len(unique_queries) + 2)
        
        for query in unique_queries:
            # Check timeout
            if time.time() - start_time > max_scrape_time:
                if self.debug:
                    print(f"  Google News scraping timed out after {max_scrape_time}s")
                break
                
            if len(sentiments) >= max_articles:
                break
                
            try:
                url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
                
                if self.debug:
                    print(f"  Google News query: {query}")
                
                response = self.make_request(url)
                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')[:articles_per_query]
                
                for item in items:
                    # Check timeout on each article
                    if time.time() - start_time > max_scrape_time:
                        if self.debug:
                            print(f"  Timeout reached during article processing")
                        break
                        
                    if len(sentiments) >= max_articles:
                        break
                        
                    title = item.title.text if item.title else ""
                    description = item.description.text if item.description else ""
                    text = f"{title}. {description}"
                    
                    # Clean HTML tags from description
                    text = re.sub(r'<[^>]+>', '', text)
                    text = self.clean_text(text)
                    
                    pub_date = item.pubDate.text if item.pubDate else ""
                    timestamp = self._parse_date(pub_date)
                    
                    link = item.link.text if item.link else ""
                    
                    # More flexible relevance check
                    if not self._is_stock_relevant(title, description):
                        continue
                    
                    # Check for duplicates based on title similarity
                    if self._is_duplicate(title, sentiments):
                        continue
                    
                    sentiment = self._analyze_text(text)
                    article_data = SentimentData(
                        text=text,
                        source="Google News",
                        timestamp=timestamp,
                        polarity=sentiment['polarity'],
                        compound=sentiment['compound'],
                        url=link
                    )
                    
                    # Try to enhance with full article content (with timeout)
                    if link and not self.skip_enhancement:
                        try:
                            import concurrent.futures
                            import threading
                            
                            # Use timeout to prevent enhancement from hanging
                            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                                future = executor.submit(self.enhance_article_data, article_data)
                                try:
                                    article_data = future.result(timeout=10)  # 10 second timeout
                                except concurrent.futures.TimeoutError:
                                    if self.debug:
                                        print(f"    Article enhancement timed out after 10s - using original")
                                    future.cancel()  # Try to cancel
                                    
                        except Exception as e:
                            if self.debug:
                                print(f"    Failed to enhance article: {e}")
                    elif self.skip_enhancement and self.debug:
                        print(f"    Skipping enhancement to prevent hanging")
                    
                    sentiments.append(article_data)
                
                # Add delay between queries
                self.random_delay(0.5, 1.0)
                
            except Exception as e:
                if self.debug:
                    print(f"  Google News query '{query}' failed: {str(e)}")
                continue
        
        return sentiments
    
    def _is_stock_relevant(self, title: str, description: str = "") -> bool:
        """Enhanced relevance check for stock-related content"""
        text_to_check = f"{title} {description}".lower()
        
        # Check for direct symbol mention
        if self.symbol.lower() in text_to_check:
            return True
        
        # Check for company name (handle partial matches)
        if self.company_name != self.symbol:
            company_words = self.company_name.lower().split()
            # If any significant word from company name appears
            for word in company_words:
                if len(word) > 3 and word in text_to_check:  # Ignore short words like "Inc", "Co"
                    return True
        
        # Financial keywords that suggest stock relevance
        financial_keywords = [
            'stock', 'shares', 'trading', 'earnings', 'revenue', 'profit', 'dividend',
            'market', 'investor', 'investment', 'financial', 'quarter', 'analyst',
            'price', 'valuation', 'buy', 'sell', 'rating', 'upgrade', 'downgrade'
        ]
        
        # If title contains financial keywords, it's likely relevant
        title_lower = title.lower()
        if any(keyword in title_lower for keyword in financial_keywords):
            # Additional check to ensure it's not completely unrelated
            if len(title_lower) > 20:  # Ignore very short titles
                return True
        
        return False
    
    def _is_duplicate(self, new_title: str, existing_sentiments: List[SentimentData]) -> bool:
        """Check if this title is too similar to existing ones"""
        if not existing_sentiments:
            return False
        
        new_words = set(new_title.lower().split())
        
        for sentiment in existing_sentiments:
            existing_title = sentiment.text.split('.')[0]  # Get first sentence (title)
            existing_words = set(existing_title.lower().split())
            
            # Calculate similarity
            if new_words and existing_words:
                intersection = new_words.intersection(existing_words)
                union = new_words.union(existing_words)
                similarity = len(intersection) / len(union) if union else 0
                
                if similarity > 0.7:  # 70% similarity threshold
                    return True
        
        return False