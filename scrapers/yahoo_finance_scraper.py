#!/usr/bin/env python3
"""
Yahoo Finance scraper for stock sentiment analysis
"""

from typing import List
import time
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, SentimentData


class YahooFinanceScraper(BaseScraper):
    """Enhanced Yahoo Finance scraper with multiple fallback strategies"""
    
    @property
    def source_name(self) -> str:
        return "Yahoo Finance"
    
    def __init__(self, symbol: str, debug: bool = False):
        super().__init__(symbol, debug)
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
    
    def scrape(self, max_articles: int = 12) -> List[SentimentData]:
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
                if self.debug:
                    print(f"  Trying Yahoo Finance strategy {strategy_num}: {url}")
                
                # Enhanced headers to avoid 404s
                headers = {
                    'User-Agent': self.get_random_user_agent(),
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
                }
                
                # Try the request with retries
                response = None
                for attempt in range(3):  # 3 attempts per strategy
                    try:
                        response = self.make_request(url, headers=headers, timeout=20)
                        break
                    except Exception as e:
                        if self.debug:
                            print(f"    Request failed on attempt {attempt + 1}: {e}")
                        if attempt < 2:  # Don't sleep on last attempt
                            self.random_delay(0.5, 2.0)
                
                if not response or response.status_code != 200:
                    continue
                    
                soup = BeautifulSoup(response.content, 'html.parser')
                articles_found = self._extract_yahoo_articles(soup, max_articles - len(sentiments))
                
                if articles_found:
                    sentiments.extend(articles_found)
                    if self.debug:
                        print(f"    Found {len(articles_found)} articles with strategy {strategy_num}")
                
                # Brief delay between strategies
                self.random_delay(1.0, 2.0)
                
            except Exception as e:
                if self.debug:
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
                    if self.debug:
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
            if not self.is_relevant_content(title):
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
            text = self.clean_text(text)
            
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
            
            article_data = SentimentData(
                text=text,
                source="Yahoo Finance",
                timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
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
                        print(f"      Failed to enhance Yahoo article: {e}")
            
            return article_data
            
        except Exception as e:
            if self.debug:
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
                    
                    cleaned_text = self.clean_text(text)
                    sentiment = self._analyze_text(cleaned_text)
                    
                    article_data = SentimentData(
                        text=cleaned_text,
                        source="Yahoo Finance",
                        timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
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
                                print(f"        Failed to enhance text-based article: {e}")
                    
                    articles_data.append(article_data)
                    
                except Exception:
                    continue
        
        except Exception as e:
            if self.debug:
                print(f"    Text-based search failed: {e}")
        
        return articles_data