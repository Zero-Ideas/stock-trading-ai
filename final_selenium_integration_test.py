#!/usr/bin/env python3
"""
Final test to validate the complete selenium integration
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.google_news_scraper import GoogleNewsScraper
from scrapers.base_scraper import BaseScraper, SELENIUM_AVAILABLE

def test_selenium_integration():
    """Test the complete selenium integration"""
    print("FINAL SELENIUM INTEGRATION TEST")
    print("=" * 50)
    
    print(f"1. Checking selenium availability...")
    print(f"   Selenium available: {SELENIUM_AVAILABLE}")
    print(f"   BaseScraper has selenium methods: {hasattr(BaseScraper, 'get_selenium_driver')}")
    print(f"   BaseScraper has enhanced requests: {hasattr(BaseScraper, 'make_request_enhanced')}")
    
    if not SELENIUM_AVAILABLE:
        print("   WARNING: Selenium not available - some features will be limited")
        return False
    
    print(f"\n2. Testing Google News scraper with selenium integration...")
    
    try:
        scraper = GoogleNewsScraper("AAPL", debug=True)
        
        print(f"   Scraper created successfully")
        print(f"   Has enhanced capabilities: {hasattr(scraper, 'make_request_enhanced')}")
        
        # Test with a small number of articles
        print(f"\n   Testing scraping with 1 article...")
        articles = scraper.scrape(max_articles=1)
        
        if articles:
            article = articles[0]
            print(f"   SUCCESS: Got article with {len(article.text)} characters")
            print(f"   URL: {article.url[:80]}...")
            
            # Check if enhancement worked
            if hasattr(article, 'raw_extracted_text') and article.raw_extracted_text:
                print(f"   ENHANCEMENT: Successfully extracted {len(article.raw_extracted_text)} chars")
                print(f"   This indicates selenium URL resolution is working!")
                return True
            else:
                print(f"   No enhancement detected")
                return False
        else:
            print(f"   No articles found")
            return False
            
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print(f"\n3. Cleaning up selenium resources...")
        try:
            BaseScraper.cleanup_selenium_driver()
            print(f"   Cleanup successful")
        except Exception as e:
            print(f"   Cleanup warning: {e}")

def test_shared_selenium_session():
    """Test that selenium session is properly shared"""
    print(f"\n" + "=" * 50)
    print("TESTING SHARED SELENIUM SESSION")
    print("=" * 50)
    
    if not SELENIUM_AVAILABLE:
        print("Selenium not available, skipping test")
        return False
    
    try:
        print("1. Creating multiple scraper instances...")
        scraper1 = GoogleNewsScraper("AAPL", debug=False)
        scraper2 = GoogleNewsScraper("MSFT", debug=False) 
        
        print("2. Getting selenium driver from first scraper...")
        driver1 = scraper1.get_selenium_driver()
        print(f"   Driver 1 ID: {id(driver1)}")
        
        print("3. Getting selenium driver from second scraper...")
        driver2 = scraper2.get_selenium_driver()
        print(f"   Driver 2 ID: {id(driver2)}")
        
        if driver1 is driver2:
            print("   SUCCESS: Same driver instance shared between scrapers!")
            return True
        else:
            print("   FAILED: Different driver instances created")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    
    finally:
        BaseScraper.cleanup_selenium_driver()

def main():
    """Run all integration tests"""
    print("COMPREHENSIVE SELENIUM INTEGRATION VALIDATION")
    print("=" * 70)
    
    # Test 1: Basic integration
    success1 = test_selenium_integration()
    
    # Test 2: Shared session
    success2 = test_shared_selenium_session()
    
    # Summary
    print(f"\n" + "=" * 70)
    print("FINAL VALIDATION RESULTS")
    print("=" * 70)
    print(f"Basic selenium integration: {'PASS' if success1 else 'FAIL'}")
    print(f"Shared session management: {'PASS' if success2 else 'FAIL'}")
    
    overall_success = success1 and success2
    
    if overall_success:
        print(f"\n✅ SUCCESS! Selenium integration is fully functional!")
        print(f"\nKey capabilities now available to ALL scrapers:")
        print(f"  • Shared selenium session for performance")
        print(f"  • Automatic anti-bot protection bypass") 
        print(f"  • Enhanced request methods with smart fallback")
        print(f"  • JavaScript-rendered page support")
        print(f"  • Google News URL resolution with selenium")
        print(f"  • Robust error handling and graceful degradation")
        
        print(f"\nUsage in any scraper:")
        print(f"  response = self.make_request_enhanced(url)")
        print(f"  # Automatically uses selenium if blocked!")
        
    else:
        print(f"\n❌ INTEGRATION ISSUES DETECTED")
        print(f"Please check selenium installation and ChromeDriver")
    
    print(f"=" * 70)
    return overall_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)