#!/usr/bin/env python3
"""
Quick test to verify improved scrapers
"""

import sys
import os
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.newsapi_scraper import NewsAPIScraper
from scrapers.google_news_scraper import GoogleNewsScraper

def test_newsapi_enhancement():
    """Test NewsAPI with newspaper3k enhancement"""
    print("Testing NewsAPI with newspaper3k enhancement...")
    print("-" * 50)
    
    scraper = NewsAPIScraper("AAPL", debug=True)
    articles = scraper.scrape(max_articles=2)
    
    print(f"Found {len(articles)} articles")
    for i, article in enumerate(articles):
        print(f"\nArticle {i+1}:")
        print(f"  Length: {len(article.text)} characters")
        print(f"  URL: {article.url}")
        print(f"  Enhanced: {hasattr(article, 'raw_extracted_text') and bool(article.raw_extracted_text)}")
        if hasattr(article, 'raw_extracted_text') and article.raw_extracted_text:
            print(f"  Raw extraction length: {len(article.raw_extracted_text)}")
        print(f"  Preview: {article.text[:200]}...")

def test_google_news_improved():
    """Test improved Google News scraper"""
    print("\nTesting improved Google News scraper...")
    print("-" * 50)
    
    scraper = GoogleNewsScraper("AAPL", debug=True)
    articles = scraper.scrape(max_articles=2)
    
    print(f"Found {len(articles)} articles")
    for i, article in enumerate(articles):
        print(f"\nArticle {i+1}:")
        print(f"  Length: {len(article.text)} characters")
        print(f"  URL: {article.url}")
        print(f"  Enhanced: {hasattr(article, 'raw_extracted_text') and bool(article.raw_extracted_text)}")
        if hasattr(article, 'raw_extracted_text') and article.raw_extracted_text:
            print(f"  Raw extraction length: {len(article.raw_extracted_text)}")
        print(f"  Preview: {article.text}...")

def main():
    print("IMPROVED SCRAPERS TEST")
    print("=" * 60)
    
    try:
        test_newsapi_enhancement()
        time.sleep(3)  # Rate limiting
        test_google_news_improved()
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()