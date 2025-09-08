#!/usr/bin/env python3
"""
Transfer Stock Data from CSV files to PostgreSQL
Transfers all CSV files from day, hour, and minute directories to respective PostgreSQL tables
"""

# =============================================================================
# SKIP LIST - Add symbols here to skip during transfer
# =============================================================================
SKIP_SYMBOLS = ['CRM', 'GS', 'HD', 'BRK.A', 'AMT', 'FDX', 'CCI', 'BA', 'MSFT', 'UPS', 'C', 'T', 'LLY', 'XOM', 'PYPL', 'SNOW', 'CVS', 'BB', 'COIN', 'TMUS', 'LYFT', 'NKE', 'PLTR', 'TWTR', 'UBER', 'WMT', 'VTI', 'CAT', 'AMD', 'ABT', 'GME', 'AXP', 'SPOT', 'BAC', 'QQQ', 'CRWD', 'ORCL', 'INTC', 'JPM', 'QCOM', 'SPY', 'PLD', 'JNJ', 'TSLA', 'DIS', 'FTNT', 'TMO', 'MA', 'OKTA', 'ZS', 'MRNA', 'MMM', 'CVX', 'PANW', 'PINS', 'ABBV', 'MCD', 'DOCU', 'ROKU', 'AMC', 'VZ', 'NEE', 'NFLX', 'PG', 'UNH', 'AMGN', 'GE', 'SBUX', 'NOK', 'CSCO', 'AAPL', 'ZM', 'PFE', 'ADBE', 'NVDA', 'GOOGL', 'PEP', 'TXN', 'KO', 'SQ', 'SNAP', 'COP', 'WFC', 'AMZN', 'RBLX', 'HON', 'V', 'META', 'BNTX', 'IWM', 'MS', 'AVGO', 'BRK.B']
print(f"SKIP_SYMBOLS: {len(SKIP_SYMBOLS)}")
# =============================================================================

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch, execute_values
from database_config import POSTGRES_CONFIG
from tqdm import tqdm
import glob
from datetime import datetime
import io
import sys

def get_connection():
    """Create PostgreSQL connection with performance optimizations"""
    conn = psycopg2.connect(
        host=POSTGRES_CONFIG['host'],
        port=POSTGRES_CONFIG['port'],
        database=POSTGRES_CONFIG['database'],
        user=POSTGRES_CONFIG['username'],
        password=POSTGRES_CONFIG['password']
    )
    
    # Performance optimizations
    conn.autocommit = False  # Use transactions
    cursor = conn.cursor()
    
    try:
        # Increase work_mem for this session (helps with sorting/indexing)
        cursor.execute("SET work_mem = '1024MB'")
        
        # Increase maintenance_work_mem (helps with index creation)
        cursor.execute("SET maintenance_work_mem = '1024MB'")
        
        # Disable synchronous_commit for this session (faster commits)
        cursor.execute("SET synchronous_commit = off")
        
        conn.commit()  # Commit the settings
        
    except psycopg2.Error as e:
        # Some settings might not be available in all PostgreSQL versions
        print(f"[WARNING] Could not apply some performance settings: {e}")
        conn.rollback()  # Rollback failed settings
    
    cursor.close()
    return conn

def transfer_csv_fast_copy(csv_file, table_name, conn, update_duplicates=False):
    """Ultra-fast CSV transfer using PostgreSQL COPY command with proper progress tracking"""
    symbol = os.path.basename(csv_file).replace('.csv', '')
    
    # Check skip list
    if symbol in SKIP_SYMBOLS:
        print(f"[SKIP] Skipping {symbol} (in skip list)")
        return 0, symbol, 0, 0
    
    try:
        # Read CSV file efficiently
        df = pd.read_csv(csv_file, dtype={
            'volume': 'Int64',
            'trade_count': 'Int64'
        })
        
        # Rename timestamp column to match database schema
        if 'timestamp' in df.columns:
            df = df.rename(columns={'timestamp': 'price_timestamp'})
        
        # Add required columns
        df['original'] = True
        
        total_rows = len(df)
        cursor = conn.cursor()
        
        # Count existing records for this symbol to track duplicates
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE symbol = %s", (symbol,))
        existing_count_before = cursor.fetchone()[0]
        
        # Create progress bar that works properly
        progress_bar = tqdm(
            total=total_rows, 
            desc=f"Processing {symbol}", 
            unit=' rows',
            position=1,
            leave=False,
            file=sys.stdout,
            dynamic_ncols=True
        )
        
        if update_duplicates or existing_count_before == 0:
            # Use COPY for maximum speed when no duplicates expected or updating
            
            # Reorder columns to match database schema
            df_ordered = df[[
                'symbol', 'price_timestamp', 'open', 'high', 'low', 'close', 
                'volume', 'trade_count', 'vwap', 'original'
            ]]
            
            # Create CSV buffer in memory
            progress_bar.set_description(f"Preparing {symbol}")
            csv_buffer = io.StringIO()
            df_ordered.to_csv(csv_buffer, index=False, header=False, na_rep='\\N')
            csv_buffer.seek(0)
            progress_bar.update(total_rows // 4)  # 25% for preparation
            
            if update_duplicates:
                # Create temporary table for COPY, then merge
                temp_table = f"{table_name}_temp_{symbol.replace('.', '_')}"
                
                progress_bar.set_description(f"Creating temp table {symbol}")
                cursor.execute(f"""
                    CREATE TEMP TABLE {temp_table} (LIKE {table_name} INCLUDING DEFAULTS)
                """)
                progress_bar.update(total_rows // 4)  # 50% total
                
                # COPY to temp table
                progress_bar.set_description(f"COPY {symbol} to temp")
                cursor.copy_expert(f"""
                    COPY {temp_table} (symbol, price_timestamp, open, high, low, close, volume, trade_count, vwap, original)
                    FROM STDIN WITH CSV
                """, csv_buffer)
                progress_bar.update(total_rows // 4)  # 75% total
                
                # Merge from temp table with conflict resolution
                progress_bar.set_description(f"Merging {symbol}")
                cursor.execute(f"""
                    INSERT INTO {table_name} 
                    SELECT * FROM {temp_table}
                    ON CONFLICT (symbol, price_timestamp) 
                    DO UPDATE SET 
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        trade_count = EXCLUDED.trade_count,
                        vwap = EXCLUDED.vwap,
                        original = EXCLUDED.original
                """)
                
                cursor.execute(f"DROP TABLE {temp_table}")
                progress_bar.update(total_rows // 4)  # 100% total
                
            else:
                # Direct COPY with duplicate handling via temp table
                temp_table = f"{table_name}_temp_{symbol.replace('.', '_')}"
                
                progress_bar.set_description(f"Creating temp table {symbol}")
                cursor.execute(f"""
                    CREATE TEMP TABLE {temp_table} (LIKE {table_name} INCLUDING DEFAULTS)
                """)
                progress_bar.update(total_rows // 4)  # 50% total
                
                # COPY to temp table
                progress_bar.set_description(f"COPY {symbol} data")
                cursor.copy_expert(f"""
                    COPY {temp_table} (symbol, price_timestamp, open, high, low, close, volume, trade_count, vwap, original)
                    FROM STDIN WITH CSV
                """, csv_buffer)
                progress_bar.update(total_rows // 4)  # 75% total
                
                # Insert only new records
                progress_bar.set_description(f"Inserting {symbol}")
                cursor.execute(f"""
                    INSERT INTO {table_name} 
                    SELECT t.* FROM {temp_table} t
                    WHERE NOT EXISTS (
                        SELECT 1 FROM {table_name} m 
                        WHERE m.symbol = t.symbol 
                        AND m.price_timestamp = t.price_timestamp
                    )
                """)
                
                cursor.execute(f"DROP TABLE {temp_table}")
                progress_bar.update(total_rows // 4)  # 100% total
            
            conn.commit()
            
        else:
            # Use execute_values for existing data with duplicates
            progress_bar.set_description(f"Preparing {symbol} data")
            data_tuples = []
            batch_size = 25000
            processed = 0
            
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
                
                processed += 1
                if processed % batch_size == 0:
                    progress_bar.update(batch_size)
                    progress_bar.set_description(f"Bulk insert {symbol} ({processed:,}/{total_rows:,})")
                    
                    # Insert batch
                    execute_values(
                        cursor,
                        f"""
                        INSERT INTO {table_name} (symbol, price_timestamp, open, high, low, close, volume, trade_count, vwap, original)
                        VALUES %s
                        ON CONFLICT (symbol, price_timestamp) DO NOTHING
                        """,
                        data_tuples,
                        template=None,
                        page_size=batch_size
                    )
                    conn.commit()
                    data_tuples = []
            
            # Insert remaining data
            if data_tuples:
                execute_values(
                    cursor,
                    f"""
                    INSERT INTO {table_name} (symbol, price_timestamp, open, high, low, close, volume, trade_count, vwap, original)
                    VALUES %s
                    ON CONFLICT (symbol, price_timestamp) DO NOTHING
                    """,
                    data_tuples,
                    template=None,
                    page_size=len(data_tuples)
                )
                conn.commit()
                progress_bar.update(len(data_tuples))
        
        progress_bar.close()
        
        # Count records after insertion to calculate new inserts
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE symbol = %s", (symbol,))
        existing_count_after = cursor.fetchone()[0]
        
        new_records = existing_count_after - existing_count_before
        duplicates_skipped = total_rows - new_records
        
        cursor.close()
        return total_rows, symbol, new_records, duplicates_skipped
        
    except Exception as e:
        print(f"[ERROR] Failed to transfer {csv_file}: {e}")
        if 'progress_bar' in locals():
            progress_bar.close()
        if 'cursor' in locals():
            cursor.close()
        return 0, symbol, 0, 0

def transfer_csv_batch(csv_file, table_name, conn, batch_size=50000, update_duplicates=False):
    """Transfer a single CSV file to PostgreSQL table - redirects to fast COPY method"""
    return transfer_csv_fast_copy(csv_file, table_name, conn, update_duplicates)

def transfer_all_data():
    """Transfer all CSV files to PostgreSQL"""
    print("=== Stock Data Transfer Script ===")
    print("Transferring CSV data to PostgreSQL with partitioning...")
    
    # Show skip list if not empty
    if SKIP_SYMBOLS:
        print(f"\n[INFO] Skipping symbols: {', '.join(SKIP_SYMBOLS)}")
    
    # Define directories and their corresponding table names
    transfer_configs = [
        ('StockData/minute', 'stock_data_minute')
    ]
    
    total_files_transferred = 0
    total_rows_transferred = 0
    total_files_skipped = 0
    
    conn = get_connection()
    
    for directory, table_name in transfer_configs:
        if not os.path.exists(directory):
            print(f"[SKIP] Directory {directory} does not exist")
            continue
            
        # Get all CSV files in directory
        csv_files = glob.glob(os.path.join(directory, '*.csv'))
        
        if not csv_files:
            print(f"[SKIP] No CSV files found in {directory}")
            continue
        
        # Filter out skipped files
        original_count = len(csv_files)
        csv_files = [f for f in csv_files if os.path.basename(f).replace('.csv', '') not in SKIP_SYMBOLS]
        skipped_count = original_count - len(csv_files)
        total_files_skipped += skipped_count
            
        print(f"\n=== Transferring {len(csv_files)} files from {directory} to {table_name} ===")
        if skipped_count > 0:
            print(f"[INFO] Skipping {skipped_count} files due to skip list")
        
        # Progress bar for files in this directory
        file_progress = tqdm(
            csv_files, 
            desc=f"Processing {directory}",
            position=0,
            leave=True,
            file=sys.stdout,
            dynamic_ncols=True
        )
        
        directory_files_transferred = 0
        directory_rows_transferred = 0
        
        for csv_file in file_progress:
            symbol = os.path.basename(csv_file).replace('.csv', '')
            file_progress.set_description(f"Processing {directory} - Current: {symbol}")
            
            total_rows, symbol, new_records, duplicates_skipped = transfer_csv_batch(csv_file, table_name, conn)
            
            if total_rows > 0:
                directory_files_transferred += 1
                directory_rows_transferred += new_records
                if duplicates_skipped > 0:
                    file_progress.write(f"[OK] {symbol}: {new_records:,} new rows, {duplicates_skipped:,} duplicates skipped")
                else:
                    file_progress.write(f"[OK] {symbol}: {new_records:,} rows")
            elif total_rows == 0 and symbol not in SKIP_SYMBOLS:
                file_progress.write(f"[ERROR] {symbol}: Failed")
            # Skip symbols are already handled with their own message
        
        file_progress.close()
        
        print(f"[SUMMARY] {directory}: {directory_files_transferred} files processed, {directory_rows_transferred:,} rows transferred")
        total_files_transferred += directory_files_transferred
        total_rows_transferred += directory_rows_transferred
    
    conn.close()
    
    print(f"\n=== FINAL SUMMARY ===")
    print(f"Total files transferred: {total_files_transferred}")
    print(f"Total rows transferred: {total_rows_transferred:,}")
    print(f"Transfer completed at: {datetime.now()}")

def verify_data():
    """Verify the transferred data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("\n=== DATA VERIFICATION ===")
    
    # Check row counts for each table
    tables = ['stock_data_day', 'stock_data_hour', 'stock_data_minute']
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{table}: {count:,} rows")
        
        # Check number of unique symbols
        cursor.execute(f"SELECT COUNT(DISTINCT symbol) FROM {table}")
        symbols = cursor.fetchone()[0]
        print(f"  - Unique symbols: {symbols}")
        
        # Check date range
        cursor.execute(f"SELECT MIN(price_timestamp), MAX(price_timestamp) FROM {table}")
        date_range = cursor.fetchone()
        if date_range[0] and date_range[1]:
            print(f"  - Date range: {date_range[0]} to {date_range[1]}")
        
        # Check sample of data
        cursor.execute(f"SELECT symbol, price_timestamp, close, volume, original FROM {table} ORDER BY price_timestamp DESC LIMIT 3")
        samples = cursor.fetchall()
        print(f"  - Sample data:")
        for sample in samples:
            print(f"    {sample[0]}: {sample[1]} | Close: ${sample[2]:.2f} | Vol: {sample[3]:,} | Original: {sample[4]}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    print("=== Stock Data Transfer Script ===")
    print("Transferring CSV data to PostgreSQL with partitioning...")
    
    try:
        transfer_all_data()
        verify_data()
        
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Transfer cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] Transfer failed: {e}")
        import traceback
        traceback.print_exc()