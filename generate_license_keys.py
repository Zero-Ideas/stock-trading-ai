#!/usr/bin/env python3
"""
License Key Generator Script
Create license keys for different tiers
"""

import sys
import argparse
from datetime import datetime, timedelta
from license_manager import license_manager

def main():
    parser = argparse.ArgumentParser(description='Generate license keys for Stock Trading AI')
    parser.add_argument('tier', choices=['evaluation', 'standard', 'premium', 'master'],
                       help='License tier to create')
    parser.add_argument('--user-name', help='User name (optional)')
    parser.add_argument('--user-email', help='User email (optional)')
    parser.add_argument('--expires-days', type=int, help='Expiration in days (optional)')
    parser.add_argument('--count', type=int, default=1, help='Number of keys to generate')

    args = parser.parse_args()

    try:
        print(f"Generating {args.count} {args.tier} license key(s)...")
        print("-" * 50)

        for i in range(args.count):
            license_key = license_manager.generate_license_key(
                tier_name=args.tier,
                user_name=args.user_name,
                user_email=args.user_email,
                expires_days=args.expires_days
            )

            print(f"License Key {i+1}: {license_key}")
            print(f"Tier: {args.tier}")
            if args.user_name:
                print(f"User: {args.user_name}")
            if args.user_email:
                print(f"Email: {args.user_email}")
            if args.expires_days:
                expiry = datetime.utcnow() + timedelta(days=args.expires_days)
                print(f"Expires: {expiry.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            else:
                print("Expires: Never")
            print("-" * 50)

        print("License key generation completed successfully!")

    except Exception as e:
        print(f"Error generating license keys: {e}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())