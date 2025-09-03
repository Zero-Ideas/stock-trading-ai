#!/usr/bin/env python3
"""
Debug Selenium resolution in detail
"""

import time
import sys
from scrapers.google_news_scraper import GoogleNewsScraper

def debug_selenium_resolution():
    """Debug the Selenium resolution process step by step"""
    print("Debug Selenium Resolution Process", flush=True)
    print("=" * 50, flush=True)
    
    scraper = GoogleNewsScraper('AAPL', debug=True)
    
    # Test URL
    test_url = "https://news.google.com/rss/articles/CBMiugFBVV95cUxQdnZNZkJ5a0Y2bUdLMWlDUGh0bWhTRHBrN3JHZHFDRkFvdS04eGhnamxHbFpNR00yeUZKWThiOGdESzRhMVlzQVpkZ183UGJ3NEg2emcxa3dkd01QTW1DQkpDVGdWenF1aTdQWTFCZUtWUlVuV0pQYkxiYzNXMzdTd1NIbmRkcEpPMVQyay1lTmdhOWNlNTlabDJ3THVfUWxrNzBfWHI2YnpoWllsMDIzMk5lN1d2ZEEyeEE?oc=5"
    
    print(f"Testing URL: {test_url}")
    print(f"URL length: {len(test_url)}")
    print("", flush=True)
    
    # Step 1: Test base64 decoding methods
    print("STEP 1: Testing base64 decoding methods...", flush=True)
    
    # Extract encoded part
    parts = test_url.split('/articles/')
    if len(parts) > 1:
        encoded_part = parts[1].split('?')[0]
        print(f"Encoded part: {encoded_part}")
        
        # Try different decoding methods manually
        import base64
        import urllib.parse
        
        methods = [
            "CBM prefix handling",
            "Standard Base64",
            "URL decode + Base64",
            "Base64URL"
        ]
        
        for i, method in enumerate(methods, 1):
            try:
                print(f"Method {i} ({method}):", end=" ", flush=True)
                
                if method == "CBM prefix handling" and encoded_part.startswith('CBM'):
                    decoded_bytes = base64.b64decode(encoded_part[3:] + '=' * (4 - len(encoded_part[3:]) % 4))
                elif method == "Standard Base64":
                    decoded_bytes = base64.b64decode(encoded_part + '=' * (4 - len(encoded_part) % 4))
                elif method == "URL decode + Base64":
                    decoded_bytes = base64.b64decode(urllib.parse.unquote(encoded_part), validate=False)
                else:  # Base64URL
                    url_safe = encoded_part.replace('-', '+').replace('_', '/')
                    decoded_bytes = base64.b64decode(url_safe + '=' * (4 - len(url_safe) % 4))
                
                decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
                print(f"SUCCESS - {len(decoded_text)} chars", flush=True)
                print(f"  Preview: {decoded_text[:100]}...")
                
                # Look for URLs
                import re
                urls = re.findall(r'https?://[^\s<>"\'`]+', decoded_text)
                for url in urls:
                    if 'google.com' not in url:
                        print(f"  Found URL: {url}")
                        
            except Exception as e:
                print(f"FAILED - {e}", flush=True)
    
    print("\nSTEP 2: Testing Selenium approach...", flush=True)
    
    try:
        page_source, final_url = scraper.make_request_with_selenium(
            test_url,
            wait_for_selector="body",
            wait_timeout=15
        )
        
        if page_source:
            print(f"SUCCESS: Got {len(page_source)} chars from Selenium")
            print(f"Final URL: {final_url}")
            
            if final_url != test_url:
                print("URL changed!")
                if 'google.com' not in final_url:
                    print("Successfully redirected away from Google!")
                    return final_url
        else:
            print("FAILED: No page source returned")
            
    except Exception as e:
        print(f"ERROR: Selenium failed - {e}")
        import traceback
        traceback.print_exc()
    
    return None

if __name__ == "__main__":
    result = debug_selenium_resolution()
    
    if result:
        print(f"\nSUCCESS: Resolved to {result}")
    else:
        print("\nFAILED: Could not resolve URL")