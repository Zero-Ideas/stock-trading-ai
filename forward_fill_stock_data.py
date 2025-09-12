#!/usr/bin/env python3
"""
Forward Fill Script for Stock Data Tables

This script identifies gaps in time series stock data and forward fills them
using the last known values. Forward filled data points are marked with original=false.

The script handles three timeframes:
- Daily data (stock_data_day)
- Hourly data (stock_data_hour) 
- Minute data (stock_data_minute)

Usage:
    python forward_fill_stock_data.py --timeframe all [--symbol SYMBOL] [--dry-run]
    python forward_fill_stock_data.py --timeframe day [--symbol SYMBOL] [--dry-run]
    python forward_fill_stock_data.py --timeframe hour [--symbol SYMBOL] [--dry-run]
    python forward_fill_stock_data.py --timeframe minute [--symbol SYMBOL] [--dry-run]

Arguments:
    --timeframe: Choose 'all', 'day', 'hour', or 'minute'
    --symbol: Optional. Fill gaps for specific symbol only (default: all symbols)
    --dry-run: Show what would be filled without making changes
"""
"""
\n  Analyzing AAPL...
    Found 186046 gaps for AAPL
    Inserted 3365038 forward filled data points for AAPL
    Filled 3365038 data points for AAPL
\n  Analyzing ABBV...
    Found 41453 gaps for ABBV
    Inserted 4094263 forward filled data points for ABBV
    Filled 4094263 data points for ABBV
\n  Analyzing ABT...
    Found 24919 gaps for ABT
    Inserted 4116232 forward filled data points for ABT
    Filled 4116232 data points for ABT
\n  Analyzing ADBE...
    Found 47062 gaps for ADBE
    Inserted 4091167 forward filled data points for ADBE
    Filled 4091167 data points for ADBE
\n  Analyzing AMC...
    Found 145634 gaps for AMC
    Inserted 3776817 forward filled data points for AMC
    Filled 3776817 data points for AMC
\n  Analyzing AMD...
    Found 178759 gaps for AMD
    Inserted 3411492 forward filled data points for AMD
    Filled 3411492 data points for AMD
\n  Analyzing AMGN...
    Found 29960 gaps for AMGN
    Inserted 4124603 forward filled data points for AMGN
    Filled 4124603 data points for AMGN
\n  Analyzing AMT...
    Found 22715 gaps for AMT
    Inserted 4150910 forward filled data points for AMT
    Filled 4150910 data points for AMT
\n  Analyzing AMZN...
    Found 155906 gaps for AMZN
    Inserted 3704820 forward filled data points for AMZN
    Filled 3704820 data points for AMZN
\n  Analyzing AVGO...
    Found 69637 gaps for AVGO
    Inserted 4029328 forward filled data points for AVGO
    Filled 4029328 data points for AVGO
\n  Analyzing AXP...
    Found 35373 gaps for AXP
    Inserted 4108038 forward filled data points for AXP
    Filled 4108038 data points for AXP
\n  Analyzing BA...
    Found 123538 gaps for BA
    Inserted 3879231 forward filled data points for BA
    Filled 3879231 data points for BA
"""
import argparse
import sys
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import psycopg2.extras

# Add the core module to path
sys.path.append('.')
from core.database import SentimentDatabase


class StockDataForwardFiller:
    """Handles forward filling of stock data gaps"""
    
    def __init__(self):
        """Initialize with database connection"""
        self.db = SentimentDatabase()
        self.timeframe_configs = {
            'day': {
                'table': 'stock_data_day',
                'interval': '1 day',
                'interval_delta': timedelta(days=1)
            },
            'hour': {
                'table': 'stock_data_hour', 
                'interval': '1 hour',
                'interval_delta': timedelta(hours=1)
            },
            'minute': {
                'table': 'stock_data_minute',
                'interval': '1 minute', 
                'interval_delta': timedelta(minutes=1)
            }
        }
    
    def get_symbols_in_table(self, table_name: str) -> List[str]:
        """Get all unique symbols in a table"""
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT DISTINCT symbol 
                    FROM {table_name} 
                    ORDER BY symbol
                """)
                return [row['symbol'] for row in cursor.fetchall()]
    
    def find_gaps(self, table_name: str, symbol: str, interval_delta: timedelta) -> List[Tuple[datetime, datetime, Dict]]:
        """
        Find gaps in time series data for a symbol
        
        Returns:
            List of tuples: (gap_start, gap_end, last_known_values)
        """
        gaps = []
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get all data points for the symbol, ordered by timestamp
                cursor.execute(f"""
                    SELECT price_timestamp, open, high, low, close, volume, trade_count, vwap
                    FROM {table_name}
                    WHERE symbol = %s
                    ORDER BY price_timestamp ASC
                """, (symbol,))
                
                rows = cursor.fetchall()
                if len(rows) < 2:
                    return gaps
                
                for i in range(len(rows) - 1):
                    current_row = rows[i]
                    next_row = rows[i + 1]
                    
                    current_time = current_row['price_timestamp']
                    next_time = next_row['price_timestamp']
                    expected_next_time = current_time + interval_delta
                    
                    # Check if there's a gap larger than the expected interval
                    if next_time > expected_next_time:
                        # Found a gap - calculate how many intervals are missing
                        gap_start = expected_next_time
                        gap_end = next_time - interval_delta
                        
                        # Store the last known values for forward filling
                        last_known_values = {
                            'open': current_row['open'],
                            'high': current_row['high'], 
                            'low': current_row['low'],
                            'close': current_row['close'],
                            'volume': current_row['volume'] or 0,  # Use 0 for NULL volumes
                            'trade_count': current_row['trade_count'] or 0,  # Use 0 for NULL trade_counts
                            'vwap': current_row['vwap']
                        }
                        
                        gaps.append((gap_start, gap_end, last_known_values))
                
                return gaps
    
    def generate_fill_timestamps(self, gap_start: datetime, gap_end: datetime, interval_delta: timedelta) -> List[datetime]:
        """Generate timestamps to fill within a gap"""
        timestamps = []
        current_time = gap_start
        
        while current_time <= gap_end:
            timestamps.append(current_time)
            current_time += interval_delta
        
        return timestamps
    
    def forward_fill_gaps(self, table_name: str, symbol: str, gaps: List[Tuple[datetime, datetime, Dict]], 
                         interval_delta: timedelta, dry_run: bool = False) -> int:
        """
        Forward fill identified gaps with last known values
        
        Returns:
            Number of data points filled
        """
        total_filled = 0
        
        if not gaps:
            return 0
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                for gap_start, gap_end, last_values in gaps:
                    # Generate timestamps to fill
                    fill_timestamps = self.generate_fill_timestamps(gap_start, gap_end, interval_delta)
                    
                    #print(f"    Gap found: {gap_start} to {gap_end} ({len(fill_timestamps)} points)")
                    
                    if dry_run:
                        total_filled += len(fill_timestamps)
                        continue
                    
                    # Insert forward filled data points
                    for timestamp in fill_timestamps:
                        try:
                            cursor.execute(f"""
                                INSERT INTO {table_name} (
                                    symbol, price_timestamp, open, high, low, close,
                                    volume, trade_count, vwap, original, created_at
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                            """, (
                                symbol,
                                timestamp,
                                last_values['open'],
                                last_values['high'],
                                last_values['low'],
                                last_values['close'],
                                last_values['volume'],
                                last_values['trade_count'],
                                last_values['vwap'],
                                False,  # original = False for forward filled data
                                datetime.utcnow()
                            ))
                            total_filled += 1
                        except psycopg2.IntegrityError:
                            # Skip if timestamp already exists (shouldn't happen but safety check)
                            continue
                    
            if not dry_run:
                print(f"    Inserted {total_filled} forward filled data points for {symbol}")
                conn.commit()
        
        return total_filled
    
    def process_timeframe(self, timeframe: str, symbol: Optional[str] = None, dry_run: bool = False) -> Dict[str, int]:
        """
        Process forward filling for a specific timeframe
        
        Returns:
            Dictionary with symbol -> filled_count mapping
        """
        if timeframe not in self.timeframe_configs:
            raise ValueError(f"Invalid timeframe: {timeframe}. Must be one of {list(self.timeframe_configs.keys())}")
        
        config = self.timeframe_configs[timeframe]
        table_name = config['table']
        interval_delta = config['interval_delta']
        
        print(f"\\n=== Processing {timeframe.upper()} timeframe ({table_name}) ===")
        
        # Get symbols to process
        if symbol:
            symbols = [symbol.upper()]
            print(f"Processing specific symbol: {symbol}")
        else:
            symbols = self.get_symbols_in_table(table_name)
            print(f"Processing {len(symbols)} symbols: {', '.join(symbols[:10])}")
            if len(symbols) > 10:
                print(f"... and {len(symbols) - 10} more")
        
        results = {}
        
        for sym in symbols:
            print(f"\\n  Analyzing {sym}...")
            
            # Find gaps in data
            gaps = self.find_gaps(table_name, sym, interval_delta)
            
            if not gaps:
                print(f"    No gaps found for {sym}")
                results[sym] = 0
                continue
            
            print(f"    Found {len(gaps)} gaps for {sym}")
            
            # Forward fill the gaps
            filled_count = self.forward_fill_gaps(table_name, sym, gaps, interval_delta, dry_run)
            results[sym] = filled_count
            
            if dry_run:
                print(f"    [DRY RUN] Would fill {filled_count} data points for {sym}")
            else:
                print(f"    Filled {filled_count} data points for {sym}")
        
        return results
    
    def run_forward_fill(self, timeframes: List[str], symbol: Optional[str] = None, dry_run: bool = False):
        """
        Run forward fill process for specified timeframes
        
        Args:
            timeframes: List of timeframes to process ('day', 'hour', 'minute')
            symbol: Optional specific symbol to process
            dry_run: If True, show what would be done without making changes
        """
        print("Stock Data Forward Fill Tool")
        print("=" * 50)
        
        if dry_run:
            print("[DRY RUN] MODE - No changes will be made")
        
        total_results = {}
        
        for timeframe in timeframes:
            try:
                results = self.process_timeframe(timeframe, symbol, dry_run)
                total_results[timeframe] = results
                
                # Summary for this timeframe
                total_filled = sum(results.values())
                symbols_with_gaps = len([s for s, count in results.items() if count > 0])
                
                print(f"\\n  {timeframe.upper()} Summary:")
                print(f"    - Total data points filled: {total_filled}")
                print(f"    - Symbols with gaps: {symbols_with_gaps}/{len(results)}")
                
            except Exception as e:
                print(f"\\n  ERROR processing {timeframe}: {e}")
                continue
        
        # Overall summary
        print(f"\\n{'=' * 50}")
        print("OVERALL SUMMARY")
        
        grand_total = 0
        for timeframe, results in total_results.items():
            timeframe_total = sum(results.values())
            grand_total += timeframe_total
            print(f"  {timeframe.upper():8}: {timeframe_total:8,} data points filled")
        
        print(f"  {'TOTAL':8}: {grand_total:8,} data points filled")
        
        if dry_run:
            print("\\n[DRY RUN] This was a dry run. Use without --dry-run to apply changes.")
        else:
            print("\\nForward fill completed successfully!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Forward fill gaps in stock data tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--timeframe',
        choices=['all', 'day', 'hour', 'minute'],
        required=True,
        help='Timeframe to process (all, day, hour, or minute)'
    )
    
    parser.add_argument(
        '--symbol',
        type=str,
        help='Process specific symbol only (optional)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be filled without making changes'
    )
    
    args = parser.parse_args()
    
    # Determine timeframes to process
    if args.timeframe == 'all':
        timeframes = ['day', 'hour', 'minute']
    else:
        timeframes = [args.timeframe]
    
    try:
        filler = StockDataForwardFiller()
        filler.run_forward_fill(timeframes, args.symbol, args.dry_run)
        
    except KeyboardInterrupt:
        print("\\n\\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n\\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()