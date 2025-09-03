#!/usr/bin/env python3
"""
Flask Web Application for Stock Sentiment Analyzer
Modern web UI that provides easy access to sentiment analysis functionality
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from datetime import datetime
import threading
import time
from typing import Dict, Any
import traceback

# Import our sentiment analyzer
from sentiment import StockSentimentAnalyzer

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Enable CORS for API calls

# Global cache for analysis results to avoid re-running same analysis
analysis_cache = {}
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
    """Serve the main web UI"""
    return send_from_directory('.', 'index.html')


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
        'cache_size': len(analysis_cache)
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
    to_remove = []
    for cache_key, cached_data in analysis_cache.items():
        if (current_time - cached_data['timestamp']).seconds > cache_timeout:
            to_remove.append(cache_key)
    
    for cache_key in to_remove:
        del analysis_cache[cache_key]


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
    print("Starting Stock Sentiment Analyzer Web App...")
    print("Modern UI with real-time sentiment analysis")
    print("Supports 50+ news sources with newspaper3k integration")
    print("Interactive charts and article previews")
    print("")
    print("Web UI will be available at: http://localhost:5000")
    print("API endpoints:")
    print("   POST /api/analyze - Start background analysis")
    print("   GET  /api/status/<id> - Check analysis status") 
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
    
    print("\n" + "="*60)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # Set to False for production
        threaded=True
    )