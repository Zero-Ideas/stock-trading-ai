import sentiment, historicalDataGetter
from flask import Flask, request, jsonify, send_from_directory, send_file, session, g
from flask_cors import CORS
import os
import json
from datetime import datetime
import hashlib
import secrets
import industry_analysis

# Import licensing and technical analysis
from license_manager import license_manager, require_license, admin_required
from unified import UnifiedAnalyzer
from technical_optimized import OptimizedTradingBot
import industry_analysis

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = secrets.token_hex(32)  # For session management
CORS(app, supports_credentials=True, origins=['http://localhost:5173'],
     allow_headers=['Content-Type', 'Authorization', 'X-Session-Token'],
     expose_headers=['Set-Cookie'])  # Enable CORS for web UI with credentials

# Initialize components
getter = historicalDataGetter.HistoricalDataGetter()
industry_analyzer = industry_analysis.IndustryAnalyzer()
unified_analyzer = UnifiedAnalyzer()
technical_bot = OptimizedTradingBot()
@app.route('/')
def index():
    return jsonify({
        "message": "Stock Trading AI API",
        "version": "2.0",
        "authentication": "License key required for most endpoints",
        "endpoints": {
            # Public endpoints
            "/health": "GET - Health check",
            "/auth/login": "POST - Login with license key",
            "/auth/logout": "POST - Logout and invalidate session",
            "/auth/validate": "GET - Validate current session",
            "/license/tiers": "GET - Get available license tiers",

            # Licensed endpoints
            "/sentiment": "GET - Analyze stock sentiment (requires sentiment feature)",
            "/technical": "GET - Technical analysis and predictions (requires technical feature)",
            "/unified": "GET - Comprehensive unified analysis (requires unified feature)",
            "/historical": "GET - Get historical stock data (requires historical feature)",
            "/current": "GET - Get current stock price (requires historical feature)",
            "/industry": "GET - Industry sentiment analysis (requires sentiment feature)",
            "/macro": "GET - Analyze macro sentiment for stock (requires sentiment feature)",
            "/macro/enhanced": "GET - Enhanced macro sentiment analysis (requires sentiment feature)",
            "/sector": "GET - Get sector outlook (requires sentiment feature)",

            # Admin endpoints (master license required)
            "/admin/licenses": "GET/POST - Manage license keys",
            "/admin/usage": "GET - View usage statistics",
            "/admin/sessions": "GET - View active sessions",
            "/files": "GET - List available files",
            "/files/<path>": "GET - Download specific file"
        }
    })

# Authentication endpoints
@app.route('/auth/login', methods=['POST'])
def login():
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

        # Store session token in Flask session
        session['session_token'] = session_result['session_token']
        session['license_key'] = license_key
        session['tier_name'] = validation['tier_name']
        session['user_name'] = validation['user_name']

        return jsonify({
            "success": True,
            "message": "Login successful",
            "session_token": session_result['session_token'],
            "tier_name": validation['tier_name'],
            "user_name": validation['user_name'],
            "features_enabled": validation['features_enabled']
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    try:
        session_token = session.get('session_token')
        if session_token:
            # Deactivate session in database
            from license_manager import license_manager
            with license_manager.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE license_sessions
                        SET is_active = FALSE
                        WHERE session_token = %s
                    """, (session_token,))
                conn.commit()

        # Clear Flask session
        session.clear()

        return jsonify({
            "success": True,
            "message": "Logout successful"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/auth/validate', methods=['GET'])
def validate_session():
    try:
        session_token = session.get('session_token')
        if not session_token:
            return jsonify({
                "valid": False,
                "message": "No active session"
            }), 401

        validation = license_manager.validate_session(session_token)
        return jsonify({
            "valid": validation['valid'],
            "tier_name": validation.get('tier_name'),
            "features_enabled": validation.get('features_enabled'),
            "message": validation['message']
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/license/tiers', methods=['GET'])
def get_license_tiers():
    try:
        tiers = license_manager.get_license_tiers()
        return jsonify({"tiers": tiers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/debug/session', methods=['GET'])
def debug_session():
    return jsonify({
        "session_data": dict(session),
        "headers": dict(request.headers),
        "cookies": dict(request.cookies)
    })

# Licensed endpoints
@app.route('/sentiment', methods=['GET'])
@require_license(['sentiment'])
def get_sentiment():
    try:
        symbol = request.args.get('symbol')
        articles = request.args.get('articles', type=int, default=10)

        if not symbol:
            return jsonify({"error": "Symbol parameter is required"}), 400

        analyzer = sentiment.StockSentimentAnalyzer(symbol)
        results = analyzer.analyze_sentiment(target_articles=articles)
        print("Sentiment analysis results:", results)  # Debugging log
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/technical', methods=['GET'])
@require_license(['technical'])
def get_technical_analysis():
    try:
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe', default='hour')
        model_type = request.args.get('model_type', default='xgboost')
        include_analysis = request.args.get('include_analysis', type=bool, default=True)
        data_limit = request.args.get('data_limit', type=int, default=500)

        if not symbol:
            return jsonify({"error": "Symbol parameter is required"}), 400

        # Get technical analysis prediction
        prediction_json = technical_bot.get_enhanced_prediction(
            symbol=symbol,
            timeframe=timeframe,
            model_type=model_type,
            include_analysis=include_analysis,
            data_limit=data_limit
        )

        prediction_data = json.loads(prediction_json)
        return jsonify(prediction_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/technical/compare', methods=['GET'])
@require_license(['technical'])
def get_technical_comparison():
    try:
        symbol = request.args.get('symbol')
        model_type = request.args.get('model_type', default='xgboost')
        data_limit = request.args.get('data_limit', type=int, default=500)

        if not symbol:
            return jsonify({"error": "Symbol parameter is required"}), 400

        # Get timeframe comparison
        comparison_data = technical_bot.compare_timeframes(
            symbol=symbol,
            model_type=model_type,
            data_limit=data_limit
        )

        return jsonify(comparison_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/unified', methods=['GET'])
@require_license(['unified'])
def get_unified_analysis():
    try:
        symbol = request.args.get('symbol')
        articles = request.args.get('articles', type=int, default=20)
        save_output = request.args.get('save_output', type=bool, default=False)

        if not symbol:
            return jsonify({"error": "Symbol parameter is required"}), 400

        # Run comprehensive unified analysis
        result = unified_analyzer.analyze_symbol(
            symbol=symbol.upper(),
            articles=articles,
            save_output=save_output
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/industry', methods=['GET'])
@require_license(['sentiment'])
def get_industry_analysis():
    try:
        symbol = request.args.get('symbol')
        force_refresh = request.args.get('force_refresh', type=bool, default=False)
        cache_hours = request.args.get('cache_hours', type=float, default=24.0)

        if not symbol:
            return jsonify({"error": "Symbol parameter is required"}), 400

        # Run industry analysis
        analyzer = industry_analysis.IndustryAnalyzer()
        result = analyzer.analyze_industry(
            target_company_symbol=symbol,
            force_refresh=force_refresh,
            cache_hours=cache_hours
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/historical', methods=['GET'])
@require_license(['historical'])
def get_historical_data():
    try:
        symbol = request.args.get('symbol')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not all([symbol, start_date, end_date]):
            return jsonify({"error": "symbol, start_date, and end_date parameters are required"}), 400

        data = getter.get_historical_data(symbol, start_date, end_date)

        if data is None:
            return jsonify({"error": "Failed to retrieve historical data"}), 500

        return jsonify(data.to_dict('records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/current', methods=['GET'])
@require_license(['historical'])
def get_current_data():
    try:
        symbol = request.args.get('symbol')

        if not symbol:
            return jsonify({"error": "symbol parameter is required"}), 400

        data = getter.get_current_price_google_finance(symbol)

        if data is None:
            return jsonify({"error": "Failed to retrieve current price data"}), 500

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/macro', methods=['GET'])
@require_license(['sentiment'])
def get_macro_sentiment():
    try:
        symbol = request.args.get('symbol')
        days_back = request.args.get('days_back', type=int, default=7)

        if not symbol:
            return jsonify({"error": "symbol parameter is required"}), 400

        result = macro_analyzer.analyze_macro_sentiment(symbol, days_back)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sector', methods=['GET'])
@require_license(['sentiment'])
def get_sector_outlook():
    try:
        sector = request.args.get('sector')
        days_back = request.args.get('days_back', type=int, default=7)

        if not sector:
            return jsonify({"error": "sector parameter is required"}), 400

        result = industry_analyzer.analyze_industry()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/macro/enhanced', methods=['GET'])
@require_license(['sentiment'])
def get_enhanced_macro_sentiment():
    try:
        symbol = request.args.get('symbol')
        days_back = request.args.get('days_back', type=int, default=7)
        min_quality = request.args.get('min_quality', type=float, default=0.6)

        if not symbol:
            return jsonify({"error": "symbol parameter is required"}), 400

        # Use industry_analyzer
        return
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Admin endpoints
@app.route('/admin/licenses', methods=['GET'])
@admin_required
def admin_list_licenses():
    try:
        with license_manager.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT lk.id, lk.license_key, lk.user_name, lk.user_email,
                           lk.is_active, lk.expires_at, lk.disabled_message,
                           lk.created_at, lk.last_used_at,
                           lt.tier_name, lt.display_name
                    FROM license_keys lk
                    JOIN license_tiers lt ON lk.tier_id = lt.id
                    ORDER BY lk.created_at DESC
                """)

                licenses = []
                for row in cursor.fetchall():
                    licenses.append({
                        'id': row['id'],
                        'license_key': row['license_key'][:8] + '...',  # Hide full key
                        'user_name': row['user_name'],
                        'user_email': row['user_email'],
                        'tier_name': row['tier_name'],
                        'tier_display': row['display_name'],
                        'is_active': row['is_active'],
                        'expires_at': row['expires_at'].isoformat() if row['expires_at'] else None,
                        'disabled_message': row['disabled_message'],
                        'created_at': row['created_at'].isoformat(),
                        'last_used_at': row['last_used_at'].isoformat() if row['last_used_at'] else None
                    })

                return jsonify({'licenses': licenses})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/licenses', methods=['POST'])
@admin_required
def admin_create_license():
    try:
        data = request.get_json()
        tier_name = data.get('tier_name')
        user_name = data.get('user_name')
        user_email = data.get('user_email')
        expires_days = data.get('expires_days')

        if not tier_name:
            return jsonify({"error": "tier_name is required"}), 400

        license_key = license_manager.generate_license_key(
            tier_name=tier_name,
            user_name=user_name,
            user_email=user_email,
            expires_days=expires_days
        )

        return jsonify({
            'success': True,
            'license_key': license_key,
            'message': f'License key created successfully for {user_name or "Anonymous"}'
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/usage', methods=['GET'])
@admin_required
def admin_usage_stats():
    try:
        license_key = request.args.get('license_key')
        days_back = request.args.get('days_back', type=int, default=30)

        stats = license_manager.get_license_usage_stats(
            license_key=license_key,
            days_back=days_back
        )

        return jsonify({'usage_stats': stats})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/sessions', methods=['GET'])
@admin_required
def admin_active_sessions():
    try:
        with license_manager.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT ls.id, ls.session_token, ls.device_fingerprint,
                           ls.ip_address, ls.is_active, ls.expires_at,
                           ls.created_at, ls.last_activity_at,
                           lk.user_name, lt.tier_name
                    FROM license_sessions ls
                    JOIN license_keys lk ON ls.license_key_id = lk.id
                    JOIN license_tiers lt ON lk.tier_id = lt.id
                    WHERE ls.is_active = TRUE
                    ORDER BY ls.last_activity_at DESC
                """)

                sessions = []
                for row in cursor.fetchall():
                    sessions.append({
                        'id': row['id'],
                        'session_token': row['session_token'][:8] + '...',  # Hide full token
                        'user_name': row['user_name'],
                        'tier_name': row['tier_name'],
                        'device_fingerprint': row['device_fingerprint'][:8] + '...' if row['device_fingerprint'] else None,
                        'ip_address': str(row['ip_address']) if row['ip_address'] else None,
                        'expires_at': row['expires_at'].isoformat() if row['expires_at'] else None,
                        'created_at': row['created_at'].isoformat(),
                        'last_activity_at': row['last_activity_at'].isoformat()
                    })

                return jsonify({'active_sessions': sessions})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/files', methods=['GET'])
@admin_required
def list_files():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        files = []

        for root, dirs, filenames in os.walk(base_dir):
            for filename in filenames:
                if not filename.startswith('.') and filename.endswith(('.py', '.csv', '.json', '.txt')):
                    rel_path = os.path.relpath(os.path.join(root, filename), base_dir)
                    files.append({
                        "name": filename,
                        "path": rel_path.replace('\\', '/'),
                        "size": os.path.getsize(os.path.join(root, filename))
                    })

        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/files/<path:filename>', methods=['GET'])
@admin_required
def download_file(filename):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, filename.replace('/', '\\'))

        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return jsonify({"error": "File not found"}), 404

        return send_file(file_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
