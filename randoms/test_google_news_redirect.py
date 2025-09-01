#!/usr/bin/env python3
"""
Comprehensive test to prove Google News redirect resolution works
"""

import sys
import os
import requests
import base64
import urllib.parse
from bs4 import BeautifulSoup

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.base_scraper import BaseScraper
from scrapers.google_news_scraper import GoogleNewsScraper

def test_individual_google_news_url(url: str) -> dict:
    """Test a single Google News URL to see if we can resolve it"""
    print(f"\n{'='*80}")
    print(f"TESTING GOOGLE NEWS URL:")
    print(f"  {url}")
    print(f"{'='*80}")
    
    result = {
        'original_url': url,
        'resolved_url': None,
        'method_used': None,
        'newspaper3k_success': False,
        'extracted_chars': 0,
        'error': None
    }
    
    try:
        # Test the base scraper's resolution method
        scraper = BaseScraper("AAPL", debug=True)
        resolved_url = scraper._resolve_google_news_url(url)
        
        if resolved_url:
            result['resolved_url'] = resolved_url
            result['method_used'] = 'base_scraper_resolution'
            print(f"✓ RESOLUTION SUCCESS: {resolved_url}")
            
            # Test newspaper3k on resolved URL
            try:
                extracted_text = scraper.fetch_full_article(resolved_url, max_length=2000)
                if extracted_text and len(extracted_text) > 100:
                    result['newspaper3k_success'] = True
                    result['extracted_chars'] = len(extracted_text)
                    print(f"✓ NEWSPAPER3K SUCCESS: Extracted {len(extracted_text)} characters")
                    print(f"   Preview: {extracted_text[:200]}...")
                else:
                    print(f"✗ NEWSPAPER3K FAILED: Got {len(extracted_text) if extracted_text else 0} chars")
            except Exception as e:
                result['error'] = str(e)
                print(f"✗ NEWSPAPER3K ERROR: {e}")
        else:
            print(f"✗ RESOLUTION FAILED")
            result['method_used'] = 'failed'
            
    except Exception as e:
        result['error'] = str(e)
        print(f"✗ TEST ERROR: {e}")
    
    return result

def manual_google_news_redirect_test(url: str) -> dict:
    """Manual test to follow Google News redirects"""
    print(f"\n{'='*60}")
    print(f"MANUAL REDIRECT TEST")
    print(f"{'='*60}")
    
    result = {
        'original_url': url,
        'resolved_url': None,
        'method_used': None,
        'steps': []
    }
    
    try:
        # Method 1: Direct HTTP request with follow redirects
        print("Method 1: Direct HTTP redirect following...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        session = requests.Session()
        response = session.get(url, headers=headers, allow_redirects=True, timeout=15)
        
        print(f"  Status: {response.status_code}")
        print(f"  Final URL: {response.url}")
        print(f"  Redirects: {len(response.history)}")
        
        result['steps'].append(f"HTTP redirect: {response.status_code} -> {response.url}")
        
        if response.url != url and 'google.com' not in response.url:
            result['resolved_url'] = response.url
            result['method_used'] = 'http_redirect'
            print(f"✓ SUCCESS: Resolved to {response.url}")
            return result
        
        # Method 2: Parse HTML for meta refresh or JavaScript redirects
        if response.status_code == 200:
            print("\nMethod 2: HTML parsing for redirects...")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for meta refresh
            meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if meta_refresh:
                content = meta_refresh.get('content', '')
                if 'url=' in content.lower():
                    redirect_url = content.split('url=')[1].strip()
                    if redirect_url.startswith('http'):
                        result['resolved_url'] = redirect_url
                        result['method_used'] = 'meta_refresh'
                        print(f"✓ SUCCESS: Meta refresh to {redirect_url}")
                        return result
            
            # Look for canonical links
            canonical = soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                canonical_url = canonical['href']
                if 'google.com' not in canonical_url:
                    result['resolved_url'] = canonical_url
                    result['method_used'] = 'canonical'
                    print(f"✓ SUCCESS: Canonical URL {canonical_url}")
                    return result
            
            # Look for article links
            for link in soup.find_all('a', href=True)[:20]:
                href = link['href']
                if (href.startswith('http') and 
                    'google.com' not in href and
                    any(domain in href for domain in 
                        ['yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                         'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com', 'thetradable.com'])):
                    result['resolved_url'] = href
                    result['method_used'] = 'html_link'
                    print(f"✓ SUCCESS: Found article link {href}")
                    return result
        
        # Method 3: Try to decode the Google News URL
        print("\nMethod 3: URL decoding...")
        if '/articles/' in url:
            parts = url.split('/articles/')
            if len(parts) > 1:
                encoded_part = parts[1].split('?')[0]
                print(f"  Encoded part: {encoded_part[:50]}...")
                
                # Try various decoding methods
                for method_name, decode_func in [
                    ("Base64 with padding", lambda x: base64.b64decode(x + '=' * (4 - len(x) % 4))),
                    ("Base64 no validation", lambda x: base64.b64decode(x, validate=False)),
                    ("URL decode + Base64", lambda x: base64.b64decode(urllib.parse.unquote(x), validate=False)),
                ]:
                    try:
                        decoded_bytes = decode_func(encoded_part)
                        decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
                        
                        # Look for URLs in decoded text
                        import re
                        url_pattern = r'https?://[^\s<>"\'`]+'
                        urls = re.findall(url_pattern, decoded_text)
                        
                        for found_url in urls:
                            if 'google.com' not in found_url and len(found_url) > 20:
                                result['resolved_url'] = found_url
                                result['method_used'] = f'decode_{method_name}'
                                print(f"✓ SUCCESS: {method_name} -> {found_url}")
                                return result
                                
                    except Exception as e:
                        print(f"  {method_name} failed: {e}")
                        continue
        
        print("✗ ALL METHODS FAILED")
        
    except Exception as e:
        result['error'] = str(e)
        print(f"✗ MANUAL TEST ERROR: {e}")
    
    return result

def comprehensive_google_news_test():
    """Run comprehensive tests on Google News redirect resolution"""
    print("🧪 COMPREHENSIVE GOOGLE NEWS REDIRECT TEST")
    print("=" * 100)
    
    # First, get some real Google News URLs
    print("Step 1: Getting real Google News URLs...")
    try:
        scraper = GoogleNewsScraper("AAPL", debug=False)
        articles = scraper.scrape(max_articles=3)
        
        if not articles:
            print("❌ No Google News articles found!")
            return
        
        google_urls = [article.url for article in articles if 'news.google.com' in article.url]
        
        if not google_urls:
            print("❌ No Google News RSS URLs found!")
            return
        
        print(f"✓ Found {len(google_urls)} Google News URLs to test")
        
        # Test each URL
        all_results = []
        for i, url in enumerate(google_urls[:2]):  # Test first 2 URLs
            print(f"\n{'#' * 20} TESTING URL {i+1}/{len(google_urls[:2])} {'#' * 20}")
            
            # Test with our current implementation
            result1 = test_individual_google_news_url(url)
            all_results.append(result1)
            
            # If our implementation failed, try manual methods
            if not result1['resolved_url']:
                print("\n🔧 Our implementation failed, trying manual methods...")
                result2 = manual_google_news_redirect_test(url)
                all_results.append(result2)
        
        # Summary
        print(f"\n{'=' * 100}")
        print("📊 FINAL RESULTS SUMMARY")
        print(f"{'=' * 100}")
        
        successful_resolutions = [r for r in all_results if r['resolved_url']]
        newspaper3k_successes = [r for r in all_results if r['newspaper3k_success']]
        
        print(f"📈 STATISTICS:")
        print(f"   URLs tested: {len(google_urls[:2])}")
        print(f"   Resolution attempts: {len(all_results)}")
        print(f"   Successful resolutions: {len(successful_resolutions)}")
        print(f"   Newspaper3k successes: {len(newspaper3k_successes)}")
        
        if successful_resolutions:
            print(f"\n✅ SUCCESS CASES:")
            for result in successful_resolutions:
                print(f"   Method: {result['method_used']}")
                print(f"   Original: {result['original_url'][:60]}...")
                print(f"   Resolved: {result['resolved_url']}")
                if result['newspaper3k_success']:
                    print(f"   Extracted: {result['extracted_chars']} characters")
                print()
        
        if len(successful_resolutions) == 0:
            print(f"\n❌ NO SUCCESSFUL RESOLUTIONS - Need to implement better methods")
            print("\n💡 RECOMMENDATIONS:")
            print("   1. Google may have changed their URL encoding")
            print("   2. Need to implement more sophisticated redirect following")
            print("   3. May need to use browser automation (selenium)")
            print("   4. Consider using alternative scraping methods")
        
        return len(successful_resolutions) > 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = comprehensive_google_news_test()
    
    if success:
        print("\n🎉 Google News redirect resolution is working!")
    else:
        print("\n🔧 Need to implement better redirect resolution methods")