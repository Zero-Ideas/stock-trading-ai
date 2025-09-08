# Automatic Stock Database Update Script

## Overview

The `update_stock_database.py` script automatically keeps your PostgreSQL stock database up-to-date by:

1. **Gap Detection**: Identifies symbols with missing or outdated data
2. **Smart Fetching**: Requests only missing data from Alpaca API (1 day before last record to 1 day after today)
3. **Duplicate Prevention**: Uses database constraints to avoid duplicate entries
4. **Progress Tracking**: Shows real-time progress with tqdm bars
5. **Comprehensive Logging**: Logs all operations to `database_update.log`

## Features

### Automatic Gap Detection
- Scans all symbols in `stock_data_day`, `stock_data_hour`, and `stock_data_minute` tables
- Calculates how many days behind each symbol is
- Only fetches missing data (efficient API usage)

### Smart Date Range Calculation
```python
# Example: If AAPL has data up to 2025-09-04
start_date = 2025-09-03  # 1 day before last data
end_date = 2025-09-08    # 1 day after today (2025-09-07)
```

### Multi-Timeframe Support
- **Daily data**: `stock_data_day` table
- **Hourly data**: `stock_data_hour` table  
- **Minute data**: `stock_data_minute` table

## Usage

### Update All Symbols
```bash
python update_stock_database.py
```
This will:
- Find all symbols in your database
- Check each symbol's latest data across all timeframes
- Fetch missing data from Alpaca API
- Insert new records while avoiding duplicates

### Update Specific Symbols
```bash
python update_stock_database.py AAPL GOOGL MSFT
```
This will update only the specified symbols.

### Test Database Status
```bash
python test_database_update.py
```
This will:
- Show current database statistics
- Identify which symbols need updates
- Display gap analysis for major symbols

## Example Output

```
=== Starting Automatic Database Update ===
Found 94 symbols to update

Updating AAPL: 100%|████████████| 94/94 [00:45<00:00,  2.09 symbols/s]

[OK] AAPL: 156 new records
[CURRENT] GOOGL: Already up to date  
[OK] TSLA: 234 new records
[ERROR] META: {"message":"subscription does not permit querying recent SIP data"}

=== Update Complete ===
Symbols updated: 87/94
Total new records: 45,678
Total duplicates skipped: 1,234
Update completed at: 2025-09-07 16:15:32
```

## API Limitations

**Important**: Your current Alpaca subscription has limitations:
- ✅ Can fetch historical data (older than ~15 minutes)
- ❌ Cannot fetch recent SIP data (last few days)
- ❌ Real-time data requires paid subscription

### Workaround for Testing
To test the script with available data, you can modify the date ranges:

```python
# In update_stock_database.py, modify calculate_fetch_range():
def calculate_fetch_range(self, symbol, table_name, max_date):
    if max_date is None:
        # Fetch older data for testing
        end_date = date(2025, 9, 1)  # Use older end date
        start_date = end_date - timedelta(days=7)
    else:
        # Fetch gap in historical data
        start_date = max_date - timedelta(days=7)
        end_date = max_date - timedelta(days=1)
```

## Configuration

### Database Settings
The script uses settings from `database_config.py`:
```python
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_sentiment', 
    'username': 'postgres',
    'password': 'sudo'
}
```

### Alpaca API Credentials
```python
# In update_stock_database.py
self.client = StockHistoricalDataClient(
    "PK3S7CKIFQBPLZLSV691",
    "HOXAsPCVF2v3Pz63wmRR5xrd2cLbyakoAedH3HP4"
)
```

## Data Flow

```
1. Query Database → Find all symbols
2. Check Each Symbol → Get latest timestamp per table  
3. Calculate Gap → Determine missing date range
4. Fetch from Alpaca → Get missing data via API
5. Insert to Database → Bulk insert with duplicate prevention
6. Verify & Log → Count new records, log results
```

## Error Handling

- **API Errors**: Logged and skipped, other symbols continue
- **Database Errors**: Transaction rollback, prevents corruption  
- **Network Issues**: Automatic retry logic (built into Alpaca client)
- **Data Validation**: Checks for required columns and valid data types

## Logging

All operations are logged to `database_update.log`:
```
2025-09-07 16:15:32 - INFO - === Starting Automatic Database Update ===
2025-09-07 16:15:33 - INFO - Found 94 symbols to update
2025-09-07 16:15:34 - INFO - AAPL: Fetching from 2025-09-03 to 2025-09-08
2025-09-07 16:15:35 - INFO - Successfully fetched 156 bars for AAPL 1Day
2025-09-07 16:15:36 - INFO - Inserted 156 new records, 0 duplicates skipped
```

## Database Schema Compatibility

The script works with your existing partitioned tables:
- `stock_data_day` (partitioned by symbol hash)
- `stock_data_hour` (partitioned by symbol hash)
- `stock_data_minute` (partitioned by symbol hash)

Each table has unique constraints on `(symbol, price_timestamp)` to prevent duplicates.

## Files Created

1. **`update_stock_database.py`** - Main update script
2. **`test_database_update.py`** - Testing and status checking
3. **`database_update.log`** - Detailed operation logs
4. **`README_Database_Update.md`** - This documentation

## Next Steps

1. **Test with available data**: Modify date ranges to use historical data your subscription allows
2. **Schedule regular updates**: Set up cron job or Windows Task Scheduler
3. **Monitor logs**: Check `database_update.log` for any issues
4. **Consider API upgrade**: For real-time data access

## Troubleshooting

**"subscription does not permit querying recent SIP data"**
- Your Alpaca plan doesn't include recent market data
- Modify date ranges to use older historical data
- Consider upgrading Alpaca subscription for real-time updates

**"No symbols found in database"**
- Run your existing transfer scripts first to populate the database
- Check database connection settings in `database_config.py`

**Slow performance**
- The script processes all symbols sequentially
- Consider parallel processing for large symbol counts
- Monitor database performance during bulk inserts

## Integration with Existing Workflow

This update script complements your existing tools:
- Use `transfer_stock_data_fixed.py` for initial bulk data transfer
- Use `update_stock_database.py` for ongoing maintenance
- Both scripts share the same database schema and duplicate prevention logic