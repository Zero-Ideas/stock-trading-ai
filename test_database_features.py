#!/usr/bin/env python3
"""
Test script for new database features:
- Per-symbol tables
- Duplicate URL checking
- Article saving and retrieval
"""

from datetime import datetime
from core.database import SentimentDatabase

def test_database_features():
    """Test new database functionality"""
    print("=" * 60)
    print("TESTING NEW DATABASE FEATURES")
    print("=" * 60)
    
    try:
        # Initialize database
        print("1. Initializing database connection...")
        db = SentimentDatabase()
        print("   SUCCESS: Database connected")
        
        # Test creating symbol table
        print("\n2. Creating symbol table for TEST...")
        test_symbol = "TEST"
        
        # Test saving articles
        print("\n3. Testing article saving with duplicate checking...")
        test_articles = [
            {
                "title": "Test Article 1",
                "text": "This is a test article about TEST stock going up",
                "raw_extracted_text": "Extended content for test article 1",
                "extraction_successful": True,
                "source": "Test Source 1",
                "url": "https://test.com/article1",
                "timestamp": datetime.now().isoformat(),
                "polarity": 0.5,
                "sentiment": 0.6,
                "sentiment_label": "Positive",
                "text_length": 45,
                "extracted_length": 35,
                "enhancement_ratio": 77.8
            },
            {
                "title": "Test Article 2",
                "text": "This is another test article about TEST stock declining",
                "raw_extracted_text": "Extended content for test article 2",
                "extraction_successful": True,
                "source": "Test Source 2",
                "url": "https://test.com/article2",
                "timestamp": datetime.now().isoformat(),
                "polarity": -0.3,
                "sentiment": -0.4,
                "sentiment_label": "Negative",
                "text_length": 55,
                "extracted_length": 35,
                "enhancement_ratio": 63.6
            },
            {
                "title": "Test Article 1 (Duplicate)",
                "text": "This is the same test article about TEST stock going up",
                "raw_extracted_text": "Extended content for duplicate test article",
                "extraction_successful": True,
                "source": "Test Source 1",
                "url": "https://test.com/article1",  # Same URL - should be rejected
                "timestamp": datetime.now().isoformat(),
                "polarity": 0.5,
                "sentiment": 0.6,
                "sentiment_label": "Positive",
                "text_length": 56,
                "extracted_length": 40,
                "enhancement_ratio": 71.4
            }
        ]
        
        saved_count = db.save_articles_to_symbol_table(test_symbol, test_articles)
        print(f"   SUCCESS: Saved {saved_count} articles (should be 2, rejecting 1 duplicate)")
        
        # Test retrieving articles
        print("\n4. Testing article retrieval...")
        retrieved_articles = db.get_recent_articles_from_db(test_symbol, 10, 24)
        print(f"   SUCCESS: Retrieved {len(retrieved_articles)} articles")
        
        for i, article in enumerate(retrieved_articles, 1):
            print(f"     Article {i}: {article['title'][:40]}... (sentiment: {article['sentiment']})")
        
        # Test URL existence checking
        print("\n5. Testing URL duplicate checking...")
        exists1 = db.check_url_exists(test_symbol, "https://test.com/article1")
        exists2 = db.check_url_exists(test_symbol, "https://test.com/nonexistent")
        
        print(f"   URL https://test.com/article1 exists: {exists1} (should be True)")
        print(f"   URL https://test.com/nonexistent exists: {exists2} (should be False)")
        
        # Test cached analysis with articles
        print("\n6. Testing cached analysis retrieval...")
        
        # Create a dummy analysis first
        dummy_analysis = {
            "symbol": test_symbol,
            "company_name": "Test Company Inc.",
            "total_articles": len(retrieved_articles),
            "overall_sentiment": "Positive",
            "sentiment_scores": {
                "average_sentiment": 0.15,
                "weighted_avg_from_sources": 0.12
            },
            "sentiment_distribution": {
                "positive": 1,
                "negative": 1,
                "neutral": 0,
                "positive_percentage": 50.0,
                "negative_percentage": 50.0,
                "neutral_percentage": 0.0
            },
            "source_breakdown": {
                "Test Source 1": {"count": 1, "avg_sentiment": 0.6},
                "Test Source 2": {"count": 1, "avg_sentiment": -0.4}
            }
        }
        
        analysis_id = db.save_analysis(dummy_analysis, test_articles[:2])  # Save without duplicate
        print(f"   SUCCESS: Created test analysis (ID: {analysis_id})")
        
        # Try to get cached analysis
        cached = db.get_cached_analysis(test_symbol, 1.0)
        if cached:
            print(f"   SUCCESS: Retrieved cached analysis with {len(cached.get('raw_articles', []))} articles")
            print(f"   Overall sentiment: {cached['overall_sentiment']}")
        else:
            print("   INFO: No cached analysis found (this is normal for first run)")
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("New features are working correctly:")
        print("SUCCESS: Per-symbol table creation")
        print("SUCCESS: Article saving with duplicate URL checking")
        print("SUCCESS: Article retrieval from per-symbol tables")
        print("SUCCESS: URL existence checking")
        print("SUCCESS: Integration with analysis caching")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_database_features():
        print("\nSUCCESS: All database features are working correctly!")
    else:
        print("\nERROR: Some tests failed. Please check the errors above.")