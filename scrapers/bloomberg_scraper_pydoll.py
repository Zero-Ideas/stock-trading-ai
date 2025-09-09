#!/usr/bin/env python3
"""
Bloomberg scraper using pydoll for enhanced bot evasion
"""

import asyncio
import time
import random
from typing import List
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
import newspaper
from pydoll.browser import Chrome
from .base_scraper import BaseScraper, SentimentData


class BloombergScraperPydoll(BaseScraper):
    """Bloomberg scraper using pydoll with enhanced bot evasion"""
    
    @property
    def source_name(self) -> str:
        return "Bloomberg (Pydoll)"
    
    def _analyze_text(self, text: str) -> dict:
        """Analyze text sentiment (placeholder - will be handled by main analyzer)"""
        return {'polarity': 0.0, 'compound': 0.0}
    
    def scrape(self, max_articles: int = 10) -> List[SentimentData]:
        """Scrape Bloomberg using pydoll for better bot evasion"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in a running loop, we need to use a thread
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
                thread.join(timeout=120)  # Add timeout to prevent hanging
                
                if thread.is_alive():
                    if self.debug:
                        print("Bloomberg pydoll scraper timed out, returning empty results")
                    return []
                
                status, result = result_queue.get()
                if status == 'error':
                    raise result
                return result
            else:
                return loop.run_until_complete(self._async_scrape(max_articles))
        except RuntimeError:
            return asyncio.run(self._async_scrape(max_articles))
    
    async def _async_scrape(self, max_articles: int = 10) -> List[SentimentData]:
        """Asynchronous scraping implementation with timeout protection"""
        sentiments = []
        
        # Add overall timeout to prevent infinite hanging (shorter for small requests)
        timeout_seconds = 60.0 if max_articles <= 10 else 180.0
        try:
            if self.debug:
                print(f"Starting Bloomberg pydoll scraper with {timeout_seconds}s timeout for {max_articles} articles")
            return await asyncio.wait_for(self._async_scrape_impl(max_articles), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            if self.debug:
                print(f"Bloomberg pydoll scraper overall timeout reached after {timeout_seconds}s, returning partial results")
            return sentiments
    
    async def _async_scrape_impl(self, max_articles: int = 10) -> List[SentimentData]:
        """Internal scraping implementation"""
        sentiments = []
        
        try:
            if self.debug:
                print("      Pydoll Bloomberg: Initializing URL strategies...")
                
            # Bloomberg URL strategies optimized for pydoll
            url_strategies = [
                f"https://www.bloomberg.com/search?query={quote(self.symbol)}",
                #f"https://www.bloomberg.com/quote/{self.symbol}:US",
                #f"https://www.bloomberg.com/technology",
                #f"https://www.bloomberg.com/markets/stocks",
                #f"https://www.bloomberg.com/news",
                #f"https://www.bloomberg.com/search?query={quote(self.symbol)}%20stock",
                #f"https://www.bloomberg.com/search?query={quote(self.symbol)}%20earnings"
            ]
            
            # Add overall timeout for the entire scraping process
            try:
                if self.debug:
                    print("      Pydoll Bloomberg: Starting Chrome browser...")
                async with Chrome() as browser:
                    tab = await browser.start()
                    
                    for i, url in enumerate(url_strategies):
                        if len(sentiments) >= max_articles:
                            break
                        
                        try:
                            if self.debug:
                                print(f"      Pydoll Bloomberg: Fetching {url}")
                            
                            # Navigate to URL
                            await tab.go_to(url)
                            browser.clic
                            # Wait for page to fully load with proper timeout
                            current_url = None
                            last_url = ""
                            max_wait_attempts = 20  # Max 10 seconds wait
                            for attempt in range(max_wait_attempts):
                                try:
                                    current_url = await asyncio.wait_for(tab.current_url, timeout=2.0)
                                    if current_url == last_url and current_url != "":
                                        break
                                    last_url = current_url
                                    await asyncio.sleep(0.5)
                                except asyncio.TimeoutError:
                                    if self.debug:
                                        print(f"        Timeout getting URL on attempt {attempt + 1}, skipping...")
                                    break
                            
                            # Get page content using pydoll's enhanced method with timeout
                            try:
                                contents = await asyncio.wait_for(tab.request.get(current_url), timeout=30.0)
                            except asyncio.TimeoutError:
                                if self.debug:
                                    print(f"        Request timeout for {url}, skipping...")
                                continue
                            
                            if contents and contents.text:
                                # Parse with BeautifulSoup
                                soup = BeautifulSoup(contents.text, 'html.parser')
                                
                                # Extract articles using enhanced selectors
                                articles = self._extract_articles_from_soup(soup, url)
                                
                                # Process articles with newspaper3k for better content extraction
                                strategy_articles = await self._process_articles_with_newspaper(
                                    articles, max_articles - len(sentiments), tab
                                )
                                
                                if strategy_articles:
                                    sentiments.extend(strategy_articles)
                                    if self.debug:
                                        print(f"      Pydoll Bloomberg: Found {len(strategy_articles)} articles from {url}")
                        
                            # Rate limiting between requests
                            await asyncio.sleep(random.uniform(1.0, 2.0))  # Reduced delay
                            
                            # Early exit if we have enough articles for efficiency
                            if len(sentiments) >= max_articles:
                                if self.debug:
                                    print(f"      Pydoll Bloomberg: Reached target, stopping at URL {i+1}/{len(url_strategies)}")
                                break
                            
                        except Exception as e:
                            if self.debug:
                                print(f"      Pydoll Bloomberg error for {url}: {e}")
                            continue
                
                    await tab.close()
                    await browser.stop()
            except Exception as browser_error:
                if self.debug:
                    print(f"Browser error: {browser_error}")
                # Continue to return whatever we got
        
        except Exception as e:
            if self.debug:
                print(f"Pydoll Bloomberg scraping error: {e}")
        
        return sentiments
    
    def _extract_articles_from_soup(self, soup: BeautifulSoup, url: str) -> List:
        """Extract article elements from parsed HTML"""
        articles = []
        selectors = []
        # Determine strategy based on URL
        if "/search?" in url:
            # Search results page selectors
            selectors = [
                'div[data-module="SearchStory"]',
                'div[data-component="search-result"]',
                'article[data-module="story"]',
                'div.search-result',
                'a[class*="SearchResult_storyLink"]',
                'main[role="main"] > div > div'
            ]
        elif "/quote/" in url:
            # Quote page selectors
            selectors = [
                'div[data-module="RelatedStories"]',
                'div[data-module="News"]',
                'article',
                'div.story-package-module__story',
                'article[role="article"]'
            ]
        else:
            # News section page selectors
            selectors = [
                'article',
                'div[role="main"] article',
                'main article',
                'div[class*="story"]',
                'div[class*="article"]',
                'a[href*="/news/articles/"]',
                'div:has(time)'
            ]
        
        # Try each selector and collect articles
        for selector in selectors:
            print(f"      Pydoll Bloomberg: Trying selector {selector}")
            try:
                found = soup.select(selector)
                if found:
                    articles.extend(found[:20])  # Limit per selector
            except Exception as e:
                if self.debug:
                    print(f"        Selector {selector} failed: {e}")
                continue
        
        # Remove duplicates
        return self._deduplicate_articles(articles)
    
    def _deduplicate_articles(self, articles) -> list:
        """Remove duplicate articles based on URLs and titles"""
        seen_urls = set()
        seen_titles = set()
        unique_articles = []
        
        for article in articles:
            # Extract URL
            url = ""
            link_elem = article.find('a')
            if link_elem and link_elem.get('href'):
                url = link_elem.get('href')
            elif article.name == 'a' and article.get('href'):
                url = article.get('href')
            
            # Extract title
            title = ""
            if article.name == 'a':
                title = article.get_text(strip=True)
            else:
                for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    title_elem = article.find(tag)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break
                
                if not title:
                    link_elem = article.find('a')
                    if link_elem:
                        title = link_elem.get_text(strip=True)
            
            # Skip duplicates
            if url and url in seen_urls:
                continue
            if title and title in seen_titles:
                continue
            
            if url:
                seen_urls.add(url)
            if title:
                seen_titles.add(title)
            
            unique_articles.append(article)
        
        return unique_articles
    
    async def _process_articles_with_newspaper(
        self, 
        articles: List, 
        max_needed: int, 
        tab
    ) -> List[SentimentData]:
        """Process articles using newspaper3k for enhanced content extraction"""
        processed_articles = []
        
        for i, article_elem in enumerate(articles[:max_needed]):
            try:
                # Early exit if we have enough articles
                if len(processed_articles) >= max_needed:
                    if self.debug:
                        print(f"        Reached target articles, stopping processing at {i+1}/{len(articles[:max_needed])}")
                    break
                # Extract title
                title = self._extract_title(article_elem)
                if not title or len(title) < 10:
                    continue
                
                # Extract URL
                url = self._extract_url(article_elem)
                
                # Extract summary from current page
                summary = self._extract_summary(article_elem)
                
                # If we have a full URL, try to get the full article content using pydoll (with timeout)
                full_text = ""
                if url and url.startswith('http'):
                    try:
                        # Add timeout for individual article content fetching
                        full_text = await asyncio.wait_for(
                            self._get_full_article_content(tab, url), 
                            timeout=20.0
                        )
                    except asyncio.TimeoutError:
                        if self.debug:
                            print(f"        Full content fetch timeout for {url}, using summary only")
                    except Exception as e:
                        if self.debug:
                            print(f"        Failed to get full content for {url}: {e}")
                
                # Combine title, summary, and full text
                if full_text:
                    text = f"{title}. {summary}. {full_text[:1000]}"  # Limit full text
                else:
                    text = f"{title}. {summary}" if summary else title
                
                text = self.clean_text(text)
                
                # Check relevance
                if not self.is_relevant_content(text):
                    continue
                
                # Create sentiment data
                sentiment = self._analyze_text(text)
                article_data = SentimentData(
                    text=text,
                    source="Bloomberg (Pydoll)",
                    timestamp=datetime.now() - timedelta(hours=random.randint(1, 24)),
                    polarity=sentiment['polarity'],
                    compound=sentiment['compound'],
                    url=url,
                    raw_extracted_text=full_text if full_text else text
                )
                
                processed_articles.append(article_data)
                
            except Exception as e:
                if self.debug:
                    print(f"        Error processing article: {e}")
                continue
        
        return processed_articles
    
    def _extract_title(self, article_elem) -> str:
        """Extract title from article element"""
        title_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a[data-module="headline"]', 'a']
        
        for selector in title_selectors:
            title_elem = article_elem.find(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 10:
                    return title
        
        # Fallback: if article is a link itself
        if article_elem.name == 'a':
            return article_elem.get_text(strip=True)
        
        return ""
    
    def _extract_url(self, article_elem) -> str:
        """Extract URL from article element"""
        link_elem = article_elem.find('a')
        if link_elem and link_elem.get('href'):
            href = link_elem.get('href')
            if href.startswith('/'):
                return f"https://www.bloomberg.com{href}"
            elif href.startswith('http'):
                return href
        elif article_elem.name == 'a' and article_elem.get('href'):
            href = article_elem.get('href')
            if href.startswith('/'):
                return f"https://www.bloomberg.com{href}"
            elif href.startswith('http'):
                return href
        return ""
    
    def _extract_summary(self, article_elem) -> str:
        """Extract summary from article element"""
        summary_selectors = [
            'p[data-module="summary"]',
            'div[data-module="abstract"]',
            'p',
            'div.abstract',
            'div.summary'
        ]
        
        for selector in summary_selectors:
            summary_elem = article_elem.find(selector)
            if summary_elem:
                summary_text = summary_elem.get_text(strip=True)
                if summary_text and len(summary_text) > 20:
                    return summary_text[:300]  # Limit length
        
        return ""
    
    async def _get_full_article_content(self, tab, url: str) -> str:
        """Get full article content using pydoll and newspaper3k"""
        try:
            # Navigate to article URL
            await tab.go_to(url)
            
            # Wait for page to load with timeout
            current_url = None
            last_url = ""
            max_wait_attempts = 10  # Max 5 seconds wait
            for attempt in range(max_wait_attempts):
                try:
                    current_url = await asyncio.wait_for(tab.current_url, timeout=2.0)
                    if current_url == last_url and current_url != "":
                        break
                    last_url = current_url
                    await asyncio.sleep(0.5)
                except asyncio.TimeoutError:
                    if self.debug:
                        print(f"        Timeout getting article URL on attempt {attempt + 1}, giving up")
                    return ""
            
            # Get page content with timeout
            try:
                contents = await asyncio.wait_for(tab.request.get(current_url), timeout=20.0)
            except asyncio.TimeoutError:
                if self.debug:
                    print(f"        Request timeout for article {url}, skipping...")
                return ""
            
            if contents and contents.text:
                # Use newspaper3k to extract clean article text
                article = newspaper.Article('')
                article.set_html(contents.text)
                article.parse()
                
                return article.text if article.text else ""
        
        except Exception as e:
            if self.debug:
                print(f"        Error getting full article content: {e}")
        
        return ""