import { AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

interface Alert {
  id: string;
  title: string;
  severity: 'critical' | 'warning' | 'info';
  status: string;
  triggered_at: string;
}

interface AlertSummary {
  total: number;
  unresolved: number;
  by_severity: {
    critical: number;
    warning: number;
    info: number;
  };
  recent_alerts: Alert[];
}

interface AlertStatusCardProps {
  alertSummary: AlertSummary | null;
  loading?: boolean;
}

export default function AlertStatusCard({ alertSummary, loading }: AlertStatusCardProps) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 animate-pulse">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
          <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
          <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  if (!alertSummary) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
          Alert Status
        </h3>
        <p className="text-gray-500 dark:text-gray-400">No alert data available</p>
      </div>
    );
  }

  const { by_severity, unresolved, recent_alerts } = alertSummary;

  const severityConfig = {
    critical: {
      icon: AlertTriangle,
      color: 'text-red-500',
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-200 dark:border-red-800'
    },
    warning: {
      icon: AlertCircle,
      color: 'text-yellow-500',
      bg: 'bg-yellow-50 dark:bg-yellow-900/20',
      border: 'border-yellow-200 dark:border-yellow-800'
    },
    info: {
      icon: Info,
      color: 'text-blue-500',
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      border: 'border-blue-200 dark:border-blue-800'
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Alert Status
        </h3>
        <button
          onClick={() => navigate('/alerts')}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          View all
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {Object.entries(by_severity).map(([severity, count]) => {
          const config = severityConfig[severity as keyof typeof severityConfig];
          const Icon = config.icon;
          return (
            <motion.div
              key={severity}
              className={`${config.bg} ${config.border} border rounded-lg p-3 text-center`}
              whileHover={{ scale: 1.05 }}
            >
              <Icon className={`${config.color} w-6 h-6 mx-auto mb-1`} />
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{count}</p>
              <p className="text-xs text-gray-600 dark:text-gray-400 capitalize">{severity}</p>
            </motion.div>
          );
        })}
      </div>

      {/* Total Unresolved */}
      <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">Total Unresolved</span>
          <span className="text-xl font-bold text-gray-900 dark:text-white">{unresolved}</span>
        </div>
      </div>

      {/* Recent Alerts */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Recent Alerts
        </h4>
        {recent_alerts && recent_alerts.length > 0 ? (
          <div className="space-y-2">
            {recent_alerts.slice(0, 5).map((alert) => {
              const config = severityConfig[alert.severity];
              const Icon = config.icon;
              return (
                <div
                  key={alert.id}
                  className="flex items-start space-x-2 p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
                  onClick={() => navigate('/alerts')}
                >
                  <Icon className={`${config.color} w-4 h-4 mt-0.5 flex-shrink-0`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900 dark:text-white truncate">
                      {alert.title}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {new Date(alert.triggered_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex items-center justify-center py-8 text-gray-500 dark:text-gray-400">
            <CheckCircle className="w-5 h-5 mr-2" />
            <span className="text-sm">No active alerts</span>
          </div>
        )}
      </div>
    </div>
  );
}
