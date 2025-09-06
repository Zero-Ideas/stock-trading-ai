#!/usr/bin/env python3
"""
Test script for Yahoo Finance newspaper3k enhancement
"""

import sys
import os
sys.path.append('.')

from scrapers import YahooFinanceScraper

def test_yahoo_finance_extraction():
    """Test Yahoo Finance scraper with detailed debugging"""
    print("=== TESTING YAHOO FINANCE EXTRACTION ===\n")
    
    symbol = "AAPL"
    debug = True
    
    # Create scraper with debug enabled
    scraper = YahooFinanceScraper(symbol, debug)
    print(f"Testing Yahoo Finance scraper for {symbol}\n")
    
    # Check if there's a skip_enhancement flag
    if hasattr(scraper, 'skip_enhancement'):
        print(f"skip_enhancement flag: {scraper.skip_enhancement}")
    else:
        print("No skip_enhancement flag found (good - means enhancement should work)")
    
    # Test with a small number of articles first
    target_articles = 8
    print(f"Requesting {target_articles} articles...\n")
    
    try:
        results = scraper.scrape(target_articles)
        
        if not results:
            print("No results returned from scraper")
            return
        
        print(f"FOUND {len(results)} articles")
        print(f"Testing newspaper3k enhancement on Yahoo Finance articles\n")
        
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
                
                # Show sample of extracted text
                sample_text = article.raw_extracted_text[:150].replace('\n', ' ')
                print(f"Sample extracted: {sample_text}...")
            else:
                print(f"NO newspaper3k enhancement")
                print(f"Has raw_extracted_text attr: {hasattr(article, 'raw_extracted_text')}")
                if hasattr(article, 'raw_extracted_text'):
                    raw_content = getattr(article, 'raw_extracted_text', 'N/A')
                    print(f"raw_extracted_text content: '{raw_content[:50]}...'")
            
            total_original_chars += len(article.text)
            
            # Check URL pattern
            if article.url:
                if 'yahoo.com' in article.url:
                    print(f"Yahoo Finance URL detected")
                else:
                    print(f"External URL: {article.url[:100]}...")
            else:
                print(f"No URL available")
        
        # Summary statistics
        print(f"\n=== EXTRACTION SUMMARY ===")
        print(f"Total articles analyzed: {min(5, len(results))}")
        print(f"Enhanced with newspaper3k: {enhanced_count}")
        print(f"Enhancement rate: {(enhanced_count / min(5, len(results))) * 100:.1f}%")
        if enhanced_count > 0:
            print(f"Average extracted length: {total_extracted_chars // enhanced_count} chars")
        print(f"Average original length: {total_original_chars // min(5, len(results))} chars")
        
        # Test specific URL if we have Yahoo Finance URLs
        print(f"\n=== URL ENHANCEMENT TEST ===")
        yahoo_urls = [r.url for r in results if r.url and 'yahoo.com' in r.url]
        if yahoo_urls:
            print(f"Found {len(yahoo_urls)} Yahoo Finance URLs")
            test_url = yahoo_urls[0]
            print(f"Testing newspaper3k extraction for: {test_url[:80]}...")
            
            try:
                from scrapers.base_scraper import BaseScraper
                extracted_text = BaseScraper.extract_with_newspaper3k(test_url)
                if extracted_text:
                    print(f"SUCCESS: newspaper3k extracted {len(extracted_text)} chars")
                    print(f"Sample: {extracted_text[:200]}...")
                else:
                    print(f"FAILED: newspaper3k extraction returned empty")
            except Exception as e:
                print(f"ERROR testing newspaper3k: {e}")
        else:
            print(f"No Yahoo Finance URLs found to test")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_yahoo_finance_extraction()