#!/usr/bin/env python3
"""
Simple Google News resolution test
"""

from scrapers.google_news_scraper import GoogleNewsScraper

def simple_test():
    """Simple test without unicode issues"""
    print("Simple Google News Test")
    print("=" * 30)
    
    scraper = GoogleNewsScraper('AAPL', debug=True)
    
    # Test URL from earlier
    test_url = "https://news.google.com/rss/articles/CBMiugFBVV95cUxQdnZNZkJ5a0Y2bUdLMWlDUGh0bWhTRHBrN3JHZHFDRkFvdS04eGhnamxHbFpNR00yeUZKWThiOGdESzRhMVlzQVpkZ183UGJ3NEg2emcxa3dkd01QTW1DQkpDVGdWenF1aTdQWTFCZUtWUlVuV0pQYkxiYzNXMzdTd1NIbmRkcEpPMVQyay1lTmdhOWNlNTlabDJ3THVfUWxrNzBfWHI2YnpoWllsMDIzMk5lN1d2ZEEyeEE?oc=5"
    
    print("Testing Google News URL resolution...")
    print(f"URL: {test_url[:100]}...")
    
    try:
        resolved = scraper._resolve_google_news_url(test_url)
        
        if resolved and resolved != test_url and 'google.com' not in resolved:
            print("SUCCESS: URL resolved!")
            print(f"Resolved to: {resolved}")
            
            # Test newspaper3k on resolved URL
            print("Testing newspaper3k extraction...")
            full_text = scraper.fetch_full_article(resolved)
            if full_text:
                print(f"SUCCESS: Extracted {len(full_text)} characters")
                print(f"Sample: {full_text[:200]}...")
                return True
            else:
                print("FAILED: No content extracted")
        else:
            print("FAILED: URL not resolved")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    return False

if __name__ == "__main__":
    success = simple_test()
    print(f"\nOverall result: {'PASS' if success else 'FAIL'}")