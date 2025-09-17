#!/usr/bin/env python3
"""
Technical Trading Bot - ML-Based Trading Signal Generator
Implements the complete pipeline from data preparation to JSON prediction output
"""

import numpy as np
import pandas as pd
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Database and ML imports
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

# Technical analysis
import pandas_ta as ta

# ML libraries
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, accuracy_score
import xgboost as xgb

# Performance analysis
import scipy.stats as stats


class TechnicalTradingBot:
    """Complete Technical Trading Bot with ML predictions and backtesting"""

    def __init__(self, host='localhost', port=5432, database='stock_sentiment',
                 username='postgres', password=None):
        """Initialize the trading bot with database connection"""
        self.db_config = {
            'host': host,
            'port': port,
            'database': database,
            'user': username,
            'password': password or self._get_password()
        }
        self._test_connection()

    def _get_password(self) -> str:
        """Get PostgreSQL password from config or environment"""
        import os
        import sys

        # Try environment variable
        password = os.getenv('POSTGRES_PASSWORD')
        if password:
            return password

        # Try config file
        try:
            sys.path.insert(0, '.')
            import database_config
            if hasattr(database_config, 'POSTGRES_CONFIG'):
                return database_config.POSTGRES_CONFIG.get('password')
        except ImportError:
            pass

        # Try common passwords
        common_passwords = ['postgres', '', 'admin', 'password']
        for pwd in common_passwords:
            if self._try_connection(pwd):
                return pwd

        raise Exception("Could not connect to PostgreSQL. Please set POSTGRES_PASSWORD environment variable.")

    def _try_connection(self, password: str) -> bool:
        """Test connection with given password"""
        try:
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                database='postgres',
                user=self.db_config['user'],
                password=password
            )
            conn.close()
            return True
        except:
            return False

    def _test_connection(self):
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            print("[SUCCESS] Database connection established")
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config, cursor_factory=psycopg2.extras.RealDictCursor)
            yield conn
        finally:
            if conn:
                conn.close()

    def load_stock_data(self, symbol: str, timeframe: str = 'hour', limit: int = None) -> pd.DataFrame:
        """
        Load stock data from database for a specific symbol and timeframe

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            timeframe: 'day', 'hour', or 'minute'
            limit: Maximum number of records to load (None = all data)

        Returns:
            DataFrame with OHLCV data and metadata
        """
        if limit is None:
            print(f"[DATA] Loading ALL {timeframe}ly records for {symbol}")
        else:
            print(f"[DATA] Loading {limit} {timeframe}ly records for {symbol}")

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                if limit is None:
                    # Load all data
                    query = f"""
                        SELECT symbol, price_timestamp, open, high, low, close, volume,
                               trade_count, vwap, original
                        FROM stock_data_{timeframe}
                        WHERE symbol = %s
                        ORDER BY price_timestamp ASC
                    """
                    cursor.execute(query, (symbol,))
                else:
                    # Load limited recent data
                    query = f"""
                        SELECT symbol, price_timestamp, open, high, low, close, volume,
                               trade_count, vwap, original
                        FROM stock_data_{timeframe}
                        WHERE symbol = %s
                        ORDER BY price_timestamp DESC
                        LIMIT %s
                    """
                    cursor.execute(query, (symbol, limit))
                rows = cursor.fetchall()

                # Convert to DataFrame manually
                if not rows:
                    df = pd.DataFrame()
                else:
                    # Get column names
                    columns = [desc[0] for desc in cursor.description]

                    # Convert rows to list of dictionaries
                    data = []
                    for row in rows:
                        if hasattr(row, 'keys'):
                            row_dict = dict(row)
                        else:
                            row_dict = dict(zip(columns, row))
                        data.append(row_dict)

                    df = pd.DataFrame(data)

        if df.empty:
            raise ValueError(f"No data found for {symbol} in {timeframe} timeframe")


        # Convert timestamp and set as index
        # Handle timezone-aware datetime objects from PostgreSQL
        if 'price_timestamp' in df.columns:
            # Convert timezone-aware datetime to timezone-naive for pandas compatibility
            df['price_timestamp'] = pd.to_datetime(df['price_timestamp'], utc=True).dt.tz_localize(None)
            df.set_index('price_timestamp', inplace=True)

            # Sort by timestamp ascending for proper time series analysis
            if not df.index.is_monotonic_increasing:
                df = df.sort_index()

        # Convert numeric columns
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'trade_count', 'vwap']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Filter out forward-filled data for training if specified
        # Keep original data only for better quality
        original_count = len(df)
        df_original = df[df['original'] == True].copy()

        print(f"[DATA] Loaded {len(df_original)} original records (filtered {original_count - len(df_original)} forward-filled)")

        return df_original if len(df_original) > 100 else df

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate comprehensive technical indicators

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with added technical indicators
        """
        print("[FEATURES] Calculating technical indicators")

        # Make a copy to avoid modifying original
        data = df.copy()

        # Trend Indicators
        data['sma_10'] = ta.sma(data['close'], length=10)
        data['sma_20'] = ta.sma(data['close'], length=20)
        data['sma_50'] = ta.sma(data['close'], length=50)
        data['ema_10'] = ta.ema(data['close'], length=10)
        data['ema_20'] = ta.ema(data['close'], length=20)
        data['ema_50'] = ta.ema(data['close'], length=50)

        # MACD
        macd_data = ta.macd(data['close'])
        if macd_data is not None:
            data = pd.concat([data, macd_data], axis=1)

        # ADX (Directional Movement)
        adx_data = ta.adx(data['high'], data['low'], data['close'], length=14)
        if adx_data is not None:
            data = pd.concat([data, adx_data], axis=1)

        # Momentum Indicators
        data['rsi'] = ta.rsi(data['close'], length=14)

        # Stochastic
        stoch_data = ta.stoch(data['high'], data['low'], data['close'])
        if stoch_data is not None:
            data = pd.concat([data, stoch_data], axis=1)

        # Volatility Indicators
        bb_data = ta.bbands(data['close'], length=20, std=2)
        if bb_data is not None:
            data = pd.concat([data, bb_data], axis=1)

        data['atr'] = ta.atr(data['high'], data['low'], data['close'], length=14)

        # Volume Indicators
        data['obv'] = ta.obv(data['close'], data['volume'])

        # Price-based features
        data['price_change'] = data['close'].pct_change()
        data['high_low_pct'] = (data['high'] - data['low']) / data['close']
        data['close_open_pct'] = (data['close'] - data['open']) / data['open']

        # Volume features
        data['volume_sma'] = ta.sma(data['volume'], length=20)
        data['volume_ratio'] = data['volume'] / data['volume_sma']

        # Relative position indicators
        data['close_sma20_ratio'] = data['close'] / data['sma_20']
        data['close_sma50_ratio'] = data['close'] / data['sma_50']

        print(f"[FEATURES] Added {len([col for col in data.columns if col not in df.columns])} technical indicators")

        return data

    def create_prediction_labels(self, df: pd.DataFrame, periods_ahead: int = 5,
                               threshold_pct: float = 1.0) -> pd.DataFrame:
        """
        Create prediction labels for classification (Buy/Sell/Hold)

        Args:
            df: DataFrame with price data
            periods_ahead: Number of periods to look ahead
            threshold_pct: Price change threshold percentage

        Returns:
            DataFrame with added target labels
        """
        print(f"[LABELS] Creating prediction labels ({periods_ahead} periods ahead, {threshold_pct}% threshold)")

        data = df.copy()

        # Calculate future price change
        data['future_close'] = data['close'].shift(-periods_ahead)
        data['future_return'] = (data['future_close'] - data['close']) / data['close'] * 100

        # Create classification labels
        def classify_signal(future_return):
            if pd.isna(future_return):
                return None
            elif future_return > threshold_pct:
                return 1  # Buy signal
            elif future_return < -threshold_pct:
                return -1  # Sell signal
            else:
                return 0  # Hold signal

        data['target'] = data['future_return'].apply(classify_signal)

        # Remove rows without valid targets
        data = data.dropna(subset=['target'])

        # Label distribution
        label_counts = data['target'].value_counts().sort_index()
        print(f"[LABELS] Label distribution:")
        for label, count in label_counts.items():
            label_name = {-1: 'Sell', 0: 'Hold', 1: 'Buy'}[label]
            pct = count / len(data) * 100
            print(f"  {label_name}: {count} ({pct:.1f}%)")

        return data

    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Prepare feature matrix by selecting relevant columns and handling missing data

        Args:
            df: DataFrame with indicators and targets

        Returns:
            Tuple of (features_df, feature_names_list)
        """
        print("[FEATURES] Preparing feature matrix")

        # Define feature columns (exclude metadata and target columns)
        exclude_cols = ['symbol', 'original', 'target', 'future_close', 'future_return']
        feature_cols = [col for col in df.columns if col not in exclude_cols]

        # Select features
        features = df[feature_cols].copy()

        # Handle missing values - drop rows with too many NaNs
        initial_rows = len(features)
        features = features.dropna()

        print(f"[FEATURES] Selected {len(feature_cols)} features, kept {len(features)}/{initial_rows} rows after removing NaNs")

        return features, feature_cols

    def split_temporal_data(self, df: pd.DataFrame, train_end_date: str = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split data temporally (older data for training, recent data for testing)

        Args:
            df: DataFrame with time-indexed data
            train_end_date: End date for training data (YYYY-MM-DD)

        Returns:
            Tuple of (train_df, test_df)
        """
        if train_end_date is None:
            # Use 80% of data for training by default
            split_idx = int(len(df) * 0.8)
            train_data = df.iloc[:split_idx]
            test_data = df.iloc[split_idx:]
        else:
            train_end = pd.to_datetime(train_end_date)
            train_data = df[df.index <= train_end]
            test_data = df[df.index > train_end]

        print(f"[SPLIT] Training: {len(train_data)} records ({train_data.index.min()} to {train_data.index.max()})")
        print(f"[SPLIT] Testing: {len(test_data)} records ({test_data.index.min()} to {test_data.index.max()})")

        return train_data, test_data

    def train_model(self, X_train: pd.DataFrame, y_train: pd.Series, model_type: str = 'xgboost') -> Tuple[object, dict]:
        """
        Train machine learning model

        Args:
            X_train: Training features
            y_train: Training targets
            model_type: 'xgboost' or 'random_forest'

        Returns:
            Tuple of (trained model object, label_mapping)
        """
        print(f"[MODEL] Training {model_type} model on {len(X_train)} samples")

        # Create label mapping for XGBoost (needs 0,1,2 labels)
        unique_labels = sorted(y_train.unique())
        label_mapping = {label: i for i, label in enumerate(unique_labels)}
        reverse_mapping = {i: label for label, i in label_mapping.items()}

        # Convert labels for training
        y_train_mapped = y_train.map(label_mapping)

        print(f"[MODEL] Label mapping: {label_mapping}")

        if model_type == 'xgboost':
            model = xgb.XGBClassifier(
                objective='multi:softmax',
                num_class=len(unique_labels),
                max_depth=6,
                learning_rate=0.1,
                n_estimators=100,
                random_state=42,
                eval_metric='mlogloss'
            )
        elif model_type == 'random_forest':
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

        # Train model with mapped labels
        model.fit(X_train, y_train_mapped)

        # Get feature importance
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            feature_importance = list(zip(X_train.columns, importances))
            feature_importance.sort(key=lambda x: x[1], reverse=True)

            print("[MODEL] Top 10 most important features:")
            for feature, importance in feature_importance[:10]:
                print(f"  {feature}: {importance:.4f}")

        return model, reverse_mapping

    def backtest_strategy(self, model, X_test: pd.DataFrame, y_test: pd.Series,
                         test_prices: pd.Series, label_mapping: dict) -> Dict:
        """
        Backtest the trading strategy on test data

        Args:
            model: Trained ML model
            X_test: Test features
            y_test: True test labels
            test_prices: Test period prices

        Returns:
            Dictionary of backtest metrics
        """
        print("[BACKTEST] Running strategy simulation")

        # Get predictions and probabilities
        predictions_mapped = model.predict(X_test)
        # Convert predictions back to original labels
        predictions = pd.Series(predictions_mapped).map(label_mapping)

        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(X_test)
        else:
            probabilities = None

        # Initialize backtest variables
        portfolio_value = 10000  # Starting capital
        position = 0  # 0 = no position, 1 = long, -1 = short
        trades = []
        portfolio_values = [portfolio_value]

        transaction_cost = 0.001  # 0.1% transaction cost

        # Simulate trading
        for i in range(len(predictions)):
            pred = predictions[i]
            price = test_prices.iloc[i]

            # Trading logic
            if pred == 1 and position <= 0:  # Buy signal
                if position == -1:  # Close short position
                    portfolio_value = portfolio_value * (1 - transaction_cost)
                # Open long position
                position = 1
                entry_price = price
                trades.append(('BUY', price, X_test.index[i]))

            elif pred == -1 and position >= 0:  # Sell signal
                if position == 1:  # Close long position
                    portfolio_value = portfolio_value * (price / entry_price) * (1 - transaction_cost)
                # Open short position
                position = -1
                entry_price = price
                trades.append(('SELL', price, X_test.index[i]))

            # Calculate current portfolio value based on position
            if position == 1:  # Long position
                current_value = portfolio_value * (price / entry_price)
            elif position == -1:  # Short position
                current_value = portfolio_value * (entry_price / price)
            else:  # No position
                current_value = portfolio_value

            portfolio_values.append(current_value)

        # Calculate performance metrics
        portfolio_values = np.array(portfolio_values[1:])  # Remove initial value
        returns = np.diff(portfolio_values) / portfolio_values[:-1]

        # Buy and hold benchmark
        buy_hold_return = (test_prices.iloc[-1] / test_prices.iloc[0] - 1) * 100

        # Strategy metrics
        total_return_pct = (portfolio_values[-1] / 10000 - 1) * 100

        if len(returns) > 1:
            sharpe_ratio = np.sqrt(252) * np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0

            # Calculate drawdown
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            max_drawdown_pct = np.min(drawdown) * 100

            # Sortino ratio (downside deviation)
            downside_returns = returns[returns < 0]
            sortino_ratio = np.sqrt(252) * np.mean(returns) / np.std(downside_returns) if len(downside_returns) > 0 and np.std(downside_returns) > 0 else 0

            # Calmar ratio
            calmar_ratio = (total_return_pct / 100) / abs(max_drawdown_pct / 100) if max_drawdown_pct < 0 else 0

            # R-squared vs market (correlation with buy-and-hold)
            market_returns = np.diff(test_prices) / test_prices[:-1]
            if len(market_returns) == len(returns):
                r_squared_vs_market = np.corrcoef(returns, market_returns)[0, 1] ** 2 if not np.isnan(np.corrcoef(returns, market_returns)[0, 1]) else 0
            else:
                r_squared_vs_market = 0
        else:
            sharpe_ratio = 0
            sortino_ratio = 0
            calmar_ratio = 0
            max_drawdown_pct = 0
            r_squared_vs_market = 0

        # Model accuracy
        accuracy = accuracy_score(y_test, predictions)

        metrics = {
            'total_return_pct': total_return_pct,
            'buy_hold_return_pct': buy_hold_return,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown_pct': max_drawdown_pct,
            'r_squared_vs_market': r_squared_vs_market,
            'accuracy': accuracy,
            'num_trades': len(trades),
            'final_portfolio_value': portfolio_values[-1]
        }

        print(f"[BACKTEST] Strategy return: {total_return_pct:.2f}% vs Buy & Hold: {buy_hold_return:.2f}%")
        print(f"[BACKTEST] Sharpe ratio: {sharpe_ratio:.3f}, Max drawdown: {max_drawdown_pct:.2f}%")
        print(f"[BACKTEST] Model accuracy: {accuracy:.3f}, Trades executed: {len(trades)}")

        return metrics

    def generate_prediction(self, symbol: str, model, feature_names: List[str],
                          latest_data: pd.DataFrame, backtest_metrics: Dict, label_mapping: dict) -> str:
        """
        Generate JSON prediction output for the latest data

        Args:
            symbol: Stock symbol
            model: Trained model
            feature_names: List of feature column names
            latest_data: Latest market data with indicators
            backtest_metrics: Backtesting performance metrics

        Returns:
            JSON string with prediction and analysis
        """
        print("[PREDICTION] Generating final prediction")

        # Get the most recent data point
        latest_features = latest_data[feature_names].iloc[-1:].fillna(0)

        # Make prediction
        prediction_mapped = model.predict(latest_features)[0]
        prediction = label_mapping[prediction_mapped]

        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(latest_features)[0]
            confidence_score = np.max(probabilities)
        else:
            confidence_score = 0.5

        # Map prediction to label
        prediction_labels = {-1: 'Sell', 0: 'Hold', 1: 'Buy'}
        prediction_label = prediction_labels[prediction]

        # Get feature importance for key drivers
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            feature_importance = dict(zip(feature_names, importances))
            # Get top 5 features
            key_drivers = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5])
        else:
            key_drivers = {}

        # Get latest indicator values for analysis
        latest_indicators = {}
        indicator_cols = ['rsi', 'sma_20', 'ema_20', 'close', 'volume', 'atr']
        for col in indicator_cols:
            if col in latest_data.columns:
                latest_indicators[col] = float(latest_data[col].iloc[-1]) if not pd.isna(latest_data[col].iloc[-1]) else 0.0

        # Get time range for indicators
        time_range = {
            'start_date': latest_data.index[0].isoformat(),
            'end_date': latest_data.index[-1].isoformat(),
            'data_points': len(latest_data)
        }

        # Assemble final JSON
        output = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "symbol": symbol,
            "prediction": prediction_label,
            "confidence_score": float(confidence_score),
            "analysis": {
                "indicators": {
                    "time_range": time_range,
                    "values": latest_indicators
                },
                "risk_return": {
                    "sharpe_ratio": backtest_metrics.get("sharpe_ratio"),
                    "sortino_ratio": backtest_metrics.get("sortino_ratio"),
                    "calmar_ratio": backtest_metrics.get("calmar_ratio"),
                    "max_drawdown_pct": backtest_metrics.get("max_drawdown_pct")
                },
                "performance": {
                    "backtest_total_return_pct": backtest_metrics.get("total_return_pct"),
                    "r_squared_vs_market": backtest_metrics.get("r_squared_vs_market"),
                    "model_accuracy": backtest_metrics.get("accuracy"),
                    "buy_hold_return_pct": backtest_metrics.get("buy_hold_return_pct")
                },
                "key_drivers": key_drivers
            }
        }

        # Convert numpy types to Python types for JSON serialization
        def convert_types(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(v) for v in obj]
            return obj

        output = convert_types(output)
        return json.dumps(output, indent=2)

    def run_full_analysis(self, symbol: str, timeframe: str = 'hour',
                         model_type: str = 'xgboost', periods_ahead: int = 5,
                         threshold_pct: float = 1.0, limit: int = None) -> str:
        """
        Run complete analysis pipeline from data loading to prediction

        Args:
            symbol: Stock symbol to analyze
            timeframe: Data timeframe ('day', 'hour', 'minute')
            model_type: ML model type ('xgboost', 'random_forest')
            periods_ahead: Periods to look ahead for labeling
            threshold_pct: Price change threshold percentage
            limit: Maximum records to load (None = all data)

        Returns:
            JSON prediction string
        """
        if limit is None:
            print(f"[START] Running FULL DATASET analysis for {symbol}")
        else:
            print(f"[START] Running analysis for {symbol} (limit: {limit} records)")

        # Step 1: Load and prepare data
        df = self.load_stock_data(symbol, timeframe, limit)
        df_with_indicators = self.calculate_technical_indicators(df)
        df_labeled = self.create_prediction_labels(df_with_indicators, periods_ahead, threshold_pct)

        # Step 2: Prepare features
        features_df, feature_names = self.prepare_features(df_labeled)

        # Align features with targets
        aligned_data = features_df.join(df_labeled['target'], how='inner')
        aligned_data = aligned_data.dropna()

        if len(aligned_data) < 100:
            raise ValueError(f"Insufficient data after preprocessing: {len(aligned_data)} records")

        # Step 3: Split data temporally
        train_data, test_data = self.split_temporal_data(aligned_data)

        X_train = train_data[feature_names]
        y_train = train_data['target']
        X_test = test_data[feature_names]
        y_test = test_data['target']

        # Step 4: Train model
        model, label_mapping = self.train_model(X_train, y_train, model_type)

        # Step 5: Backtest strategy
        test_prices = df_labeled.loc[test_data.index, 'close']
        backtest_metrics = self.backtest_strategy(model, X_test, y_test, test_prices, label_mapping)

        # Step 6: Generate prediction
        latest_data_with_indicators = df_with_indicators.tail(50)  # Use recent data for indicators
        prediction_json = self.generate_prediction(symbol, model, feature_names,
                                                 latest_data_with_indicators, backtest_metrics, label_mapping)

        print(f"[COMPLETE] Analysis completed for {symbol}")
        return prediction_json


def main():
    """CLI interface for the Technical Trading Bot"""
    parser = argparse.ArgumentParser(description='Technical Trading Bot - ML-based trading signals')
    parser.add_argument('symbol', help='Stock symbol to analyze (e.g., AAPL)')
    parser.add_argument('--timeframe', choices=['day', 'hour', 'minute'], default='hour',
                       help='Data timeframe (default: hour)')
    parser.add_argument('--model', choices=['xgboost', 'random_forest'], default='xgboost',
                       help='ML model type (default: xgboost)')
    parser.add_argument('--periods', type=int, default=5,
                       help='Periods ahead for prediction (default: 5)')
    parser.add_argument('--threshold', type=float, default=1.0,
                       help='Price change threshold percentage (default: 1.0)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Maximum records to load (default: None = all data)')
    parser.add_argument('--output', '-o', help='Output file for JSON result')

    args = parser.parse_args()

    try:
        # Initialize bot
        bot = TechnicalTradingBot()

        # Run analysis
        result_json = bot.run_full_analysis(
            symbol=args.symbol.upper(),
            timeframe=args.timeframe,
            model_type=args.model,
            periods_ahead=args.periods,
            threshold_pct=args.threshold,
            limit=args.limit
        )

        # Output result
        if args.output:
            with open(args.output, 'w') as f:
                f.write(result_json)
            print(f"[OUTPUT] Results saved to {args.output}")
        else:
            print("\n" + "="*60)
            print("TRADING BOT PREDICTION")
            print("="*60)
            print(result_json)

    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())