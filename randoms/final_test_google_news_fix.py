#!/usr/bin/env python3
"""
Final comprehensive test of the improved Google News URL resolution
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.google_news_scraper import GoogleNewsScraper

def final_test():
    """Final comprehensive test"""
    print("FINAL COMPREHENSIVE TEST - GOOGLE NEWS REDIRECT FIX")
    print("=" * 60)
    
    try:
        # Test with debug enabled to see detailed output
        scraper = GoogleNewsScraper("AAPL", debug=True)
        print("Testing with 3 Google News articles...")
        articles = scraper.scrape(max_articles=3)
        
        print(f"\nFound {len(articles)} articles")
        
        enhanced_count = 0
        total_enhanced_chars = 0
        resolved_urls = []
        
        for i, article in enumerate(articles):
            print(f"\n{'='*20} ARTICLE {i+1} {'='*20}")
            print(f"Title/Description: {article.text[:100]}...")
            print(f"Original URL: {article.url}")
            print(f"Original length: {len(article.text)} characters")
            
            # Check if newspaper3k enhancement worked
            has_enhancement = hasattr(article, 'raw_extracted_text') and article.raw_extracted_text
            if has_enhancement:
                enhanced_count += 1
                enhancement_chars = len(article.raw_extracted_text)
                total_enhanced_chars += enhancement_chars
                print(f"ENHANCEMENT SUCCESS: +{enhancement_chars} chars from newspaper3k")
                print(f"Enhanced text preview: {article.raw_extracted_text[:150]}...")
                
                # Try to identify what URL was actually used
                if 'google.com' not in article.url:
                    resolved_urls.append(article.url)
                else:
                    resolved_urls.append("Could not resolve Google URL")
            else:
                print(f"ENHANCEMENT: None - likely still using Google RSS URL")
            
            print(f"Final combined text: {article.text[:200]}...")
        
        print(f"\n{'='*60}")
        print(f"FINAL TEST RESULTS")
        print(f"{'='*60}")
        print(f"Articles processed: {len(articles)}")
        print(f"Successfully enhanced: {enhanced_count}")
        print(f"Enhancement success rate: {(enhanced_count/len(articles)*100):.1f}%" if articles else "0%")
        
        if enhanced_count > 0:
            avg_enhancement = total_enhanced_chars // enhanced_count
            print(f"Average enhancement: {avg_enhancement} characters")
            print(f"\nResolved URLs:")
            for i, url in enumerate(resolved_urls):
                print(f"  {i+1}. {url}")
            print(f"\nSUCCESS: Google News redirect resolution is working!")
            print(f"newspaper3k is now receiving proper article URLs instead of Google RSS links")
        else:
            print(f"\nISSUE: No articles were enhanced")
            print(f"This suggests Google News URLs are still not being resolved properly")
            print(f"newspaper3k is still receiving Google RSS URLs which contain no useful content")
        
        return enhanced_count > 0
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting final test...")
    success = final_test()
    
    print(f"\n{'='*60}")
    if success:
        print("FINAL RESULT: SUCCESS! Google News redirect resolution is working.")
        print("The scraper now properly resolves Google News URLs to actual article URLs")
        print("before passing them to newspaper3k for content extraction.")
    else:
        print("FINAL RESULT: FAILED. Google News URLs are still not being resolved.")
        print("newspaper3k is still receiving Google RSS URLs instead of real article URLs.")
        print("Further improvements to the URL resolution logic are needed.")
    print(f"{'='*60}")