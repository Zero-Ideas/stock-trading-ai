#!/usr/bin/env python3
"""
Quick test to verify improvements work
"""

import time
from sentiment import StockSentimentAnalyzer

def quick_test():
    """Quick test with AAPL"""
    symbol = 'AAPL'
    print(f"Quick test with {symbol}...")
    print("=" * 40)
    
    start_time = time.time()
    
    try:
        analyzer = StockSentimentAnalyzer(symbol)
        result = analyzer.analyze_sentiment(target_articles=15)  # Small test
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\nRESULT:")
        print(f"  Total articles: {result.get('total_articles', 0)}")
        print(f"  Processing time: {processing_time:.1f}s")
        print(f"  Overall sentiment: {result.get('overall_sentiment', 'Unknown')}")
        print(f"  Working sources: {len([s for s in result.get('source_breakdown', {}).values() if s['count'] > 0])}")
        
        # Show URL resolution stats
        from scrapers.base_scraper import BaseScraper
        url_stats = BaseScraper.get_url_resolution_stats()
        if url_stats:
            print(f"\nURL RESOLUTION STATS:")
            for source, stats in url_stats.items():
                status = "DISABLED" if stats['disabled'] else "ACTIVE"
                print(f"  {source}: {stats['success_rate']:.1f}% ({stats['successes']}/{stats['attempts']}) - {status}")
        
        print("\nTest completed successfully!")
        return True
        
    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"Test failed after {processing_time:.1f}s")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = quick_test()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")