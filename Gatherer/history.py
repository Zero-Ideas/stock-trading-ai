import requests
import csv
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import time
from bs4 import BeautifulSoup
import re
import json
import random

class CustomStockScraper:
    def __init__(self, data_dir: str = "./Data"):
        """Initialize the custom stock scraper with a data directory."""
        self.data_dir = data_dir
        self.ensure_data_directory()
        
        # Common headers to mimic a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Session for connection pooling and cookie persistence
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def ensure_data_directory(self):
        """Create data directory if it doesn't exist."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def random_delay(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """Add random delay to avoid being detected as a bot."""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def get_current_price_google_finance(self, symbol: str) -> Optional[Dict]:
        """
        Scrape current stock price from Google Finance.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
            
        Returns:
            Dictionary with current price data or None
        """
        try:
            url = f"https://www.google.com/finance/quote/{symbol}:NASDAQ"
            
            print(f"Scraping Google Finance for {symbol}...")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find the price element (Google Finance changes these frequently)
            price_selectors = [
                'div[class*="YMlKec fxKbKc"]',
                'div[class*="YMlKec"]', 
                'span[class*="IsqQVc NprOob XcVN5d"]',
                'div.YMlKec.fxKbKc',
                '[data-last-price]'
            ]
            
            current_price = None
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text().strip()
                    # Extract numeric value
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                    if price_match:
                        current_price = float(price_match.group())
                        break
            
            if not current_price:
                print(f"Could not find price for {symbol} on Google Finance")
                return None
            
            # Try to get additional info
            change_element = soup.select_one('span[class*="JwB6zf"]')
            change_percent_element = soup.select_one('span[class*="NegFNd"]')
            
            result = {
                'symbol': symbol,
                'price': current_price,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'time': datetime.now().strftime('%H:%M:%S'),
                'source': 'Google Finance'
            }
            
            if change_element:
                change_text = change_element.get_text().strip()
                change_match = re.search(r'[+-]?[\d,]+\.?\d*', change_text.replace(',', ''))
                if change_match:
                    result['change'] = float(change_match.group())
            
            if change_percent_element:
                percent_text = change_percent_element.get_text().strip()
                percent_match = re.search(r'[+-]?[\d,]+\.?\d*', percent_text.replace(',', '').replace('%', ''))
                if percent_match:
                    result['change_percent'] = float(percent_match.group())
            
            print(f"Successfully scraped {symbol}: ${current_price}")
            return result
            
        except requests.RequestException as e:
            print(f"Network error scraping {symbol} from Google Finance: {e}")
            return None
        except Exception as e:
            print(f"Error scraping {symbol} from Google Finance: {e}")
            return None
    
    def get_current_price_yahoo_finance_web(self, symbol: str) -> Optional[Dict]:
        """
        Scrape current stock price from Yahoo Finance website.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
            
        Returns:
            Dictionary with current price data or None
        """
        try:
            url = f"https://finance.yahoo.com/quote/{symbol}"
            
            print(f"Scraping Yahoo Finance website for {symbol}...")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Yahoo Finance price selectors (these change frequently)
            price_selectors = [
                'fin-streamer[data-symbol="' + symbol + '"][data-field="regularMarketPrice"]',
                'span[data-reactid*="32"]',
                'span.Trsdu\\(0\\.3s\\)',
                '[data-field="regularMarketPrice"]'
            ]
            
            current_price = None
            for selector in price_selectors:
                try:
                    price_element = soup.select_one(selector)
                    if price_element:
                        price_text = price_element.get('value') or price_element.get_text()
                        if price_text:
                            price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                            if price_match:
                                current_price = float(price_match.group())
                                break
                except:
                    continue
            
            # Alternative: Look for JSON data in script tags
            if not current_price:
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'QuoteSummaryStore' in script.string:
                        try:
                            # Extract JSON data
                            json_start = script.string.find('{"QuoteSummaryStore"')
                            json_end = script.string.find('}}};', json_start) + 3
                            json_str = script.string[json_start:json_end]
                            data = json.loads(json_str)
                            
                            price_data = data.get('QuoteSummaryStore', {}).get('price', {})
                            if price_data:
                                current_price = price_data.get('regularMarketPrice', {}).get('raw')
                                if current_price:
                                    break
                        except:
                            continue
            
            if not current_price:
                print(f"Could not find price for {symbol} on Yahoo Finance")
                return None
            
            result = {
                'symbol': symbol,
                'price': current_price,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'time': datetime.now().strftime('%H:%M:%S'),
                'source': 'Yahoo Finance Web'
            }
            
            print(f"Successfully scraped {symbol}: ${current_price}")
            return result
            
        except requests.RequestException as e:
            print(f"Network error scraping {symbol} from Yahoo Finance: {e}")
            return None
        except Exception as e:
            print(f"Error scraping {symbol} from Yahoo Finance: {e}")
            return None
    
    def get_current_price_marketwatch(self, symbol: str) -> Optional[Dict]:
        """
        Scrape current stock price from MarketWatch.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
            
        Returns:
            Dictionary with current price data or None
        """
        try:
            url = f"https://www.marketwatch.com/investing/stock/{symbol.lower()}"
            
            print(f"Scraping MarketWatch for {symbol}...")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # MarketWatch price selectors
            price_selectors = [
                'bg-quote[class*="value"]',
                'h2.intraday__price span',
                '.intraday__price .value',
                '[data-module="LastPrice"]'
            ]
            
            current_price = None
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text().strip()
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', '').replace('$', ''))
                    if price_match:
                        current_price = float(price_match.group())
                        break
            
            if not current_price:
                print(f"Could not find price for {symbol} on MarketWatch")
                return None
            
            result = {
                'symbol': symbol,
                'price': current_price,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'time': datetime.now().strftime('%H:%M:%S'),
                'source': 'MarketWatch'
            }
            
            print(f"Successfully scraped {symbol}: ${current_price}")
            return result
            
        except requests.RequestException as e:
            print(f"Network error scraping {symbol} from MarketWatch: {e}")
            return None
        except Exception as e:
            print(f"Error scraping {symbol} from MarketWatch: {e}")
            return None
    
    def get_current_price_cnbc(self, symbol: str) -> Optional[Dict]:
        """
        Scrape current stock price from CNBC.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
            
        Returns:
            Dictionary with current price data or None
        """
        try:
            url = f"https://www.cnbc.com/quotes/{symbol}"
            
            print(f"Scraping CNBC for {symbol}...")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # CNBC price selectors
            price_selectors = [
                'span[class*="QuoteStrip-lastPrice"]',
                '.QuoteStrip-lastPrice',
                '[data-module="LastPrice"]'
            ]
            
            current_price = None
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text().strip()
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', '').replace('$', ''))
                    if price_match:
                        current_price = float(price_match.group())
                        break
            
            if not current_price:
                print(f"Could not find price for {symbol} on CNBC")
                return None
            
            result = {
                'symbol': symbol,
                'price': current_price,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'time': datetime.now().strftime('%H:%M:%S'),
                'source': 'CNBC'
            }
            
            print(f"Successfully scraped {symbol}: ${current_price}")
            return result
            
        except requests.RequestException as e:
            print(f"Network error scraping {symbol} from CNBC: {e}")
            return None
        except Exception as e:
            print(f"Error scraping {symbol} from CNBC: {e}")
            return None
    
    def get_stock_price_multi_source(self, symbol: str, sources: List[str] = None) -> List[Dict]:
        """
        Get stock price from multiple sources for comparison.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
            sources: List of sources to try (default: all available)
            
        Returns:
            List of dictionaries with price data from different sources
        """
        if sources is None:
            sources = ['google', 'yahoo', 'marketwatch', 'cnbc']
        
        results = []
        source_methods = {
            'google': self.get_current_price_google_finance,
            'yahoo': self.get_current_price_yahoo_finance_web,
            'marketwatch': self.get_current_price_marketwatch,
            'cnbc': self.get_current_price_cnbc 
        }
        
        for source in sources:
            if source in source_methods:
                try:
                    result = source_methods[source](symbol)
                    if result:
                        results.append(result)
                    
                    # Add delay between requests to be respectful
                    self.random_delay(2, 4)
                    
                except Exception as e:
                    print(f"Error with {source} for {symbol}: {e}")
                    continue
        
        return results
    
    def collect_historical_data_points(self, symbol: str, days: int = 30, 
                                     interval_hours: int = 24) -> List[Dict]:
        """
        Collect multiple data points over time by running the scraper periodically.
        Note: This is meant to be run over time, not all at once.
        
        Args:
            symbol: Stock symbol
            days: Number of days to collect data
            interval_hours: Hours between data collection
            
        Returns:
            List of historical data points
        """
        print(f"Starting data collection for {symbol} over {days} days")
        print(f"This will take approximately {days * interval_hours} hours to complete")
        
        data_points = []
        end_date = datetime.now() + timedelta(days=days)
        
        while datetime.now() < end_date:
            # Get current price from the most reliable source
            price_data = self.get_current_price_google_finance(symbol)
            
            if not price_data:
                # Fallback to other sources
                sources = ['yahoo', 'marketwatch', 'cnbc']
                for source in sources:
                    if source == 'yahoo':
                        price_data = self.get_current_price_yahoo_finance_web(symbol)
                    elif source == 'marketwatch':
                        price_data = self.get_current_price_marketwatch(symbol)
                    elif source == 'cnbc':
                        price_data = self.get_current_price_cnbc(symbol)
                    
                    if price_data:
                        break
            
            if price_data:
                data_points.append(price_data)
                print(f"Collected data point {len(data_points)} for {symbol}")
            else:
                print(f"Failed to collect data point for {symbol}")
            
            # Wait for the specified interval
            print(f"Waiting {interval_hours} hours until next collection...")
            time.sleep(interval_hours * 3600)  # Convert hours to seconds
        
        return data_points
    
    def save_to_csv(self, data: List[Dict], symbol: str, filename: Optional[str] = None):
        """
        Save scraped stock data to CSV file.
        
        Args:
            data: List of dictionaries containing stock data
            symbol: Stock symbol for filename
            filename: Optional custom filename
        """
        if not data:
            print("No data to save")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_scraped_data_{timestamp}.csv"
        
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(data)
            
            print(f"Data successfully saved to: {filepath}")
            print(f"Total records: {len(data)}")
            
        except Exception as e:
            print(f"Error saving data to CSV: {e}")


def main():
    """Example usage of the CustomStockScraper class."""
    
    # Initialize the scraper
    scraper = CustomStockScraper(data_dir="./ScrapedData")
    
    print("=== Custom Stock Web Scraper ===")
    print("Warning: Web scraping can be unreliable due to website changes and anti-bot measures")
    print("Consider using official APIs for production use.")
    print()
    
    # Example 1: Get current price from multiple sources
    symbol = "AAPL"
    print(f"=== Getting current price for {symbol} from multiple sources ===")
    
    results = scraper.get_stock_price_multi_source(symbol)
    
    if results:
        print(f"\nPrice comparison for {symbol}:")
        for result in results:
            source = result.get('source', 'Unknown')
            price = result.get('price', 'N/A')
            print(f"{source}: ${price}")
        
        # Calculate average price
        prices = [r['price'] for r in results if 'price' in r]
        if prices:
            avg_price = sum(prices) / len(prices)
            print(f"\nAverage price: ${avg_price:.2f}")
        
        # Save results
        scraper.save_to_csv(results, symbol)
    else:
        print(f"Could not get price data for {symbol}")
    
    # Example 2: Get prices for multiple stocks
    print(f"\n=== Getting prices for multiple stocks ===")
    symbols = ["AAPL", "GOOGL", "MSFT"]
    
    all_data = []
    for symbol in symbols:
        print(f"\nProcessing {symbol}...")
        
        # Try Google Finance first (usually most reliable)
        price_data = scraper.get_current_price_google_finance(symbol)
        
        if not price_data:
            # Fallback to Yahoo Finance
            price_data = scraper.get_current_price_yahoo_finance_web(symbol)
        
        if price_data:
            all_data.append(price_data)
        
        # Be respectful - add delay between requests
        scraper.collect_historical_data_points(symbol)  # No actual waiting
        scraper.random_delay(1, 3)
    
    if all_data:
        scraper.save_to_csv(all_data, "multiple_stocks")
        
        print("\nSummary:")
        for data in all_data:
            print(f"{data['symbol']}: ${data['price']} ({data['source']})")
    
    print("\n=== Important Notes ===")
    print("1. Web scraping financial sites may violate their Terms of Service")
    print("2. These sites implement anti-bot measures that can block requests")
    print("3. HTML structure changes frequently, breaking scrapers")
    print("4. For reliable historical data, consider using official APIs")
    print("5. Always add delays between requests to be respectful")


if __name__ == "__main__":
    main()