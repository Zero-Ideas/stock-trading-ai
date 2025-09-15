#!/usr/bin/env python3
"""
Model Trainer - Comprehensive training system with segmented processing and model persistence
Trains models across all stocks and timeframes with RAM management
"""
import numpy as np
import pandas as pd
import json
import pickle
import joblib
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
import os
import gc
import argparse
from pathlib import Path
warnings.filterwarnings('ignore')

# Database and ML imports
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

# Technical analysis
import pandas_ta as ta

# ML libraries
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb

# Custom imports
from technical import TechnicalTradingBot


class ModelTrainer:
    """Advanced model trainer with segmented processing and persistence"""

    def __init__(self, model_dir: str = "./models", batch_size: int = 50000):
        """Initialize trainer with model storage directory and batch processing"""
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        self.batch_size = batch_size

        # Initialize technical bot for helper methods
        self.bot = TechnicalTradingBot()

        print(f"[TRAINER] Initialized with model directory: {self.model_dir}")
        print(f"[TRAINER] Batch processing size: {batch_size:,} records")

    def get_available_symbols(self, timeframe: str = 'hour', min_records: int = 5000) -> List[str]:
        """Get symbols with sufficient data for training"""
        print(f"[SYMBOLS] Finding symbols with >={min_records} records in {timeframe} timeframe")

        with self.bot.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT
                        symbol,
                        COUNT(*) FILTER (WHERE original = true) as original_records
                    FROM stock_data_{timeframe}
                    GROUP BY symbol
                    HAVING COUNT(*) FILTER (WHERE original = true) >= %s
                    ORDER BY original_records DESC
                """, (min_records,))

                symbols_data = cursor.fetchall()
                symbols = [row['symbol'] for row in symbols_data]

        if not symbols:
            print(f"[ERROR] No symbols found with >={min_records} records in {timeframe} timeframe")
            print(f"[DEBUG] Check if data exists and timeframe is correct")
            return []

        print(f"[SYMBOLS] Found {len(symbols)} symbols: {symbols[:10]}{'...' if len(symbols) > 10 else ''}")
        return symbols

    def load_symbol_data_batch(self, symbol: str, timeframe: str,
                              start_date: str = None, end_date: str = None,
                              limit: int = None, offset: int = 0) -> pd.DataFrame:
        """Load data for a symbol in batches to manage RAM"""

        with self.bot.get_connection() as conn:
            query = f"""
                SELECT symbol, price_timestamp, open, high, low, close, volume,
                       trade_count, vwap, original
                FROM stock_data_{timeframe}
                WHERE symbol = %s AND original = true
            """
            params = [symbol]

            if start_date:
                query += " AND price_timestamp >= %s"
                params.append(start_date)
            if end_date:
                query += " AND price_timestamp <= %s"
                params.append(end_date)

            query += " ORDER BY price_timestamp ASC"

            if limit:
                query += f" LIMIT {limit}"
            if offset > 0:
                query += f" OFFSET {offset}"

            with conn.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

                if not rows:
                    df = pd.DataFrame()
                else:
                    # Convert to DataFrame manually
                    columns = [desc[0] for desc in cursor.description]
                    data = []
                    for row in rows:
                        if hasattr(row, 'keys'):
                            row_dict = dict(row)
                        else:
                            row_dict = dict(zip(columns, row))
                        data.append(row_dict)

                    df = pd.DataFrame(data)

        if df.empty:
            return pd.DataFrame()

        # Process timestamps
        if 'price_timestamp' in df.columns:
            df['price_timestamp'] = pd.to_datetime(df['price_timestamp'], utc=True).dt.tz_localize(None)
            df.set_index('price_timestamp', inplace=True)

        # Convert numeric columns
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'trade_count', 'vwap']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def get_total_symbol_records(self, symbol: str, timeframe: str) -> int:
        """Get total number of records for a symbol"""
        with self.bot.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT COUNT(*) as total
                    FROM stock_data_{timeframe}
                    WHERE symbol = %s AND original = true
                """, (symbol,))
                result = cursor.fetchone()
                return result['total'] if result else 0

    def process_symbol_in_batches(self, symbol: str, timeframe: str,
                                 max_records: int = None,
                                 preserve_continuity: bool = True,
                                 periods_ahead: int = 5,
                                 threshold_pct: float = 1.0) -> Tuple[List[pd.DataFrame], List[pd.Series]]:
        """Process a single symbol in batches with memory management"""
        total_records = self.get_total_symbol_records(symbol, timeframe)

        print(f"[BATCH] {symbol} has {total_records:,} total records available")

        if max_records:
            original_total = total_records
            total_records = min(total_records, max_records)
            print(f"[BATCH] Limited to {total_records:,} records (was {original_total:,})")

        if total_records < 100:
            print(f"[WARNING] Skipping {symbol}: insufficient data ({total_records} records) - need at least 100")
            return [], []

        all_features = []
        all_targets = []
        processed_count = 0
        batch_num = 1
        overlap_size = 200 if preserve_continuity else 0  # Overlap for continuity

        while processed_count < total_records:
            # Calculate batch parameters
            current_offset = max(0, processed_count - overlap_size)
            remaining = total_records - current_offset
            current_limit = min(self.batch_size + overlap_size, remaining)

            print(f"[BATCH] {symbol} batch {batch_num}: loading {current_limit:,} records (offset: {current_offset:,})")

            try:
                # Load batch
                df = self.load_symbol_data_batch(symbol, timeframe,
                                                limit=current_limit, offset=current_offset)

                if len(df) < 50:
                    print(f"[BATCH] Batch {batch_num} too small: {len(df)} records")
                    break

                # Calculate technical indicators
                df_indicators = self.bot.calculate_technical_indicators(df)

                # Create prediction labels with configurable parameters
                # periods_ahead: Look N periods into future
                # threshold_pct: ±X% price change threshold for Buy/Sell vs Hold
                df_labeled = self.bot.create_prediction_labels(df_indicators,
                                                              periods_ahead=periods_ahead,
                                                              threshold_pct=threshold_pct)

                # Prepare features
                features_df, feature_names = self.bot.prepare_features(df_labeled)

                # Align with targets and clean
                aligned_data = features_df.join(df_labeled['target'], how='inner')
                aligned_data = aligned_data.dropna()

                if len(aligned_data) < 10:
                    print(f"[BATCH] Batch {batch_num} insufficient clean data: {len(aligned_data)} records")
                    processed_count += (self.batch_size - overlap_size)
                    batch_num += 1
                    continue

                # Add symbol as feature
                aligned_data['symbol_encoded'] = hash(symbol) % 1000

                # Handle overlapping data (skip if not first batch)
                if batch_num > 1 and overlap_size > 0:
                    # Skip overlapped records to avoid duplicates
                    skip_records = min(overlap_size, len(aligned_data))
                    aligned_data = aligned_data.iloc[skip_records:]

                if len(aligned_data) > 0:
                    # Separate features and targets
                    features = aligned_data.drop('target', axis=1)
                    targets = aligned_data['target']

                    all_features.append(features)
                    all_targets.append(targets)

                    print(f"[BATCH] {symbol} batch {batch_num}: {len(features):,} clean records added")

                # Memory cleanup
                del df, df_indicators, df_labeled, features_df, aligned_data
                if 'features' in locals():
                    del features, targets
                gc.collect()

                # Update progress
                processed_count += (self.batch_size - overlap_size)
                batch_num += 1

                # Break if we've processed enough records
                if max_records and sum(len(f) for f in all_features) >= max_records:
                    break

            except Exception as e:
                print(f"[ERROR] Batch {batch_num} failed for {symbol}: {e}")
                processed_count += (self.batch_size - overlap_size)
                batch_num += 1
                continue

        print(f"[BATCH] {symbol} completed: {len(all_features)} batches, {sum(len(f) for f in all_features):,} total records")
        return all_features, all_targets

    def prepare_training_data_batch(self, symbols: List[str], timeframe: str,
                                   max_records_per_symbol: int = None,
                                   total_row_limit: int = None,
                                   periods_ahead: int = 5,
                                   threshold_pct: float = 1.0) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare combined training data from multiple symbols with progressive batch loading"""
        print(f"[DATA] Preparing training data for {len(symbols)} symbols ({timeframe})")
        if max_records_per_symbol:
            print(f"[DATA] Max records per symbol: {max_records_per_symbol:,}")
        if total_row_limit:
            print(f"[DATA] Total row limit: {total_row_limit:,}")

        all_combined_features = []
        all_combined_targets = []
        total_records = 0
        symbols_processed = 0

        for i, symbol in enumerate(symbols):
            print(f"\n[DATA] Processing {symbol} ({i+1}/{len(symbols)})")

            try:
                # Process symbol in batches
                symbol_features, symbol_targets = self.process_symbol_in_batches(
                    symbol, timeframe, max_records_per_symbol, True, periods_ahead, threshold_pct
                )

                if not symbol_features:
                    continue

                # Combine symbol batches
                if symbol_features and symbol_targets:
                    combined_features = pd.concat(symbol_features, ignore_index=True)
                    combined_targets = pd.concat(symbol_targets, ignore_index=True)

                    # Apply total row limit if specified
                    if total_row_limit and total_records + len(combined_features) > total_row_limit:
                        remaining_rows = total_row_limit - total_records
                        if remaining_rows > 0:
                            combined_features = combined_features.iloc[:remaining_rows]
                            combined_targets = combined_targets.iloc[:remaining_rows]
                        else:
                            print(f"[DATA] Total row limit ({total_row_limit:,}) reached. Stopping.")
                            break

                    all_combined_features.append(combined_features)
                    all_combined_targets.append(combined_targets)
                    total_records += len(combined_features)
                    symbols_processed += 1

                    print(f"[DATA] {symbol}: {len(combined_features):,} records added (total: {total_records:,})")

                    # Memory cleanup
                    del symbol_features, symbol_targets, combined_features, combined_targets
                    gc.collect()

                    # Check if we've hit the total row limit
                    if total_row_limit and total_records >= total_row_limit:
                        print(f"[DATA] Total row limit ({total_row_limit:,}) reached. Processing complete.")
                        break

            except Exception as e:
                print(f"[ERROR] Failed to process {symbol}: {e}")
                continue

        if not all_combined_features:
            raise ValueError("No valid data found for training")

        # Final combination
        print(f"\n[DATA] Combining {total_records:,} records from {symbols_processed} symbols")
        final_features = pd.concat(all_combined_features, ignore_index=True)
        final_targets = pd.concat(all_combined_targets, ignore_index=True)

        # Final cleanup
        del all_combined_features, all_combined_targets
        gc.collect()

        print(f"[DATA] Final dataset: {len(final_features):,} samples with {len(final_features.columns)} features")
        return final_features, final_targets

    def backtest_strategy(self, model, X_test: pd.DataFrame, y_test: pd.Series,
                         test_prices: pd.Series, label_mapping: dict) -> Dict:
        """
        Backtest the trading strategy on test data with comprehensive risk metrics
        """
        print("[BACKTEST] Running strategy simulation with risk analysis")

        # Get predictions
        predictions_mapped = model.predict(X_test)
        predictions = pd.Series(predictions_mapped).map(label_mapping)

        # Initialize backtest variables
        portfolio_value = 10000  # Starting capital
        position = 0  # 0 = no position, 1 = long, -1 = short
        trades = []
        portfolio_values = [portfolio_value]
        transaction_cost = 0.001  # 0.1% transaction cost

        # Check prediction distribution
        pred_counts = predictions.value_counts()
        print(f"[BACKTEST] Prediction distribution:")
        for pred, count in pred_counts.items():
            label_name = {-1: 'Sell', 0: 'Hold', 1: 'Buy'}[pred]
            print(f"  {label_name}: {count} signals ({count/len(predictions)*100:.1f}%)")

        # Simulate trading
        for i in range(len(predictions)):
            pred = predictions.iloc[i]
            price = test_prices.iloc[i]

            # Trading logic
            if pred == 1 and position <= 0:  # Buy signal
                if position == -1:  # Close short position
                    portfolio_value = portfolio_value * (1 - transaction_cost)
                position = 1
                entry_price = price
                trades.append(('BUY', price, X_test.index[i]))

            elif pred == -1 and position >= 0:  # Sell signal
                if position == 1:  # Close long position
                    portfolio_value = portfolio_value * (price / entry_price) * (1 - transaction_cost)
                position = -1
                entry_price = price
                trades.append(('SELL', price, X_test.index[i]))

            # Calculate current portfolio value
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
        total_return_pct = (portfolio_values[-1] / 10000 - 1) * 100

        if len(returns) > 1:
            # Sharpe ratio
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

            # R-squared vs market
            market_returns = np.diff(test_prices) / test_prices[:-1]
            if len(market_returns) == len(returns):
                correlation = np.corrcoef(returns, market_returns)[0, 1]
                r_squared_vs_market = correlation ** 2 if not np.isnan(correlation) else 0
            else:
                r_squared_vs_market = 0
        else:
            sharpe_ratio = 0
            sortino_ratio = 0
            calmar_ratio = 0
            max_drawdown_pct = 0
            r_squared_vs_market = 0

        # Model accuracy - use mapped predictions vs mapped targets
        accuracy = accuracy_score(y_test, predictions_mapped)

        risk_metrics = {
            'total_return_pct': total_return_pct,
            'buy_hold_return_pct': buy_hold_return,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown_pct': max_drawdown_pct,
            'r_squared_vs_market': r_squared_vs_market,
            'strategy_accuracy': accuracy,
            'num_trades': len(trades),
            'final_portfolio_value': portfolio_values[-1]
        }

        print(f"[BACKTEST] Strategy return: {total_return_pct:.2f}% vs Buy & Hold: {buy_hold_return:.2f}%")
        print(f"[BACKTEST] Sharpe ratio: {sharpe_ratio:.3f}, Max drawdown: {max_drawdown_pct:.2f}%")
        print(f"[BACKTEST] Sortino ratio: {sortino_ratio:.3f}, Calmar ratio: {calmar_ratio:.3f}")
        print(f"[BACKTEST] Executed {len(trades)} trades, Final position: {position}")
        if len(trades) == 0:
            print(f"[BACKTEST WARNING] No trades executed - strategy is very conservative")
        elif len(trades) < 5:
            print(f"[BACKTEST WARNING] Very few trades ({len(trades)}) - consider lower prediction thresholds")

        return risk_metrics

    def train_timeframe_model(self, timeframe: str, model_type: str = 'xgboost',
                             max_symbols: int = None, max_records_per_symbol: int = None,
                             total_row_limit: int = None, periods_ahead: int = 5,
                             threshold_pct: float = 1.0, learning_rate: float = 0.1,
                             n_estimators: int = 100) -> Dict:
        """Train a comprehensive model for a specific timeframe

        Args:
            periods_ahead: Number of periods to look ahead for prediction labels (default: 5)
            threshold_pct: Price change threshold % for Buy/Sell classification (default: 1.0%)
                          Buy: future_return > +threshold_pct
                          Sell: future_return < -threshold_pct
                          Hold: -threshold_pct <= future_return <= +threshold_pct
            learning_rate: Learning rate for XGBoost model (default: 0.1)
            n_estimators: Number of estimators/epochs for model training (default: 100)
        """
        print(f"\n{'='*60}")
        print(f"TRAINING {timeframe.upper()} MODEL ({model_type})")
        print(f"{'='*60}")

        # Get available symbols
        symbols = self.get_available_symbols(timeframe, min_records=500)
        if max_symbols:
            symbols = symbols[:max_symbols]

        print(f"[TRAINING] Using {len(symbols)} symbols for training")
        if max_records_per_symbol:
            print(f"[TRAINING] Max records per symbol: {max_records_per_symbol:,}")
        if total_row_limit:
            print(f"[TRAINING] Total row limit: {total_row_limit:,}")

        # Prepare training data
        X, y = self.prepare_training_data_batch(symbols, timeframe, max_records_per_symbol,
                                               total_row_limit, periods_ahead, threshold_pct)

        print(f"[TRAINING] Total training samples: {len(X)}")
        print(f"[TRAINING] Features: {len(X.columns)}")

        # Label distribution
        label_counts = y.value_counts().sort_index()
        print(f"[TRAINING] Label distribution:")
        for label, count in label_counts.items():
            label_name = {-1: 'Sell', 0: 'Hold', 1: 'Buy'}[label]
            pct = count / len(y) * 100
            print(f"  {label_name}: {count} ({pct:.1f}%)")

        # Create temporal split (80% training, 20% validation)
        split_idx = int(len(X) * 0.8)
        X_train = X.iloc[:split_idx]
        y_train = y.iloc[:split_idx]
        X_val = X.iloc[split_idx:]
        y_val = y.iloc[split_idx:]

        print(f"[TRAINING] Training samples: {len(X_train)}")
        print(f"[TRAINING] Validation samples: {len(X_val)}")

        # Create label mapping for consistent encoding
        unique_labels = sorted(y_train.unique())
        label_mapping = {label: i for i, label in enumerate(unique_labels)}
        reverse_mapping = {i: label for label, i in label_mapping.items()}

        y_train_mapped = y_train.map(label_mapping)
        y_val_mapped = y_val.map(label_mapping)

        # Calculate class weights to handle imbalance
        from sklearn.utils.class_weight import compute_class_weight
        import numpy as np

        # Get actual classes present in mapped data
        mapped_classes = np.array(sorted(y_train_mapped.unique()))
        class_weights = compute_class_weight(
            'balanced',
            classes=mapped_classes,
            y=y_train_mapped
        )

        # Create class weight dictionary
        class_weight_dict = dict(zip(mapped_classes, class_weights))
        sample_weights = np.array([class_weight_dict[label] for label in y_train_mapped])

        print(f"[TRAINING] Class weights: {class_weight_dict}")

        # Train model
        final_epoch_model = None  # Initialize for scope
        if model_type == 'xgboost':
            model = xgb.XGBClassifier(
                objective='multi:softmax',           # multi-class classification
                num_class=len(unique_labels),
                max_depth=6,                          # controls tree complexity
                learning_rate=learning_rate,                   # lower LR for stable convergence
                n_estimators=n_estimators,                     # more trees with low learning rate
                random_state=42,
                eval_metric='mlogloss',
                n_jobs=-1,                            # use all CPU cores
                subsample=0.8,                        # row sampling to reduce overfitting
                colsample_bytree=0.8,                 # feature sampling per tree
                gamma=0.1,                            # minimum loss reduction to make a split
                reg_alpha=0.5,                        # L1 regularization (sparse features / noise)
                reg_lambda=1.0,                        # L2 regularization
                scale_pos_weight=1,                    # optional: adjust if class imbalance exists
                use_label_encoder=False,               # suppress deprecation warning
                tree_method='hist'                     # faster histogram-based algorithm
            )
                        # Train with sample weights to handle class imbalance
            print(f"[TRAINING] Training with sample weights to balance classes...")
            model.fit(X_train, y_train_mapped, sample_weight=sample_weights)

            # Create a separate model for final epoch evaluation
            print(f"[TRAINING] Creating final-epoch-only model for comparison...")
            final_epoch_model = xgb.XGBClassifier(
                objective='multi:softmax',
                num_class=len(unique_labels),
                max_depth=6,
                learning_rate=learning_rate,
                n_estimators=1,  # Only one tree (final epoch equivalent)
                random_state=42,
                eval_metric='mlogloss',
                n_jobs=-1
            )
            final_epoch_model.fit(X_train, y_train_mapped, sample_weight=sample_weights)
        elif model_type == 'random_forest':
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

        print(f"[TRAINING] Training {model_type} model with class balancing...")
        if model_type != 'xgboost':  # XGBoost already fitted above
            model.fit(X_train, y_train_mapped)

        # Validation
        val_predictions = model.predict(X_val)
        val_accuracy = accuracy_score(y_val_mapped, val_predictions)
        print(f"[TRAINING] Validation accuracy: {val_accuracy:.4f}")

        # Run backtest analysis on validation data
        backtest_metrics = {}
        try:
            # Get price data for the validation period (use first symbol as representative)
            representative_symbol = symbols[0]
            print(f"[BACKTEST] Getting price data for representative symbol: {representative_symbol}")

            full_df = self.load_symbol_data_batch(representative_symbol, timeframe)
            print(f"[BACKTEST] Loaded {len(full_df)} price records for {representative_symbol}")

            if len(full_df) > 100:
                # Use temporal split to match training data
                split_idx = int(len(full_df) * 0.8)
                val_df = full_df.iloc[split_idx:]

                print(f"[BACKTEST] Validation period: {len(val_df)} price records")
                print(f"[BACKTEST] X_val samples: {len(X_val)}")

                # Take the minimum length to avoid index errors
                min_length = min(len(val_df), len(X_val))

                if min_length >= 50:  # Minimum required for meaningful backtest
                    val_prices = val_df['close'].iloc[:min_length]
                    X_val_subset = X_val.iloc[:min_length]
                    y_val_subset = y_val_mapped.iloc[:min_length]

                    print(f"[BACKTEST] Running backtest with {min_length} samples")

                    # Run backtest with full model (all epochs)
                    backtest_metrics = self.backtest_strategy(
                        model, X_val_subset, y_val_subset, val_prices, reverse_mapping
                    )
                    print(f"[BACKTEST] Full model (all epochs) risk-adjusted metrics calculated successfully")

                    # Run separate backtest with final epoch model if using XGBoost
                    if model_type == 'xgboost' and final_epoch_model is not None:
                        print(f"[BACKTEST] Running separate backtest for final-epoch-only model...")
                        final_epoch_metrics = self.backtest_strategy(
                            final_epoch_model, X_val_subset, y_val_subset, val_prices, reverse_mapping
                        )
                        print(f"[BACKTEST] Final-epoch-only model risk-adjusted metrics calculated successfully")

                        # Print comparison summary
                        print(f"\n[COMPARISON] Portfolio Performance Summary:")
                        print(f"  Full Model ({n_estimators} epochs): ${backtest_metrics.get('final_portfolio_value', 0):,.0f}")
                        print(f"  Final Epoch Only (1 epoch): ${final_epoch_metrics.get('final_portfolio_value', 0):,.0f}")
                        print(f"  Difference: ${(final_epoch_metrics.get('final_portfolio_value', 0) - backtest_metrics.get('final_portfolio_value', 0)):,.0f}")

                        # Add final epoch metrics to the result
                        backtest_metrics['final_epoch_metrics'] = final_epoch_metrics
                else:
                    print(f"[BACKTEST] Insufficient data for backtest: {min_length} samples")
            else:
                print(f"[BACKTEST] Insufficient price data: {len(full_df)} records")

        except Exception as e:
            print(f"[WARNING] Backtest analysis failed: {e}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            backtest_metrics = {}

        # Feature importance
        if hasattr(model, 'feature_importances_'):
            feature_importance = dict(zip(X.columns, model.feature_importances_))
            top_features = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10])
            print(f"[TRAINING] Top features: {list(top_features.keys())[:5]}")

        # Model metadata with risk metrics
        model_info = {
            'timeframe': timeframe,
            'model_type': model_type,
            'training_samples': len(X_train),
            'validation_samples': len(X_val),
            'validation_accuracy': val_accuracy,
            'symbols_used': symbols,
            'feature_names': list(X.columns),
            'label_mapping': label_mapping,
            'reverse_mapping': reverse_mapping,
            'created_at': datetime.now().isoformat(),
            'feature_importance': dict(zip(X.columns, model.feature_importances_)) if hasattr(model, 'feature_importances_') else None,
            'risk_metrics': backtest_metrics or {}
        }

        return {
            'model': model,
            'model_info': model_info,
            'X_columns': list(X.columns)
        }

    def save_model(self, model_data: Dict, timeframe: str, model_type: str):
        """Save trained model and metadata"""
        model_filename = f"trading_model_{timeframe}_{model_type}.pkl"
        info_filename = f"trading_model_{timeframe}_{model_type}_info.json"

        model_path = self.model_dir / model_filename
        info_path = self.model_dir / info_filename

        # Save model
        joblib.dump({
            'model': model_data['model'],
            'feature_names': model_data['X_columns'],
            'label_mapping': model_data['model_info']['label_mapping'],
            'reverse_mapping': model_data['model_info']['reverse_mapping']
        }, model_path)

        # Convert numpy types for JSON serialization
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

        # Save metadata
        with open(info_path, 'w') as f:
            json.dump(convert_types(model_data['model_info']), f, indent=2)

        print(f"[SAVE] Model saved: {model_path}")
        print(f"[SAVE] Info saved: {info_path}")

    def train_all_timeframes(self, model_type: str = 'xgboost', max_symbols: int = 20,
                           max_records_per_symbol: int = None, total_row_limit: int = None,
                           periods_ahead: int = 5, threshold_pct: float = 1.0,
                           learning_rate: float = 0.1, n_estimators: int = 100):
        """Train models for all timeframes"""
        timeframes = ['day', 'hour', 'minute']
        results = {}

        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE MODEL TRAINING - {model_type.upper()}")
        print(f"{'='*80}")

        for timeframe in timeframes:
            try:
                print(f"\n[START] Training {timeframe} model...")

                model_data = self.train_timeframe_model(
                    timeframe=timeframe,
                    model_type=model_type,
                    max_symbols=max_symbols,
                    max_records_per_symbol=max_records_per_symbol,
                    total_row_limit=total_row_limit,
                    periods_ahead=periods_ahead,
                    threshold_pct=threshold_pct,
                    learning_rate=learning_rate,
                    n_estimators=n_estimators
                )

                self.save_model(model_data, timeframe, model_type)

                results[timeframe] = {
                    'success': True,
                    'validation_accuracy': model_data['model_info']['validation_accuracy'],
                    'training_samples': model_data['model_info']['training_samples'],
                    'symbols_count': len(model_data['model_info']['symbols_used'])
                }

                print(f"[SUCCESS] {timeframe} model completed!")

                # Clean up memory
                del model_data
                gc.collect()

            except Exception as e:
                print(f"[ERROR] {timeframe} model failed: {e}")
                results[timeframe] = {'success': False, 'error': str(e)}

        # Summary
        print(f"\n{'='*60}")
        print("TRAINING SUMMARY")
        print(f"{'='*60}")
        for timeframe, result in results.items():
            if result['success']:
                print(f"{timeframe.upper():>8}: [OK] Accuracy: {result['validation_accuracy']:.4f} "
                      f"({result['training_samples']:,} samples, {result['symbols_count']} symbols)")
            else:
                print(f"{timeframe.upper():>8}: [ERROR] Failed: {result['error']}")

        return results

    def list_available_models(self) -> Dict:
        """List all available trained models"""
        models = {}

        for model_file in self.model_dir.glob("trading_model_*.pkl"):
            parts = model_file.stem.split('_')
            if len(parts) >= 4:
                timeframe = parts[2]
                model_type = parts[3]

                # Load model info
                info_file = self.model_dir / f"{model_file.stem}_info.json"
                if info_file.exists():
                    with open(info_file, 'r') as f:
                        info = json.load(f)

                    models[f"{timeframe}_{model_type}"] = {
                        'timeframe': timeframe,
                        'model_type': model_type,
                        'model_file': str(model_file),
                        'info_file': str(info_file),
                        'created_at': info.get('created_at'),
                        'validation_accuracy': info.get('validation_accuracy'),
                        'training_samples': info.get('training_samples'),
                        'symbols_count': len(info.get('symbols_used', []))
                    }

        return models


def main():
    parser = argparse.ArgumentParser(description='Train comprehensive trading models with memory-efficient batch processing')
    parser.add_argument('--timeframe', choices=['day', 'hour', 'minute', 'all'], default='all',
                       help='Timeframe to train (default: all)')
    parser.add_argument('--model', choices=['xgboost', 'random_forest'], default='xgboost',
                       help='Model type (default: xgboost)')
    parser.add_argument('--symbols', type=int, default=20,
                       help='Maximum symbols to use (default: 20)')
    parser.add_argument('--max-records-per-symbol', type=str, default=None,
                       help='Maximum records per symbol (default: unlimited, use "all" for unlimited)')
    parser.add_argument('--total-row-limit', type=str, default=None,
                       help='Total row limit across all symbols (default: unlimited, use "all" for unlimited)')
    parser.add_argument('--batch-size', type=int, default=50000,
                       help='Internal batch size for memory management (default: 50000)')
    parser.add_argument('--periods-ahead', type=int, default=5,
                       help='Number of periods to look ahead for predictions (default: 5)')
    parser.add_argument('--threshold', type=float, default=1.0,
                       help='Price change threshold percentage for Buy/Sell vs Hold (default: 1.0 percent)')
    parser.add_argument('--learning-rate', type=float, default=0.1,
                       help='Learning rate for XGBoost model (default: 0.1)')
    parser.add_argument('--epochs', '--n-estimators', type=int, default=100, dest='n_estimators',
                       help='Number of epochs/estimators for model training (default: 100)')
    parser.add_argument('--list', action='store_true', help='List available models')
    parser.add_argument('--model-dir', default='./models', help='Model storage directory')

    args = parser.parse_args()

    # Parse data limit arguments
    def parse_data_limit(value):
        if value is None or value == 'all':
            return None
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Invalid data limit: {value}. Use integer or 'all'")

    max_records_per_symbol = parse_data_limit(args.max_records_per_symbol)
    total_row_limit = parse_data_limit(args.total_row_limit)

    print(f"[CONFIG] Batch size (memory): {args.batch_size:,}")
    print(f"[CONFIG] Max records per symbol: {'unlimited' if max_records_per_symbol is None else f'{max_records_per_symbol:,}'}")
    print(f"[CONFIG] Total row limit: {'unlimited' if total_row_limit is None else f'{total_row_limit:,}'}")
    print(f"[CONFIG] Learning rate: {args.learning_rate}")
    print(f"[CONFIG] Epochs/Estimators: {args.n_estimators}")

    try:
        trainer = ModelTrainer(model_dir=args.model_dir, batch_size=args.batch_size)

        if args.list:
            models = trainer.list_available_models()
            print(f"\nAVAILABLE MODELS ({len(models)} found):")
            print("-" * 80)
            for name, info in models.items():
                print(f"{name:>15}: {info['validation_accuracy']:.4f} accuracy, "
                      f"{info['training_samples']:,} samples, {info['symbols_count']} symbols")
                print(f"{'':>17} Created: {info['created_at']}")
            return

        if args.timeframe == 'all':
            results = trainer.train_all_timeframes(
                model_type=args.model,
                max_symbols=args.symbols,
                max_records_per_symbol=max_records_per_symbol,
                total_row_limit=total_row_limit,
                periods_ahead=args.periods_ahead,
                threshold_pct=args.threshold,
                learning_rate=args.learning_rate,
                n_estimators=args.n_estimators
            )
        else:
            model_data = trainer.train_timeframe_model(
                timeframe=args.timeframe,
                model_type=args.model,
                max_symbols=args.symbols,
                max_records_per_symbol=max_records_per_symbol,
                total_row_limit=total_row_limit,
                periods_ahead=args.periods_ahead,
                threshold_pct=args.threshold,
                learning_rate=args.learning_rate,
                n_estimators=args.n_estimators
            )
            trainer.save_model(model_data, args.timeframe, args.model)
            print(f"\n[SUCCESS] {args.timeframe} model training completed!")

    except Exception as e:
        print(f"[ERROR] Training failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())