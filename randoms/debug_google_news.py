#!/usr/bin/env python3
"""
Debug Google News URL resolution to see what's happening with redirects
"""

import time
from scrapers.google_news_scraper import GoogleNewsScraper
from scrapers.base_scraper import BaseScraper

def debug_google_news():
    """Debug Google News URL resolution"""
    print("Debugging Google News URL Resolution")
    print("=" * 50)
    
    # Enable debug mode
    scraper = GoogleNewsScraper('AAPL', debug=True)
    
    print("1. Getting Google News articles...")
    articles = scraper.scrape(max_articles=5)
    
    print(f"\nFound {len(articles)} articles")
    
    for i, article in enumerate(articles, 1):
        print(f"\n--- Article {i} ---")
        print(f"Title: {article.text[:100]}...")
        print(f"Original URL: {article.url}")
        print(f"URL length: {len(article.url) if article.url else 0}")
        print(f"Text length: {len(article.text)}")
        print(f"Has raw_extracted_text: {hasattr(article, 'raw_extracted_text') and bool(article.raw_extracted_text)}")
        
        if hasattr(article, 'raw_extracted_text') and article.raw_extracted_text:
            print(f"Extracted text length: {len(article.raw_extracted_text)}")
            print(f"First 100 chars: {article.raw_extracted_text[:100]}...")
        
        # Test URL resolution manually
        if article.url and 'google.com' in article.url:
            print(f"\n[DEBUG] Testing URL resolution for Google News URL...")
            print(f"Google URL: {article.url}")
            
            # Track resolution attempt
            BaseScraper.track_url_resolution_attempt("Google News Debug")
            
            resolved_url = scraper._resolve_google_news_url(article.url)
            if resolved_url and resolved_url != article.url:
                print(f"✅ Resolved to: {resolved_url}")
                BaseScraper.track_url_resolution_success("Google News Debug")
                
                # Test newspaper3k on resolved URL
                print(f"[DEBUG] Testing newspaper3k on resolved URL...")
                full_text = scraper.fetch_full_article(resolved_url)
                if full_text:
                    print(f"✅ newspaper3k extracted {len(full_text)} characters")
                    print(f"Sample: {full_text[:200]}...")
                else:
                    print(f"❌ newspaper3k failed to extract content")
            else:
                print(f"❌ URL resolution failed")
                
                # Try selenium approach directly
                print(f"[DEBUG] Testing direct selenium approach...")
                page_source, final_url = scraper.make_request_with_selenium(
                    article.url, 
                    wait_for_selector="body",
                    wait_timeout=10
                )
                
                if page_source and final_url:
                    print(f"✅ Selenium got page: {len(page_source)} chars, final URL: {final_url}")
                    if final_url != article.url and 'google.com' not in final_url:
                        print(f"✅ Selenium successfully redirected!")
                        
                        # Test newspaper3k on selenium result
                        full_text = scraper.fetch_full_article(final_url)
                        if full_text:
                            print(f"✅ newspaper3k on selenium URL: {len(full_text)} chars")
                        else:
                            print(f"❌ newspaper3k failed on selenium URL")
                    else:
                        print(f"❌ Selenium didn't redirect properly")
                else:
                    print(f"❌ Selenium failed")
    
    # Show URL resolution stats
    print(f"\n--- URL Resolution Statistics ---")
    stats = BaseScraper.get_url_resolution_stats()
    for source, data in stats.items():
        print(f"{source}: {data['success_rate']:.1f}% ({data['successes']}/{data['attempts']})")

if __name__ == "__main__":
    debug_google_news()