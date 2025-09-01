#!/usr/bin/env python3
"""
Analyze Google News page structure to understand how redirects work
"""

import sys
import os
import requests
from bs4 import BeautifulSoup

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.google_news_scraper import GoogleNewsScraper

def analyze_google_news_page(url: str):
    """Analyze a Google News page to understand its structure"""
    print(f"ANALYZING GOOGLE NEWS PAGE")
    print("=" * 50)
    print(f"URL: {url[:80]}...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://news.google.com/',
            'Upgrade-Insecure-Requests': '1'
        }
        
        session = requests.Session()
        response = session.get(url, headers=headers, allow_redirects=True, timeout=15)
        
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")
        print(f"Redirects: {len(response.history)}")
        print(f"Content Length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for interesting elements
            print("\n--- ANALYZING PAGE STRUCTURE ---")
            
            # Check title
            title = soup.find('title')
            if title:
                print(f"Title: {title.get_text()}")
            
            # Look for all links
            all_links = soup.find_all('a', href=True)
            print(f"Found {len(all_links)} links")
            
            external_links = []
            for link in all_links:
                href = link.get('href', '')
                if href.startswith('http') and 'google.com' not in href:
                    external_links.append((href, link.get_text(strip=True)[:50]))
            
            if external_links:
                print(f"\nFound {len(external_links)} external links:")
                for href, text in external_links[:10]:  # Show first 10
                    print(f"  {href} -> {text}")
            else:
                print("\nNo external links found in HTML")
            
            # Look for scripts that might contain the redirect logic
            scripts = soup.find_all('script')
            print(f"\nFound {len(scripts)} script tags")
            
            # Check for any script that might contain URLs
            interesting_scripts = []
            for script in scripts:
                script_content = script.get_text() if script.string else ""
                if script_content and ('http' in script_content or 'url' in script_content.lower()):
                    interesting_scripts.append(script_content[:500])  # First 500 chars
            
            if interesting_scripts:
                print(f"Found {len(interesting_scripts)} scripts with URL-like content:")
                for i, script_content in enumerate(interesting_scripts[:3]):  # Show first 3
                    print(f"\nScript {i+1}: {script_content[:300]}...")
            
            # Look for meta tags
            meta_tags = soup.find_all('meta')
            print(f"\nFound {len(meta_tags)} meta tags")
            
            for meta in meta_tags:
                if meta.get('http-equiv') or meta.get('name') in ['description', 'og:url', 'twitter:url']:
                    print(f"  {meta.get('name', meta.get('http-equiv', 'unknown'))}: {meta.get('content', 'N/A')[:100]}...")
            
            # Look for any data attributes that might contain the real URL
            all_elements = soup.find_all(attrs=lambda x: x and any(k.startswith('data-') for k in x.keys()))
            data_elements = []
            for elem in all_elements:
                for attr, value in elem.attrs.items():
                    if attr.startswith('data-') and isinstance(value, str) and len(value) > 20:
                        data_elements.append((elem.name, attr, value[:100]))
            
            if data_elements:
                print(f"\nFound {len(data_elements)} elements with data attributes:")
                for tag, attr, value in data_elements[:10]:  # Show first 10
                    print(f"  <{tag} {attr}='{value}...'>")
            
        return True
        
    except Exception as e:
        print(f"Error analyzing page: {e}")
        return False

def main():
    # Get a Google News URL to analyze
    scraper = GoogleNewsScraper("AAPL", debug=False)
    articles = scraper.scrape(max_articles=1)
    
    if not articles:
        print("No articles found")
        return
    
    google_urls = [article.url for article in articles if 'news.google.com' in article.url]
    
    if not google_urls:
        print("No Google News URLs found")
        return
    
    analyze_google_news_page(google_urls[0])

if __name__ == "__main__":
    main()