#!/usr/bin/env python3
"""
Test the updated Google News resolver directly
"""

from google_news_resolver import GoogleNewsResolver

def test_resolver():
    """Test the Google News resolver directly"""
    print("Testing Google News Resolver")
    print("=" * 40)
    
    # Use the URL we know works from our previous test
    test_url = "https://news.google.com/rss/articles/CBMiugFBVV95cUxQdnZNZkJ5a0Y2bUdLMWlDUGh0bWhTRHBrN3JHZHFDRkFvdS04eGhnamxHbFpNR00yeUZKWThiOGdESzRhMVlzQVpkZ183UGJ3NEg2emcxa3dkd01QTW1DQkpDVGdWenF1aTdQWTFCZUtWUlVuV0pQYkxiYzNXMzdTd1NIbmRkcEpPMVQyay1lTmdhOWNlNTlabDJ3THVfUWxrNzBfWHI2YnpoWllsMDIzMk5lN1d2ZEEyeEE?oc=5"
    
    print(f"Testing URL: {test_url[:100]}...")
    
    resolver = GoogleNewsResolver(debug=True)
    
    resolved = resolver.resolve_url(test_url)
    
    if resolved and resolved != test_url and 'google.com' not in resolved:
        print(f"\nSUCCESS!")
        print(f"Resolved to: {resolved}")
        
        # Test newspaper3k on the resolved URL
        print(f"\nTesting newspaper3k extraction...")
        try:
            from scrapers.google_news_scraper import GoogleNewsScraper
            scraper = GoogleNewsScraper('AAPL', debug=False)  # No debug to avoid extra output
            
            full_text = scraper.fetch_full_article(resolved)
            if full_text and len(full_text) > 500:
                print(f"SUCCESS: Extracted {len(full_text)} characters")
                print(f"Sample: {full_text[:200]}...")
                return True
            else:
                print(f"FAILED: Only extracted {len(full_text) if full_text else 0} characters")
        except Exception as e:
            print(f"ERROR: newspaper3k failed - {e}")
    else:
        print(f"FAILED: Could not resolve URL")
        if resolved:
            print(f"Got: {resolved}")
    
    return False

if __name__ == "__main__":
    success = test_resolver()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")