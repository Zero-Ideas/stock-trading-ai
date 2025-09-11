import alpaca
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
import pandas as pd
from tqdm import tqdm
import time
import threading

# Get Alpaca credentials from environment variables
alpaca_key_id = os.getenv('ALPACA_API_KEY_ID')
alpaca_secret_key = os.getenv('ALPACA_SECRET_KEY')

if not alpaca_key_id or not alpaca_secret_key:
    raise ValueError("Alpaca API credentials must be set in environment variables: ALPACA_API_KEY_ID, ALPACA_SECRET_KEY")

client = StockHistoricalDataClient(alpaca_key_id, alpaca_secret_key)


STOCK_SYMBOL_TO_COMPANY = {
    # Major Tech Stocksw
    'GOOG': 'GOOGLE',
}

total_symbols = len(STOCK_SYMBOL_TO_COMPANY)
symbol_progress = tqdm(total=total_symbols, desc="Processing symbols", position=0)

for symbol, company_name in STOCK_SYMBOL_TO_COMPANY.items():
    try:
        symbol_progress.set_description(f"Processing {symbol}")
        
        # Create a spinner-like progress for fetching
        fetch_progress = tqdm(desc=f"Fetching {symbol} data", position=1, leave=False)
        fetch_progress.set_postfix_str("Contacting API...")
        
        request_params = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Minute,
            start=datetime(2025, 9, 5),
            end=datetime(2025, 9, 7)
        )
        
        fetch_progress.set_postfix_str("Downloading data...")
        # Get the data (this may involve multiple API calls internally)
        bars = client.get_stock_bars(request_params)
        
        fetch_progress.set_postfix_str("Processing response...")
        # Convert to DataFrame to get row count
        df = bars.df
        
        print(df.tail())
    except Exception as e:
        if 'fetch_progress' in locals():
            fetch_progress.close()


symbol_progress.close()