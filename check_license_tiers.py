#!/usr/bin/env python3
"""
Check License Tiers Configuration
"""

from core.database import SentimentDatabase

def main():
    db = SentimentDatabase()
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM license_tiers ORDER BY price_monthly')
            tiers = cursor.fetchall()
            print('License Tiers Configuration:')
            print('=' * 80)
            for tier in tiers:
                print(f'Tier: {tier["tier_name"]}')
                print(f'  Display Name: {tier["display_name"]}')
                print(f'  Max Sessions: {tier["max_concurrent_sessions"]}')
                print(f'  API Calls/Hour: {tier["max_api_calls_per_hour"]}')
                print(f'  API Calls/Day: {tier["max_api_calls_per_day"]}')
                print(f'  Features: {tier["features_enabled"]}')
                print(f'  Price: ${tier["price_monthly"]}/month')
                print('-' * 40)

if __name__ == '__main__':
    main()