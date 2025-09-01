import sentiment, historicalDataGetter, macrosentiment
from flask import Flask, request, jsonify, send_from_directory, send_file
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')
getter = historicalDataGetter.HistoricalDataGetter()
macro_analyzer = macrosentiment.MacroSentimentAnalyzer()
@app.route('/')
def index():
    return jsonify({
        "message": "Stock Trading AI API",
        "endpoints": {
            "/sentiment": "GET - Analyze stock sentiment",
            "/historical": "GET - Get historical stock data",
            "/current": "GET - Get current stock price", 
            "/macro": "GET - Analyze macro sentiment for stock (legacy)",
            "/macro/enhanced": "GET - Enhanced macro sentiment analysis",
            "/sector": "GET - Get sector outlook",
            "/files": "GET - List available files",
            "/files/<path>": "GET - Download specific file",
            "/health": "GET - Health check"
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/sentiment', methods=['GET'])
def get_sentiment():
    try:
        symbol = request.args.get('symbol')
        articles = request.args.get('articles', type=int, default=10)
        
        if not symbol:
            return jsonify({"error": "Symbol parameter is required"}), 400
            
        analyzer = sentiment.StockSentimentAnalyzer(symbol)
        results = analyzer.analyze_sentiment(target_articles=articles)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/historical', methods=['GET'])
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
def get_current_data():
    try:
        symbol = request.args.get('symbol')

        print(f"Received request for current price of symbol: {symbol}")
        if not all([symbol]):
            return jsonify({"error": "symbol parameter is required"}), 400
            
        data = getter.get_current_price_google_finance(symbol)
        
        if data is None:
            return jsonify({"error": "Failed to retrieve historical data"}), 500
            
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/macro', methods=['GET'])
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
def get_sector_outlook():
    try:
        sector = request.args.get('sector')
        days_back = request.args.get('days_back', type=int, default=7)
        
        if not sector:
            return jsonify({"error": "sector parameter is required"}), 400
            
        result = macro_analyzer.get_sector_outlook(sector, days_back)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/macro/enhanced', methods=['GET'])
def get_enhanced_macro_sentiment():
    try:
        symbol = request.args.get('symbol')
        days_back = request.args.get('days_back', type=int, default=7)
        min_quality = request.args.get('min_quality', type=float, default=0.6)
        
        if not symbol:
            return jsonify({"error": "symbol parameter is required"}), 400
        
        # Use enhanced analyzer directly
        enhanced_analyzer = macrosentiment.EnhancedMacroSentimentAnalyzer()
        result = enhanced_analyzer.analyze_sector_sentiment(
            symbol=symbol,
            days_back=days_back,
            min_quality_threshold=min_quality
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/files', methods=['GET'])
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
