# Selenium Integration Guide

## Overview

All scrapers now have access to enhanced web scraping capabilities with Selenium integration for bypassing anti-bot protection and handling JavaScript-heavy websites. The system uses a shared Selenium session for optimal performance.

## Key Features

### 1. Shared Selenium Session
- **Single browser instance** shared across all scrapers
- **Automatic cleanup** after 5 minutes of inactivity  
- **Performance optimized** with disabled images, extensions, and selective JavaScript
- **Anti-detection measures** built-in

### 2. Enhanced Request Methods
- **`make_request_enhanced()`**: Tries regular requests first, falls back to Selenium
- **`make_request_with_selenium()`**: Direct Selenium usage for complex scenarios
- **Automatic anti-bot detection** and fallback activation

### 3. Smart Anti-Bot Detection
Automatically detects when requests are blocked by:
- Status codes: 403, 429, 503
- Content indicators: "cloudflare", "captcha", "blocked", etc.
- Automatically switches to Selenium when detected

## Usage Examples

### Basic Enhanced Scraping
```python
from scrapers.your_scraper import YourScraper

scraper = YourScraper("AAPL", debug=True)

# This will automatically use Selenium if the regular request is blocked
response = scraper.make_request_enhanced(
    "https://example.com/article",
    use_selenium_fallback=True,
    selenium_wait_selector="article",  # Wait for this element
    timeout=10
)
```

### Direct Selenium Usage
```python
# For JavaScript-heavy pages or complex interactions
page_source, final_url = scraper.make_request_with_selenium(
    "https://dynamic-site.com",
    wait_for_selector=".content",  # CSS selector to wait for
    wait_timeout=15,
    enable_javascript=True
)
```

### Accessing the Shared Driver
```python
# Get the shared selenium driver for custom operations
driver = scraper.get_selenium_driver()
driver.get("https://example.com")

# Your custom selenium operations here
elements = driver.find_elements("css selector", ".article")

# Driver is automatically managed, no need to quit()
```

## Implementation in Custom Scrapers

### Method 1: Use Enhanced Requests (Recommended)
```python
class MyCustomScraper(BaseScraper):
    def scrape(self, max_articles: int = 10):
        articles = []
        
        for url in self.get_urls():
            try:
                # This automatically handles anti-bot protection
                response = self.make_request_enhanced(
                    url,
                    use_selenium_fallback=True,
                    selenium_wait_selector="article, .content"
                )
                
                # Process response normally
                soup = BeautifulSoup(response.content, 'html.parser')
                # ... extract content ...
                
            except Exception as e:
                self.debug and print(f"Failed: {e}")
                continue
        
        return articles
```

### Method 2: Direct Selenium Control
```python
class AdvancedScraper(BaseScraper):
    def scrape_complex_site(self, url: str):
        # For sites requiring JavaScript execution or complex interactions
        page_source, final_url = self.make_request_with_selenium(
            url,
            wait_for_selector=".dynamic-content",
            wait_timeout=20,
            enable_javascript=True
        )
        
        if page_source:
            soup = BeautifulSoup(page_source, 'html.parser')
            # Process the fully-rendered page
            return self.extract_articles(soup)
        
        return []
```

## Configuration Options

### Selenium Driver Configuration
The shared driver is configured with:
- **Headless mode**: Runs without visible browser
- **Anti-detection**: Removes webdriver properties
- **Performance optimization**: Disabled images, extensions
- **Timeout management**: 30-second page load timeout
- **Session reuse**: 5-minute timeout for resource efficiency

### Enhanced Request Options
```python
response = scraper.make_request_enhanced(
    url="https://example.com",
    use_selenium_fallback=True,     # Enable selenium fallback
    selenium_wait_selector="article", # CSS selector to wait for
    timeout=10,                     # Regular request timeout
    headers={"Custom": "Header"}    # Additional headers
)
```

## Performance Considerations

### Benefits
- **Shared session**: One browser instance for all scrapers
- **Resource optimization**: Disabled unnecessary features
- **Smart fallback**: Only uses Selenium when needed
- **Automatic cleanup**: Prevents memory leaks

### Best Practices
1. **Use `make_request_enhanced()` first** - tries regular requests before Selenium
2. **Specify `wait_for_selector`** - improves reliability for dynamic content
3. **Add delays** between requests to avoid rate limiting
4. **Clean up when done** - call `BaseScraper.cleanup_selenium_driver()` in long-running processes

## Error Handling

### Graceful Degradation
```python
try:
    response = scraper.make_request_enhanced(url, use_selenium_fallback=True)
except Exception as e:
    # Falls back to basic request method
    response = scraper.make_request(url)
```

### Selenium-Specific Errors
- **ImportError**: Selenium not installed - automatically handled
- **WebDriverException**: ChromeDriver issues - check installation
- **TimeoutException**: Page loading timeout - adjust wait_timeout

## Installation Requirements

```bash
pip install selenium
```

Download ChromeDriver from https://chromedriver.chromium.org/ and ensure it's in your PATH.

## Examples of Supported Scenarios

### 1. Cloudflare Protection
```python
# Automatically detected and handled
response = scraper.make_request_enhanced("https://protected-site.com")
```

### 2. JavaScript-Rendered Content
```python
page_source, url = scraper.make_request_with_selenium(
    "https://spa-site.com",
    wait_for_selector=".loaded-content",
    enable_javascript=True
)
```

### 3. Dynamic Loading
```python
# Wait for specific content to load
response = scraper.make_request_enhanced(
    "https://dynamic-site.com",
    selenium_wait_selector=".article-content"
)
```

## Google News Integration

The Google News scraper now uses this enhanced system to:
1. **Resolve redirect URLs** using Selenium when Base64 decoding fails
2. **Handle JavaScript redirects** that regular HTTP requests can't follow  
3. **Extract actual article URLs** from Google's redirect pages
4. **Bypass anti-bot measures** on news sites

## Monitoring and Debugging

Enable debug mode to see selenium activity:
```python
scraper = MyScaper("AAPL", debug=True)

# You'll see output like:
# "Request appears blocked, trying selenium fallback..."
# "Selenium: Navigating to https://example.com..."  
# "Selenium: Success! Final URL: https://actual-article.com"
```

## Migration Guide

### Existing Scrapers
No changes needed! Existing scrapers automatically get:
- Enhanced anti-bot protection
- Selenium fallback capabilities
- Performance optimizations

### New Scrapers
Inherit from `BaseScraper` and use:
```python
# Instead of:
response = requests.get(url)

# Use:
response = self.make_request_enhanced(url)
```

This integration provides robust web scraping capabilities while maintaining backward compatibility and optimizing performance through shared resources.