import React, { useState, useEffect } from 'react';
import { Search, Download, Share2, TrendingUp, BarChart3, Brain, Building2, History } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { analysisAPI } from '../services/api';
import SentimentDistributionChart from '../components/charts/SentimentDistributionChart';
import SourcePieChart from '../components/charts/SourcePieChart';
import ArticlesSidebar from '../components/ArticlesSidebar';
import HistoricalDataSection from '../components/HistoricalDataSection';
import type { AnalysisConfig, LoadingState } from '../types';

const Analyze: React.FC = () => {
  const { user } = useAuth();
  const [config, setConfig] = useState<AnalysisConfig>({
    symbol: '',
    analysisType: 'sentiment',
    articles: 20,
    timeframe: 'hour',
    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0]
  });
  const [loading, setLoading] = useState<LoadingState>({ isLoading: false });
  const [result, setResult] = useState<any>(null);
  const [isDarkMode, setIsDarkMode] = useState<boolean>(false);

  // Detect dark mode from document
  useEffect(() => {
    const checkDarkMode = () => {
      setIsDarkMode(document.documentElement.classList.contains('dark'));
    };

    checkDarkMode();

    // Watch for theme changes
    const observer = new MutationObserver(checkDarkMode);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => observer.disconnect();
  }, []);

  const handleAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config.symbol.trim()) return;

    setLoading({ isLoading: true, message: 'Running detailed analysis...' });
    setResult(null);

    try {
      let response;
      const symbol = config.symbol.toUpperCase();

      switch (config.analysisType) {
        case 'sentiment':
          response = await analysisAPI.getSentiment(symbol, config.articles);
          break;
        case 'technical':
          response = await analysisAPI.getTechnical(symbol, config.timeframe);
          break;
        case 'unified':
          response = await analysisAPI.getUnified(symbol, config.articles);
          break;
        case 'industry':
          response = await analysisAPI.getIndustry(symbol);
          break;
        case 'historical':
          response = await analysisAPI.getHistorical(symbol, config.startDate!, config.endDate!);
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

  const renderSentimentResults = (data: any) => (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        {/* Overview Stats */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 flex items-center">
            <Brain className="h-6 w-6 mr-2 text-blue-600" />
            Overall Sentiment Analysis
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="text-3xl font-bold mb-2">
                <span className={`px-4 py-2 rounded-full text-lg font-medium ${getSentimentColor(data.overall_sentiment)}`}>
                  {data.overall_sentiment}
                </span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Score: {data.sentiment_scores?.average_sentiment?.toFixed(3)}
              </p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="text-2xl font-bold text-blue-600 mb-1">{data.total_articles}</div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Articles</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="text-2xl font-bold text-purple-600 mb-1">
                {((data.sentiment_scores?.weighted_avg_from_sources || 0) * 100).toFixed(0)}%
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Confidence</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="text-2xl font-bold text-green-600 mb-1">
                {Object.keys(data.source_breakdown || {}).length}
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Sources</p>
            </div>
          </div>

          {/* Distribution Bar */}
          <div>
            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-3">Sentiment Distribution</h4>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-8 flex overflow-hidden">
              <div
                className="bg-green-500 flex items-center justify-center text-white text-sm font-medium"
                style={{ width: `${data.sentiment_distribution?.positive_percentage || 0}%` }}
              >
                {data.sentiment_distribution?.positive_percentage?.toFixed(1)}%
              </div>
              <div
                className="bg-yellow-500 flex items-center justify-center text-white text-sm font-medium"
                style={{ width: `${data.sentiment_distribution?.neutral_percentage || 0}%` }}
              >
                {data.sentiment_distribution?.neutral_percentage?.toFixed(1)}%
              </div>
              <div
                className="bg-red-500 flex items-center justify-center text-white text-sm font-medium"
                style={{ width: `${data.sentiment_distribution?.negative_percentage || 0}%` }}
              >
                {data.sentiment_distribution?.negative_percentage?.toFixed(1)}%
              </div>
            </div>
            <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mt-2">
              <span>Positive</span>
              <span>Neutral</span>
              <span>Negative</span>
            </div>
          </div>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">📈 Sentiment Distribution</h4>
            <div className="h-64">
              <SentimentDistributionChart
                distribution={{
                  positive: data.sentiment_distribution?.positive || 0,
                  negative: data.sentiment_distribution?.negative || 0,
                  neutral: data.sentiment_distribution?.neutral || 0,
                }}
                isDarkMode={isDarkMode}
              />
            </div>
          </div>

          {data.source_breakdown && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">🥧 Source Distribution</h4>
              <div className="h-64">
                <SourcePieChart
                  sourceBreakdown={data.source_breakdown}
                  isDarkMode={isDarkMode}
                />
              </div>
            </div>
          )}
        </div>

        {/* Historical Data */}
        {config.symbol && (
          <HistoricalDataSection symbol={config.symbol} isDarkMode={isDarkMode} />
        )}
      </div>

      {/* Articles Sidebar */}
      <div className="lg:col-span-1">
        <ArticlesSidebar
          articles={data.recent_articles || data.raw_articles || []}
          loading={loading.isLoading}
        />
      </div>
    </div>
  );

  const renderTechnicalResults = (data: any) => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 text-center">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Prediction</h3>
          <span className={`px-3 py-1 rounded-full text-lg font-medium ${
            data.prediction_summary?.prediction === 'BUY' ? 'text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-200' :
            data.prediction_summary?.prediction === 'SELL' ? 'text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-200' :
            'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300'
          }`}>
            {data.prediction_summary?.prediction || 'HOLD'}
          </span>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            Confidence: {((data.prediction_summary?.confidence || 0) * 100).toFixed(1)}%
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 text-center">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Current Price</h3>
          <div className="text-2xl font-bold text-blue-600">
            ${data.market_analysis?.current_price?.toFixed(2)}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            Trend: {data.market_analysis?.price_trend}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 text-center">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">RSI</h3>
          <div className="text-2xl font-bold text-purple-600">
            {data.market_analysis?.rsi_value?.toFixed(1)}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            {data.market_analysis?.rsi_condition}
          </p>
        </div>
      </div>

      <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Technical Indicators</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <span className="text-gray-600 dark:text-gray-400">Price Trend:</span>
            <span className="ml-2 px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-sm">
              {data.market_analysis?.price_trend}
            </span>
          </div>
          <div>
            <span className="text-gray-600 dark:text-gray-400">Volume Trend:</span>
            <span className="ml-2 px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-sm">
              {data.market_analysis?.volume_trend}
            </span>
          </div>
          <div>
            <span className="text-gray-600 dark:text-gray-400">RSI Condition:</span>
            <span className="ml-2 px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-sm">
              {data.market_analysis?.rsi_condition}
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center">
          <Search className="h-8 w-8 mr-3 text-blue-600" />
          Stock Analysis
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Comprehensive analysis tools for informed trading decisions
        </p>
      </div>

      {/* Analysis Configuration */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8">
        <div className="flex items-center mb-4">
          <BarChart3 className="h-5 w-5 text-blue-600 mr-2" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Analysis Configuration</h2>
        </div>

        <form onSubmit={handleAnalysis} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Stock Symbol *
              </label>
              <input
                type="text"
                value={config.symbol}
                onChange={(e) => setConfig({ ...config, symbol: e.target.value })}
                placeholder="e.g., AAPL, TSLA"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                required
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Analysis Type *
              </label>
              <select
                value={config.analysisType}
                onChange={(e) => setConfig({ ...config, analysisType: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                {user?.features?.sentiment && <option value="sentiment">Sentiment Analysis</option>}
                {user?.features?.technical && <option value="technical">Technical Analysis</option>}
                {user?.features?.unified && <option value="unified">Unified Analysis</option>}
                {user?.features?.sentiment && <option value="industry">Industry Analysis</option>}
                {user?.features?.historical && <option value="historical">Historical Data</option>}
              </select>
            </div>

            {(config.analysisType === 'sentiment' || config.analysisType === 'unified') && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Articles
                </label>
                <input
                  type="number"
                  value={config.articles}
                  onChange={(e) => setConfig({ ...config, articles: parseInt(e.target.value) })}
                  min="5"
                  max="100"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            )}

            {config.analysisType === 'technical' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Timeframe
                </label>
                <select
                  value={config.timeframe}
                  onChange={(e) => setConfig({ ...config, timeframe: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="minute">Minute</option>
                  <option value="hour">Hour</option>
                  <option value="day">Day</option>
                </select>
              </div>
            )}

            {config.analysisType === 'historical' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={config.startDate}
                    onChange={(e) => setConfig({ ...config, startDate: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    End Date
                  </label>
                  <input
                    type="date"
                    value={config.endDate}
                    onChange={(e) => setConfig({ ...config, endDate: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
              </>
            )}

            <div className="flex items-end">
              <button
                type="submit"
                disabled={loading.isLoading || !config.symbol.trim()}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {loading.isLoading ? (
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Analyzing...
                  </div>
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Run Analysis
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Results */}
      {loading.isLoading && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8">
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Running Analysis...</h3>
            <p className="text-gray-600 dark:text-gray-400">
              {loading.message || 'This may take a few moments depending on the analysis type and data volume.'}
            </p>
          </div>
        </div>
      )}

      {result?.error && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8">
          <div className="text-center py-12">
            <div className="text-red-600 dark:text-red-400">
              <h3 className="text-lg font-medium mb-2">Analysis Failed</h3>
              <p>{result.error}</p>
            </div>
          </div>
        </div>
      )}

      {result && !result.error && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
              <TrendingUp className="h-6 w-6 mr-3 text-blue-600" />
              {config.analysisType.charAt(0).toUpperCase() + config.analysisType.slice(1)} Analysis for {config.symbol.toUpperCase()}
            </h2>
            <div className="flex space-x-2">
              <button className="px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center transition-colors">
                <Download className="h-4 w-4 mr-1" />
                Export
              </button>
              <button className="px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center transition-colors">
                <Share2 className="h-4 w-4 mr-1" />
                Share
              </button>
            </div>
          </div>

          {config.analysisType === 'sentiment' && renderSentimentResults(result)}
          {config.analysisType === 'technical' && renderTechnicalResults(result)}
          {config.analysisType === 'unified' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                <div className="bg-green-50 dark:bg-green-900 border border-green-200 dark:border-green-700 rounded-lg p-6">
                  <h4 className="font-medium text-green-800 dark:text-green-200 mb-2">Analysis Complete</h4>
                  <p className="text-green-700 dark:text-green-300">
                    {result.summary?.data_sources_successful}/{result.summary?.total_data_sources} data sources processed successfully
                  </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <h4 className="font-medium text-gray-900 dark:text-white mb-4">Data Source Status</h4>
                    <div className="space-y-3">
                      {[
                        { label: 'Company Sentiment', status: result.summary?.company_sentiment_status },
                        { label: 'Industry Sentiment', status: result.summary?.industry_sentiment_status },
                        { label: 'Market Data', status: result.summary?.market_data_status },
                        { label: 'Technical Analysis', status: result.summary?.technical_analysis_status }
                      ].map((item, index) => (
                        <div key={index} className="flex justify-between items-center">
                          <span className="text-gray-600 dark:text-gray-400">{item.label}</span>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            item.status === 'success'
                              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                              : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                          }`}>
                            {item.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <h4 className="font-medium text-gray-900 dark:text-white mb-4">Analysis Details</h4>
                    <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                      <p><strong>GPT-5 Prompt Length:</strong> {result.gpt5_prompt?.length || 0} characters</p>
                      <p><strong>Analysis Timestamp:</strong> {new Date(result.analysis_timestamp).toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="lg:col-span-1">
                <ArticlesSidebar
                  articles={result.recent_articles || []}
                  loading={loading.isLoading}
                />
              </div>
            </div>
          )}
          {config.analysisType === 'industry' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 text-center">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Industry</h3>
                    <div className="text-2xl font-bold text-blue-600">{result.industry || 'Unknown'}</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 text-center">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Industry Sentiment</h3>
                    <span className={`px-4 py-2 rounded-full text-lg font-medium ${getSentimentColor(result.industry_sentiment)}`}>
                      {result.industry_sentiment || 'Neutral'}
                    </span>
                  </div>
                </div>

                {result.peer_analysis && Object.keys(result.peer_analysis).length > 0 && (
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <h4 className="font-medium text-gray-900 dark:text-white mb-4">Peer Companies</h4>
                    <div className="space-y-3">
                      {Object.entries(result.peer_analysis).map(([symbol, data]: [string, any]) => (
                        <div key={symbol} className="flex justify-between items-center bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                          <div>
                            <span className="font-medium text-gray-900 dark:text-white">{symbol}</span>
                            <span className="text-gray-600 dark:text-gray-400 ml-2">{data.company_name || symbol}</span>
                          </div>
                          <span className={`px-3 py-1 rounded text-sm font-medium ${getSentimentColor(data.sentiment)}`}>
                            {data.sentiment || 'Unknown'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="lg:col-span-1">
                <ArticlesSidebar
                  articles={result.recent_articles || []}
                  loading={loading.isLoading}
                />
              </div>
            </div>
          )}
          {config.analysisType === 'historical' && (
            <div className="space-y-6">
              <div className="bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-700 rounded-lg p-6">
                <h4 className="font-medium text-blue-800 dark:text-blue-200 mb-2">Historical Data Retrieved</h4>
                <p className="text-blue-700 dark:text-blue-300">
                  {Array.isArray(result) ? result.length : 0} data points from {config.startDate} to {config.endDate}
                </p>
              </div>

              {Array.isArray(result) && result.length > 0 && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                      <thead className="bg-gray-50 dark:bg-gray-700">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Date</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Open</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">High</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Low</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Close</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Volume</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                        {result.slice(0, 10).map((row: any, index: number) => (
                          <tr key={index}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                              {new Date(row.Date).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                              ${row.Open?.toFixed(2)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                              ${row.High?.toFixed(2)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                              ${row.Low?.toFixed(2)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                              ${row.Close?.toFixed(2)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                              {row.Volume?.toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {result.length > 10 && (
                      <div className="bg-gray-50 dark:bg-gray-700 px-6 py-3">
                        <p className="text-center text-gray-500 dark:text-gray-400 text-sm">
                          Showing first 10 of {result.length} records
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Analyze;