import { Server, Activity, CheckCircle, AlertCircle, XCircle, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';

interface ClusterCardProps {
  name: string;
  type: 'kubernetes' | 'docker';
  healthStatus: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  isActive: boolean;
  metrics?: {
    nodes?: number;
    namespaces?: number;
    containers?: number;
    services?: number;
  };
  lastSync?: string;
  onViewDetails?: () => void;
}

const ClusterCard = ({
  name,
  type,
  healthStatus,
  isActive,
  metrics,
  lastSync,
  onViewDetails
}: ClusterCardProps) => {
  const getHealthIcon = () => {
    switch (healthStatus) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'degraded':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      case 'unhealthy':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Activity className="w-5 h-5 text-gray-400" />;
    }
  };

  const getHealthBadgeColor = () => {
    switch (healthStatus) {
      case 'healthy':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'unhealthy':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 rounded-lg shadow-md hover:shadow-lg transition-all duration-200 overflow-hidden border border-gray-200 dark:border-gray-700"
    >
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <Server className="w-6 h-6 text-blue-600 dark:text-blue-300" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {name}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 capitalize">
                {type}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {getHealthIcon()}
            <span
              className={`px-2 py-1 text-xs font-medium rounded-full ${getHealthBadgeColor()}`}
            >
              {healthStatus}
            </span>
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="p-6">
        <div className="grid grid-cols-2 gap-4">
          {metrics?.nodes !== undefined && (
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Nodes</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {metrics.nodes}
              </p>
            </div>
          )}
          {metrics?.namespaces !== undefined && (
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Namespaces</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {metrics.namespaces}
              </p>
            </div>
          )}
          {metrics?.containers !== undefined && (
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Containers</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {metrics.containers}
              </p>
            </div>
          )}
          {metrics?.services !== undefined && (
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Services</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {metrics.services}
              </p>
            </div>
          )}
        </div>

        {/* Status and Last Sync */}
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500 dark:text-gray-400">Status:</span>
            <span
              className={`font-medium ${
                isActive
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
            >
              {isActive ? 'Active' : 'Inactive'}
            </span>
          </div>
          {lastSync && (
            <div className="flex items-center justify-between text-sm mt-2">
              <span className="text-gray-500 dark:text-gray-400">Last Sync:</span>
              <span className="text-gray-900 dark:text-white">
                {new Date(lastSync).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      {onViewDetails && (
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onViewDetails}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
          >
            <span>View Details</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </motion.div>
  );
};

export default ClusterCard;
