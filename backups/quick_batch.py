#!/usr/bin/env python3
"""
Quick runner for 50 companies - just run this script!
"""
import subprocess
import time

# 50 companies
companies = ['AAPL','MSFT','NVDA','GOOGL','AMZN','META','TSLA',"QCOM"]

print(f"Running sentiment analysis on {len(companies)} companies...")
print("This will take about 1-2 hours depending on your connection.")
print("Files will be saved in the Data/ folder.")

successful = 0
for i, symbol in enumerate(companies, 1):
    print(f"\n[{i:2d}/50] {symbol}...", end=' ')
    try:
        result = subprocess.run(f'python sentiment.py {symbol} --articles 100', 
                              shell=True, capture_output=True, timeout=120)
        if result.returncode == 0:
            print("✅")
            successful += 1
        else:
            print("❌")
    except:
        print("⏰")
    
    # Brief pause between requests
    if i < len(companies):
        time.sleep(1)

print(f"\n🏁 Done! Successfully analyzed {successful}/50 companies.")
print("Check the Data/ folder for all the JSON files.")