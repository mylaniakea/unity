import React, { useState, useEffect } from 'react';
import { Plug, Activity, Server, AlertTriangle } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '@/api/client';

interface Plugin {
  id: string;
  name: string;
  enabled: boolean;
}

export default function Dashboard() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [pluginsRes, healthRes] = await Promise.all([
        api.get('/plugins'),
        api.get('../health')
      ]);
      setPlugins(pluginsRes.data);
      setHealth(healthRes.data);
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const enabledPlugins = plugins.filter(p => p.enabled).length;
  const totalPlugins = plugins.length;

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">Dashboard</h1>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Link to="/plugins" className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Plugins</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{loading ? '...' : totalPlugins}</p>
              <p className="text-xs text-green-600 dark:text-green-400 mt-1">{enabledPlugins} enabled</p>
            </div>
            <Plug className="text-blue-500" size={32} />
          </div>
        </Link>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">System Status</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {loading ? '...' : health?.status || 'Unknown'}
              </p>
              {health && (
                <p className="text-xs text-green-600 dark:text-green-400 mt-1 capitalize">
                  {health.scheduler} • {health.cache}
                </p>
              )}
            </div>
            <Activity className="text-green-500" size={32} />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Servers</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">0</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">No servers configured</p>
            </div>
            <Server className="text-purple-500" size={32} />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Alerts</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">0</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">No active alerts</p>
            </div>
            <AlertTriangle className="text-orange-500" size={32} />
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Link to="/plugins" className="p-4 text-center border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
            <Plug className="mx-auto mb-2 text-blue-500" size={24} />
            <span className="text-sm text-gray-900 dark:text-white">Manage Plugins</span>
          </Link>
          <Link to="/settings" className="p-4 text-center border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
            <Activity className="mx-auto mb-2 text-green-500" size={24} />
            <span className="text-sm text-gray-900 dark:text-white">System Health</span>
          </Link>
          <Link to="/homelab" className="p-4 text-center border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
            <Server className="mx-auto mb-2 text-purple-500" size={24} />
            <span className="text-sm text-gray-900 dark:text-white">Homelab</span>
          </Link>
          <Link to="/alerts" className="p-4 text-center border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
            <AlertTriangle className="mx-auto mb-2 text-orange-500" size={24} />
            <span className="text-sm text-gray-900 dark:text-white">View Alerts</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
