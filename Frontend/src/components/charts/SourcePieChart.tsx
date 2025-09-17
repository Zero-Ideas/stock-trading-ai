import React from 'react';
import { Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

interface SourcePieChartProps {
  sourceBreakdown: Record<string, { count: number; avg_sentiment: number }>;
  isDarkMode?: boolean;
}

const SourcePieChart: React.FC<SourcePieChartProps> = ({
  sourceBreakdown,
  isDarkMode = false,
}) => {
  const sources = Object.keys(sourceBreakdown);
  const counts = sources.map(source => sourceBreakdown[source].count);
  const colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#34495e', '#e67e22'];

  const data = {
    labels: sources.map(s => s.replace(/[()]/g, '').substring(0, 12)),
    datasets: [
      {
        data: counts,
        backgroundColor: colors.slice(0, sources.length),
        borderWidth: 2,
        borderColor: isDarkMode ? '#4a4a4a' : '#ffffff',
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
            size: 11,
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

  return <Pie data={data} options={options} />;
};

export default SourcePieChart;