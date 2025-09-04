#!/usr/bin/env python3
"""
Database Cleanup Script for Stock Sentiment Analysis
Cleans out existing database and prepares for new per-symbol table structure
"""

import psycopg2
import psycopg2.extras
import os
import sys

def get_database_config():
    """Load database configuration"""
    try:
        import database_config
        return database_config.POSTGRES_CONFIG
    except ImportError:
        print("ERROR: database_config.py not found!")
        print("Please copy database_config_example.py to database_config.py and configure your settings.")
        return None

def clean_database():
    """Clean existing database tables and prepare for new structure"""
    config = get_database_config()
    if not config:
        return False
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['username'],
            password=config['password']
        )
        
        with conn.cursor() as cursor:
            print("Cleaning existing database...")
            
            # Drop existing tables to start fresh
            print("  - Dropping existing tables...")
            cursor.execute("DROP TABLE IF EXISTS sentiment_articles CASCADE")
            cursor.execute("DROP TABLE IF EXISTS sentiment_analyses CASCADE")
            
            # Drop any existing symbol tables
            print("  - Finding existing symbol tables...")
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE tablename LIKE 'articles_%'
                AND schemaname = 'public'
            """)
            
            symbol_tables = cursor.fetchall()
            for table in symbol_tables:
                table_name = table[0]
                print(f"    - Dropping {table_name}")
                cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
            
            # Drop existing functions and views
            print("  - Dropping existing functions and views...")
            cursor.execute("DROP VIEW IF EXISTS recent_analyses CASCADE")
            cursor.execute("DROP VIEW IF EXISTS cached_analyses CASCADE")
            cursor.execute("DROP FUNCTION IF EXISTS get_cached_analysis(VARCHAR) CASCADE")
            cursor.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
            cursor.execute("DROP FUNCTION IF EXISTS create_symbol_table(VARCHAR) CASCADE")
            cursor.execute("DROP FUNCTION IF EXISTS generate_url_hash(TEXT) CASCADE")
            cursor.execute("DROP FUNCTION IF EXISTS get_recent_articles(VARCHAR, INTEGER, INTEGER) CASCADE")
            cursor.execute("DROP FUNCTION IF EXISTS url_exists_in_symbol_table(VARCHAR, TEXT) CASCADE")
            cursor.execute("DROP FUNCTION IF EXISTS insert_article_to_symbol_table(VARCHAR, TEXT, TEXT, TEXT, BOOLEAN, VARCHAR, TEXT, TIMESTAMP, DECIMAL, DECIMAL, VARCHAR, INTEGER, INTEGER, DECIMAL) CASCADE")
            cursor.execute("DROP FUNCTION IF EXISTS get_cached_analysis_with_articles(VARCHAR, DECIMAL) CASCADE")
        
        conn.commit()
        print("SUCCESS: Database cleaned successfully!")
        
        # Now recreate the schema
        print("\nRecreating database schema...")
        schema_path = os.path.join(os.path.dirname(__file__), "database_schema.sql")
        
        if not os.path.exists(schema_path):
            print(f"ERROR: Schema file not found: {schema_path}")
            return False
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        with conn.cursor() as cursor:
            cursor.execute(schema_sql)
        
        conn.commit()
        conn.close()
        
        print("SUCCESS: Database schema recreated successfully!")
        print("\nDatabase is now ready for the new per-symbol table structure!")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to clean database: {e}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("DATABASE CLEANUP SCRIPT")
    print("=" * 60)
    print("This script will:")
    print("1. Drop all existing sentiment analysis tables")
    print("2. Drop all existing per-symbol tables")
    print("3. Drop all existing functions and views")
    print("4. Recreate the new schema with per-symbol support")
    print()
    
    # Auto-proceed for batch execution
    print("Auto-proceeding with cleanup...")
    
    if clean_database():
        print("\n" + "=" * 60)
        print("SUCCESS: Database cleanup completed!")
        print("=" * 60)
        print("You can now run sentiment analysis with the new features:")
        print("- Per-symbol tables for better organization")
        print("- Duplicate URL checking")
        print("- Always save title data to database")
        print("- Improved caching and retrieval")
    else:
        print("\n" + "=" * 60)
        print("FAILED: Database cleanup failed!")
        print("=" * 60)
        print("Please check the error messages above and try again.")

if __name__ == "__main__":
    main()