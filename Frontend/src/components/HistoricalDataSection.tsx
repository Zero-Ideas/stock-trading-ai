import React, { useState, useEffect } from 'react';
import { TrendingUp, Calendar } from 'lucide-react';
import HistoricalChart from './charts/HistoricalChart';
import { analysisAPI } from '../services/api';

interface HistoricalDataSectionProps {
  symbol: string;
  isDarkMode?: boolean;
}

interface HistoricalData {
  dates: string[];
  prices: number[];
}

interface HoverData {
  date: string;
  price: number;
  index: number;
}

const HistoricalDataSection: React.FC<HistoricalDataSectionProps> = ({
  symbol,
  isDarkMode = false,
}) => {
  const [timeframe, setTimeframe] = useState<string>('30d');
  const [historicalData, setHistoricalData] = useState<HistoricalData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [hoverData, setHoverData] = useState<HoverData | null>(null);
  const [stats, setStats] = useState<{
    currentPrice: number;
    high: number;
    low: number;
    change: number;
    changePercent: number;
  } | null>(null);

  const getDateRange = (timeframe: string) => {
    const endDate = new Date();
    const startDate = new Date();

    switch (timeframe) {
      case '30d':
        startDate.setDate(endDate.getDate() - 30);
        break;
      case '90d':
        startDate.setDate(endDate.getDate() - 90);
        break;
      case '1y':
        startDate.setFullYear(endDate.getFullYear() - 1);
        break;
      case '2y':
        startDate.setFullYear(endDate.getFullYear() - 2);
        break;
      default:
        startDate.setDate(endDate.getDate() - 30);
    }

    return {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0],
    };
  };

  const fetchHistoricalData = async () => {
    if (!symbol) return;

    setLoading(true);
    try {
      const { startDate, endDate } = getDateRange(timeframe);
      const response = await analysisAPI.getHistorical(symbol, startDate, endDate);

      if (response.data && Array.isArray(response.data)) {
        const dates = response.data.map((item: any) =>
          new Date(item.Date).toLocaleDateString()
        );
        const prices = response.data.map((item: any) => item.Close);

        const historicalData = { dates, prices };
        setHistoricalData(historicalData);

        // Calculate statistics
        const currentPrice = prices[prices.length - 1];
        const firstPrice = prices[0];
        const high = Math.max(...prices);
        const low = Math.min(...prices);
        const change = currentPrice - firstPrice;
        const changePercent = (change / firstPrice) * 100;

        setStats({
          currentPrice,
          high,
          low,
          change,
          changePercent,
        });
      }
    } catch (error) {
      console.error('Error fetching historical data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistoricalData();
  }, [symbol, timeframe]);

  const handleHover = (data: HoverData | null) => {
    setHoverData(data);
  };

  const getChangeColor = (change: number) => {
    if (change > 0) return 'text-green-600';
    if (change < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
          <TrendingUp className="h-5 w-5 mr-2 text-blue-600" />
          Historical Stock Data
        </h3>
        <div className="flex items-center">
          <Calendar className="h-4 w-4 mr-2 text-gray-600 dark:text-gray-400" />
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="text-sm px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="30d">30 Days</option>
            <option value="90d">90 Days</option>
            <option value="1y">1 Year</option>
            <option value="2y">2 Years</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="h-80">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : historicalData ? (
              <HistoricalChart
                historicalData={historicalData}
                isDarkMode={isDarkMode}
                onHover={handleHover}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                No data available
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          {stats && (
            <>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Price Statistics
                </h4>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 dark:text-gray-400 text-sm">Current:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      ${stats.currentPrice.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 dark:text-gray-400 text-sm">High:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      ${stats.high.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 dark:text-gray-400 text-sm">Low:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      ${stats.low.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 dark:text-gray-400 text-sm">Change:</span>
                    <span className={`font-medium ${getChangeColor(stats.change)}`}>
                      {stats.change >= 0 ? '+' : ''}${stats.change.toFixed(2)} ({stats.change >= 0 ? '+' : ''}{stats.changePercent.toFixed(2)}%)
                    </span>
                  </div>
                </div>
              </div>

              {hoverData && (
                <div className="bg-blue-50 dark:bg-blue-900 rounded-lg p-4 border border-blue-200 dark:border-blue-700">
                  <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-3">
                    Point Details
                  </h4>
                  <div className="space-y-2">
                    <div className="text-sm">
                      <span className="text-blue-700 dark:text-blue-300 font-medium">Date:</span>
                      <span className="ml-2 text-blue-900 dark:text-blue-100">
                        {new Date(hoverData.date).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="text-sm">
                      <span className="text-blue-700 dark:text-blue-300 font-medium">Price:</span>
                      <span className="ml-2 text-blue-900 dark:text-blue-100 font-bold">
                        ${hoverData.price.toFixed(2)}
                      </span>
                    </div>
                    {hoverData.index > 0 && historicalData && (
                      <div className="text-sm">
                        <span className="text-blue-700 dark:text-blue-300 font-medium">Change:</span>
                        <span className={`ml-2 font-medium ${
                          getChangeColor(hoverData.price - historicalData.prices[hoverData.index - 1])
                        }`}>
                          {(() => {
                            const dayChange = hoverData.price - historicalData.prices[hoverData.index - 1];
                            const dayChangePercent = (dayChange / historicalData.prices[hoverData.index - 1]) * 100;
                            return `${dayChange >= 0 ? '+' : ''}${dayChange.toFixed(2)} (${dayChange >= 0 ? '+' : ''}${dayChangePercent.toFixed(2)}%)`;
                          })()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoricalDataSection;