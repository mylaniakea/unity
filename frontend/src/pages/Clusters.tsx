import { useState, useEffect } from 'react';
import { RefreshCw, Plus, Container, X, Globe, Link as LinkIcon, Info, Search } from 'lucide-react';
import { motion } from 'framer-motion';
import api from '@/api/client';
import ClusterCard from '@/components/ClusterCard';
import { useNotification } from '@/contexts/NotificationContext';
import { useRole } from '@/contexts/RoleContext';

interface K8sCluster {
  id: number;
  name: string;
  kubeconfig_path?: string;
  is_active: boolean;
  last_sync?: string;
  health_status?: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  node_count?: number;
  namespace_count?: number;
}

interface DockerHost {
  id: number;
  name: string;
  host_url: string;
  is_active: boolean;
  container_count?: number;
  health_status?: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
}

export default function Clusters() {
  const [k8sClusters, setK8sClusters] = useState<K8sCluster[]>([]);
  const [dockerHosts, setDockerHosts] = useState<DockerHost[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [showAddK8sModal, setShowAddK8sModal] = useState(false);
  const [showAddDockerModal, setShowAddDockerModal] = useState(false);
  const [showEditK8sModal, setShowEditK8sModal] = useState(false);
  const [showEditDockerModal, setShowEditDockerModal] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedCluster, setSelectedCluster] = useState<K8sCluster | null>(null);
  const [selectedHost, setSelectedHost] = useState<DockerHost | null>(null);
  const [detailsType, setDetailsType] = useState<'k8s' | 'docker' | null>(null);
  
  const { isAdmin } = useRole();
  const { showNotification } = useNotification();

  const fetchClusters = async () => {
    try {
      const [k8sRes, dockerRes] = await Promise.all([
        api.get('/k8s/clusters'),
        api.get('/docker/hosts')
      ]);
      
      const k8sData = k8sRes.data?.clusters || k8sRes.data || [];
      const dockerData = dockerRes.data?.hosts || dockerRes.data || [];
      
      setK8sClusters(Array.isArray(k8sData) ? k8sData : []);
      setDockerHosts(Array.isArray(dockerData) ? dockerData : []);
    } catch (error) {
      console.error('Failed to fetch clusters:', error);
      showNotification('Failed to fetch infrastructure data', 'error');
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

  const handleScan = async () => {
    setScanning(true);
    try {
      const res = await api.post('/system/scan');
      showNotification(`Scan complete. Docker: ${res.data.docker}, K8s: ${res.data.kubernetes}`, 'success');
      await fetchClusters();
    } catch (error) {
      console.error('Scan failed:', error);
      showNotification('Failed to scan local environment', 'error');
    } finally {
      setScanning(false);
    }
  };

  if (loading) {
  
  const handleDeleteK8sCluster = async (cluster: K8sCluster) => {
    if (!window.confirm(`Delete Kubernetes cluster "${cluster.name}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(`/k8s/clusters/${cluster.id}`);
      showNotification(`Cluster "${cluster.name}" deleted successfully`, 'success');
      fetchClusters();
    } catch (error: any) {
      console.error('Failed to delete cluster', error);
      showNotification(error.response?.data?.detail || 'Failed to delete cluster', 'error');
    }
  };

  const handleDeleteDockerHost = async (host: DockerHost) => {
    if (!window.confirm(`Delete Docker host "${host.name}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(`/docker/hosts/${host.id}`);
      showNotification(`Docker host "${host.name}" deleted successfully`, 'success');
      fetchClusters();
    } catch (error: any) {
      console.error('Failed to delete Docker host', error);
      showNotification(error.response?.data?.detail || 'Failed to delete Docker host', 'error');
    }
  };

  const handleViewDetails = (item: K8sCluster | DockerHost, type: 'k8s' | 'docker') => {
    if (type === 'k8s') {
      setSelectedCluster(item as K8sCluster);
    } else {
      setSelectedHost(item as DockerHost);
    }
    setDetailsType(type);
    setShowDetailsModal(true);
  };

  return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center space-y-4">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-muted-foreground">Loading Infrastructure...</p>
        </div>
      </div>
    );
  }


  const handleDeleteK8sCluster = async (cluster: K8sCluster) => {
    if (!window.confirm(`Delete Kubernetes cluster "${cluster.name}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(`/k8s/clusters/${cluster.id}`);
      showNotification(`Cluster "${cluster.name}" deleted successfully`, 'success');
      fetchClusters();
    } catch (error: any) {
      console.error('Failed to delete cluster', error);
      showNotification(error.response?.data?.detail || 'Failed to delete cluster', 'error');
    }
  };

  const handleDeleteDockerHost = async (host: DockerHost) => {
    if (!window.confirm(`Delete Docker host "${host.name}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(`/docker/hosts/${host.id}`);
      showNotification(`Docker host "${host.name}" deleted successfully`, 'success');
      fetchClusters();
    } catch (error: any) {
      console.error('Failed to delete Docker host', error);
      showNotification(error.response?.data?.detail || 'Failed to delete Docker host', 'error');
    }
  };

  const handleViewDetails = (item: K8sCluster | DockerHost, type: 'k8s' | 'docker') => {
    if (type === 'k8s') {
      setSelectedCluster(item as K8sCluster);
    } else {
      setSelectedHost(item as DockerHost);
    }
    setDetailsType(type);
    setShowDetailsModal(true);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            Infrastructure Clusters
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage your Kubernetes clusters and Docker hosts
          </p>
        </div>
        <div className="flex space-x-2">
          {isAdmin && (
            <button
              onClick={handleScan}
              disabled={scanning || refreshing}
              className="flex items-center space-x-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              <Search className={`w-4 h-4 ${scanning ? 'animate-pulse' : ''}`} />
              <span>{scanning ? 'Scanning...' : 'Scan Local'}</span>
            </button>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center space-x-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Kubernetes Clusters */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-semibold text-foreground flex items-center space-x-2">
            <Container className="w-6 h-6" />
            <span>Kubernetes Clusters</span>
          </h2>
          {isAdmin && (
            <button 
              onClick={() => setShowAddK8sModal(true)}
              className="flex items-center space-x-2 px-4 py-2 border border-border rounded-lg hover:bg-muted/50 transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Add Cluster</span>
            </button>
          )}
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
                hostUrl={cluster.kubeconfig_path}
                onViewDetails={() => handleViewDetails(cluster, 'k8s')}
                onEdit={isAdmin ? () => {
                  setSelectedCluster(cluster);
                  setShowEditK8sModal(true);
                } : undefined}
                onDelete={isAdmin ? () => handleDeleteK8sCluster(cluster) : undefined}
              />
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-card border-2 border-dashed border-border rounded-xl p-8 text-center"
          >
            <Container className="w-12 h-12 mx-auto text-gray-400 mb-3" />
            <h3 className="text-lg font-medium text-foreground mb-2">
              No Kubernetes clusters configured
            </h3>
            <p className="text-muted-foreground mb-4">
              Add your first Kubernetes cluster to start managing your workloads
            </p>
            {isAdmin && (
              <button 
                onClick={() => setShowAddK8sModal(true)}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors shadow-sm"
              >
                <Plus className="w-4 h-4" />
                <span>Add Cluster</span>
              </button>
            )}
          </motion.div>
        )}
      </div>

      {/* Docker Hosts */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-semibold text-foreground flex items-center space-x-2">
            <Container className="w-6 h-6" />
            <span>Docker Hosts</span>
          </h2>
          {isAdmin && (
            <button 
              onClick={() => setShowAddDockerModal(true)}
              className="flex items-center space-x-2 px-4 py-2 border border-border rounded-lg hover:bg-muted/50 transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Add Host</span>
            </button>
          )}
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
                hostUrl={host.host_url}
                onViewDetails={() => handleViewDetails(host, 'docker')}
                onEdit={isAdmin ? () => {
                  setSelectedHost(host);
                  setShowEditDockerModal(true);
                } : undefined}
                onDelete={isAdmin ? () => handleDeleteDockerHost(host) : undefined}
              />
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-card border-2 border-dashed border-border rounded-xl p-8 text-center"
          >
            <Container className="w-12 h-12 mx-auto text-gray-400 mb-3" />
            <h3 className="text-lg font-medium text-foreground mb-2">
              No Docker hosts configured
            </h3>
            <p className="text-muted-foreground mb-4">
              Add Docker hosts to monitor containers and services
            </p>
            {isAdmin && (
              <button 
                onClick={() => setShowAddDockerModal(true)}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors shadow-sm"
              >
                <Plus className="w-4 h-4" />
                <span>Add Host</span>
              </button>
            )}
          </motion.div>
        )}
      </div>

      {/* Modals */}
      {showAddK8sModal && (
        <AddK8sClusterModal
          onClose={() => setShowAddK8sModal(false)}
          onSuccess={() => {
            setShowAddK8sModal(false);
            fetchClusters();
          }}
        />
      )}

      {showAddDockerModal && (
        <AddDockerHostModal
          onClose={() => setShowAddDockerModal(false)}
          onSuccess={() => {
            setShowAddDockerModal(false);
            fetchClusters();
          }}
        />
      )}

      {showEditK8sModal && selectedCluster && (
        <EditK8sClusterModal
          cluster={selectedCluster}
          onClose={() => {
            setShowEditK8sModal(false);
            setSelectedCluster(null);
          }}
          onSuccess={fetchClusters}
        />
      )}

      {showEditDockerModal && selectedHost && (
        <EditDockerHostModal
          host={selectedHost}
          onClose={() => {
            setShowEditDockerModal(false);
            setSelectedHost(null);
          }}
          onSuccess={fetchClusters}
        />
      )}

      {showDetailsModal && (
        <DetailsModal
          item={detailsType === "k8s" ? selectedCluster : selectedHost}
          type={detailsType}
          onClose={() => {
            setShowDetailsModal(false);
            setSelectedCluster(null);
            setSelectedHost(null);
            setDetailsType(null);
          }}
        />
      )}
    </div>
  );
}

function AddK8sClusterModal({ onClose, onSuccess }: { onClose: () => void, onSuccess: () => void }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [kubeconfigPath, setKubeconfigPath] = useState('');
  const [contextName, setContextName] = useState('');
  const [loading, setLoading] = useState(false);
  const { showNotification } = useNotification();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post('/k8s/clusters', {
        name,
        description,
        kubeconfig_path: kubeconfigPath || null,
        context_name: contextName || null,
        is_active: true
      });
      showNotification('Kubernetes cluster added successfully', 'success');
      onSuccess();
    } catch (error: any) {
      showNotification(error.response?.data?.detail || 'Failed to add cluster', 'error');
    } finally {
      setLoading(false);
    }
  };


  const handleDeleteK8sCluster = async (cluster: K8sCluster) => {
    if (!window.confirm(`Delete Kubernetes cluster "${cluster.name}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(`/k8s/clusters/${cluster.id}`);
      showNotification(`Cluster "${cluster.name}" deleted successfully`, 'success');
      fetchClusters();
    } catch (error: any) {
      console.error('Failed to delete cluster', error);
      showNotification(error.response?.data?.detail || 'Failed to delete cluster', 'error');
    }
  };

  const handleDeleteDockerHost = async (host: DockerHost) => {
    if (!window.confirm(`Delete Docker host "${host.name}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(`/docker/hosts/${host.id}`);
      showNotification(`Docker host "${host.name}" deleted successfully`, 'success');
      fetchClusters();
    } catch (error: any) {
      console.error('Failed to delete Docker host', error);
      showNotification(error.response?.data?.detail || 'Failed to delete Docker host', 'error');
    }
  };

  const handleViewDetails = (item: K8sCluster | DockerHost, type: 'k8s' | 'docker') => {
    if (type === 'k8s') {
      setSelectedCluster(item as K8sCluster);
    } else {
      setSelectedHost(item as DockerHost);
    }
    setDetailsType(type);
    setShowDetailsModal(true);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-card border border-border rounded-xl shadow-lg p-6 w-full max-w-md shadow-2xl"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Globe className="w-6 h-6 text-blue-500" />
            Add K8s Cluster
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-muted/50 rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Cluster Name *</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production Cluster"
              className="w-full bg-muted/30 border border-border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Primary Kubernetes cluster"
              className="w-full bg-muted/30 border border-border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Kubeconfig Path</label>
            <input
              type="text"
              value={kubeconfigPath}
              onChange={(e) => setKubeconfigPath(e.target.value)}
              placeholder="/home/user/.kube/config"
              className="w-full bg-muted/30 border border-border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
            />
            <p className="text-xs text-gray-500 flex items-center gap-1">
              <Info className="w-3 h-3" />
              Path relative to the backend container
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Context Name</label>
            <input
              type="text"
              value={contextName}
              onChange={(e) => setContextName(e.target.value)}
              placeholder="default"
              className="w-full bg-muted/30 border border-border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-sm"
            >
              {loading ? 'Adding...' : 'Add Cluster'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

function AddDockerHostModal({ onClose, onSuccess }: { onClose: () => void, onSuccess: () => void }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [hostUrl, setHostUrl] = useState('unix:///var/run/docker.sock');
  const [loading, setLoading] = useState(false);
  const { showNotification } = useNotification();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post('/docker/hosts', {
        name,
        description,
        host_url: hostUrl,
        is_active: true
      });
      showNotification('Docker host added successfully', 'success');
      onSuccess();
    } catch (error: any) {
      showNotification(error.response?.data?.detail || 'Failed to add Docker host', 'error');
    } finally {
      setLoading(false);
    }
  };


  const handleDeleteK8sCluster = async (cluster: K8sCluster) => {
    if (!window.confirm(`Delete Kubernetes cluster "${cluster.name}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(`/k8s/clusters/${cluster.id}`);
      showNotification(`Cluster "${cluster.name}" deleted successfully`, 'success');
      fetchClusters();
    } catch (error: any) {
      console.error('Failed to delete cluster', error);
      showNotification(error.response?.data?.detail || 'Failed to delete cluster', 'error');
    }
  };

  const handleDeleteDockerHost = async (host: DockerHost) => {
    if (!window.confirm(`Delete Docker host "${host.name}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(`/docker/hosts/${host.id}`);
      showNotification(`Docker host "${host.name}" deleted successfully`, 'success');
      fetchClusters();
    } catch (error: any) {
      console.error('Failed to delete Docker host', error);
      showNotification(error.response?.data?.detail || 'Failed to delete Docker host', 'error');
    }
  };

  const handleViewDetails = (item: K8sCluster | DockerHost, type: 'k8s' | 'docker') => {
    if (type === 'k8s') {
      setSelectedCluster(item as K8sCluster);
    } else {
      setSelectedHost(item as DockerHost);
    }
    setDetailsType(type);
    setShowDetailsModal(true);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-card border border-border rounded-xl shadow-lg p-6 w-full max-w-md shadow-2xl"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Container className="w-6 h-6 text-blue-500" />
            Add Docker Host
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-muted/50 rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Host Name *</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Local Machine"
              className="w-full bg-muted/30 border border-border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Development machine"
              className="w-full bg-muted/30 border border-border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Host URL *</label>
            <div className="relative">
              <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                required
                value={hostUrl}
                onChange={(e) => setHostUrl(e.target.value)}
                placeholder="unix:///var/run/docker.sock"
                className="w-full bg-muted/30 border border-border rounded-lg pl-10 pr-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
            <p className="text-xs text-gray-500 flex items-center gap-1">
              <Info className="w-3 h-3" />
              Use tcp://ip:port for remote hosts
            </p>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-sm"
            >
              {loading ? 'Adding...' : 'Add Host'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

// Edit K8s Cluster Modal
function EditK8sClusterModal({ cluster, onClose, onSuccess }: { cluster: K8sCluster, onClose: () => void, onSuccess: () => void }) {
  const { showNotification } = useNotification();
  const [name, setName] = useState(cluster.name);
  const [description, setDescription] = useState(cluster.description || '');
  const [kubeconfigPath, setKubeconfigPath] = useState(cluster.kubeconfig_path || '');
  const [contextName, setContextName] = useState(cluster.context_name || '');
  const [isActive, setIsActive] = useState(cluster.is_active);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await api.put(`/k8s/clusters/${cluster.id}`, {
        name,
        description,
        kubeconfig_path: kubeconfigPath,
        context_name: contextName,
        is_active: isActive,
      });

      showNotification(`Cluster "${name}" updated successfully`, 'success');
      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Failed to update cluster', error);
      showNotification(error.response?.data?.detail || 'Failed to update cluster', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-card rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto"
      >
        <div className="p-6">
          <h2 className="text-2xl font-bold mb-6 text-foreground">Edit Kubernetes Cluster</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2 text-foreground">Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-foreground">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                rows={3}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-foreground">Kubeconfig Path</label>
              <input
                type="text"
                value={kubeconfigPath}
                onChange={(e) => setKubeconfigPath(e.target.value)}
                placeholder="/path/to/kubeconfig"
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-foreground">Context Name</label>
              <input
                type="text"
                value={contextName}
                onChange={(e) => setContextName(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="rounded"
              />
              <label className="text-sm font-medium text-foreground">Active</label>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 shadow-sm"
              >
                {loading ? 'Updating...' : 'Update Cluster'}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 bg-muted border border-border text-foreground rounded-lg hover:bg-muted/50 shadow-sm"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </motion.div>
    </div>
  );
}

// Edit Docker Host Modal
function EditDockerHostModal({ host, onClose, onSuccess }: { host: DockerHost, onClose: () => void, onSuccess: () => void }) {
  const { showNotification } = useNotification();
  const [name, setName] = useState(host.name);
  const [description, setDescription] = useState(host.description || '');
  const [hostUrl, setHostUrl] = useState(host.host_url);
  const [isActive, setIsActive] = useState(host.is_active);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await api.put(`/docker/hosts/${host.id}`, {
        name,
        description,
        host_url: hostUrl,
        is_active: isActive,
      });

      showNotification(`Docker host "${name}" updated successfully`, 'success');
      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Failed to update Docker host', error);
      showNotification(error.response?.data?.detail || 'Failed to update Docker host', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-card rounded-lg shadow-xl max-w-md w-full"
      >
        <div className="p-6">
          <h2 className="text-2xl font-bold mb-6 text-foreground">Edit Docker Host</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2 text-foreground">Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-foreground">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                rows={3}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-foreground">Host URL *</label>
              <input
                type="text"
                value={hostUrl}
                onChange={(e) => setHostUrl(e.target.value)}
                required
                placeholder="unix:///var/run/docker.sock or tcp://host:2375"
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="rounded"
              />
              <label className="text-sm font-medium text-foreground">Active</label>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 shadow-sm"
              >
                {loading ? 'Updating...' : 'Update Host'}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 bg-muted border border-border text-foreground rounded-lg hover:bg-muted/50 shadow-sm"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </motion.div>
    </div>
  );
}

// Details Modal
function DetailsModal({ item, type, onClose }: { item: K8sCluster | DockerHost | null, type: 'k8s' | 'docker' | null, onClose: () => void }) {
  if (!item || !type) return null;

  const isK8s = type === 'k8s';
  const k8sItem = isK8s ? (item as K8sCluster) : null;
  const dockerItem = !isK8s ? (item as DockerHost) : null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
      >
        <div className="p-6">
          <h2 className="text-2xl font-bold mb-6 text-foreground">{item.name} - Details</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">Type</label>
              <p className="text-lg text-foreground">{isK8s ? 'Kubernetes Cluster' : 'Docker Host'}</p>
            </div>

            {item.description && (
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">Description</label>
                <p className="text-foreground">{item.description}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">Status</label>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-1 rounded text-sm ${item.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'}`}>
                  {item.is_active ? 'Active' : 'Inactive'}
                </span>
                {item.health_status && (
                  <span className={`px-2 py-1 rounded text-sm ${
                    item.health_status === 'healthy' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                    item.health_status === 'degraded' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                    item.health_status === 'unhealthy' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                    'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
                  }`}>
                    {item.health_status}
                  </span>
                )}
              </div>
            </div>

            {isK8s && k8sItem && (
              <>
                {k8sItem.kubeconfig_path && (
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-1">Kubeconfig Path</label>
                    <p className="font-mono text-sm bg-muted/30 px-3 py-2 rounded text-foreground">{k8sItem.kubeconfig_path}</p>
                  </div>
                )}
                {k8sItem.context_name && (
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-1">Context Name</label>
                    <p className="font-mono text-sm text-foreground">{k8sItem.context_name}</p>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  {k8sItem.node_count !== undefined && (
                    <div>
                      <label className="block text-sm font-medium text-muted-foreground mb-1">Nodes</label>
                      <p className="text-2xl font-bold text-foreground">{k8sItem.node_count}</p>
                    </div>
                  )}
                  {k8sItem.namespace_count !== undefined && (
                    <div>
                      <label className="block text-sm font-medium text-muted-foreground mb-1">Namespaces</label>
                      <p className="text-2xl font-bold text-foreground">{k8sItem.namespace_count}</p>
                    </div>
                  )}
                </div>
              </>
            )}

            {!isK8s && dockerItem && (
              <>
                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">Host URL</label>
                  <p className="font-mono text-sm bg-muted/30 px-3 py-2 rounded break-all text-foreground">{dockerItem.host_url}</p>
                  {dockerItem.host_url.includes('unix:///var/run/docker.sock') && (
                    <p className="text-xs text-green-600 dark:text-green-400 mt-1">✓ Local Docker socket</p>
                  )}
                </div>
                {dockerItem.container_count !== undefined && (
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-1">Containers</label>
                    <p className="text-2xl font-bold text-foreground">{dockerItem.container_count}</p>
                  </div>
                )}
              </>
            )}

            {item.last_sync && (
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">Last Sync</label>
                <p className="text-foreground">{new Date(item.last_sync).toLocaleString()}</p>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-6 mt-6 border-t border-border">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 shadow-sm"
            >
              Close
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
