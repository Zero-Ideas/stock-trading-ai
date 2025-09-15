#!/usr/bin/env python3
"""
Training Verifier - Verify and visualize the ML training process
"""

import pandas as pd
import numpy as np
from technical import TechnicalTradingBot
import matplotlib.pyplot as plt
import argparse

def verify_training_process(symbol='AAPL', timeframe='hour'):
    """
    Step-by-step verification of the training process
    """
    print(f"=== Training Verification for {symbol} ===\n")

    # Initialize bot
    bot = TechnicalTradingBot()

    # Step 1: Data Loading
    print("1. DATA LOADING")
    df = bot.load_stock_data(symbol, timeframe, limit=1000)
    print(f"   [OK] Loaded {len(df)} records")
    print(f"   [OK] Date range: {df.index.min()} to {df.index.max()}")
    print(f"   [OK] Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"   [OK] Latest close: ${df['close'].iloc[-1]:.2f}")
    print()

    # Step 2: Technical Indicators
    print("2. TECHNICAL INDICATORS")
    df_indicators = bot.calculate_technical_indicators(df)
    new_cols = len(df_indicators.columns) - len(df.columns)
    print(f"   [OK] Added {new_cols} technical indicators")

    # Show some key indicators
    latest = df_indicators.iloc[-1]
    print("   Latest indicator values:")
    for indicator in ['rsi', 'sma_20', 'ema_20', 'atr']:
        if indicator in latest:
            print(f"     {indicator.upper()}: {latest[indicator]:.2f}")
    print()

    # Step 3: Label Creation
    print("3. PREDICTION LABELS")
    df_labeled = bot.create_prediction_labels(df_indicators, periods_ahead=5, threshold_pct=1.0)
    print(f"   [OK] Created labels for {len(df_labeled)} records")

    # Label distribution
    label_counts = df_labeled['target'].value_counts().sort_index()
    for label, count in label_counts.items():
        label_name = {-1: 'Sell', 0: 'Hold', 1: 'Buy'}[label]
        pct = count / len(df_labeled) * 100
        print(f"     {label_name}: {count} ({pct:.1f}%)")
    print()

    # Step 4: Feature Preparation
    print("4. FEATURE PREPARATION")
    features_df, feature_names = bot.prepare_features(df_labeled)
    print(f"   [OK] Prepared {len(feature_names)} features")
    print(f"   [OK] {len(features_df)} clean records after removing NaNs")

    # Align with targets
    aligned_data = features_df.join(df_labeled['target'], how='inner')
    aligned_data = aligned_data.dropna()
    print(f"   [OK] {len(aligned_data)} records with valid targets")
    print()

    # Step 5: Train/Test Split
    print("5. TRAIN/TEST SPLIT")
    train_data, test_data = bot.split_temporal_data(aligned_data)
    print(f"   [OK] Training: {len(train_data)} records")
    print(f"   [OK] Testing: {len(test_data)} records")
    print(f"   [OK] Train period: {train_data.index.min()} to {train_data.index.max()}")
    print(f"   [OK] Test period: {test_data.index.min()} to {test_data.index.max()}")
    print()

    # Step 6: Model Training
    print("6. MODEL TRAINING")
    X_train = train_data[feature_names]
    y_train = train_data['target']
    X_test = test_data[feature_names]
    y_test = test_data['target']

    model, label_mapping = bot.train_model(X_train, y_train, 'xgboost')
    print(f"   [OK] Trained XGBoost model on {len(X_train)} samples")
    print(f"   [OK] Label mapping: {label_mapping}")
    print()

    # Step 7: Backtesting
    print("7. BACKTESTING")
    test_prices = df_labeled.loc[test_data.index, 'close']
    backtest_metrics = bot.backtest_strategy(model, X_test, y_test, test_prices, label_mapping)

    print("   Performance Summary:")
    print(f"     Strategy Return: {backtest_metrics['total_return_pct']:.2f}%")
    print(f"     Buy & Hold Return: {backtest_metrics['buy_hold_return_pct']:.2f}%")
    print(f"     Sharpe Ratio: {backtest_metrics['sharpe_ratio']:.3f}")
    print(f"     Max Drawdown: {backtest_metrics['max_drawdown_pct']:.2f}%")
    print(f"     Model Accuracy: {backtest_metrics['accuracy']:.3f}")
    print(f"     Number of Trades: {backtest_metrics['num_trades']}")
    print()

    # Step 8: Current Prediction
    print("8. CURRENT PREDICTION")
    latest_data = df_indicators.tail(50)
    prediction_json = bot.generate_prediction(symbol, model, feature_names,
                                            latest_data, backtest_metrics, label_mapping)

    import json
    prediction = json.loads(prediction_json)
    print(f"   [OK] Prediction: {prediction['prediction']}")
    print(f"   [OK] Confidence: {prediction['confidence_score']:.1%}")
    print(f"   [OK] Current RSI: {prediction['analysis']['indicators']['values']['rsi']:.1f}")
    print(f"   [OK] Current Price: ${prediction['analysis']['indicators']['values']['close']:.2f}")

    print(f"\n=== Training Verification Complete ===")

    return {
        'data_records': len(df),
        'training_records': len(X_train),
        'testing_records': len(X_test),
        'model_accuracy': backtest_metrics['accuracy'],
        'strategy_return': backtest_metrics['total_return_pct'],
        'current_prediction': prediction['prediction']
    }

def compare_symbols(symbols=['AAPL', 'NVDA', 'TSLA'], timeframe='hour'):
    """Compare training results across multiple symbols"""

    print("=== Multi-Symbol Training Comparison ===\n")

    results = {}
    for symbol in symbols:
        print(f"Training {symbol}...")
        try:
            result = verify_training_process(symbol, timeframe)
            results[symbol] = result
            print(f"[OK] {symbol} completed\n")
        except Exception as e:
            print(f"[ERROR] {symbol} failed: {e}\n")
            results[symbol] = None

    # Summary table
    print("TRAINING RESULTS SUMMARY:")
    print(f"{'Symbol':<8} {'Records':<8} {'Accuracy':<10} {'Strategy %':<12} {'Prediction':<10}")
    print("-" * 60)

    for symbol, result in results.items():
        if result:
            print(f"{symbol:<8} {result['training_records']:<8} {result['model_accuracy']:.3f} "
                  f"{result['strategy_return']:>8.2f}% {result['current_prediction']:<10}")
        else:
            print(f"{symbol:<8} FAILED")

def main():
    parser = argparse.ArgumentParser(description='Verify ML trading model training')
    parser.add_argument('--symbol', default='AAPL', help='Symbol to verify (default: AAPL)')
    parser.add_argument('--compare', nargs='+', help='Compare multiple symbols')
    parser.add_argument('--timeframe', choices=['day', 'hour', 'minute'], default='hour')

    args = parser.parse_args()

    if args.compare:
        compare_symbols(args.compare, args.timeframe)
    else:
        verify_training_process(args.symbol, args.timeframe)

if __name__ == '__main__':
    main()