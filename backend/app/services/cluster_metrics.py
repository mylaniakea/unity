"""
Cluster Metrics Collection Service

Collects and stores metrics for Kubernetes clusters including:
- Cluster-level aggregated metrics
- Per-node resource usage
- Pod status counts
- Historical metrics queries
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models import KubernetesCluster, ClusterMetric, NodeMetric
from app.services.k8s_client import KubernetesClient, KubernetesClientError

logger = logging.getLogger(__name__)


def parse_resource_quantity(quantity_str: str) -> float:
    """
    Parse Kubernetes resource quantity string to numeric value.
    
    Examples:
        "1000m" -> 1.0 (CPU cores)
        "1000Mi" -> 1048576000 (bytes)
        "1Gi" -> 1073741824 (bytes)
    """
    if not quantity_str:
        return 0.0
    
    quantity_str = quantity_str.strip()
    
    # CPU millicores
    if quantity_str.endswith('m'):
        return float(quantity_str[:-1]) / 1000.0
    
    # Memory units
    units = {
        'Ki': 1024,
        'Mi': 1024**2,
        'Gi': 1024**3,
        'Ti': 1024**4,
        'K': 1000,
        'M': 1000**2,
        'G': 1000**3,
        'T': 1000**4,
    }
    
    for suffix, multiplier in units.items():
        if quantity_str.endswith(suffix):
            try:
                return float(quantity_str[:-len(suffix)]) * multiplier
            except ValueError:
                return 0.0
    
    # Plain number
    try:
        return float(quantity_str)
    except ValueError:
        return 0.0


class ClusterMetricsService:
    """Service for collecting and querying cluster metrics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def collect_cluster_metrics(self, cluster: KubernetesCluster) -> Optional[ClusterMetric]:
        """
        Collect and store metrics for a cluster.
        
        Args:
            cluster: KubernetesCluster model instance
            
        Returns:
            ClusterMetric instance if successful, None otherwise
        """
        try:
            client = KubernetesClient(
                kubeconfig_path=cluster.kubeconfig_path,
                context=cluster.context_name
            )
            
            # Get nodes
            nodes = await client.get_nodes()
            node_count = len(nodes)
            ready_nodes = sum(1 for n in nodes if n["status"] == "Ready")
            
            # Get all pods across all namespaces
            pods = await client.get_all_pods()
            pod_status_counts = self._count_pod_statuses(pods)
            
            # Calculate aggregated resource usage from nodes
            cpu_usage = 0.0
            cpu_capacity = 0.0
            memory_usage = 0
            memory_capacity = 0
            storage_usage = 0
            storage_capacity = 0
            
            for node in nodes:
                capacity = node.get("capacity", {})
                cpu_capacity += parse_resource_quantity(capacity.get("cpu", "0"))
                memory_capacity += int(parse_resource_quantity(capacity.get("memory", "0")))
                storage_capacity += int(parse_resource_quantity(capacity.get("ephemeral_storage", "0")))
            
            # Try to get metrics from metrics-server
            try:
                node_metrics = await client.get_node_metrics()
                for metric in node_metrics:
                    cpu_usage += parse_resource_quantity(metric.get("cpu_usage", "0"))
                    memory_usage += int(parse_resource_quantity(metric.get("memory_usage", "0")))
            except Exception as e:
                logger.warning(f"Could not get node metrics from metrics-server: {e}")
            
            # Get recent cluster events
            events = await client.get_cluster_events(minutes=5)
            event_counts = self._count_events_by_level(events)
            
            # Create and store metric
            metric = ClusterMetric(
                tenant_id=cluster.tenant_id,
                cluster_id=cluster.id,
                timestamp=datetime.utcnow(),
                total_nodes=node_count,
                ready_nodes=ready_nodes,
                total_pods=len(pods),
                running_pods=pod_status_counts.get("Running", 0),
                failed_pods=pod_status_counts.get("Failed", 0),
                pending_pods=pod_status_counts.get("Pending", 0),
                cpu_usage_cores=cpu_usage,
                cpu_capacity_cores=cpu_capacity,
                memory_usage_bytes=memory_usage,
                memory_capacity_bytes=memory_capacity,
                storage_usage_bytes=storage_usage,
                storage_capacity_bytes=storage_capacity,
                warning_events=event_counts.get("Warning", 0),
                error_events=event_counts.get("Error", 0)
            )
            
            self.db.add(metric)
            
            # Also collect per-node metrics
            await self._collect_node_metrics(cluster, nodes, client)
            
            self.db.commit()
            self.db.refresh(metric)
            
            logger.info(f"Collected metrics for cluster {cluster.name}: {node_count} nodes, {len(pods)} pods")
            return metric
            
        except KubernetesClientError as e:
            logger.error(f"Failed to collect metrics for cluster {cluster.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error collecting metrics for {cluster.name}: {e}", exc_info=True)
            return None
    
    async def _collect_node_metrics(self, cluster: KubernetesCluster, nodes: List[Dict], client: KubernetesClient):
        """Collect and store per-node metrics"""
        try:
            # Get metrics from metrics-server
            node_metrics_map = {}
            try:
                node_metrics_list = await client.get_node_metrics()
                for metric in node_metrics_list:
                    node_name = metric.get("node_name")
                    if node_name:
                        node_metrics_map[node_name] = metric
            except Exception:
                pass
            
            # Get pod counts per node
            pods = await client.get_all_pods()
            pod_counts = {}
            for pod in pods:
                node_name = pod.get("node_name")
                if node_name:
                    pod_counts[node_name] = pod_counts.get(node_name, 0) + 1
            
            timestamp = datetime.utcnow()
            
            for node in nodes:
                node_name = node["name"]
                capacity = node.get("capacity", {})
                node_info = node.get("node_info", {})
                
                # Get metrics if available
                metrics = node_metrics_map.get(node_name, {})
                
                node_metric = NodeMetric(
                    tenant_id=cluster.tenant_id,
                    cluster_id=cluster.id,
                    node_name=node_name,
                    timestamp=timestamp,
                    status=node["status"],
                    role=node["roles"][0] if node.get("roles") else "worker",
                    cpu_usage_cores=parse_resource_quantity(metrics.get("cpu_usage", "0")),
                    cpu_capacity_cores=parse_resource_quantity(capacity.get("cpu", "0")),
                    memory_usage_bytes=int(parse_resource_quantity(metrics.get("memory_usage", "0"))),
                    memory_capacity_bytes=int(parse_resource_quantity(capacity.get("memory", "0"))),
                    storage_usage_bytes=0,  # Not available from basic metrics
                    storage_capacity_bytes=int(parse_resource_quantity(capacity.get("ephemeral_storage", "0"))),
                    pod_count=pod_counts.get(node_name, 0),
                    pod_capacity=int(parse_resource_quantity(capacity.get("pods", "0"))),
                    kubelet_version=node_info.get("kubelet_version"),
                    os_image=node_info.get("os_image"),
                    kernel_version=node_info.get("kernel_version"),
                    container_runtime=node_info.get("container_runtime"),
                    architecture=node_info.get("architecture")
                )
                
                self.db.add(node_metric)
                
        except Exception as e:
            logger.error(f"Error collecting node metrics: {e}", exc_info=True)
    
    def _count_pod_statuses(self, pods: List[Dict]) -> Dict[str, int]:
        """Count pods by status"""
        counts = {}
        for pod in pods:
            phase = pod.get("phase", "Unknown")
            counts[phase] = counts.get(phase, 0) + 1
        return counts
    
    def _count_events_by_level(self, events: List[Dict]) -> Dict[str, int]:
        """Count events by type/level"""
        counts = {}
        for event in events:
            event_type = event.get("type", "Normal")
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts
    
    def get_cluster_metrics_history(
        self,
        cluster_id: int,
        hours: int = 24,
        limit: int = 100
    ) -> List[ClusterMetric]:
        """
        Query historical cluster metrics.
        
        Args:
            cluster_id: Cluster ID
            hours: How many hours back to query
            limit: Maximum number of metrics to return
            
        Returns:
            List of ClusterMetric instances
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = self.db.query(ClusterMetric).filter(
            and_(
                ClusterMetric.cluster_id == cluster_id,
                ClusterMetric.timestamp >= cutoff_time
            )
        ).order_by(desc(ClusterMetric.timestamp)).limit(limit).all()
        
        return metrics
    
    def get_node_metrics_history(
        self,
        cluster_id: int,
        node_name: str,
        hours: int = 24,
        limit: int = 100
    ) -> List[NodeMetric]:
        """
        Query historical node metrics.
        
        Args:
            cluster_id: Cluster ID
            node_name: Node name
            hours: How many hours back to query
            limit: Maximum number of metrics to return
            
        Returns:
            List of NodeMetric instances
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = self.db.query(NodeMetric).filter(
            and_(
                NodeMetric.cluster_id == cluster_id,
                NodeMetric.node_name == node_name,
                NodeMetric.timestamp >= cutoff_time
            )
        ).order_by(desc(NodeMetric.timestamp)).limit(limit).all()
        
        return metrics
    
    def get_latest_cluster_metric(self, cluster_id: int) -> Optional[ClusterMetric]:
        """Get the most recent metric for a cluster"""
        return self.db.query(ClusterMetric).filter(
            ClusterMetric.cluster_id == cluster_id
        ).order_by(desc(ClusterMetric.timestamp)).first()
    
    def cleanup_old_metrics(self, days: int = 7):
        """
        Delete metrics older than specified days.
        
        Args:
            days: Delete metrics older than this many days
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # Delete old cluster metrics
        cluster_deleted = self.db.query(ClusterMetric).filter(
            ClusterMetric.timestamp < cutoff_time
        ).delete()
        
        # Delete old node metrics
        node_deleted = self.db.query(NodeMetric).filter(
            NodeMetric.timestamp < cutoff_time
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Cleaned up {cluster_deleted} cluster metrics and {node_deleted} node metrics")
