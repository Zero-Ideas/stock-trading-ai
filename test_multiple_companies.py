#!/usr/bin/env python3
"""
Test sentiment analysis with multiple companies to reproduce Selenium hanging
"""

import time
import subprocess
import threading
from datetime import datetime

def test_company(symbol, timeout_seconds=180):
    """Test sentiment analysis for a specific company with timeout"""
    print(f"\n{'='*50}")
    print(f"Testing {symbol} - Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*50}")
    
    start_time = time.time()
    
    try:
        # Run sentiment analysis with timeout
        cmd = f'python -c "from sentiment import StockSentimentAnalyzer; analyzer = StockSentimentAnalyzer(\'{symbol}\'); results = analyzer.analyze_sentiment(target_articles=30); print(f\'SUCCESS: {symbol} completed with {{results.get(\\\"total_articles\\\", 0)}} articles\')"'
        
        process = subprocess.Popen(
            cmd, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            cwd=r"C:\Users\ethan\Desktop\stock trading ai"
        )
        
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        end_time = time.time()
        duration = end_time - start_time
        
        if process.returncode == 0:
            print(f"✅ {symbol} SUCCESS ({duration:.1f}s)")
            if "SUCCESS:" in stdout:
                print(f"   {stdout.strip().split('SUCCESS:')[-1]}")
            return True, duration, "success"
        else:
            print(f"❌ {symbol} FAILED ({duration:.1f}s)")
            print(f"   Error: {stderr.strip()[:200]}...")
            return False, duration, "failed"
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {symbol} TIMEOUT ({timeout_seconds}s) - POTENTIAL SELENIUM HANG!")
        process.kill()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
        return False, timeout_seconds, "timeout"
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"💥 {symbol} ERROR ({duration:.1f}s): {str(e)}")
        return False, duration, "error"

def main():
    """Test multiple companies to find Selenium hanging patterns"""
    companies = ['AAPL', 'TSLA', 'MSFT', 'NVDA', 'GOOGL']
    results = {}
    
    print("Testing Multiple Companies for Selenium Hanging Issues")
    print("=" * 60)
    
    for symbol in companies:
        success, duration, status = test_company(symbol, timeout_seconds=180)
        results[symbol] = {
            'success': success,
            'duration': duration, 
            'status': status
        }
        
        # Short break between tests
        if symbol != companies[-1]:  # Not the last one
            print(f"\nBreak before next test...")
            time.sleep(5)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY - Selenium Hanging Investigation")
    print(f"{'='*60}")
    
    successful = 0
    timeouts = 0
    
    for symbol, result in results.items():
        status_icon = "✅" if result['success'] else ("⏰" if result['status'] == 'timeout' else "❌")
        print(f"{status_icon} {symbol}: {result['status'].upper()} ({result['duration']:.1f}s)")
        
        if result['success']:
            successful += 1
        elif result['status'] == 'timeout':
            timeouts += 1
    
    print(f"\nResults: {successful}/{len(companies)} successful, {timeouts} timeouts")
    
    if timeouts > 0:
        print(f"\n⚠️  SELENIUM HANGING DETECTED in {timeouts} tests!")
        print("Companies with timeouts likely have Selenium driver cleanup issues.")
    else:
        print(f"\n✅ No hanging detected - all tests completed within timeout")
    
    return timeouts == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)