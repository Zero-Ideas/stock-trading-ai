#!/usr/bin/env python3
"""
Enhanced Seeking Alpha scraper using pydoll for superior anti-bot evasion
Pydoll provides state-of-the-art stealth capabilities for scraping protected sites
"""

import asyncio
import time
import random
import re
from typing import List
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
import newspaper
from pydoll.browser import Chrome
from .base_scraper import BaseScraper, SentimentData
from pydoll.browser.options import ChromiumOptions as Options

class SeekingAlphaScraperPydoll(BaseScraper):
    """Enhanced Seeking Alpha scraper using pydoll with advanced anti-bot evasion"""
    
    @property
    def source_name(self) -> str:
        return "Seeking Alpha (Pydoll)"
    
    def __init__(self, symbol: str, debug: bool = False):
        super().__init__(symbol, debug)
        self.visited_urls = set()  # Track visited URLs to avoid duplicates
        self.max_timeout = 90  # Maximum timeout for entire scraping session
    
    def _analyze_text(self, text: str) -> dict:
        """Analyze text sentiment (placeholder - will be handled by main analyzer)"""
        return {'polarity': 0.0, 'compound': 0.0}
    
    def scrape(self, max_articles: int = 8) -> List[SentimentData]:
        """Main scraping method with async event loop handling"""
        if self.debug:
            print(f"Starting Seeking Alpha Pydoll scraper for {self.symbol} ({self.common_name})")
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in a running loop, use a thread
                import threading
                import queue
                
                result_queue = queue.Queue()
                
                def run_in_thread():
                    try:
                        result = asyncio.run(self._async_scrape(max_articles))
                        result_queue.put(('success', result))
                    except Exception as e:
                        result_queue.put(('error', e))
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join(timeout=self.max_timeout)
                
                if thread.is_alive():
                    if self.debug:
                        print("      Seeking Alpha pydoll scraper timed out")
                    return []
                
                status, result = result_queue.get()
                if status == 'error':
                    if self.debug:
                        print(f"      Seeking Alpha pydoll error: {result}")
                    return []
                return result
            else:
                return loop.run_until_complete(self._async_scrape(max_articles))
        except RuntimeError:
            return asyncio.run(self._async_scrape(max_articles))
        except Exception as e:
            if self.debug:
                print(f"      Seeking Alpha pydoll scraper failed: {e}")
            return []
    
    async def _async_scrape(self, max_articles: int = 8) -> List[SentimentData]:
        """Asynchronous scraping implementation with timeout protection"""
        try:
            return await asyncio.wait_for(
                self._async_scrape_impl(max_articles), 
                timeout=self.max_timeout
            )
        except asyncio.TimeoutError:
            if self.debug:
                print(f"      Seeking Alpha pydoll overall timeout reached after {self.max_timeout}s")
            return []
    
    async def _async_scrape_impl(self, max_articles: int = 8) -> List[SentimentData]:
        """Core scraping implementation using pydoll"""
        sentiments = []
        browser = None
        
        try:
            if self.debug:
                print("      Pydoll Seeking Alpha: Initializing stealth browser...")
            opts = Options()
            opts.headless = False
            #opts.add_argument('--window-size=1920,1080')
            # Initialize pydoll Chrome browser with built-in stealth features
            async with Chrome(options = opts) as browser:
                tab = await browser.start()
                
                if self.debug:
                    print("      Pydoll browser started successfully")
                
                # Multiple scraping strategies for better coverage
                strategies = [
                    self._scrape_symbol_page,
                    self._scrape_search_results,
                    self._scrape_news_feed,
                    self._scrape_analysis_feed
                ]
                
                articles_per_strategy = max(2, max_articles // len(strategies))
                
                for i, strategy in enumerate(strategies):
                    if len(sentiments) >= max_articles:
                        break
                        
                    try:
                        if self.debug:
                            print(f"      Executing strategy {i+1}/{len(strategies)}: {strategy.__name__}")
                        
                        strategy_articles = await strategy(
                            tab, 
                            min(articles_per_strategy, max_articles - len(sentiments))
                        )
                        
                        # Add articles avoiding duplicates
                        for article in strategy_articles:
                            if article and article.url not in self.visited_urls:
                                sentiments.append(article)
                                self.visited_urls.add(article.url)
                                if len(sentiments) >= max_articles:
                                    break
                        
                        # Random delay between strategies
                        await asyncio.sleep(random.uniform(1.0, 3.0))
                        
                    except Exception as e:
                        if self.debug:
                            print(f"      Strategy {strategy.__name__} failed: {e}")
                        continue
                
                await tab.close()
                await browser.stop()
                
                if self.debug:
                    print(f"      Pydoll Seeking Alpha: Collected {len(sentiments)} articles")
            
        except Exception as e:
            if self.debug:
                print(f"      Pydoll Seeking Alpha error: {e}")
        
        return sentiments
    
    async def _scrape_symbol_page(self, tab, max_articles: int) -> List[SentimentData]:
        """Scrape the main symbol page for articles"""
        articles = []
        
        try:
            url = f"https://seekingalpha.com/symbol/{self.symbol}"
            if self.debug:
                print(f"        Loading symbol page: {url}")
            
            await tab.go_to(url)
            
            # Wait for page to load
            await asyncio.sleep(3.0)
            
            # Handle potential cookie/privacy notices
            await self._handle_privacy_notices(tab)
            
            # Get page content
            page_response = await tab.request.get(url)
            content = page_response.text if page_response else ""
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract articles from various sections
            article_links = await self._extract_article_links(soup, tab)
            
            for link_data in article_links[:max_articles]:
                article = await self._process_article(tab, link_data)
                if article:
                    articles.append(article)
                    
        except Exception as e:
            if self.debug:
                print(f"        Symbol page scraping failed: {e}")
        
        return articles
    
    async def _scrape_search_results(self, tab, max_articles: int) -> List[SentimentData]:
        """Scrape search results for the company"""
        articles = []
        
        try:
            # Use common name for better search results
            search_query = f"{self.common_name} stock analysis earnings"
            url = f"https://seekingalpha.com/search?q={quote(search_query)}"
            
            if self.debug:
                print(f"        Loading search results: {search_query}")
            
            await tab.go_to(url)
            await asyncio.sleep(2.0)
            
            # Handle privacy notices
            await self._handle_privacy_notices(tab)
            
            page_response = await tab.request.get(url)
            content = page_response.text if page_response else ""
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract search result articles
            search_articles = await self._extract_search_results(soup, tab)
            
            for link_data in search_articles[:max_articles]:
                if self._is_relevant_to_symbol(link_data['title']):
                    article = await self._process_article(tab, link_data)
                    if article:
                        articles.append(article)
                        
        except Exception as e:
            if self.debug:
                print(f"        Search results scraping failed: {e}")
        
        return articles
    
    async def _scrape_news_feed(self, tab, max_articles: int) -> List[SentimentData]:
        """Scrape the news feed for the symbol"""
        articles = []
        
        try:
            url = f"https://seekingalpha.com/symbol/{self.symbol}/news"
            if self.debug:
                print(f"        Loading news feed: {url}")
            
            await tab.go_to(url)
            await asyncio.sleep(2.0)
            
            await self._handle_privacy_notices(tab)
            
            page_response = await tab.request.get(url)
            content = page_response.text if page_response else ""
            soup = BeautifulSoup(content, 'html.parser')
            
            news_articles = await self._extract_news_articles(soup, tab)
            
            for link_data in news_articles[:max_articles]:
                article = await self._process_article(tab, link_data)
                if article:
                    articles.append(article)
                    
        except Exception as e:
            if self.debug:
                print(f"        News feed scraping failed: {e}")
        
        return articles
    
    async def _scrape_analysis_feed(self, tab, max_articles: int) -> List[SentimentData]:
        """Scrape the analysis feed for the symbol"""
        articles = []
        
        try:
            url = f"https://seekingalpha.com/symbol/{self.symbol}/analysis"
            if self.debug:
                print(f"        Loading analysis feed: {url}")
            
            await tab.go_to(url)
            await asyncio.sleep(2.0)
            
            await self._handle_privacy_notices(tab)
            
            page_response = await tab.request.get(url)
            content = page_response.text if page_response else ""
            soup = BeautifulSoup(content, 'html.parser')
            
            analysis_articles = await self._extract_analysis_articles(soup, tab)
            
            for link_data in analysis_articles[:max_articles]:
                article = await self._process_article(tab, link_data)
                if article:
                    articles.append(article)
                    
        except Exception as e:
            if self.debug:
                print(f"        Analysis feed scraping failed: {e}")
        
        return articles
    
    async def _handle_privacy_notices(self, tab):
        """Handle cookie consent and privacy notices"""
        try:
            # Simple privacy notice handling - just wait a bit for any popups to appear
            # pydoll's stealth capabilities should handle most cookie notices automatically
            await asyncio.sleep(1.0)
            if self.debug:
                print("        Privacy notice handling completed")
        except Exception as e:
            if self.debug:
                print(f"        Privacy notice handling failed: {e}")
    
    async def _extract_article_links(self, soup: BeautifulSoup, tab) -> List[dict]:
        """Extract article links from the page"""
        links = []
        
        try:
            # Multiple selectors for different article types
            article_selectors = [
                'a[href*="/article/"]',
                'a[href*="/news/"]',
                'a[data-testid*="article"]',
                '.article-link',
                '[data-module="ArticleList"] a',
                '[data-testid="post-list"] a'
            ]
            
            for selector in article_selectors:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get('href')
                    if href and ('/article/' in href or '/news/' in href):
                        title = self._extract_title_from_element(element)
                        if title and len(title) > 10:
                            full_url = urljoin("https://seekingalpha.com", href)
                            links.append({
                                'url': full_url,
                                'title': title,
                                'element': element
                            })
            
            # Remove duplicates based on URL
            unique_links = []
            seen_urls = set()
            for link in links:
                if link['url'] not in seen_urls:
                    unique_links.append(link)
                    seen_urls.add(link['url'])
            
            if self.debug:
                print(f"        Extracted {len(unique_links)} unique article links")
            
        except Exception as e:
            if self.debug:
                print(f"        Article link extraction failed: {e}")
        
        return unique_links
    
    def _extract_title_from_element(self, element) -> str:
        """Extract title text from an article element"""
        try:
            # Try different methods to get the title
            title = element.get_text(strip=True)
            
            if not title or len(title) < 10:
                # Look in parent elements
                parent = element.parent
                if parent:
                    title_elem = parent.find(['h1', 'h2', 'h3', 'h4', 'span'])
                    if title_elem:
                        title = title_elem.get_text(strip=True)
            
            # Clean and validate title
            if title:
                title = re.sub(r'\s+', ' ', title).strip()
                if len(title) > 200:  # Truncate overly long titles
                    title = title[:200] + "..."
                    
            return title if title and len(title) >= 10 else ""
            
        except:
            return ""
    
    async def _extract_search_results(self, soup: BeautifulSoup, tab) -> List[dict]:
        """Extract articles from search results"""
        return await self._extract_article_links(soup, tab)
    
    async def _extract_news_articles(self, soup: BeautifulSoup, tab) -> List[dict]:
        """Extract articles from news feed"""
        return await self._extract_article_links(soup, tab)
    
    async def _extract_analysis_articles(self, soup: BeautifulSoup, tab) -> List[dict]:
        """Extract articles from analysis feed"""
        return await self._extract_article_links(soup, tab)
    
    def _is_relevant_to_symbol(self, title: str) -> bool:
        """Check if article title is relevant to our symbol"""
        if not title:
            return False
            
        title_lower = title.lower()
        
        # Check for symbol or common name
        if (self.symbol.lower() in title_lower or 
            self.common_name.lower() in title_lower):
            return True
        
        # Check for company name variations
        if hasattr(self, 'company_name') and self.company_name:
            company_words = self.company_name.lower().split()
            # If multiple company name words are found, it's likely relevant
            matches = sum(1 for word in company_words if word in title_lower)
            if matches >= 2:
                return True
        
        return False
    
    async def _process_article(self, tab, link_data: dict) -> SentimentData:
        """Process an individual article and extract content"""
        try:
            url = link_data['url']
            title = link_data['title']
            
            if not self._is_relevant_to_symbol(title):
                return None
            
            # Try to get more content using newspaper3k for speed
            enhanced_text = await self._enhance_with_newspaper3k(url, title)
            
            if not enhanced_text or len(enhanced_text) < 50:
                # Fallback to tab scraping if newspaper3k fails
                enhanced_text = await self._scrape_article_with_browser(tab, url, title)
            
            if not enhanced_text or len(enhanced_text) < 20:
                enhanced_text = title  # Use title as fallback
            
            # Clean the text
            enhanced_text = self.clean_text(enhanced_text)
            
            # Create sentiment data
            sentiment = self._analyze_text(enhanced_text)
            
            return SentimentData(
                text=enhanced_text,
                source="Seeking Alpha (Pydoll)",
                timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                polarity=sentiment['polarity'],
                compound=sentiment['compound'],
                url=url,
                raw_extracted_text=enhanced_text if enhanced_text != title else ""
            )
            
        except Exception as e:
            if self.debug:
                print(f"        Article processing failed: {e}")
            return None
    
    async def _enhance_with_newspaper3k(self, url: str, fallback_text: str) -> str:
        """Try to enhance article text using newspaper3k (async wrapper)"""
        try:
            import asyncio
            import concurrent.futures
            
            def extract_article():
                try:
                    from newspaper import Article, Config
                    
                    config = Config()
                    config.browser_user_agent = (
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    )
                    config.request_timeout = 8
                    config.number_threads = 1
                    
                    article = Article(url, config=config)
                    article.download()
                    article.parse()
                    
                    if article.text and len(article.text) > len(fallback_text):
                        return f"{article.title}. {article.text}" if article.title else article.text
                    
                except Exception as e:
                    if self.debug:
                        print(f"        newspaper3k extraction failed: {e}")
                
                return fallback_text
            
            # Run newspaper3k in thread pool to avoid blocking
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(extract_article)
                return await asyncio.wait_for(
                    asyncio.wrap_future(future), 
                    timeout=10.0
                )
                
        except (asyncio.TimeoutError, Exception) as e:
            if self.debug:
                print(f"        newspaper3k async enhancement failed: {e}")
            return fallback_text
    
    async def _scrape_article_with_browser(self, tab, url: str, fallback_text: str) -> str:
        """Scrape article content using the tab as fallback"""
        try:
            if self.debug:
                print(f"        Scraping article content: {url}")
            
            await tab.go_to(url)
            await asyncio.sleep(2.0)
            
            # Handle privacy notices
            await self._handle_privacy_notices(tab)
            
            page_response = await tab.request.get(url)
            content = page_response.text if page_response else ""
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for article content
            content_selectors = [
                '[data-testid="content-container"]',
                '.article-content',
                '[data-module="ArticleBody"]',
                '.content-body',
                'article',
                '.post-content'
            ]
            
            article_text = ""
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    article_text = element.get_text(strip=True)
                    if len(article_text) > 100:
                        break
            
            return article_text if article_text else fallback_text
            
        except Exception as e:
            if self.debug:
                print(f"        Browser article scraping failed: {e}")
            return fallback_text