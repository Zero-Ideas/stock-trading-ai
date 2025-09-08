#!/usr/bin/env python3
"""
Verify PostgreSQL Partitioning for Stock Data
Check that data is properly distributed across partitions
"""
import psycopg2
from database_config import POSTGRES_CONFIG

def verify_partitioning():
    """Verify that partitioning is working correctly"""
    conn = psycopg2.connect(
        host=POSTGRES_CONFIG['host'],
        port=POSTGRES_CONFIG['port'],
        database=POSTGRES_CONFIG['database'],
        user=POSTGRES_CONFIG['username'],
        password=POSTGRES_CONFIG['password']
    )
    cursor = conn.cursor()
    
    print("=== PostgreSQL Partitioning Verification ===\n")
    
    # Check main tables
    main_tables = ['stock_data_day', 'stock_data_hour', 'stock_data_minute']
    
    for main_table in main_tables:
        print(f"=== {main_table.upper()} ===")
        
        # Get total row count from main table
        cursor.execute(f"SELECT COUNT(*) FROM {main_table}")
        total_rows = cursor.fetchone()[0]
        print(f"Total rows in {main_table}: {total_rows:,}")
        
        if total_rows == 0:
            print("No data found in this table.\n")
            continue
            
        # Check distribution across partitions
        cursor.execute(f"""
            SELECT schemaname, relname, n_tup_ins
            FROM pg_stat_user_tables 
            WHERE schemaname = 'public' 
            AND relname LIKE '{main_table}_p%'
            ORDER BY relname
        """)
        
        partitions = cursor.fetchall()
        print(f"Data distribution across {len(partitions)} partitions:")
        
        partition_total = 0
        for schema, table, rows in partitions:
            if rows > 0:
                print(f"  {table}: {rows:,} rows")
                partition_total += rows
        
        print(f"Total rows from partitions: {partition_total:,}")
        print(f"Match with main table: {'YES' if total_rows == partition_total else 'NO'}")
        
        # Check symbols distribution
        cursor.execute(f"""
            SELECT symbol, COUNT(*) as count 
            FROM {main_table} 
            GROUP BY symbol 
            ORDER BY count DESC 
            LIMIT 10
        """)
        
        symbol_distribution = cursor.fetchall()
        print("Top 10 symbols by row count:")
        for symbol, count in symbol_distribution:
            print(f"  {symbol}: {count:,} rows")
        
        # Check date range
        cursor.execute(f"""
            SELECT MIN(price_timestamp), MAX(price_timestamp), COUNT(*)
            FROM {main_table}
        """)
        date_info = cursor.fetchone()
        if date_info[0] and date_info[1]:
            print(f"Date range: {date_info[0]} to {date_info[1]} ({date_info[2]:,} total records)")
        
        # Verify original column
        cursor.execute(f"""
            SELECT original, COUNT(*) 
            FROM {main_table} 
            GROUP BY original
        """)
        original_counts = cursor.fetchall()
        print("Original data flag distribution:")
        for original, count in original_counts:
            print(f"  original={original}: {count:,} rows")
        
        print()
    
    # Test partition pruning with a sample query
    print("=== Testing Partition Pruning ===")
    cursor.execute("EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM stock_data_day WHERE symbol = 'AAPL' LIMIT 10")
    explain_result = cursor.fetchall()
    print("Query plan for 'SELECT * FROM stock_data_day WHERE symbol = 'AAPL' LIMIT 10':")
    for line in explain_result:
        print(f"  {line[0]}")
    
    cursor.close()
    conn.close()
    
    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    verify_partitioning()