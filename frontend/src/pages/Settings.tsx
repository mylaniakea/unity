import React, { useState, useEffect } from 'react';
import api from '@/api/client';
import { Settings as SettingsIcon, Activity, Database, Clock } from 'lucide-react';

interface HealthStatus {
  status: string;
  scheduler: string;
  cache: string;
  timestamp: string;
}

export default function Settings() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchHealth = async () => {
    try {
      const res = await api.get('../health');
      setHealth(res.data);
    } catch (err) {
      console.error('Failed to fetch health:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    if (status === 'healthy' || status === 'running' || status === 'connected') {
      return 'text-green-500';
    }
    return 'text-red-500';
  };

  const getStatusBg = (status: string) => {
    if (status === 'healthy' || status === 'running' || status === 'connected') {
      return 'bg-green-100 dark:bg-green-900/30';
    }
    return 'bg-red-100 dark:bg-red-900/30';
  };

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <SettingsIcon className="text-gray-900 dark:text-white" size={32} />
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>
      </div>

      {/* System Health */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">System Health</h2>
        
        {loading ? (
          <p className="text-gray-600 dark:text-gray-400">Loading...</p>
        ) : health ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <Activity className={getStatusColor(health.status)} size={24} />
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Backend Status</p>
                <p className="font-semibold text-gray-900 dark:text-white capitalize">{health.status}</p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <Clock className={getStatusColor(health.scheduler)} size={24} />
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Scheduler</p>
                <p className="font-semibold text-gray-900 dark:text-white capitalize">{health.scheduler}</p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <Database className={getStatusColor(health.cache)} size={24} />
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Cache</p>
                <p className="font-semibold text-gray-900 dark:text-white capitalize">{health.cache}</p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-red-600 dark:text-red-400">Failed to load health status</p>
        )}

        {health && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-4">
            Last updated: {new Date(health.timestamp).toLocaleString()}
          </p>
        )}
      </div>

      {/* Application Info */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Application Info</h2>
        <div className="space-y-3">
          <div className="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
            <span className="text-gray-600 dark:text-gray-400">Version</span>
            <span className="font-medium text-gray-900 dark:text-white">1.0.0</span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
            <span className="text-gray-600 dark:text-gray-400">Environment</span>
            <span className="font-medium text-gray-900 dark:text-white">Development</span>
          </div>
          <div className="flex justify-between py-2">
            <span className="text-gray-600 dark:text-gray-400">API Endpoint</span>
            <span className="font-medium text-gray-900 dark:text-white">/api</span>
          </div>
        </div>
      </div>
    </div>
  );
}
