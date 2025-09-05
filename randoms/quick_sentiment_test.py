#!/usr/bin/env python3
"""
Quick test of sentiment.py with thread safety fixes
"""

if __name__ == "__main__":
    from sentiment import StockSentimentAnalyzer
    
    print("Testing sentiment analysis with thread safety fixes...")
    
    analyzer = StockSentimentAnalyzer("NVDA")  # Use NVDA to avoid AAPL rate limiting
    results = analyzer.analyze_sentiment(target_articles=15)
    
    print(f"SUCCESS: Collected {results.get('total_articles', 0)} articles")
    print(f"Sentiment: {results.get('overall_sentiment', 'Unknown')}")
    print("Check above for 'Selenium driver cleaned up successfully' message")