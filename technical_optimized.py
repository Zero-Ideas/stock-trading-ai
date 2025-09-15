#!/usr/bin/env python3
"""
Optimized Technical Trading Bot - Uses pre-trained models for fast predictions
"""

import numpy as np
import pandas as pd
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

from model_predictor import ModelPredictor
from technical import TechnicalTradingBot


class OptimizedTradingBot:
    """Optimized trading bot using pre-trained models"""

    def __init__(self, model_dir: str = "./models"):
        """Initialize optimized bot with model directory"""
        self.predictor = ModelPredictor(model_dir)
        self.fallback_bot = TechnicalTradingBot()  # Fallback for missing models

        print(f"[OPTIMIZED BOT] Initialized with model directory: {model_dir}")

    def get_available_symbols(self, timeframe: str = 'hour', min_records: int = 5000) -> List[str]:
        """Get symbols with sufficient data for analysis"""
        with self.fallback_bot.get_connection() as conn:
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

        print(f"[SYMBOLS] Found {len(symbols)} symbols with >={min_records} records in {timeframe} timeframe")
        return symbols

    def get_enhanced_prediction(self, symbol: str, timeframe: str = 'hour',
                               model_type: str = 'xgboost',
                               include_analysis: bool = True, data_limit: int = None) -> str:
        """Get enhanced prediction with comprehensive analysis"""

        try:
            # Try to use pre-trained model first
            prediction_result = self.predictor.make_prediction(symbol, timeframe, model_type, data_limit)

            if not include_analysis:
                return json.dumps(prediction_result, indent=2)

            # Add comprehensive analysis
            enhanced_result = self._add_market_analysis(prediction_result, symbol, timeframe, data_limit)

            return json.dumps(enhanced_result, indent=2)

        except FileNotFoundError as e:
            print(f"[WARNING] Pre-trained model not found: {e}")
            print(f"[FALLBACK] Using on-demand training for {symbol}")

            # Fallback to original training method
            return self.fallback_bot.run_full_analysis(
                symbol=symbol,
                timeframe=timeframe,
                model_type=model_type,
                periods_ahead=5,
                threshold_pct=1.0,
                limit=10000  # Limit for faster training
            )

        except Exception as e:
            print(f"[ERROR] Prediction failed: {e}")
            raise

    def _add_market_analysis(self, prediction_result: Dict, symbol: str, timeframe: str, data_limit: int = None) -> Dict:
        """Add comprehensive market analysis to prediction"""

        # Get recent market data for analysis
        try:
            # Use the same data limit as the prediction, or default to 100 if None
            limit = data_limit if data_limit is not None else 100
            recent_df = self.fallback_bot.load_stock_data(symbol, timeframe, limit=limit)
            df_with_indicators = self.fallback_bot.calculate_technical_indicators(recent_df)

            # Get latest values
            latest = df_with_indicators.iloc[-1]

            # Calculate some basic analysis metrics
            price_trend = "Uptrend" if latest['close'] > latest['sma_20'] else "Downtrend"

            rsi_condition = "Oversold" if latest.get('rsi', 50) < 30 else "Overbought" if latest.get('rsi', 50) > 70 else "Neutral"

            volume_trend = "High" if latest['volume'] > latest.get('volume_sma', latest['volume']) * 1.5 else "Normal"

            # Market context
            market_analysis = {
                "current_price": float(latest['close']),
                "price_trend": price_trend,
                "rsi_condition": rsi_condition,
                "rsi_value": float(latest.get('rsi', 0)),
                "volume_trend": volume_trend,
                "sma_20": float(latest.get('sma_20', 0)),
                "ema_20": float(latest.get('ema_20', 0)),
                "atr": float(latest.get('atr', 0)),
                "data_range": {
                    "start_date": df_with_indicators.index[0].isoformat(),
                    "end_date": df_with_indicators.index[-1].isoformat(),
                    "total_periods": len(df_with_indicators)
                }
            }

            # Add risk analysis if available in model info
            risk_analysis = {}
            model_info = prediction_result.get('model_info', {})
            risk_metrics = model_info.get('risk_metrics', {})

            if risk_metrics:
                risk_analysis = {
                    "sharpe_ratio": risk_metrics.get('sharpe_ratio', 0),
                    "sortino_ratio": risk_metrics.get('sortino_ratio', 0),
                    "calmar_ratio": risk_metrics.get('calmar_ratio', 0),
                    "max_drawdown_pct": risk_metrics.get('max_drawdown_pct', 0),
                    "strategy_return_pct": risk_metrics.get('total_return_pct', 0),
                    "buy_hold_return_pct": risk_metrics.get('buy_hold_return_pct', 0),
                    "r_squared_vs_market": risk_metrics.get('r_squared_vs_market', 0)
                }

            # Enhanced result with risk analysis
            enhanced_result = {
                "prediction_summary": {
                    "symbol": prediction_result['symbol'],
                    "prediction": prediction_result['prediction'],
                    "confidence": prediction_result['confidence_score'],
                    "timeframe": prediction_result['timeframe']
                },
                "market_analysis": market_analysis,
                "risk_analysis": risk_analysis,
                "model_performance": prediction_result['model_info'],
                "technical_factors": prediction_result.get('feature_explanation', {}),
                "probability_breakdown": prediction_result.get('probability_distribution', {}),
                "timestamp": prediction_result['timestamp'],
                "source": "pre_trained_model"
            }

            return enhanced_result

        except Exception as e:
            print(f"[WARNING] Could not add market analysis: {e}")
            return prediction_result

    def compare_timeframes(self, symbol: str, model_type: str = 'xgboost', data_limit: int = None) -> Dict:
        """Compare predictions across different timeframes"""

        print(f"[COMPARE] Analyzing {symbol} across all timeframes")

        timeframes = ['day', 'hour', 'minute']
        results = {}

        for timeframe in timeframes:
            try:
                prediction = self.predictor.make_prediction(symbol, timeframe, model_type, data_limit)
                # Extract risk metrics if available
                risk_metrics = prediction.get('model_info', {}).get('risk_metrics', {})

                results[timeframe] = {
                    'prediction': prediction['prediction'],
                    'confidence': prediction['confidence_score'],
                    'model_accuracy': prediction['model_info']['accuracy'],
                    'risk_metrics': {
                        'sharpe_ratio': risk_metrics.get('sharpe_ratio', 0),
                        'max_drawdown_pct': risk_metrics.get('max_drawdown_pct', 0),
                        'strategy_return_pct': risk_metrics.get('total_return_pct', 0)
                    } if risk_metrics else {}
                }
            except Exception as e:
                print(f"[ERROR] {timeframe} prediction failed: {e}")
                results[timeframe] = {'error': str(e)}

        # Summary analysis
        successful_predictions = {k: v for k, v in results.items() if 'error' not in v}
        consensus = None

        if len(successful_predictions) >= 2:
            predictions = [v['prediction'] for v in successful_predictions.values()]
            if len(set(predictions)) == 1:
                consensus = predictions[0]
            else:
                # Weighted consensus based on confidence
                weighted_votes = {'Buy': 0, 'Hold': 0, 'Sell': 0}
                for tf_result in successful_predictions.values():
                    pred = tf_result['prediction']
                    conf = tf_result['confidence']
                    weighted_votes[pred] += conf

                consensus = max(weighted_votes.items(), key=lambda x: x[1])[0]

        comparison_result = {
            'symbol': symbol,
            'timeframe_analysis': results,
            'consensus_prediction': consensus,
            'analysis_timestamp': datetime.now().isoformat(),
            'successful_timeframes': len(successful_predictions),
            'total_timeframes': len(timeframes)
        }

        return comparison_result

    def batch_analysis(self, symbols: List[str], timeframe: str = 'hour',
                      model_type: str = 'xgboost', data_limit: int = None) -> Dict:
        """Analyze multiple symbols efficiently"""

        print(f"[BATCH] Analyzing {len(symbols)} symbols")

        # Use predictor's batch functionality
        batch_results = self.predictor.batch_predictions(symbols, timeframe, model_type, data_limit)

        # Add summary statistics
        successful_predictions = {k: v for k, v in batch_results.items() if 'error' not in v}

        if successful_predictions:
            prediction_counts = {'Buy': 0, 'Hold': 0, 'Sell': 0}
            total_confidence = 0
            high_confidence_count = 0

            total_sharpe = 0
            total_max_drawdown = 0
            total_strategy_return = 0
            risk_data_count = 0

            for result in successful_predictions.values():
                pred = result.get('prediction', 'Hold')
                conf = result.get('confidence_score', 0)

                prediction_counts[pred] += 1
                total_confidence += conf

                if conf > 0.7:  # High confidence threshold
                    high_confidence_count += 1

                # Aggregate risk metrics if available
                risk_metrics = result.get('risk_metrics', {})
                if risk_metrics:
                    total_sharpe += risk_metrics.get('sharpe_ratio', 0)
                    total_max_drawdown += abs(risk_metrics.get('max_drawdown_pct', 0))
                    total_strategy_return += risk_metrics.get('strategy_return_pct', 0)
                    risk_data_count += 1

            # Calculate average risk metrics
            avg_risk_metrics = {}
            if risk_data_count > 0:
                avg_risk_metrics = {
                    'avg_sharpe_ratio': total_sharpe / risk_data_count,
                    'avg_max_drawdown_pct': total_max_drawdown / risk_data_count,
                    'avg_strategy_return_pct': total_strategy_return / risk_data_count
                }

            summary = {
                'total_symbols': len(symbols),
                'successful_predictions': len(successful_predictions),
                'risk_summary': avg_risk_metrics,
                'failed_predictions': len(symbols) - len(successful_predictions),
                'prediction_distribution': prediction_counts,
                'average_confidence': total_confidence / len(successful_predictions),
                'high_confidence_predictions': high_confidence_count,
                'model_info': {
                    'timeframe': timeframe,
                    'model_type': model_type
                }
            }
        else:
            summary = {
                'total_symbols': len(symbols),
                'successful_predictions': 0,
                'failed_predictions': len(symbols),
                'error': 'All predictions failed'
            }

        result = {
            'batch_analysis': True,
            'summary': summary,
            'individual_results': batch_results,
            'timestamp': datetime.now().isoformat()
        }

        return result


def main():
    """Enhanced CLI interface for optimized trading bot"""
    parser = argparse.ArgumentParser(description='Optimized Technical Trading Bot - Using Pre-trained Models')
    parser.add_argument('symbol', nargs='?', help='Stock symbol to analyze (e.g., AAPL)')
    parser.add_argument('--timeframe', choices=['day', 'hour', 'minute'], default='hour',
                       help='Data timeframe (default: hour)')
    parser.add_argument('--model', choices=['xgboost', 'random_forest'], default='xgboost',
                       help='ML model type (default: xgboost)')
    parser.add_argument('--batch', nargs='+', help='Analyze multiple symbols (list symbols or use number for batch size)')
    parser.add_argument('--batch-size', type=int, help='Number of symbols to analyze (automatically selects top symbols)')
    parser.add_argument('--all-symbols', action='store_true', help='Analyze all available symbols with sufficient data')
    parser.add_argument('--compare', action='store_true', help='Compare across timeframes')
    parser.add_argument('--simple', action='store_true', help='Simple prediction without analysis')
    parser.add_argument('--models', action='store_true', help='List available models')
    parser.add_argument('--model-dir', default='./models', help='Model directory path')
    parser.add_argument('--data-limit', type=str, default='100', help='Number of database records to use for prediction (default: 100, use "all" for unlimited)')
    parser.add_argument('--output', '-o', help='Output file for JSON result')

    args = parser.parse_args()

    # Parse data limit argument
    def parse_data_limit(value):
        if value == 'all':
            return None
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Invalid data limit: {value}. Use integer or 'all'")

    data_limit = parse_data_limit(args.data_limit)

    try:
        # Initialize optimized bot
        bot = OptimizedTradingBot(model_dir=args.model_dir)

        print(f"[CONFIG] Data limit: {'all available' if data_limit is None else f'{data_limit:,} records'}")

        # Handle different modes
        if args.models:
            models = bot.predictor.list_available_models()
            print(f"\nAVAILABLE MODELS ({len(models)} found):")
            print("-" * 80)
            for name, info in models.items():
                print(f"{name:>15}: {info['validation_accuracy']:.4f} accuracy, "
                      f"{info['training_samples']:,} samples, {info['symbols_count']} symbols")
                print(f"{'':>17} Created: {info['created_at']}")
            return 0

        elif args.all_symbols or args.batch_size or args.batch:
            # Determine symbols to analyze
            if args.all_symbols:
                # Get all available symbols
                symbols = bot.get_available_symbols(args.timeframe)
                print(f"[INFO] Analyzing all {len(symbols)} available symbols")
            elif args.batch_size:
                # Get top N symbols by data volume
                all_symbols = bot.get_available_symbols(args.timeframe)
                if args.batch_size > len(all_symbols):
                    print(f"[WARNING] Requested {args.batch_size} symbols, but only {len(all_symbols)} available")
                    symbols = all_symbols
                else:
                    symbols = all_symbols[:args.batch_size]
                print(f"[INFO] Analyzing top {len(symbols)} symbols by data volume")
            else:
                # Use explicitly provided symbols
                symbols = args.batch
                print(f"[INFO] Analyzing {len(symbols)} specified symbols")

            result = bot.batch_analysis(symbols, args.timeframe, args.model, data_limit)
            output_json = json.dumps(result, indent=2)

        elif args.batch:  # Legacy fallback
            result = bot.batch_analysis(args.batch, args.timeframe, args.model, data_limit)
            output_json = json.dumps(result, indent=2)

        elif args.compare and args.symbol:
            result = bot.compare_timeframes(args.symbol.upper(), args.model, data_limit)
            output_json = json.dumps(result, indent=2)

        elif args.symbol:
            output_json = bot.get_enhanced_prediction(
                symbol=args.symbol.upper(),
                timeframe=args.timeframe,
                model_type=args.model,
                include_analysis=not args.simple,
                data_limit=data_limit
            )

        else:
            print("Please specify a symbol, use batch options, --models to list models, or see examples below:")
            print("\nExamples:")
            print("  python technical_optimized.py AAPL")
            print("  python technical_optimized.py AAPL --data-limit 500")
            print("  python technical_optimized.py AAPL --data-limit all")
            print("  python technical_optimized.py --batch AAPL NVDA TSLA --data-limit 1000")
            print("  python technical_optimized.py --batch-size 10 --data-limit 1000")
            print("  python technical_optimized.py --all-symbols --data-limit 500")
            print("  python technical_optimized.py AAPL --compare --data-limit all")
            return 1

        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_json)
            print(f"[OUTPUT] Results saved to {args.output}")
        else:
            print("\n" + "="*60)
            print("OPTIMIZED TRADING BOT RESULTS")
            print("="*60)
            print(output_json)

    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())