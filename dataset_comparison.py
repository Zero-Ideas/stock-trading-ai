#!/usr/bin/env python3
"""
Dataset Comparison - Compare training results with different data volumes
"""

from technical import TechnicalTradingBot
import json
import time

def compare_data_sizes(symbol='AAPL', timeframe='hour'):
    """Compare training with different dataset sizes"""

    print(f"=== Dataset Size Comparison for {symbol} ===\n")

    bot = TechnicalTradingBot()
    results = {}

    # Test different data sizes
    test_sizes = [
        (1000, "1K Recent"),
        (5000, "5K Recent"),
        (10000, "10K Recent"),
        (None, "FULL Dataset")
    ]

    for limit, label in test_sizes:
        print(f"Testing {label}...")
        start_time = time.time()

        try:
            result_json = bot.run_full_analysis(
                symbol=symbol,
                timeframe=timeframe,
                model_type='xgboost',
                periods_ahead=5,
                threshold_pct=1.0,
                limit=limit
            )

            result = json.loads(result_json)
            duration = time.time() - start_time

            results[label] = {
                'duration': duration,
                'prediction': result['prediction'],
                'confidence': result['confidence_score'],
                'strategy_return': result['analysis']['performance']['backtest_total_return_pct'],
                'buy_hold_return': result['analysis']['performance']['buy_hold_return_pct'],
                'accuracy': result['analysis']['performance']['model_accuracy'],
                'sharpe_ratio': result['analysis']['risk_return']['sharpe_ratio'],
                'max_drawdown': result['analysis']['risk_return']['max_drawdown_pct'],
                'current_rsi': result['analysis']['indicators']['values']['rsi'],
                'current_price': result['analysis']['indicators']['values']['close']
            }

            print(f"✓ {label} completed in {duration:.1f}s")

        except Exception as e:
            print(f"✗ {label} failed: {e}")
            results[label] = None

        print()

    # Summary table
    print("="*90)
    print(f"DATASET SIZE COMPARISON SUMMARY FOR {symbol}")
    print("="*90)
    print(f"{'Size':<12} {'Duration':<10} {'Strategy %':<12} {'Buy&Hold %':<12} {'Accuracy':<10} {'Prediction':<10}")
    print("-"*90)

    for size_label, result in results.items():
        if result:
            print(f"{size_label:<12} {result['duration']:>7.1f}s {result['strategy_return']:>9.2f}% "
                  f"{result['buy_hold_return']:>9.2f}% {result['accuracy']:>7.3f}  {result['prediction']:<10}")
        else:
            print(f"{size_label:<12} FAILED")

    print("\nKEY INSIGHTS:")

    if results.get("FULL Dataset") and results.get("5K Recent"):
        full_result = results["FULL Dataset"]
        small_result = results["5K Recent"]

        strategy_diff = full_result['strategy_return'] - small_result['strategy_return']
        accuracy_diff = full_result['accuracy'] - small_result['accuracy']

        print(f"• Full dataset vs 5K recent:")
        print(f"  - Strategy return difference: {strategy_diff:+.2f}%")
        print(f"  - Accuracy difference: {accuracy_diff:+.3f}")
        print(f"  - Training time: {full_result['duration']:.1f}s vs {small_result['duration']:.1f}s")

    # Find best performing size
    best_strategy = max(results.items(), key=lambda x: x[1]['strategy_return'] if x[1] else -999)
    print(f"• Best strategy return: {best_strategy[0]} ({best_strategy[1]['strategy_return']:.2f}%)")

    return results

def multi_symbol_full_comparison(symbols=['AAPL', 'NVDA', 'TSLA']):
    """Compare full dataset training across multiple symbols"""

    print("="*80)
    print("MULTI-SYMBOL FULL DATASET COMPARISON")
    print("="*80)

    bot = TechnicalTradingBot()
    results = {}

    for symbol in symbols:
        print(f"\nTraining {symbol} with FULL dataset...")
        start_time = time.time()

        try:
            result_json = bot.run_full_analysis(
                symbol=symbol,
                timeframe='hour',
                model_type='xgboost',
                periods_ahead=5,
                threshold_pct=1.0,
                limit=None  # Full dataset
            )

            result = json.loads(result_json)
            duration = time.time() - start_time

            results[symbol] = {
                'duration': duration,
                'prediction': result['prediction'],
                'confidence': result['confidence_score'],
                'strategy_return': result['analysis']['performance']['backtest_total_return_pct'],
                'buy_hold_return': result['analysis']['performance']['buy_hold_return_pct'],
                'accuracy': result['analysis']['performance']['model_accuracy'],
                'sharpe_ratio': result['analysis']['risk_return']['sharpe_ratio'],
                'current_price': result['analysis']['indicators']['values']['close']
            }

            perf = result['analysis']['performance']
            print(f"✓ {symbol}: {perf['backtest_total_return_pct']:.2f}% vs {perf['buy_hold_return_pct']:.2f}% B&H")

        except Exception as e:
            print(f"✗ {symbol} failed: {e}")
            results[symbol] = None

    # Summary table
    print("\n" + "="*85)
    print("FULL DATASET MULTI-SYMBOL RESULTS")
    print("="*85)
    print(f"{'Symbol':<8} {'Strategy %':<12} {'Buy&Hold %':<12} {'Accuracy':<10} {'Prediction':<12} {'Price':<10}")
    print("-"*85)

    for symbol, result in results.items():
        if result:
            print(f"{symbol:<8} {result['strategy_return']:>9.2f}% {result['buy_hold_return']:>9.2f}% "
                  f"{result['accuracy']:>7.3f}  {result['prediction']:<12} ${result['current_price']:>7.2f}")
        else:
            print(f"{symbol:<8} FAILED")

    # Analysis
    successful_results = {k: v for k, v in results.items() if v}
    if successful_results:
        avg_strategy = sum(r['strategy_return'] for r in successful_results.values()) / len(successful_results)
        avg_buyhold = sum(r['buy_hold_return'] for r in successful_results.values()) / len(successful_results)
        avg_accuracy = sum(r['accuracy'] for r in successful_results.values()) / len(successful_results)

        print(f"\nSUMMARY:")
        print(f"• Average strategy return: {avg_strategy:.2f}%")
        print(f"• Average buy & hold return: {avg_buyhold:.2f}%")
        print(f"• Average model accuracy: {avg_accuracy:.3f}")
        print(f"• Strategy outperformance: {avg_strategy - avg_buyhold:+.2f}%")

    return results

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Compare training with different dataset sizes')
    parser.add_argument('--symbol', default='AAPL', help='Symbol for size comparison')
    parser.add_argument('--multi', action='store_true', help='Multi-symbol full dataset comparison')
    parser.add_argument('--symbols', nargs='+', default=['AAPL', 'NVDA', 'TSLA'],
                       help='Symbols for multi-symbol comparison')

    args = parser.parse_args()

    if args.multi:
        multi_symbol_full_comparison(args.symbols)
    else:
        compare_data_sizes(args.symbol)