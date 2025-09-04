#!/usr/bin/env python3
"""
Simple database connection test script
Allows manual testing of PostgreSQL connection parameters
"""

import psycopg2
import os
import sys

def test_postgres_connection():
    """Test PostgreSQL connection with manual configuration"""
    print("=== PostgreSQL Connection Test ===")
    print("PostgreSQL 17 service is running. Testing connection...")
    
    # Common configurations to try
    configs = [
        # (host, port, database, user, password, description)
        ("localhost", 5432, "postgres", "postgres", "", "Default with empty password"),
        ("localhost", 5432, "postgres", "postgres", "postgres", "Default with 'postgres' password"),
        ("localhost", 5432, "postgres", "postgres", "admin", "Default with 'admin' password"),
        ("localhost", 5432, "postgres", "postgres", "password", "Default with 'password' password"),
        ("127.0.0.1", 5432, "postgres", "postgres", "", "IPv4 with empty password"),
        ("127.0.0.1", 5432, "postgres", "postgres", "postgres", "IPv4 with 'postgres' password"),
    ]
    
    print("\nTrying common configurations...")
    
    for host, port, database, user, password, description in configs:
        try:
            print(f"Testing: {description}")
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            
            # Test query
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"[SUCCESS] Connection established!")
            print(f"PostgreSQL version: {version}")
            print(f"Working configuration:")
            print(f"  Host: {host}")
            print(f"  Port: {port}")
            print(f"  Database: {database}")
            print(f"  User: {user}")
            print(f"  Password: {'(empty)' if not password else '*' * len(password)}")
            
            # Set environment variable for other scripts
            os.environ['POSTGRES_PASSWORD'] = password
            
            print(f"\nTo use this configuration, set environment variable:")
            print(f"set POSTGRES_PASSWORD={password}")
            
            return True, (host, port, database, user, password)
            
        except psycopg2.OperationalError as e:
            if "password authentication failed" in str(e):
                print(f"[FAILED] Wrong password")
            elif "does not exist" in str(e):
                print(f"[FAILED] Database/user doesn't exist")
            else:
                print(f"[FAILED] {e}")
        except Exception as e:
            print(f"[FAILED] Unexpected error: {e}")
    
    print(f"\n[ERROR] None of the common configurations worked.")
    print(f"PostgreSQL is running but may have custom authentication settings.")
    print(f"Please check your PostgreSQL configuration or pg_hba.conf file.")
    print(f"\nYou can also manually test with:")
    print(f"psql -U postgres -d postgres -h localhost")
    
    return False, None

def test_sentiment_database():
    """Test our SentimentDatabase class"""
    try:
        from core.database import SentimentDatabase
        print(f"\n=== Testing SentimentDatabase class ===")
        
        db = SentimentDatabase()
        print(f"[SUCCESS] SentimentDatabase initialized successfully!")
        return db
        
    except Exception as e:
        print(f"[ERROR] SentimentDatabase failed: {e}")
        return None

if __name__ == "__main__":
    success, config = test_postgres_connection()
    
    if success:
        print(f"\n" + "="*50)
        print(f"DATABASE CONNECTION SUCCESSFUL!")
        print(f"="*50)
        
        # Test our database class
        db = test_sentiment_database()
        
        if db:
            print(f"\nReady to proceed with:")
            print(f"1. Migration: python migrate_data_to_postgresql.py --dry-run")
            print(f"2. Testing: python sentiment.py AAPL")
        
    else:
        print(f"\n" + "="*50)
        print(f"DATABASE CONNECTION FAILED")
        print(f"="*50)
        print(f"Please check your PostgreSQL installation and authentication settings.")