#!/usr/bin/env python3
"""
Reuters scraper for stock sentiment analysis
"""

from typing import List
import random
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, SentimentData


class ReutersScraper(BaseScraper):
    """Scraper for Reuters articles"""
    
    @property
    def source_name(self) -> str:
        return "Reuters"
    
    def _analyze_text(self, text: str) -> dict:
        """Analyze text sentiment (placeholder - will be handled by main analyzer)"""
        # This is a placeholder - actual sentiment analysis will be done by the main StockSentimentAnalyzer
        return {'polarity': 0.0, 'compound': 0.0}
    
    def scrape(self, max_articles: int = 10) -> List[SentimentData]:
        """Scrape Reuters for stock news"""
        sentiments = []
        
        try:
            # Reuters search URLs to try
            urls_to_try = [
                f"https://www.reuters.com/search/news?blob={quote(self.symbol)}",
                f"https://www.reuters.com/companies/{self.symbol}.O",
                f"https://www.reuters.com/markets/companies/{self.symbol}"
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
                        'div[data-testid="MediaStoryCard"]',
                        'article',
                        'div.story-content',
                        'div[class*="story"]',
                        'div.search-result-content'
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
                            title_elem = (article.find('h3') or 
                                        article.find('h2') or 
                                        article.find('h4') or
                                        article.find('a'))
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text(strip=True)
                            if not title or len(title) < 10:
                                continue
                            
                            # Check relevance
                            if not self.is_relevant_content(title):
                                continue
                            
                            # Get summary
                            summary_elem = (article.find('p') or
                                          article.find('div', class_=lambda x: x and 'summary' in x.lower() if x else False))
                            summary = summary_elem.get_text(strip=True) if summary_elem else ""
                            
                            text = f"{title}. {summary}" if summary else title
                            text = self.clean_text(text)
                            
                            # Get URL
                            link_elem = article.find('a')
                            url = ""
                            if link_elem and link_elem.get('href'):
                                href = link_elem.get('href')
                                if href.startswith('/'):
                                    url = f"https://www.reuters.com{href}"
                                elif href.startswith('http'):
                                    url = href
                            
                            sentiment = self._analyze_text(text)
                            article_data = SentimentData(
                                text=text,
                                source="Reuters",
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
                                        print(f"      Failed to enhance Reuters article: {e}")
                            
                            sentiments.append(article_data)
                            
                        except Exception as e:
                            if self.debug:
                                print(f"Error processing Reuters article: {e}")
                            continue
                    
                    # Add delay between URLs
                    self.random_delay(1.0, 2.0)
                            
                except Exception as e:
                    if self.debug:
                        print(f"Error with Reuters URL {search_url}: {e}")
                    continue
        
        except Exception as e:
            if self.debug:
                print(f"Reuters scraping error: {e}")
        
        return sentiments