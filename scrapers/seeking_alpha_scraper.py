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
        """Enhanced Seeking Alpha scraper using Selenium to handle JavaScript and extract Analysis/News sections"""
        sentiments = []
        
        try:
            # Primary strategy: Use Selenium to load the main symbol page and extract articles
            symbol_url = f"https://seekingalpha.com/symbol/{self.symbol}"
            selenium_articles = self._scrape_with_selenium(symbol_url, max_articles)
            sentiments.extend(selenium_articles)
            
            # If we got some articles but not enough, try fallback methods
            if len(sentiments) < max_articles:
                remaining = max_articles - len(sentiments)
                fallback_articles = self._scrape_fallback_methods(remaining)
                sentiments.extend(fallback_articles)
            
        except Exception as e:
            if self.debug:
                print(f"Seeking Alpha scraping error: {e}")
        
        return sentiments[:max_articles]
    
    def _scrape_with_selenium(self, url: str, max_articles: int) -> List[SentimentData]:
        """Use Selenium to scrape the JavaScript-rendered page and find Analysis/News sections"""
        sentiments = []
        
        try:
            # Track URL resolution attempt
            self.track_url_resolution_attempt(self.source_name)
            
            if self.debug:
                print(f"      Seeking Alpha: Using Selenium to load {url}")
            
            # Use Selenium to load the page and wait for content
            page_source, final_url = self.make_request_with_selenium(
                url, 
                wait_for_selector="body", 
                wait_timeout=10
            )
            
            if not page_source:
                if self.debug:
                    print(f"      Seeking Alpha: Selenium failed to load page")
                return sentiments
            
            # Track successful resolution
            self.track_url_resolution_success(self.source_name)
            
            # Parse the rendered content
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Strategy 1: Look for sections that contain "Analysis" or "News" with the symbol
            if self.debug:
                print(f"      Seeking Alpha: Looking for {self.symbol} Analysis and News sections...")
            
            # Find Analysis and News sections
            analysis_articles = self._extract_analysis_section(soup, max_articles // 2)
            news_articles = self._extract_news_section(soup, max_articles // 2)
            
            sentiments.extend(analysis_articles)
            sentiments.extend(news_articles)
            
            # If we didn't find enough from sections, look for general article links
            if len(sentiments) < max_articles:
                general_articles = self._extract_general_articles(soup, max_articles - len(sentiments))
                sentiments.extend(general_articles)
            
            if self.debug:
                analysis_count = len(analysis_articles)
                news_count = len(news_articles)
                general_count = len(sentiments) - analysis_count - news_count
                print(f"      Seeking Alpha: Found {analysis_count} analysis, {news_count} news, {general_count} general articles")
            
        except Exception as e:
            if self.debug:
                print(f"      Seeking Alpha: Selenium scraping failed: {e}")
        
        return sentiments
    
    def _extract_analysis_section(self, soup: BeautifulSoup, max_articles: int) -> List[SentimentData]:
        """Extract articles from the Analysis section"""
        articles = []
        
        try:
            # Look for sections/headers that mention Analysis
            analysis_selectors = [
                f'*[data-testid*="analysis"]',
                f'section:has(*:contains("{self.symbol} Analysis"))',
                f'div:has(h2:contains("Analysis"))',
                f'div:has(h3:contains("Analysis"))',
                f'*:contains("{self.symbol} Analysis")',
                f'*:contains("Analysis")'
            ]
            
            for selector in analysis_selectors:
                try:
                    sections = soup.select(selector)
                    for section in sections:
                        # Look for article links within this section
                        links = section.find_all('a', href=lambda x: x and '/article/' in x)
                        for link in links[:max_articles]:
                            article = self._process_article_link(link, "Analysis")
                            if article:
                                articles.append(article)
                                if len(articles) >= max_articles:
                                    return articles
                except:
                    continue
            
            # If no specific analysis section found, look for analysis article links directly
            if not articles:
                analysis_links = soup.find_all('a', href=lambda x: x and '/article/' in x and 'analysis' in x.lower())
                for link in analysis_links[:max_articles]:
                    article = self._process_article_link(link, "Analysis")
                    if article:
                        articles.append(article)
                        if len(articles) >= max_articles:
                            break
            
        except Exception as e:
            if self.debug:
                print(f"      Analysis section extraction error: {e}")
        
        return articles
    
    def _extract_news_section(self, soup: BeautifulSoup, max_articles: int) -> List[SentimentData]:
        """Extract articles from the News section"""
        articles = []
        
        try:
            # Look for sections/headers that mention News
            news_selectors = [
                f'*[data-testid*="news"]',
                f'section:has(*:contains("{self.symbol} News"))',
                f'div:has(h2:contains("News"))',
                f'div:has(h3:contains("News"))',
                f'*:contains("{self.symbol} News")',
                f'*:contains("News")'
            ]
            
            for selector in news_selectors:
                try:
                    sections = soup.select(selector)
                    for section in sections:
                        # Look for article links within this section
                        links = section.find_all('a', href=lambda x: x and ('/news/' in x or '/article/' in x))
                        for link in links[:max_articles]:
                            article = self._process_article_link(link, "News")
                            if article:
                                articles.append(article)
                                if len(articles) >= max_articles:
                                    return articles
                except:
                    continue
            
            # If no specific news section found, look for news article links directly
            if not articles:
                news_links = soup.find_all('a', href=lambda x: x and '/news/' in x)
                for link in news_links[:max_articles]:
                    article = self._process_article_link(link, "News")
                    if article:
                        articles.append(article)
                        if len(articles) >= max_articles:
                            break
            
        except Exception as e:
            if self.debug:
                print(f"      News section extraction error: {e}")
        
        return articles
    
    def _extract_general_articles(self, soup: BeautifulSoup, max_articles: int) -> List[SentimentData]:
        """Extract general articles from any links found on the page"""
        articles = []
        
        try:
            # Look for any article/news links on the page
            all_article_links = soup.find_all('a', href=lambda x: x and ('/article/' in x or '/news/' in x))
            
            for link in all_article_links[:max_articles * 2]:  # Get more candidates to filter
                article = self._process_article_link(link, "General")
                if article and len(articles) < max_articles:
                    articles.append(article)
                    if len(articles) >= max_articles:
                        break
            
        except Exception as e:
            if self.debug:
                print(f"      General articles extraction error: {e}")
        
        return articles
    
    def _process_article_link(self, link, section_type: str) -> SentimentData:
        """Process an individual article link and extract content"""
        try:
            href = link.get('href', '')
            if not href:
                return None
            
            # Ensure full URL
            if href.startswith('/'):
                href = f"https://seekingalpha.com{href}"
            elif not href.startswith('http'):
                return None
            
            # Get article title
            title = link.get_text(strip=True)
            if not title or len(title) < 10:
                # Try to get title from nearby elements
                parent = link.parent
                if parent:
                    title_elem = parent.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                    if title_elem:
                        title = title_elem.get_text(strip=True)
            
            if not title or len(title) < 10:
                return None
            
            # Check relevance to our symbol
            if not self.is_relevant_content(title):
                return None
            
            # Try to get article summary or description
            summary = ""
            parent = link.parent
            if parent:
                # Look for summary/description in nearby elements
                summary_elem = (parent.find('p') or 
                               parent.find('div', class_=lambda x: x and 'summary' in x.lower()) or
                               parent.find('span', class_=lambda x: x and 'description' in x.lower()))
                if summary_elem:
                    summary = summary_elem.get_text(strip=True)
            
            # Combine title and summary
            text = f"{title}. {summary}" if summary else title
            text = self.clean_text(text)
            
            # Try to enhance with newspaper3k if available
            enhanced_text = self._enhance_with_newspaper3k(href, text)
            
            # Create sentiment data
            sentiment = self._analyze_text(enhanced_text)
            return SentimentData(
                text=enhanced_text,
                source=f"Seeking Alpha ({section_type})",
                timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                polarity=sentiment['polarity'],
                compound=sentiment['compound'],
                url=href,
                raw_extracted_text=enhanced_text if enhanced_text != text else ""
            )
            
        except Exception as e:
            if self.debug:
                print(f"      Error processing article link: {e}")
            return None
    
    def _enhance_with_newspaper3k(self, url: str, fallback_text: str) -> str:
        """Try to enhance article text using newspaper3k"""
        try:
            # Import newspaper3k if available
            from newspaper import Article, Config
            
            config = Config()
            config.browser_user_agent = self.get_random_user_agent()
            config.request_timeout = 5
            config.number_threads = 1
            
            article = Article(url, config=config)
            article.download()
            article.parse()
            
            if article.text and len(article.text) > len(fallback_text):
                if self.debug:
                    print(f"      Enhanced article with newspaper3k: {len(article.text)} chars vs {len(fallback_text)} chars")
                return f"{article.title}. {article.text}" if article.title else article.text
            
        except Exception as e:
            if self.debug:
                print(f"      newspaper3k enhancement failed: {e}")
        
        return fallback_text
    
    def _scrape_fallback_methods(self, max_articles: int) -> List[SentimentData]:
        """Fallback scraping methods if Selenium doesn't get enough articles"""
        sentiments = []
        
        try:
            # Try direct news and analysis page URLs
            fallback_urls = [
                f"https://seekingalpha.com/symbol/{self.symbol}/news",
                f"https://seekingalpha.com/symbol/{self.symbol}/analysis"
            ]
            
            for url in fallback_urls:
                if len(sentiments) >= max_articles:
                    break
                
                try:
                    # Try with requests first (faster)
                    headers = self._get_enhanced_headers()
                    response = self._make_resilient_request(url, headers, max_attempts=2)
                    
                    if response and response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        articles = self._extract_general_articles(soup, max_articles - len(sentiments))
                        sentiments.extend(articles)
                    
                except Exception as e:
                    if self.debug:
                        print(f"      Fallback URL {url} failed: {e}")
                    continue
            
            # RSS feed as final fallback
            if len(sentiments) < max_articles:
                rss_articles = self._try_seekingalpha_rss(max_articles - len(sentiments))
                sentiments.extend(rss_articles)
            
        except Exception as e:
            if self.debug:
                print(f"      Fallback methods error: {e}")
        
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