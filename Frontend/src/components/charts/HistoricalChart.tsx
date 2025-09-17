import React from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface HistoricalChartProps {
  historicalData: {
    dates: string[];
    prices: number[];
  };
  isDarkMode?: boolean;
  onHover?: (dataPoint: { date: string; price: number; index: number } | null) => void;
}

const HistoricalChart: React.FC<HistoricalChartProps> = ({
  historicalData,
  isDarkMode = false,
  onHover,
}) => {
  // Validate data before rendering
  if (!historicalData || !historicalData.dates || !historicalData.prices) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        No chart data available
      </div>
    );
  }

  if (historicalData.dates.length === 0 || historicalData.prices.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        No chart data points
      </div>
    );
  }

  if (historicalData.dates.length !== historicalData.prices.length) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Chart data mismatch
      </div>
    );
  }

  const data = {
    labels: historicalData.dates,
    datasets: [
      {
        label: 'Close Price',
        data: historicalData.prices,
        borderColor: '#667eea',
        backgroundColor: 'rgba(102, 126, 234, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 8,
        pointBackgroundColor: '#667eea',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      intersect: false,
      mode: 'index' as const,
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        enabled: false, // We'll use custom hover display
      },
    },
    onHover: (event: any, activeElements: any[]) => {
      if (onHover) {
        if (activeElements.length > 0) {
          const index = activeElements[0].index;
          const price = historicalData.prices[index];
          const date = historicalData.dates[index];
          onHover({ date, price, index });
        } else {
          onHover(null);
        }
      }
    },
    scales: {
      y: {
        beginAtZero: false,
        ticks: {
          color: isDarkMode ? '#cccccc' : '#666666',
          callback: function(value: any) {
            return '$' + value.toFixed(2);
          },
        },
        grid: {
          color: isDarkMode ? '#666666' : '#e1e5e9',
        },
      },
      x: {
        ticks: {
          color: isDarkMode ? '#cccccc' : '#666666',
          maxTicksLimit: 8,
        },
        grid: {
          color: isDarkMode ? '#666666' : '#e1e5e9',
        },
      },
    },
  };

  try {
    return <Line data={data} options={options} />;
  } catch (error) {
    console.error('Chart rendering error:', error);
    return (
      <div className="flex items-center justify-center h-full text-red-500">
        Error rendering chart
      </div>
    );
  }
};

export default HistoricalChart;