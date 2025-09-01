#!/usr/bin/env python3
"""
Debug why enhancement detection isn't working properly
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.google_news_scraper import GoogleNewsScraper

def debug_enhancement():
    """Debug the enhancement process"""
    print("DEBUGGING ENHANCEMENT DETECTION")
    print("=" * 40)
    
    scraper = GoogleNewsScraper("AAPL", debug=True)
    articles = scraper.scrape(max_articles=1)
    
    if not articles:
        print("No articles found")
        return
    
    article = articles[0]
    
    print(f"\nArticle attributes:")
    for attr in dir(article):
        if not attr.startswith('_'):
            value = getattr(article, attr)
            if not callable(value):
                print(f"  {attr}: {type(value).__name__} = {str(value)[:100]}...")
    
    print(f"\nChecking for enhancement indicators:")
    print(f"  hasattr(article, 'raw_extracted_text'): {hasattr(article, 'raw_extracted_text')}")
    if hasattr(article, 'raw_extracted_text'):
        print(f"  article.raw_extracted_text length: {len(article.raw_extracted_text) if article.raw_extracted_text else 0}")
        print(f"  article.raw_extracted_text type: {type(article.raw_extracted_text)}")
        if article.raw_extracted_text:
            print(f"  article.raw_extracted_text preview: {article.raw_extracted_text[:200]}...")
    
    print(f"\nText analysis:")
    print(f"  Original text length: {len(article.text)}")
    print(f"  Text preview: {article.text[:200]}...")
    
    # Check if the text contains evidence of successful enhancement
    if len(article.text) > 500:
        print(f"  LIKELY ENHANCED: Text is longer than typical RSS excerpt")
    else:
        print(f"  LIKELY NOT ENHANCED: Text appears to be just RSS excerpt")

if __name__ == "__main__":
    debug_enhancement()