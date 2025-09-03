#!/usr/bin/env python3
"""
Test sentiment.py directly with different companies using subprocess to detect hanging
"""

import subprocess
import time
from datetime import datetime

def test_sentiment_direct(symbol, timeout_seconds=180):
    """Run sentiment.py directly with a specific symbol and detect hanging"""
    print(f"\n{'='*60}")
    print(f"Testing sentiment.py directly with {symbol}")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Timeout: {timeout_seconds} seconds")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Create a modified sentiment.py temporarily for this symbol
        temp_script = f"""
if __name__ == "__main__":
    from sentiment import StockSentimentAnalyzer
    import json
    
    analyzer = StockSentimentAnalyzer("{symbol}")
    results = analyzer.analyze_sentiment(target_articles=100)
    
    print(f"FINAL_RESULT: {{symbol}} completed with {{results.get('total_articles', 0)}} articles")
    print(json.dumps(results, indent=2, default=str))
"""
        
        with open('temp_sentiment_test.py', 'w') as f:
            f.write(temp_script)
        
        # Run the script with timeout
        process = subprocess.Popen(
            ['python', 'temp_sentiment_test.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=r"C:\Users\ethan\Desktop\stock trading ai"
        )
        
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Clean up temp file
        try:
            import os
            os.remove('temp_sentiment_test.py')
        except:
            pass
        
        if process.returncode == 0:
            print(f"✅ {symbol} SUCCESS - Completed in {duration:.1f}s")
            
            # Check for cleanup message
            if "Selenium driver cleaned up successfully" in stdout:
                print("✅ Selenium cleanup detected")
            else:
                print("⚠️  No Selenium cleanup message found")
            
            # Check for completion
            if "FINAL_RESULT:" in stdout:
                result_line = [line for line in stdout.split('\n') if 'FINAL_RESULT:' in line][0]
                print(f"✅ {result_line}")
            
            return True, duration, "success"
        else:
            print(f"❌ {symbol} FAILED - Process returned code {process.returncode}")
            print(f"Error output: {stderr[:300]}...")
            return False, duration, "failed"
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {symbol} TIMEOUT after {timeout_seconds}s - SELENIUM HANGING DETECTED!")
        process.kill()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
        
        # Clean up temp file
        try:
            import os
            os.remove('temp_sentiment_test.py')
        except:
            pass
            
        return False, timeout_seconds, "timeout"
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"💥 {symbol} ERROR after {duration:.1f}s: {e}")
        
        # Clean up temp file
        try:
            import os
            os.remove('temp_sentiment_test.py')
        except:
            pass
            
        return False, duration, "error"

def main():
    """Test sentiment.py directly with multiple companies"""
    companies = ['MSFT', 'NVDA', 'GOOGL']  # Skip AAPL due to rate limiting
    results = {}
    
    print("Testing sentiment.py DIRECTLY for Selenium hanging issues")
    print("This tests the actual script execution, not isolated components")
    
    for symbol in companies:
        success, duration, status = test_sentiment_direct(symbol, timeout_seconds=200)
        results[symbol] = {
            'success': success,
            'duration': duration,
            'status': status
        }
        
        # Break between tests to avoid rate limiting
        if symbol != companies[-1]:
            print(f"\nWaiting 10 seconds before next test...")
            time.sleep(10)
    
    # Summary
    print(f"\n{'='*60}")
    print("DIRECT SENTIMENT.PY TEST RESULTS")
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
    
    print(f"\nResults: {successful}/{len(companies)} successful")
    
    if timeouts > 0:
        print(f"\n⚠️  HANGING CONFIRMED: {timeouts} tests timed out")
        print("sentiment.py still has Selenium cleanup issues!")
    else:
        print(f"\n✅ No hanging detected in sentiment.py direct execution")
    
    return timeouts == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)