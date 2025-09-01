import requests
import pandas as pd
from datetime import datetime
import time
import csv
from typing import Optional
from bs4 import BeautifulSoup
from typing import Optional, Dict, List, Tuple
import re
class HistoricalDataGetter:
    def __init__(self):
        self.base_url = "https://finance.yahoo.com/quote/{}/history/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def date_to_timestamp(self, date_str: str) -> int:
        """Convert date string (YYYY-MM-DD) to Unix timestamp"""
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return int(time.mktime(dt.timetuple()))
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
    
    def get_historical_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Get historical stock data from Yahoo Finance by scraping the history page
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            DataFrame with historical data or None if failed
        """
        try:
            period1 = self.date_to_timestamp(start_date)
            period2 = self.date_to_timestamp(end_date)
            
            url = self.base_url.format(symbol.upper())
            params = {
                'period1': period1,
                'period2': period2
            }
            
            print(f"Fetching data from: {url}?period1={period1}&period2={period2}")
            
            # Add delay to avoid rate limiting
            time.sleep(1)
            
            # First, get the main page to establish session
            main_url = f"https://finance.yahoo.com/quote/{symbol.upper()}"
            main_response = self.session.get(main_url)
            main_response.raise_for_status()
            
            # Now get the history page
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the historical data table - try multiple selectors
            table = None
            
            # Try different table selectors
            table_selectors = [
                'table[data-test="historical-prices"]',
                'table.W\\(100\\%\\)',
                'table.yf-1jecxey',
                'table',
                '[data-test="historical-prices"] table'
            ]
            
            for selector in table_selectors:
                try:
                    table = soup.select_one(selector)
                    if table:
                        print(f"Found table using selector: {selector}")
                        break
                except:
                    continue
            
            if not table:
                print(f"Could not find data table for {symbol}")
                print("Available tables:")
                for i, t in enumerate(soup.find_all('table')):
                    print(f"  Table {i}: {t.get('class', 'no-class')}")
                return None
            
            # Extract table headers
            headers = []
            header_row = table.find('thead')
            if header_row:
                for th in header_row.find_all('th'):
                    headers.append(th.get_text().strip())
            else:
                # Fallback to first row if no thead
                first_row = table.find('tr')
                if first_row:
                    for th in first_row.find_all(['th', 'td']):
                        headers.append(th.get_text().strip())
            
            if not headers:
                print(f"Could not extract table headers for {symbol}")
                return None
            
            # Extract table data
            data = []
            tbody = table.find('tbody')
            rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]  # Skip header row if no tbody
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= len(headers):
                    row_data = []
                    for cell in cells[:len(headers)]:  # Only take as many cells as headers
                        text = cell.get_text().strip()
                        # Clean up the text (remove commas from numbers)
                        text = text.replace(',', '')
                        row_data.append(text)
                    data.append(row_data)
            
            if not data:
                print(f"No data rows found for {symbol}")
                return None
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=headers)
            
            # Convert numeric columns (skip Date column)
            for col in df.columns:
                if col.lower() != 'date':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Convert Date column
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                # Remove rows with invalid dates before setting index
                df = df.dropna(subset=['Date'])
                df = df.set_index('Date').sort_index()
            
            return df
            
        except requests.RequestException as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
        except Exception as e:
            print(f"Error processing data for {symbol}: {e}")
            return None
    
    def save_to_csv(self, data: pd.DataFrame, symbol: str, 
                   start_date: str, end_date: str, filename: Optional[str] = None):
        """
        Save historical data to CSV file
        
        Args:
            data: DataFrame with historical data
            symbol: Stock symbol
            start_date: Start date string
            end_date: End date string
            filename: Custom filename (optional)
        """
        if filename is None:
            filename = f"./HistoricalData/{symbol}_historical_{start_date}_to_{end_date}.csv"
        
        try:
            data.to_csv(filename)
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Error saving data to CSV: {e}")

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
#def main():
#    """Example usage of the HistoricalDataGetter"""
#    getter = HistoricalDataGetter()
#    
#    # Example: Get AAPL data for the last year
#    symbol = "AAPL"
#    start_date = "1975-01-01"
#    end_date = "2025-08-28"
#    
#    print(f"Fetching historical data for {symbol} from {start_date} to {end_date}")
#    data = getter.get_historical_data(symbol, start_date, end_date)
#    
#    if data is not None:
#        print(f"Retrieved {len(data)} trading days of data")
#        print("\nFirst few rows:")
#        
#        data.rename(columns={"Close   Close price adjusted for splits.": "close split","Adj Close   Adjusted close price adjusted for splits and dividend and/or capital gain distributions.":"Close splits and dividend"}, inplace=True)
#        print(data.head(50))
#        # Save to CSV
#        getter.save_to_csv(data, symbol, start_date, end_date)
#    else:
#        print("Failed to retrieve data")

#if __name__ == "__main__":
#    main()