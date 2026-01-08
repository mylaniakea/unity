import { useState, useEffect } from 'react';
import { RefreshCw, Plus, Container } from 'lucide-react';
import { motion } from 'framer-motion';
import api from '@/api/client';
import ClusterCard from '@/components/ClusterCard';

interface K8sCluster {
  id: number;
  name: string;
  kubeconfig_path?: string;
  is_active: boolean;
  last_sync?: string;
  health_status?: 'healthy' | 'degraded' | 'unhealthy';
  node_count?: number;
  namespace_count?: number;
}

interface DockerHost {
  id: number;
  name: string;
  host_url: string;
  is_active: boolean;
  container_count?: number;
  health_status?: 'healthy' | 'degraded' | 'unhealthy';
}

export default function Clusters() {
  const [k8sClusters, setK8sClusters] = useState<K8sCluster[]>([]);
  const [dockerHosts, setDockerHosts] = useState<DockerHost[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchClusters = async () => {
    try {
      const [k8sRes, dockerRes] = await Promise.all([
        api.get('/k8s/clusters'),
        api.get('/docker/hosts')
      ]);
      
      setK8sClusters(k8sRes.data.clusters || k8sRes.data || []);
      setDockerHosts(dockerRes.data || []);
    } catch (error) {
      console.error('Failed to fetch clusters:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchClusters();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchClusters();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center space-y-4">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-gray-600 dark:text-gray-400">Loading Infrastructure...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Infrastructure Clusters
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage your Kubernetes clusters and Docker hosts
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Kubernetes Clusters */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
            <Container className="w-6 h-6" />
            <span>Kubernetes Clusters</span>
          </h2>
          <button className="flex items-center space-x-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            <Plus className="w-4 h-4" />
            <span>Add Cluster</span>
          </button>
        </div>

        {k8sClusters.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {k8sClusters.map((cluster) => (
              <ClusterCard
                key={cluster.id}
                name={cluster.name}
                type="kubernetes"
                healthStatus={cluster.health_status || 'unknown'}
                isActive={cluster.is_active}
                metrics={{
                  nodes: cluster.node_count,
                  namespaces: cluster.namespace_count
                }}
                lastSync={cluster.last_sync}
                onViewDetails={() => {
                  // TODO: Navigate to cluster details
                  console.log('View details for', cluster.name);
                }}
              />
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-gray-50 dark:bg-gray-800 rounded-lg p-8 text-center border-2 border-dashed border-gray-300 dark:border-gray-700"
          >
            <Container className="w-12 h-12 mx-auto text-gray-400 mb-3" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No Kubernetes clusters configured
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Add your first Kubernetes cluster to start managing your workloads
            </p>
            <button className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              <Plus className="w-4 h-4" />
              <span>Add Cluster</span>
            </button>
          </motion.div>
        )}
      </div>

      {/* Docker Hosts */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
            <Container className="w-6 h-6" />
            <span>Docker Hosts</span>
          </h2>
          <button className="flex items-center space-x-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            <Plus className="w-4 h-4" />
            <span>Add Host</span>
          </button>
        </div>

        {dockerHosts.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {dockerHosts.map((host) => (
              <ClusterCard
                key={host.id}
                name={host.name}
                type="docker"
                healthStatus={host.health_status || 'unknown'}
                isActive={host.is_active}
                metrics={{
                  containers: host.container_count
                }}
                onViewDetails={() => {
                  // TODO: Navigate to host details
                  console.log('View details for', host.name);
                }}
              />
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-gray-50 dark:bg-gray-800 rounded-lg p-8 text-center border-2 border-dashed border-gray-300 dark:border-gray-700"
          >
            <Container className="w-12 h-12 mx-auto text-gray-400 mb-3" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No Docker hosts configured
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Add Docker hosts to monitor containers and services
            </p>
            <button className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              <Plus className="w-4 h-4" />
              <span>Add Host</span>
            </button>
          </motion.div>
        )}
      </div>
    </div>
  );
}
