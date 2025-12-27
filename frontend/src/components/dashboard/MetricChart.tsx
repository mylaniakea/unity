import React from 'react';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ChartOptions
} from 'chart.js';
import { useTheme } from '../../contexts/ThemeContext';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface DataPoint {
  timestamp: string;
  value: number;
}

interface MetricChartProps {
  title: string;
  data: DataPoint[];
  color?: string;
  unit?: string;
  chartType?: 'line' | 'bar';
  height?: number;
}

export default function MetricChart({
  title,
  data,
  color = '#3b82f6',
  unit = '',
  chartType = 'line',
  height = 300
}: MetricChartProps) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // Prepare chart data
  const labels = data.map(d => {
    const date = new Date(d.timestamp);
    return date.toLocaleTimeString();
  });

  const values = data.map(d => d.value);

  const chartData = {
    labels,
    datasets: [
      {
        label: title,
        data: values,
        borderColor: color,
        backgroundColor: chartType === 'line' 
          ? `${color}33` // 20% opacity for area fill
          : color,
        fill: chartType === 'line',
        tension: 0.4,
        pointRadius: data.length > 50 ? 0 : 3,
        pointHoverRadius: 5
      }
    ]
  };

  const options: ChartOptions<'line' | 'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: (context) => {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += context.parsed.y.toFixed(2) + unit;
            }
            return label;
          }
        }
      }
    },
    scales: {
      x: {
        grid: {
          color: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
        },
        ticks: {
          color: isDark ? '#9ca3af' : '#6b7280',
          maxTicksLimit: 8
        }
      },
      y: {
        grid: {
          color: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
        },
        ticks: {
          color: isDark ? '#9ca3af' : '#6b7280',
          callback: function(value) {
            return value + unit;
          }
        },
        beginAtZero: true
      }
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
        {title}
      </h3>
      <div style={{ height: `${height}px` }}>
        {data.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
            No data available
          </div>
        ) : chartType === 'line' ? (
          <Line data={chartData} options={options} />
        ) : (
          <Bar data={chartData} options={options as ChartOptions<'bar'>} />
        )}
      </div>
    </div>
  );
}
