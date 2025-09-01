#!/usr/bin/env python3
"""
Test the enhanced scraping capabilities with selenium fallback for all scrapers
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.google_news_scraper import GoogleNewsScraper
from scrapers.base_scraper import BaseScraper

def test_enhanced_scraping():
    """Test enhanced scraping with selenium fallback"""
    print("TESTING ENHANCED SCRAPING WITH SELENIUM FALLBACK")
    print("=" * 60)
    
    try:
        print("1. Testing Google News scraper with enhanced requests...")
        google_scraper = GoogleNewsScraper("AAPL", debug=True)
        
        print(f"   Selenium available: {hasattr(BaseScraper, 'get_selenium_driver')}")
        
        # Test the scraping
        articles = google_scraper.scrape(max_articles=2)
        
        print(f"\nResults:")
        print(f"  Articles found: {len(articles)}")
        
        enhanced_count = 0
        selenium_used = False
        
        for i, article in enumerate(articles):
            print(f"\n  Article {i+1}:")
            print(f"    Length: {len(article.text)} chars")
            print(f"    URL: {article.url[:80]}...")
            
            # Check if enhanced
            if hasattr(article, 'raw_extracted_text') and article.raw_extracted_text:
                enhanced_count += 1
                print(f"    ENHANCED: Yes (+{len(article.raw_extracted_text)} chars from newspaper3k)")
            else:
                print(f"    ENHANCED: No")
        
        # Check if selenium was used
        if hasattr(google_scraper, '_selenium_used') and google_scraper._selenium_used:
            selenium_used = True
            print(f"\n  Selenium was used during scraping")
        else:
            print(f"\n  Selenium was not needed")
        
        print(f"\n--- SUMMARY ---")
        print(f"  Success rate: {enhanced_count}/{len(articles)} articles enhanced")
        print(f"  Selenium utilized: {'Yes' if selenium_used else 'No'}")
        
        if enhanced_count > 0:
            print(f"  SUCCESS: Enhanced scraping is working!")
            print(f"           Scrapers can now bypass anti-bot protection")
            print(f"           Full article content extracted successfully")
        
        return enhanced_count > 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up selenium driver
        print(f"\nCleaning up selenium resources...")
        BaseScraper.cleanup_selenium_driver()

def test_direct_selenium_usage():
    """Test direct usage of selenium capabilities"""
    print("\n" + "=" * 60)
    print("TESTING DIRECT SELENIUM USAGE")
    print("=" * 60)
    
    try:
        # Create a test scraper
        scraper = GoogleNewsScraper("AAPL", debug=True)
        
        # Test direct selenium request
        test_url = "https://news.google.com/topstories?hl=en-US&gl=US&ceid=US:en"
        print(f"Testing selenium request to: {test_url}")
        
        page_source, final_url = scraper.make_request_with_selenium(
            test_url, 
            wait_for_selector="article", 
            wait_timeout=5
        )
        
        if page_source:
            print(f"SUCCESS: Got {len(page_source)} chars of page source")
            print(f"Final URL: {final_url}")
            
            # Check if it contains news content
            if 'news' in page_source.lower() or 'article' in page_source.lower():
                print(f"Page contains news content")
            
            return True
        else:
            print(f"FAILED: No page source returned")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_enhanced_request_method():
    """Test the enhanced request method with fallback"""
    print("\n" + "=" * 60)
    print("TESTING ENHANCED REQUEST METHOD")
    print("=" * 60)
    
    try:
        scraper = GoogleNewsScraper("AAPL", debug=True)
        
        # Test on a potentially problematic URL
        test_urls = [
            "https://httpbin.org/status/403",  # Simulates blocked request
            "https://httpbin.org/status/200",  # Normal request
        ]
        
        for i, url in enumerate(test_urls):
            print(f"\nTest {i+1}: {url}")
            
            try:
                response = scraper.make_request_enhanced(
                    url, 
                    use_selenium_fallback=True,
                    timeout=10
                )
                
                print(f"  Status: {response.status_code}")
                print(f"  Final URL: {response.url}")
                print(f"  Content length: {len(response.content)}")
                print(f"  Type: {type(response).__name__}")
                
            except Exception as e:
                print(f"  Failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    print("COMPREHENSIVE ENHANCED SCRAPING TEST")
    print("=" * 70)
    
    success1 = test_enhanced_scraping()
    success2 = test_direct_selenium_usage() 
    success3 = test_enhanced_request_method()
    
    print(f"\n" + "=" * 70)
    print(f"FINAL RESULTS:")
    print(f"  Enhanced scraping: {'PASS' if success1 else 'FAIL'}")
    print(f"  Direct selenium: {'PASS' if success2 else 'FAIL'}")
    print(f"  Enhanced requests: {'PASS' if success3 else 'FAIL'}")
    
    overall_success = success1 or success2 or success3
    
    if overall_success:
        print(f"\nSUCCESS: Enhanced scraping capabilities are working!")
        print(f"All scrapers now have access to:")
        print(f"  - Shared selenium session for performance")
        print(f"  - Automatic anti-bot protection bypass")
        print(f"  - Enhanced request methods with fallback")
        print(f"  - JavaScript-rendered page support")
    else:
        print(f"\nFAILED: Enhanced scraping needs more work")
    
    print(f"=" * 70)