#!/usr/bin/env python3
"""
Seeking Alpha scraper for stock sentiment analysis
"""

from typing import List
import random
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, SentimentData


class SeekingAlphaScraper(BaseScraper):
    """Scraper for Seeking Alpha stock analysis"""
    
    @property
    def source_name(self) -> str:
        return "Seeking Alpha"
    
    def __init__(self, symbol: str, debug: bool = False):
        super().__init__(symbol, debug)
    
    def _analyze_text(self, text: str) -> dict:
        """Analyze text sentiment (placeholder - will be handled by main analyzer)"""
        # This is a placeholder - actual sentiment analysis will be done by the main StockSentimentAnalyzer
        return {'polarity': 0.0, 'compound': 0.0}
    
    def scrape(self, max_articles: int = 8) -> List[SentimentData]:
        """Enhanced Seeking Alpha scraper with improved anti-bot measures"""
        sentiments = []
        
        try:
            # Multiple URL strategies with fallbacks
            url_strategies = [
                # Strategy 1: Symbol-specific pages
                (f"https://seekingalpha.com/symbol/{self.symbol}/news", "news_page"),
                (f"https://seekingalpha.com/symbol/{self.symbol}", "symbol_page"),
                # Strategy 2: Alternative formats
                (f"https://seekingalpha.com/symbol/{self.symbol.upper()}/news", "news_page_upper"),
                (f"https://seekingalpha.com/symbol/{self.symbol.lower()}/analysis", "analysis_page"),
                # Strategy 3: Search fallback
                (f"https://seekingalpha.com/search?q={quote(self.symbol)}", "search_page"),
                # Strategy 4: Mobile site (sometimes less protected)
                (f"https://m.seekingalpha.com/symbol/{self.symbol}", "mobile_page")
            ]
            
            for search_url, strategy_name in url_strategies:
                if len(sentiments) >= max_articles:
                    break
                    
                try:
                    # Enhanced headers to mimic real browser
                    headers = self._get_enhanced_headers()
                    
                    # Multiple retry attempts with different approaches
                    response = self._make_resilient_request(search_url, headers, max_attempts=3)
                    
                    if not response or response.status_code != 200:
                        if self.debug:
                            status = response.status_code if response else "No Response"
                            print(f"      Seeking Alpha {strategy_name} failed: HTTP {status}")
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
                            
                            # Check relevance
                            if not self.is_relevant_content(title):
                                continue
                            
                            # Look for summary
                            summary_elem = (article.find('p') or 
                                          article.find('div', {'data-testid': 'post-list-content'}))
                            summary = summary_elem.get_text(strip=True) if summary_elem else ""
                            
                            text = f"{title}. {summary}" if summary else title
                            text = self.clean_text(text)
                            
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
                            
                        except Exception as e:
                            if self.debug:
                                print(f"Error processing Seeking Alpha article: {e}")
                            continue
                            
                    # Add delay between URLs
                    self.random_delay(1.0, 2.0)
                            
                except Exception as e:
                    if self.debug:
                        print(f"Error with Seeking Alpha URL {search_url}: {e}")
                    continue
        
        except Exception as e:
            if self.debug:
                print(f"Seeking Alpha scraping error: {e}")
        
        # If no articles found from any strategy, try RSS feed as last resort
        if not sentiments and self.debug:
            print("      Trying Seeking Alpha RSS feeds as fallback...")
            sentiments = self._try_seekingalpha_rss(max_articles)
        
        return sentiments
    
    def _get_enhanced_headers(self) -> dict:
        """Generate enhanced headers to bypass anti-bot protection"""
        base_headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Randomly add some optional headers
        optional_headers = {
            'Sec-CH-UA': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"Windows"',
            'Referer': 'https://www.google.com/',
        }
        
        # Add some optional headers randomly
        for header, value in optional_headers.items():
            if random.random() > 0.5:  # 50% chance to include each optional header
                base_headers[header] = value
        
        return base_headers
    
    def _make_resilient_request(self, url: str, headers: dict, max_attempts: int = 3):
        """Make request with multiple retry strategies"""
        for attempt in range(max_attempts):
            try:
                # Add random delay between attempts
                if attempt > 0:
                    self.random_delay(2.0 + attempt, 5.0 + attempt * 2)
                    # Change User-Agent for retry
                    headers['User-Agent'] = self.get_random_user_agent()
                
                # Try different timeout values
                timeout = 15 + (attempt * 5)
                
                response = self.session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    if self.debug:
                        print(f"        403 Forbidden on attempt {attempt + 1}, retrying...")
                    continue
                elif response.status_code in [429, 503]:
                    if self.debug:
                        print(f"        Rate limited ({response.status_code}) on attempt {attempt + 1}")
                    # Longer delay for rate limiting
                    self.random_delay(5.0 + attempt * 3, 10.0 + attempt * 5)
                    continue
                else:
                    if self.debug:
                        print(f"        HTTP {response.status_code} on attempt {attempt + 1}")
                    return response
                    
            except Exception as e:
                if self.debug:
                    print(f"        Request attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    return None
                continue
        
        return None
    
    def _try_seekingalpha_rss(self, max_articles: int) -> List[SentimentData]:
        """Try to get articles from Seeking Alpha RSS feeds as fallback"""
        sentiments = []
        
        try:
            # Seeking Alpha RSS feeds
            rss_urls = [
                "https://seekingalpha.com/feed.xml",
                f"https://seekingalpha.com/symbol/{self.symbol}/feed",
                "https://seekingalpha.com/market-news/feed"
            ]
            
            for rss_url in rss_urls:
                if len(sentiments) >= max_articles:
                    break
                
                try:
                    headers = {'User-Agent': self.get_random_user_agent()}
                    response = self.session.get(rss_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        from bs4 import BeautifulSoup
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
                                source="Seeking Alpha (RSS)",
                                timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                                polarity=sentiment['polarity'],
                                compound=sentiment['compound'],
                                url=link
                            ))
                            
                            if len(sentiments) >= max_articles:
                                break
                    
                    self.random_delay(1.0, 2.0)
                    
                except Exception as e:
                    if self.debug:
                        print(f"        RSS feed {rss_url} failed: {e}")
                    continue
                    
        except Exception as e:
            if self.debug:
                print(f"        RSS fallback failed: {e}")
        
        return sentiments