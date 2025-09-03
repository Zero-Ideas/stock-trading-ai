#!/usr/bin/env python3
"""
Quick test script to verify the implemented improvements work across different stock symbols
"""

import time
import json
from sentiment import StockSentimentAnalyzer

def test_stock_symbols():
    """Test the improvements with different stock symbols"""
    test_symbols = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL']
    results = {}
    
    print("Testing sentiment analysis improvements with different stocks...")
    print("=" * 60)
    
    for symbol in test_symbols:
        print(f"\n[*] Testing {symbol}...")
        start_time = time.time()
        
        try:
            analyzer = StockSentimentAnalyzer(symbol)
            # Test with smaller article count for quick validation
            result = analyzer.analyze_sentiment(target_articles=20)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Extract key metrics
            results[symbol] = {
                'success': True,
                'total_articles': result.get('total_articles', 0),
                'processing_time': round(processing_time, 2),
                'overall_sentiment': result.get('overall_sentiment', 'Unknown'),
                'working_sources': len([s for s in result.get('source_breakdown', {}).values() if s['count'] > 0])
            }
            
            print(f"[+] {symbol}: {result['total_articles']} articles in {processing_time:.1f}s")
            print(f"    Sentiment: {result['overall_sentiment']}")
            print(f"    Working sources: {results[symbol]['working_sources']}")
            
        except Exception as e:
            end_time = time.time()
            processing_time = end_time - start_time
            
            results[symbol] = {
                'success': False,
                'error': str(e),
                'processing_time': round(processing_time, 2)
            }
            
            print(f"[-] {symbol}: FAILED after {processing_time:.1f}s")
            print(f"   Error: {str(e)[:100]}")
    
    # Summary
    print("\n" + "=" * 60)
    print("IMPROVEMENT TEST SUMMARY:")
    print("=" * 60)
    
    successful_tests = sum(1 for r in results.values() if r['success'])
    total_tests = len(results)
    
    print(f"Success Rate: {successful_tests}/{total_tests} ({(successful_tests/total_tests*100):.1f}%)")
    
    if successful_tests > 0:
        avg_articles = sum(r['total_articles'] for r in results.values() if r['success']) / successful_tests
        avg_time = sum(r['processing_time'] for r in results.values() if r['success']) / successful_tests
        
        print(f"Average Articles: {avg_articles:.1f}")
        print(f"Average Time: {avg_time:.1f}s")
    
    # Show URL resolution stats
    from scrapers.base_scraper import BaseScraper
    url_stats = BaseScraper.get_url_resolution_stats()
    if url_stats:
        print(f"\nURL RESOLUTION PERFORMANCE:")
        for source, stats in url_stats.items():
            status = "DISABLED" if stats['disabled'] else "ACTIVE"
            print(f"  {source}: {stats['success_rate']:.1f}% ({stats['successes']}/{stats['attempts']}) - {status}")
    
    return results

if __name__ == "__main__":
    test_results = test_stock_symbols()
    
    # Save results
    with open('test_results.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\nTest results saved to test_results.json")