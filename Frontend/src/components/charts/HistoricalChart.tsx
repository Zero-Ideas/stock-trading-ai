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

  return <Line data={data} options={options} />;
};

export default HistoricalChart;