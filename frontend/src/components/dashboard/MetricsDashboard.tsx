import React from 'react';
import { useState, useEffect, useCallback } from 'react';
import { useUpdates } from '@/contexts/UpdatesContext';
import MetricChart from './MetricChart';
import dashboardApi, { MetricsHistory } from '../../api/dashboard';

type TimeRange = '1h' | '6h' | '24h' | '7d';

interface MetricsDashboardProps {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export default function MetricsDashboard({ 
  autoRefresh = true, 
  refreshInterval = 30000 
}: MetricsDashboardProps) {
  const { updatesPaused } = useUpdates();
  const [timeRange, setTimeRange] = useState<TimeRange>('1h');
  const [metricsData, setMetricsData] = useState<MetricsHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      setError(null);
      const data = await dashboardApi.getMetricsHistory(timeRange);
      setMetricsData(data);
    } catch (err) {
      console.error('Failed to fetch metrics history:', err);
      setError('Failed to load metrics data');
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  useEffect(() => {
    if (!autoRefresh || updatesPaused) return;

    const interval = setInterval(fetchMetrics, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, updatesPaused, fetchMetrics]);

  const timeRangeOptions: TimeRange[] = ['1h', '6h', '24h', '7d'];
  const timeRangeLabels = {
    '1h': '1 Hour',
    '6h': '6 Hours',
    '24h': '24 Hours',
    '7d': '7 Days'
  };

  if (loading && !metricsData) {
    return (
      <div className="space-y-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4 animate-pulse"></div>
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-red-800 dark:text-red-200">{error}</p>
        <button
          onClick={fetchMetrics}
          className="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  const cpuData = metricsData?.metrics['system_info.cpu_percent'] || [];
  const memoryData = metricsData?.metrics['system_info.memory_percent'] || [];
  const diskData = metricsData?.metrics['disk_monitor.disk_usage_percent'] || [];
  const networkSentData = metricsData?.metrics['network_monitor.network_bytes_sent'] || [];
  const networkRecvData = metricsData?.metrics['network_monitor.network_bytes_recv'] || [];

  // Combine network data for dual metric
  const networkData = networkSentData.length > 0 ? networkSentData : [];

  return (
    <div className="space-y-6">
      {/* Time Range Selector */}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Historical Metrics
        </h2>
        <div className="flex space-x-2">
          {timeRangeOptions.map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {timeRangeLabels[range]}
            </button>
          ))}
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {/* CPU Chart */}
        <MetricChart
          title="CPU Usage"
          data={cpuData}
          color="#3b82f6"
          unit="%"
          chartType="line"
          height={250}
        />

        {/* Memory Chart */}
        <MetricChart
          title="Memory Usage"
          data={memoryData}
          color="#8b5cf6"
          unit="%"
          chartType="line"
          height={250}
        />

        {/* Disk Chart */}
        <MetricChart
          title="Disk Usage"
          data={diskData}
          color="#f59e0b"
          unit="%"
          chartType="line"
          height={250}
        />

        {/* Network Chart */}
        <MetricChart
          title="Network Traffic (Sent)"
          data={networkData}
          color="#10b981"
          unit=" bytes"
          chartType="line"
          height={250}
        />
      </div>

      {/* Last Updated */}
      {metricsData && (
        <p className="text-xs text-gray-500 dark:text-gray-400 text-right">
          Last updated: {new Date(metricsData.fetched_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}
