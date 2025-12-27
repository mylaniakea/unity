import api from './client';

export interface DashboardOverview {
  timestamp: string;
  metrics: {
    cpu: { value: number; timestamp: string } | null;
    memory: { value: number; timestamp: string } | null;
    disk: { value: number; timestamp: string } | null;
    network: { value: number; timestamp: string } | null;
  };
  alerts: {
    total: number;
    unresolved: number;
    by_severity: {
      critical: number;
      warning: number;
      info: number;
    };
    recent_alerts: Array<{
      id: string;
      title: string;
      severity: string;
      status: string;
      triggered_at: string;
      resource_type: string | null;
      resource_id: string | null;
    }>;
  };
  infrastructure: {
    servers: {
      total: number;
      healthy: number;
      unhealthy: number;
    };
    storage: {
      total: number;
      devices: number;
      pools: number;
    };
    databases: {
      total: number;
      online: number;
      offline: number;
    };
  };
  plugins: {
    total: number;
    enabled: number;
    healthy: number;
    stale: number;
    items: Array<{
      plugin_id: string;
      name: string;
      category: string;
      enabled: boolean;
      last_execution: string | null;
      status: string;
      is_stale: boolean;
    }>;
  };
}

export interface MetricsHistory {
  time_range: string;
  metrics: {
    [key: string]: Array<{
      timestamp: string;
      value: number;
    }>;
  };
  fetched_at: string;
}

export interface PluginHealth {
  total: number;
  summary: {
    healthy: number;
    stale: number;
    failed: number;
    unknown: number;
  };
  plugins: Array<{
    plugin_id: string;
    name: string;
    category: string;
    enabled: boolean;
    last_execution: string | null;
    status: string;
    is_stale: boolean;
  }>;
  fetched_at: string;
}

export const dashboardApi = {
  /**
   * Get complete dashboard overview data
   */
  async getOverview(): Promise<DashboardOverview> {
    const response = await api.get('/api/v1/monitoring/dashboard/overview');
    return response.data;
  },

  /**
   * Get historical metrics data
   */
  async getMetricsHistory(timeRange: '1h' | '6h' | '24h' | '7d' = '1h'): Promise<MetricsHistory> {
    const response = await api.get('/api/v1/monitoring/dashboard/metrics/history', {
      params: { time_range: timeRange }
    });
    return response.data;
  },

  /**
   * Get plugin health status
   */
  async getPluginHealth(category?: string): Promise<PluginHealth> {
    const response = await api.get('/api/v1/monitoring/dashboard/plugins/health', {
      params: category ? { category } : {}
    });
    return response.data;
  },

  /**
   * Get single metric history
   */
  async getSingleMetricHistory(
    pluginId: string,
    metricName: string,
    timeRange: '1h' | '6h' | '24h' | '7d' = '1h'
  ): Promise<{
    plugin_id: string;
    metric_name: string;
    time_range: string;
    data: Array<{ timestamp: string; value: number }>;
    count: number;
    fetched_at: string;
  }> {
    const response = await api.get(
      `/api/v1/monitoring/dashboard/metrics/${pluginId}/${metricName}/history`,
      {
        params: { time_range: timeRange }
      }
    );
    return response.data;
  }
};

export default dashboardApi;
