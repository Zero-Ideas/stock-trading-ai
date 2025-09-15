#!/usr/bin/env python3
"""
Unified Analysis Script - Combines all data sources for comprehensive stock analysis
Gathers sentiment, technical, and market data to create GPT-5 decision prompts
"""

import json
import pandas as pd
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# Custom imports
from technical_optimized import TechnicalTradingBot

# Import sentiment and industry analysis with error handling
try:
    from sentiment import StockSentimentAnalyzer
    SENTIMENT_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Sentiment analysis not available: {e}")
    SENTIMENT_AVAILABLE = False

try:
    import industry_analysis
    INDUSTRY_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Industry analysis not available: {e}")
    INDUSTRY_AVAILABLE = False

try:
    from technical_optimized import OptimizedTradingBot
    TECHNICAL_OPTIMIZED_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Technical optimized analysis not available: {e}")
    TECHNICAL_OPTIMIZED_AVAILABLE = False

class UnifiedAnalyzer:
    """Master analyzer combining sentiment, industry, and technical analysis"""

    def __init__(self):
        """Initialize the unified analyzer"""
        self.bot = TechnicalTradingBot()
        self.analysis_timestamp = datetime.now().isoformat()

    def get_company_sentiment(self, symbol: str, articles: int = 20) -> Dict:
        """Get company sentiment analysis using direct import"""
        print(f"[SENTIMENT] Analyzing company sentiment for {symbol}...")

        if not SENTIMENT_AVAILABLE:
            return {"status": "error", "error": "Sentiment analysis module not available"}

        try:
            # Create sentiment analyzer instance
            analyzer = StockSentimentAnalyzer(symbol, use_database=True)

            # Run the analysis
            result = analyzer.analyze_sentiment(target_articles=articles)

            print(f"[SENTIMENT] Company sentiment analysis completed")
            return {
                "status": "success",
                "data": result,
                "articles_analyzed": result.get("total_articles", 0),
                "overall_sentiment": result.get("overall_sentiment", "neutral"),
                "sentiment_score": result.get("sentiment_score", 0.0)
            }

        except Exception as e:
            print(f"[SENTIMENT] Company sentiment analysis error: {e}")
            return {"status": "error", "error": str(e)}

    def get_industry_sentiment(self, symbol: str) -> Dict:
        """Get industry sentiment analysis using direct import"""
        print(f"[INDUSTRY] Analyzing industry sentiment for {symbol}...")

        if not INDUSTRY_AVAILABLE:
            return {"status": "error", "error": "Industry analysis module not available"}

        try:
            # Create industry analyzer instance
            analyzer = industry_analysis.IndustryAnalyzer()

            # Run the analysis for the symbol
            result = analyzer.analyze_industry(target_company_symbol=symbol, force_refresh=False, cache_hours=24.0)

            print(f"[INDUSTRY] Industry sentiment analysis completed")
            return {
                "status": "success",
                "data": result,
                "industry": result.get("industry", "unknown"),
                "industry_sentiment": result.get("industry_sentiment", "neutral"),
                "peer_comparison": result.get("peer_analysis", {})
            }

        except Exception as e:
            print(f"[INDUSTRY] Industry sentiment analysis error: {e}")
            return {"status": "error", "error": str(e)}

    def get_recent_market_data(self, symbol: str) -> Dict:
        """Get recent market data for different timeframes"""
        print(f"[MARKET] Loading recent market data for {symbol}...")

        market_data = {}

        try:
            # Get minute-level data (last 100 rows)
            minute_df = self.bot.load_stock_data(symbol, 'minute', limit=100)
            if not minute_df.empty:
                minute_data = minute_df[['open', 'high', 'low', 'close', 'vwap', 'volume', 'trade_count']].tail(100)
                market_data['minute_data'] = {
                    'timeframe': 'minute',
                    'rows': len(minute_data),
                    'latest_timestamp': minute_data.index[-1].isoformat(),
                    'earliest_timestamp': minute_data.index[0].isoformat(),
                    'latest_price': float(minute_data['close'].iloc[-1]),
                    'price_change_1min': float(minute_data['close'].iloc[-1] - minute_data['close'].iloc[-2]) if len(minute_data) >= 2 else 0,
                    'volume_latest': int(minute_data['volume'].iloc[-1]),
                    'vwap_latest': float(minute_data['vwap'].iloc[-1]),
                    'data': minute_data.to_dict('records')
                }

            # Get hour-level data (last 24 rows)
            hour_df = self.bot.load_stock_data(symbol, 'hour', limit=24)
            if not hour_df.empty:
                hour_data = hour_df[['open', 'high', 'low', 'close', 'vwap', 'volume', 'trade_count']].tail(24)
                market_data['hour_data'] = {
                    'timeframe': 'hour',
                    'rows': len(hour_data),
                    'latest_timestamp': hour_data.index[-1].isoformat(),
                    'earliest_timestamp': hour_data.index[0].isoformat(),
                    'latest_price': float(hour_data['close'].iloc[-1]),
                    'price_change_1hour': float(hour_data['close'].iloc[-1] - hour_data['close'].iloc[-2]) if len(hour_data) >= 2 else 0,
                    'price_change_24hour': float(hour_data['close'].iloc[-1] - hour_data['close'].iloc[0]) if len(hour_data) >= 24 else 0,
                    'volume_latest': int(hour_data['volume'].iloc[-1]),
                    'vwap_latest': float(hour_data['vwap'].iloc[-1]),
                    'data': hour_data.to_dict('records')
                }

            # Get day-level data (last 7 rows)
            day_df = self.bot.load_stock_data(symbol, 'day', limit=7)
            if not day_df.empty:
                day_data = day_df[['open', 'high', 'low', 'close', 'vwap', 'volume', 'trade_count']].tail(7)
                market_data['day_data'] = {
                    'timeframe': 'day',
                    'rows': len(day_data),
                    'latest_timestamp': day_data.index[-1].isoformat(),
                    'earliest_timestamp': day_data.index[0].isoformat(),
                    'latest_price': float(day_data['close'].iloc[-1]),
                    'price_change_1day': float(day_data['close'].iloc[-1] - day_data['close'].iloc[-2]) if len(day_data) >= 2 else 0,
                    'price_change_7day': float(day_data['close'].iloc[-1] - day_data['close'].iloc[0]) if len(day_data) >= 7 else 0,
                    'volume_latest': int(day_data['volume'].iloc[-1]),
                    'vwap_latest': float(day_data['vwap'].iloc[-1]),
                    'data': day_data.to_dict('records')
                }

            print(f"[MARKET] Market data loaded successfully")
            return {"status": "success", "data": market_data}

        except Exception as e:
            print(f"[MARKET] Market data loading error: {e}")
            return {"status": "error", "error": str(e)}

    def get_technical_analysis(self, symbol: str) -> Dict:
        """Get technical analysis and predictions using direct imports"""
        print(f"[TECHNICAL] Running technical analysis for {symbol}...")

        if not TECHNICAL_OPTIMIZED_AVAILABLE:
            return {"status": "error", "error": "Technical optimized analysis module not available"}

        try:
            # Create optimized trading bot instance
            bot = OptimizedTradingBot()

            # Get timeframe comparison
            comparison_data = {}
            try:
                comparison_data = bot.compare_timeframes(symbol, model_type='xgboost', data_limit=500)
            except Exception as e:
                print(f"[TECHNICAL] Timeframe comparison failed: {e}")

            # Get dedicated hour timeframe prediction
            hour_prediction = {}
            try:
                hour_prediction_json = bot.get_enhanced_prediction(
                    symbol=symbol,
                    timeframe='hour',
                    model_type='xgboost',
                    include_analysis=True,
                    data_limit=500
                )
                hour_prediction = json.loads(hour_prediction_json)
            except Exception as e:
                print(f"[TECHNICAL] Hour prediction failed: {e}")

            print(f"[TECHNICAL] Technical analysis completed")
            return {
                "status": "success",
                "timeframe_comparison": comparison_data,
                "hour_prediction": hour_prediction,
                "analysis_summary": {
                    "comparison_available": bool(comparison_data),
                    "hour_prediction_available": bool(hour_prediction),
                    "consensus_prediction": comparison_data.get("consensus_prediction"),
                    "hour_prediction_signal": hour_prediction.get("prediction_summary", {}).get("prediction"),
                    "hour_confidence": hour_prediction.get("prediction_summary", {}).get("confidence")
                }
            }

        except Exception as e:
            print(f"[TECHNICAL] Technical analysis error: {e}")
            return {"status": "error", "error": str(e)}

    def create_gpt5_prompt(self, symbol: str, analysis_data: Dict) -> str:
        """Create a comprehensive prompt for GPT-5 decision making"""

        prompt = f"""# Comprehensive Stock Analysis Request for {symbol}

## Analysis Timestamp: {self.analysis_timestamp}

I need a trading decision recommendation based on the comprehensive analysis below. Please provide:
1. **DECISION**: BUY, SELL, or HOLD
2. **CONFIDENCE**: High, Medium, or Low
3. **REASONING**: Detailed explanation weighing all factors
4. **RISK ASSESSMENT**: Key risks and opportunities
5. **TIME HORIZON**: Short-term (1-7 days) or Medium-term (1-4 weeks) recommendation

---

## 1. COMPANY SENTIMENT ANALYSIS
"""

        # Add company sentiment
        sentiment = analysis_data.get('company_sentiment', {})
        if sentiment.get('status') == 'success':
            data = sentiment['data']
            prompt += f"""
**Overall Sentiment**: {sentiment.get('overall_sentiment', 'Unknown')}
**Sentiment Score**: {sentiment.get('sentiment_score', 0):.3f}
**Articles Analyzed**: {sentiment.get('articles_analyzed', 0)}

**Key Insights**:
- Recent news sentiment: {data.get('recent_sentiment', 'No data')}
- Source diversity: {len(data.get('sources', []))} different sources
- Sentiment breakdown: {data.get('sentiment_breakdown', {})}
"""
        else:
            prompt += f"**Status**: Failed to retrieve company sentiment - {sentiment.get('error', 'Unknown error')}\n"

        # Add industry sentiment
        prompt += "\n## 2. INDUSTRY SENTIMENT ANALYSIS\n"
        industry = analysis_data.get('industry_sentiment', {})
        if industry.get('status') == 'success':
            data = industry['data']
            prompt += f"""
**Industry**: {industry.get('industry', 'Unknown')}
**Industry Sentiment**: {industry.get('industry_sentiment', 'Unknown')}
**Peer Comparison**: {len(industry.get('peer_comparison', {}))} peers analyzed

**Industry Context**:
- Sector performance vs market
- Competitive positioning
- Industry-specific trends and catalysts
"""
        else:
            prompt += f"**Status**: Failed to retrieve industry sentiment - {industry.get('error', 'Unknown error')}\n"

        # Add market data
        prompt += "\n## 3. RECENT MARKET DATA\n"
        market = analysis_data.get('market_data', {})
        if market.get('status') == 'success':
            data = market['data']

            # Minute data summary
            if 'minute_data' in data:
                min_data = data['minute_data']
                prompt += f"""
**Latest Minute Data** (Last {min_data['rows']} minutes):
- Current Price: ${min_data['latest_price']:.2f}
- 1-min Change: ${min_data['price_change_1min']:.2f}
- Latest Volume: {min_data['volume_latest']:,}
- VWAP: ${min_data['vwap_latest']:.2f}
- Time Range: {min_data['earliest_timestamp']} to {min_data['latest_timestamp']}
"""

            # Hour data summary
            if 'hour_data' in data:
                hour_data = data['hour_data']
                prompt += f"""
**Latest Hourly Data** (Last {hour_data['rows']} hours):
- Current Price: ${hour_data['latest_price']:.2f}
- 1-hour Change: ${hour_data['price_change_1hour']:.2f}
- 24-hour Change: ${hour_data['price_change_24hour']:.2f}
- Latest Volume: {hour_data['volume_latest']:,}
- VWAP: ${hour_data['vwap_latest']:.2f}
"""

            # Day data summary
            if 'day_data' in data:
                day_data = data['day_data']
                prompt += f"""
**Latest Daily Data** (Last {day_data['rows']} days):
- Current Price: ${day_data['latest_price']:.2f}
- 1-day Change: ${day_data['price_change_1day']:.2f}
- 7-day Change: ${day_data['price_change_7day']:.2f}
- Latest Volume: {day_data['volume_latest']:,}
- VWAP: ${day_data['vwap_latest']:.2f}
"""
        else:
            prompt += f"**Status**: Failed to retrieve market data - {market.get('error', 'Unknown error')}\n"

        # Add technical analysis
        prompt += "\n## 4. TECHNICAL ANALYSIS\n"
        technical = analysis_data.get('technical_analysis', {})
        if technical.get('status') == 'success':
            summary = technical.get('analysis_summary', {})
            prompt += f"""
**Multi-Timeframe Consensus**: {summary.get('consensus_prediction', 'No consensus')}
**Hour Prediction**: {summary.get('hour_prediction_signal', 'Unknown')}
**Hour Confidence**: {summary.get('hour_confidence', 0):.1%}

**Timeframe Analysis Available**: {summary.get('comparison_available', False)}
**Hour Prediction Available**: {summary.get('hour_prediction_available', False)}

**Technical Insights**:
- Model accuracy and validation metrics
- Risk-adjusted performance indicators
- Feature importance and market factors
- Historical backtesting results
"""

            # Add detailed hour prediction if available
            hour_pred = technical.get('hour_prediction', {})
            if hour_pred:
                pred_summary = hour_pred.get('prediction_summary', {})
                market_analysis = hour_pred.get('market_analysis', {})

                prompt += f"""
**Detailed Hour Analysis**:
- Prediction: {pred_summary.get('prediction', 'Unknown')}
- Confidence: {pred_summary.get('confidence', 0):.1%}
- Current Price: ${market_analysis.get('current_price', 0):.2f}
- Price Trend: {market_analysis.get('price_trend', 'Unknown')}
- RSI Condition: {market_analysis.get('rsi_condition', 'Unknown')} (RSI: {market_analysis.get('rsi_value', 0):.1f})
- Volume Trend: {market_analysis.get('volume_trend', 'Unknown')}
"""
        else:
            prompt += f"**Status**: Failed to retrieve technical analysis - {technical.get('error', 'Unknown error')}\n"

        # Add decision framework
        prompt += f"""
---

## DECISION FRAMEWORK

Please analyze the above data and provide:

1. **PRIMARY RECOMMENDATION**: BUY/SELL/HOLD with confidence level
2. **KEY FACTORS**: Top 3 factors supporting your decision
3. **RISK ASSESSMENT**:
   - Primary risks to the position
   - Risk mitigation strategies
   - Position sizing recommendations
4. **TIME HORIZON**:
   - Short-term outlook (1-7 days)
   - Medium-term outlook (1-4 weeks)
5. **ENTRY/EXIT STRATEGY**:
   - Optimal entry points
   - Stop-loss levels
   - Take-profit targets
6. **MONITORING POINTS**: Key metrics/events to watch

**Analysis Constraints**:
- Current timestamp: {self.analysis_timestamp}
- Data freshness varies by source
- Technical models trained on historical data
- Sentiment analysis reflects recent news only

Please provide a clear, actionable recommendation that considers all available data sources and their relative reliability.
"""

        return prompt

    def analyze_symbol(self, symbol: str, articles: int = 20, save_output: bool = True) -> Dict:
        """Run comprehensive analysis for a symbol"""
        print(f"\n{'='*80}")
        print(f"UNIFIED ANALYSIS FOR {symbol}")
        print(f"{'='*80}")

        analysis_data = {}

        # Gather all data sources
        analysis_data['company_sentiment'] = self.get_company_sentiment(symbol, articles)
        analysis_data['industry_sentiment'] = self.get_industry_sentiment(symbol)
        analysis_data['market_data'] = self.get_recent_market_data(symbol)
        analysis_data['technical_analysis'] = self.get_technical_analysis(symbol)

        # Create GPT-5 prompt
        gpt5_prompt = self.create_gpt5_prompt(symbol, analysis_data)

        # Compile final result
        result = {
            'symbol': symbol,
            'analysis_timestamp': self.analysis_timestamp,
            'data_sources': analysis_data,
            'gpt5_prompt': gpt5_prompt,
            'summary': {
                'company_sentiment_status': analysis_data['company_sentiment']['status'],
                'industry_sentiment_status': analysis_data['industry_sentiment']['status'],
                'market_data_status': analysis_data['market_data']['status'],
                'technical_analysis_status': analysis_data['technical_analysis']['status'],
                'data_sources_successful': sum(1 for source in analysis_data.values() if source.get('status') == 'success'),
                'total_data_sources': len(analysis_data)
            }
        }

        # Save output if requested
        if save_output:
            output_file = f"unified_analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            print(f"\n[OUTPUT] Analysis saved to: {output_file}")

            # Save GPT-5 prompt separately
            prompt_file = f"gpt5_prompt_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(prompt_file, 'w') as f:
                f.write(gpt5_prompt)
            print(f"[OUTPUT] GPT-5 prompt saved to: {prompt_file}")

        return result

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='Unified Stock Analysis - Combines all data sources for GPT-5 decision making')
    parser.add_argument('symbol', help='Stock symbol to analyze (e.g., AAPL)')
    parser.add_argument('--articles', type=int, default=20, help='Number of articles for sentiment analysis (default: 20)')
    parser.add_argument('--no-save', action='store_true', help='Do not save output files')
    parser.add_argument('--prompt-only', action='store_true', help='Only display the GPT-5 prompt')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    args = parser.parse_args()

    try:
        analyzer = UnifiedAnalyzer()
        result = analyzer.analyze_symbol(
            symbol=args.symbol.upper(),
            articles=args.articles,
            save_output=not args.no_save
        )

        if args.prompt_only:
            print("\n" + "="*80)
            print("GPT-5 DECISION PROMPT")
            print("="*80)
            print(result['gpt5_prompt'])
        elif args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"\n[SUCCESS] Unified analysis completed for {args.symbol}")
            print(f"Data sources successful: {result['summary']['data_sources_successful']}/{result['summary']['total_data_sources']}")
            print(f"Analysis timestamp: {result['analysis_timestamp']}")

            print(f"\n[GPT-5 PROMPT LENGTH]: {len(result['gpt5_prompt'])} characters")
            print(f"[RECOMMENDATION]: Review the generated prompt file and submit to GPT-5 for decision making")

    except KeyboardInterrupt:
        print("\n[CANCELLED] Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())