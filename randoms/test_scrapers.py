#!/usr/bin/env python3
"""
Test script to evaluate all scrapers' reliability and newspaper3k integration
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, List, Any

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers import AVAILABLE_SCRAPERS

def test_scraper(scraper_name: str, scraper_class, symbol: str = "AAPL", max_articles: int = 5) -> Dict[str, Any]:
    """Test a single scraper and return detailed results"""
    print(f"\n{'='*60}")
    print(f"Testing {scraper_name.upper()} scraper...")
    print(f"{'='*60}")
    
    results = {
        'scraper': scraper_name,
        'success': False,
        'error': None,
        'articles_count': 0,
        'articles': [],
        'avg_text_length': 0,
        'min_text_length': 0,
        'max_text_length': 0,
        'has_urls': False,
        'url_count': 0,
        'enhanced_articles': 0,
        'execution_time': 0
    }
    
    try:
        start_time = time.time()
        
        # Initialize scraper with debug enabled
        scraper = scraper_class(symbol=symbol, debug=True)
        print(f"Scraper initialized for symbol: {symbol}")
        
        # Test scraping
        print(f"Scraping up to {max_articles} articles...")
        articles = scraper.scrape(max_articles=max_articles)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        results['execution_time'] = execution_time
        results['articles_count'] = len(articles)
        results['success'] = True
        
        print(f"Scraped {len(articles)} articles in {execution_time:.2f} seconds")
        
        if articles:
            text_lengths = []
            urls_found = 0
            enhanced_count = 0
            
            for i, article in enumerate(articles):
                article_info = {
                    'index': i + 1,
                    'text_length': len(article.text),
                    'source': article.source,
                    'timestamp': article.timestamp.isoformat() if article.timestamp else None,
                    'has_url': bool(article.url),
                    'url': article.url,
                    'title_preview': article.text[:100] + "..." if len(article.text) > 100 else article.text
                }
                
                results['articles'].append(article_info)
                text_lengths.append(len(article.text))
                
                if article.url:
                    urls_found += 1
                
                # Check if article was enhanced with newspaper3k
                if hasattr(article, 'raw_extracted_text') and article.raw_extracted_text:
                    enhanced_count += 1
                
                print(f"  Article {i+1}: {len(article.text)} chars, URL: {'YES' if article.url else 'NO'}")
                print(f"    Preview: {article.text[:150]}...")
                print(f"    Source: {article.source}")
                print(f"    Timestamp: {article.timestamp}")
                if hasattr(article, 'raw_extracted_text') and article.raw_extracted_text:
                    print(f"    Enhanced: YES ({len(article.raw_extracted_text)} chars raw)")
                print()
            
            results['avg_text_length'] = sum(text_lengths) / len(text_lengths)
            results['min_text_length'] = min(text_lengths)
            results['max_text_length'] = max(text_lengths)
            results['has_urls'] = urls_found > 0
            results['url_count'] = urls_found
            results['enhanced_articles'] = enhanced_count
            
            print(f"STATISTICS:")
            print(f"   Average text length: {results['avg_text_length']:.0f} characters")
            print(f"   Min text length: {results['min_text_length']} characters")
            print(f"   Max text length: {results['max_text_length']} characters")
            print(f"   Articles with URLs: {urls_found}/{len(articles)}")
            print(f"   Enhanced articles: {enhanced_count}/{len(articles)}")
            
        else:
            print("No articles found")
            
    except Exception as e:
        results['error'] = str(e)
        results['success'] = False
        print(f"Error testing {scraper_name}: {e}")
        import traceback
        traceback.print_exc()
    
    return results

def test_newspaper3k_enhancement(symbol: str = "AAPL") -> None:
    """Test newspaper3k enhancement with a sample URL"""
    print(f"\n{'='*60}")
    print("Testing newspaper3k enhancement...")
    print(f"{'='*60}")
    
    try:
        from scrapers.base_scraper import BaseScraper
        
        # Create a test scraper instance
        class TestScraper(BaseScraper):
            @property
            def source_name(self) -> str:
                return "Test"
            
            def scrape(self, max_articles: int = 10):
                return []
        
        scraper = TestScraper(symbol=symbol, debug=True)
        
        # Test URLs from different sources
        test_urls = [
            "https://www.reuters.com/business/healthcare-pharmaceuticals/apple-plans-new-health-features-2024-01-15/",
            "https://www.marketwatch.com/story/apple-stock-rises-ahead-of-earnings-2024-01-15",
            "https://finance.yahoo.com/news/apple-announces-quarterly-results-2024-01-15.html",
        ]
        
        for url in test_urls:
            print(f"\nTesting URL: {url}")
            try:
                content = scraper.fetch_full_article(url, max_length=200000)
                if content:
                    print(f"Extracted {len(content)} characters")
                    print(f"Preview: {content[:200]}...")
                else:
                    print("No content extracted")
            except Exception as e:
                print(f"Error: {e}")
            
            time.sleep(2)  # Rate limiting
            
    except Exception as e:
        print(f"Error testing newspaper3k: {e}")

def main():
    """Main testing function"""
    print("SCRAPER RELIABILITY TEST")
    print("=" * 80)
    
    # Test symbol
    test_symbol = "AAPL"
    max_articles_per_scraper = 5
    
    all_results = []
    
    # Test each scraper
    for scraper_name, scraper_class in AVAILABLE_SCRAPERS.items():
        result = test_scraper(scraper_name, scraper_class, test_symbol, max_articles_per_scraper)
        all_results.append(result)
        
        # Small delay between scrapers to be respectful
        time.sleep(2)
    
    # Test newspaper3k enhancement
    test_newspaper3k_enhancement(test_symbol)
    
    # Summary report
    print(f"\n{'='*80}")
    print("COMPREHENSIVE RESULTS SUMMARY")
    print(f"{'='*80}")
    
    successful_scrapers = [r for r in all_results if r['success']]
    failed_scrapers = [r for r in all_results if not r['success']]
    
    print(f"Successful scrapers: {len(successful_scrapers)}/{len(all_results)}")
    print(f"Failed scrapers: {len(failed_scrapers)}/{len(all_results)}")
    print()
    
    # Performance ranking
    print("SCRAPER PERFORMANCE RANKING:")
    print("-" * 50)
    
    # Sort by article count and average text length
    successful_scrapers.sort(key=lambda x: (x['articles_count'], x['avg_text_length']), reverse=True)
    
    for i, result in enumerate(successful_scrapers):
        rank = i + 1
        scraper_name = result['scraper']
        article_count = result['articles_count']
        avg_length = result['avg_text_length']
        url_count = result['url_count']
        enhanced = result['enhanced_articles']
        exec_time = result['execution_time']
        
        quality_score = article_count * 10 + (avg_length / 100) + (url_count * 5) + (enhanced * 3)
        
        print(f"{rank:2d}. {scraper_name.upper():15} | "
              f"Articles: {article_count:2d} | "
              f"Avg Length: {avg_length:4.0f} | "
              f"URLs: {url_count:2d} | "
              f"Enhanced: {enhanced:2d} | "
              f"Time: {exec_time:5.2f}s | "
              f"Score: {quality_score:6.1f}")
    
    print()
    
    # Problem scrapers
    if failed_scrapers:
        print("PROBLEM SCRAPERS:")
        print("-" * 30)
        for result in failed_scrapers:
            print(f"FAILED {result['scraper'].upper()}: {result['error']}")
        print()
    
    # Low-performing scrapers
    low_performers = [r for r in successful_scrapers if r['articles_count'] < 2 or r['avg_text_length'] < 200]
    if low_performers:
        print("LOW-PERFORMING SCRAPERS (Need Improvement):")
        print("-" * 50)
        for result in low_performers:
            issues = []
            if result['articles_count'] < 2:
                issues.append(f"Low article count ({result['articles_count']})")
            if result['avg_text_length'] < 200:
                issues.append(f"Short articles (avg {result['avg_text_length']:.0f} chars)")
            if result['url_count'] == 0:
                issues.append("No URLs found")
            if result['enhanced_articles'] == 0:
                issues.append("No enhancement")
            
            print(f"NEEDS WORK {result['scraper'].upper():15} | Issues: {', '.join(issues)}")
        print()
    
    # Recommendations
    print("RECOMMENDATIONS:")
    print("-" * 20)
    
    for result in all_results:
        scraper_name = result['scraper']
        
        if not result['success']:
            print(f"FIX {scraper_name.upper()}: Fix critical errors - {result['error']}")
        elif result['articles_count'] == 0:
            print(f"FIX {scraper_name.upper()}: No articles found - check selectors and URLs")
        elif result['articles_count'] < 3:
            print(f"IMPROVE {scraper_name.upper()}: Low yield - improve article detection")
        elif result['avg_text_length'] < 200:
            print(f"ENHANCE {scraper_name.upper()}: Short content - enhance text extraction")
        elif result['url_count'] == 0:
            print(f"ADD URLS {scraper_name.upper()}: Missing URLs - add URL extraction")
        elif result['enhanced_articles'] == 0 and result['url_count'] > 0:
            print(f"USE NEWSPAPER3K {scraper_name.upper()}: Not using newspaper3k - add enhancement")
        else:
            print(f"GOOD {scraper_name.upper()}: Performing well")

if __name__ == "__main__":
    main()