#!/usr/bin/env python3
"""
Google News URL resolver using multiple strategies including browser automation
"""

import requests
import time
import base64
import urllib.parse
import re
from bs4 import BeautifulSoup
from typing import Optional

class GoogleNewsResolver:
    """Resolves Google News URLs to actual article URLs"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        # Simple cache to avoid re-resolving the same URLs
        self._resolution_cache = {}
        self._selenium_attempts = 0
        self._max_selenium_attempts = 3  # Enable selenium with our working implementation
    
    def resolve_url(self, google_news_url: str) -> Optional[str]:
        """
        Resolve a Google News URL to the actual article URL using multiple strategies
        """
        if not ('news.google.com' in google_news_url and '/articles/' in google_news_url):
            return google_news_url
        
        # Check cache first
        if google_news_url in self._resolution_cache:
            if self.debug:
                print(f"Using cached resolution for: {google_news_url[:80]}...")
            return self._resolution_cache[google_news_url]
        
        if self.debug:
            print(f"Resolving: {google_news_url[:80]}...")
        
        # Strategy 1: Try different URL manipulation approaches (fast)
        #resolved_url = self._try_url_manipulation(google_news_url)
        #if resolved_url:
        #    self._resolution_cache[google_news_url] = resolved_url
        #    return resolved_url
        #
        ## Strategy 2: Try HTTP requests with different headers and approaches (medium speed)
        #resolved_url = self._try_http_approaches(google_news_url)
        #if resolved_url:
        #    self._resolution_cache[google_news_url] = resolved_url
        #    return resolved_url
        
        # Strategy 3: Use selenium if available and under limit (slow, limited usage)
        try:
            if self._selenium_attempts < self._max_selenium_attempts:
                resolved_url = self._try_selenium_approach(google_news_url)
                if resolved_url:
                    self._resolution_cache[google_news_url] = resolved_url
                    return resolved_url
        except ImportError:
            if self.debug:
                print("  Selenium not available, skipping browser automation")
        except Exception as e:
            if self.debug:
                print(f"  Selenium approach failed: {e}")
        
        # Cache failed resolution to avoid retrying the same URL
        self._resolution_cache[google_news_url] = None
        
        if self.debug:
            print("  All resolution methods failed")
        
        return None
    
    def _try_url_manipulation(self, url: str) -> Optional[str]:
        """Try various URL manipulation techniques"""
        if self.debug:
            print("  Trying URL manipulation...")
        
        try:
            # Extract the encoded part
            parts = url.split('/articles/')
            if len(parts) < 2:
                return None
                
            encoded_part = parts[1].split('?')[0]
            
            # Try multiple decoding approaches
            decode_methods = [
                self._decode_base64_with_padding,
                self._decode_base64_no_validation,
                self._decode_url_then_base64,
                self._decode_base64url,
                self._try_cbm_decoding
            ]
            
            for method in decode_methods:
                try:
                    decoded_url = method(encoded_part)
                    if decoded_url and self._is_valid_news_url(decoded_url):
                        if self.debug:
                            print(f"    SUCCESS: {method.__name__} -> {decoded_url}")
                        return decoded_url
                except Exception as e:
                    if self.debug:
                        print(f"    {method.__name__} failed: {e}")
                    continue
                    
        except Exception as e:
            if self.debug:
                print(f"  URL manipulation failed: {e}")
        
        return None
    
    def _decode_base64_with_padding(self, encoded_part: str) -> Optional[str]:
        """Decode base64 with proper padding"""
        padded = encoded_part + '=' * (4 - len(encoded_part) % 4)
        decoded_bytes = base64.b64decode(padded, validate=True)
        decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
        return self._extract_url_from_text(decoded_text)
    
    def _decode_base64_no_validation(self, encoded_part: str) -> Optional[str]:
        """Decode base64 without validation"""
        decoded_bytes = base64.b64decode(encoded_part, validate=False)
        decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
        return self._extract_url_from_text(decoded_text)
    
    def _decode_url_then_base64(self, encoded_part: str) -> Optional[str]:
        """URL decode first, then base64"""
        url_decoded = urllib.parse.unquote(encoded_part)
        decoded_bytes = base64.b64decode(url_decoded, validate=False)
        decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
        return self._extract_url_from_text(decoded_text)
    
    def _decode_base64url(self, encoded_part: str) -> Optional[str]:
        """Try base64url decoding (URL-safe base64)"""
        # Convert to standard base64
        base64_standard = encoded_part.replace('-', '+').replace('_', '/')
        padded = base64_standard + '=' * (4 - len(base64_standard) % 4)
        decoded_bytes = base64.b64decode(padded)
        decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
        return self._extract_url_from_text(decoded_text)
    
    def _try_cbm_decoding(self, encoded_part: str) -> Optional[str]:
        """Special handling for CBM-prefixed Google News URLs"""
        if encoded_part.startswith('CBM'):
            # Remove CBM prefix and try decoding the rest
            without_prefix = encoded_part[3:]
            return self._decode_base64_with_padding(without_prefix)
        return None
    
    def _extract_url_from_text(self, text: str) -> Optional[str]:
        """Extract a valid news URL from decoded text"""
        url_pattern = r'https?://[^\s<>"\'`]+'
        urls = re.findall(url_pattern, text)
        
        for url in urls:
            if self._is_valid_news_url(url):
                return url
        
        return None
    
    def _is_valid_news_url(self, url: str) -> bool:
        """Check if URL is a valid news site URL"""
        if not url or not url.startswith('http'):
            return False
        
        if 'google.com' in url or len(url) < 30:
            return False
        
        news_domains = [
            'yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
            'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com', 'ap.com',
            'washingtonpost.com', 'nytimes.com', 'businessinsider.com', 'forbes.com',
            'benzinga.com', 'seekingalpha.com', 'fool.com', 'zacks.com', 
            'carboncredits.com', 'newser.com', 'thetradable.com', 'thehill.com',
            'usatoday.com', 'abcnews.go.com', 'cbsnews.com', 'nbcnews.com',
            'foxnews.com', 'espn.com', 'techcrunch.com', 'tipranks.com'
        ]
        
        return any(domain in url for domain in news_domains)
    
    def _try_http_approaches(self, url: str) -> Optional[str]:
        """Try various HTTP request approaches"""
        if self.debug:
            print("  Trying HTTP approaches...")
        
        approaches = [
            self._try_direct_redirect,
            self._try_with_different_headers,
            self._try_mobile_user_agent
        ]
        
        for approach in approaches:
            try:
                result = approach(url)
                if result and self._is_valid_news_url(result):
                    if self.debug:
                        print(f"    SUCCESS: {approach.__name__} -> {result}")
                    return result
            except Exception as e:
                if self.debug:
                    print(f"    {approach.__name__} failed: {e}")
                continue
        
        return None
    
    def _try_direct_redirect(self, url: str) -> Optional[str]:
        """Try direct HTTP redirect"""
        headers = {
            'User-Agent': self.user_agents[0],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://news.google.com/',
        }
        
        response = self.session.get(url, headers=headers, allow_redirects=True, timeout=15)
        
        if response.url != url and self._is_valid_news_url(response.url):
            return response.url
        
        return None
    
    def _try_with_different_headers(self, url: str) -> Optional[str]:
        """Try with different headers that might trigger redirects"""
        headers = {
            'User-Agent': self.user_agents[1],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1'
        }
        
        response = self.session.get(url, headers=headers, allow_redirects=True, timeout=15)
        
        # Check if redirected to a valid news site
        if response.url != url and self._is_valid_news_url(response.url):
            return response.url
        
        # Parse HTML for links if we didn't get redirected
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for canonical URL
            canonical = soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                canonical_url = canonical['href']
                if self._is_valid_news_url(canonical_url):
                    return canonical_url
            
            # Look for article links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('http') and self._is_valid_news_url(href):
                    return href
        
        return None
    
    def _try_mobile_user_agent(self, url: str) -> Optional[str]:
        """Try with mobile user agent (sometimes gives different responses)"""
        mobile_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://news.google.com/',
        }
        
        response = self.session.get(url, headers=mobile_headers, allow_redirects=True, timeout=15)
        
        if response.url != url and self._is_valid_news_url(response.url):
            return response.url
        
        return None
    
    def _try_selenium_approach(self, url: str) -> Optional[str]:
        """Try using Selenium with JavaScript support for Google News redirects"""
        self._selenium_attempts += 1
        
        try:
            # Use the working approach from base_scraper.py
            from scrapers.base_scraper import BaseScraper
            
            if self.debug:
                print(f"  Selenium attempt {self._selenium_attempts}/{self._max_selenium_attempts}")
                print(f"  Using working Selenium approach for Google News...")
            
            # Create a temporary base scraper instance to use its working Selenium method
            temp_scraper = type('TempScraper', (BaseScraper,), {
                'source_name': property(lambda self: 'GoogleNewsResolver'),
                'scrape': lambda self, max_articles=10: [],
                'debug': self.debug
            })('TEMP', debug=self.debug)
            
            # Use the working make_request_with_selenium method
            page_source, final_url = temp_scraper.make_request_with_selenium(
                url,
                wait_for_selector="body",
                wait_timeout=10
            )
            
            if page_source and final_url and final_url != url:
                if self._is_valid_news_url(final_url):
                    if self.debug:
                        print(f"    SUCCESS: Selenium redirected to {final_url}")
                    return final_url
            
            if self.debug:
                print("    Selenium didn't find valid redirect")
            return None
                            
        except ImportError:
            if self.debug:
                print("    Selenium not available")
        except Exception as e:
            if self.debug:
                print(f"    Selenium approach failed: {str(e)}")
        
        return None
    

def test_resolver():
    """Test the Google News resolver"""
    print("TESTING GOOGLE NEWS RESOLVER")
    print("=" * 40)
    
    # Import here to avoid import issues in main module
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from scrapers.google_news_scraper import GoogleNewsScraper
    
    # Get some test URLs
    scraper = GoogleNewsScraper("AAPL", debug=False)
    articles = scraper.scrape(max_articles=2)
    
    if not articles:
        print("No articles found for testing")
        return
    
    google_urls = [article.url for article in articles if 'news.google.com' in article.url]
    
    if not google_urls:
        print("No Google News URLs found")
        return
    
    resolver = GoogleNewsResolver(debug=True)
    
    successful = 0
    total = len(google_urls[:2])  # Test first 2
    
    for i, url in enumerate(google_urls[:2]):
        print(f"\n--- TEST {i+1}/{total} ---")
        print(f"Original: {url[:80]}...")
        
        resolved = resolver.resolve_url(url)
        
        if resolved and resolved != url:
            print(f"SUCCESS: {resolved}")
            
            # Test with newspaper3k
            print("Testing newspaper3k extraction...")
            try:
                from scrapers.base_scraper import BaseScraper
                base_scraper = BaseScraper("AAPL", debug=True)
                extracted_text = base_scraper.fetch_full_article(resolved, max_length=500)
                if extracted_text and len(extracted_text) > 100:
                    print(f"NEWSPAPER3K SUCCESS: {len(extracted_text)} chars")
                    print(f"Preview: {extracted_text[:150]}...")
                    successful += 1
                else:
                    print(f"NEWSPAPER3K FAILED: Only {len(extracted_text) if extracted_text else 0} chars")
            except Exception as e:
                print(f"NEWSPAPER3K ERROR: {e}")
        else:
            print("RESOLUTION FAILED")
    
    print(f"\nFINAL RESULTS: {successful}/{total} successful")
    return successful > 0

if __name__ == "__main__":
    success = test_resolver()
    if success:
        print("Resolution working!")
    else:
        print("Need more work on resolution")