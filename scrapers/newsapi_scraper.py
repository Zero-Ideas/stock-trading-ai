#!/usr/bin/env python3
"""
NewsAPI scraper for stock sentiment analysis
"""

from typing import List
import requests
import re
import time
import random
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from .base_scraper import BaseScraper, SentimentData

# Load environment variables
load_dotenv()


class NewsAPIScraper(BaseScraper):
    """Scraper for NewsAPI.org news articles"""
    
    @property
    def source_name(self) -> str:
        return "NewsAPI"
    
    def __init__(self, symbol: str, debug: bool = False, api_key: str = None):
        super().__init__(symbol, debug)
        self.api_key = api_key or os.getenv('NEWSAPI_KEY')
        if not self.api_key:
            raise ValueError("NewsAPI key must be provided either as parameter or environment variable 'NEWSAPI_KEY'")
        self.company_name = self._get_company_name()
    
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
    
    def _analyze_text(self, text: str) -> dict:
        """Analyze text sentiment (placeholder - will be handled by main analyzer)"""
        # This is a placeholder - actual sentiment analysis will be done by the main StockSentimentAnalyzer
        return {'polarity': 0.0, 'compound': 0.0}
    
    def scrape(self, max_articles: int = 20) -> List[SentimentData]:
        """Scrape NewsAPI for stock-related articles"""
        sentiments = []
        
        if not self.api_key or self.api_key == "YOUR_NEWS_API_KEY_HERE":
            if self.debug:
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
                        'apiKey': self.api_key,
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
                        if self.debug:
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
                            text = self.clean_text(text)
                            
                            if len(text) < 50:  # Skip very short articles
                                continue
                            
                            # Check relevance
                            if not self.is_relevant_content(title, f"{description} {content}"):
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
                            
                            # Create article data
                            article_data = SentimentData(
                                text=text,
                                source=f"NewsAPI ({source_name})",
                                timestamp=timestamp,
                                polarity=sentiment['polarity'],
                                compound=sentiment['compound'],
                                url=url
                            )
                            
                            # Try to enhance with full article content using newspaper3k
                            if url:
                                try:
                                    article_data = self.enhance_article_data(article_data)
                                except Exception as e:
                                    if self.debug:
                                        print(f"    Failed to enhance NewsAPI article: {e}")
                            
                            sentiments.append(article_data)
                            
                        except Exception as e:
                            if self.debug:
                                print(f"    Error processing NewsAPI article: {e}")
                            continue
                    
                    # Rate limiting - NewsAPI allows 1000 requests per day for free tier
                    self.random_delay(0.5, 1.0)
                    
                except requests.exceptions.RequestException as e:
                    if self.debug:
                        print(f"NewsAPI request error for query '{query}': {e}")
                    continue
                except Exception as e:
                    if self.debug:
                        print(f"NewsAPI error for query '{query}': {e}")
                    continue
            
            if self.debug and sentiments:
                print(f"NewsAPI: Successfully collected {len(sentiments)} articles")
            
        except Exception as e:
            if self.debug:
                print(f"NewsAPI general error: {e}")
                import traceback
                traceback.print_exc()
        
        return sentiments