#!/usr/bin/env python3
"""
Database Setup and Configuration Script
Helps set up PostgreSQL database for sentiment analysis caching
"""

import os
import getpass
import psycopg2
from core.database import SentimentDatabase

def test_connection(host="localhost", port=5432, database="postgres", username="sudo", password="sudo"):
    """Test PostgreSQL connection with given parameters"""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password
        )
        conn.close()
        return True, "Connection successful"
    except psycopg2.OperationalError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"

def interactive_setup():
    """Interactive setup for PostgreSQL connection"""
    print("=== PostgreSQL Database Setup ===")
    print("This script will help you configure PostgreSQL for sentiment analysis caching.")
    print()
    
    # Get connection parameters
    host = input("PostgreSQL host [localhost]: ").strip() or "localhost"
    port = input("PostgreSQL port [5432]: ").strip() or "5432"
    username = input("PostgreSQL username [postgres]: ").strip() or "postgres"
    
    try:
        port = int(port)
    except ValueError:
        print("Invalid port number, using 5432")
        port = 5432
    
    # Try common passwords first
    common_passwords = ["postgres", "", "admin", "password"]
    password = None
    
    print(f"\nTesting connection to {host}:{port} as user '{username}'...")
    
    # Try common passwords
    for pwd in common_passwords:
        print(f"Trying password: {'(empty)' if not pwd else '*' * len(pwd)}")
        success, message = test_connection(host, port, "postgres", username, pwd)
        if success:
            password = pwd
            print("[SUCCESS] Connection established!")
            break
        else:
            print(f"[FAILED] {message}")
    
    # If common passwords don't work, ask user
    if password is None:
        print("\nCommon passwords didn't work. Please enter your PostgreSQL password:")
        while True:
            password = getpass.getpass("Password: ")
            success, message = test_connection(host, port, "postgres", username, password)
            if success:
                print("[SUCCESS] Connection established!")
                break
            else:
                print(f"[FAILED] {message}")
                retry = input("Try again? (y/n): ").strip().lower()
                if retry != 'y':
                    print("Setup cancelled.")
                    return None
    
    # Test with our database class
    try:
        print(f"\nTesting with SentimentDatabase class...")
        os.environ['POSTGRES_PASSWORD'] = password
        db = SentimentDatabase(host=host, port=port, username=username, password=password)
        print("[SUCCESS] Database setup completed successfully!")
        
        # Save configuration
        config = f"""# PostgreSQL Configuration
# Add these to your environment variables or .env file
POSTGRES_HOST={host}
POSTGRES_PORT={port}
POSTGRES_DATABASE=stock_sentiment
POSTGRES_USERNAME={username}
POSTGRES_PASSWORD={password}
"""
        
        with open("database_config.txt", "w") as f:
            f.write(config)
        
        print(f"\nConfiguration saved to: database_config.txt")
        print("You can set these as environment variables or modify core/database.py")
        
        return db
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize SentimentDatabase: {e}")
        return None

def main():
    """Main setup function"""
    print("Stock Sentiment Analysis - Database Setup")
    print("=" * 50)
    
    # Check if PostgreSQL is installed
    try:
        import psycopg2
        print("[SUCCESS] psycopg2 is installed")
    except ImportError:
        print("[ERROR] psycopg2 not installed. Run: pip install psycopg2-binary")
        return
    
    # Interactive setup
    db = interactive_setup()
    
    if db:
        print("\n=== Next Steps ===")
        print("1. Run migration script to import existing data:")
        print("   python migrate_data_to_postgresql.py --dry-run")
        print("   python migrate_data_to_postgresql.py")
        print()
        print("2. Test sentiment analysis with caching:")
        print("   python sentiment.py AAPL")
        print("   python sentiment.py AAPL --force-refresh")
        print()
        print("3. Verify data:")
        print("   python migrate_data_to_postgresql.py --verify")

if __name__ == "__main__":
    main()