#!/usr/bin/env python3
"""
Test the fixed Google News URL resolution
"""

import time
from scrapers.google_news_scraper import GoogleNewsScraper
from scrapers.base_scraper import BaseScraper

def test_google_news_fix():
    """Test Google News URL resolution fix"""
    print("Testing Google News URL Resolution Fix")
    print("=" * 50)
    
    # Enable debug mode
    scraper = GoogleNewsScraper('AAPL', debug=True)
    
    print("1. Testing with 3 articles...")
    articles = scraper.scrape(max_articles=3)
    
    print(f"\nFound {len(articles)} articles")
    
    success_count = 0
    enhanced_count = 0
    
    for i, article in enumerate(articles, 1):
        print(f"\n--- Article {i} ---")
        print(f"Title: {article.text[:80]}...")
        print(f"Original URL: {article.url[:80]}...")
        
        if article.url and 'google.com' in article.url:
            print("Google News URL detected - testing resolution...")
            
            # Test resolution
            resolved_url = scraper._resolve_google_news_url(article.url)
            if resolved_url and resolved_url != article.url and 'google.com' not in resolved_url:
                print(f"✅ Resolved to: {resolved_url[:80]}...")
                success_count += 1
                
                # Test newspaper3k enhancement
                full_text = scraper.fetch_full_article(resolved_url)
                if full_text and len(full_text) > len(article.text):
                    print(f"✅ Enhanced with newspaper3k: {len(full_text)} chars")
                    enhanced_count += 1
                else:
                    print(f"❌ newspaper3k failed or didn't improve content")
            else:
                print(f"❌ Resolution failed")
        else:
            print("Not a Google News URL")
    
    # Show results
    print(f"\n--- RESULTS ---")
    print(f"Articles processed: {len(articles)}")
    print(f"Google URLs resolved: {success_count}")
    print(f"Articles enhanced: {enhanced_count}")
    
    # Show URL resolution stats
    stats = BaseScraper.get_url_resolution_stats()
    if stats:
        print(f"\nURL Resolution Stats:")
        for source, data in stats.items():
            if data['attempts'] > 0:
                print(f"  {source}: {data['success_rate']:.1f}% ({data['successes']}/{data['attempts']})")
    
    return success_count > 0

if __name__ == "__main__":
    success = test_google_news_fix()
    print(f"\nTest {'PASSED' if success else 'FAILED'} - Google News resolution {'working' if success else 'not working'}")