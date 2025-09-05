#!/usr/bin/env python3
"""
Performance benchmarking script to measure time per article and identify bottlenecks
"""

import time
import statistics
import json
from datetime import datetime
from sentiment import StockSentimentAnalyzer

def benchmark_performance():
    """Benchmark performance and identify bottlenecks"""
    print("Performance Benchmarking - Sentiment Analysis System")
    print("=" * 60)
    
    # Test parameters
    symbol = 'AAPL'
    target_articles = 25
    
    print(f"Test Symbol: {symbol}")
    print(f"Target Articles: {target_articles}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    # Timing variables
    timings = {
        'total_time': 0,
        'scraper_times': {},
        'analysis_time': 0,
        'enhancement_times': [],
        'article_count': 0
    }
    
    start_total = time.time()
    
    try:
        # Initialize analyzer (measure initialization time)
        print("1. Initializing analyzer...")
        init_start = time.time()
        analyzer = StockSentimentAnalyzer(symbol)
        init_time = time.time() - init_start
        print(f"   Initialization: {init_time:.2f}s")
        
        # Run sentiment analysis with detailed timing
        print("\n2. Running sentiment analysis...")
        analysis_start = time.time()
        result = analyzer.analyze_sentiment(target_articles=target_articles)
        analysis_end = time.time()
        
        timings['total_time'] = analysis_end - start_total
        timings['analysis_time'] = analysis_end - analysis_start
        timings['article_count'] = result.get('total_articles', 0)
        
        print(f"   Analysis completed: {timings['analysis_time']:.2f}s")
        print(f"   Articles collected: {timings['article_count']}")
        
        # Calculate performance metrics
        if timings['article_count'] > 0:
            time_per_article = timings['analysis_time'] / timings['article_count']
            articles_per_second = timings['article_count'] / timings['analysis_time']
        else:
            time_per_article = 0
            articles_per_second = 0
        
        print(f"\n3. Performance Metrics:")
        print(f"   Total runtime: {timings['total_time']:.2f}s")
        print(f"   Analysis time: {timings['analysis_time']:.2f}s")
        print(f"   Articles processed: {timings['article_count']}")
        print(f"   Time per article: {time_per_article:.2f}s")
        print(f"   Articles per second: {articles_per_second:.2f}")
        
        # Source breakdown performance
        print(f"\n4. Source Performance:")
        source_breakdown = result.get('source_breakdown', {})
        for source, data in source_breakdown.items():
            count = data.get('count', 0)
            if count > 0:
                efficiency = count / timings['analysis_time'] if timings['analysis_time'] > 0 else 0
                print(f"   {source}: {count} articles ({efficiency:.2f} articles/sec)")
        
        # URL Resolution Statistics
        from scrapers.base_scraper import BaseScraper
        url_stats = BaseScraper.get_url_resolution_stats()
        if url_stats:
            print(f"\n5. URL Resolution Performance:")
            for source, stats in url_stats.items():
                success_rate = stats['success_rate']
                attempts = stats['attempts']
                successes = stats['successes']
                status = "DISABLED" if stats['disabled'] else "ACTIVE"
                
                if attempts > 0:
                    avg_time_per_attempt = timings['analysis_time'] / attempts if attempts > 0 else 0
                    print(f"   {source}: {success_rate:.1f}% success ({successes}/{attempts}) - {status}")
                    print(f"     Est. time per attempt: {avg_time_per_attempt:.2f}s")
        
        # Enhancement statistics
        print(f"\n6. Article Enhancement Performance:")
        enhanced_count = sum(1 for s in result.get('source_breakdown', {}).values() 
                           if s.get('enhanced', 0) > 0)
        print(f"   Enhanced articles: {enhanced_count}")
        
        if timings['article_count'] > 0:
            enhancement_rate = enhanced_count / timings['article_count'] * 100
            print(f"   Enhancement rate: {enhancement_rate:.1f}%")
        
        # Bottleneck identification
        print(f"\n7. Bottleneck Analysis:")
        
        if time_per_article > 3.0:
            print("   ⚠️  HIGH: Time per article > 3s - Consider reducing scraper timeouts")
        elif time_per_article > 2.0:
            print("   ⚡ MEDIUM: Time per article > 2s - Performance acceptable")
        else:
            print("   ✅ LOW: Time per article < 2s - Good performance")
        
        if articles_per_second < 0.5:
            print("   ⚠️  LOW throughput: < 0.5 articles/sec - Check network or scraper efficiency")
        elif articles_per_second < 1.0:
            print("   ⚡ MEDIUM throughput: < 1 article/sec - Consider parallel optimization")
        else:
            print("   ✅ GOOD throughput: > 1 article/sec - Efficient processing")
        
        # Recommendations
        print(f"\n8. Performance Recommendations:")
        
        working_sources = len([s for s in source_breakdown.values() if s.get('count', 0) > 0])
        total_sources = len(source_breakdown)
        
        if working_sources < total_sources * 0.7:
            print("   • Consider investigating failed sources or implementing fallbacks")
        
        if url_stats:
            low_success_sources = [name for name, stats in url_stats.items() 
                                 if stats['success_rate'] < 50 and stats['attempts'] > 5]
            if low_success_sources:
                print(f"   • Investigate low success rate sources: {', '.join(low_success_sources)}")
        
        if time_per_article > 2.5:
            print("   • Consider reducing request timeouts or implementing better caching")
        
        if timings['article_count'] < target_articles * 0.8:
            print(f"   • Article collection below target ({timings['article_count']}/{target_articles})")
        
        # Save benchmark results
        benchmark_data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'target_articles': target_articles,
            'collected_articles': timings['article_count'],
            'total_time': timings['total_time'],
            'analysis_time': timings['analysis_time'],
            'time_per_article': time_per_article,
            'articles_per_second': articles_per_second,
            'working_sources': working_sources,
            'total_sources': total_sources,
            'url_resolution_stats': url_stats,
            'source_breakdown': source_breakdown
        }
        
        with open('benchmark_results.json', 'w') as f:
            json.dump(benchmark_data, f, indent=2)
        
        print(f"\n9. Results saved to benchmark_results.json")
        print(f"\nBenchmark completed successfully!")
        
        return True
        
    except Exception as e:
        end_time = time.time()
        total_time = end_time - start_total
        
        print(f"\nBenchmark failed after {total_time:.1f}s")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = benchmark_performance()
    print(f"\nBenchmark {'COMPLETED' if success else 'FAILED'}")