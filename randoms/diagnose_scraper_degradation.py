#!/usr/bin/env python3
"""
Diagnose Scraper Performance Degradation
Compares current scraping performance vs historical success to identify issues
"""

import json
from datetime import datetime
from sentiment import StockSentimentAnalyzer
import time

def load_historical_data():
    """Load historical successful analysis for comparison"""
    try:
        with open(r'C:\Users\ethan\Desktop\stock trading ai\Data\sentiment_analysis_AAPL_20250901_131914.json', 'r', encoding='utf-8') as f:
            historical_data = json.load(f)
        
        print("=== Historical Success (Sept 1st) ===")
        print(f"Total articles: {historical_data['total_articles']}")
        print("Source breakdown:")
        for source, data in historical_data['source_breakdown'].items():
            print(f"  - {source}: {data['count']} articles")
        print(f"Raw articles available: {len(historical_data['raw_articles'])}")
        print()
        
        return historical_data
    except Exception as e:
        print(f"Could not load historical data: {e}")
        return None

def test_current_scraping_performance():
    """Test current scraping performance"""
    print("=== Current Scraping Test ===")
    print("Testing individual scrapers to identify failures...")
    print()
    
    # Test with database disabled to focus purely on scraping
    analyzer = StockSentimentAnalyzer("AAPL", use_database=False)
    
    scraper_results = {}
    total_articles = 0
    
    # Test each scraper individually
    for scraper_name, scraper in analyzer.scrapers.items():
        print(f"Testing {scraper_name} ({scraper.source_name})...")
        
        try:
            start_time = time.time()
            articles = scraper.scrape(max_articles=15)  # Test with moderate target
            elapsed = time.time() - start_time
            
            article_count = len(articles) if articles else 0
            total_articles += article_count
            
            scraper_results[scraper_name] = {
                "success": article_count > 0,
                "count": article_count,
                "elapsed": elapsed,
                "source_name": scraper.source_name
            }
            
            if articles:
                print(f"  [SUCCESS] {article_count} articles in {elapsed:.1f}s")
                # Show sample
                sample = articles[0]
                print(f"    Sample: '{sample.text[:60]}...'")
                print(f"    URL: {sample.url}")
                
                # Check for newspaper3k enhancement
                enhanced = hasattr(sample, 'raw_extracted_text') and sample.raw_extracted_text
                if enhanced:
                    print(f"    Enhanced: +{len(sample.raw_extracted_text)} chars from newspaper3k")
            else:
                print(f"  [FAILED] No articles returned")
                
        except Exception as e:
            error_msg = str(e)[:100]
            scraper_results[scraper_name] = {
                "success": False,
                "count": 0,
                "elapsed": 0,
                "error": error_msg,
                "source_name": scraper.source_name
            }
            
            # Identify error type
            if "429" in error_msg or "Too Many Requests" in error_msg:
                print(f"  [RATE LIMITED] {error_msg}")
            elif "403" in error_msg or "Forbidden" in error_msg:
                print(f"  [BLOCKED] Anti-bot protection: {error_msg}")
            elif "timeout" in error_msg.lower():
                print(f"  [TIMEOUT] Network timeout: {error_msg}")
            else:
                print(f"  [ERROR] {error_msg}")
        
        print()
        time.sleep(1)  # Small delay between scraper tests
    
    print(f"Total articles from individual tests: {total_articles}")
    print()
    
    return scraper_results, total_articles

def test_full_analysis():
    """Test full sentiment analysis process"""
    print("=== Full Analysis Test ===")
    print("Running complete analysis to see final article count...")
    print()
    
    try:
        analyzer = StockSentimentAnalyzer("AAPL", use_database=False)
        
        start_time = time.time()
        all_sentiments = analyzer.get_comprehensive_sentiment(target_articles=20)
        elapsed = time.time() - start_time
        
        print(f"Full analysis completed in {elapsed:.1f}s")
        print(f"Final article count: {len(all_sentiments)}")
        
        if all_sentiments:
            # Source breakdown
            sources = {}
            for sentiment in all_sentiments:
                source = sentiment.source
                sources[source] = sources.get(source, 0) + 1
            
            print("Final source breakdown:")
            for source, count in sorted(sources.items()):
                print(f"  - {source}: {count} articles")
        
        return len(all_sentiments)
        
    except Exception as e:
        print(f"Full analysis failed: {e}")
        return 0

def analyze_degradation(historical_data, scraper_results, current_total):
    """Analyze the performance degradation"""
    print("=== Performance Degradation Analysis ===")
    
    if historical_data:
        historical_total = historical_data['total_articles']
        print(f"Historical performance (Sept 1): {historical_total} articles")
        print(f"Current performance: {current_total} articles")
        print(f"Degradation: {historical_total - current_total} articles lost ({((historical_total - current_total) / historical_total * 100):.1f}% reduction)")
        print()
        
        # Compare source performance
        print("Source-by-source comparison:")
        historical_sources = historical_data['source_breakdown']
        
        for scraper_name, result in scraper_results.items():
            source_name = result['source_name']
            current_count = result['count']
            
            # Find historical count for this source
            historical_count = 0
            for hist_source, hist_data in historical_sources.items():
                if source_name in hist_source or hist_source in source_name:
                    historical_count = hist_data['count']
                    break
            
            if historical_count > 0:
                change = current_count - historical_count
                if change < 0:
                    print(f"  {source_name}: {historical_count} -> {current_count} ({change} articles lost)")
                elif change > 0:
                    print(f"  {source_name}: {historical_count} -> {current_count} (+{change} articles gained)")
                else:
                    print(f"  {source_name}: {historical_count} -> {current_count} (no change)")
            else:
                print(f"  {source_name}: NEW -> {current_count} articles")
    
    print()
    
    # Identify failed scrapers
    failed_scrapers = [name for name, result in scraper_results.items() if not result['success']]
    working_scrapers = [name for name, result in scraper_results.items() if result['success']]
    
    print("Scraper Status:")
    print(f"  Working scrapers: {len(working_scrapers)}/{len(scraper_results)}")
    for name in working_scrapers:
        result = scraper_results[name]
        print(f"    - {result['source_name']}: {result['count']} articles")
    
    if failed_scrapers:
        print(f"  Failed scrapers: {len(failed_scrapers)}")
        for name in failed_scrapers:
            result = scraper_results[name]
            error = result.get('error', 'Unknown error')
            print(f"    - {result['source_name']}: {error}")

def main():
    """Main diagnostic function"""
    print("=== Scraper Performance Degradation Diagnosis ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load historical success data
    historical_data = load_historical_data()
    
    # Test current scraping performance
    scraper_results, individual_total = test_current_scraping_performance()
    
    # Test full analysis
    current_total = test_full_analysis()
    
    # Analyze degradation
    analyze_degradation(historical_data, scraper_results, current_total)
    
    print("=== Recommendations ===")
    if current_total < 10:
        print("CRITICAL: Severe scraping degradation detected")
        print("  - Multiple scrapers are failing due to rate limiting or anti-bot protection")
        print("  - Consider using proxy rotation or VPN")
        print("  - Try running analysis during off-peak hours")
        print("  - Check for scraper code updates or anti-bot countermeasures")
    elif current_total < historical_data['total_articles'] * 0.7:
        print("WARNING: Significant performance reduction")
        print("  - Some key scrapers are underperforming")
        print("  - Monitor for specific error patterns")
        print("  - Consider implementing exponential backoff for failed requests")
    else:
        print("NORMAL: Performance within acceptable range")

if __name__ == "__main__":
    main()