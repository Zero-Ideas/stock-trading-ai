#!/usr/bin/env python3
"""
License System Installation Script
Sets up the database schema with license management tables
"""

import sys
import os
from datetime import datetime
from core.database import SentimentDatabase

def main():
    print("Stock Trading AI - License System Installation")
    print("=" * 50)

    try:
        # Initialize database connection
        print("1. Connecting to database...")
        db = SentimentDatabase()
        print("   [OK] Database connection successful")

        # Initialize the schema (this will run the full schema including license tables)
        print("2. Installing database schema...")
        db.initialize_schema()
        print("   [OK] Database schema installed successfully")

        # Verify license tables exist
        print("3. Verifying license tables...")
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check if license tables exist
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name IN ('license_tiers', 'license_keys', 'license_sessions', 'api_usage_logs')
                    ORDER BY table_name
                """)
                tables = [row['table_name'] for row in cursor.fetchall()]

                expected_tables = ['api_usage_logs', 'license_keys', 'license_sessions', 'license_tiers']
                if set(tables) == set(expected_tables):
                    print("   [OK] All license tables created successfully")
                    for table in tables:
                        print(f"     - {table}")
                else:
                    missing = set(expected_tables) - set(tables)
                    print(f"   [ERROR] Missing tables: {missing}")
                    return 1

        # Verify license tiers data
        print("4. Verifying license tiers...")
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT tier_name, display_name FROM license_tiers ORDER BY price_monthly")
                tiers = cursor.fetchall()
                if tiers:
                    print("   [OK] License tiers configured:")
                    for tier in tiers:
                        print(f"     - {tier['tier_name']}: {tier['display_name']}")
                else:
                    print("   [ERROR] No license tiers found")
                    return 1

        print("\n" + "=" * 50)
        print("[SUCCESS] License system installation completed successfully!")
        print()
        print("Next steps:")
        print("1. Generate license keys using: python generate_license_keys.py")
        print("2. Start the licensed web app: python licensed_web_app.py")
        print("3. Start the API server: python server.py")
        print()
        print("Example commands:")
        print("  # Generate a master license key")
        print("  python generate_license_keys.py master --user-name Admin")
        print()
        print("  # Generate evaluation keys")
        print("  python generate_license_keys.py evaluation --count 5 --expires-days 30")
        print()

    except Exception as e:
        print(f"\n[ERROR] Installation failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running")
        print("2. Check database_config.py settings")
        print("3. Verify database permissions")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())