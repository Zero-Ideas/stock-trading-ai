#!/usr/bin/env python3
"""
Test QCOM with full debugging to see exact data flow
"""

from sentiment import StockSentimentAnalyzer
from core.database import SentimentDatabase
from datetime import datetime
import json

def clear_qcom_data():
    """Clear any existing QCOM data to start fresh"""
    print("=== Clearing QCOM Data for Fresh Test ===")
    
    db = SentimentDatabase()
    
    # Check existing QCOM data
    existing_articles = db.get_recent_articles_from_db('QCOM', 100, 48)
    print(f"Existing QCOM articles: {len(existing_articles)}")
    
    if existing_articles:
        print("Note: There are existing QCOM articles in the database")
        print("This test will add to them (duplicate checking will prevent actual duplicates)")

def test_qcom_with_debug():
    """Test QCOM sentiment analysis with full debugging"""
    print("\n=== QCOM Sentiment Analysis with Debug ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Create analyzer with database enabled
    print("Creating StockSentimentAnalyzer for QCOM...")
    analyzer = StockSentimentAnalyzer("QCOM", use_database=True)
    print(f"Analyzer created - Symbol: {analyzer.symbol}")
    print(f"Database enabled: {analyzer.use_database}")
    print(f"Database object: {analyzer.db is not None}")
    print()
    
    # Run sentiment analysis with target articles
    target_articles = 15
    print(f"Running analyze_sentiment(target_articles={target_articles})...")
    print("=" * 60)
    
    try:
        results = analyzer.analyze_sentiment(target_articles=target_articles, force_refresh=True)
        
        print("=" * 60)
        print("\n=== ANALYSIS COMPLETE - FINAL RESULTS ===")
        
        if "error" in results:
            print(f"ERROR: {results['error']}")
            return results
        
        print(f"Symbol: {results['symbol']}")
        print(f"Total articles: {results['total_articles']}")
        print(f"Overall sentiment: {results['overall_sentiment']}")
        
        print(f"\nSource breakdown:")
        for source, data in results['source_breakdown'].items():
            print(f"  - {source}: {data['count']} articles (avg sentiment: {data['avg_sentiment']:.3f})")
        
        print(f"\nResults structure:")
        print(f"  - total_articles: {results['total_articles']}")
        print(f"  - recent_articles: {len(results['recent_articles'])}")
        print(f"  - raw_articles: {len(results['raw_articles'])}")
        
        # Show sample from each collection
        if results['recent_articles']:
            print(f"\nSample recent_articles:")
            for i, article in enumerate(results['recent_articles'][:3]):
                print(f"  {i+1}. {article['text'][:50]}... ({article['source']})")
        
        if results['raw_articles']:
            print(f"\nSample raw_articles:")
            for i, article in enumerate(results['raw_articles'][:3]):
                print(f"  {i+1}. {article['text'][:50]}... ({article['source']})")
        
        return results
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def verify_qcom_database():
    """Verify what's actually in the QCOM database table"""
    print("\n=== QCOM Database Verification ===")
    
    db = SentimentDatabase()
    
    # Get all QCOM articles
    all_articles = db.get_recent_articles_from_db('QCOM', 100, 24)  # Last 24 hours
    print(f"Total QCOM articles in database: {len(all_articles)}")
    
    if all_articles:
        # Source breakdown
        sources = {}
        for article in all_articles:
            source = article['source']
            sources[source] = sources.get(source, 0) + 1
        
        print(f"Database source breakdown:")
        for source, count in sources.items():
            print(f"  - {source}: {count} articles")
        
        print(f"\nDatabase sample articles:")
        for i, article in enumerate(all_articles[:5]):
            print(f"  {i+1}. {article['title'][:50]}... ({article['source']})")
            print(f"      URL: {article['url']}")
            print(f"      Sentiment: {article['sentiment']:.3f}")
    
    return len(all_articles)

def main():
    """Main test function"""
    print("=== QCOM Data Flow Debug Test ===")
    print("This will show exactly what data flows from scrapers → sentiment.py → database")
    print()
    
    # Clear existing data context
    clear_qcom_data()
    
    # Run analysis with full debugging
    results = test_qcom_with_debug()
    
    # Verify database contents
    db_count = verify_qcom_database()
    
    # Final comparison
    print(f"\n=== FINAL COMPARISON ===")
    if results:
        print(f"Results total_articles: {results['total_articles']}")
        print(f"Results raw_articles: {len(results['raw_articles'])}")
        print(f"Results recent_articles: {len(results['recent_articles'])}")
        print(f"Database articles found: {db_count}")
        
        # Check for alignment
        if results['total_articles'] == len(results['raw_articles']):
            print("✅ total_articles matches raw_articles count")
        else:
            print(f"⚠️ MISMATCH: total_articles ({results['total_articles']}) != raw_articles ({len(results['raw_articles'])})")
        
        if len(results['raw_articles']) == db_count:
            print("✅ raw_articles count matches database count")
        elif db_count > len(results['raw_articles']):
            print(f"ℹ️ Database has more articles ({db_count}) than current analysis ({len(results['raw_articles'])}) - likely from previous runs")
        else:
            print(f"⚠️ DATABASE MISMATCH: Expected {len(results['raw_articles'])} in DB but found {db_count}")
    else:
        print("Analysis failed - no results to compare")
    
    print(f"\nCheck the 'articles_qcom' table in pgAdmin4 to verify these results")

if __name__ == "__main__":
    main()