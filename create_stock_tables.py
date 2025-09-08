#!/usr/bin/env python3
"""
Create PostgreSQL tables for stock data
"""
import psycopg2
from database_config import POSTGRES_CONFIG
import sys

def create_stock_tables():
    """Create the stock data tables using the SQL schema"""
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=POSTGRES_CONFIG['host'],
            port=POSTGRES_CONFIG['port'],
            database=POSTGRES_CONFIG['database'],
            user=POSTGRES_CONFIG['username'],
            password=POSTGRES_CONFIG['password']
        )
        
        cursor = conn.cursor()
        
        # Read the SQL schema file
        with open('stock_data_schema.sql', 'r') as f:
            schema_sql = f.read()
        
        print("Creating stock data tables...")
        
        # Execute the schema
        cursor.execute(schema_sql)
        conn.commit()
        
        print("[OK] Stock data tables created successfully!")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'stock_data_%'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        sys.exit(1)
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_stock_tables()