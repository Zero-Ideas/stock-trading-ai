#!/usr/bin/env python3
"""
Improved Google News URL resolution test and implementation
"""

import sys
import os
import requests
import base64
import urllib.parse
import re
from bs4 import BeautifulSoup

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.base_scraper import BaseScraper
from scrapers.google_news_scraper import GoogleNewsScraper

def improved_google_news_resolver(url: str, debug: bool = True) -> str:
    """
    Improved Google News URL resolver using multiple strategies
    """
    if not ('news.google.com' in url and '/articles/' in url):
        return url
        
    if debug:
        print(f"Resolving Google News URL: {url[:80]}...")
    
    try:
        # Strategy 1: Try direct HTTP redirect first (most reliable)
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://news.google.com/',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # First try: Get the page and check for immediate redirect
        response = session.get(url, headers=headers, allow_redirects=True, timeout=15)
        
        if debug:
            print(f"  HTTP Status: {response.status_code}")
            print(f"  Final URL: {response.url}")
            print(f"  Redirects: {len(response.history)}")
        
        # Check if we got redirected to a real news site
        final_url = response.url
        if (final_url != url and 
            'google.com' not in final_url and
            len(final_url) > 30 and
            final_url.startswith('http') and
            any(domain in final_url for domain in 
                ['yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                 'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com', 'ap.com',
                 'washingtonpost.com', 'nytimes.com', 'businessinsider.com', 'forbes.com',
                 'benzinga.com', 'seekingalpha.com', 'fool.com', 'zacks.com', 'carboncredits.com',
                 'newser.com', 'thetradable.com'])):
            if debug:
                print(f"  SUCCESS: HTTP redirect to {final_url}")
            return final_url
        
        # Strategy 2: Parse HTML for actual article URLs
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            if debug:
                print(f"  Parsing HTML content ({len(response.content)} bytes)")
            
            # Look for article links that match known news domains
            article_links = soup.find_all('a', href=True)
            
            for link in article_links:
                href = link.get('href', '')
                
                # Check if it's a direct article URL
                if (href.startswith('http') and 
                    'google.com' not in href and
                    len(href) > 30 and
                    any(domain in href for domain in 
                        ['yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                         'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com', 'ap.com',
                         'washingtonpost.com', 'nytimes.com', 'businessinsider.com', 'forbes.com',
                         'benzinga.com', 'seekingalpha.com', 'fool.com', 'zacks.com', 'carboncredits.com',
                         'newser.com', 'thetradable.com'])):
                    if debug:
                        print(f"  SUCCESS: Found article link {href}")
                    return href
                
                # Check if it's a Google redirect URL we can follow
                if href.startswith('./articles/') or href.startswith('/articles/'):
                    full_href = urllib.parse.urljoin('https://news.google.com', href)
                    if debug:
                        print(f"  Found relative article link: {full_href}")
                    # Try to resolve this one too
                    try:
                        redirect_response = session.get(full_href, headers=headers, allow_redirects=True, timeout=10)
                        if (redirect_response.url != full_href and 
                            'google.com' not in redirect_response.url and
                            any(domain in redirect_response.url for domain in 
                                ['yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                                 'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com', 'ap.com',
                                 'washingtonpost.com', 'nytimes.com', 'businessinsider.com', 'forbes.com',
                                 'benzinga.com', 'seekingalpha.com', 'fool.com', 'zacks.com', 'carboncredits.com',
                                 'newser.com', 'thetradable.com'])):
                            if debug:
                                print(f"  SUCCESS: Relative link resolved to {redirect_response.url}")
                            return redirect_response.url
                    except:
                        continue
            
            # Strategy 3: Look for canonical URL
            canonical = soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                canonical_url = canonical['href']
                if ('google.com' not in canonical_url and 
                    canonical_url.startswith('http') and
                    any(domain in canonical_url for domain in 
                        ['yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                         'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com', 'ap.com',
                         'washingtonpost.com', 'nytimes.com', 'businessinsider.com', 'forbes.com',
                         'benzinga.com', 'seekingalpha.com', 'fool.com', 'zacks.com', 'carboncredits.com',
                         'newser.com', 'thetradable.com'])):
                    if debug:
                        print(f"  SUCCESS: Canonical URL {canonical_url}")
                    return canonical_url
            
            # Strategy 4: Look for meta refresh
            meta_refresh = soup.find('meta', attrs={'http-equiv': re.compile(r'refresh', re.I)})
            if meta_refresh:
                content = meta_refresh.get('content', '')
                if 'url=' in content.lower():
                    refresh_url = content.split('url=')[1].strip()
                    if (refresh_url.startswith('http') and 
                        'google.com' not in refresh_url and
                        any(domain in refresh_url for domain in 
                            ['yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                             'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com'])):
                        if debug:
                            print(f"  SUCCESS: Meta refresh to {refresh_url}")
                        return refresh_url
        
        # Strategy 5: Advanced Base64 decoding attempts
        if debug:
            print(f"  Trying advanced Base64 decoding...")
        
        parts = url.split('/articles/')
        if len(parts) > 1:
            encoded_part = parts[1].split('?')[0]  # Remove query params
            
            # Try multiple Base64 decoding approaches
            for method_name, decode_func in [
                ("URL decode + Base64 + padding", lambda x: base64.b64decode(urllib.parse.unquote(x) + '=' * (4 - len(urllib.parse.unquote(x)) % 4))),
                ("Direct Base64 + padding", lambda x: base64.b64decode(x + '=' * (4 - len(x) % 4))),
                ("URL decode + Base64 no validation", lambda x: base64.b64decode(urllib.parse.unquote(x), validate=False)),
                ("Direct Base64 no validation", lambda x: base64.b64decode(x, validate=False)),
            ]:
                try:
                    decoded_bytes = decode_func(encoded_part)
                    decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
                    
                    # Look for URLs in decoded text
                    url_pattern = r'https?://[^\s<>"\'\`]+'
                    urls = re.findall(url_pattern, decoded_text)
                    
                    for found_url in urls:
                        if ('google.com' not in found_url and 
                            len(found_url) > 30 and
                            any(domain in found_url for domain in 
                                ['yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                                 'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com', 'ap.com',
                                 'washingtonpost.com', 'nytimes.com', 'businessinsider.com', 'forbes.com',
                                 'benzinga.com', 'seekingalpha.com', 'fool.com', 'zacks.com', 'carboncredits.com',
                                 'newser.com', 'thetradable.com'])):
                            if debug:
                                print(f"  SUCCESS: {method_name} -> {found_url}")
                            return found_url
                            
                except Exception as e:
                    if debug:
                        print(f"  {method_name} failed: {e}")
                    continue
        
        if debug:
            print(f"  FAILED: All resolution methods failed")
        return url  # Return original if all methods fail
        
    except Exception as e:
        if debug:
            print(f"  ERROR: {e}")
        return url  # Return original URL on error

def test_improved_resolution():
    """Test the improved Google News resolution"""
    print("TESTING IMPROVED GOOGLE NEWS URL RESOLUTION")
    print("=" * 60)
    
    # Get some Google News URLs to test
    scraper = GoogleNewsScraper("AAPL", debug=False)
    articles = scraper.scrape(max_articles=3)
    
    if not articles:
        print("No articles found for testing")
        return False
    
    google_urls = [article.url for article in articles if 'news.google.com' in article.url]
    
    if not google_urls:
        print("No Google News URLs found for testing")
        return False
    
    print(f"Found {len(google_urls)} Google News URLs to test\n")
    
    successful_resolutions = 0
    
    for i, url in enumerate(google_urls[:2]):  # Test first 2 URLs
        print(f"--- TEST {i+1}/{len(google_urls[:2])} ---")
        resolved_url = improved_google_news_resolver(url, debug=True)
        
        if resolved_url != url and 'google.com' not in resolved_url:
            print(f"SUCCESS: Resolved to actual news site!")
            print(f"Original:  {url[:80]}...")
            print(f"Resolved:  {resolved_url}")
            
            # Test with newspaper3k
            print("\nTesting newspaper3k on resolved URL...")
            try:
                base_scraper = BaseScraper("AAPL", debug=True)
                extracted_text = base_scraper.fetch_full_article(resolved_url, max_length=1000)
                if extracted_text and len(extracted_text) > 100:
                    print(f"NEWSPAPER3K SUCCESS: Extracted {len(extracted_text)} characters")
                    print(f"Preview: {extracted_text[:200]}...")
                    successful_resolutions += 1
                else:
                    print(f"NEWSPAPER3K FAILED: Only got {len(extracted_text) if extracted_text else 0} chars")
            except Exception as e:
                print(f"NEWSPAPER3K ERROR: {e}")
        else:
            print(f"FAILED: Could not resolve URL")
        
        print()
    
    print(f"FINAL RESULTS:")
    print(f"URLs tested: {len(google_urls[:2])}")
    print(f"Successfully resolved + newspaper3k worked: {successful_resolutions}")
    
    return successful_resolutions > 0

if __name__ == "__main__":
    success = test_improved_resolution()
    if success:
        print("\n✅ Improved resolution is working!")
    else:
        print("\n❌ Need further improvements")