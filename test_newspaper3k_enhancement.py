#!/usr/bin/env python3
"""
Test newspaper3k enhancement on specific sites to debug why it's not working
"""

from scrapers.marketwatch_scraper import MarketWatchScraper
from scrapers.bloomberg_scraper import BloombergScraper
from scrapers.seeking_alpha_scraper import SeekingAlphaScraper
from scrapers.base_scraper import SentimentData
from datetime import datetime

def test_newspaper3k_enhancement():
    """Test newspaper3k enhancement on problematic scrapers"""
    print("=== Testing newspaper3k Enhancement Issues ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test MarketWatch
    print("1. Testing MarketWatch Scraper:")
    try:
        mw_scraper = MarketWatchScraper("NVDA", debug=True)
        mw_articles = mw_scraper.scrape(max_articles=3)
        
        print(f"   Found {len(mw_articles)} MarketWatch articles")
        if mw_articles:
            for i, article in enumerate(mw_articles[:2]):
                print(f"   Article {i+1}:")
                print(f"     Text length: {len(article.text)} chars")
                print(f"     URL: {article.url}")
                print(f"     Text start: {article.text[:100]}...")
                print(f"     Raw enhanced text: {len(article.raw_extracted_text)} chars")
                
                # Test enhancement manually if URL exists
                if article.url:
                    print(f"     Attempting manual enhancement...")
                    try:
                        enhanced = mw_scraper.enhance_article_data(article)
                        print(f"     Enhanced length: {len(enhanced.text)} chars")
                        print(f"     Raw text length: {len(enhanced.raw_extracted_text)} chars")
                    except Exception as e:
                        print(f"     Enhancement failed: {e}")
        else:
            print("   [WARNING] No MarketWatch articles found")
    except Exception as e:
        print(f"   [ERROR] MarketWatch test failed: {e}")
    
    print()
    
    # Test Bloomberg
    print("2. Testing Bloomberg Scraper:")
    try:
        bb_scraper = BloombergScraper("NVDA", debug=True)
        bb_articles = bb_scraper.scrape(max_articles=3)
        
        print(f"   Found {len(bb_articles)} Bloomberg articles")
        if bb_articles:
            for i, article in enumerate(bb_articles[:2]):
                print(f"   Article {i+1}:")
                print(f"     Text length: {len(article.text)} chars")
                print(f"     URL: {article.url}")
                print(f"     Text: {article.text}")
                print(f"     Raw enhanced text: {len(article.raw_extracted_text)} chars")
                
                # Test enhancement manually if URL exists
                if article.url:
                    print(f"     Attempting manual enhancement...")
                    try:
                        enhanced = bb_scraper.enhance_article_data(article)
                        print(f"     Enhanced length: {len(enhanced.text)} chars")
                        print(f"     Raw text length: {len(enhanced.raw_extracted_text)} chars")
                    except Exception as e:
                        print(f"     Enhancement failed: {e}")
        else:
            print("   [WARNING] No Bloomberg articles found")
    except Exception as e:
        print(f"   [ERROR] Bloomberg test failed: {e}")
    
    print()
    
    # Test Seeking Alpha
    print("3. Testing Seeking Alpha Scraper:")
    try:
        sa_scraper = SeekingAlphaScraper("NVDA", debug=True)
        sa_articles = sa_scraper.scrape(max_articles=3)
        
        print(f"   Found {len(sa_articles)} Seeking Alpha articles")
        if sa_articles:
            for i, article in enumerate(sa_articles[:2]):
                print(f"   Article {i+1}:")
                print(f"     Text length: {len(article.text)} chars")
                print(f"     URL: {article.url}")
                print(f"     Text start: {article.text[:100]}...")
                print(f"     Raw enhanced text: {len(article.raw_extracted_text)} chars")
                
                # Test enhancement manually if URL exists
                if article.url:
                    print(f"     Attempting manual enhancement...")
                    try:
                        enhanced = sa_scraper.enhance_article_data(article)
                        print(f"     Enhanced length: {len(enhanced.text)} chars")
                        print(f"     Raw text length: {len(enhanced.raw_extracted_text)} chars")
                    except Exception as e:
                        print(f"     Enhancement failed: {e}")
        else:
            print("   [WARNING] No Seeking Alpha articles found")
    except Exception as e:
        print(f"   [ERROR] Seeking Alpha test failed: {e}")

def test_direct_newspaper3k():
    """Test newspaper3k directly on known URLs"""
    print("\n4. Testing newspaper3k directly on sample URLs:")
    
    test_urls = [
        ("MarketWatch", "https://www.marketwatch.com/story/nvidia-stock-falls-after-earnings-2024-08-28"),
        ("Bloomberg", "https://www.bloomberg.com/news/articles/2024-08-28/nvidia-stock-drops-after-earnings"),
        ("Seeking Alpha", "https://seekingalpha.com/article/4712345-nvidia-corporation-nvda-q2-2024-earnings-call-transcript")
    ]
    
    try:
        from newspaper import Article, Config
        
        config = Config()
        config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        config.request_timeout = 10
        
        for site_name, url in test_urls:
            print(f"\n   Testing {site_name} URL: {url}")
            try:
                article = Article(url, config=config)
                article.download()
                
                print(f"     Download status: {article.download_state}")
                
                article.parse()
                
                print(f"     Title: {article.title}")
                print(f"     Text length: {len(article.text)}")
                print(f"     Authors: {article.authors}")
                
                if len(article.text) > 100:
                    print(f"     Text preview: {article.text[:200]}...")
                    print(f"     [SUCCESS] newspaper3k working for {site_name}")
                else:
                    print(f"     [WARNING] Short or no content extracted from {site_name}")
                    
            except Exception as e:
                print(f"     [ERROR] newspaper3k failed for {site_name}: {e}")
                
    except ImportError:
        print("   [ERROR] newspaper3k not available")

def main():
    """Main test function"""
    print("This script tests why newspaper3k isn't working on certain scrapers")
    print()
    
    test_newspaper3k_enhancement()
    test_direct_newspaper3k()
    
    print(f"\n=== DIAGNOSIS ===")
    print("Possible issues:")
    print("1. URLs not being extracted properly from scraped content")
    print("2. URLs are paywalled or blocked for newspaper3k")
    print("3. newspaper3k timeout or configuration issues")
    print("4. Site anti-bot measures blocking newspaper3k")
    print("5. Enhancement function not being called correctly")

if __name__ == "__main__":
    main()