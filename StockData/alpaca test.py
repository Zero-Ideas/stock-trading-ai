import alpaca

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
import pandas as pd

STOCK_SYMBOL_TO_COMPANY = {
    # Major Tech Stocks
    'AAPL': 'Apple Inc.',
    'MSFT': 'Microsoft Corporation',
    'GOOGL': 'Alphabet Inc.',
    'GOOG': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.',
    'META': 'Meta Platforms Inc.',
    'TSLA': 'Tesla Inc.',
    'NVDA': 'NVIDIA Corporation',
    'NFLX': 'Netflix Inc.',
    'CRM': 'Salesforce Inc.',
    'ORCL': 'Oracle Corporation',
    'ADBE': 'Adobe Inc.',
    'INTC': 'Intel Corporation',
    'AMD': 'Advanced Micro Devices Inc.',
    'QCOM': 'QUALCOMM Incorporated',
    'AVGO': 'Broadcom Inc.',
    'TXN': 'Texas Instruments Incorporated',
    'CSCO': 'Cisco Systems Inc.',
    
    # Financial Stocks
    'JPM': 'JPMorgan Chase & Co.',
    'BAC': 'Bank of America Corporation',
    'WFC': 'Wells Fargo & Company',
    'GS': 'The Goldman Sachs Group Inc.',
    'MS': 'Morgan Stanley',
    'C': 'Citigroup Inc.',
    'V': 'Visa Inc.',
    'MA': 'Mastercard Incorporated',
    'AXP': 'American Express Company',
    'BRK.A': 'Berkshire Hathaway Inc.',
    'BRK.B': 'Berkshire Hathaway Inc.',
    
    # Healthcare & Pharma
    'JNJ': 'Johnson & Johnson',
    'PFE': 'Pfizer Inc.',
    'MRNA': 'Moderna Inc.',
    'BNTX': 'BioNTech SE',
    'UNH': 'UnitedHealth Group Incorporated',
    'CVS': 'CVS Health Corporation',
    'ABBV': 'AbbVie Inc.',
    'LLY': 'Eli Lilly and Company',
    'TMO': 'Thermo Fisher Scientific Inc.',
    'ABT': 'Abbott Laboratories',
    
    # Consumer & Retail
    'WMT': 'Walmart Inc.',
    'HD': 'The Home Depot Inc.',
    'PG': 'The Procter & Gamble Company',
    'KO': 'The Coca-Cola Company',
    'PEP': 'PepsiCo Inc.',
    'MCD': 'McDonald\'s Corporation',
    'SBUX': 'Starbucks Corporation',
    'NKE': 'NIKE Inc.',
    'DIS': 'The Walt Disney Company',
    'AMGN': 'Amgen Inc.',
    
    # Energy & Utilities
    'XOM': 'Exxon Mobil Corporation',
    'CVX': 'Chevron Corporation',
    'COP': 'ConocoPhillips',
    'NEE': 'NextEra Energy Inc.',
    
    # Industrial & Manufacturing
    'BA': 'The Boeing Company',
    'CAT': 'Caterpillar Inc.',
    'GE': 'General Electric Company',
    'MMM': '3M Company',
    'HON': 'Honeywell International Inc.',
    'UPS': 'United Parcel Service Inc.',
    'FDX': 'FedEx Corporation',
    
    # Real Estate & REITs
    'AMT': 'American Tower Corporation',
    'CCI': 'Crown Castle Inc.',
    'PLD': 'Prologis Inc.',
    
    # Telecom
    'T': 'AT&T Inc.',
    'VZ': 'Verizon Communications Inc.',
    'TMUS': 'T-Mobile US Inc.',
    
    # Other Popular Stocks
    'SPY': 'SPDR S&P 500 ETF Trust',
    'QQQ': 'Invesco QQQ Trust',
    'IWM': 'iShares Russell 2000 ETF',
    'VTI': 'Vanguard Total Stock Market ETF',
    'GME': 'GameStop Corp.',
    'AMC': 'AMC Entertainment Holdings Inc.',
    'BB': 'BlackBerry Limited',
    'NOK': 'Nokia Corporation',
    'PLTR': 'Palantir Technologies Inc.',
    'SNOW': 'Snowflake Inc.',
    'RBLX': 'Roblox Corporation',
    'COIN': 'Coinbase Global Inc.',
    'SQ': 'Block Inc.',
    'PYPL': 'PayPal Holdings Inc.',
    'ZM': 'Zoom Video Communications Inc.',
    'UBER': 'Uber Technologies Inc.',
    'LYFT': 'Lyft Inc.',
    'SNAP': 'Snap Inc.',
    'TWTR': 'Twitter Inc.',
    'PINS': 'Pinterest Inc.',
    'SPOT': 'Spotify Technology S.A.',
    'ROKU': 'Roku Inc.',
    'DOCU': 'DocuSign Inc.',
    'CRWD': 'CrowdStrike Holdings Inc.',
    'OKTA': 'Okta Inc.',
    'ZS': 'Zscaler Inc.',
    'PANW': 'Palo Alto Networks Inc.',
    'FTNT': 'Fortinet Inc.',
}
client = StockHistoricalDataClient("PK3S7CKIFQBPLZLSV691","HOXAsPCVF2v3Pz63wmRR5xrd2cLbyakoAedH3HP4")
for symbol, name in STOCK_SYMBOL_TO_COMPANY.items():
    print(f"{symbol}")
    request_params = StockBarsRequest(
      symbol_or_symbols=[symbol],
      timeframe=TimeFrame.Day,
      start=datetime(2015, 9, 1),
      end=datetime(2025, 9, 6)
    )
    btc_bars = client.get_stock_bars(request_params)
    btc_bars.df.to_csv(f"./StockData/day/{symbol}.csv")
    # Convert to dataframe
    print(btc_bars.df.tail())
    print("="*50)
#
#