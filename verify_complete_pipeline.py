#!/usr/bin/env python3
"""
Verify the complete Google News → Selenium → newspaper3k pipeline
"""

from scrapers.google_news_scraper import GoogleNewsScraper
from scrapers.base_scraper import BaseScraper

def verify_complete_pipeline():
    """Test the complete pipeline end-to-end"""
    print("Verifying Complete Google News Pipeline")
    print("=" * 50)
    
    scraper = GoogleNewsScraper('AAPL', debug=True)
    
    # Get one Google News article
    print("1. Getting Google News articles...")
    articles = scraper.scrape(max_articles=2)
    
    if not articles:
        print("No articles found!")
        return False
    
    enhanced_count = 0
    
    for i, article in enumerate(articles[:2], 1):
        print(f"\n--- Testing Article {i} ---")
        print(f"Title: {article.text[:100]}...")
        print(f"Original text length: {len(article.text)} chars")
        
        if hasattr(article, 'raw_extracted_text') and article.raw_extracted_text:
            print(f"Enhanced text length: {len(article.raw_extracted_text)} chars")
            print(f"Enhancement ratio: {len(article.raw_extracted_text) / len(article.text):.1f}x")
            enhanced_count += 1
            
            # Show sample of enhanced content
            if len(article.raw_extracted_text) > 500:
                print(f"Enhanced content sample:")
                print(f"  {article.raw_extracted_text[:300]}...")
        else:
            print("No enhancement applied")
    
    # Show URL resolution stats
    stats = BaseScraper.get_url_resolution_stats()
    if stats:
        print(f"\n--- URL Resolution Performance ---")
        for source, data in stats.items():
            if data['attempts'] > 0:
                print(f"{source}: {data['success_rate']:.1f}% success rate ({data['successes']}/{data['attempts']})")
    
    print(f"\n--- PIPELINE VERIFICATION ---")
    print(f"Articles processed: {len(articles)}")
    print(f"Articles enhanced: {enhanced_count}")
    print(f"Enhancement rate: {(enhanced_count/len(articles)*100):.1f}%")
    
    success = enhanced_count > 0
    print(f"Pipeline status: {'WORKING' if success else 'NOT WORKING'}")
    
    return success

if __name__ == "__main__":
    success = verify_complete_pipeline()
    exit(0 if success else 1)