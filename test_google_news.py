#!/usr/bin/env python3
"""
Test script for Google News newspaper3k enhancement
Focused test to identify why extraction is failing despite finding articles
"""

import sys
import os
sys.path.append('.')

from scrapers import GoogleNewsScraper

def test_google_news_extraction():
    """Test Google News scraper with detailed debugging"""
    print("=== TESTING GOOGLE NEWS EXTRACTION ===\n")
    
    symbol = "AAPL"
    debug = True
    
    # Create scraper with debug enabled
    scraper = GoogleNewsScraper(symbol, debug)
    print(f"Testing Google News scraper for {symbol}\n")
    
    # Test with a small number of articles first
    target_articles = 10
    print(f"Requesting {target_articles} articles...\n")
    
    try:
        results = scraper.scrape(target_articles)
        
        if not results:
            print("No results returned from scraper")
            return
        
        print(f"FOUND {len(results)} articles")
        print(f"Expected newspaper3k enhancement on articles with redirected URLs\n")
        
        # Analyze results in detail
        enhanced_count = 0
        total_original_chars = 0
        total_extracted_chars = 0
        
        for i, article in enumerate(results[:5]):  # Check first 5 articles
            print(f"\n--- ARTICLE {i+1} ---")
            print(f"Title: {article.text[:100]}...")
            print(f"Source: {article.source}")
            print(f"URL: {article.url}")
            print(f"Original text length: {len(article.text)} chars")
            
            # Check for newspaper3k enhancement
            has_extraction = hasattr(article, 'raw_extracted_text') and article.raw_extracted_text
            if has_extraction:
                extracted_length = len(article.raw_extracted_text)
                print(f"ENHANCED with newspaper3k: {extracted_length} chars")
                print(f"Enhancement ratio: {(extracted_length / max(1, len(article.text))) * 100:.1f}%")
                enhanced_count += 1
                total_extracted_chars += extracted_length
            else:
                print(f"NO newspaper3k enhancement")
                print(f"Has raw_extracted_text attr: {hasattr(article, 'raw_extracted_text')}")
                if hasattr(article, 'raw_extracted_text'):
                    print(f"raw_extracted_text content: '{getattr(article, 'raw_extracted_text', 'N/A')[:50]}...'")
            
            total_original_chars += len(article.text)
            
            # Check URL pattern - Google News URLs should be redirects
            if 'news.google.com' in article.url:
                print(f"Google News redirect URL detected")
            else:
                print(f"Direct URL (not Google News redirect): {article.url[:100]}...")
        
        # Summary statistics
        print(f"\n=== EXTRACTION SUMMARY ===")
        print(f"Total articles analyzed: {min(5, len(results))}")
        print(f"Enhanced with newspaper3k: {enhanced_count}")
        print(f"Enhancement rate: {(enhanced_count / min(5, len(results))) * 100:.1f}%")
        if enhanced_count > 0:
            print(f"Average extracted length: {total_extracted_chars // enhanced_count} chars")
        print(f"Average original length: {total_original_chars // min(5, len(results))} chars")
        
        # Test specific URL resolution if we have Google News URLs
        print(f"\n=== URL RESOLUTION TEST ===")
        google_news_urls = [r.url for r in results if 'news.google.com' in r.url]
        if google_news_urls:
            print(f"Found {len(google_news_urls)} Google News redirect URLs")
            
            # Test URL resolution manually
            from scrapers.base_scraper import BaseScraper
            test_url = google_news_urls[0]
            print(f"Testing URL resolution for: {test_url[:100]}...")
            
            try:
                resolved_url, resolved_successfully = BaseScraper.resolve_redirect_url(test_url)
                if resolved_successfully:
                    print(f"URL resolved to: {resolved_url[:100]}...")
                    
                    # Now test newspaper3k extraction
                    print(f"Testing newspaper3k extraction on resolved URL...")
                    extracted_text = BaseScraper.extract_with_newspaper3k(resolved_url)
                    if extracted_text:
                        print(f"newspaper3k extracted {len(extracted_text)} chars")
                        print(f"Sample: {extracted_text[:200]}...")
                    else:
                        print(f"newspaper3k extraction failed")
                else:
                    print(f"URL resolution failed")
            except Exception as e:
                print(f"Error testing URL resolution: {e}")
        else:
            print(f"No Google News redirect URLs found to test")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_google_news_extraction()