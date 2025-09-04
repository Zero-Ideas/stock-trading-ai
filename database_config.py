#!/usr/bin/env python3
"""
Database Configuration
PostgreSQL connection settings for sentiment analysis caching
"""

# PostgreSQL Connection Settings
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_sentiment',
    'username': 'postgres',
    'password': 'sudo'  # User's PostgreSQL password
}