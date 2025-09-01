#!/usr/bin/env python3
"""
Example showing how to use the enhanced scraping capabilities in custom scrapers
"""

import sys
import os
from typing import List
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.base_scraper import BaseScraper, SentimentData

class ExampleEnhancedScraper(BaseScraper):
    """Example scraper demonstrating enhanced capabilities"""
    
    @property
    def source_name(self) -> str:
        return "Example Enhanced Scraper"
    
    def scrape(self, max_articles: int = 10) -> List[SentimentData]:
        """Demonstrate enhanced scraping techniques"""
        articles = []
        
        # Example URLs that might have anti-bot protection
        test_urls = [
            f"https://finance.yahoo.com/quote/{self.symbol}",
            f"https://marketwatch.com/investing/stock/{self.symbol.lower()}",
            "https://httpbin.org/status/403",  # Simulates blocked request
        ]
        
        for i, url in enumerate(test_urls[:max_articles]):
            if self.debug:
                print(f"Scraping URL {i+1}: {url}")
            
            try:
                # Method 1: Enhanced request with automatic selenium fallback
                response = self.make_request_enhanced(
                    url,
                    use_selenium_fallback=True,
                    selenium_wait_selector="article, .article, .content, #content",
                    timeout=10
                )
                
                # Parse the response
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract title and content
                title_elem = soup.find(['h1', 'title'])
                title = title_elem.get_text(strip=True) if title_elem else f"Article from {url}"
                
                # Get some content
                content_selectors = ['article', '.article-content', '.content', 'p']
                content = ""
                
                for selector in content_selectors:
                    elements = soup.select(selector)
                    if elements:
                        content = ' '.join([elem.get_text(strip=True) for elem in elements[:3]])
                        break
                
                text = f"{title}. {content}"[:500]  # Limit length
                
                if len(text) > 20:  # Only add if we got meaningful content
                    article = SentimentData(
                        text=self.clean_text(text),
                        source=self.source_name,
                        timestamp=datetime.now(),
                        polarity=0.0,
                        compound=0.0,
                        url=url
                    )
                    
                    # Try to enhance with full article content
                    enhanced_article = self.enhance_article_data(article)
                    articles.append(enhanced_article)
                    
                    if self.debug:
                        print(f"  SUCCESS: Added article ({len(enhanced_article.text)} chars)")
                else:
                    if self.debug:
                        print(f"  SKIPPED: Insufficient content")
                
                # Add delay between requests
                self.random_delay(1.0, 2.0)
                
            except Exception as e:
                if self.debug:
                    print(f"  FAILED: {e}")
                continue
        
        return articles
    
    def scrape_with_direct_selenium(self, url: str) -> str:
        """Example of using selenium directly for complex interactions"""
        if self.debug:
            print(f"Using direct selenium for: {url}")
        
        try:
            # Method 2: Direct selenium usage for complex scenarios
            page_source, final_url = self.make_request_with_selenium(
                url,
                wait_for_selector="body",  # Wait for page to load
                wait_timeout=10,
                enable_javascript=True
            )
            
            if page_source:
                if self.debug:
                    print(f"  Got {len(page_source)} chars via selenium")
                    print(f"  Final URL: {final_url}")
                
                return page_source
            
        except Exception as e:
            if self.debug:
                print(f"  Direct selenium failed: {e}")
        
        return ""
    
    def demonstrate_selenium_features(self):
        """Demonstrate advanced selenium features"""
        print(f"\nDemonstrating selenium features for {self.symbol}:")
        
        # Example 1: Handle JavaScript-heavy pages
        print("1. Handling JavaScript-heavy pages...")
        js_content = self.scrape_with_direct_selenium("https://finance.yahoo.com/")
        print(f"   Got {len(js_content)} chars of JS-rendered content")
        
        # Example 2: Wait for specific elements
        print("2. Waiting for specific elements...")
        try:
            driver = self.get_selenium_driver()
            driver.get("https://httpbin.org/delay/2")
            
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            # Wait for the response to load
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            print(f"   Successfully waited for element: {element.text[:50]}...")
            
        except Exception as e:
            print(f"   Wait failed: {e}")
        
        # Example 3: Handle forms or interactions (if needed)
        print("3. Advanced interactions (ready for future use)...")
        print("   Framework ready for form filling, clicking, etc.")

def demo_enhanced_scraping():
    """Demonstrate the enhanced scraping capabilities"""
    print("ENHANCED SCRAPING DEMO")
    print("=" * 40)
    
    # Create the enhanced scraper
    scraper = ExampleEnhancedScraper("AAPL", debug=True)
    
    print(f"Testing enhanced scraper for {scraper.symbol}...")
    
    # Regular scraping with enhancements
    articles = scraper.scrape(max_articles=2)
    
    print(f"\nResults:")
    print(f"  Articles collected: {len(articles)}")
    
    for i, article in enumerate(articles):
        print(f"\n  Article {i+1}:")
        print(f"    Source: {article.source}")
        print(f"    Length: {len(article.text)} chars")
        print(f"    URL: {article.url}")
        print(f"    Preview: {article.text[:100]}...")
        
        if hasattr(article, 'raw_extracted_text') and article.raw_extracted_text:
            print(f"    Enhanced: Yes (+{len(article.raw_extracted_text)} chars)")
        else:
            print(f"    Enhanced: No")
    
    # Demonstrate advanced features
    scraper.demonstrate_selenium_features()
    
    # Cleanup
    print(f"\nCleaning up selenium resources...")
    BaseScraper.cleanup_selenium_driver()
    
    print(f"\nDemo complete!")

if __name__ == "__main__":
    demo_enhanced_scraping()