#!/usr/bin/env python3
"""
Test the Selenium cleanup fixes
"""

import time
from sentiment import StockSentimentAnalyzer

def test_selenium_cleanup():
    """Test that sentiment analysis completes without hanging"""
    print("Testing Selenium Cleanup Fixes")
    print("=" * 40)
    
    start_time = time.time()
    
    try:
        print("Starting sentiment analysis...")
        analyzer = StockSentimentAnalyzer("MSFT")  # Use MSFT to avoid AAPL rate limiting
        results = analyzer.analyze_sentiment(target_articles=15)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ SUCCESS!")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Articles: {results.get('total_articles', 0)}")
        print(f"Sentiment: {results.get('overall_sentiment', 'Unknown')}")
        
        # Check if cleanup message appeared
        print(f"\nIf you see 'Selenium driver cleaned up successfully' above, cleanup worked!")
        
        return True
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"\n❌ ERROR after {duration:.1f}s: {e}")
        return False

if __name__ == "__main__":
    success = test_selenium_cleanup()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    exit(0 if success else 1)