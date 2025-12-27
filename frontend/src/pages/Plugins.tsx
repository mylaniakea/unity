import React, { useState, useEffect } from 'react';
import api from '@/api/client';
import { Plug, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface Plugin {
  id: string;
  name: string;
  version: string;
  description: string;
  category: string;
  enabled: boolean;
  author: string;
  config: Record<string, any>;
}

export default function Plugins() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toggling, setToggling] = useState<string | null>(null);

  useEffect(() => {
    fetchPlugins();
  }, []);

  const fetchPlugins = async () => {
    try {
      setLoading(true);
      const res = await api.get('/plugins');
      setPlugins(res.data);
      setError('');
    } catch (err: any) {
      console.error('Failed to load plugins:', err);
      setError(err.message || 'Failed to load plugins');
    } finally {
      setLoading(false);
    }
  };

  const togglePlugin = async (pluginId: string, currentState: boolean) => {
    try {
      setToggling(pluginId);
      await api.post(`/plugins/${pluginId}/enable`, {
        enabled: !currentState
      });
      // Update local state
      setPlugins(prev => prev.map(p => 
        p.id === pluginId ? { ...p, enabled: !currentState } : p
      ));
    } catch (err: any) {
      console.error('Failed to toggle plugin:', err);
      alert('Failed to toggle plugin: ' + (err.response?.data?.detail || err.message));
    } finally {
      setToggling(null);
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">Plugins</h1>
        <p className="text-gray-600 dark:text-gray-400">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">Plugins</h1>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      </div>
    );
  }

  const enabledCount = plugins.filter(p => p.enabled).length;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Plugins</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {enabledCount} / {plugins.length} enabled
          </span>
          <button
            onClick={fetchPlugins}
            className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600"
            title="Refresh"
          >
            <RefreshCw size={18} />
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {plugins.map((plugin) => (
          <div key={plugin.id} className="bg-white dark:bg-gray-800 rounded-lg shadow-md hover:shadow-lg transition-shadow p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3 flex-1">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Plug className="text-blue-600 dark:text-blue-400" size={24} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-lg text-gray-900 dark:text-white truncate">{plugin.name}</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">v{plugin.version}</p>
                </div>
              </div>
              <button
                onClick={() => togglePlugin(plugin.id, plugin.enabled)}
                disabled={toggling === plugin.id}
                className={`p-2 rounded-lg transition-colors ${
                  plugin.enabled
                    ? 'bg-green-100 dark:bg-green-900/30 hover:bg-green-200 dark:hover:bg-green-900/50'
                    : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
                title={plugin.enabled ? 'Disable' : 'Enable'}
              >
                {toggling === plugin.id ? (
                  <RefreshCw className="animate-spin" size={20} />
                ) : plugin.enabled ? (
                  <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
                ) : (
                  <XCircle className="text-gray-400" size={20} />
                )}
              </button>
            </div>
            
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-4 line-clamp-2">{plugin.description}</p>
            
            <div className="flex items-center justify-between">
              <span className="px-2 py-1 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 rounded">
                {plugin.category}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">{plugin.author}</span>
            </div>
          </div>
        ))}
      </div>

      {plugins.length === 0 && (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
          <Plug className="mx-auto text-gray-400 mb-4" size={48} />
          <p className="text-gray-500 dark:text-gray-400">No plugins available</p>
        </div>
      )}
    </div>
  );
}
