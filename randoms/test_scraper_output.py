#!/usr/bin/env python3
"""
Test Scraper Output
Tests what each scraper is actually returning to identify the source of article limitation
"""

from sentiment import StockSentimentAnalyzer
import time

def test_individual_scrapers():
    """Test each scraper individually to see output"""
    print("=== Individual Scraper Test ===")
    print("Testing what each scraper returns for AAPL...")
    print()
    
    # Create analyzer but test scrapers individually
    analyzer = StockSentimentAnalyzer("AAPL", use_database=False)
    
    print(f"Active scrapers: {len(analyzer.scrapers)}")
    for name, scraper in analyzer.scrapers.items():
        print(f"  - {name}: {scraper.source_name}")
    print()
    
    total_articles = 0
    
    for scraper_name, scraper in analyzer.scrapers.items():
        print(f"Testing {scraper_name} ({scraper.source_name})...")
        
        try:
            # Test with small number first
            start_time = time.time()
            articles = scraper.scrape(max_articles=10)
            elapsed = time.time() - start_time
            
            if articles:
                total_articles += len(articles)
                print(f"  ✓ SUCCESS: {len(articles)} articles in {elapsed:.1f}s")
                
                # Show first article
                sample = articles[0]
                print(f"    Sample: '{sample.text[:80]}...'")
                print(f"    Source: '{sample.source}'")
                print(f"    URL: {sample.url}")
                print(f"    Has newspaper3k: {hasattr(sample, 'raw_extracted_text') and sample.raw_extracted_text}")
                
            else:
                print(f"  ✗ FAILED: No articles returned")
                
        except Exception as e:
            print(f"  ✗ ERROR: {str(e)[:100]}")
        
        print()
    
    print(f"Total articles from all scrapers: {total_articles}")
    print()
    
    return total_articles

def test_full_analysis():
    """Test full sentiment analysis process"""
    print("=== Full Analysis Test ===")
    print("Running full sentiment analysis with target 25 articles...")
    print()
    
    analyzer = StockSentimentAnalyzer("AAPL", use_database=False)
    
    try:
        # Get comprehensive sentiment with moderate target
        start_time = time.time()
        all_sentiments = analyzer.get_comprehensive_sentiment(target_articles=25)
        elapsed = time.time() - start_time
        
        print(f"Analysis completed in {elapsed:.1f}s")
        print(f"Total articles collected: {len(all_sentiments)}")
        
        if all_sentiments:
            # Analyze sources
            source_breakdown = {}
            for sentiment in all_sentiments:
                source = sentiment.source
                if source not in source_breakdown:
                    source_breakdown[source] = 0
                source_breakdown[source] += 1
            
            print("Source breakdown:")
            for source, count in source_breakdown.items():
                print(f"  - {source}: {count} articles")
            
            # Show some samples
            print("\nSample articles:")
            for i, sentiment in enumerate(all_sentiments[:3]):
                print(f"  {i+1}. '{sentiment.text[:60]}...' ({sentiment.source})")
        
        return len(all_sentiments)
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    """Main test function"""
    print("=== Scraper Output Analysis ===")
    print("Investigating why only limited articles are being scraped")
    print()
    
    # Test 1: Individual scrapers
    individual_total = test_individual_scrapers()
    
    # Test 2: Full analysis process
    full_total = test_full_analysis()
    
    # Analysis
    print("=== Analysis Summary ===")
    print(f"Individual scraper test total: {individual_total}")
    print(f"Full analysis test total: {full_total}")
    
    if full_total < 15:
        print("\n[ISSUE IDENTIFIED] Low article count suggests:")
        print("  - Scrapers may be hitting rate limits or anti-bot protection")
        print("  - Some scrapers may be disabled due to low success rates")
        print("  - Network/timeout issues preventing article collection")
    elif full_total < 25:
        print("\n[PARTIAL SUCCESS] Moderate article count suggests:")
        print("  - Some scrapers working, others may have issues")
        print("  - Duplicate removal may be reducing final count")
        print("  - Some sources may be slower or less reliable")
    else:
        print("\n[SUCCESS] Good article count - system working as expected")
    
    print("\nTo address article count issues:")
    print("  1. Check scraper logs for specific error messages")
    print("  2. Consider running with longer timeout periods")
    print("  3. Verify internet connectivity to news sources")
    print("  4. Check if any sources have implemented new anti-bot measures")

if __name__ == "__main__":
    main()