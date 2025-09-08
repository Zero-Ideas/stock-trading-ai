#!/usr/bin/env python3
"""
Automatic Stock Database Update Script
Identifies missing data gaps and fetches from Alpaca API to keep database current
"""

import psycopg2
import pandas as pd
from datetime import datetime, timedelta, date
from tqdm import tqdm
import logging
import sys
import os

# Alpaca API imports
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Local imports
from database_config import POSTGRES_CONFIG

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_update.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class StockDatabaseUpdater:
    def __init__(self):
        """Initialize the database updater with Alpaca API client"""
        # Alpaca API credentials (from your existing script)
        self.client = StockHistoricalDataClient(
            "PK3S7CKIFQBPLZLSV691",
            "HOXAsPCVF2v3Pz63wmRR5xrd2cLbyakoAedH3HP4"
        )
        
        # Table configurations
        self.table_configs = {
            'stock_data_day': TimeFrame.Day,
            'stock_data_hour': TimeFrame.Hour,
            'stock_data_minute': TimeFrame.Minute
        }
        
        self.conn = None
        
    def get_connection(self):
        """Create PostgreSQL connection"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(
                host=POSTGRES_CONFIG['host'],
                port=POSTGRES_CONFIG['port'],
                database=POSTGRES_CONFIG['database'],
                user=POSTGRES_CONFIG['username'],
                password=POSTGRES_CONFIG['password']
            )
            self.conn.autocommit = False
        return self.conn
    
    def get_all_symbols(self):
        """Get all unique symbols from all tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        all_symbols = set()
        
        for table_name in self.table_configs.keys():
            try:
                cursor.execute(f"SELECT DISTINCT symbol FROM {table_name}")
                symbols = [row[0] for row in cursor.fetchall()]
                all_symbols.update(symbols)
                logger.info(f"Found {len(symbols)} symbols in {table_name}")
            except psycopg2.Error as e:
                logger.error(f"Error querying {table_name}: {e}")
        
        cursor.close()
        logger.info(f"Total unique symbols across all tables: {len(all_symbols)}")
        return sorted(list(all_symbols))
    
    def get_data_gaps(self, symbol, table_name):
        """Find data gaps for a specific symbol and table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get the most recent date for this symbol
            cursor.execute(f"""
                SELECT MAX(price_timestamp::date) as max_date,
                       MIN(price_timestamp::date) as min_date,
                       COUNT(*) as total_records
                FROM {table_name} 
                WHERE symbol = %s
            """, (symbol,))
            
            result = cursor.fetchone()
            max_date = result[0]
            min_date = result[1] 
            total_records = result[2]
            
            cursor.close()
            
            if max_date is None:
                # No data exists for this symbol
                logger.info(f"{symbol} in {table_name}: No existing data")
                return None, None, 0
            
            today = date.today()
            days_behind = (today - max_date).days
            
            logger.info(f"{symbol} in {table_name}: Latest data {max_date}, {days_behind} days behind, {total_records:,} records")
            
            return max_date, min_date, total_records
            
        except psycopg2.Error as e:
            logger.error(f"Error checking gaps for {symbol} in {table_name}: {e}")
            cursor.close()
            return None, None, 0
    
    def calculate_fetch_range(self, symbol, table_name, max_date):
        """Calculate the date range to fetch based on existing data"""
        if max_date is None:
            # No existing data - fetch last 30 days
            end_date = datetime.now().date() + timedelta(days=1)
            start_date = end_date - timedelta(days=30)
            logger.info(f"{symbol}: No existing data, fetching last 30 days")
        else:
            # Fetch from 1 day before last data to 1 day after today
            start_date = max_date - timedelta(days=1)
            end_date = datetime.now().date() + timedelta(days=0)
            logger.info(f"{symbol}: Fetching from {start_date} to {end_date}")
        
        return start_date, end_date
    
    def fetch_alpaca_data(self, symbol, timeframe, start_date, end_date):
        """Fetch data from Alpaca API"""
        try:
            logger.info(f"Fetching {symbol} {timeframe} data from {start_date} to {end_date}")
            
            request_params = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=timeframe,
                start=datetime.combine(start_date, datetime.min.time()),
                end=datetime.combine(end_date, datetime.min.time())
            )
            
            # Get the data
            bars = self.client.get_stock_bars(request_params)
            df = bars.df
            
            if df.empty:
                logger.warning(f"No data returned for {symbol} {timeframe}")
                return None
            
            # Reset index to make timestamp a column
            df = df.reset_index()
            
            # Rename columns to match database schema
            df = df.rename(columns={'timestamp': 'price_timestamp'})
            
            # Add required columns
            df['symbol'] = symbol
            df['original'] = True
            
            # Reorder columns to match database schema
            df = df[[
                'symbol', 'price_timestamp', 'open', 'high', 'low', 'close',
                'volume', 'trade_count', 'vwap', 'original'
            ]]
            
            logger.info(f"Successfully fetched {len(df):,} bars for {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {symbol} {timeframe} data: {e}")
            return None
    
    def insert_data(self, df, table_name):
        """Insert data into PostgreSQL table"""
        if df is None or df.empty:
            return 0, 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Convert DataFrame to tuples for bulk insert
            data_tuples = []
            for _, row in df.iterrows():
                data_tuples.append((
                    row['symbol'],
                    row['price_timestamp'],
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    None if pd.isna(row['volume']) else int(row['volume']),
                    None if pd.isna(row['trade_count']) else int(row['trade_count']),
                    None if pd.isna(row['vwap']) else float(row['vwap']),
                    True  # original
                ))
            
            # Count records before insertion
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE symbol = %s", (df['symbol'].iloc[0],))
            records_before = cursor.fetchone()[0]
            
            # Bulk insert with conflict handling
            from psycopg2.extras import execute_values
            execute_values(
                cursor,
                f"""
                INSERT INTO {table_name} (symbol, price_timestamp, open, high, low, close, volume, trade_count, vwap, original)
                VALUES %s
                ON CONFLICT (symbol, price_timestamp) DO NOTHING
                """,
                data_tuples,
                template=None,
                page_size=10000
            )
            
            # Count records after insertion
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE symbol = %s", (df['symbol'].iloc[0],))
            records_after = cursor.fetchone()[0]
            
            new_records = records_after - records_before
            duplicates_skipped = len(df) - new_records
            
            conn.commit()
            cursor.close()
            
            logger.info(f"Inserted {new_records:,} new records, {duplicates_skipped:,} duplicates skipped")
            return new_records, duplicates_skipped
            
        except Exception as e:
            logger.error(f"Error inserting data into {table_name}: {e}")
            conn.rollback()
            cursor.close()
            return 0, 0
    
    def update_symbol(self, symbol):
        """Update a single symbol across all tables"""
        logger.info(f"=== Updating {symbol} ===")
        
        total_new_records = 0
        total_duplicates = 0
        
        for table_name, timeframe in self.table_configs.items():
            logger.info(f"Processing {symbol} for {table_name}")
            
            # Check existing data gaps
            max_date, min_date, record_count = self.get_data_gaps(symbol, table_name)
            
            # Calculate fetch range
            start_date, end_date = self.calculate_fetch_range(symbol, table_name, max_date)
            
            # Skip if already up to date
            if max_date and max_date >= datetime.now().date():
                logger.info(f"{symbol} {table_name}: Already up to date")
                continue
            
            # Fetch data from Alpaca
            df = self.fetch_alpaca_data(symbol, timeframe, start_date, end_date)
            
            if df is not None:
                # Insert data into database
                new_records, duplicates = self.insert_data(df, table_name)
                total_new_records += new_records
                total_duplicates += duplicates
            
        logger.info(f"{symbol} update complete: {total_new_records:,} new records, {total_duplicates:,} duplicates")
        return total_new_records, total_duplicates
    
    def update_all_symbols(self):
        """Update all symbols in the database"""
        logger.info("=== Starting Automatic Database Update ===")
        
        # Get all symbols from database
        symbols = self.get_all_symbols()
        
        if not symbols:
            logger.warning("No symbols found in database. Nothing to update.")
            return
        
        logger.info(f"Found {len(symbols)} symbols to update")
        
        total_symbols_updated = 0
        total_new_records = 0
        total_duplicates = 0
        
        # Progress bar for symbols
        symbol_progress = tqdm(symbols, desc="Updating symbols", unit=" symbols")
        
        for symbol in symbol_progress:
            symbol_progress.set_description(f"Updating {symbol}")
            
            try:
                new_records, duplicates = self.update_symbol(symbol)
                
                if new_records > 0:
                    total_symbols_updated += 1
                    total_new_records += new_records
                    total_duplicates += duplicates
                    
                    symbol_progress.write(f"[OK] {symbol}: {new_records:,} new records")
                else:
                    symbol_progress.write(f"[CURRENT] {symbol}: Already up to date")
                
            except Exception as e:
                symbol_progress.write(f"[ERROR] {symbol}: {e}")
                logger.error(f"Failed to update {symbol}: {e}")
        
        symbol_progress.close()
        
        # Final summary
        logger.info("=== Update Complete ===")
        logger.info(f"Symbols updated: {total_symbols_updated}/{len(symbols)}")
        logger.info(f"Total new records: {total_new_records:,}")
        logger.info(f"Total duplicates skipped: {total_duplicates:,}")
        logger.info(f"Update completed at: {datetime.now()}")
        
        if self.conn:
            self.conn.close()
    
    def update_specific_symbols(self, symbol_list):
        """Update specific symbols only"""
        logger.info(f"=== Updating Specific Symbols: {symbol_list} ===")
        
        total_new_records = 0
        total_duplicates = 0
        
        for symbol in symbol_list:
            try:
                new_records, duplicates = self.update_symbol(symbol)
                total_new_records += new_records
                total_duplicates += duplicates
            except Exception as e:
                logger.error(f"Failed to update {symbol}: {e}")
        
        logger.info(f"Specific update complete: {total_new_records:,} new records, {total_duplicates:,} duplicates")
        
        if self.conn:
            self.conn.close()


def main():
    """Main function to run the database update"""
    updater = StockDatabaseUpdater()
    
    if len(sys.argv) > 1:
        # Update specific symbols if provided as command line arguments
        symbols = sys.argv[1:]
        logger.info(f"Updating specific symbols: {symbols}")
        updater.update_specific_symbols(symbols)
    else:
        # Update all symbols
        updater.update_all_symbols()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n[INTERRUPTED] Update cancelled by user")
    except Exception as e:
        logger.error(f"\n[ERROR] Update failed: {e}")
        import traceback
        traceback.print_exc()