import React, { useState } from 'react';
import {
  TrendingUp,
  BarChart3,
  Brain,
  History,
  Heart,
  Play,
  ChevronRight,
  IdCard,
  Check,
  X
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { analysisAPI } from '../services/api';
import type { AnalysisConfig, LoadingState } from '../types';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [quickAnalysis, setQuickAnalysis] = useState<AnalysisConfig>({
    symbol: '',
    analysisType: 'sentiment',
    articles: 20
  });
  const [loading, setLoading] = useState<LoadingState>({ isLoading: false });
  const [result, setResult] = useState<any>(null);

  const handleQuickAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickAnalysis.symbol.trim()) return;

    setLoading({ isLoading: true, message: 'Running analysis...' });
    setResult(null);

    try {
      let response;
      const symbol = quickAnalysis.symbol.toUpperCase();

      switch (quickAnalysis.analysisType) {
        case 'sentiment':
          response = await analysisAPI.getSentiment(symbol, quickAnalysis.articles);
          break;
        case 'technical':
          response = await analysisAPI.getTechnical(symbol);
          break;
        case 'unified':
          response = await analysisAPI.getUnified(symbol, quickAnalysis.articles);
          break;
        case 'industry':
          response = await analysisAPI.getIndustry(symbol);
          break;
        default:
          throw new Error('Invalid analysis type');
      }

      setResult(response.data);
    } catch (error: any) {
      console.error('Analysis failed:', error);
      setResult({ error: error.response?.data?.error || 'Analysis failed' });
    } finally {
      setLoading({ isLoading: false });
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
      case 'bullish':
        return 'text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-200';
      case 'negative':
      case 'bearish':
        return 'text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-200';
      default:
        return 'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  const getFeatureIcon = (feature: string) => {
    switch (feature) {
      case 'sentiment': return <Heart className="h-4 w-4" />;
      case 'technical': return <BarChart3 className="h-4 w-4" />;
      case 'unified': return <Brain className="h-4 w-4" />;
      case 'historical': return <History className="h-4 w-4" />;
      default: return <ChevronRight className="h-4 w-4" />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Welcome Section */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center">
          <TrendingUp className="h-8 w-8 mr-3 text-blue-600" />
          Dashboard
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Welcome back, {user?.userName}! Your account tier: {user?.tierName}
        </p>
      </div>

      {/* License Info Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8">
        <div className="flex items-center mb-4">
          <IdCard className="h-5 w-5 text-blue-600 mr-2" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">License Information</h2>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">License Tier</p>
            <p className="font-medium text-gray-900 dark:text-white capitalize">{user?.tierName}</p>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 mt-3">User</p>
            <p className="font-medium text-gray-900 dark:text-white">{user?.userName || 'Anonymous'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Available Features</p>
            <div className="flex flex-wrap gap-2">
              {user?.features && Object.entries(user.features).map(([feature, enabled]) => (
                <span
                  key={feature}
                  className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    enabled
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                  }`}
                >
                  {enabled ? <Check className="h-3 w-3 mr-1" /> : <X className="h-3 w-3 mr-1" />}
                  {feature.charAt(0).toUpperCase() + feature.slice(1)}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Analysis */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8">
        <div className="flex items-center mb-4">
          <Play className="h-5 w-5 text-blue-600 mr-2" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Quick Analysis</h2>
        </div>

        <form onSubmit={handleQuickAnalysis} className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Stock Symbol
            </label>
            <input
              type="text"
              value={quickAnalysis.symbol}
              onChange={(e) => setQuickAnalysis({ ...quickAnalysis, symbol: e.target.value })}
              placeholder="e.g., AAPL"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Analysis Type
            </label>
            <select
              value={quickAnalysis.analysisType}
              onChange={(e) => setQuickAnalysis({ ...quickAnalysis, analysisType: e.target.value as any })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              {user?.features?.sentiment && <option value="sentiment">Sentiment Analysis</option>}
              {user?.features?.technical && <option value="technical">Technical Analysis</option>}
              {user?.features?.unified && <option value="unified">Unified Analysis</option>}
              {user?.features?.sentiment && <option value="industry">Industry Analysis</option>}
            </select>
          </div>

          {(quickAnalysis.analysisType === 'sentiment' || quickAnalysis.analysisType === 'unified') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Articles
              </label>
              <input
                type="number"
                value={quickAnalysis.articles}
                onChange={(e) => setQuickAnalysis({ ...quickAnalysis, articles: parseInt(e.target.value) })}
                min="5"
                max="100"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          )}

          <div className="flex items-end">
            <button
              type="submit"
              disabled={loading.isLoading || !quickAnalysis.symbol.trim()}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {loading.isLoading ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Analyzing...
                </div>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Analyze
                </>
              )}
            </button>
          </div>
        </form>

        {/* Quick Analysis Results */}
        {result && (
          <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            {result.error ? (
              <div className="text-red-600 dark:text-red-400">
                Error: {result.error}
              </div>
            ) : (
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white mb-2">
                  Analysis Complete for {quickAnalysis.symbol.toUpperCase()}
                </h3>
                {quickAnalysis.analysisType === 'sentiment' && (
                  <div className="space-y-2">
                    <p>
                      <span className="text-gray-600 dark:text-gray-400">Overall Sentiment: </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSentimentColor(result.overall_sentiment)}`}>
                        {result.overall_sentiment}
                      </span>
                    </p>
                    <p className="text-gray-600 dark:text-gray-400">
                      Total Articles: {result.total_articles}
                    </p>
                    <p className="text-gray-600 dark:text-gray-400">
                      Average Sentiment: {result.sentiment_scores?.average_sentiment?.toFixed(3)}
                    </p>
                  </div>
                )}
                {quickAnalysis.analysisType === 'technical' && (
                  <div className="space-y-2">
                    <p>
                      <span className="text-gray-600 dark:text-gray-400">Prediction: </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        result.prediction_summary?.prediction === 'BUY' ? 'text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-200' :
                        result.prediction_summary?.prediction === 'SELL' ? 'text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-200' :
                        'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300'
                      }`}>
                        {result.prediction_summary?.prediction || 'HOLD'}
                      </span>
                    </p>
                    <p className="text-gray-600 dark:text-gray-400">
                      Confidence: {((result.prediction_summary?.confidence || 0) * 100).toFixed(1)}%
                    </p>
                    <p className="text-gray-600 dark:text-gray-400">
                      Current Price: ${result.market_analysis?.current_price?.toFixed(2)}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {user?.features?.sentiment && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
            <div className="text-center">
              <Heart className="h-12 w-12 text-blue-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Sentiment Analysis</h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
                Analyze market sentiment from news and social media
              </p>
              <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 flex items-center justify-center">
                <ChevronRight className="h-4 w-4 mr-1" />
                Start Analysis
              </button>
            </div>
          </div>
        )}

        {user?.features?.technical && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
            <div className="text-center">
              <BarChart3 className="h-12 w-12 text-green-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Technical Analysis</h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
                AI-powered technical indicators and predictions
              </p>
              <button className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 flex items-center justify-center">
                <ChevronRight className="h-4 w-4 mr-1" />
                Start Analysis
              </button>
            </div>
          </div>
        )}

        {user?.features?.unified && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
            <div className="text-center">
              <Brain className="h-12 w-12 text-purple-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Unified Analysis</h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
                Comprehensive analysis combining all data sources
              </p>
              <button className="w-full px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 flex items-center justify-center">
                <ChevronRight className="h-4 w-4 mr-1" />
                Start Analysis
              </button>
            </div>
          </div>
        )}

        {user?.features?.historical && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
            <div className="text-center">
              <History className="h-12 w-12 text-orange-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Historical Data</h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
                Access historical price and volume data
              </p>
              <button className="w-full px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 flex items-center justify-center">
                <ChevronRight className="h-4 w-4 mr-1" />
                View Data
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;