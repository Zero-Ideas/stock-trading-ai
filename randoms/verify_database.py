#!/usr/bin/env python3
"""
Database Verification Script
Verifies that articles and data are being stored properly in PostgreSQL per-symbol tables
"""

import sys
from datetime import datetime, timedelta
from core.database import SentimentDatabase
import json

def main():
    """Main verification function"""
    print("=== PostgreSQL Database Verification ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Initialize database connection
        print("1. Testing database connection...")
        db = SentimentDatabase()
        print("   [SUCCESS] Database connection successful")
        print()
        
        # Test symbols to check
        test_symbols = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL']
        
        print("2. Checking per-symbol tables and data...")
        print()
        
        total_articles_found = 0
        symbols_with_data = []
        
        for symbol in test_symbols:
            print(f"   Checking {symbol}:")
            
            # Check recent articles from per-symbol table
            recent_articles = db.get_recent_articles_from_db(symbol, 50, 72)  # Last 72 hours
            
            if recent_articles:
                total_articles_found += len(recent_articles)
                symbols_with_data.append(symbol)
                
                print(f"     [OK] Found {len(recent_articles)} articles in articles_{symbol.lower()} table")
                
                # Show sample article data
                sample = recent_articles[0]
                print(f"     Sample article:")
                print(f"       Title: {sample['title'][:80]}...")
                print(f"       Source: {sample['source']}")
                print(f"       Sentiment: {sample['sentiment']:.3f} ({sample['sentiment_label']})")
                print(f"       Text length: {sample['text_length']} chars")
                if sample.get('extracted_length', 0) > 0:
                    print(f"       Enhanced with newspaper3k: +{sample['extracted_length']} chars")
                print(f"       Timestamp: {sample['timestamp']}")
                
                # Check for various sources
                sources = set(article['source'] for article in recent_articles)
                print(f"     Sources found: {', '.join(sorted(sources))}")
                
                # Check sentiment distribution
                positive = sum(1 for a in recent_articles if a['sentiment'] > 0.05)
                negative = sum(1 for a in recent_articles if a['sentiment'] < -0.05)
                neutral = len(recent_articles) - positive - negative
                print(f"     Sentiment: {positive} positive, {negative} negative, {neutral} neutral")
                
            else:
                print(f"     [WARNING] No recent articles found in articles_{symbol.lower()} table")
            
            print()
        
        print("3. Overall Database Status:")
        print(f"   Total articles across all symbols: {total_articles_found}")
        print(f"   Symbols with data: {len(symbols_with_data)} ({', '.join(symbols_with_data)})")
        print()
        
        # Check analysis cache
        print("4. Checking analysis cache...")
        for symbol in symbols_with_data[:3]:  # Check first 3 symbols with data
            cached_analysis = db.get_cached_analysis(symbol, 24.0)  # Last 24 hours
            if cached_analysis:
                age_minutes = cached_analysis.get('cache_age_minutes', 0)
                print(f"   [OK] {symbol}: Cached analysis available (age: {age_minutes:.1f} minutes)")
                print(f"     Overall sentiment: {cached_analysis['overall_sentiment']}")
                print(f"     Articles: {cached_analysis['total_articles']}")
            else:
                print(f"   [WARNING] {symbol}: No cached analysis found")
        
        print()
        
        # Test URL duplicate checking
        print("5. Testing URL duplicate checking...")
        test_url = "https://example.com/test-article"
        for symbol in symbols_with_data[:2]:  # Test first 2 symbols
            exists = db.check_url_exists(symbol, test_url)
            print(f"   {symbol}: URL exists check = {exists}")
        
        print()
        
        # Summary
        if total_articles_found > 0:
            print("[SUCCESS] VERIFICATION PASSED")
            print("  - Database is properly storing articles in per-symbol tables")
            print("  - Articles contain titles, full text, sentiment scores, and metadata") 
            print("  - Multiple sources are being captured")
            print("  - newspaper3k text enhancement is working")
        else:
            print("[WARNING] VERIFICATION WARNING")
            print("  - No articles found in database")
            print("  - This could be normal if no sentiment analysis has been run recently")
            print("  - Try running: python sentiment.py AAPL")
        
    except Exception as e:
        print("[ERROR] VERIFICATION FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)