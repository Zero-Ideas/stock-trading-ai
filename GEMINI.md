# GEMINI.md

## Project Overview

The project is a stock sentiment analysis tool named "Financial Intelligence Platform / Future Stock Trading AI". It scrapes news articles from various sources, analyzes the sentiment of the articles using NLP models (TextBlob and potentially FinBERT/Transformers), and stores the results in a PostgreSQL database. The project also includes a Flask-based web application that provides a user interface to view the sentiment analysis results, historical stock data, and other relevant information.

## Building and Running

The project is written in Python. To run the project, you need to have Python and PostgreSQL installed.

### Dependencies

Based on the source code, the following Python libraries are used:
- `flask`
- `flask_cors`
- `psycopg2-binary`
- `yfinance`
- `numpy`
- `pandas`
- `torch`
- `transformers`
- `newspaper3k`
- `requests`
- `beautifulsoup4`
- `selenium`

A `requirements.txt` file is not provided, but you can install the dependencies using pip:
```bash
pip install flask flask_cors psycopg2-binary yfinance numpy pandas torch transformers newspaper3k requests beautifulsoup4 selenium
```

### Database Setup

The project uses a PostgreSQL database. You need to have a PostgreSQL server running. The database connection parameters can be configured in a `database_config.py` file (by copying `api_config_example.py`) or by setting environment variables. The database schema is defined in `Schemas/database_schema.sql` and is automatically initialized by the application.

### Running the Web Application

The main web application can be started by running the `enhanced_web_app.py` file:
```bash
python enhanced_web_app.py
```
The web UI will be available at `http://localhost:5000`.

## Development Conventions

- The code is structured into several directories: `core`, `scrapers`, `app`, `Schemas`, etc.
- Scrapers for different news sources are implemented as subclasses of `scrapers.base_scraper.BaseScraper`.
- The database logic is encapsulated in the `core.database.SentimentDatabase` class.
- The web application is built using Flask.
- The project uses caching for analysis results, stock information, and historical data to improve performance.
- There is a background thread for running sentiment analysis to avoid blocking the web server.
- The project uses `yfinance` to fetch historical stock data.
- The project uses `newspaper3k` to extract article content from news websites.
- The project uses `selenium` for browser automation to scrape JavaScript-heavy websites.
