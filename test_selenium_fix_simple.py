#!/usr/bin/env python3
"""
Simple test for Selenium cleanup fixes (no Unicode issues)
"""

import time
from sentiment import StockSentimentAnalyzer

def test_simple():
    """Simple test without Unicode"""
    print("Testing Selenium Cleanup - Simple Test")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        print("Starting TSLA sentiment analysis...")
        analyzer = StockSentimentAnalyzer("TSLA")
        results = analyzer.analyze_sentiment(target_articles=10)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\nSUCCESS!")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Articles: {results.get('total_articles', 0)}")
        
        return True
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"\nERROR after {duration:.1f}s: {e}")
        return False

if __name__ == "__main__":
    success = test_simple()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")
    print("Check above for 'Selenium driver cleaned up successfully' message")