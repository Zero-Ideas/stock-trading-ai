#!/usr/bin/env python3
"""
Check current Selenium status and error counts
"""

from scrapers.base_scraper import BaseScraper, _SELENIUM_ERROR_COUNT, _SELENIUM_DISABLED_UNTIL, _DISABLED_SOURCES
import time

def check_selenium_status():
    """Check Selenium status"""
    print("Checking Selenium Status")
    print("=" * 30)
    
    current_time = time.time()
    
    print(f"Selenium error count: {_SELENIUM_ERROR_COUNT}")
    print(f"Disabled until: {_SELENIUM_DISABLED_UNTIL}")
    print(f"Current time: {current_time}")
    
    if _SELENIUM_DISABLED_UNTIL > current_time:
        remaining = int(_SELENIUM_DISABLED_UNTIL - current_time)
        print(f"⚠️ Selenium is DISABLED for {remaining} more seconds")
    else:
        print("✅ Selenium is ENABLED")
    
    print(f"Disabled sources: {_DISABLED_SOURCES}")
    
    # Reset selenium state for testing
    print("\nResetting Selenium state for testing...")
    import scrapers.base_scraper as bs
    bs._SELENIUM_ERROR_COUNT = 0
    bs._SELENIUM_DISABLED_UNTIL = 0
    
    print("✅ Selenium state reset")

if __name__ == "__main__":
    check_selenium_status()