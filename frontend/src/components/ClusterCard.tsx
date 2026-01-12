import { Server, Activity, CheckCircle, AlertCircle, XCircle, ChevronRight, Edit, Trash2 } from 'lucide-react';
import { motion } from 'framer-motion';

interface ClusterCardProps {
  name: string;
  type: 'kubernetes' | 'docker';
  healthStatus?: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  isActive: boolean;
  metrics?: {
    nodes?: number;
    namespaces?: number;
    containers?: number;
    services?: number;
  };
  lastSync?: string;
  onViewDetails?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  hostUrl?: string;
}

const ClusterCard = ({
  name,
  type,
  healthStatus = 'unknown',
  isActive,
  metrics,
  lastSync,
  onViewDetails,
  onEdit,
  onDelete,
  hostUrl
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
        return 'bg-green-500/10 text-green-500 border border-green-500/20';
      case 'degraded':
        return 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20';
      case 'unhealthy':
        return 'bg-red-500/10 text-red-500 border border-red-500/20';
      default:
        return 'bg-muted/50 text-muted-foreground border border-border';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-card border border-border rounded-xl shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden"
    >
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Server className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                {name}
              </h3>
              <p className="text-sm text-muted-foreground capitalize">
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
              <p className="text-sm text-muted-foreground">Nodes</p>
              <p className="text-2xl font-bold text-foreground">
                {metrics.nodes}
              </p>
            </div>
          )}
          {metrics?.namespaces !== undefined && (
            <div>
              <p className="text-sm text-muted-foreground">Namespaces</p>
              <p className="text-2xl font-bold text-foreground">
                {metrics.namespaces}
              </p>
            </div>
          )}
          {metrics?.containers !== undefined && (
            <div>
              <p className="text-sm text-muted-foreground">Containers</p>
              <p className="text-2xl font-bold text-foreground">
                {metrics.containers}
              </p>
            </div>
          )}
          {metrics?.services !== undefined && (
            <div>
              <p className="text-sm text-muted-foreground">Services</p>
              <p className="text-2xl font-bold text-foreground">
                {metrics.services}
              </p>
            </div>
          )}
        </div>

        {/* Status */}
        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Status</span>
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium ${
                isActive
                  ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                  : 'bg-muted/50 text-muted-foreground border border-border'
              }`}
            >
              {isActive ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>

        {/* Host URL */}
        {hostUrl && (
          <div className="mt-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Host</span>
              <span className="text-xs text-foreground/70 truncate max-w-[200px]" title={hostUrl}>
                {hostUrl}
              </span>
            </div>
            {hostUrl.includes('unix:///var/run/docker.sock') && (
              <span className="text-xs text-green-500">✓ Local Docker socket</span>
            )}
          </div>
        )}

        {/* Last Sync */}
        {lastSync && (
          <div className="mt-2 text-xs text-muted-foreground">
            Last sync: {new Date(lastSync).toLocaleString()}
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="px-6 py-4 bg-muted/30 border-t border-border">
        <div className="flex items-center justify-between gap-2">
          <div className="flex gap-2">
            {onEdit && (
              <button
                onClick={onEdit}
                className="p-2 text-primary hover:bg-primary/10 rounded-md transition-colors"
                title="Edit"
              >
                <Edit size={16} />
              </button>
            )}
            {onDelete && (
              <button
                onClick={onDelete}
                className="p-2 text-destructive hover:bg-destructive/10 rounded-md transition-colors"
                title="Delete"
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
          {onViewDetails && (
            <button
              onClick={onViewDetails}
              className="flex items-center space-x-1 px-3 py-2 text-sm font-medium text-primary hover:bg-primary/10 rounded-md transition-colors"
            >
              <span>View Details</span>
              <ChevronRight size={16} />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default ClusterCard;
