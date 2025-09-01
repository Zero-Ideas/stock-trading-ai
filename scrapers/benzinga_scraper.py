#!/usr/bin/env python3
"""
Benzinga scraper for stock sentiment analysis
"""

from typing import List
import random
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, SentimentData


class BenzingaScraper(BaseScraper):
    """Scraper for Benzinga stock news"""
    
    @property
    def source_name(self) -> str:
        return "Benzinga"
    
    def _analyze_text(self, text: str) -> dict:
        """Analyze text sentiment (placeholder - will be handled by main analyzer)"""
        # This is a placeholder - actual sentiment analysis will be done by the main StockSentimentAnalyzer
        return {'polarity': 0.0, 'compound': 0.0}
    
    def scrape(self, max_articles: int = 8) -> List[SentimentData]:
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
                    response = self.make_request(search_url, timeout=15)
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
                            
                            # Check relevance
                            if not self.is_relevant_content(title):
                                continue
                            
                            # Get excerpt
                            excerpt_elem = (article.find('p', class_='excerpt') or 
                                          article.find('div', class_='excerpt') or
                                          article.find('p'))
                            excerpt = excerpt_elem.get_text(strip=True) if excerpt_elem else ""
                            
                            text = f"{title}. {excerpt}" if excerpt else title
                            text = self.clean_text(text)
                            
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
                            
                        except Exception as e:
                            if self.debug:
                                print(f"Error processing Benzinga article: {e}")
                            continue
                    
                    # Add delay between URLs
                    self.random_delay(1.0, 2.0)
                            
                except Exception as e:
                    if self.debug:
                        print(f"Error with Benzinga URL {search_url}: {e}")
                    continue
        
        except Exception as e:
            if self.debug:
                print(f"Benzinga scraping error: {e}")
        
        return sentiments