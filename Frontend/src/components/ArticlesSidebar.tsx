import React, { useState, useMemo } from 'react';
import { Filter, FileText } from 'lucide-react';

interface Article {
  text: string;
  source: string;
  sentiment: number;
  url?: string;
}

interface ArticlesSidebarProps {
  articles: Article[];
  loading?: boolean;
}

const ArticlesSidebar: React.FC<ArticlesSidebarProps> = ({ articles, loading = false }) => {
  const [sentimentFilter, setSentimentFilter] = useState<string>('all');
  const [sourceFilter, setSourceFilter] = useState<string>('all');

  const getSentimentClass = (sentiment: number) => {
    if (sentiment > 0.05) return 'positive';
    if (sentiment < -0.05) return 'negative';
    return 'neutral';
  };

  const getSentimentLabel = (sentiment: number) => {
    if (sentiment > 0.75) return 'Very Positive';
    if (sentiment > 0.15) return 'Positive';
    if (sentiment < -0.75) return 'Very Negative';
    if (sentiment < -0.15) return 'Negative';
    return 'Neutral';
  };

  const getSentimentColorClasses = (sentimentClass: string) => {
    switch (sentimentClass) {
      case 'positive':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'negative':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
    }
  };

  const sources = useMemo(() => {
    return [...new Set(articles.map(article => article.source))].sort();
  }, [articles]);

  const filteredArticles = useMemo(() => {
    let filtered = articles;

    if (sentimentFilter !== 'all') {
      filtered = filtered.filter(article => {
        const sentimentClass = getSentimentClass(article.sentiment);
        return sentimentClass === sentimentFilter;
      });
    }

    if (sourceFilter !== 'all') {
      filtered = filtered.filter(article => article.source === sourceFilter);
    }

    return filtered;
  }, [articles, sentimentFilter, sourceFilter]);

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 max-h-[800px] overflow-hidden flex flex-col">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
          <FileText className="h-5 w-5 mr-2 text-blue-600" />
          Recent Articles
        </h3>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Finding articles...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 max-h-[800px] overflow-hidden flex flex-col">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <FileText className="h-5 w-5 mr-2 text-blue-600" />
        Recent Articles
      </h3>

      {articles.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-4">
          <div className="flex items-center mb-3">
            <Filter className="h-4 w-4 mr-2 text-gray-600 dark:text-gray-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filters</span>
          </div>

          <div className="grid grid-cols-1 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                Sentiment:
              </label>
              <select
                value={sentimentFilter}
                onChange={(e) => setSentimentFilter(e.target.value)}
                className="w-full text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="all">All Sentiments</option>
                <option value="positive">Positive Only</option>
                <option value="negative">Negative Only</option>
                <option value="neutral">Neutral Only</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                Source:
              </label>
              <select
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value)}
                className="w-full text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="all">All Sources</option>
                {sources.map(source => (
                  <option key={source} value={source}>{source}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="text-xs text-gray-500 dark:text-gray-400 text-center mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
            Showing {filteredArticles.length} of {articles.length} articles
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto pr-2">
        <div className="space-y-3">
          {filteredArticles.map((article, index) => {
            const sentimentClass = getSentimentClass(article.sentiment);
            const sentimentLabel = getSentimentLabel(article.sentiment);

            return (
              <div
                key={index}
                className={`bg-gray-50 dark:bg-gray-700 p-4 rounded-lg border-l-4 border-blue-500 transition-transform hover:translate-x-1 ${
                  article.url ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600' : ''
                }`}
                onClick={() => article.url && window.open(article.url, '_blank')}
              >
                <div className="text-sm font-medium text-gray-900 dark:text-white mb-2 leading-snug">
                  {article.text}
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
                    {article.source}
                  </span>
                  <span className={`px-2 py-1 rounded font-medium ${getSentimentColorClasses(sentimentClass)}`}>
                    {sentimentLabel}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {filteredArticles.length === 0 && articles.length > 0 && (
          <div className="text-center py-8">
            <p className="text-gray-500 dark:text-gray-400">No articles match the current filters</p>
          </div>
        )}

        {articles.length === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-500 dark:text-gray-400">No articles available</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ArticlesSidebar;