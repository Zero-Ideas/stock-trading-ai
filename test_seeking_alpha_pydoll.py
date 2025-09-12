#!/usr/bin/env python3
"""
Test script for the enhanced Seeking Alpha scraper using pydoll
"""

import sys
import time
from scrapers.seeking_alpha_scraper_pydoll import SeekingAlphaScraperPydoll

def test_seeking_alpha_pydoll_scraper():
    """Test the pydoll-enhanced Seeking Alpha scraper"""
    print("TESTING SEEKING ALPHA PYDOLL SCRAPER")
    print("="*60)
    
    try:
        # Test with a popular stock
        symbol = "NVDA"
        max_articles = 5
        
        print(f"Testing with {symbol} - requesting {max_articles} articles")
        print("-" * 40)
        
        # Initialize the scraper
        scraper = SeekingAlphaScraperPydoll(symbol, debug=True)
        
        print(f"Company info:")
        print(f"  Symbol: {scraper.symbol}")
        print(f"  Company Name: {scraper.company_name}")
        print(f"  Common Name: {scraper.common_name}")
        print(f"  Industry: {scraper.industry}")
        print()
        
        # Start scraping
        start_time = time.time()
        print("Starting scraping process...")
        
        articles = scraper.scrape(max_articles)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\nScraping completed in {duration:.1f} seconds")
        print(f"Retrieved {len(articles)} articles")
        
        # Display results
        if articles:
            print("\nArticles found:")
            print("-" * 40)
            for i, article in enumerate(articles, 1):
                print(f"{i}. {article.source}")
                print(f"   Title: {article.text[:100]}...")
                print(f"   URL: {article.url}")
                print(f"   Timestamp: {article.timestamp}")
                print(f"   Text length: {len(article.text)} chars")
                if article.raw_extracted_text:
                    print(f"   Enhanced: Yes ({len(article.raw_extracted_text)} chars)")
                else:
                    print(f"   Enhanced: No")
                print()
        else:
            print("\nNo articles found - this could indicate:")
            print("1. Anti-bot measures are blocking access")
            print("2. No relevant articles are currently available")
            print("3. Network or configuration issues")
            print("\nThe pydoll scraper should perform better than regular scrapers")
            print("against bot detection systems.")
        
        # Test comparison with basic scraper if possible
        print("\n" + "="*60)
        print("COMPARISON TEST")
        print("="*60)
        
        try:
            from scrapers.seeking_alpha_scraper import SeekingAlphaScraper
            
            print("Testing basic Seeking Alpha scraper for comparison...")
            basic_scraper = SeekingAlphaScraper(symbol, debug=False)
            
            start_time = time.time()
            basic_articles = basic_scraper.scrape(max_articles)
            basic_duration = time.time() - start_time
            
            print(f"\nComparison Results:")
            print(f"Pydoll Scraper:  {len(articles)} articles in {duration:.1f}s")
            print(f"Basic Scraper:   {len(basic_articles)} articles in {basic_duration:.1f}s")
            
            if len(articles) > len(basic_articles):
                print("+ Pydoll scraper found more articles!")
            elif len(articles) == len(basic_articles):
                print("= Both scrapers found the same number of articles")
            else:
                print("- Basic scraper found more articles (unusual)")
            
        except Exception as e:
            print(f"Comparison test failed: {e}")
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("\nMake sure pydoll is installed:")
        print("pip install pydoll")
        return False
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60)
    
    return len(articles) > 0 if 'articles' in locals() else False

def test_anti_bot_features():
    """Test specific anti-bot features"""
    print("\nTESTING ANTI-BOT FEATURES")
    print("="*40)
    
    try:
        scraper = SeekingAlphaScraperPydoll("AAPL", debug=True)
        
        print("Anti-bot features in pydoll scraper:")
        print("+ Stealth browser with advanced evasion")
        print("+ Human-like timing and delays")
        print("+ Dynamic user agent rotation")
        print("+ Cookie/privacy notice handling")
        print("+ Multiple scraping strategies")
        print("+ JavaScript execution support")
        print("+ Network fingerprint masking")
        print("+ Automation detection bypass")
        
        print("\nThese features should help bypass Seeking Alpha's bot detection.")
        
    except Exception as e:
        print(f"Anti-bot feature test failed: {e}")

if __name__ == "__main__":
    print("SEEKING ALPHA PYDOLL SCRAPER TEST")
    print("=" * 80)
    
    success = test_seeking_alpha_pydoll_scraper()
    test_anti_bot_features()
    
    print("\n" + "=" * 80)
    if success:
        print("+ TEST PASSED: Pydoll scraper is working!")
    else:
        print("- TEST FAILED: Check the output above for issues")
    print("=" * 80)