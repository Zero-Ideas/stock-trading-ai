#!/usr/bin/env python3
"""
Test Selenium-based article enhancement for blocked sites
"""

from scrapers.base_scraper import SentimentData
from scrapers.marketwatch_scraper import MarketWatchScraper
from datetime import datetime

def test_selenium_enhancement():
    """Test Selenium fallback for article enhancement"""
    print("=== Testing Selenium Article Enhancement ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Create a test scraper
    scraper = MarketWatchScraper("NVDA", debug=True)
    
    # Test URLs that were blocked for newspaper3k
    test_urls = [
        "https://www.marketwatch.com/investing/stock/nvda",
        "https://www.bloomberg.com/quote/NVDA:US",
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"Test {i}: Testing Selenium enhancement on {url}")
        try:
            # Create a mock article with the blocked URL
            article = SentimentData(
                text="Test article for enhancement",
                source="Test",
                timestamp=datetime.now(),
                polarity=0.0,
                compound=0.0,
                url=url
            )
            
            print(f"   Original text length: {len(article.text)}")
            
            # Try the new Selenium fallback enhancement
            enhanced_text = scraper._extract_with_selenium_fallback(url, 2000)
            
            if enhanced_text:
                print(f"   ✓ Selenium enhancement SUCCESS!")
                print(f"   ✓ Enhanced text length: {len(enhanced_text)}")
                print(f"   ✓ Preview: {enhanced_text[:200]}...")
            else:
                print(f"   ✗ Selenium enhancement failed - no content")
                
        except Exception as e:
            print(f"   ✗ Test {i} failed: {e}")
        
        print()

def main():
    """Main test function"""
    print("Testing Selenium fallback for newspaper3k blocked sites")
    print("This should help extract content from MarketWatch, Bloomberg, etc.")
    print()
    
    test_selenium_enhancement()
    
    print("=== SUMMARY ===")
    print("If Selenium enhancement worked, the scrapers should now extract")
    print("meaningful content from previously blocked sites like:")
    print("• MarketWatch (was getting 401 errors)")  
    print("• Bloomberg (was getting 403 errors)")
    print("• Seeking Alpha (was getting 403 errors)")

if __name__ == "__main__":
    main()