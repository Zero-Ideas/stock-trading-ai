#!/usr/bin/env python3
"""
Direct test of Selenium for Google News URLs
"""

from scrapers.google_news_scraper import GoogleNewsScraper

def test_selenium_direct():
    """Test Selenium directly with Google News URL"""
    print("Direct Selenium Test for Google News")
    print("=" * 40)
    
    # Sample Google News URL
    google_url = "https://news.google.com/rss/articles/CBMiugFBVV95cUxQdnZNZkJ5a0Y2bUdLMWlDUGh0bWhTRHBrN3JHZHFDRkFvdS04eGhnamxHbFpNR00yeUZKWThiOGdESzRhMVlzQVpkZ183UGJ3NEg2emcxa3dkd01QTW1DQkpDVGdWenF1aTdQWTFCZUtWUlVuV0pQYkxiYzNXMzdTd1NIbmRkcEpPMVQyay1lTmdhOWNlNTlabDJ3THVfUWxrNzBfWHI2YnpoWllsMDIzMk5lN1d2ZEEyeEE?oc=5"
    
    print(f"Testing URL: {google_url[:80]}...")
    
    scraper = GoogleNewsScraper('TEST', debug=True)
    
    try:
        print("Attempting Selenium request...")
        page_source, final_url = scraper.make_request_with_selenium(
            google_url,
            wait_for_selector="body",
            wait_timeout=15
        )
        
        if page_source:
            print(f"✅ Got page source: {len(page_source)} characters")
            print(f"Final URL: {final_url}")
            
            if final_url != google_url:
                print("✅ URL changed!")
                if 'google.com' not in final_url:
                    print("✅ Successfully redirected away from Google!")
                    return True
                else:
                    print("Still on Google domain")
            else:
                print("URL didn't change")
        else:
            print("Failed to get page source")
            
    except Exception as e:
        print(f"Error: {e}")
    
    return False

if __name__ == "__main__":
    success = test_selenium_direct()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")