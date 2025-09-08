#!/usr/bin/env python3
"""
Fixed Stock Data Transfer Script - Reliable and Safe
Addresses data loss issues with better error handling and verification
"""

# =============================================================================
# SKIP LIST - Add symbols here to skip during transfer
# =============================================================================
SKIP_SYMBOLS = [
    # Add symbols to skip here
    # 'AAPL',     # Example: Skip Apple
]

# =============================================================================

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from database_config import POSTGRES_CONFIG
from tqdm import tqdm
import glob
from datetime import datetime
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('transfer.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_connection():
    """Create PostgreSQL connection with conservative settings"""
    conn = psycopg2.connect(
        host=POSTGRES_CONFIG['host'],
        port=POSTGRES_CONFIG['port'],
        database=POSTGRES_CONFIG['database'],
        user=POSTGRES_CONFIG['username'],
        password=POSTGRES_CONFIG['password']
    )
    
    # Conservative performance settings
    conn.autocommit = False
    cursor = conn.cursor()
    
    try:
        # Reduced memory settings for stability
        cursor.execute("SET work_mem = '1028MB'")
        cursor.execute("SET maintenance_work_mem = '1028MB'")
        cursor.execute("SET synchronous_commit = off")
        conn.commit()
        logger.info("Applied PostgreSQL performance settings")
        
    except psycopg2.Error as e:
        logger.warning(f"Could not apply some performance settings: {e}")
        conn.rollback()
    
    cursor.close()
    return conn

def verify_csv_file(csv_file):
    """Verify CSV file is readable and get basic info"""
    try:
        # Quick verification without loading full file
        df_sample = pd.read_csv(csv_file, nrows=10)
        
        # Check required columns
        required_cols = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df_sample.columns]
        
        if missing_cols:
            logger.error(f"Missing columns in {csv_file}: {missing_cols}")
            return False, 0
            
        # Get total row count
        with open(csv_file, 'r') as f:
            total_rows = sum(1 for _ in f) - 1  # -1 for header
            
        return True, total_rows
        
    except Exception as e:
        logger.error(f"Cannot read CSV file {csv_file}: {e}")
        return False, 0

def transfer_single_symbol_safe(csv_file, table_name, conn):
    """Safely transfer a single symbol with full verification"""
    symbol = os.path.basename(csv_file).replace('.csv', '')
    
    # Check skip list
    if symbol in SKIP_SYMBOLS:
        logger.info(f"Skipping {symbol} (in skip list)")
        return True, 0, 0
    
    logger.info(f"Starting transfer for {symbol}")
    
    # Verify CSV file
    is_valid, expected_rows = verify_csv_file(csv_file)
    if not is_valid:
        logger.error(f"CSV verification failed for {symbol}")
        return False, 0, 0
    
    logger.info(f"{symbol}: CSV contains {expected_rows:,} rows")
    
    try:
        # Read CSV in chunks to handle large files
        chunk_size = 50000
        cursor = conn.cursor()
        
        # Check existing data
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE symbol = %s", (symbol,))
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            logger.info(f"{symbol}: Found {existing_count:,} existing rows, checking for duplicates")
        
        # Process in chunks with progress tracking
        total_inserted = 0
        total_duplicates = 0
        
        chunk_iterator = pd.read_csv(csv_file, chunksize=chunk_size, dtype={
            'volume': 'Int64',
            'trade_count': 'Int64'
        })
        
        # Progress bar
        progress = tqdm(
            total=expected_rows,
            desc=f"Transferring {symbol}",
            unit=" rows",
            leave=False
        )
        
        for chunk_num, chunk in enumerate(chunk_iterator):
            try:
                # Prepare chunk data
                if 'timestamp' in chunk.columns:
                    chunk = chunk.rename(columns={'timestamp': 'price_timestamp'})
                    
                chunk['original'] = True
                
                # Convert to tuples
                data_tuples = []
                for _, row in chunk.iterrows():
                    data_tuples.append((
                        symbol,
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
                
                # Insert with conflict handling
                rows_before = cursor.rowcount if cursor.rowcount > 0 else 0
                
                execute_values(
                    cursor,
                    f"""
                    INSERT INTO {table_name} (symbol, price_timestamp, open, high, low, close, volume, trade_count, vwap, original)
                    VALUES %s
                    ON CONFLICT (symbol, price_timestamp) DO NOTHING
                    """,
                    data_tuples,
                    template=None,
                    page_size=chunk_size
                )
                
                # Commit chunk
                conn.commit()
                
                chunk_inserted = len(chunk)
                total_inserted += chunk_inserted
                progress.update(chunk_inserted)
                progress.set_description(f"Transferring {symbol} (chunk {chunk_num + 1})")
                
            except Exception as chunk_error:
                logger.error(f"Error in chunk {chunk_num} for {symbol}: {chunk_error}")
                conn.rollback()
                progress.close()
                cursor.close()
                return False, 0, 0
        
        progress.close()
        
        # Final verification
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE symbol = %s", (symbol,))
        final_count = cursor.fetchone()[0]
        
        new_records = final_count - existing_count
        duplicates_skipped = expected_rows - new_records
        
        # Log results
        if new_records == expected_rows:
            logger.info(f"✓ {symbol}: Perfect transfer - {new_records:,} rows inserted")
        elif new_records > 0:
            logger.info(f"✓ {symbol}: Partial transfer - {new_records:,} new rows, {duplicates_skipped:,} duplicates")
        else:
            logger.warning(f"⚠ {symbol}: No new rows inserted (all duplicates)")
        
        cursor.close()
        return True, new_records, duplicates_skipped
        
    except Exception as e:
        logger.error(f"Transfer failed for {symbol}: {e}")
        if 'cursor' in locals():
            cursor.close()
        conn.rollback()
        return False, 0, 0

def transfer_missing_symbols_only():
    """Transfer only symbols that are missing from the database"""
    logger.info("=== Transferring Missing Symbols Only ===")
    
    # Get current database symbols
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT symbol FROM stock_data_minute ORDER BY symbol")
    db_symbols = set(row[0] for row in cursor.fetchall())
    cursor.close()
    
    # Get CSV symbols
    csv_files = glob.glob("StockData/hour/*.csv")
    csv_symbols = set(os.path.basename(f).replace('.csv', '') for f in csv_files)
    
    # Find missing symbols
    missing_symbols = csv_symbols - db_symbols - set(SKIP_SYMBOLS)
    
    logger.info(f"Database has: {db_symbols} symbols")
    logger.info(f"CSV files have: {len(csv_symbols)} symbols")
    logger.info(f"Missing from DB: {missing_symbols} symbols")
    logger.info(f"Will transfer: {sorted(missing_symbols)}")
    
    #if not missing_symbols:
    #    logger.info("No missing symbols found - all data is present!")
    #    conn.close()
    #    return
    #
    ## Transfer missing symbols
    #total_success = 0
    #total_rows_transferred = 0
    #
    #for symbol in sorted(missing_symbols):
    #    csv_file = f"StockData/minute/{symbol}.csv"
    #    
    #    if not os.path.exists(csv_file):
    #        logger.warning(f"CSV file not found: {csv_file}")
    #        continue
    #    
    #    success, new_rows, duplicates = transfer_single_symbol_safe(
    #        csv_file, 'stock_data_minute', conn
    #    )
    #    
    #    if success:
    #        total_success += 1
    #        total_rows_transferred += new_rows
    #        logger.info(f"✓ {symbol} completed successfully")
    #    else:
    #        logger.error(f"✗ {symbol} failed")
    #
    #conn.close()
    #
    #logger.info(f"=== Transfer Complete ===")
    #logger.info(f"Successful transfers: {total_success}/{len(missing_symbols)}")
    #logger.info(f"Total rows transferred: {total_rows_transferred:,}")

if __name__ == "__main__":
    transfer_missing_symbols_only()