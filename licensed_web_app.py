#!/usr/bin/env python3
"""
Licensed Flask Web Application for Stock Trading AI
Modern web UI with license key authentication and comprehensive features
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, flash
from flask_cors import CORS
import os
import json
import secrets
from datetime import datetime, timedelta
import threading
import time
from typing import Dict, Any, Optional
import traceback

# Import our components
from license_manager import license_manager
from sentiment import StockSentimentAnalyzer
from historicalDataGetter import HistoricalDataGetter
from unified import UnifiedAnalyzer
from technical_optimized import OptimizedTradingBot
import industry_analysis

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = secrets.token_hex(32)
CORS(app)

# Global cache for analysis results
analysis_cache = {}
stock_info_cache = {}
historical_data_cache = {}
cache_timeout = 300  # 5 minutes

# Background analysis tracking
active_analyses = {}

class AnalysisStatus:
    """Track status of ongoing analyses"""
    def __init__(self, symbol: str, analysis_type: str, params: Dict):
        self.symbol = symbol
        self.analysis_type = analysis_type
        self.params = params
        self.status = "starting"  # starting, running, completed, error
        self.progress = 0
        self.message = "Initializing analysis..."
        self.result = None
        self.error = None
        self.start_time = datetime.now()

def require_session_login(f):
    """Decorator to require valid session for web routes"""
    def decorated_function(*args, **kwargs):
        if 'session_token' not in session:
            return redirect(url_for('login_page'))

        # Validate session
        validation = license_manager.validate_session(session['session_token'])
        if not validation['valid']:
            session.clear()
            flash('Your session has expired. Please log in again.', 'warning')
            return redirect(url_for('login_page'))

        # Store validation info for use in templates
        session['tier_name'] = validation['tier_name']
        session['features_enabled'] = validation['features_enabled']

        return f(*args, **kwargs)

    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
def index():
    """Home page - redirect to login if not authenticated"""
    if 'session_token' in session:
        validation = license_manager.validate_session(session['session_token'])
        if validation['valid']:
            return redirect(url_for('dashboard'))

    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    """Handle login API call"""
    try:
        data = request.get_json()
        license_key = data.get('license_key')

        if not license_key:
            return jsonify({"error": "License key is required"}), 400

        # Validate license key
        validation = license_manager.validate_license_key(license_key)
        if not validation['valid']:
            return jsonify({
                "error": "Invalid license key",
                "message": validation['message']
            }), 401

        # Generate device fingerprint
        import hashlib
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.remote_addr
        device_fingerprint = hashlib.sha256(f"{user_agent}_{ip_address}".encode()).hexdigest()[:32]

        # Create session
        session_result = license_manager.create_session(
            license_key=license_key,
            device_fingerprint=device_fingerprint,
            user_agent=user_agent,
            ip_address=ip_address
        )

        if not session_result['success']:
            return jsonify({
                "error": "Session creation failed",
                "message": session_result['message']
            }), 400

        # Store session info
        session['session_token'] = session_result['session_token']
        session['license_key'] = license_key
        session['tier_name'] = validation['tier_name']
        session['user_name'] = validation['user_name']
        session['features_enabled'] = validation['features_enabled']

        return jsonify({
            "success": True,
            "message": "Login successful",
            "tier_name": validation['tier_name'],
            "user_name": validation['user_name'],
            "features_enabled": validation['features_enabled']
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Handle logout"""
    try:
        session_token = session.get('session_token')
        if session_token:
            # Deactivate session in database
            with license_manager.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE license_sessions
                        SET is_active = FALSE
                        WHERE session_token = %s
                    """, (session_token,))
                conn.commit()

        session.clear()
        return jsonify({"success": True, "message": "Logout successful"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/logout')
def logout():
    """Logout route"""
    session_token = session.get('session_token')
    if session_token:
        try:
            with license_manager.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE license_sessions
                        SET is_active = FALSE
                        WHERE session_token = %s
                    """, (session_token,))
                conn.commit()
        except:
            pass  # Ignore database errors during logout

    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login_page'))

@app.route('/dashboard')
@require_session_login
def dashboard():
    """Main dashboard"""
    features = session.get('features_enabled', {})
    tier_name = session.get('tier_name', 'unknown')
    user_name = session.get('user_name', 'User')

    return render_template('dashboard.html',
                         features=features,
                         tier_name=tier_name,
                         user_name=user_name)

@app.route('/analyze')
@require_session_login
def analyze_page():
    """Analysis page"""
    features = session.get('features_enabled', {})
    return render_template('analyze.html', features=features)

def check_feature_access(feature_name):
    """Check if user has access to a specific feature"""
    features = session.get('features_enabled', {})
    return features.get(feature_name, False)

@app.route('/api/sentiment')
@require_session_login
def api_sentiment():
    """Sentiment analysis API endpoint"""
    if not check_feature_access('sentiment'):
        return jsonify({"error": "Sentiment analysis not available in your license"}), 403

    try:
        symbol = request.args.get('symbol', '').upper()
        articles = int(request.args.get('articles', 20))

        if not symbol:
            return jsonify({"error": "Symbol is required"}), 400

        # Check cache first
        cache_key = f"sentiment_{symbol}_{articles}"
        if cache_key in analysis_cache:
            cache_data = analysis_cache[cache_key]
            if datetime.now() - cache_data['timestamp'] < timedelta(seconds=cache_timeout):
                return jsonify(cache_data['result'])

        # Run analysis
        analyzer = StockSentimentAnalyzer(symbol)
        result = analyzer.analyze_sentiment(target_articles=articles)

        # Cache result
        analysis_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/technical')
@require_session_login
def api_technical():
    """Technical analysis API endpoint"""
    if not check_feature_access('technical'):
        return jsonify({"error": "Technical analysis not available in your license"}), 403

    try:
        symbol = request.args.get('symbol', '').upper()
        timeframe = request.args.get('timeframe', 'hour')

        if not symbol:
            return jsonify({"error": "Symbol is required"}), 400

        # Check cache first
        cache_key = f"technical_{symbol}_{timeframe}"
        if cache_key in analysis_cache:
            cache_data = analysis_cache[cache_key]
            if datetime.now() - cache_data['timestamp'] < timedelta(seconds=cache_timeout):
                return jsonify(cache_data['result'])

        # Run technical analysis
        bot = OptimizedTradingBot()
        prediction_json = bot.get_enhanced_prediction(
            symbol=symbol,
            timeframe=timeframe,
            model_type='xgboost',
            include_analysis=True,
            data_limit=500
        )

        result = json.loads(prediction_json)

        # Cache result
        analysis_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/unified')
@require_session_login
def api_unified():
    """Unified analysis API endpoint"""
    if not check_feature_access('unified'):
        return jsonify({"error": "Unified analysis not available in your license"}), 403

    try:
        symbol = request.args.get('symbol', '').upper()
        articles = int(request.args.get('articles', 20))

        if not symbol:
            return jsonify({"error": "Symbol is required"}), 400

        # Check cache first
        cache_key = f"unified_{symbol}_{articles}"
        if cache_key in analysis_cache:
            cache_data = analysis_cache[cache_key]
            if datetime.now() - cache_data['timestamp'] < timedelta(seconds=cache_timeout):
                return jsonify(cache_data['result'])

        # Run unified analysis
        analyzer = UnifiedAnalyzer()
        result = analyzer.analyze_symbol(
            symbol=symbol,
            articles=articles,
            save_output=False
        )

        # Cache result
        analysis_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/industry')
@require_session_login
def api_industry():
    """Industry analysis API endpoint"""
    if not check_feature_access('sentiment'):
        return jsonify({"error": "Industry analysis not available in your license"}), 403

    try:
        symbol = request.args.get('symbol', '').upper()

        if not symbol:
            return jsonify({"error": "Symbol is required"}), 400

        # Check cache first
        cache_key = f"industry_{symbol}"
        if cache_key in analysis_cache:
            cache_data = analysis_cache[cache_key]
            if datetime.now() - cache_data['timestamp'] < timedelta(seconds=cache_timeout):
                return jsonify(cache_data['result'])

        # Run industry analysis
        analyzer = industry_analysis.IndustryAnalyzer()
        result = analyzer.analyze_industry(
            target_company_symbol=symbol,
            force_refresh=False,
            cache_hours=24.0
        )

        # Cache result
        analysis_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/historical')
@require_session_login
def api_historical():
    """Historical data API endpoint"""
    if not check_feature_access('historical'):
        return jsonify({"error": "Historical data not available in your license"}), 403

    try:
        symbol = request.args.get('symbol', '').upper()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not all([symbol, start_date, end_date]):
            return jsonify({"error": "Symbol, start_date, and end_date are required"}), 400

        # Get historical data
        getter = HistoricalDataGetter()
        data = getter.get_historical_data(symbol, start_date, end_date)

        if data is None:
            return jsonify({"error": "Failed to retrieve historical data"}), 500

        return jsonify(data.to_dict('records'))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/license-info')
@require_session_login
def api_license_info():
    """Get current license information"""
    return jsonify({
        'tier_name': session.get('tier_name'),
        'user_name': session.get('user_name'),
        'features_enabled': session.get('features_enabled', {}),
        'session_valid': True
    })

@app.route('/api/license-tiers')
def api_license_tiers():
    """Get available license tiers (public endpoint)"""
    try:
        tiers = license_manager.get_license_tiers()
        return jsonify({"tiers": tiers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html',
                         error_code=404,
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html',
                         error_code=500,
                         error_message="Internal server error"), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)