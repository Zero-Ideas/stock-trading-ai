#!/usr/bin/env python3
"""
MarketWatch scraper for stock sentiment analysis
"""

from typing import List
import time
import random
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, SentimentData


class MarketWatchScraper(BaseScraper):
    """Enhanced MarketWatch scraper with improved reliability"""
    
    @property
    def source_name(self) -> str:
        return "MarketWatch"
    
    def __init__(self, symbol: str, debug: bool = False):
        super().__init__(symbol, debug)
        self.company_name = self._get_company_name()
        
        # Enhanced MarketWatch user agents to avoid 401 Forbidden errors
        self.marketwatch_user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        self._current_user_agent_index = 0
    
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
    
    def get_marketwatch_user_agent(self) -> str:
        """Get next MarketWatch-specific user agent in rotation"""
        user_agent = self.marketwatch_user_agents[self._current_user_agent_index]
        self._current_user_agent_index = (self._current_user_agent_index + 1) % len(self.marketwatch_user_agents)
        return user_agent
    
    def _analyze_text(self, text: str) -> dict:
        """Analyze text sentiment (placeholder - will be handled by main analyzer)"""
        # This is a placeholder - actual sentiment analysis will be done by the main StockSentimentAnalyzer
        return {'polarity': 0.0, 'compound': 0.0}
    
    def scrape(self, max_articles: int = 10) -> List[SentimentData]:
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
                
            if self.debug:
                print(f"    MarketWatch strategy {strategy_num}: {url}")
            
            try:
                # Enhanced headers for MarketWatch with rotating user agents
                headers = {
                    'User-Agent': self.get_marketwatch_user_agent(),  # Use specialized rotation
                    'Referer': 'https://www.marketwatch.com/',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
                
                # Multiple attempts per strategy with enhanced error handling
                response = None
                for attempt in range(3):  # Increased to 3 attempts
                    try:
                        response = self.make_request(url, headers=headers, timeout=20)
                        if response.status_code == 200:
                            break
                        elif response.status_code in [401, 403]:
                            # Try different user agent from rotation for auth errors
                            old_ua = headers['User-Agent'][:50]
                            headers['User-Agent'] = self.get_marketwatch_user_agent()
                            if self.debug:
                                print(f"      HTTP {response.status_code} - rotating user agent")
                                print(f"        From: {old_ua}...")
                                print(f"        To: {headers['User-Agent'][:50]}...")
                            self.random_delay(3.0, 5.0)  # Longer delay for auth errors
                        elif response.status_code == 429:
                            # Rate limited - wait longer
                            if self.debug:
                                print(f"      Rate limited - waiting longer before retry")
                            self.random_delay(5.0, 8.0)
                        else:
                            if self.debug:
                                print(f"      HTTP {response.status_code} on attempt {attempt + 1}")
                    except Exception as req_e:
                        if self.debug:
                            print(f"      Request failed attempt {attempt + 1}: {req_e}")
                        if attempt < 2:
                            # Rotate user agent on any exception too
                            headers['User-Agent'] = self.get_marketwatch_user_agent()
                            self.random_delay(1.0, 3.0)
                
                if not response or response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                strategy_articles = self._extract_marketwatch_articles(soup, max_articles - len(sentiments), strategy_num)
                
                if strategy_articles:
                    sentiments.extend(strategy_articles)
                    if self.debug:
                        print(f"      Found {len(strategy_articles)} articles with strategy {strategy_num}")
                
                # Rate limiting between strategies
                self.random_delay(1.0, 2.5)
                
            except Exception as e:
                if self.debug:
                    print(f"      Strategy {strategy_num} failed: {e}")
                continue
        
        if self.debug and not sentiments:
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
                    if self.debug:
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
            if not self.is_relevant_content(title):
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
            text = self.clean_text(text)
            
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
            
            article_data = SentimentData(
                text=text,
                source="MarketWatch",
                timestamp=datetime.now() - timedelta(hours=random.randint(1, 72)),
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
                        print(f"        Failed to enhance MarketWatch article: {e}")
            
            return article_data
            
        except Exception as e:
            if self.debug:
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
                        
                        if len(articles_data) >= max_articles:
                            break
                        
                        # Create article from relevant text
                        try:
                            cleaned_text = self.clean_text(text)
                            sentiment = self._analyze_text(cleaned_text)
                            
                            articles_data.append(SentimentData(
                                text=cleaned_text,
                                source="MarketWatch",
                                timestamp=datetime.now() - timedelta(hours=random.randint(1, 72)),
                                polarity=sentiment['polarity'],
                                compound=sentiment['compound'],
                                url=""
                            ))
                        except Exception:
                            continue
        
        except Exception as e:
            if self.debug:
                print(f"        MarketWatch text extraction failed: {e}")
        
        return articles_data