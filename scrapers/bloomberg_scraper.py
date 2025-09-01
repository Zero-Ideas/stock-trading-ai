#!/usr/bin/env python3
"""
Bloomberg scraper for stock sentiment analysis
"""

from typing import List
import random
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, SentimentData


class BloombergScraper(BaseScraper):
    """Enhanced Bloomberg scraper with improved reliability"""
    
    @property
    def source_name(self) -> str:
        return "Bloomberg"
    
    def _analyze_text(self, text: str) -> dict:
        """Analyze text sentiment (placeholder - will be handled by main analyzer)"""
        # This is a placeholder - actual sentiment analysis will be done by the main StockSentimentAnalyzer
        return {'polarity': 0.0, 'compound': 0.0}
    
    def scrape(self, max_articles: int = 10) -> List[SentimentData]:
        """Enhanced Bloomberg scraper with improved reliability"""
        sentiments = []
        
        try:
            # Multiple Bloomberg URL strategies
            url_strategies = [
                # Strategy 1: Company search
                
                (f"https://www.bloomberg.com/search?query={quote(self.symbol)}", "search"),
                # Strategy 2: Markets section  
                (f"https://www.bloomberg.com/quote/{self.symbol}:US", "quote"),
                # Strategy 3: Alternative quote format
                (f"https://www.bloomberg.com/quote/{self.symbol}", "quote_simple"),
                # Strategy 4: News section search
                #(f"https://www.bloomberg.com/news/search?query={quote(self.symbol)}", "news_search"),
                # Strategy 5: Markets homepage with company filter
                (f"https://www.bloomberg.com/markets/stocks/{self.symbol.lower()}-us", "markets")
            ]
            
            for search_url, strategy_name in url_strategies:
                if len(sentiments) >= max_articles:
                    break
                    
                try:
                    # Enhanced headers for Bloomberg
                    headers = {
                        'User-Agent': self.get_random_user_agent(),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    }
                    
                    # Multiple attempts per strategy
                    response = None
                    for attempt in range(2):
                        try:
                            response = self.make_request(search_url, headers=headers, timeout=20)
                            if response.status_code == 200:
                                break
                            elif response.status_code == 403:
                                if self.debug:
                                    print(f"      Bloomberg {strategy_name} blocked (403), attempt {attempt + 1}")
                                # Try different user agent
                                headers['User-Agent'] = self.get_random_user_agent()
                                self.random_delay(2.0, 4.0)
                            else:
                                if self.debug:
                                    print(f"      Bloomberg {strategy_name}: HTTP {response.status_code}")
                                break
                        except Exception as e:
                            if self.debug:
                                print(f"      Request failed attempt {attempt + 1}: {e}")
                            if attempt == 0:
                                self.random_delay(1.0, 3.0)
                    
                    if not response or response.status_code != 200:
                        continue
                        
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Enhanced selectors based on strategy
                    if strategy_name == "search":
                        article_selectors = [
                            'div[data-module="SearchStory"]',
                            'div[data-component="search-result"]',
                            'article[data-module="story"]',
                            'div.search-result',
                            'div[class*="story"]'
                        ]
                    elif strategy_name in ["quote", "quote_simple", "markets"]:
                        article_selectors = [
                            'div[data-module="RelatedStories"]',
                            'div[data-module="News"]',
                            'article',
                            'div.story-package-module__story',
                            'div[class*="story"]'
                        ]
                    else:  # news_search
                        article_selectors = [
                            'div[data-module="NewsStory"]',
                            'article[data-module="story"]',
                            'div[class*="news-story"]',
                            'div.story-package-module__story'
                        ]
                    
                    articles = []
                    for selector in article_selectors:
                        found = soup.select(selector)[:max_articles - len(sentiments)]
                        if found:
                            articles = found
                            break
                    
                    strategy_articles = self._extract_bloomberg_articles(soup, articles, max_articles - len(sentiments))
                    if strategy_articles:
                        sentiments.extend(strategy_articles)
                        if self.debug:
                            print(f"      Bloomberg {strategy_name}: Found {len(strategy_articles)} articles")
                    
                    # Rate limiting between strategies
                    self.random_delay(1.5, 3.0)
                        
                except Exception as e:
                    if self.debug:
                        print(f"      Bloomberg {strategy_name} failed: {e}")
                    continue
        
        except Exception as e:
            if self.debug:
                print(f"Bloomberg scraping error: {e}")
        
        # If no articles found, try RSS feeds as fallback
        if not sentiments:
            if self.debug:
                print("      Trying Bloomberg RSS feeds...")
            sentiments = self._try_bloomberg_rss(max_articles)
        
        return sentiments
    
    def _extract_bloomberg_articles(self, soup, articles, max_needed: int) -> List[SentimentData]:
        """Extract articles from Bloomberg page"""
        extracted_articles = []
        
        for article in articles[:max_needed]:
            try:
                # Enhanced title extraction
                title_elem = None
                title_selectors = ['h3', 'h2', 'h1', 'a[data-module="headline"]', 'a']
                
                for selector in title_selectors:
                    title_elem = article.find(selector)
                    if title_elem:
                        break
                
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                if not title or len(title) < 10:
                    continue
                
                # Check relevance
                if not self.is_relevant_content(title):
                    continue
                
                # Enhanced summary extraction
                summary = ""
                summary_selectors = [
                    'p[data-module="summary"]',
                    'div[data-module="abstract"]', 
                    'p',
                    'div.abstract',
                    'div.summary'
                ]
                
                for selector in summary_selectors:
                    summary_elem = article.find(selector)
                    if summary_elem:
                        summary_text = summary_elem.get_text(strip=True)
                        if summary_text and len(summary_text) > 20:
                            summary = summary_text[:300]  # Limit length
                            break
                
                text = f"{title}. {summary}" if summary else title
                text = self.clean_text(text)
                
                # Enhanced URL extraction
                url = ""
                link_elem = article.find('a')
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    if href.startswith('/'):
                        url = f"https://www.bloomberg.com{href}"
                    elif href.startswith('http'):
                        url = href
                
                sentiment = self._analyze_text(text)
                article_data = SentimentData(
                    text=text,
                    source="Bloomberg",
                    timestamp=datetime.now() - timedelta(hours=random.randint(1, 24)),
                    polarity=sentiment['polarity'],
                    compound=sentiment['compound'],
                    url=url
                )
                
                # Try to enhance with full article content
                if url:
                    try:
                        article_data = self.enhance_article_data(article_data)
                    except Exception as e:
                        if self.debug:
                            print(f"        Failed to enhance Bloomberg article: {e}")
                
                extracted_articles.append(article_data)
                
            except Exception as e:
                if self.debug:
                    print(f"        Error processing Bloomberg article: {e}")
                continue
        
        return extracted_articles
    
    def _try_bloomberg_rss(self, max_articles: int) -> List[SentimentData]:
        """Try Bloomberg RSS feeds as fallback"""
        sentiments = []
        
        try:
            # Bloomberg RSS feeds
            rss_feeds = [
                "https://feeds.bloomberg.com/markets/news.rss",
                "https://feeds.bloomberg.com/economics/news.rss",
                "https://feeds.bloomberg.com/technology/news.rss"
            ]
            
            for rss_url in rss_feeds:
                if len(sentiments) >= max_articles:
                    break
                
                try:
                    headers = {'User-Agent': self.get_random_user_agent()}
                    response = self.session.get(rss_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'xml')
                        items = soup.find_all('item')[:max_articles - len(sentiments)]
                        
                        for item in items:
                            title = item.title.text if item.title else ""
                            description = item.description.text if item.description else ""
                            
                            if not title or not self.is_relevant_content(title, description):
                                continue
                            
                            text = f"{title}. {description}"
                            text = self.clean_text(text)
                            
                            link = item.link.text if item.link else ""
                            
                            sentiment = self._analyze_text(text)
                            sentiments.append(SentimentData(
                                text=text,
                                source="Bloomberg (RSS)",
                                timestamp=datetime.now() - timedelta(hours=random.randint(1, 24)),
                                polarity=sentiment['polarity'],
                                compound=sentiment['compound'],
                                url=link
                            ))
                            
                            if len(sentiments) >= max_articles:
                                break
                    
                    self.random_delay(1.0, 2.0)
                    
                except Exception as e:
                    if self.debug:
                        print(f"        Bloomberg RSS {rss_url} failed: {e}")
                    continue
                    
        except Exception as e:
            if self.debug:
                print(f"        Bloomberg RSS fallback failed: {e}")
        
        return sentiments