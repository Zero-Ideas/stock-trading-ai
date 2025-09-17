#!/usr/bin/env python3
"""
Model Predictor - Lightweight prediction engine using pre-trained models
"""

import numpy as np
import pandas as pd
import json
import joblib
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
import os
from pathlib import Path
warnings.filterwarnings('ignore')

# Custom imports
from technical import TechnicalTradingBot


class ModelPredictor:
    """Lightweight prediction engine using pre-trained models"""

    def __init__(self, model_dir: str = "./models"):
        """Initialize predictor with model directory"""
        self.model_dir = Path(model_dir)
        self.models = {}  # Cache for loaded models
        self.bot = TechnicalTradingBot()

        if not self.model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {model_dir}")

        print(f"[PREDICTOR] Initialized with model directory: {self.model_dir}")

    def load_model(self, timeframe: str, model_type: str = 'xgboost') -> Dict:
        """Load a specific model and its metadata"""
        model_key = f"{timeframe}_{model_type}"

        if model_key in self.models:
            return self.models[model_key]

        model_filename = f"trading_model_{timeframe}_{model_type}.pkl"
        info_filename = f"trading_model_{timeframe}_{model_type}_info.json"

        model_path = self.model_dir / model_filename
        info_path = self.model_dir / info_filename

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        if not info_path.exists():
            raise FileNotFoundError(f"Model info not found: {info_path}")

        # Load model
        model_data = joblib.load(model_path)

        # Load metadata
        with open(info_path, 'r') as f:
            model_info = json.load(f)

        combined = {
            'model': model_data['model'],
            'feature_names': model_data['feature_names'],
            'label_mapping': model_data['label_mapping'],
            'reverse_mapping': model_data['reverse_mapping'],
            'info': model_info
        }

        # Cache the model
        self.models[model_key] = combined

        print(f"[MODEL] Loaded {timeframe} {model_type} model (accuracy: {model_info.get('validation_accuracy', 0):.4f})")
        return combined

    def prepare_prediction_features(self, symbol: str, timeframe: str, periods: int = None) -> pd.DataFrame:
        """Prepare features for prediction using recent data"""

        # Load recent data for the symbol
        if periods is None:
            print(f"[DATA] Loading all available data for {symbol} ({timeframe})")
            df = self.bot.load_stock_data(symbol, timeframe)
        else:
            print(f"[DATA] Loading {periods} recent records for {symbol} ({timeframe})")
            df = self.bot.load_stock_data(symbol, timeframe, limit=periods)

        if len(df) < 50:
            raise ValueError(f"Insufficient data for {symbol}: {len(df)} records")

        # Calculate technical indicators
        df_indicators = self.bot.calculate_technical_indicators(df)

        # Prepare features (without labels)
        exclude_cols = ['symbol', 'original']
        feature_cols = [col for col in df_indicators.columns if col not in exclude_cols]

        features = df_indicators[feature_cols].copy()

        # Add symbol encoding (same method as in trainer)
        features['symbol_encoded'] = hash(symbol) % 1000

        # Remove any NaN values by forward filling and then dropping remaining NaNs
        features = features.fillna(method='ffill').dropna()

        if len(features) == 0:
            raise ValueError(f"No valid features after processing for {symbol}")

        return features

    def make_prediction(self, symbol: str, timeframe: str = 'hour',
                       model_type: str = 'xgboost', data_limit: int = None) -> Dict:
        """Make prediction for a symbol using pre-trained model"""

        print(f"[PREDICT] Making prediction for {symbol} ({timeframe})")

        # Load model
        model_data = self.load_model(timeframe, model_type)

        # Prepare features
        features_df = self.prepare_prediction_features(symbol, timeframe, periods=data_limit)

        # Get the latest data point
        latest_features = features_df.iloc[-1:].copy()

        # Ensure all required features are present
        model_features = model_data['feature_names']
        missing_features = set(model_features) - set(latest_features.columns)

        if missing_features:
            # Add missing features with default values
            for feature in missing_features:
                latest_features[feature] = 0.0
            print(f"[WARNING] Added {len(missing_features)} missing features with default values")

        # Reorder features to match model training order
        latest_features = latest_features[model_features]

        # Make prediction
        prediction_mapped = model_data['model'].predict(latest_features)[0]
        prediction = model_data['reverse_mapping'][prediction_mapped]

        # Get prediction probabilities if available
        if hasattr(model_data['model'], 'predict_proba'):
            probabilities = model_data['model'].predict_proba(latest_features)[0]
            confidence_score = np.max(probabilities)

            # Create probability distribution
            prob_dist = {}
            for i, prob in enumerate(probabilities):
                original_label = model_data['reverse_mapping'][i]
                label_name = {-1: 'Sell', 0: 'Hold', 1: 'Buy'}[original_label]
                prob_dist[label_name] = float(prob)
        else:
            confidence_score = 0.5
            prob_dist = {}

        # Map prediction to label
        prediction_labels = {-1: 'Sell', 0: 'Hold', 1: 'Buy'}
        prediction_label = prediction_labels[prediction]

        # Get current market data
        current_data = features_df.iloc[-1]

        # Get model feature importance for explanation
        feature_importance = {}
        if model_data['info'].get('feature_importance'):
            # Get top 5 most important features and their current values
            top_features = sorted(model_data['info']['feature_importance'].items(),
                                key=lambda x: x[1], reverse=True)[:5]

            for feature, importance in top_features:
                if feature in current_data.index:
                    feature_importance[feature] = {
                        'importance': float(importance),
                        'current_value': float(current_data[feature])
                    }

        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'model_type': model_type,
            'prediction': prediction_label,
            'prediction_numeric': int(prediction),
            'confidence_score': float(confidence_score),
            'probability_distribution': prob_dist,
            'model_info': {
                'accuracy': model_data['info'].get('validation_accuracy', 0),
                'training_samples': model_data['info'].get('training_samples', 0),
                'symbols_trained': len(model_data['info'].get('symbols_used', [])),
                'created_at': model_data['info'].get('created_at'),
                'risk_metrics': model_data['info'].get('risk_metrics', {})
            },
            'feature_explanation': feature_importance,
            'timestamp': datetime.now().isoformat()
        }

        print(f"[PREDICT] {symbol}: {prediction_label} (confidence: {confidence_score:.1%})")
        return result

    def batch_predictions(self, symbols: List[str], timeframe: str = 'hour',
                         model_type: str = 'xgboost', data_limit: int = None) -> Dict[str, Dict]:
        """Make predictions for multiple symbols"""

        print(f"[BATCH] Making predictions for {len(symbols)} symbols")
        results = {}

        for symbol in symbols:
            try:
                result = self.make_prediction(symbol, timeframe, model_type, data_limit)
                results[symbol] = result
            except Exception as e:
                print(f"[ERROR] Failed to predict {symbol}: {e}")
                results[symbol] = {'error': str(e)}

        return results

    def list_available_models(self) -> Dict:
        """List all available models"""
        models = {}

        for model_file in self.model_dir.glob("trading_model_*.pkl"):
            parts = model_file.stem.split('_')
            if len(parts) >= 4:
                timeframe = parts[2]
                model_type = parts[3]

                info_file = self.model_dir / f"{model_file.stem}_info.json"
                if info_file.exists():
                    with open(info_file, 'r') as f:
                        info = json.load(f)

                    models[f"{timeframe}_{model_type}"] = {
                        'timeframe': timeframe,
                        'model_type': model_type,
                        'validation_accuracy': info.get('validation_accuracy', 0),
                        'training_samples': info.get('training_samples', 0),
                        'symbols_count': len(info.get('symbols_used', [])),
                        'created_at': info.get('created_at')
                    }

        return models

    def get_model_summary(self, timeframe: str = None, model_type: str = None) -> Dict:
        """Get summary of available models"""
        models = self.list_available_models()

        if timeframe:
            models = {k: v for k, v in models.items() if v['timeframe'] == timeframe}
        if model_type:
            models = {k: v for k, v in models.items() if v['model_type'] == model_type}

        summary = {
            'total_models': len(models),
            'models': models,
            'best_accuracy': max([m['validation_accuracy'] for m in models.values()]) if models else 0,
            'total_training_samples': sum([m['training_samples'] for m in models.values()]) if models else 0
        }

        return summary


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Make predictions using pre-trained models')
    parser.add_argument('symbol', nargs='?', help='Stock symbol to predict')
    parser.add_argument('--timeframe', choices=['day', 'hour', 'minute'], default='hour')
    parser.add_argument('--model', choices=['xgboost', 'random_forest'], default='xgboost')
    parser.add_argument('--batch', nargs='+', help='Multiple symbols for batch prediction')
    parser.add_argument('--list', action='store_true', help='List available models')
    parser.add_argument('--model-dir', default='./models', help='Model directory')
    parser.add_argument('--output', '-o', help='Output file for results')

    args = parser.parse_args()

    try:
        predictor = ModelPredictor(model_dir=args.model_dir)

        if args.list:
            models = predictor.list_available_models()
            print(f"\nAVAILABLE MODELS ({len(models)} found):")
            print("-" * 80)
            for name, info in models.items():
                print(f"{name:>15}: {info['validation_accuracy']:.4f} accuracy, "
                      f"{info['training_samples']:,} samples, {info['symbols_count']} symbols")
            return 0

        if args.batch:
            results = predictor.batch_predictions(args.batch, args.timeframe, args.model)
            output = {
                'batch_prediction': True,
                'timeframe': args.timeframe,
                'model_type': args.model,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
        elif args.symbol:
            result = predictor.make_prediction(args.symbol.upper(), args.timeframe, args.model)
            output = result
        else:
            print("Please specify a symbol or use --batch for multiple symbols")
            return 1

        # Output results
        output_json = json.dumps(output, indent=2)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_json)
            print(f"[OUTPUT] Results saved to {args.output}")
        else:
            print("\n" + "="*60)
            print("PREDICTION RESULTS")
            print("="*60)
            print(output_json)

    except Exception as e:
        print(f"[ERROR] Prediction failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())