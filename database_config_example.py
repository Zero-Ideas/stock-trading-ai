#!/usr/bin/env python3
"""
Database Configuration Template
Copy this file to database_config.py and fill in your PostgreSQL credentials
"""

# PostgreSQL Connection Settings
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_sentiment',
    'username': 'postgres',
    'password': 'sudo'  # Replace with your actual password
}

# Instructions:
# 1. Copy this file to database_config.py
# 2. Replace 'YOUR_POSTGRES_PASSWORD_HERE' with your actual PostgreSQL password
# 3. Optionally modify other settings if your PostgreSQL setup is different
# 4. The database 'stock_sentiment' will be created automatically if it doesn't exist