#!/usr/bin/env python3
"""
Data Inspector - Check and analyze stock data in database
"""

import pandas as pd
from core.database import SentimentDatabase
import argparse

def inspect_data(symbol='AAPL', timeframe='hour', limit=100):
    """Inspect stock data for a symbol"""

    print(f"=== Data Inspection for {symbol} ({timeframe}) ===")

    db = SentimentDatabase()
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            # Get basic stats
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(*) FILTER (WHERE original = true) as original_records,
                    MIN(price_timestamp) as earliest,
                    MAX(price_timestamp) as latest
                FROM stock_data_{timeframe}
                WHERE symbol = %s
            """, (symbol,))

            stats = cursor.fetchone()
            print(f"Total Records: {stats['total_records']}")
            print(f"Original Records: {stats['original_records']}")
            print(f"Date Range: {stats['earliest']} to {stats['latest']}")
            print()

            # Get recent data sample
            cursor.execute(f"""
                SELECT symbol, price_timestamp, open, high, low, close, volume, original
                FROM stock_data_{timeframe}
                WHERE symbol = %s AND original = true
                ORDER BY price_timestamp DESC
                LIMIT %s
            """, (symbol, limit))

            recent = cursor.fetchall()
            if recent:
                print("Recent Original Data (latest first):")
                for i, row in enumerate(recent[:5]):
                    print(f"  {i+1}. {row['price_timestamp']}: O={row['open']} H={row['high']} L={row['low']} C={row['close']} V={row['volume']}")

                # Convert to DataFrame for analysis
                df = pd.DataFrame([dict(r) for r in recent])
                df['price_timestamp'] = pd.to_datetime(df['price_timestamp'])
                df = df.sort_values('price_timestamp')

                print(f"\nData Quality Analysis:")
                print(f"  Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
                print(f"  Average volume: {df['volume'].mean():.0f}")
                print(f"  Latest close: ${df['close'].iloc[-1]:.2f}")
                print(f"  Data spans: {(df['price_timestamp'].max() - df['price_timestamp'].min()).days} days")
            else:
                print(f"No original data found for {symbol}")

            # Check forward-filled data ratio
            cursor.execute(f"""
                SELECT
                    COUNT(*) FILTER (WHERE original = true) as original,
                    COUNT(*) FILTER (WHERE original = false) as forward_filled,
                    COUNT(*) as total
                FROM stock_data_{timeframe}
                WHERE symbol = %s
            """, (symbol,))

            ratio = cursor.fetchone()
            if ratio['total'] > 0:
                orig_pct = ratio['original'] / ratio['total'] * 100
                ff_pct = ratio['forward_filled'] / ratio['total'] * 100
                print(f"\nData Composition:")
                print(f"  Original: {ratio['original']} ({orig_pct:.1f}%)")
                print(f"  Forward-filled: {ratio['forward_filled']} ({ff_pct:.1f}%)")

def list_available_symbols(timeframe='hour', limit=20):
    """List available symbols with data counts"""

    print(f"=== Available Symbols ({timeframe}) ===")

    db = SentimentDatabase()
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    symbol,
                    COUNT(*) as total_records,
                    COUNT(*) FILTER (WHERE original = true) as original_records,
                    MIN(price_timestamp) as earliest,
                    MAX(price_timestamp) as latest
                FROM stock_data_{timeframe}
                GROUP BY symbol
                ORDER BY original_records DESC
                LIMIT %s
            """, (limit,))

            symbols = cursor.fetchall()

            print(f"{'Symbol':<8} {'Original':<10} {'Total':<10} {'Latest Date':<20}")
            print("-" * 60)

            for s in symbols:
                print(f"{s['symbol']:<8} {s['original_records']:<10} {s['total_records']:<10} {str(s['latest'])[:19]:<20}")

def main():
    parser = argparse.ArgumentParser(description='Inspect stock data in database')
    parser.add_argument('--symbol', default='AAPL', help='Symbol to inspect')
    parser.add_argument('--timeframe', choices=['day', 'hour', 'minute'], default='hour')
    parser.add_argument('--list', action='store_true', help='List available symbols')
    parser.add_argument('--limit', type=int, default=100, help='Limit for data sample')

    args = parser.parse_args()

    if args.list:
        list_available_symbols(args.timeframe)
    else:
        inspect_data(args.symbol, args.timeframe, args.limit)

if __name__ == '__main__':
    main()