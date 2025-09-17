#!/usr/bin/env python3
"""
Base scraper interface and common utilities for all scrapers
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import requests
import time
import random
import re
import threading
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import base64
# Try to import newspaper3k for better article extraction
try:
    from newspaper import Article, Config
    NEWSPAPER3K_AVAILABLE = True
except ImportError:
    NEWSPAPER3K_AVAILABLE = False
    print("WARNING: newspaper3k not available. Using fallback extraction methods.")

# Try to import playwright for browser automation
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    if __name__ == "__main__":  # Only show warning if running directly
        print("INFO: Playwright not available. Browser automation features disabled.")

# Global playwright browser instance for performance optimization
_GLOBAL_PLAYWRIGHT = None
_GLOBAL_BROWSER = None
_BROWSER_LAST_USED = 0
_PLAYWRIGHT_ERROR_COUNT = 0
_PLAYWRIGHT_DISABLED_UNTIL = 0
_BROWSER_CREATION_IN_PROGRESS = False
_BROWSER_CREATION_COUNT = 0
_MAX_BROWSER_CREATIONS = 3

# Global URL resolution success tracking
_URL_RESOLUTION_STATS = {}  # {source_name: {"attempts": int, "successes": int}}
_DISABLED_SOURCES = set()  # Sources with <10% success rate

# Thread safety lock for Playwright operations
_PLAYWRIGHT_LOCK = threading.RLock()


@dataclass
class SentimentData:
    """Data structure for sentiment analysis results"""
    text: str
    source: str
    timestamp: datetime
    polarity: float  # TextBlob polarity (-1 to 1)
    compound: float  # VADER compound score (-1 to 1)
    url: str = ""
    raw_extracted_text: str = ""  # Raw text extracted by newspaper3k for debugging


class BaseScraper(ABC):
    """Abstract base class for all news scrapers"""
    
    def __init__(self, symbol: str, debug: bool = True):
        self.symbol = symbol.upper()
        self.debug = debug
        
        # Get complete company information
        company_info = self._get_company_info()
        self.company_name = company_info.get('company_name', self.symbol)  # Full official name
        self.common_name = company_info.get('common_name', self.symbol)    # Search-friendly name
        self.industry = company_info.get('industry', 'Unknown')            # Industry classification
        
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:109.0) Gecko/20100101 Firefox/120.0'
        ]
        self.header_sets = [
            {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            },
            {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            },
            {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,de-DE;q=0.8,de;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site'
            }
        ]
        # Track playwright usage for this scraper instance
        self._playwright_used = False
        self._last_playwright_request = 0  # Timestamp of last playwright request
        
    @abstractmethod
    def scrape(self, max_articles: int = 10) -> List[SentimentData]:
        """Scrape articles and return sentiment data"""
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the scraper source"""
        pass
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent to avoid blocking"""
        return random.choice(self.user_agents)
    
    def make_request(self, url: str, headers: Dict[str, Any] = None, timeout: int = 10) -> requests.Response:
        """Make a request with random user agent and error handling"""
        if headers is None:
            headers = {}
        
        headers.update({
            'User-Agent': self.get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        try:
            response = self.session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            if self.debug:
                print(f"Request failed for {url}: {e}")
            raise
    
    def random_delay(self, min_seconds: float = 0.5, max_seconds: float = 2.0):
        """Add random delay to avoid rate limiting"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def _get_company_info(self) -> Dict[str, str]:
        """Get complete company information from database or resolve using Gemini API"""
        try:
            # Import database module
            import sys
            import os
            current_dir = os.path.dirname(os.path.dirname(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            from core.database import SentimentDatabase
            
            # Get or resolve complete company info using the database
            db = SentimentDatabase()
            company_info = db.get_or_resolve_company_info(self.symbol)
            
            if self.debug:
                print(f"[{self.source_name}] Company info for '{self.symbol}': {company_info}")
            
            return company_info
            
        except Exception as e:
            if self.debug:
                print(f"[{self.source_name}] Failed to get company info for {self.symbol}: {e}")
                print(f"[{self.source_name}] Falling back to defaults")
            
            # Fallback to defaults
            return {
                'company_name': self.symbol,
                'common_name': self.symbol,
                'industry': 'Unknown'
            }
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text for processing"""
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        text = ' '.join(text.split())
        
        # Remove common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        
        return text.strip()
    
    def is_relevant_content(self, title: str, content: str = "") -> bool:
        """Check if content is relevant to the stock symbol or company name"""
        text_to_check = f"{title} {content}".lower()
        
        # Check for direct symbol mention
        if self.symbol.lower() in text_to_check:
            return True
        
        # Check for common name mention (if different from symbol)
        if (hasattr(self, 'common_name') and self.common_name and 
            self.common_name != self.symbol and 
            self.common_name.lower() in text_to_check):
            return True
        
        # Additional relevance checks can be added here
        return False
    
    @classmethod
    def track_url_resolution_attempt(cls, source_name: str):
        """Track URL resolution attempt for success rate monitoring"""
        global _URL_RESOLUTION_STATS
        
        if source_name not in _URL_RESOLUTION_STATS:
            _URL_RESOLUTION_STATS[source_name] = {"attempts": 0, "successes": 0}
        
        _URL_RESOLUTION_STATS[source_name]["attempts"] += 1
    
    @classmethod
    def track_url_resolution_success(cls, source_name: str):
        """Track successful URL resolution"""
        global _URL_RESOLUTION_STATS
        
        if source_name in _URL_RESOLUTION_STATS:
            _URL_RESOLUTION_STATS[source_name]["successes"] += 1
        
        # Check if source should be disabled
        cls._evaluate_source_success_rate(source_name)
    
    @classmethod
    def _evaluate_source_success_rate(cls, source_name: str):
        """Evaluate source success rate and disable if below 10%"""
        global _URL_RESOLUTION_STATS, _DISABLED_SOURCES
        
        stats = _URL_RESOLUTION_STATS.get(source_name, {})
        attempts = stats.get("attempts", 0)
        successes = stats.get("successes", 0)
        
        # Only evaluate after minimum attempts
        if attempts >= 10:  
            success_rate = (successes / attempts) * 100
            if success_rate < 10:
                _DISABLED_SOURCES.add(source_name)
                print(f"WARNING: {source_name} disabled - success rate: {success_rate:.1f}% ({successes}/{attempts})")
    
    @classmethod
    def is_source_disabled(cls, source_name: str) -> bool:
        """Check if source is disabled due to low success rate"""
        return source_name in _DISABLED_SOURCES
    
    @classmethod
    def get_url_resolution_stats(cls) -> dict:
        """Get URL resolution statistics for all sources"""
        global _URL_RESOLUTION_STATS
        stats = {}
        for source, data in _URL_RESOLUTION_STATS.items():
            attempts = data["attempts"]
            successes = data["successes"]
            success_rate = (successes / attempts * 100) if attempts > 0 else 0
            stats[source] = {
                "attempts": attempts,
                "successes": successes,
                "success_rate": success_rate,
                "disabled": source in _DISABLED_SOURCES
            }
        return stats
    
    @classmethod
    def get_playwright_browser(cls):
        """Get shared playwright browser instance for all scrapers with error tracking and auto-refresh"""
        global _GLOBAL_PLAYWRIGHT, _GLOBAL_BROWSER, _BROWSER_LAST_USED, _PLAYWRIGHT_ERROR_COUNT, _PLAYWRIGHT_DISABLED_UNTIL, _BROWSER_CREATION_IN_PROGRESS, _BROWSER_CREATION_COUNT, _MAX_BROWSER_CREATIONS
        
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not available. Install playwright and run 'playwright install'.")
        
        current_time = time.time()
        
        # Check if playwright is temporarily disabled due to errors
        if current_time < _PLAYWRIGHT_DISABLED_UNTIL:
            remaining_time = int(_PLAYWRIGHT_DISABLED_UNTIL - current_time)
            print(f"  Playwright temporarily disabled for {remaining_time} more seconds due to errors")
            raise Exception(f"Playwright disabled for {remaining_time} seconds due to repeated errors")
        
        # Thread-safe check for browser creation in progress
        with _PLAYWRIGHT_LOCK:
            if _BROWSER_CREATION_IN_PROGRESS:
                print(f"  Playwright browser creation already in progress, waiting...")
                time.sleep(2)
                if _GLOBAL_BROWSER is not None:
                    return _GLOBAL_BROWSER
                else:
                    raise Exception("Browser creation failed or taking too long")
        
        # More lenient creation limits for heavy workloads
        if _BROWSER_CREATION_COUNT >= 10:  # Increased from 3 to 10
            print(f"  Maximum playwright browser creations ({_MAX_BROWSER_CREATIONS}) reached for this session")
            raise Exception("Maximum playwright browser creations reached - preventing infinite loops")
        
        # Auto-refresh browser conditions:
        # 1. No browser exists
        # 2. Browser is older than 3 minutes (reduced from 5 for freshness)
        # 3. High error count suggests browser issues
        needs_refresh = (
            _GLOBAL_BROWSER is None or 
            (current_time - _BROWSER_LAST_USED) > 180 or  # 3 minutes instead of 5
            _PLAYWRIGHT_ERROR_COUNT >= 3  # Refresh if errors accumulate
        )
        
        if needs_refresh:
            _BROWSER_CREATION_IN_PROGRESS = True
            _BROWSER_CREATION_COUNT += 1
            
            try:
                # Close existing browser if it exists
                if _GLOBAL_BROWSER is not None:
                    try:
                        _GLOBAL_BROWSER.close()
                    except:
                        pass
                
                if _GLOBAL_PLAYWRIGHT is not None:
                    try:
                        _GLOBAL_PLAYWRIGHT.stop()
                    except:
                        pass
                
                # Start new playwright instance
                _GLOBAL_PLAYWRIGHT = sync_playwright().start()
                
                # Launch browser with optimized settings
                try:
                    _GLOBAL_BROWSER = _GLOBAL_PLAYWRIGHT.chromium.launch(
                        headless=True,  # More stable than visible browser
                        args=[
                            '--no-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-gpu',
                            '--disable-extensions',
                            '--disable-plugins',
                            '--disable-images',
                            '--disable-background-timer-throttling',
                            '--disable-renderer-backgrounding',
                            '--disable-backgrounding-occluded-windows',
                            '--disable-background-networking',
                            '--disable-sync',
                            '--disable-translate',
                            '--disable-ipc-flooding-protection',
                            '--memory-pressure-off',
                            '--max_old_space_size=2048',
                            '--ignore-ssl-errors-on-localhost',
                            '--ignore-ssl-errors',
                            '--ignore-certificate-errors',
                            '--allow-running-insecure-content',
                            '--disable-web-security',
                            '--disable-features=VizDisplayCompositor'
                        ]
                    )
                    
                    # Reset error count on successful browser creation
                    _PLAYWRIGHT_ERROR_COUNT = 0
                    
                    print("  Playwright browser initialized with heavy workload optimizations")
                    
                except Exception as e:
                    print(f"  WARNING: Playwright browser creation failed: {e}")
                    _GLOBAL_BROWSER = None
                    _PLAYWRIGHT_ERROR_COUNT += 3  # Penalize creation failures more heavily
                    raise e
                
            finally:
                _BROWSER_CREATION_IN_PROGRESS = False
        
        _BROWSER_LAST_USED = current_time
        
        return _GLOBAL_BROWSER
    
    @classmethod
    def cleanup_playwright_browser(cls):
        """Cleanup the global playwright browser with thread safety"""
        global _GLOBAL_PLAYWRIGHT, _GLOBAL_BROWSER
        
        with _PLAYWRIGHT_LOCK:  # Prevent concurrent cleanup
            if _GLOBAL_BROWSER is not None:
                try:
                    # First try graceful close
                    _GLOBAL_BROWSER.close()
                    print("  Playwright browser cleaned up successfully")
                except Exception as e:
                    print(f"  Warning: Browser cleanup error ({e})")
                finally:
                    _GLOBAL_BROWSER = None
            
            if _GLOBAL_PLAYWRIGHT is not None:
                try:
                    _GLOBAL_PLAYWRIGHT.stop()
                    print("  Playwright instance stopped successfully")
                except Exception as e:
                    print(f"  Warning: Playwright cleanup error ({e})")
                finally:
                    _GLOBAL_PLAYWRIGHT = None
    
    def make_request_with_playwright(self, url: str, wait_for_selector: str = None, 
                                  wait_timeout: int = 10, enable_javascript: bool = True) -> tuple:
        """
        Make a request using playwright for JavaScript-heavy sites or anti-bot protection
        
        Args:
            url: URL to fetch
            wait_for_selector: CSS selector to wait for before returning
            wait_timeout: How long to wait for the selector
            enable_javascript: Whether to enable JavaScript execution
            
        Returns:
            tuple: (page_source, final_url) or (None, None) if failed
        """
        global _PLAYWRIGHT_ERROR_COUNT, _PLAYWRIGHT_DISABLED_UNTIL
        
        if not PLAYWRIGHT_AVAILABLE:
            if self.debug:
                print("      Playwright not available, falling back to requests")
            return None, None
        
        # Add small delay between playwright requests to prevent browser overload
        current_time = time.time()
        if self._last_playwright_request > 0:
            time_since_last = current_time - self._last_playwright_request
            if time_since_last < 1.0:  # Less than 1 second since last request
                delay = 1.0 - time_since_last
                if self.debug:
                    print(f"      Playwright: Adding {delay:.1f}s delay to prevent overload")
                time.sleep(delay)
        
        self._last_playwright_request = time.time()
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                browser = self.get_playwright_browser()
                if browser is None:
                    if self.debug:
                        print("      Playwright browser not available")
                    return None, None
                
                self._playwright_used = True
                
                # Create new page context for each request
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True,
                    java_script_enabled=enable_javascript
                )
                
                page = context.new_page()
                
                # Enhanced error handling for navigation
                if self.debug:
                    print(f"      Playwright: Attempt {attempt + 1} - Navigating to {url[:80]}...")
                
                # Dynamic timeout based on URL complexity
                if 'google.com' in url:
                    page_timeout = 10000  # Google News needs more time for redirects (in ms)
                else:
                    page_timeout = 10000   # Standard timeout for other sites (in ms)
                
                # Navigate with enhanced timeout handling
                try:
                    # Navigate to the page
                    response = page.goto(url, timeout=page_timeout, wait_until='domcontentloaded')
                    
                    # For Google News URLs, wait for potential redirects
                    if 'news.google.com' in url and '/articles/' in url:
                        if self.debug:
                            print(f"      Playwright: Waiting for Google News redirect...")
                        
                        # Wait up to 5 seconds for URL to change (redirect)
                        try:
                            page.wait_for_load_state('networkidle', timeout=5000)
                            current_url = page.url
                            if current_url != url and 'google.com' not in current_url:
                                if self.debug:
                                    print(f"      Playwright: Successful redirect detected to: {current_url}")
                        except PlaywrightTimeoutError:
                            if self.debug:
                                print(f"      Playwright: No redirect detected after timeout")
                    
                except PlaywrightTimeoutError:
                    if self.debug:
                        print(f"      Playwright: Page load timeout, but continuing...")
                    # Continue anyway, partial load might be sufficient
                
                # Wait strategy with multiple fallbacks
                wait_successful = False
                
                if wait_for_selector:
                    try:
                        # Wait for specific selector
                        page.wait_for_selector(wait_for_selector, timeout=min(wait_timeout, 6) * 1000)
                        wait_successful = True
                        if self.debug:
                            print(f"      Playwright: Successfully found selector '{wait_for_selector}'")
                    except PlaywrightTimeoutError:
                        # Try alternative waiting strategies
                        try:
                            page.wait_for_selector("body", timeout=2000)
                            wait_successful = True
                            if self.debug:
                                print(f"      Playwright: Selector timeout, but body loaded")
                        except PlaywrightTimeoutError:
                            if self.debug:
                                print(f"      Playwright: Both selectors failed, using minimal wait")
                
                if not wait_successful:
                    # Minimal wait as last resort
                    time.sleep(1)
                
                # Get page content with error handling
                try:
                    page_source = page.content()
                    final_url = page.url
                    
                    if page_source and len(page_source) > 100:  # Basic validation
                        # Reset error count on successful operation
                        _PLAYWRIGHT_ERROR_COUNT = max(0, _PLAYWRIGHT_ERROR_COUNT - 1)  # Gradually reduce error count
                        
                        if self.debug:
                            print(f"      Playwright: Success! Final URL: {final_url[:60]}...")
                            print(f"      Playwright: Page source length: {len(page_source)} chars")
                        return page_source, final_url
                    else:
                        if self.debug:
                            print(f"      Playwright: Page source too short ({len(page_source) if page_source else 0} chars)")
                        
                except Exception as content_error:
                    if self.debug:
                        print(f"      Playwright: Failed to get page content: {content_error}")
                finally:
                    # Always close the page context
                    try:
                        context.close()
                    except:
                        pass
                    
            except Exception as pwe:
                _PLAYWRIGHT_ERROR_COUNT += 1
                
                if self.debug:
                    error_msg = str(pwe)
                    if "timeout" in error_msg.lower():
                        print(f"      Playwright: Timeout error on attempt {attempt + 1} (total errors: {_PLAYWRIGHT_ERROR_COUNT})")
                    elif "connection" in error_msg.lower():
                        print(f"      Playwright: Connection error on attempt {attempt + 1} (total errors: {_PLAYWRIGHT_ERROR_COUNT})")
                    else:
                        print(f"      Playwright: Error on attempt {attempt + 1}: {error_msg[:100]} (total errors: {_PLAYWRIGHT_ERROR_COUNT})")
                
                # Enhanced error recovery - force browser refresh for certain errors
                critical_errors = ["browser has been closed", "target closed", "connection refused"]
                if any(error_phrase in str(pwe).lower() for error_phrase in critical_errors):
                    if self.debug:
                        print(f"      Playwright: Critical error detected - forcing browser refresh")
                    self.cleanup_playwright_browser()
                    # Clear error count since we're getting a fresh browser
                    _PLAYWRIGHT_ERROR_COUNT = max(0, _PLAYWRIGHT_ERROR_COUNT - 2)
                
                # More lenient error threshold for heavy workloads
                if _PLAYWRIGHT_ERROR_COUNT >= 8:  # Increased from 5 to 8
                    _PLAYWRIGHT_DISABLED_UNTIL = time.time() + 180  # Reduced from 5 minutes to 3 minutes
                    if self.debug:
                        print(f"      Playwright: Disabled for 3 minutes due to {_PLAYWRIGHT_ERROR_COUNT} consecutive errors")
                    self.cleanup_playwright_browser()
                    return None, None
                    
                if attempt == max_retries - 1:
                    return None, None
                    
                time.sleep(min(2 * attempt, 5))  # Exponential backoff
                
            except Exception as e:
                if self.debug:
                    print(f"      Playwright: Unexpected error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return None, None
                time.sleep(1)
        
        return None, None
    
    def make_request_enhanced(self, url: str, use_playwright_fallback: bool = True, 
                            playwright_wait_selector: str = None, **kwargs) -> requests.Response:
        """
        Enhanced request method that tries requests first, then playwright if needed
        
        Args:
            url: URL to fetch
            use_playwright_fallback: Whether to try playwright if requests fails
            playwright_wait_selector: CSS selector to wait for in playwright
            **kwargs: Additional arguments for requests
            
        Returns:
            requests.Response or custom response object
        """
        # Try regular requests first
        try:
            response = self.make_request(url, **kwargs)
            
            # Check if we got blocked/redirected to anti-bot page
            if self._is_likely_blocked(response):
                if use_playwright_fallback and PLAYWRIGHT_AVAILABLE:
                    if self.debug:
                        print(f"      Request appears blocked, trying playwright fallback...")
                    return self._playwright_to_response(url, playwright_wait_selector)
                else:
                    if self.debug:
                        print(f"      Request appears blocked but playwright fallback disabled")
            
            return response
            
        except Exception as e:
            if self.debug:
                print(f"      Regular request failed: {e}")
            
            if use_playwright_fallback and PLAYWRIGHT_AVAILABLE:
                if self.debug:
                    print(f"      Trying playwright fallback...")
                return self._playwright_to_response(url, playwright_wait_selector)
            else:
                raise e
    
    def _is_likely_blocked(self, response: requests.Response) -> bool:
        """Check if response indicates we were blocked by anti-bot measures"""
        # Check status codes that suggest blocking
        if response.status_code in [403, 429, 503]:
            return True
        
        # Check for common anti-bot content
        content_lower = response.text.lower()
        block_indicators = [
            'cloudflare', 'captcha', 'blocked', 'access denied', 
            'please verify', 'security check', 'bot detected',
            'suspicious activity', 'rate limit', 'too many requests'
        ]
        
        return any(indicator in content_lower for indicator in block_indicators)
    
    def _playwright_to_response(self, url: str, wait_selector: str = None) -> object:
        """Convert playwright result to requests.Response-like object"""
        page_source, final_url = self.make_request_with_playwright(url, wait_selector)
        
        if page_source is None:
            raise Exception("Playwright request failed")
        
        # Create a minimal response-like object
        class PlaywrightResponse:
            def __init__(self, content, url, status_code=200):
                self.text = content
                self.content = content.encode('utf-8')
                self.url = url
                self.status_code = status_code
                self.headers = {}
            
            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests.HTTPError(f"{self.status_code} Error")
        
        return PlaywrightResponse(page_source, final_url or url)
    
    def fetch_full_article(self, url: str, max_length: int = 3000) -> str:
        """Fetch and extract full article text using newspaper3k (preferred) or fallback methods"""
        if not url or not url.startswith('http'):
            return ""
        
        # Try newspaper3k first (much more reliable)
        if NEWSPAPER3K_AVAILABLE:
            return self._extract_with_newspaper3k(url, max_length)
        
        # Fallback to custom extraction methods
        return self._extract_with_custom_methods(url, max_length)
    
    def _extract_with_newspaper3k(self, url: str, max_length: int) -> str:
        """Extract article content using newspaper3k library"""
        try:
            if self.debug:
                print(f"      Starting newspaper3k extraction for: {url[:80]}...")
            
            # Configure newspaper3k
            config = Config()
            config.browser_user_agent = self.get_random_user_agent()
            config.request_timeout = 7
            config.fetch_images = False
            config.memoize_articles = False
            
            if self.debug:
                print(f"      Config set - User Agent: {config.browser_user_agent[:50]}...")
            
            # Create and process article
            article = Article(url, config=config)
            
            # Note: Google News redirect resolution is now handled in enhance_article_data() before calling this method
            
            # Download and parse
            if self.debug:
                print(f"      Downloading article...")
            article.download()
            
            if self.debug:
                print(f"      Download status: {article.download_state}")
                print(f"      Response code: {getattr(article, 'response', {}).get('status_code', 'Unknown')}")
            
            if self.debug:
                print(f"      Parsing article...")
            article.parse()
            
            # Get the main article text
            article_text = article.text
            article_title = article.title
            article_authors = article.authors
            article_summary = article.summary
            
            if self.debug:
                print(f"      NEWSPAPER3K DEBUG:")
                print(f"        Title: {article_title[:100] if article_title else 'None'}...")
                print(f"        Authors: {article_authors}")
                print(f"        Summary length: {len(article_summary) if article_summary else 0}")
                print(f"        Article text length: {len(article_text) if article_text else 0}")
                print(f"        Article URL: {article.url}")
                print(f"        Top image: {article.top_image}")
                
                if article_text:
                    print(f"        First 200 chars of text: {article_text[:200]}...")
                else:
                    print(f"        Article text is EMPTY or None")
                    print(f"        HTML length: {len(article.html) if article.html else 0}")
                    if article.html:
                        print(f"        HTML sample: {article.html[:300]}...")
            
            if not article_text or len(article_text.strip()) < 100:
                if self.debug:
                    print(f"      newspaper3k: Article text too short or empty - FAILED")
                return ""
            
            # Additional metadata that might be useful
            title = article.title
            summary = article.summary
            
            # Combine title with article text if title is substantial and different
            if (title and len(title) > 10 and 
                title.lower() not in article_text.lower()[:200]):
                full_text = f"{title}. {article_text}"
            else:
                full_text = article_text
            
            # Clean and limit the text
            full_text = self.clean_text(full_text)
            
            # Check if content seems legitimate
            if not self._is_legitimate_article_content(full_text):
                if self.debug:
                    print(f"      newspaper3k: Content failed legitimacy check")
                return ""
            
            # Smart truncation at sentence boundaries
            if len(full_text) > max_length:
                sentences = full_text.split('.')
                truncated = ""
                for sentence in sentences:
                    if len(truncated) + len(sentence) + 1 <= max_length:
                        truncated += sentence + "."
                    else:
                        break
                full_text = truncated.strip()
                if not full_text.endswith('.'):
                    full_text += "..."
            
            if self.debug and full_text:
                print(f"      newspaper3k: Successfully extracted {len(full_text)} characters")
                print(f"      newspaper3k: First 200 chars: {full_text[:200]}...")
            elif self.debug:
                print(f"      newspaper3k: No content extracted or failed validation")
            
            return full_text
            
        except Exception as e:
            if self.debug:
                print(f"      newspaper3k extraction failed: {e}")
            
            # If newspaper3k failed due to 403/401 errors, try Playwright fallback
            if ("403" in str(e) or "401" in str(e) or "Forbidden" in str(e) or 
                "Client Error" in str(e)):
                if self.debug:
                    print(f"      newspaper3k blocked - trying Playwright fallback...")
                return self._extract_with_playwright_fallback(url, max_length)
            
            return ""
    
    def _extract_with_playwright_fallback(self, url: str, max_length: int) -> str:
        """Extract article content using Playwright when newspaper3k is blocked"""
        if not PLAYWRIGHT_AVAILABLE:
            if self.debug:
                print(f"      Playwright not available for fallback extraction")
            return ""
        
        try:
            if self.debug:
                print(f"      Starting Playwright article extraction for: {url[:80]}...")
            
            # Use Playwright to fetch the page content
            page_source, final_url = self.make_request_with_playwright(
                url, 
                wait_for_selector="body",
                wait_timeout=15,
                enable_javascript=True
            )
            
            if not page_source:
                if self.debug:
                    print(f"      Playwright extraction failed - no page source")
                return ""
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Clean the soup of unwanted elements
            self._clean_soup_for_extraction(soup)
            
            # Try different content extraction strategies based on the site
            content = ""
            
            # Strategy 1: Look for common article content selectors
            article_selectors = [
                'article', 'div[class*="article"]', 'div[class*="content"]',
                'div[class*="story"]', 'div[class*="post"]', 'div[class*="main"]',
                'section[class*="content"]', 'main', '[role="main"]',
                'div[class*="body"]', 'div[id*="content"]', 'div[id*="article"]'
            ]
            
            for selector in article_selectors:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        text = element.get_text(separator=' ', strip=True)
                        # Look for substantial content that mentions our symbol or financial terms
                        if (len(text) > 200 and 
                            (self.symbol.lower() in text.lower() or 
                             any(term in text.lower() for term in ['stock', 'shares', 'trading', 'market', 'earnings']))):
                            content = text
                            break
                    if content:
                        break
                except Exception:
                    continue
            
            # Strategy 2: If no article content found, try paragraph extraction
            if not content:
                paragraphs = soup.find_all('p')
                relevant_paragraphs = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if (len(text) > 50 and 
                        (self.symbol.lower() in text.lower() or 
                         any(term in text.lower() for term in ['stock', 'shares', 'trading', 'market']))):
                        relevant_paragraphs.append(text)
                
                if relevant_paragraphs:
                    content = ' '.join(relevant_paragraphs)
            
            # Clean and validate content
            if content:
                content = self.clean_text(content)
                
                # Check if content is legitimate
                if self._is_legitimate_article_content(content):
                    # Truncate if too long
                    if len(content) > max_length:
                        sentences = content.split('.')
                        truncated = ""
                        for sentence in sentences:
                            if len(truncated) + len(sentence) + 1 <= max_length:
                                truncated += sentence + "."
                            else:
                                break
                        content = truncated.strip()
                        if not content.endswith('.'):
                            content += "..."
                    
                    if self.debug:
                        print(f"      Playwright extraction SUCCESS: {len(content)} characters")
                        print(f"      First 150 chars: {content[:150]}...")
                    
                    return content
                else:
                    if self.debug:
                        print(f"      Playwright content failed legitimacy check")
            else:
                if self.debug:
                    print(f"      No relevant content found with Playwright")
            
        except Exception as e:
            if self.debug:
                print(f"      Playwright fallback extraction failed: {e}")
        
        return ""
    
    def _extract_with_custom_methods(self, url: str, max_length: int) -> str:
        """Fallback to custom extraction methods when newspaper3k is not available"""
        try:
            # Handle Google News redirect URLs
            if 'news.google.com' in url and '/articles/' in url:
                # Try to extract the actual article URL
                response = self.make_request(url, timeout=10)
                if response.status_code in [301, 302]:
                    url = response.headers.get('Location', url)
            
            # Enhanced headers for better content access
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = self.make_request(url, headers=headers, timeout=20)
            if response.status_code != 200:
                return ""
            
            # Check if we got redirected to a paywall or login page
            final_url = response.url
            if any(indicator in final_url.lower() for indicator in ['login', 'subscribe', 'paywall', 'signin']):
                if self.debug:
                    print(f"Article appears to be behind paywall: {final_url}")
                return ""
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for paywall indicators in content
            if self._is_paywalled_content(soup):
                if self.debug:
                    print(f"Content appears to be paywalled")
                return ""
            
            # Remove unwanted elements early
            self._clean_soup_for_extraction(soup)
            
            # Try multiple strategies to extract article content
            article_text = self._extract_article_content(soup)
            
            if article_text:
                # Clean and validate text
                article_text = self.clean_text(article_text)
                
                # Filter out very short extractions (likely failed)
                if len(article_text) < 100:
                    return ""
                
                # Check if content seems legitimate (not just navigation/ads)
                if not self._is_legitimate_article_content(article_text):
                    return ""
                
                # Limit length but allow more content
                if len(article_text) > max_length:
                    # Try to cut at sentence boundary
                    sentences = article_text.split('.')
                    truncated = ""
                    for sentence in sentences:
                        if len(truncated) + len(sentence) + 1 <= max_length:
                            truncated += sentence + "."
                        else:
                            break
                    article_text = truncated.strip() + "..."
                
                return article_text
                
        except Exception as e:
            if self.debug:
                print(f"Failed to fetch full article from {url}: {e}")
        
        return ""
    
    def _clean_soup_for_extraction(self, soup: BeautifulSoup):
        """Remove unwanted elements before content extraction"""
        # Remove scripts, styles, and other non-content elements
        for element in soup(['script', 'style', 'noscript', 'svg']):
            element.decompose()
        
        # Remove common navigation and promotional elements
        unwanted_selectors = [
            'nav', 'header', 'footer', 'aside',
            '[class*="nav"]', '[class*="menu"]', '[class*="sidebar"]',
            '[class*="ad"]', '[class*="advertisement"]', '[class*="promo"]',
            '[class*="social"]', '[class*="share"]', '[class*="follow"]',
            '[class*="newsletter"]', '[class*="subscribe"]', '[class*="signup"]',
            '[class*="related"]', '[class*="recommended"]', '[class*="trending"]',
            '[class*="comment"]', '[class*="discuss"]', '[class*="feedback"]',
            '[class*="cookie"]', '[class*="gdpr"]', '[class*="consent"]',
            '[id*="ad"]', '[id*="social"]', '[id*="comment"]'
        ]
        
        for selector in unwanted_selectors:
            try:
                for element in soup.select(selector):
                    element.decompose()
            except:
                continue
    
    def _is_paywalled_content(self, soup: BeautifulSoup) -> bool:
        """Check if content appears to be behind a paywall"""
        paywall_indicators = [
            'subscribe', 'subscription', 'paywall', 'premium', 'member only',
            'sign in to continue', 'login to read', 'free trial', 'unlock',
            'this article is for subscribers', 'become a member'
        ]
        
        page_text = soup.get_text().lower()
        return any(indicator in page_text for indicator in paywall_indicators)
    
    def _is_legitimate_article_content(self, text: str) -> bool:
        """Check if extracted text appears to be legitimate article content"""
        text_lower = text.lower()
        
        # Check for common non-article content patterns
        junk_patterns = [
            'click here', 'subscribe now', 'sign up', 'follow us',
            'terms of service', 'privacy policy', 'cookie policy',
            'advertisement', 'sponsored content'
        ]
        
        junk_count = sum(1 for pattern in junk_patterns if pattern in text_lower)
        if junk_count > 3:  # Too much promotional content
            return False
        
        # Check for reasonable sentence structure
        sentences = text.split('.')
        good_sentences = sum(1 for s in sentences if len(s.strip()) > 20)
        
        if good_sentences < 3:  # Need at least 3 substantial sentences
            return False
        
        return True
    
    def _extract_article_content(self, soup: BeautifulSoup) -> str:
        """Intelligently extract main article content using advanced strategies"""
        
        # Strategy 1: Use readability-based content extraction
        content = self._extract_with_readability_heuristics(soup)
        if content:
            return content
        
        # Strategy 2: JSON-LD structured data extraction
        content = self._extract_from_structured_data(soup)
        if content:
            return content
        
        # Strategy 3: Advanced semantic article detection
        content = self._extract_with_semantic_analysis(soup)
        if content:
            return content
        
        # Strategy 4: Content density analysis
        content = self._extract_by_content_density(soup)
        if content:
            return content
        
        # Strategy 5: Fallback to basic extraction
        return self._extract_basic_content(soup)
    
    def _extract_with_readability_heuristics(self, soup: BeautifulSoup) -> str:
        """Extract content using readability-based scoring similar to Mozilla's Readability"""
        
        # Remove obviously non-content elements
        for element in soup(['script', 'style', 'nav', 'aside', 'footer', 'header', 
                           'form', 'button', 'input', 'select', 'textarea']):
            element.decompose()
        
        # Prioritized article container selectors
        article_containers = [
            'article',
            '[role="main"]',
            'main',
            '.post-content',
            '.entry-content', 
            '.article-content',
            '.article-body',
            '.story-body',
            '.content-body',
            '.post-body',
            '.entry-body',
            '#content',
            '.content',
            '#main-content',
            '.main-content'
        ]
        
        best_container = None
        best_score = 0
        
        for selector in article_containers:
            try:
                containers = soup.select(selector)
                for container in containers:
                    score = self._score_content_container(container)
                    if score > best_score:
                        best_score = score
                        best_container = container
            except:
                continue
        
        if best_container and best_score > 50:  # Minimum quality threshold
            return self._extract_text_from_container(best_container)
        
        return ""
    
    def _score_content_container(self, element) -> int:
        """Score a container based on content quality indicators"""
        if not element:
            return 0
            
        score = 0
        text_length = len(element.get_text(strip=True))
        
        # Base score from text length
        score += min(text_length // 10, 100)  # Cap at 100 for length
        
        # Count paragraph elements (good indicator)
        paragraphs = element.find_all('p')
        score += len(paragraphs) * 10
        
        # Penalize if too few paragraphs relative to text
        if text_length > 500 and len(paragraphs) < 3:
            score -= 30
        
        # Reward good paragraph length distribution
        good_paragraphs = sum(1 for p in paragraphs if 50 < len(p.get_text(strip=True)) < 800)
        score += good_paragraphs * 15
        
        # Check for article-like class names
        class_attr = element.get('class', [])
        id_attr = element.get('id', '')
        
        good_indicators = ['article', 'content', 'post', 'story', 'entry', 'main', 'body']
        bad_indicators = ['comment', 'sidebar', 'nav', 'menu', 'ad', 'footer', 'header', 'social']
        
        for indicator in good_indicators:
            if any(indicator in str(attr).lower() for attr in class_attr + [id_attr]):
                score += 25
        
        for indicator in bad_indicators:
            if any(indicator in str(attr).lower() for attr in class_attr + [id_attr]):
                score -= 30
        
        # Check link density (too many links = probably not main content)
        links = element.find_all('a')
        if text_length > 0:
            link_density = sum(len(link.get_text(strip=True)) for link in links) / text_length
            if link_density > 0.3:  # More than 30% links
                score -= 40
        
        # Reward presence of time/date indicators
        if element.find(['time', '[datetime]']) or any(word in element.get_text().lower() 
            for word in ['published', 'updated', 'posted', 'ago', 'am', 'pm']):
            score += 15
        
        return max(0, score)
    
    def _extract_from_structured_data(self, soup: BeautifulSoup) -> str:
        """Extract content from JSON-LD structured data"""
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    
                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        data = data[0]
                    
                    # Look for article content
                    if data.get('@type') in ['Article', 'NewsArticle', 'BlogPosting']:
                        article_body = data.get('articleBody', '')
                        if article_body and len(article_body) > 200:
                            return article_body
                        
                        # Try description as fallback
                        description = data.get('description', '')
                        if description and len(description) > 100:
                            return description
                            
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        except Exception:
            pass
        return ""
    
    def _extract_with_semantic_analysis(self, soup: BeautifulSoup) -> str:
        """Extract content using semantic HTML analysis"""
        
        # Look for semantic elements in order of preference
        semantic_selectors = [
            'article',
            'section[class*="article"]',
            'section[class*="story"]', 
            'section[class*="content"]',
            'div[class*="article-text"]',
            'div[class*="story-text"]',
            'div[class*="post-text"]',
            'div[itemtype*="Article"]',  # Schema.org markup
            '[role="article"]',
            '[role="main"]'
        ]
        
        for selector in semantic_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    content = self._extract_text_from_container(element)
                    if len(content) > 300:  # Minimum content length
                        return content
            except:
                continue
        
        return ""
    
    def _extract_by_content_density(self, soup: BeautifulSoup) -> str:
        """Find content by analyzing text density in different page regions"""
        
        # Get all divs and sections that might contain content
        candidates = soup.find_all(['div', 'section', 'article'], recursive=True)
        
        best_candidate = None
        best_density = 0
        
        for candidate in candidates:
            # Skip small elements
            total_text = candidate.get_text(strip=True)
            if len(total_text) < 200:
                continue
            
            # Calculate text density (text per HTML element)
            child_elements = len(candidate.find_all())
            if child_elements == 0:
                continue
                
            density = len(total_text) / child_elements
            
            # Bonus for paragraph-rich content
            paragraphs = candidate.find_all('p')
            if paragraphs:
                avg_para_length = sum(len(p.get_text(strip=True)) for p in paragraphs) / len(paragraphs)
                if 50 < avg_para_length < 500:  # Good paragraph length range
                    density *= 1.5
            
            # Penalty for too many links or images
            links = len(candidate.find_all('a'))
            images = len(candidate.find_all('img'))
            if links + images > child_elements * 0.3:
                density *= 0.7
            
            if density > best_density:
                best_density = density
                best_candidate = candidate
        
        if best_candidate and best_density > 5:  # Minimum density threshold
            return self._extract_text_from_container(best_candidate)
        
        return ""
    
    def _extract_text_from_container(self, container) -> str:
        """Extract clean text from a content container"""
        if not container:
            return ""
        
        # Remove unwanted nested elements
        for element in container(['script', 'style', 'nav', 'aside', 'footer', 'header',
                                'div[class*="ad"]', 'div[class*="social"]', 'div[class*="share"]',
                                'div[class*="related"]', 'div[class*="comment"]', 'form']):
            element.decompose()
        
        # Get text from paragraphs and headings primarily
        text_parts = []
        
        # Extract headings (but not too many)
        headings = container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        heading_texts = []
        for heading in headings[:3]:  # Limit to first 3 headings
            h_text = heading.get_text(strip=True)
            if h_text and len(h_text) > 10 and len(h_text) < 200:
                heading_texts.append(h_text)
        
        # Extract paragraphs
        paragraphs = container.find_all('p')
        para_texts = []
        for para in paragraphs:
            p_text = para.get_text(strip=True)
            # Filter out short paragraphs and likely navigation/metadata
            if (p_text and len(p_text) > 30 and 
                not any(word in p_text.lower() for word in ['copyright', 'subscribe', 'follow us', 'share this', 'read more'])):
                para_texts.append(p_text)
        
        # Combine headings and paragraphs
        if heading_texts:
            text_parts.extend(heading_texts)
        if para_texts:
            text_parts.extend(para_texts)
        
        # If we didn't get enough from paragraphs, try other elements
        if len(' '.join(text_parts)) < 200:
            other_elements = container.find_all(['div', 'span', 'section'])
            for elem in other_elements:
                # Only direct text, not nested
                direct_text = ''.join(elem.find_all(text=True, recursive=False)).strip()
                if direct_text and len(direct_text) > 50:
                    text_parts.append(direct_text)
        
        full_text = ' '.join(text_parts)
        
        # Clean up the text
        full_text = re.sub(r'\s+', ' ', full_text)  # Normalize whitespace
        full_text = re.sub(r'[\r\n]+', ' ', full_text)  # Remove line breaks
        
        return full_text.strip()
    
    def _extract_basic_content(self, soup: BeautifulSoup) -> str:
        """Fallback basic content extraction"""
        # Find all paragraphs and filter by quality
        paragraphs = soup.find_all('p')
        if paragraphs:
            text_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if (text and len(text) > 40 and  # Longer paragraphs
                    not any(word in text.lower() for word in ['cookie', 'privacy', 'subscribe', 'newsletter'])):
                    text_parts.append(text)
            
            if len(text_parts) >= 3:  # Need at least 3 good paragraphs
                return ' '.join(text_parts)
        
        return ""
    
    def _try_google_news_redirect(self, url: str) -> str:
        """Try multiple strategies to resolve Google News URLs to actual article URLs"""
        try:
            # Strategy 1: Try with minimal headers first
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = self.session.get(url, headers=headers, allow_redirects=True, timeout=10)
            
            # Check if we got redirected to a real news site
            final_url = response.url
            if (final_url != url and 
                'google.com' not in final_url and
                len(final_url) > 20 and
                any(domain in final_url for domain in 
                    ['yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                     'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com', 'ap.com',
                     'washingtonpost.com', 'nytimes.com', 'businessinsider.com', 'forbes.com',
                     'benzinga.com', 'seekingalpha.com', 'fool.com', 'zacks.com'])):
                return final_url
            
            # Strategy 2: Try to parse HTML for canonical URL or actual article link
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for canonical URL
                canonical = soup.find('link', rel='canonical')
                if canonical and canonical.get('href'):
                    canonical_url = canonical['href']
                    if ('google.com' not in canonical_url and 
                        any(domain in canonical_url for domain in 
                            ['yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                             'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com'])):
                        return canonical_url
                
                # Look for article links in the page
                article_links = soup.find_all('a', href=True)
                for link in article_links:
                    href = link['href']
                    if (href.startswith('http') and 
                        'google.com' not in href and
                        any(domain in href for domain in 
                            ['yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                             'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com'])):
                        return href
        
        except Exception:
            pass
        
        return None
    
    def _extract_urls_from_decoded_text(self, decoded_text: str) -> str:
        """Extract valid news URLs from decoded Google News text"""
        try:
            import re
            url_pattern = r'https?://[^\s<>"\'`]+'
            urls = re.findall(url_pattern, decoded_text)
            
            for url in urls:
                # Skip Google URLs and look for actual news sites
                if ('google.com' not in url and 
                    any(domain in url for domain in 
                        ['yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                         'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com', 'ap.com',
                         'washingtonpost.com', 'nytimes.com', 'businessinsider.com', 'forbes.com',
                         'benzinga.com', 'seekingalpha.com', 'fool.com', 'zacks.com', 'thetradable.com'])):
                    return url
            
            # If no recognized news site, return first non-Google URL
            for url in urls:
                if 'google.com' not in url and len(url) > 20:
                    return url
                    
        except Exception:
            pass
        
        return None
    
    def _resolve_google_news_url(self, google_news_url: str) -> str:
        """Resolve Google News URL to actual article URL using improved strategies"""
        try:
            # Use the improved Google News resolver
            from google_news_resolver import GoogleNewsResolver
            resolver = GoogleNewsResolver(debug=self.debug)
            resolved_url = resolver.resolve_url(google_news_url)
            return resolved_url
        except ImportError:
            # Fallback to original method if resolver not available
            return self._resolve_google_news_url_fallback(google_news_url)
        except Exception as e:
            if self.debug:
                print(f"    Improved resolver failed: {e}, falling back to original method")
            return self._resolve_google_news_url_fallback(google_news_url)
    
    def _resolve_google_news_url_fallback(self, google_news_url: str) -> str:
        """Fallback Google News URL resolution method with circuit breaker"""
        # Track resolution attempt
        self.track_url_resolution_attempt("Google News")
        
        # Circuit breaker: Check if Google News resolution is temporarily disabled
        if "Google News" in _DISABLED_SOURCES:
            if self.debug:
                print(f"      Google News URL resolution is disabled due to repeated failures")
            return None
        
        try:
            import base64
            import urllib.parse
            
            # Extract the encoded part from URL
            parts = google_news_url.split('/articles/')
            if len(parts) > 1:
                encoded_part = parts[1].split('?')[0]  # Remove query params
                
                if self.debug:
                    print(f"      Trying fallback decode: {encoded_part[:50]}...")
                
                # Enhanced Base64 decode attempts with more methods
                decode_methods = [
                    # Method 1: CBM prefix handling + Base64
                    lambda x: self._try_cbm_decode(x),
                    # Method 2: Standard Base64 with padding
                    lambda x: base64.b64decode(x + '=' * (4 - len(x) % 4), validate=True),
                    # Method 3: Base64 without validation
                    lambda x: base64.b64decode(x, validate=False),
                    # Method 4: URL decode + Base64
                    lambda x: base64.b64decode(urllib.parse.unquote(x), validate=False),
                    # Method 5: Base64URL (URL-safe base64)
                    lambda x: base64.b64decode(x.replace('-', '+').replace('_', '/') + '=' * (4 - len(x.replace('-', '+').replace('_', '/')) % 4)),
                ]
                
                for i, decode_func in enumerate(decode_methods):
                    try:
                        decoded_bytes = decode_func(encoded_part)
                        decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
                        decoded_url = self._extract_urls_from_decoded_text(decoded_text)
                        if decoded_url:
                            if self.debug:
                                print(f"      SUCCESS: Method {i+1} decoded to: {decoded_url}")
                            # Track successful resolution
                            self.track_url_resolution_success("Google News")
                            return decoded_url
                    except Exception as e:
                        if self.debug and i < 2:  # Only show first few failures to avoid spam
                            print(f"      Method {i+1} failed: {e}")
                        continue
                
                if self.debug:
                    print(f"      All decode methods failed, trying Playwright approach...")
                
                # Use Playwright for JavaScript-based redirects (Google News requires JS)
                if self.debug:
                    print(f"      Using Playwright for Google News redirect...")
                
                try:
                    page_source, final_url = self.make_request_with_playwright(
                        google_news_url, 
                        wait_for_selector="body",  # Wait for page to load
                        wait_timeout=10,  # Longer timeout for redirects
                        enable_javascript=True
                    )
                except Exception as playwright_error:
                    if self.debug:
                        print(f"      Playwright error: {playwright_error}")
                    page_source, final_url = None, None
                
                if page_source and final_url and final_url != google_news_url:
                    # Check if we got redirected to a real news site
                    news_domains = [
                        'yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                        'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com', 'ap.com',
                        'washingtonpost.com', 'nytimes.com', 'businessinsider.com', 'forbes.com',
                        'benzinga.com', 'seekingalpha.com', 'fool.com', 'zacks.com', 
                        'carboncredits.com', 'newser.com', 'thetradable.com', 'thehill.com',
                        'usatoday.com', 'abcnews.go.com', 'cbsnews.com', 'nbcnews.com'
                    ]
                    
                    if ('google.com' not in final_url and
                        len(final_url) > 25 and
                        any(domain in final_url for domain in news_domains)):
                        if self.debug:
                            print(f"      SUCCESS: Playwright redirect to: {final_url}")
                        self.track_url_resolution_success("Google News")
                        return final_url
                
                # Fallback to HTTP approach if Playwright didn't work
                if self.debug:
                    print(f"      Playwright failed, trying HTTP approach...")
                
                headers = {
                    'User-Agent': self.get_random_user_agent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Referer': 'https://news.google.com/',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'no-cache'
                }
                
                response = self.session.get(google_news_url, headers=headers, allow_redirects=True, timeout=15)
                
                # Enhanced domain list
                news_domains = [
                    'yahoo.com', 'reuters.com', 'cnn.com', 'bbc.com', 'marketwatch.com',
                    'bloomberg.com', 'wsj.com', 'fortune.com', 'cnbc.com', 'ap.com',
                    'washingtonpost.com', 'nytimes.com', 'businessinsider.com', 'forbes.com',
                    'benzinga.com', 'seekingalpha.com', 'fool.com', 'zacks.com', 
                    'carboncredits.com', 'newser.com', 'thetradable.com', 'thehill.com',
                    'usatoday.com', 'abcnews.go.com', 'cbsnews.com', 'nbcnews.com'
                ]
                
                # Check if we got redirected to a real news site
                final_url = response.url
                if (final_url != google_news_url and 
                    'google.com' not in final_url and
                    len(final_url) > 25 and
                    any(domain in final_url for domain in news_domains)):
                    if self.debug:
                        print(f"      SUCCESS: HTTP redirect to: {final_url}")
                    # Track successful resolution
                    self.track_url_resolution_success("Google News")
                    return final_url
                
                # Parse HTML for links if no redirect
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for canonical URL
                    canonical = soup.find('link', rel='canonical')
                    if canonical and canonical.get('href'):
                        canonical_url = canonical['href']
                        if ('google.com' not in canonical_url and 
                            any(domain in canonical_url for domain in news_domains)):
                            if self.debug:
                                print(f"      SUCCESS: Canonical URL found: {canonical_url}")
                            # Track successful resolution
                            self.track_url_resolution_success("Google News")
                            return canonical_url
                    
                    # Look for article links in the page (expanded search)
                    for link in soup.find_all('a', href=True)[:30]:  # Check more links
                        href = link['href']
                        if (href.startswith('http') and 
                            'google.com' not in href and
                            len(href) > 25 and
                            any(domain in href for domain in news_domains)):
                            if self.debug:
                                print(f"      SUCCESS: Article link found: {href}")
                            # Track successful resolution
                            self.track_url_resolution_success("Google News")
                            return href
        
        except Exception as e:
            if self.debug:
                print(f"    Fallback Google News URL resolution failed: {e}")
        
        return None
    
    def _try_cbm_decode(self, encoded_part: str) -> bytes:
        """Handle CBM-prefixed Google News URLs"""
        if encoded_part.startswith('CBM'):
            # Remove CBM prefix and decode the rest
            without_prefix = encoded_part[3:]
            return base64.b64decode(without_prefix + '=' * (4 - len(without_prefix) % 4))
        else:
            # Standard decode
            return base64.b64decode(encoded_part + '=' * (4 - len(encoded_part) % 4))
    
    def enhance_article_data(self, article_data: 'SentimentData') -> 'SentimentData':
        """Enhance article data by fetching full article content"""
        if not article_data.url:
            if self.debug:
                print(f"    No URL to enhance article")
            return article_data
        
        if self.debug:
            print(f"    Enhancing article from URL: {article_data.url}")
            print(f"    Original text length: {len(article_data.text)} chars")
        
        # Pre-resolve Google News URLs before newspaper3k processing with timeout
        effective_url = article_data.url
        if 'news.google.com' in article_data.url and '/articles/' in article_data.url:
            if self.debug:
                print(f"    Pre-resolving Google News redirect...")
            
            # Add timeout wrapper for Google News resolution to prevent hanging
            import concurrent.futures
            
            resolved_url = None
            try:
                # Use ThreadPoolExecutor with timeout for Windows compatibility
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._resolve_google_news_url, article_data.url)
                    try:
                        resolved_url = future.result(timeout=15)  # 15-second timeout
                    except concurrent.futures.TimeoutError:
                        if self.debug:
                            print(f"    Google News resolution timed out after 15s - canceling")
                        future.cancel()  # Try to cancel the future
                        resolved_url = None
                        
            except Exception as e:
                if self.debug:
                    print(f"    Google News resolution failed: {e}")
                resolved_url = None
            
            if resolved_url and resolved_url != article_data.url:
                effective_url = resolved_url
                if self.debug:
                    print(f"    SUCCESS: Resolved to: {effective_url}")
            else:
                if self.debug:
                    print(f"    Could not resolve Google News URL, skipping enhancement")
                # Don't waste time trying newspaper3k on unresolved Google URLs
                return article_data
            
        full_text = self.fetch_full_article(effective_url)
        
        if full_text and len(full_text) > len(article_data.text):
            # Store the raw extracted text for debugging/verification
            article_data.raw_extracted_text = full_text
            
            # Combine title/summary with full article
            original_length = len(article_data.text)
            enhanced_text = f"{article_data.text} {full_text}"
            article_data.text = enhanced_text
            
            if self.debug:
                print(f"    SUCCESS Enhanced! Original: {original_length} -> Enhanced: {len(article_data.text)} chars")
                print(f"    Enhancement added {len(full_text)} chars of article content")
        elif self.debug:
            if not full_text:
                print(f"    X No article content extracted")
            else:
                print(f"    X Extracted content ({len(full_text)} chars) not longer than original ({len(article_data.text)} chars)")
            
        return article_data