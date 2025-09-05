#!/usr/bin/env python3
"""
Test QCOM with mock data to show exact data flow without scraper rate limiting
"""

from sentiment import StockSentimentAnalyzer
from core.database import SentimentDatabase
from scrapers.base_scraper import SentimentData
from datetime import datetime, timedelta
import random

def create_mock_sentiment_data(count=8):
    """Create mock sentiment data like scrapers would return"""
    mock_articles = []
    sources = ["Google News", "NewsAPI", "Yahoo Finance", "Bloomberg", "MarketWatch"]
    
    titles = [
        "QCOM reports strong quarterly earnings beating expectations",
        "Qualcomm faces regulatory challenges in China market",
        "QCOM stock rises on 5G technology leadership news",
        "Analysts upgrade Qualcomm to buy rating",
        "Qualcomm announces new chip architecture breakthrough",
        "QCOM dividend increase signals confidence in growth",
        "Qualcomm partners with major automotive companies",
        "QCOM stock volatile amid semiconductor sector concerns"
    ]
    
    for i in range(count):
        timestamp = datetime.now() - timedelta(hours=random.randint(1, 12))
        sentiment_score = random.uniform(-0.6, 0.8)
        
        mock_article = SentimentData(
            text=titles[i % len(titles)] + f" Full article content would be here for article {i+1}. This represents the extracted text from the news source with relevant information about Qualcomm's business performance and market position.",
            source=sources[i % len(sources)],
            timestamp=timestamp,
            polarity=sentiment_score * 0.8,  # Slightly different from compound
            compound=sentiment_score,
            url=f"https://mock-news.com/qcom/article-{i+1}"
        )
        
        # Add newspaper3k enhancement to some articles
        if i % 3 == 0:
            mock_article.raw_extracted_text = f"Enhanced content from newspaper3k for article {i+1}. This would include additional paragraphs, quotes, and detailed information that was extracted from the full web page beyond the initial snippet."
        
        mock_articles.append(mock_article)
    
    return mock_articles

class MockStockSentimentAnalyzer(StockSentimentAnalyzer):
    """Analyzer that uses mock data instead of real scrapers"""
    
    def get_comprehensive_sentiment(self, target_articles: int = 50):
        """Override to return mock data instead of scraping"""
        print(f"[MOCK] Creating {min(target_articles, 12)} mock sentiment articles...")
        
        # Create mock articles (simulate what scrapers would return)
        mock_count = min(target_articles, 12)  # Limit to reasonable number for testing
        mock_sentiments = create_mock_sentiment_data(mock_count)
        
        print(f"[MOCK] Created {len(mock_sentiments)} mock articles")
        
        # Show what mock data looks like
        print(f"[MOCK] Sample mock articles:")
        for i, sentiment in enumerate(mock_sentiments[:3]):
            print(f"[MOCK]   {i+1}. {sentiment.text[:60]}... ({sentiment.source})")
        
        # Call parent's processing logic (which will save to database)
        return super().get_comprehensive_sentiment(target_articles)

def test_qcom_mock_data():
    """Test QCOM with mock data to show exact data flow"""
    print("=== QCOM Mock Data Flow Test ===")
    print("This bypasses scraper rate limiting to show the actual data flow")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check existing QCOM data
    db = SentimentDatabase()
    existing_articles = db.get_recent_articles_from_db('QCOM', 50, 24)
    print(f"Existing QCOM articles in database: {len(existing_articles)}")
    
    # Create mock analyzer
    print("\nCreating MockStockSentimentAnalyzer for QCOM...")
    analyzer = MockStockSentimentAnalyzer("QCOM", use_database=True)
    
    # Override the get_comprehensive_sentiment to return mock data
    original_method = analyzer.get_comprehensive_sentiment
    
    def mock_comprehensive_sentiment(target_articles: int = 50):
        print(f"\n[MOCK] get_comprehensive_sentiment called with target: {target_articles}")
        
        # Create mock articles
        mock_count = min(target_articles, 10)  # Create 10 mock articles
        mock_sentiments = create_mock_sentiment_data(mock_count)
        
        print(f"[MOCK] Created {len(mock_sentiments)} mock articles to simulate scraper output")
        
        # Show the mock data that would normally come from scrapers
        print(f"[MOCK] Mock articles created:")
        for i, sentiment in enumerate(mock_sentiments):
            print(f"[MOCK]   Article {i+1}: {sentiment.text[:50]}... ({sentiment.source})")
        
        # Now continue with the normal processing (remove duplicates, save to DB, etc.)
        # This simulates what would happen after scrapers return data
        
        # Remove duplicates (using parent's method)
        unique_sentiments = analyzer._remove_duplicates(mock_sentiments)
        print(f"[MOCK] After duplicate removal: {len(unique_sentiments)} articles")
        
        # The rest of the debug output will come from the modified sentiment.py code
        # This simulates the exact same flow but with controlled mock data
        
        return unique_sentiments
    
    # Replace method temporarily
    analyzer.get_comprehensive_sentiment = mock_comprehensive_sentiment
    
    # Run analysis
    print(f"\nRunning analyze_sentiment with mock data...")
    print("=" * 60)
    
    try:
        results = analyzer.analyze_sentiment(target_articles=10, force_refresh=True)
        
        print("=" * 60)
        print("\n=== MOCK ANALYSIS RESULTS ===")
        
        if "error" not in results:
            print(f"Symbol: {results['symbol']}")
            print(f"Total articles: {results['total_articles']}")
            print(f"Recent articles count: {len(results['recent_articles'])}")
            print(f"Raw articles count: {len(results['raw_articles'])}")
            
            print(f"\nSource breakdown from analysis:")
            for source, data in results['source_breakdown'].items():
                print(f"  - {source}: {data['count']} articles")
            
            # Verify database
            print(f"\nDatabase verification:")
            final_articles = db.get_recent_articles_from_db('QCOM', 50, 1)  # Last hour
            print(f"Articles in QCOM table: {len(final_articles)}")
            
            if final_articles:
                db_sources = {}
                for article in final_articles:
                    source = article['source']
                    db_sources[source] = db_sources.get(source, 0) + 1
                
                print(f"Database source breakdown:")
                for source, count in db_sources.items():
                    print(f"  - {source}: {count} articles")
            
            # Compare results
            print(f"\n=== DATA FLOW VERIFICATION ===")
            print(f"Results total_articles: {results['total_articles']}")
            print(f"Results raw_articles: {len(results['raw_articles'])}")
            print(f"Database articles: {len(final_articles)}")
            
            if results['total_articles'] == len(results['raw_articles']) == len(final_articles):
                print("SUCCESS: All counts match - data flow is working correctly!")
            else:
                print("MISMATCH: Data is being lost somewhere in the flow")
                
        else:
            print(f"Analysis error: {results['error']}")
        
        return results
        
    except Exception as e:
        print(f"Mock test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_qcom_mock_data()
    print(f"\nCheck the 'articles_qcom' table in pgAdmin4 to verify the saved data")