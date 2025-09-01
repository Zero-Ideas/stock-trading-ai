#!/usr/bin/env python3
"""
Quick test of sentiment.py with optimized selenium
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sentiment import StockSentimentAnalyzer

def test_sentiment_quick():
    """Quick test with small number of articles"""
    print("QUICK SENTIMENT TEST WITH SELENIUM OPTIMIZATIONS")
    print("=" * 60)
    
    try:
        analyzer = StockSentimentAnalyzer("AAPL")
        print(f"Analyzer created for {analyzer.symbol}")
        print(f"Company name: {analyzer.company_name}")
        
        # Run with very small number to test quickly
        print("\nRunning sentiment analysis with 5 articles...")
        results = analyzer.analyze_sentiment(target_articles=5)
        
        print(f"\nRESULTS:")
        print(f"  Total articles: {results.get('total_articles', 0)}")
        print(f"  Overall sentiment: {results.get('overall_sentiment', 'N/A')}")
        print(f"  Average compound: {results.get('sentiment_scores', {}).get('average_compound', 0):.4f}")
        
        if 'source_breakdown' in results:
            print(f"  Sources used:")
            for source, data in results['source_breakdown'].items():
                print(f"    {source}: {data.get('count', 0)} articles")
        
        print(f"\n✅ SUCCESS: sentiment.py working with selenium optimizations")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sentiment_quick()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")