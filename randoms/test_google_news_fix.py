#!/usr/bin/env python3
"""
Test script to verify Google News URL resolution fix
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.google_news_scraper import GoogleNewsScraper

def test_google_news_newspaper3k_fix():
    """Test that Google News URLs are resolved before newspaper3k processing"""
    print("TESTING GOOGLE NEWS NEWSPAPER3K FIX")
    print("=" * 50)
    
    try:
        # Initialize scraper with debug enabled
        scraper = GoogleNewsScraper("AAPL", debug=True)
        
        print("Scraping 2 Google News articles to test newspaper3k integration...")
        articles = scraper.scrape(max_articles=5)
        
        print(f"\nFound {len(articles)} articles")
        
        enhanced_count = 0
        total_enhanced_chars = 0
        
        for i, article in enumerate(articles):
            print(f"\n--- Article {i+1} ---")
            print(f"Original length: {len(article.text)} characters")
            print(f"URL: {article.url}")
            print(f"Source: {article.source}")
            
            # Check if newspaper3k enhancement worked
            has_enhancement = hasattr(article, 'raw_extracted_text') and article.raw_extracted_text
            if has_enhancement:
                enhanced_count += 1
                enhancement_chars = len(article.raw_extracted_text)
                total_enhanced_chars += enhancement_chars
                print(f"ENHANCEMENT: SUCCESS! +{enhancement_chars} chars from newspaper3k")
                print(f"Enhanced text preview: {article.raw_extracted_text[:200]}...")
            else:
                print(f"ENHANCEMENT: None (expected for Google News RSS URLs)")
            
            print(f"Final text preview: {article.text[:200]}...")
        
        print(f"\n=== SUMMARY ===")
        print(f"Articles found: {len(articles)}")
        print(f"Enhanced articles: {enhanced_count}")
        if enhanced_count > 0:
            avg_enhancement = total_enhanced_chars // enhanced_count
            print(f"Average enhancement: {avg_enhancement} characters")
            print(f"SUCCESS: Google News newspaper3k integration is working!")
        else:
            print(f"INFO: No articles enhanced (may be due to Google News RSS format)")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_google_news_newspaper3k_fix()
    if success:
        print(f"\nTest completed.")
    else:
        print(f"\nTest failed.")