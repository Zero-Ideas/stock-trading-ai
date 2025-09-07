import alpaca

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
import pandas as pd
client = StockHistoricalDataClient("PK3S7CKIFQBPLZLSV691","HOXAsPCVF2v3Pz63wmRR5xrd2cLbyakoAedH3HP4")
request_params = StockBarsRequest(
  symbol_or_symbols=["AAPL"],
  timeframe=TimeFrame.Minute,
  start=datetime(2015, 9, 1),
  end=datetime(2025, 9, 6)
)
btc_bars = client.get_stock_bars(request_params)
btc_bars.df.to_csv("AAPL.csv")
# Convert to dataframe
print(btc_bars.df.tail())

