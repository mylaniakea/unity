import { CheckCircle, XCircle, Clock, MinusCircle } from 'lucide-react';
import { motion } from 'framer-motion';

interface Plugin {
  plugin_id: string;
  name: string;
  category: string;
  enabled: boolean;
  last_execution: string | null;
  status: string;
  is_stale: boolean;
}

interface PluginHealthGridProps {
  plugins: Plugin[];
  loading?: boolean;
}

export default function PluginHealthGrid({ plugins, loading }: PluginHealthGridProps) {
  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4 animate-pulse"></div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {[...Array(12)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  const getStatusConfig = (plugin: Plugin) => {
    if (!plugin.enabled) {
      return {
        icon: MinusCircle,
        color: 'text-gray-400',
        bg: 'bg-gray-100 dark:bg-gray-700',
        border: 'border-gray-300 dark:border-gray-600',
        label: 'Disabled'
      };
    }
    
    if (plugin.status === 'error') {
      return {
        icon: XCircle,
        color: 'text-red-500',
        bg: 'bg-red-50 dark:bg-red-900/20',
        border: 'border-red-300 dark:border-red-800',
        label: 'Error'
      };
    }
    
    if (plugin.is_stale) {
      return {
        icon: Clock,
        color: 'text-yellow-500',
        bg: 'bg-yellow-50 dark:bg-yellow-900/20',
        border: 'border-yellow-300 dark:border-yellow-800',
        label: 'Stale'
      };
    }
    
    return {
      icon: CheckCircle,
      color: 'text-green-500',
      bg: 'bg-green-50 dark:bg-green-900/20',
      border: 'border-green-300 dark:border-green-800',
      label: 'Healthy'
    };
  };

  const categoryCounts = plugins.reduce((acc, p) => {
    acc[p.category] = (acc[p.category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Plugin Health
        </h3>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {plugins.filter(p => p.enabled).length}/{plugins.length} enabled
        </span>
      </div>

      {/* Category Summary */}
      <div className="mb-4 flex flex-wrap gap-2">
        {Object.entries(categoryCounts).map(([category, count]) => (
          <span
            key={category}
            className="px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
          >
            {category}: {count}
          </span>
        ))}
      </div>

      {/* Plugin Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {plugins.map((plugin) => {
          const config = getStatusConfig(plugin);
          const Icon = config.icon;
          
          return (
            <motion.div
              key={plugin.plugin_id}
              className={`${config.bg} ${config.border} border rounded-lg p-3 cursor-pointer`}
              whileHover={{ scale: 1.05 }}
              title={`${plugin.name}\nStatus: ${config.label}\nLast run: ${plugin.last_execution ? new Date(plugin.last_execution).toLocaleString() : 'Never'}`}
            >
              <div className="flex flex-col items-center text-center">
                <Icon className={`${config.color} w-6 h-6 mb-1`} />
                <p className="text-xs font-medium text-gray-900 dark:text-white truncate w-full">
                  {plugin.name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                  {config.label}
                </p>
              </div>
            </motion.div>
          );
        })}
      </div>

      {plugins.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          No plugins configured
        </div>
      )}
    </div>
  );
}
