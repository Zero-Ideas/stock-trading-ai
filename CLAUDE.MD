# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Stock Trading AI platform that provides intelligent financial sentiment analysis by scraping news from multiple sources and using AI models (FinBERT, TextBlob, VADER) to analyze sentiment. The system features a web interface, database caching, and concurrent scraping architecture.

## Core Architecture

### Main Components
- **sentiment.py**: Core sentiment analysis engine and CLI interface
- **core/database.py**: PostgreSQL database interface for caching results
- **scrapers/**: Modular scraper framework with individual scrapers for Bloomberg, MarketWatch, Yahoo Finance, Seeking Alpha, Google News, NewsAPI, Reuters, Financial Times, and Benzinga
- **Web interfaces**: Multiple web apps (web_app.py, enhanced_web_app.py, server.py) with HTML frontends

### Key Design Patterns
- **Lazy loading**: Scrapers and AI models only load when needed
- **Concurrent execution**: ThreadPoolExecutor for parallel scraping across sources
- **Modular scrapers**: All inherit from base_scraper.py with common functionality
- **Database per symbol**: Tables created dynamically as `articles_{symbol}`
- **Content enhancement**: newspaper3k + Selenium fallback for blocked sites
- **Duplicate prevention**: SHA-256 URL hashing prevents duplicate articles

## Development Commands

### Core Analysis
```bash
# Basic sentiment analysis
python sentiment.py NVDA --articles 20

# Force refresh bypassing cache
python sentiment.py TSLA --force-refresh

# JSON output for integration
python sentiment.py AAPL --json > output.json

# No database mode (file output only)
python sentiment.py MSFT --no-database

# Skip FinBERT for faster startup
python sentiment.py SPY --no-finbert
```

### Database Operations
```bash
# Initialize database schema
python -c "from core.database import SentimentDatabase; SentimentDatabase().initialize_database()"

# Test database connection
python -c "from core.database import SentimentDatabase; print('Database OK' if SentimentDatabase()._test_connection() else 'Database Error')"
```

### Web Interfaces
```bash
# Basic web app
python web_app.py

# Enhanced web app with additional features (way better)
python enhanced_web_app.py

# Server with API endpoints
python server.py
```

### Database Setup
1. Ensure PostgreSQL is running
2. Copy `database_config_example.py` to `database_config.py` if it doesn't exist
3. Update `database_config.py` with your PostgreSQL credentials
4. Run database initialization command above

## Configuration Files

- **database_config.py**: PostgreSQL connection settings (not in git)
- **scrapers/__init__.py**: Scraper registration and SentimentData model
- **Schemas/database_schema.sql**: Database table definitions


Key dependencies:
- **transformers**: FinBERT model for financial sentiment
- **torch**: PyTorch backend for transformers
- **psycopg2-binary**: PostgreSQL connector
- **selenium**: Web automation for redirect handing and blocked sites
- **pydoll**: Web automation with extreme stealth capabilities
- **newspaper3k**: Article content extraction
- **beautifulsoup4**: HTML parsing
- **textblob, vaderSentiment**: Alternative sentiment engines
- **pandas**: Data manipulation
- **flask**: Web framework (for web interfaces)

## Testing

The codebase includes several test files:
- Performance and threading tests
- Database functionality verification
- Individual scraper testing
- Google News timeout handling tests

## Current Development Status

See TODO.md for active development tasks including:
- Frontend/backend refactoring to JavaScript + Flask API
- Line graph rendering fixes
- Article filtering by sentiment and source
- Theme support improvements
- Playwright testing integration

## Important Notes

- Scrapers implement anti-bot measures (user agent rotation, delays)
- System handles graceful degradation when sources fail
- AI models support fallback (FinBERT → TextBlob → VADER)
- Database connection includes automatic password detection
- All major operations include timeout protection