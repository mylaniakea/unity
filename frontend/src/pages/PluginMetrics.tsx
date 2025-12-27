import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, CheckCircle, XCircle } from 'lucide-react';
import MetricChart from '../components/dashboard/MetricChart';
import dashboardApi from '../api/dashboard';

type TimeRange = '1h' | '6h' | '24h' | '7d';

interface MetricData {
  plugin_id: string;
  metric_name: string;
  time_range: string;
  data: Array<{ timestamp: string; value: number }>;
  count: number;
  fetched_at: string;
}

export default function PluginMetrics() {
  const { pluginId } = useParams<{ pluginId: string }>();
  const navigate = useNavigate();
  
  const [timeRange, setTimeRange] = useState<TimeRange>('1h');
  const [metrics, setMetrics] = useState<MetricData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Common metrics to try fetching (we'll filter out empty ones)
  const commonMetrics = [
    'cpu_percent',
    'memory_percent',
    'disk_usage_percent',
    'network_bytes_sent',
    'network_bytes_recv',
    'response_time',
    'connection_count',
    'query_count',
    'error_rate'
  ];

  const fetchMetrics = async () => {
    if (!pluginId) return;
    
    try {
      setError(null);
      setLoading(true);
      
      // Try to fetch common metrics
      const metricPromises = commonMetrics.map(metric =>
        dashboardApi.getSingleMetricHistory(pluginId, metric, timeRange)
          .catch(() => null) // Ignore errors for metrics that don't exist
      );
      
      const results = await Promise.all(metricPromises);
      const validMetrics = results.filter((m): m is MetricData => 
        m !== null && m.data.length > 0
      );
      
      setMetrics(validMetrics);
    } catch (err) {
      console.error('Failed to fetch plugin metrics:', err);
      setError('Failed to load metrics for this plugin');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, [pluginId, timeRange]);

  const timeRangeOptions: TimeRange[] = ['1h', '6h', '24h', '7d'];
  const timeRangeLabels = {
    '1h': '1 Hour',
    '6h': '6 Hours',
    '24h': '24 Hours',
    '7d': '7 Days'
  };

  const formatMetricName = (name: string): string => {
    return name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getMetricColor = (metricName: string): string => {
    const colorMap: Record<string, string> = {
      cpu_percent: '#3b82f6',
      memory_percent: '#8b5cf6',
      disk_usage_percent: '#f59e0b',
      network_bytes_sent: '#10b981',
      network_bytes_recv: '#06b6d4',
      response_time: '#ec4899',
      connection_count: '#6366f1',
      query_count: '#84cc16',
      error_rate: '#ef4444'
    };
    return colorMap[metricName] || '#6b7280';
  };

  const getMetricUnit = (metricName: string): string => {
    if (metricName.includes('percent')) return '%';
    if (metricName.includes('bytes')) return ' bytes';
    if (metricName.includes('time')) return ' ms';
    if (metricName.includes('rate')) return '%';
    return '';
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4 animate-pulse"></div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-64 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => navigate('/plugins')}
          className="flex items-center text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Plugins
        </button>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <p className="text-red-800 dark:text-red-200 mb-2">{error}</p>
          <button
            onClick={fetchMetrics}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/plugins')}
          className="flex items-center text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Plugins
        </button>
        
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Plugin Metrics
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              {pluginId}
            </p>
          </div>
          
          {/* Time Range Selector */}
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
      </div>

      {/* Metrics Grid */}
      {metrics.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {metrics.map((metric) => (
            <MetricChart
              key={metric.metric_name}
              title={formatMetricName(metric.metric_name)}
              data={metric.data}
              color={getMetricColor(metric.metric_name)}
              unit={getMetricUnit(metric.metric_name)}
              chartType="line"
              height={300}
            />
          ))}
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
          <Clock className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            No Metrics Available
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            This plugin hasn't reported any metrics yet, or metrics data is not available for the selected time range.
          </p>
        </div>
      )}

      {/* Metrics Summary */}
      {metrics.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Metrics Summary
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {metrics.map((metric) => {
              const lastValue = metric.data[metric.data.length - 1]?.value;
              const avgValue = metric.data.reduce((sum, d) => sum + d.value, 0) / metric.data.length;
              
              return (
                <div key={metric.metric_name} className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                    {formatMetricName(metric.metric_name)}
                  </p>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">
                    {lastValue?.toFixed(2)}{getMetricUnit(metric.metric_name)}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Avg: {avgValue.toFixed(2)}{getMetricUnit(metric.metric_name)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
