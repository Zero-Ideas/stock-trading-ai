#!/usr/bin/env python3
"""
Quick Batch Runner - Run sentiment analysis on multiple companies
Usage: python run_batch.py [--count N] [--articles N] [--delay N]
"""

import subprocess
import time
import random
import argparse
from datetime import datetime

# Top 50 most popular stocks by market cap and trading volume
COMPANIES = [
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK-A', 'LLY', 'V',
    'JPM', 'UNH', 'XOM', 'MA', 'PG', 'JNJ', 'HD', 'MRK', 'CVX', 'ABBV',
    'KO', 'BAC', 'AVGO', 'PEP', 'COST', 'TMO', 'WMT', 'MCD', 'ABT', 'ACN',
    'CSCO', 'DIS', 'AMD', 'DHR', 'VZ', 'ADBE', 'PFE', 'NFLX', 'CRM', 'BMY',
    'TXN', 'RTX', 'PM', 'INTC', 'NKE', 'CMCSA', 'UPS', 'T', 'QCOM', 'MS'
]

def run_single_analysis(symbol, articles=30):
    """Run sentiment analysis for one symbol"""
    print(f"Analyzing {symbol}...", end=' ')
    
    try:
        cmd = f'python sentiment.py {symbol} --articles {articles}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        
        if result.returncode == 0:
            print("✅")
            return True
        else:
            print("❌")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ (timeout)")
        return False
    except Exception as e:
        print(f"💥 ({str(e)[:20]}...)")
        return False

def main():
    parser = argparse.ArgumentParser(description='Run batch sentiment analysis')
    parser.add_argument('--count', type=int, default=10, help='Number of companies to analyze (default: 10)')
    parser.add_argument('--articles', type=int, default=25, help='Articles per company (default: 25)')
    parser.add_argument('--delay', type=int, default=15, help='Delay between companies in seconds (default: 15)')
    
    args = parser.parse_args()
    
    # Select companies to analyze
    companies_to_analyze = COMPANIES[:args.count]
    
    print(f"🚀 Batch Sentiment Analysis")
    print(f"📊 Companies: {args.count}")
    print(f"📰 Articles per company: {args.articles}")
    print(f"⏳ Delay between companies: {args.delay}s")
    print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📋 Companies: {', '.join(companies_to_analyze)}")
    print("-" * 60)
    
    successful = 0
    start_time = time.time()
    
    for i, symbol in enumerate(companies_to_analyze, 1):
        print(f"[{i:2d}/{args.count}] ", end='')
        
        if run_single_analysis(symbol, args.articles):
            successful += 1
        
        # Delay between requests (except for last one)
        if i < len(companies_to_analyze):
            time.sleep(args.delay)
    
    # Summary
    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"✅ Successful: {successful}/{args.count} ({successful/args.count*100:.1f}%)")
    print(f"⏰ Total time: {elapsed/60:.1f} minutes")
    print(f"🏁 Completed: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()