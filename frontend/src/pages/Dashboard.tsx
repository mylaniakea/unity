import { useState, useEffect, useCallback } from 'react';
import { Cpu, HardDrive, Server, Activity, Wifi, WifiOff } from 'lucide-react';
import dashboardApi, { DashboardOverview } from '../api/dashboard';
import AlertStatusCard from '../components/dashboard/AlertStatusCard';
import PluginHealthGrid from '../components/dashboard/PluginHealthGrid';
import InfrastructureOverview from '../components/dashboard/InfrastructureOverview';
import MetricsDashboard from '../components/dashboard/MetricsDashboard';
import { useWebSocket, WebSocketMessage } from '../hooks/useWebSocket';
import { useUpdates } from '@/contexts/UpdatesContext';

interface StatCardProps {
  title: string;
  value: string | number;
  subtext?: string;
  icon: React.ElementType;
  color: string;
}

function StatCard({ title, value, subtext, icon: Icon, color }: StatCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
          <p className={`text-3xl font-bold mt-2 ${color}`}>{value}</p>
          {subtext && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{subtext}</p>
          )}
        </div>
        <Icon className={`w-12 h-12 ${color} opacity-20`} />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [useWebSocketUpdates, setUseWebSocketUpdates] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // WebSocket connection for real-time updates
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    if (message.type === 'metrics:update') {
      // Update metrics in real-time
      setOverview(prev => {
        if (!prev) return prev;
        
        const pluginId = message.plugin_id;
        const metrics = message.metrics;
        
        // Update specific plugin metrics
        // This is a simplified update - in production, you'd want more sophisticated merging
        return {
          ...prev,
          timestamp: message.timestamp || new Date().toISOString(),
        };
      });
      setLastUpdate(new Date());
    } else if (message.type === 'plugin:status') {
      // Update plugin status
      setOverview(prev => {
        if (!prev) return prev;
        
        const pluginId = message.plugin_id;
        const status = message.status;
        
        // Update plugin status in plugins list
        const updatedPlugins = prev.plugins.items.map(p => 
          p.plugin_id === pluginId 
            ? { ...p, status: status.status || p.status, last_execution: status.last_execution || p.last_execution }
            : p
        );
        
        return {
          ...prev,
          plugins: {
            ...prev.plugins,
            items: updatedPlugins,
          },
        };
      });
      setLastUpdate(new Date());
    } else if (message.type === 'execution:complete') {
      // Plugin execution completed - trigger a refresh of that plugin's data
      setLastUpdate(new Date());
    }
  }, []);

  const { updatesPaused } = useUpdates();
  
  const { connected: wsConnected, reconnect: wsReconnect } = useWebSocket({
    onMessage: handleWebSocketMessage,
    onConnect: () => {
      console.log('WebSocket connected - using real-time updates');
    },
    onDisconnect: () => {
      console.log('WebSocket disconnected - falling back to polling');
    },
    onError: (err) => {
      console.error('WebSocket error:', err);
    },
    // Disable WebSocket when updates are paused
    enabled: !updatesPaused,
  });

  const fetchDashboardData = useCallback(async () => {
    try {
      setError(null);
      const data = await dashboardApi.getOverview();
      setOverview(data);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Fallback polling when WebSocket is not connected (every 60 seconds - less aggressive)
  useEffect(() => {
    if (!wsConnected && !updatesPaused) {
      const interval = setInterval(fetchDashboardData, 60000); // 60 seconds instead of 30
      return () => clearInterval(interval);
    }
  }, [wsConnected, updatesPaused, fetchDashboardData]);

  const formatValue = (val: number | null | undefined, unit = '', decimals = 1): string => {
    if (val === null || val === undefined) return 'N/A';
    return `${val.toFixed(decimals)}${unit}`;
  };

  if (loading && !overview) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <p className="text-red-800 dark:text-red-200 mb-2">{error}</p>
        <button
          onClick={fetchDashboardData}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  const metrics = overview?.metrics;
  const alerts = overview?.alerts;
  const infrastructure = overview?.infrastructure;
  const plugins = overview?.plugins;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Real-time monitoring and system overview
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            {wsConnected ? (
              <>
                <Wifi className="w-4 h-4 text-green-500" />
                <span className="text-sm text-green-600 dark:text-green-400">Live</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-500">Polling</span>
                <button
                  onClick={wsReconnect}
                  className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                >
                  Reconnect
                </button>
              </>
            )}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="CPU Usage"
          value={formatValue(metrics?.cpu?.value, '%')}
          subtext={metrics?.cpu ? new Date(metrics.cpu.timestamp).toLocaleTimeString() : undefined}
          icon={Cpu}
          color="text-blue-600 dark:text-blue-400"
        />
        <StatCard
          title="Memory Usage"
          value={formatValue(metrics?.memory?.value, '%')}
          subtext={metrics?.memory ? new Date(metrics.memory.timestamp).toLocaleTimeString() : undefined}
          icon={Activity}
          color="text-purple-600 dark:text-purple-400"
        />
        <StatCard
          title="Disk Usage"
          value={formatValue(metrics?.disk?.value, '%')}
          subtext={metrics?.disk ? new Date(metrics.disk.timestamp).toLocaleTimeString() : undefined}
          icon={HardDrive}
          color="text-orange-600 dark:text-orange-400"
        />
        <StatCard
          title="Active Plugins"
          value={`${plugins?.healthy || 0}/${plugins?.enabled || 0}`}
          subtext={`${plugins?.stale || 0} stale`}
          icon={Server}
          color="text-green-600 dark:text-green-400"
        />
      </div>

      {/* Alert Status & Infrastructure */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AlertStatusCard 
          alertSummary={alerts || null} 
          loading={loading}
        />
        <InfrastructureOverview 
          infrastructure={infrastructure || null}
          loading={loading}
        />
      </div>

      {/* Plugin Health Grid */}
      <PluginHealthGrid 
        plugins={plugins?.items || []}
        loading={loading}
      />

      {/* Historical Metrics Charts */}
      <MetricsDashboard autoRefresh={true} refreshInterval={120000} />

      {/* Footer Info */}
      <div className="text-center text-xs text-gray-500 dark:text-gray-400 py-4">
        <p>
          {wsConnected ? 'Real-time updates via WebSocket' : 'Polling every 30 seconds'} • 
          {plugins?.total || 0} total plugins • 
          {alerts?.unresolved || 0} unresolved alerts
        </p>
      </div>
    </div>
  );
}
