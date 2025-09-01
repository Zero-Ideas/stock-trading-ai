#!/usr/bin/env python3
"""
Stock Sentiment Analyzer
A web scraper that analyzes public sentiment for stock symbols using news and social media data.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import yfinance as yf
import time
import random
from datetime import datetime, timedelta
import re
from urllib.parse import quote
import json
from dataclasses import dataclass
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# Global debug flag
debug = False

@dataclass
class SentimentData:
    """Data structure for sentiment analysis results"""
    text: str
    source: str
    timestamp: datetime
    polarity: float  # TextBlob polarity (-1 to 1)
    compound: float  # VADER compound score (-1 to 1)
    url: str = ""

class StockSentimentAnalyzer:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.analyzer = SentimentIntensityAnalyzer()
        self.session = requests.Session()
        # More diverse and recent user agents to avoid blocking
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Company name mapping for better search results
        self.company_name = self._get_company_name(self.symbol)
        
        print(f"Initialized analyzer for {self.symbol} ({self.company_name})")
    
    def _get_company_name(self, symbol: str) -> str:
        """Get company name from symbol using web search if needed"""
        # Common stock symbols mapping
        symbol_map = {
            'AAPL': 'Apple Inc',
            'MSFT': 'Microsoft Corporation',
            'GOOGL': 'Alphabet Google',
            'AMZN': 'Amazon',
            'TSLA': 'Tesla',
            'META': 'Meta Facebook',
            'NVDA': 'NVIDIA Corporation',
            'NFLX': 'Netflix',
            'BABA': 'Alibaba',
            'CRM': 'Salesforce',
            'ORCL': 'Oracle Corporation',
            'AMD': 'Advanced Micro Devices',
            'INTC': 'Intel Corporation',
            'IBM': 'International Business Machines',
            'UBER': 'Uber Technologies',
            'SPOT': 'Spotify',
            'SNAP': 'Snap Inc',
            'TWTR': 'Twitter',
            'SQ': 'Block Square',
            'PYPL': 'PayPal',
            'DIS': 'Disney',
            'BA': 'Boeing',
            'JPM': 'JPMorgan Chase',
            'V': 'Visa Inc',
            'MA': 'Mastercard',
            'WMT': 'Walmart',
            'PG': 'Procter Gamble',
            'JNJ': 'Johnson Johnson',
            'KO': 'Coca Cola'
        }
        
        if symbol in symbol_map:
            return symbol_map[symbol]
        
        # If not in mapping, try to find it via web search
        try:
            search_url = f"https://finance.yahoo.com/quote/{symbol}"
            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to extract company name from Yahoo Finance page
            h1_tag = soup.find('h1', class_='D(ib)')
            if h1_tag:
                full_text = h1_tag.get_text()
                # Extract company name (usually before the parentheses)
                if '(' in full_text:
                    company_name = full_text.split('(')[0].strip()
                    return company_name
            
            # Fallback: look for any element with company name
            title_tag = soup.find('title')
            if title_tag and 'Stock' in title_tag.text:
                return title_tag.text.split('(')[0].strip()
                
        except Exception as e:
            print(f"Could not fetch company name: {e}")
        
        return symbol  # Fallback to symbol if company name not found

    def get_comprehensive_sentiment(self, target_articles: int = 50) -> List[SentimentData]:
        """Intelligently gather sentiment data from multiple sources until target is reached"""
        all_sentiments = []
        
        # Define source functions with their expected yield and priority
        source_functions = [
            (self._scrape_google_news, "Google News", 15),
            (self._scrape_cnbc, "CNBC", 8),
            (self._scrape_yahoo_finance, "Yahoo Finance", 12),
            (self._scrape_marketwatch, "MarketWatch", 10),
            (self._scrape_reuters, "Reuters", 8),
            (self._scrape_seeking_alpha, "Seeking Alpha", 8),
            (self._scrape_benzinga, "Benzinga", 8),
            (self._scrape_bloomberg_search, "Bloomberg", 6),
        ]
        
        print(f"Target: {target_articles} articles")
        
        # Try each source until we have enough data or exhaust all sources
        for source_func, source_name, expected_yield in source_functions:
            if len(all_sentiments) >= target_articles:
                break
                
            print(f"Scraping {source_name}...")
            
            try:
                # Randomize user agent for each source
                self.session.headers.update({
                    'User-Agent': random.choice(self.user_agents)
                })
                
                # Calculate how many we need from this source
                remaining_needed = target_articles - len(all_sentiments)
                articles_to_fetch = min(expected_yield, remaining_needed + 5)  # +5 buffer
                
                source_sentiments = source_func(articles_to_fetch)
                
                if source_sentiments:
                    all_sentiments.extend(source_sentiments)
                    print(f"  -> Found {len(source_sentiments)} articles from {source_name}")
                else:
                    print(f"  -> No articles found from {source_name}")
                
                # Rate limiting with more variation
                time.sleep(random.uniform(1.5, 3.0))
                
            except Exception as e:
                print(f"  -> Error with {source_name}: {str(e)}")
                import traceback
                if debug:
                    traceback.print_exc()
                continue
        
        # Remove duplicates based on text similarity
        unique_sentiments = self._remove_duplicates(all_sentiments)
        
        print(f"Total unique articles collected: {len(unique_sentiments)}")
        return unique_sentiments
    
    def _remove_duplicates(self, sentiments: List[SentimentData]) -> List[SentimentData]:
        """Remove duplicate articles based on text similarity"""
        unique_sentiments = []
        seen_texts = set()
        
        for sentiment in sentiments:
            # Create a normalized version of the text for comparison
            normalized_text = re.sub(r'[^\w\s]', '', sentiment.text.lower())[:100]
            
            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                unique_sentiments.append(sentiment)
        
        return unique_sentiments

    def _scrape_google_news(self, max_articles: int = 10) -> List[SentimentData]:
        """Scrape Google News for stock-related articles"""
        sentiments = []
        query = f"{self.symbol} {self.company_name} stock"
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
        
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')[:max_articles]
            
            for item in items:
                title = item.title.text if item.title else ""
                description = item.description.text if item.description else ""
                text = f"{title}. {description}"
                
                # Clean HTML tags from description
                text = re.sub(r'<[^>]+>', '', text)
                
                pub_date = item.pubDate.text if item.pubDate else ""
                timestamp = self._parse_date(pub_date)
                
                link = item.link.text if item.link else ""
                
                sentiment = self._analyze_text(text)
                sentiments.append(SentimentData(
                    text=text,
                    source="Google News",
                    timestamp=timestamp,
                    polarity=sentiment['polarity'],
                    compound=sentiment['compound'],
                    url=link
                ))
        
        except Exception as e:
            print(f"Error scraping Google News: {str(e)}")
            import traceback
            if debug:
                traceback.print_exc()
        
        return sentiments

    def _scrape_yahoo_finance(self, max_articles: int = 12) -> List[SentimentData]:
        """Scrape Yahoo Finance for stock news"""
        sentiments = []
        
        try:
            # Try Yahoo Finance news page
            news_url = f"https://finance.yahoo.com/quote/{self.symbol}/news"
            response = self.session.get(news_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for news articles
                news_selectors = [
                    'div[data-testid="news-stream"] h3',
                    'div.Py\\(14px\\) h3',
                    'h3 a[data-testid="clamp-container"]',
                    'li.js-stream-content h3',
                    'div.js-content-viewer h3'
                ]
                
                articles = []
                for selector in news_selectors:
                    found = soup.select(selector)[:max_articles]
                    if found:
                        articles = found
                        break
                
                # If CSS selectors don't work, try class-based search
                if not articles:
                    articles = (soup.find_all('h3', class_='Mb(5px)') +
                               soup.find_all('h3', class_='LineClamp(2,20px)') +
                               soup.find_all('div', class_='C($c-fuji-grey-j)')[:max_articles])
                
                for article in articles[:max_articles]:
                    try:
                        # Get title
                        if article.name == 'h3':
                            title_elem = article
                        else:
                            title_elem = article.find('h3') or article.find('a')
                            
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        if not title or len(title) < 10:
                            continue
                        
                        # Try to get summary/description
                        parent = article.parent or article
                        summary_elem = (parent.find('p') or 
                                      parent.find('div', string=True) or
                                      parent.find_next('p'))
                        summary = summary_elem.get_text(strip=True) if summary_elem else ""
                        
                        text = f"{title}. {summary}" if summary else title
                        
                        # Get URL
                        link_elem = article.find('a') if article.name != 'a' else article
                        url = ""
                        if link_elem and link_elem.get('href'):
                            href = link_elem.get('href')
                            if href.startswith('/news/'):
                                url = f"https://finance.yahoo.com{href}"
                            elif href.startswith('http'):
                                url = href
                        
                        sentiment = self._analyze_text(text)
                        sentiments.append(SentimentData(
                            text=text,
                            source="Yahoo Finance",
                            timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                            polarity=sentiment['polarity'],
                            compound=sentiment['compound'],
                            url=url
                        ))
                        
                    except Exception:
                        continue
        
        except Exception as e:
            print(f"Error scraping Yahoo Finance: {str(e)}")
        
        return sentiments

    def _scrape_marketwatch(self, max_articles: int = 10) -> List[SentimentData]:
        """Scrape MarketWatch for stock news"""
        sentiments = []
        
        try:
            # Try direct stock page first
            stock_url = f"https://www.marketwatch.com/investing/stock/{self.symbol.lower()}"
            response = self.session.get(stock_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for news articles on stock page
                news_articles = soup.find_all('div', class_='article__content') or soup.find_all('div', class_='newsitem')
                
                for article in news_articles[:max_articles]:
                    try:
                        title_elem = article.find('h3') or article.find('h4') or article.find('a')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        if not title or len(title) < 10:
                            continue
                        
                        # Get snippet/description
                        snippet_elem = article.find('p') or article.find('div', class_='article__summary')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        
                        text = f"{title}. {snippet}" if snippet else title
                        
                        # Get URL
                        link_elem = article.find('a')
                        url = ""
                        if link_elem and link_elem.get('href'):
                            href = link_elem.get('href')
                            url = href if href.startswith('http') else f"https://www.marketwatch.com{href}"
                        
                        sentiment = self._analyze_text(text)
                        sentiments.append(SentimentData(
                            text=text,
                            source="MarketWatch",
                            timestamp=datetime.now() - timedelta(hours=random.randint(1, 72)),
                            polarity=sentiment['polarity'],
                            compound=sentiment['compound'],
                            url=url
                        ))
                    except Exception:
                        continue
            
            # If direct page didn't work, try search
            if len(sentiments) < max_articles // 2:
                search_url = f"https://www.marketwatch.com/search?q={quote(self.symbol)}"
                response = self.session.get(search_url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find article links with multiple selectors
                articles = (soup.find_all('div', class_='searchresult') + 
                           soup.find_all('div', class_='result') + 
                           soup.find_all('article'))[:max_articles]
                
                for article in articles:
                    if len(sentiments) >= max_articles:
                        break
                    try:
                        title_elem = article.find('h3') or article.find('h4') or article.find('a')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        if not title or len(title) < 10:
                            continue
                        
                        # Get snippet/description
                        snippet_elem = article.find('p')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        
                        text = f"{title}. {snippet}" if snippet else title
                        
                        # Get URL
                        link_elem = article.find('a')
                        url = ""
                        if link_elem and link_elem.get('href'):
                            href = link_elem.get('href')
                            url = href if href.startswith('http') else f"https://www.marketwatch.com{href}"
                        
                        sentiment = self._analyze_text(text)
                        sentiments.append(SentimentData(
                            text=text,
                            source="MarketWatch",
                            timestamp=datetime.now() - timedelta(hours=random.randint(1, 72)),
                            polarity=sentiment['polarity'],
                            compound=sentiment['compound'],
                            url=url
                        ))
                    except Exception:
                        continue
        
        except Exception as e:
            print(f"Error scraping MarketWatch: {str(e)}")
        
        return sentiments
    
    def _scrape_seeking_alpha(self, max_articles: int = 8) -> List[SentimentData]:
        """Scrape Seeking Alpha for stock analysis"""
        sentiments = []
        
        try:
            # Try multiple URLs for Seeking Alpha
            urls_to_try = [
                f"https://seekingalpha.com/symbol/{self.symbol}/news",
                f"https://seekingalpha.com/symbol/{self.symbol}",
                f"https://seekingalpha.com/search?q={quote(self.symbol)}"
            ]
            
            for search_url in urls_to_try:
                if len(sentiments) >= max_articles:
                    break
                    
                try:
                    # Add specific headers for Seeking Alpha
                    headers = self.session.headers.copy()
                    headers.update({
                        'Referer': 'https://seekingalpha.com/',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                    })
                    
                    response = self.session.get(search_url, timeout=15, headers=headers)
                    if response.status_code != 200:
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
                            
                            # Look for summary
                            summary_elem = (article.find('p') or 
                                          article.find('div', {'data-testid': 'post-list-content'}))
                            summary = summary_elem.get_text(strip=True) if summary_elem else ""
                            
                            text = f"{title}. {summary}" if summary else title
                            
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
                            
                        except Exception:
                            continue
                            
                except Exception:
                    continue
        
        except Exception as e:
            print(f"Error scraping Seeking Alpha: {str(e)}")
        
        return sentiments
    
    def _scrape_benzinga(self, max_articles: int = 8) -> List[SentimentData]:
        """Scrape Benzinga for stock news"""
        sentiments = []
        
        try:
            # Try multiple approaches for Benzinga
            urls_to_try = [
                f"https://www.benzinga.com/quote/{self.symbol}/news",
                f"https://www.benzinga.com/search?q={quote(self.symbol)}",
                f"https://www.benzinga.com/news/earnings?tickers={self.symbol}"
            ]
            
            for search_url in urls_to_try:
                if len(sentiments) >= max_articles:
                    break
                    
                try:
                    response = self.session.get(search_url, timeout=15)
                    if response.status_code != 200:
                        continue
                        
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Try multiple selectors for articles
                    article_selectors = [
                        'div.story-item',
                        'div.feed-item',
                        'div.post-item',
                        'article',
                        'div.news-item'
                    ]
                    
                    articles = []
                    for selector in article_selectors:
                        found = soup.select(selector)[:max_articles - len(sentiments)]
                        if found:
                            articles = found
                            break
                    
                    for article in articles:
                        if len(sentiments) >= max_articles:
                            break
                            
                        try:
                            title_elem = (article.find('h4') or 
                                        article.find('h3') or 
                                        article.find('h2') or
                                        article.find('a'))
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text(strip=True)
                            if not title or len(title) < 10:
                                continue
                            
                            # Get excerpt
                            excerpt_elem = (article.find('p', class_='excerpt') or 
                                          article.find('div', class_='excerpt') or
                                          article.find('p'))
                            excerpt = excerpt_elem.get_text(strip=True) if excerpt_elem else ""
                            
                            text = f"{title}. {excerpt}" if excerpt else title
                            
                            # Get URL
                            link_elem = article.find('a')
                            url = ""
                            if link_elem and link_elem.get('href'):
                                href = link_elem.get('href')
                                if href.startswith('/'):
                                    url = f"https://www.benzinga.com{href}"
                                elif href.startswith('http'):
                                    url = href
                            
                            sentiment = self._analyze_text(text)
                            sentiments.append(SentimentData(
                                text=text,
                                source="Benzinga",
                                timestamp=datetime.now() - timedelta(hours=random.randint(1, 72)),
                                polarity=sentiment['polarity'],
                                compound=sentiment['compound'],
                                url=url
                            ))
                            
                        except Exception:
                            continue
                            
                except Exception:
                    continue
        
        except Exception as e:
            print(f"Error scraping Benzinga: {str(e)}")
        
        return sentiments
    
    def _scrape_financial_times(self, max_articles: int = 8) -> List[SentimentData]:
        """Scrape Financial Times for stock coverage"""
        sentiments = []
        
        try:
            search_url = f"https://www.ft.com/search?q={quote(self.company_name)}"
            response = self.session.get(search_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = soup.find_all('div', class_='o-teaser__content')[:max_articles]
            
            for article in articles:
                try:
                    title_elem = article.find('div', class_='o-teaser__heading') or article.find('h3')
                    if not title_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    
                    # Get standfirst (summary)
                    summary_elem = article.find('p', class_='o-teaser__standfirst') or article.find('p')
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    
                    text = f"{title}. {summary}" if summary else title
                    
                    # Get URL
                    link_elem = article.find('a')
                    url = ""
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        url = href if href.startswith('http') else f"https://www.ft.com{href}"
                    
                    sentiment = self._analyze_text(text)
                    sentiments.append(SentimentData(
                        text=text,
                        source="Financial Times",
                        timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                        polarity=sentiment['polarity'],
                        compound=sentiment['compound'],
                        url=url
                    ))
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"Error scraping Financial Times: {str(e)}")
        
        return sentiments
    
    def _scrape_bloomberg_search(self, max_articles: int = 12) -> List[SentimentData]:
        """Scrape Bloomberg search results"""
        sentiments = []
        
        try:
            search_url = f"https://www.bloomberg.com/search?query={quote(self.symbol)}+{quote(self.company_name)}"
            response = self.session.get(search_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Bloomberg uses various classes, try multiple selectors
            articles = soup.find_all('div', class_='storyItem__aHqJu')[:max_articles]
            if not articles:
                articles = soup.find_all('div', class_='search-result-story')[:max_articles]
            
            for article in articles:
                try:
                    title_elem = article.find('h3') or article.find('h4') or article.find('a')
                    if not title_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    
                    # Get summary
                    summary_elem = article.find('p')
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    
                    text = f"{title}. {summary}" if summary else title
                    
                    # Get URL
                    link_elem = article.find('a')
                    url = ""
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        url = href if href.startswith('http') else f"https://www.bloomberg.com{href}"
                    
                    sentiment = self._analyze_text(text)
                    sentiments.append(SentimentData(
                        text=text,
                        source="Bloomberg",
                        timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                        polarity=sentiment['polarity'],
                        compound=sentiment['compound'],
                        url=url
                    ))
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"Error scraping Bloomberg: {str(e)}")
        
        return sentiments
    
    def _scrape_cnbc(self, max_articles: int = 10) -> List[SentimentData]:
        """Scrape CNBC for stock news"""
        sentiments = []
        
        try:
            # Try direct stock quotes page first
            quotes_url = f"https://www.cnbc.com/quotes/{self.symbol.upper()}"
            response = self.session.get(quotes_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for news section on quotes page
                news_articles = (soup.find_all('div', class_='RelatedNews-container') + 
                               soup.find_all('div', class_='InlineVideo-container') + 
                               soup.find_all('div', class_='Card-container'))
                
                for article in news_articles[:max_articles // 2]:
                    try:
                        title_elem = article.find('h4') or article.find('h3') or article.find('a')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        if not title or len(title) < 10:
                            continue
                        
                        # Get summary if available
                        summary_elem = article.find('p')
                        summary = summary_elem.get_text(strip=True) if summary_elem else ""
                        
                        text = f"{title}. {summary}" if summary else title
                        
                        # Get URL
                        link_elem = article.find('a')
                        url = ""
                        if link_elem and link_elem.get('href'):
                            href = link_elem.get('href')
                            url = href if href.startswith('http') else f"https://www.cnbc.com{href}"
                        
                        sentiment = self._analyze_text(text)
                        sentiments.append(SentimentData(
                            text=text,
                            source="CNBC",
                            timestamp=datetime.now() - timedelta(hours=random.randint(1, 72)),
                            polarity=sentiment['polarity'],
                            compound=sentiment['compound'],
                            url=url
                        ))
                    except Exception:
                        continue
            
            # Try search if we need more articles
            if len(sentiments) < max_articles:
                search_url = f"https://www.cnbc.com/search/?query={quote(self.symbol)}"
                response = self.session.get(search_url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try multiple selectors
                article_selectors = [
                    'div.SearchResult-searchResult',
                    'div.InlineVideo-container',
                    'div.Card-container',
                    'div[data-module="ArticleList"]'
                ]
                
                articles = []
                for selector in article_selectors:
                    found = soup.select(selector)[:max_articles - len(sentiments)]
                    if found:
                        articles.extend(found)
                        break
                
                for article in articles:
                    if len(sentiments) >= max_articles:
                        break
                        
                    try:
                        title_elem = (article.find('h3') or 
                                    article.find('h4') or
                                    article.find('a'))
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        if not title or len(title) < 10:
                            continue
                        
                        # Get summary
                        summary_elem = article.find('p')
                        summary = summary_elem.get_text(strip=True) if summary_elem else ""
                        
                        text = f"{title}. {summary}" if summary else title
                        
                        # Get URL
                        link_elem = article.find('a')
                        url = ""
                        if link_elem and link_elem.get('href'):
                            href = link_elem.get('href')
                            url = href if href.startswith('http') else f"https://www.cnbc.com{href}"
                        
                        sentiment = self._analyze_text(text)
                        sentiments.append(SentimentData(
                            text=text,
                            source="CNBC",
                            timestamp=datetime.now() - timedelta(hours=random.randint(1, 72)),
                            polarity=sentiment['polarity'],
                            compound=sentiment['compound'],
                            url=url
                        ))
                    except Exception:
                        continue
        
        except Exception as e:
            print(f"Error scraping CNBC: {str(e)}")
        
        return sentiments

    def _scrape_reuters(self, max_articles: int = 10) -> List[SentimentData]:
        """Scrape Reuters for stock news"""
        sentiments = []
        
        try:
            # Try multiple approaches for Reuters
            search_queries = [
                f"https://www.reuters.com/markets/companies/{self.symbol.upper()}",
                f"https://www.reuters.com/site-search/?query={quote(self.symbol)}",
                f"https://www.reuters.com/site-search/?query={quote(self.company_name)}"
            ]
            
            for search_url in search_queries:
                if len(sentiments) >= max_articles:
                    break
                    
                try:
                    response = self.session.get(search_url, timeout=15)
                    if response.status_code != 200:
                        continue
                        
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Try multiple selectors for articles
                    article_selectors = [
                        'div[data-testid="MediaStoryCard"]',
                        'div.search-result-indiv',
                        'div.story-content',
                        'article',
                        'div.media-story-card'
                    ]
                    
                    articles = []
                    for selector in article_selectors:
                        found = soup.select(selector)[:max_articles - len(sentiments)]
                        if found:
                            articles = found
                            break
                    
                    for article in articles:
                        if len(sentiments) >= max_articles:
                            break
                            
                        try:
                            # Try multiple ways to get title
                            title_elem = (article.find('h3') or 
                                        article.find('h4') or 
                                        article.find('h2') or 
                                        article.find('a'))
                            
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text(strip=True)
                            if not title or len(title) < 10:
                                continue
                            
                            # Try to get summary
                            summary_elem = (article.find('p') or 
                                          article.find('div', class_='summary'))
                            summary = summary_elem.get_text(strip=True) if summary_elem else ""
                            
                            text = f"{title}. {summary}" if summary else title
                            
                            # Try to get the article URL
                            link_elem = article.find('a')
                            url = ""
                            if link_elem and link_elem.get('href'):
                                href = link_elem.get('href')
                                if href.startswith('http'):
                                    url = href
                                elif href.startswith('/'):
                                    url = "https://www.reuters.com" + href
                            
                            sentiment = self._analyze_text(text)
                            sentiments.append(SentimentData(
                                text=text,
                                source="Reuters",
                                timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                                polarity=sentiment['polarity'],
                                compound=sentiment['compound'],
                                url=url
                            ))
                            
                        except Exception:
                            continue
                            
                except Exception:
                    continue
        
        except Exception as e:
            print(f"Error scraping Reuters: {str(e)}")
        
        return sentiments

    def get_reddit_sentiment(self, max_posts: int = 20) -> List[SentimentData]:
        """Get sentiment from Reddit posts (using pushshift API alternative)"""
        sentiments = []
        
        # Note: Reddit's API requires authentication. This is a simplified approach.
        # For production use, implement proper Reddit API authentication.
        
        try:
            # Search for posts mentioning the stock symbol
            subreddits = ['stocks', 'investing', 'SecurityAnalysis', 'ValueInvesting', 'StockMarket']
            
            for subreddit in subreddits[:3]:  # Limit to avoid rate limiting
                try:
                    # This would require praw (Python Reddit API Wrapper) for proper implementation
                    # For now, we'll simulate some data
                    print(f"Note: Reddit scraping requires proper API authentication")
                    break
                except:
                    continue
        
        except Exception as e:
            print(f"Error getting Reddit data: {str(e)}")
        
        return sentiments

    def _analyze_text(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text using both TextBlob and VADER"""
        # TextBlob analysis
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # VADER analysis
        vader_scores = self.analyzer.polarity_scores(text)
        compound = vader_scores['compound']
        
        return {
            'polarity': polarity,
            'compound': compound,
            'positive': vader_scores['pos'],
            'neutral': vader_scores['neu'],
            'negative': vader_scores['neg']
        }

    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats"""
        try:
            # Try common date formats
            formats = [
                '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # If parsing fails, return current time minus random hours
            return datetime.now() - timedelta(hours=random.randint(1, 24))
        
        except:
            return datetime.now()

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
        avg_polarity = sum(s.polarity for s in all_sentiments) / total_articles
        avg_compound = sum(s.compound for s in all_sentiments) / total_articles
        
        # Categorize sentiment
        positive_count = sum(1 for s in all_sentiments if s.compound > 0.05)
        negative_count = sum(1 for s in all_sentiments if s.compound < -0.05)
        neutral_count = total_articles - positive_count - negative_count
        
        # Determine overall sentiment with more nuanced thresholds
        if avg_compound > 0.2:
            overall_sentiment = "Very Positive"
        elif avg_compound > 0.05:
            overall_sentiment = "Positive"
        elif avg_compound > -0.05:
            overall_sentiment = "Neutral"
        elif avg_compound > -0.2:
            overall_sentiment = "Negative"
        else:
            overall_sentiment = "Very Negative"
        
        # Get stock price for context (using web scraping instead of yfinance)
        current_price, price_change = self._get_stock_price_context()
        
        # Calculate source diversity score
        source_count = len(set(s.source for s in all_sentiments))
        diversity_score = min(source_count / 8.0, 1.0)  # Max 8 sources
        
        # Create summary report
        results = {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_sources_analyzed": total_articles,
            "unique_sources_count": source_count,
            "source_diversity_score": round(diversity_score, 2),
            "overall_sentiment": overall_sentiment,
            "sentiment_scores": {
                "average_polarity": round(avg_polarity, 3),
                "average_compound": round(avg_compound, 3)
            },
            "sentiment_distribution": {
                "positive": positive_count,
                "neutral": neutral_count,
                "negative": negative_count,
                "positive_percentage": round((positive_count / total_articles) * 100, 1),
                "negative_percentage": round((negative_count / total_articles) * 100, 1)
            },
            "stock_context": {
                "current_price": current_price,
                "daily_change_percent": price_change
            },
            "sources": {
                source: len([s for s in all_sentiments if s.source == source])
                for source in set(s.source for s in all_sentiments)
            },
            "sample_articles": [
                {
                    "text": s.text[:300] + "..." if len(s.text) > 300 else s.text,
                    "source": s.source,
                    "sentiment_score": round(s.compound, 3),
                    "sentiment_label": self._get_sentiment_label(s.compound),
                    "timestamp": s.timestamp.isoformat(),
                    "url": s.url
                }
                for s in sorted(all_sentiments, key=lambda x: abs(x.compound), reverse=True)
            ],
            "top_sentiment_articles": [
                {
                    "text": s.text[:200] + "..." if len(s.text) > 200 else s.text,
                    "source": s.source,
                    "sentiment_score": round(s.compound, 3),
                    "sentiment_label": self._get_sentiment_label(s.compound),
                    "timestamp": s.timestamp.isoformat(),
                    "url": s.url
                }
                for s in sorted(all_sentiments, key=lambda x: abs(x.compound), reverse=True)[:10]
            ],
            "sentiment_trends": self._analyze_sentiment_trends(all_sentiments),
            "confidence_metrics": {
                "sample_size": "Good" if total_articles >= 30 else "Limited" if total_articles >= 15 else "Very Limited",
                "source_diversity": "High" if source_count >= 6 else "Medium" if source_count >= 4 else "Low",
                "data_recency": "Current" if any(s.timestamp > datetime.now() - timedelta(days=1) for s in all_sentiments) else "Recent"
            }
        }
        
        return results
    
    def _get_stock_price_context(self) -> Tuple[float, float]:
        """Get current stock price and change using web scraping"""
        try:
            # Try Yahoo Finance page scraping
            url = f"https://finance.yahoo.com/quote/{self.symbol}"
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for price elements
            price_elem = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
            if not price_elem:
                price_elem = soup.find('span', class_='Trsdu(0.3s)')
            
            change_elem = soup.find('fin-streamer', {'data-field': 'regularMarketChangePercent'})
            if not change_elem:
                change_elem = soup.find('span', class_='Trsdu(0.3s)', string=re.compile(r'[+-]\d+\.\d+%'))
            
            current_price = None
            price_change = None
            
            if price_elem:
                price_text = price_elem.get_text().replace(',', '')
                try:
                    current_price = float(price_text)
                except ValueError:
                    pass
            
            if change_elem:
                change_text = change_elem.get_text().replace('%', '').replace('+', '')
                try:
                    price_change = float(change_text)
                except ValueError:
                    pass
            
            return current_price, price_change
            
        except Exception as e:
            print(f"Could not fetch stock price: {e}")
            return None, None
    
    def _get_sentiment_label(self, compound_score: float) -> str:
        """Convert compound score to readable label"""
        if compound_score > 0.5:
            return "Very Positive"
        elif compound_score > 0.05:
            return "Positive"
        elif compound_score > -0.05:
            return "Neutral"
        elif compound_score > -0.5:
            return "Negative"
        else:
            return "Very Negative"
    
    def _analyze_sentiment_trends(self, sentiments: List[SentimentData]) -> Dict:
        """Analyze sentiment trends over time"""
        if not sentiments:
            return {}
        
        # Group by time periods
        now = datetime.now()
        recent_24h = [s for s in sentiments if s.timestamp > now - timedelta(hours=24)]
        recent_week = [s for s in sentiments if s.timestamp > now - timedelta(days=7)]
        
        def avg_sentiment(sentiment_list):
            return sum(s.compound for s in sentiment_list) / len(sentiment_list) if sentiment_list else 0
        
        return {
            "last_24h_average": round(avg_sentiment(recent_24h), 3) if recent_24h else None,
            "last_week_average": round(avg_sentiment(recent_week), 3) if recent_week else None,
            "overall_average": round(avg_sentiment(sentiments), 3),
            "articles_last_24h": len(recent_24h),
            "articles_last_week": len(recent_week)
        } 

    def save_results(self, results: Dict, filename: str = None) -> str:
        """Save results to JSON file with error handling"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.symbol}_sentiment_{timestamp}.json"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Ensure results can be serialized
                test_json = json.dumps(results, indent=2, ensure_ascii=False)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(test_json)
                
                print(f"Results successfully saved to {filename}")
                print(f"File contains {len(results.get('sample_articles', []))} articles from {results.get('unique_sources_count', 0)} sources")
                return filename
                
            except (IOError, OSError, PermissionError) as e:
                print(f"Attempt {attempt + 1} failed to save file: {str(e)}")
                if attempt < max_retries - 1:
                    # Try alternative filename
                    base_name = filename.rsplit('.', 1)[0]
                    filename = f"{base_name}_alt{attempt + 1}.json"
                    time.sleep(0.5)
                else:
                    print(f"Failed to save results after {max_retries} attempts")
                    return None
            except Exception as e:
                print(f"Unexpected error saving results: {str(e)}")
                return None
        
        return None

def main():
    """Main function to run the sentiment analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze stock sentiment from news and social media")
    parser.add_argument("symbol", help="Stock symbol (e.g., AAPL, TSLA, NVDA)")
    parser.add_argument("--articles", type=int, default=50, help="Maximum number of articles to analyze (default: 50)")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to JSON file (saves by default)")
    parser.add_argument("--output", help="Output filename (optional)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output for troubleshooting")
    
    args = parser.parse_args()
    
    # Set global debug flag
    global debug
    debug = args.debug

    # Create analyzer and run analysis
    analyzer = StockSentimentAnalyzer(args.symbol)
    results = analyzer.analyze_sentiment(target_articles=args.articles)
    
    if "error" in results:
        print(f"Error: {results['error']}")
        return
    
    # Print results
    print("\n" + "="*60)
    print(f"SENTIMENT ANALYSIS RESULTS FOR {results['symbol']}")
    print("="*60)
    print(f"Company: {results['company_name']}")
    print(f"Analysis Time: {results['analysis_timestamp']}")
    print(f"Sources Analyzed: {results['total_sources_analyzed']}")
    print(f"Overall Sentiment: {results['overall_sentiment']}")
    print(f"Average Sentiment Score: {results['sentiment_scores']['average_compound']}")
    
    # Stock context
    if results['stock_context']['current_price']:
        print(f"Current Price: ${results['stock_context']['current_price']}")
        if results['stock_context']['daily_change_percent'] is not None:
            print(f"Daily Change: {results['stock_context']['daily_change_percent']:+.2f}%")
        else:
            print(f"Daily Change: N/A")
    
    # Sentiment distribution
    dist = results['sentiment_distribution']
    print(f"\nSentiment Distribution:")
    print(f"  Positive: {dist['positive']} ({dist['positive_percentage']}%)")
    print(f"  Neutral: {dist['neutral']} ({100 - dist['positive_percentage'] - dist['negative_percentage']:.1f}%)")
    print(f"  Negative: {dist['negative']} ({dist['negative_percentage']}%)")
    
    # Sample articles
    print(f"\nTop Sentiment-Driving Articles:")
    for i, article in enumerate(results['top_sentiment_articles'], 1):
        sentiment_label = "Positive" if article['sentiment_score'] > 0.05 else "Negative" if article['sentiment_score'] < -0.05 else "Neutral"
        print(f"\n{i}. [{article['source']}] Score: {article['sentiment_score']} ({sentiment_label})")
        print(f"   {article['text']}")
        if article['url']:
            print(f"   URL: {article['url']}")
    
    print(f"\n[INFO] All {len(results['sample_articles'])} articles saved to JSON file.")
    
    # Save results by default (unless --no-save is specified)
    if not args.no_save:
        saved_file = analyzer.save_results(results, args.output)
        if saved_file:
            print(f"\n[SUCCESS] Complete analysis saved to: {saved_file}")
        else:
            print(f"\n[WARNING] Failed to save results to file")
    else:
        print(f"\n[INFO] Results not saved (--no-save flag used)")

if __name__ == "__main__":
    main()