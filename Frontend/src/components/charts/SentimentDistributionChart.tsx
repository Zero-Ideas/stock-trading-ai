import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

interface SentimentDistributionChartProps {
  distribution: {
    positive: number;
    negative: number;
    neutral: number;
  };
  isDarkMode?: boolean;
}

const SentimentDistributionChart: React.FC<SentimentDistributionChartProps> = ({
  distribution,
  isDarkMode = false,
}) => {
  const data = {
    labels: ['Positive', 'Negative', 'Neutral'],
    datasets: [
      {
        data: [distribution.positive, distribution.negative, distribution.neutral],
        backgroundColor: ['#27ae60', '#e74c3c', '#f39c12'],
        borderWidth: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          color: isDarkMode ? '#cccccc' : '#888888',
          font: {
            size: 12,
          },
        },
      },
      tooltip: {
        backgroundColor: isDarkMode ? '#374151' : '#ffffff',
        titleColor: isDarkMode ? '#ffffff' : '#000000',
        bodyColor: isDarkMode ? '#cccccc' : '#666666',
        borderColor: isDarkMode ? '#4b5563' : '#e5e7eb',
        borderWidth: 1,
      },
    },
  };

  return <Doughnut data={data} options={options} />;
};

export default SentimentDistributionChart;