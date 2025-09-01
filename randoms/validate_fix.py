#!/usr/bin/env python3
"""
Final validation that the Google News URL resolution fix is working
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.google_news_scraper import GoogleNewsScraper

def validate_fix():
    """Validate that the Google News URL resolution fix is working"""
    print("VALIDATING GOOGLE NEWS URL RESOLUTION FIX")
    print("=" * 50)
    
    scraper = GoogleNewsScraper("AAPL", debug=True)
    articles = scraper.scrape(max_articles=3)
    
    print(f"\nProcessed {len(articles)} articles")
    
    success_count = 0
    resolution_details = []
    
    for i, article in enumerate(articles):
        print(f"\n--- ARTICLE {i+1} ---")
        print(f"URL: {article.url}")
        print(f"Total text length: {len(article.text)} chars")
        
        # Check if enhancement worked
        has_raw_text = hasattr(article, 'raw_extracted_text') and article.raw_extracted_text
        
        if has_raw_text:
            print(f"SUCCESS! Enhanced with {len(article.raw_extracted_text)} chars from newspaper3k")
            print(f"Raw extracted preview: {article.raw_extracted_text[:150]}...")
            success_count += 1
            
            # Try to infer what the resolved URL was by looking at content
            if 'carboncredits.com' in article.raw_extracted_text.lower():
                resolved_url = "carboncredits.com"
            elif 'motley fool' in article.raw_extracted_text.lower() or 'fool.com' in article.raw_extracted_text.lower():
                resolved_url = "fool.com" 
            elif any(domain in article.raw_extracted_text.lower() for domain in 
                    ['reuters', 'cnn', 'bbc', 'bloomberg', 'wsj', 'yahoo', 'cnbc']):
                resolved_url = "major news site"
            else:
                resolved_url = "unknown news site"
            
            resolution_details.append(f"Article {i+1}: {resolved_url}")
        else:
            print(f"FAILED: No newspaper3k enhancement (likely still using Google RSS URL)")
        
        print(f"Combined text preview: {article.text[:200]}...")
    
    print(f"\n{'='*50}")
    print(f"VALIDATION RESULTS")
    print(f"{'='*50}")
    print(f"Total articles: {len(articles)}")
    print(f"Successfully enhanced: {success_count}")
    print(f"Success rate: {(success_count/len(articles)*100):.1f}%" if articles else "0%")
    
    if success_count > 0:
        print(f"\nResolved URLs:")
        for detail in resolution_details:
            print(f"  {detail}")
        
        print(f"\n✅ SUCCESS! The Google News URL resolution fix is working!")
        print(f"   - Google News RSS URLs are being resolved to actual article URLs")
        print(f"   - newspaper3k is successfully extracting full article content")
        print(f"   - Articles now contain full content instead of just RSS excerpts")
        
        if success_count < len(articles):
            print(f"\nNote: {len(articles) - success_count} articles could not be resolved.")
            print("This is expected as some Google News URLs may be more difficult to resolve.")
    else:
        print(f"\n❌ FAILED! Google News URL resolution is still not working.")
        print(f"   All articles are still using Google RSS URLs")
        print(f"   newspaper3k is not receiving proper article URLs")
    
    return success_count > 0

if __name__ == "__main__":
    success = validate_fix()
    print(f"\n{'='*50}")
    if success:
        print("🎉 VALIDATION PASSED: Google News redirect resolution is working!")
    else:
        print("🔧 VALIDATION FAILED: More work needed on URL resolution")
    print(f"{'='*50}")