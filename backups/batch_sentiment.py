#!/usr/bin/env python3
"""
Batch Sentiment Analyzer
Runs sentiment analysis on multiple stock symbols automatically.
"""

import subprocess
import time
import random
import os
import sys
from datetime import datetime

# List of 50 popular stock symbols
STOCK_SYMBOLS = [
    # Tech Giants
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'NFLX', 'ORCL', 'CRM',
    # Finance
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA', 'PYPL', 'SQ',
    # Consumer & Retail
    'WMT', 'HD', 'PG', 'KO', 'PEP', 'MCD', 'SBUX', 'NKE', 'DIS', 'TGT',
    # Healthcare & Pharma
    'JNJ', 'PFE', 'ABBV', 'MRK', 'UNH', 'CVS', 'AMGN', 'GILD', 'BMY', 'LLY',
    # Energy & Industrial
    'XOM', 'CVX', 'COP', 'BA', 'CAT', 'MMM', 'GE', 'RTX', 'UPS', 'FDX'
]

def run_sentiment_analysis(symbol, articles=30, delay_range=(10, 30)):
    """Run sentiment analysis for a single symbol"""
    print(f"\n{'='*60}")
    print(f"Starting sentiment analysis for {symbol}")
    print(f"{'='*60}")
    
    try:
        # Run the sentiment analysis
        cmd = [sys.executable, 'sentiment.py', symbol, '--articles', str(articles)]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        end_time = time.time()
        
        if result.returncode == 0:
            print(f"✅ SUCCESS: {symbol} completed in {end_time - start_time:.1f}s")
            return True
        else:
            print(f"❌ FAILED: {symbol}")
            if result.stderr:
                print(f"Error: {result.stderr[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT: {symbol} took too long (>5min)")
        return False
    except Exception as e:
        print(f"💥 ERROR: {symbol} - {str(e)}")
        return False
    finally:
        # Random delay between requests to be polite to servers
        delay = random.uniform(delay_range[0], delay_range[1])
        print(f"⏳ Waiting {delay:.1f}s before next symbol...")
        time.sleep(delay)

def main():
    """Main function to run batch sentiment analysis"""
    print("🚀 Starting Batch Sentiment Analysis")
    print(f"📊 Will analyze {len(STOCK_SYMBOLS)} companies")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create Data directory if it doesn't exist
    os.makedirs('./Data', exist_ok=True)
    
    successful = 0
    failed = 0
    failed_symbols = []
    
    start_time = time.time()
    
    for i, symbol in enumerate(STOCK_SYMBOLS, 1):
        print(f"\n🔄 Progress: {i}/{len(STOCK_SYMBOLS)} ({i/len(STOCK_SYMBOLS)*100:.1f}%)")
        
        success = run_sentiment_analysis(symbol, articles=30)
        
        if success:
            successful += 1
        else:
            failed += 1
            failed_symbols.append(symbol)
        
        # Show running totals
        print(f"📈 Running totals: ✅{successful} ❌{failed}")
        
        # Estimate remaining time
        elapsed = time.time() - start_time
        if i > 0:
            avg_time_per_symbol = elapsed / i
            remaining_symbols = len(STOCK_SYMBOLS) - i
            estimated_remaining = remaining_symbols * avg_time_per_symbol
            print(f"⏱️  Estimated time remaining: {estimated_remaining/60:.1f} minutes")
    
    # Final summary
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print("📋 FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful: {successful}/{len(STOCK_SYMBOLS)} ({successful/len(STOCK_SYMBOLS)*100:.1f}%)")
    print(f"❌ Failed: {failed}/{len(STOCK_SYMBOLS)} ({failed/len(STOCK_SYMBOLS)*100:.1f}%)")
    print(f"⏰ Total time: {total_time/60:.1f} minutes")
    print(f"🏁 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if failed_symbols:
        print(f"\n❌ Failed symbols: {', '.join(failed_symbols)}")
    
    print(f"\n📁 All results saved in the Data/ folder")

if __name__ == "__main__":
    main()