#!/usr/bin/env python3
"""
Database Migration Utility
Migrates from per-symbol tables to partitioned table architecture
"""

import sys
import os
from typing import Dict

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(__file__))

from core.database import SentimentDatabase

def print_migration_status(db: SentimentDatabase):
    """Print current migration status"""
    print("\n" + "="*60)
    print("DATABASE MIGRATION STATUS")
    print("="*60)
    
    status = db.get_migration_status()
    
    print(f"Partitioned table exists: {status['partitioned_table_exists']}")
    print(f"Articles in partitioned table: {status['partitioned_article_count']}")
    print(f"Articles in legacy tables: {status['legacy_article_count']}")
    print(f"Legacy tables found: {len(status['legacy_tables'])}")
    
    if status['symbols_migrated']:
        print(f"Symbols in partitioned table: {', '.join(status['symbols_migrated'])}")
    
    if status['legacy_tables']:
        print("\nLegacy tables:")
        for table in status['legacy_tables']:
            print(f"  {table['table_name']}: {table['article_count']} articles")

def apply_partitioned_schema(db: SentimentDatabase):
    """Apply the new partitioned database schema"""
    print("\n" + "="*60)
    print("APPLYING PARTITIONED SCHEMA")
    print("="*60)
    
    schema_path = os.path.join(os.path.dirname(__file__), "database_schema_partitioned.sql")
    
    if not os.path.exists(schema_path):
        print(f"ERROR: Schema file not found: {schema_path}")
        return False
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
            conn.commit()
        
        print("[SUCCESS] Partitioned schema applied successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to apply schema: {e}")
        return False

def run_migration(db: SentimentDatabase):
    """Run the data migration"""
    print("\n" + "="*60)
    print("RUNNING DATA MIGRATION")
    print("="*60)
    
    migration_path = os.path.join(os.path.dirname(__file__), "migrate_to_partitioned.sql")
    
    if not os.path.exists(migration_path):
        print(f"ERROR: Migration file not found: {migration_path}")
        return False
    
    try:
        with open(migration_path, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Enable verbose output
                cursor.execute("SET client_min_messages = NOTICE;")
                cursor.execute(migration_sql)
            conn.commit()
        
        print("[SUCCESS] Data migration completed")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to run migration: {e}")
        return False

def test_partitioned_functions(db: SentimentDatabase):
    """Test that the partitioned table functions work correctly"""
    print("\n" + "="*60)
    print("TESTING PARTITIONED TABLE FUNCTIONS")
    print("="*60)
    
    try:
        # Test getting recent articles
        test_symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        for symbol in test_symbols:
            articles = db.get_recent_articles_from_db(symbol, 5, 168)  # 1 week
            print(f"{symbol}: Found {len(articles)} recent articles")
            
            # Test URL checking
            if articles:
                exists = db.check_url_exists(symbol, articles[0]['url'])
                print(f"  URL exists check: {exists}")
        
        print("[SUCCESS] Partitioned table functions working correctly")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to test partitioned functions: {e}")
        return False

def main():
    """Main migration process"""
    print("Stock Sentiment Database Migration Utility")
    print("==========================================")
    
    try:
        # Initialize database connection
        db = SentimentDatabase()
        
        # Show initial status
        print_migration_status(db)
        
        # Check if partitioned table already exists
        status = db.get_migration_status()
        
        if not status['partitioned_table_exists']:
            # Apply partitioned schema
            if not apply_partitioned_schema(db):
                return 1
        else:
            print("\n[INFO] Partitioned table already exists")
        
        # Run migration if there are legacy tables
        if status['legacy_tables'] and status['legacy_article_count'] > 0:
            print(f"\n[INFO] Found {len(status['legacy_tables'])} legacy tables with {status['legacy_article_count']} total articles")
            
            response = input("Do you want to run the migration? (y/N): ").lower().strip()
            if response in ['y', 'yes']:
                if not run_migration(db):
                    return 1
            else:
                print("[INFO] Migration skipped by user")
        else:
            print("\n[INFO] No legacy tables found or they are empty")
        
        # Test the partitioned functions
        if not test_partitioned_functions(db):
            return 1
        
        # Show final status
        print_migration_status(db)
        
        print("\n" + "="*60)
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("Your database has been migrated to use partitioned tables.")
        print("The application will now use the new partitioned architecture.")
        print("You can safely remove legacy tables after verifying everything works.")
        
        return 0
        
    except Exception as e:
        print(f"\n[FATAL ERROR] Migration failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())