#!/usr/bin/env python3
"""
Enhanced Flask Web Application for Stock Sentiment Analyzer
Modern web UI with historical data integration and comprehensive features
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from datetime import datetime, timedelta
import threading
import time
from typing import Dict, Any, Optional
import traceback
import yfinance as yf

# Import our sentiment analyzer and historical data getter
from sentiment import StockSentimentAnalyzer
from historicalDataGetter import HistoricalDataGetter

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Enable CORS for API calls

# Global cache for analysis results to avoid re-running same analysis
analysis_cache = {}
stock_info_cache = {}
historical_data_cache = {}
cache_timeout = 300  # 5 minutes

# Background analysis tracking
active_analyses = {}


class AnalysisStatus:
    """Track status of ongoing analyses"""
    def __init__(self, symbol: str, target_articles: int):
        self.symbol = symbol
        self.target_articles = target_articles
        self.status = "starting"  # starting, running, completed, error
        self.progress = 0
        self.message = "Initializing analysis..."
        self.result = None
        self.error = None
        self.start_time = datetime.now()


def run_background_analysis(analysis_id: str, symbol: str, target_articles: int):
    """Run sentiment analysis in background thread"""
    analysis = active_analyses[analysis_id]
    
    try:
        analysis.status = "running"
        analysis.message = "Initializing scrapers..."
        
        # Create analyzer
        analyzer = StockSentimentAnalyzer(symbol)
        
        analysis.progress = 10
        analysis.message = f"Analyzing {symbol} with {target_articles} target articles..."
        
        # Run the actual analysis
        results = analyzer.analyze_sentiment(target_articles=target_articles)
        
        if "error" in results:
            analysis.status = "error"
            analysis.error = results["error"]
            analysis.message = f"Analysis failed: {results['error']}"
        else:
            analysis.status = "completed"
            analysis.result = results
            analysis.progress = 100
            analysis.message = f"Analysis completed! Found {results['total_articles']} articles"
            
            # Cache the results
            cache_key = f"{symbol}_{target_articles}"
            analysis_cache[cache_key] = {
                'timestamp': datetime.now(),
                'result': results
            }
            
    except Exception as e:
        analysis.status = "error"
        analysis.error = str(e)
        analysis.message = f"Analysis error: {str(e)[:100]}..."
        print(f"Analysis error for {symbol}: {e}")
        traceback.print_exc()


@app.route('/')
def index():
    """Serve the enhanced web UI"""
    return send_from_directory('.', 'enhanced_index.html')


@app.route('/api/stock_info/<symbol>')
def get_stock_info(symbol):
    """Get current stock price and company information"""
    try:
        symbol = symbol.upper().strip()
        
        # Check cache first
        if symbol in stock_info_cache:
            cached = stock_info_cache[symbol]
            # Check if cache is still valid (5 minutes)
            if (datetime.now() - cached['timestamp']).seconds < cache_timeout:
                return jsonify(cached['data'])
        
        print(f"Fetching stock info for {symbol}...")
        
        # Try to get data from yfinance first (faster and more reliable)
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="2d")
            
            if len(hist) >= 1:
                current_price = float(hist['Close'].iloc[-1])
                
                # Calculate change if we have at least 2 days
                if len(hist) >= 2:
                    previous_price = float(hist['Close'].iloc[-2])
                    change = current_price - previous_price
                    change_percent = (change / previous_price) * 100
                else:
                    change = 0.0
                    change_percent = 0.0
                
                # Get company name
                company_name = info.get('longName') or info.get('shortName') or symbol
                
                stock_data = {
                    'symbol': symbol,
                    'company_name': company_name,
                    'price': current_price,
                    'change': change,
                    'change_percent': change_percent,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'source': 'Yahoo Finance'
                }
                
                # Cache the result
                stock_info_cache[symbol] = {
                    'timestamp': datetime.now(),
                    'data': stock_data
                }
                
                return jsonify(stock_data)
        except Exception as yf_error:
            print(f"YFinance error for {symbol}: {yf_error}")
        
        # Fallback to historical data getter (Google Finance scraping)
        try:
            getter = HistoricalDataGetter()
            stock_data = getter.get_current_price_google_finance(symbol)
            
            if stock_data:
                # Add company name from yfinance if possible
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    company_name = info.get('longName') or info.get('shortName') or symbol
                    stock_data['company_name'] = company_name
                except:
                    stock_data['company_name'] = symbol
                
                # Cache the result
                stock_info_cache[symbol] = {
                    'timestamp': datetime.now(),
                    'data': stock_data
                }
                
                return jsonify(stock_data)
        except Exception as scraper_error:
            print(f"Historical data getter error for {symbol}: {scraper_error}")
        
        # If all methods fail, return basic info
        return jsonify({
            'symbol': symbol,
            'company_name': symbol,
            'price': 0.0,
            'change': 0.0,
            'change_percent': 0.0,
            'error': 'Could not fetch stock price'
        }), 404
        
    except Exception as e:
        print(f"Stock info API error: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/historical/<symbol>')
def get_historical_data(symbol):
    """Get historical stock data for charting with optional period parameter"""
    try:
        symbol = symbol.upper().strip()
        
        # Get period from query parameters (default to 30d)
        period = request.args.get('period', '30d')
        
        # Create cache key that includes period
        cache_key = f"{symbol}_{period}"
        
        # Check cache first
        if cache_key in historical_data_cache:
            cached = historical_data_cache[cache_key]
            # Check if cache is still valid (30 minutes)
            if (datetime.now() - cached['timestamp']).seconds < 1800:
                return jsonify(cached['data'])
        
        print(f"Fetching historical data for {symbol} ({period})...")
        
        # Create a simple test data if yfinance fails (for development)
        # This ensures the UI works even if data sources are unavailable
        
        # Try yfinance first (more reliable)
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            # Get historical data for the specified period
            hist = ticker.history(period=period)
            
            print(f"YFinance data shape: {hist.shape if not hist.empty else 'empty'}")
            print(f"YFinance columns: {list(hist.columns) if not hist.empty else 'none'}")
            
            if not hist.empty and len(hist) > 0:
                # Make sure we have Close data
                if 'Close' in hist.columns:
                    dates = [date.strftime('%Y-%m-%d') for date in hist.index]
                    prices = [round(float(price), 2) for price in hist['Close']]
                    
                    if len(dates) > 0 and len(prices) > 0:
                        historical_data = {
                            'symbol': symbol,
                            'dates': dates,
                            'prices': prices,
                            'period': period,
                            'source': 'Yahoo Finance'
                        }
                        
                        print(f"Successfully fetched {len(prices)} data points for {symbol}")
                        
                        # Cache the result
                        historical_data_cache[cache_key] = {
                            'timestamp': datetime.now(),
                            'data': historical_data
                        }
                        
                        return jsonify(historical_data)
                else:
                    print(f"No 'Close' column in yfinance data for {symbol}, columns: {list(hist.columns)}")
            else:
                print(f"Empty yfinance data for {symbol}")
        except Exception as yf_error:
            print(f"YFinance historical error for {symbol}: {yf_error}")
            import traceback
            traceback.print_exc()
        
        # Try to load historical data from CSV files
        print(f"Attempting to load historical data from CSV files for {symbol}")
        import pandas as pd
        import os
        
        try:
            # Look for historical data files
            csv_files = [
                f"HistoricalData/{symbol}_historical_2020-01-01_to_2025-08-28.csv",
                f"HistoricalData/{symbol}_historical_1975-01-01_to_2025-08-28.csv"
            ]
            
            df = None
            for csv_file in csv_files:
                if os.path.exists(csv_file):
                    print(f"Loading data from {csv_file}")
                    df = pd.read_csv(csv_file)
                    break
            
            if df is not None and not df.empty:
                # Convert dates and filter by period
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.sort_values('Date')
                
                # Map period to days for filtering
                period_days = {'30d': 30, '90d': 90, '1y': 365, '2y': 730}
                days = period_days.get(period, 30)
                
                # Filter to recent period
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                df_filtered = df[df['Date'] >= start_date]
                
                if not df_filtered.empty:
                    dates = [date.strftime('%Y-%m-%d') for date in df_filtered['Date']]
                    
                    # Try different close price column names
                    close_columns = ['Close', 'close', 'Close*', 'Adj Close', 'close split']
                    prices = None
                    
                    for col in close_columns:
                        if col in df_filtered.columns:
                            prices = [round(float(price), 2) for price in df_filtered[col]]
                            print(f"Using {col} column for {symbol} prices")
                            break
                    
                    if prices and len(dates) > 0:
                        historical_data = {
                            'symbol': symbol,
                            'dates': dates,
                            'prices': prices,
                            'period': period,
                            'source': f'Historical CSV ({len(dates)} data points)'
                        }
                        
                        print(f"Successfully loaded {len(prices)} data points from CSV for {symbol}")
                        
                        # Cache the result
                        historical_data_cache[cache_key] = {
                            'timestamp': datetime.now(),
                            'data': historical_data
                        }
                        
                        return jsonify(historical_data)
                else:
                    print(f"No data in specified period for {symbol}")
            else:
                print(f"No CSV data found for {symbol}")
        except Exception as csv_error:
            print(f"Error loading CSV data for {symbol}: {csv_error}")
            import traceback
            traceback.print_exc()
        
        # Generate sample data as final fallback
        print(f"Generating sample data for {symbol}")
        from datetime import datetime, timedelta
        import random
        
        # Map period to days for sample data
        period_days = {'30d': 30, '90d': 90, '1y': 365, '2y': 730}
        days = period_days.get(period, 30)
        
        # Generate sample dates and prices
        end_date = datetime.now()
        dates = []
        prices = []
        base_price = 229.72 if symbol == 'AAPL' else 150.0  # Use current price as base
        
        for i in range(days):
            date = end_date - timedelta(days=days-i-1)
            dates.append(date.strftime('%Y-%m-%d'))
            # Generate realistic price movement
            change = random.uniform(-0.02, 0.02)  # -2% to +2% daily change
            base_price = max(base_price * (1 + change), 1.0)  # Ensure price stays positive
            prices.append(round(base_price, 2))
        
        historical_data = {
            'symbol': symbol,
            'dates': dates,
            'prices': prices,
            'period': period,
            'source': f'Sample Data ({len(dates)} points)'
        }
        
        print(f"Generated {len(prices)} sample data points for {symbol}")
        
        # Cache the result
        historical_data_cache[cache_key] = {
            'timestamp': datetime.now(),
            'data': historical_data
        }
        
        return jsonify(historical_data)
        
    except Exception as e:
        print(f"Historical data API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_symbol():
    """Start sentiment analysis for a symbol"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper().strip()
        target_articles = data.get('target_articles', 50)
        
        if not symbol:
            return jsonify({'error': 'Symbol is required'}), 400
        
        if not symbol.replace('.', '').isalnum() or len(symbol) > 10:
            return jsonify({'error': 'Invalid symbol format'}), 400
        
        # Validate article count
        if target_articles < 5 or target_articles > 200:
            return jsonify({'error': 'Target articles must be between 5 and 200'}), 400
        
        # Check cache first
        cache_key = f"{symbol}_{target_articles}"
        if cache_key in analysis_cache:
            cached = analysis_cache[cache_key]
            # Check if cache is still valid (5 minutes)
            if (datetime.now() - cached['timestamp']).seconds < cache_timeout:
                print(f"Returning cached result for {symbol}")
                return jsonify(cached['result'])
        
        # Create unique analysis ID
        analysis_id = f"{symbol}_{target_articles}_{int(time.time())}"
        
        # Check if analysis is already running for this symbol
        existing_analysis = None
        for aid, analysis in active_analyses.items():
            if (analysis.symbol == symbol and 
                analysis.target_articles == target_articles and 
                analysis.status in ['starting', 'running']):
                existing_analysis = aid
                break
        
        if existing_analysis:
            return jsonify({
                'analysis_id': existing_analysis,
                'status': 'already_running',
                'message': f'Analysis already running for {symbol}'
            })
        
        # Start new background analysis
        analysis = AnalysisStatus(symbol, target_articles)
        active_analyses[analysis_id] = analysis
        
        # Start background thread
        thread = threading.Thread(
            target=run_background_analysis,
            args=(analysis_id, symbol, target_articles),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            'analysis_id': analysis_id,
            'status': 'started',
            'message': f'Started analysis for {symbol}'
        })
        
    except Exception as e:
        print(f"API error: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/status/<analysis_id>')
def get_analysis_status(analysis_id):
    """Get status of ongoing analysis"""
    try:
        if analysis_id not in active_analyses:
            return jsonify({'error': 'Analysis not found'}), 404
        
        analysis = active_analyses[analysis_id]
        
        response = {
            'analysis_id': analysis_id,
            'symbol': analysis.symbol,
            'status': analysis.status,
            'progress': analysis.progress,
            'message': analysis.message,
            'elapsed_time': int((datetime.now() - analysis.start_time).seconds)
        }
        
        if analysis.status == 'completed':
            response['result'] = analysis.result
            # Clean up completed analysis
            del active_analyses[analysis_id]
        elif analysis.status == 'error':
            response['error'] = analysis.error
            # Clean up failed analysis
            del active_analyses[analysis_id]
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Status API error: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/quick_analyze', methods=['POST'])
def quick_analyze():
    """Synchronous analysis for immediate results (for testing/small analyses)"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper().strip()
        target_articles = min(data.get('target_articles', 25), 25)  # Limit to 25 for quick analysis
        
        if not symbol:
            return jsonify({'error': 'Symbol is required'}), 400
            
        if not symbol.replace('.', '').isalnum() or len(symbol) > 10:
            return jsonify({'error': 'Invalid symbol format'}), 400
        
        print(f"Starting quick analysis for {symbol} with {target_articles} articles")
        
        # Run analysis directly (blocking)
        analyzer = StockSentimentAnalyzer(symbol)
        results = analyzer.analyze_sentiment(target_articles=target_articles)
        
        if "error" in results:
            return jsonify({'error': results["error"]}), 500
            
        return jsonify(results)
        
    except Exception as e:
        print(f"Quick analysis error: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_analyses': len(active_analyses),
        'cache_size': len(analysis_cache),
        'stock_info_cache_size': len(stock_info_cache),
        'historical_cache_size': len(historical_data_cache)
    })


@app.route('/api/examples')
def get_examples():
    """Get example stock symbols for the UI"""
    examples = [
        {'symbol': 'MSFT', 'name': 'Microsoft', 'sector': 'Technology'},
        {'symbol': 'AAPL', 'name': 'Apple', 'sector': 'Technology'},
        {'symbol': 'NVDA', 'name': 'NVIDIA', 'sector': 'Technology'},
        {'symbol': 'TSLA', 'name': 'Tesla', 'sector': 'Automotive'},
        {'symbol': 'GOOGL', 'name': 'Alphabet', 'sector': 'Technology'},
        {'symbol': 'AMZN', 'name': 'Amazon', 'sector': 'E-commerce'},
        {'symbol': 'META', 'name': 'Meta Platforms', 'sector': 'Social Media'},
        {'symbol': 'JPM', 'name': 'JPMorgan Chase', 'sector': 'Finance'},
        {'symbol': 'V', 'name': 'Visa', 'sector': 'Finance'},
        {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Healthcare'},
    ]
    return jsonify(examples)


def cleanup_old_analyses():
    """Clean up old analyses and cache entries"""
    current_time = datetime.now()
    
    # Clean up old analyses (older than 10 minutes)
    to_remove = []
    for analysis_id, analysis in active_analyses.items():
        if (current_time - analysis.start_time).seconds > 600:  # 10 minutes
            to_remove.append(analysis_id)
    
    for analysis_id in to_remove:
        del active_analyses[analysis_id]
    
    # Clean up old cache entries
    for cache_dict in [analysis_cache, stock_info_cache, historical_data_cache]:
        to_remove = []
        for cache_key, cached_data in cache_dict.items():
            if (current_time - cached_data['timestamp']).seconds > cache_timeout:
                to_remove.append(cache_key)
        
        for cache_key in to_remove:
            del cache_dict[cache_key]


# Cleanup old analyses every 5 minutes
def run_cleanup_task():
    while True:
        time.sleep(300)  # 5 minutes
        try:
            cleanup_old_analyses()
        except Exception as e:
            print(f"Cleanup task error: {e}")


# Start cleanup task
cleanup_thread = threading.Thread(target=run_cleanup_task, daemon=True)
cleanup_thread.start()


if __name__ == '__main__':
    print("Starting Enhanced Stock Sentiment Analyzer Web App...")
    print("Modern UI with real-time sentiment analysis")
    print("Features: Light/Dark theme, Historical data, Custom article amounts")
    print("Supports 50+ news sources with newspaper3k integration")
    print("Interactive charts and article previews")
    print("")
    print("Web UI will be available at: http://localhost:5000")
    print("Enhanced API endpoints:")
    print("   POST /api/analyze - Start background analysis")
    print("   GET  /api/status/<id> - Check analysis status") 
    print("   GET  /api/stock_info/<symbol> - Get current stock price")
    print("   GET  /api/historical/<symbol> - Get historical data")
    print("   POST /api/quick_analyze - Quick synchronous analysis")
    print("   GET  /api/health - Health check")
    print("   GET  /api/examples - Example stock symbols")
    print("")
    
    # Check if required dependencies are available
    try:
        from scrapers import GoogleNewsScraper
        print("Scrapers loaded successfully")
    except Exception as e:
        print(f"Warning: Scraper loading issue: {e}")
    
    try:
        # Try to import FinBERT dependencies
        import torch
        from transformers import AutoTokenizer
        print("FinBERT/Transformers available for enhanced sentiment analysis")
    except ImportError:
        print("Using TextBlob for sentiment analysis (install transformers for FinBERT)")
    
    try:
        # Check yfinance
        import yfinance as yf
        print("YFinance available for stock data")
    except ImportError:
        print("Warning: YFinance not available - stock info may be limited")
    
    print("\n" + "="*60)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # Set to False for production
        threaded=True
    )