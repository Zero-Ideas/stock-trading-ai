#!/usr/bin/env python3
"""
Test Improved Scraping Performance
Tests the fixes made to restore normal article collection
"""

from sentiment import StockSentimentAnalyzer
from datetime import datetime
import json

def test_improved_scraping():
    """Test scraping with improved retry logic and delays"""
    print("=== Testing Improved Scraping Performance ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("Improvements implemented:")
    print("  - Increased retries from 2 to 3 attempts")
    print("  - Added exponential backoff for rate limits (2s, 6s, 18s)")
    print("  - Reduced concurrent workers from 6 to 4")
    print("  - Added 0.5s staggered delays between scraper starts")
    print("  - Increased timeout from 45s to 90s")
    print("  - Enhanced error categorization and logging")
    print()
    
    # Test with a symbol that should have fewer cached articles
    test_symbol = "GOOGL"
    
    print(f"Testing sentiment analysis for {test_symbol}...")
    print("Target: 25 articles (should get more than the previous ~5)")
    print()
    
    try:
        # Create analyzer (with database to save results)
        analyzer = StockSentimentAnalyzer(test_symbol, use_database=True)
        
        start_time = datetime.now()
        
        # Run analysis with improved scrapers
        results = analyzer.analyze_sentiment(target_articles=25, force_refresh=True)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n=== Results After {duration:.1f} seconds ===")
        print(f"Total articles collected: {results['total_articles']}")
        print(f"Overall sentiment: {results['overall_sentiment']}")
        
        # Check if we improved from ~5 to 14+ articles
        if results['total_articles'] >= 14:
            print(f"✅ SUCCESS: Restored to historical performance level (14+ articles)")
        elif results['total_articles'] >= 10:
            print(f"⚠️ IMPROVED: Better than before but still below optimal ({results['total_articles']} articles)")
        else:
            print(f"❌ LIMITED: Still experiencing significant scraping issues ({results['total_articles']} articles)")
        
        print(f"\nSource breakdown:")
        for source, data in results['source_breakdown'].items():
            print(f"  - {source}: {data['count']} articles (avg sentiment: {data['avg_sentiment']:.3f})")
        
        print(f"\nSentiment distribution:")
        print(f"  - Positive: {results['sentiment_distribution']['positive_percentage']:.1f}%")
        print(f"  - Negative: {results['sentiment_distribution']['negative_percentage']:.1f}%")
        print(f"  - Neutral: {results['sentiment_distribution']['neutral_percentage']:.1f}%")
        
        # Show some sample articles
        print(f"\nSample articles:")
        for i, article in enumerate(results['recent_articles'][:3]):
            title = article['text'][:60] + "..." if len(article['text']) > 60 else article['text']
            print(f"  {i+1}. {title} ({article['source']})")
        
        # Verify database storage
        print(f"\nDatabase verification:")
        from core.database import SentimentDatabase
        db = SentimentDatabase()
        stored_articles = db.get_recent_articles_from_db(test_symbol, 50, 1)  # Last 1 hour
        print(f"Articles stored in {test_symbol.lower()} table: {len(stored_articles)}")
        
        if len(stored_articles) == results['total_articles']:
            print("✅ Database storage working correctly - all articles saved")
        else:
            print(f"⚠️ Storage mismatch: {results['total_articles']} collected vs {len(stored_articles)} stored")
        
        return results['total_articles']
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    """Main test function"""
    article_count = test_improved_scraping()
    
    print(f"\n=== Summary ===")
    print(f"Article collection: {article_count} articles")
    
    if article_count >= 14:
        print("🎉 Scraping performance restored to historical levels!")
        print("The database was working correctly - the issue was scraper reliability.")
    elif article_count >= 8:
        print("📈 Scraping performance improved but may need further optimization")
        print("Consider running during off-peak hours for better results.")
    else:
        print("⚠️ Scraping still experiencing issues")
        print("Rate limiting and anti-bot measures are still affecting performance.")
        print("Consider:")
        print("  - Using proxy rotation")
        print("  - Running analysis during off-peak hours (late night/early morning)")
        print("  - Waiting 24 hours for rate limits to reset")

if __name__ == "__main__":
    main()