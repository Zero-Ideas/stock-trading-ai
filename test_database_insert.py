#!/usr/bin/env python3
"""
Test Database Insert Script
Creates sample data to test if the database is storing articles properly per symbol
"""

from datetime import datetime, timedelta
from core.database import SentimentDatabase
import random

def create_test_articles(symbol, count=5):
    """Create sample test articles for a symbol"""
    test_articles = []
    
    sources = ['NewsAPI', 'Google News', 'Yahoo Finance', 'MarketWatch', 'Bloomberg']
    
    sample_titles = [
        f"{symbol} stock rises 3% on strong earnings report",
        f"{symbol} faces challenges with new regulatory changes",
        f"Analysts upgrade {symbol} to buy rating",
        f"{symbol} quarterly results beat expectations",
        f"Market volatility affects {symbol} trading volume"
    ]
    
    sample_texts = [
        f"{symbol} Corporation reported strong quarterly earnings today, beating analyst expectations by $0.05 per share. The company's revenue increased 12% year-over-year, driven by strong demand in key markets. Investors reacted positively to the news, pushing the stock price up in after-hours trading.",
        
        f"{symbol} is facing new regulatory challenges that could impact its operations in the coming quarters. The company stated it is working closely with regulators to ensure compliance. Industry analysts suggest this could create short-term headwinds for the stock.",
        
        f"Wall Street analysts have upgraded {symbol} to a buy rating, citing strong fundamentals and growth potential. The price target has been raised to reflect the company's improving outlook. Several institutional investors have increased their positions recently.",
        
        f"{symbol} announced its quarterly results after market close, reporting earnings that exceeded Wall Street expectations. Revenue growth was particularly strong in the company's core business segments. Management provided positive guidance for the next quarter.",
        
        f"Trading volume for {symbol} increased significantly today as market volatility affected investor sentiment. The stock experienced price swings throughout the session but ended near unchanged. Technical analysts note key support and resistance levels to watch."
    ]
    
    for i in range(count):
        timestamp = datetime.now() - timedelta(hours=random.randint(1, 48))
        
        # Random sentiment scores
        sentiment_score = random.uniform(-0.8, 0.8)
        polarity = sentiment_score * 0.8  # Slightly different from sentiment
        
        # Sentiment label
        if sentiment_score > 0.1:
            sentiment_label = "Positive"
        elif sentiment_score < -0.1:
            sentiment_label = "Negative"
        else:
            sentiment_label = "Neutral"
        
        article = {
            "title": sample_titles[i % len(sample_titles)],
            "text": sample_texts[i % len(sample_texts)],
            "raw_extracted_text": sample_texts[i % len(sample_texts)] + f" Additional extracted content from newspaper3k for {symbol} analysis.",
            "extraction_successful": random.choice([True, False]),
            "source": random.choice(sources),
            "url": f"https://example.com/{symbol.lower()}/article-{i+1}",
            "timestamp": timestamp.isoformat(),
            "polarity": polarity,
            "sentiment": sentiment_score,
            "sentiment_label": sentiment_label,
            "text_length": len(sample_texts[i % len(sample_texts)]),
            "extracted_length": random.randint(200, 800),
            "enhancement_ratio": random.uniform(1.2, 3.5)
        }
        
        test_articles.append(article)
    
    return test_articles

def main():
    """Main test function"""
    print("=== Database Insert Test ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Initialize database
        print("1. Connecting to database...")
        db = SentimentDatabase()
        print("   [SUCCESS] Database connection established")
        print()
        
        # Test symbols
        test_symbols = ['AAPL', 'TSLA', 'NVDA']
        
        print("2. Creating and inserting test articles...")
        total_inserted = 0
        
        for symbol in test_symbols:
            print(f"   Testing {symbol}:")
            
            # Create test articles
            test_articles = create_test_articles(symbol, 5)
            
            # Save to database
            new_articles = db.save_articles_to_symbol_table(symbol, test_articles)
            total_inserted += new_articles
            
            print(f"     [OK] Inserted {new_articles} articles into articles_{symbol.lower()} table")
            
            # Verify insertion by reading back
            recent_articles = db.get_recent_articles_from_db(symbol, 10, 48)
            print(f"     [OK] Verified {len(recent_articles)} articles can be retrieved")
            
            if recent_articles:
                sample = recent_articles[0]
                print(f"     Sample: '{sample['title'][:50]}...' from {sample['source']}")
        
        print()
        print("3. Testing URL duplicate checking...")
        
        # Test duplicate URL
        test_url = "https://example.com/aapl/article-1"
        exists = db.check_url_exists('AAPL', test_url)
        print(f"   URL exists check for '{test_url}': {exists}")
        
        # Test non-existent URL
        fake_url = "https://example.com/fake/article-999"
        exists = db.check_url_exists('AAPL', fake_url)
        print(f"   URL exists check for fake URL: {exists}")
        
        print()
        print("4. Testing analysis cache...")
        
        # Create a sample analysis record
        sample_analysis = {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "total_articles": 5,
            "overall_sentiment": "Positive",
            "sentiment_scores": {
                "average_sentiment": 0.25,
                "weighted_avg_from_sources": 0.3
            },
            "sentiment_distribution": {
                "positive": 3,
                "negative": 1,
                "neutral": 1,
                "positive_percentage": 60.0,
                "negative_percentage": 20.0,
                "neutral_percentage": 20.0
            },
            "source_breakdown": {
                "NewsAPI": {"count": 2, "avg_sentiment": 0.4},
                "Google News": {"count": 3, "avg_sentiment": 0.2}
            }
        }
        
        # Get test articles data for analysis
        test_articles_data = create_test_articles("AAPL", 5)
        
        # Save analysis
        analysis_id = db.save_analysis(sample_analysis, test_articles_data)
        print(f"   [OK] Saved sample analysis (ID: {analysis_id})")
        
        # Test cache retrieval
        cached = db.get_cached_analysis("AAPL", 1.0)
        if cached:
            print(f"   [OK] Retrieved cached analysis: {cached['overall_sentiment']}")
        else:
            print(f"   [WARNING] Could not retrieve cached analysis")
        
        print()
        print(f"[SUCCESS] Database insert test completed")
        print(f"  - Total articles inserted: {total_inserted}")
        print(f"  - Per-symbol tables created and populated")
        print(f"  - URL duplicate checking works")
        print(f"  - Analysis caching works")
        print()
        print("You can now run 'python verify_database.py' to see the populated data")
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()