"""Kubernetes runtime provider implementation."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import os

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    client = None
    config = None
    ApiException = Exception

from .provider import ContainerRuntimeProvider, RuntimeProviderFactory
import app.models as models

logger = logging.getLogger(__name__)


class KubernetesProvider(ContainerRuntimeProvider):
    """Kubernetes runtime provider using kubernetes Python client."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        
        if not KUBERNETES_AVAILABLE:
            logger.warning("kubernetes Python client is not installed. K8s support is disabled.")
        
        self._clients: Dict[int, tuple] = {}  # host_id -> (api_client, apps_v1, core_v1)
    
    async def connect(self, host_id: int) -> tuple:
        """Establish connection to Kubernetes cluster.
        
        Returns:
            Tuple of (api_client, apps_v1_api, core_v1_api)
        """
        if not KUBERNETES_AVAILABLE:
            raise RuntimeError("kubernetes client is not installed. Install with: pip install kubernetes")
        
        # Return cached client if available
        if host_id in self._clients:
            return self._clients[host_id]
        
        # Get host configuration from database
        host = self.db.query(models.ContainerHost).filter(
            models.ContainerHost.id == host_id
        ).first()
        
        if not host:
            raise ValueError(f"Container host with ID {host_id} not found")
        
        if not host.enabled:
            raise ValueError(f"Container host '{host.name}' is disabled")
        
        if host.runtime_type != "kubernetes":
            raise ValueError(f"Host {host_id} is not a Kubernetes host (type: {host.runtime_type})")
        
        # Create new client
        try:
            # Load kubeconfig
            if host.kubeconfig_path:
                config.load_kube_config(config_file=host.kubeconfig_path, context=host.context)
            else:
                # Try in-cluster config first, then default kubeconfig
                try:
                    config.load_incluster_config()
                except Exception:
                    config.load_kube_config(context=host.context)
            
            # Create API clients
            api_client = client.ApiClient()
            apps_v1 = client.AppsV1Api(api_client)
            core_v1 = client.CoreV1Api(api_client)
            
            # Test connection by getting server version
            version_api = client.VersionApi(api_client)
            version_api.get_code()
            
            # Cache the clients
            self._clients[host_id] = (api_client, apps_v1, core_v1)
            
            # Update host status
            host.last_seen = datetime.utcnow()
            host.status = "online"
            host.status_message = None
            self.db.commit()
            
            return self._clients[host_id]
            
        except Exception as e:
            logger.error(f"Failed to connect to Kubernetes host '{host.name}': {e}")
            host.status = "error"
            host.status_message = str(e)
            self.db.commit()
            raise
    
    async def get_host_info(self, host_id: int) -> Dict[str, Any]:
        """Get Kubernetes cluster information."""
        try:
            api_client, apps_v1, core_v1 = await self.connect(host_id)
            
            # Get version info
            version_api = client.VersionApi(api_client)
            version_info = version_api.get_code()
            
            # Get node information
            nodes = core_v1.list_node()
            total_cpus = 0
            total_memory = 0
            
            for node in nodes.items:
                capacity = node.status.capacity
                total_cpus += int(capacity.get('cpu', 0))
                # Memory is in Ki, convert to bytes
                mem_str = capacity.get('memory', '0Ki')
                if mem_str.endswith('Ki'):
                    total_memory += int(mem_str[:-2]) * 1024
            
            # Get host config for namespace
            host = self.db.query(models.ContainerHost).filter(
                models.ContainerHost.id == host_id
            ).first()
            namespace = host.namespace or "default"
            
            # Count resources in namespace
            pods = core_v1.list_namespaced_pod(namespace)
            deployments = apps_v1.list_namespaced_deployment(namespace)
            statefulsets = apps_v1.list_namespaced_stateful_set(namespace)
            daemonsets = apps_v1.list_namespaced_daemon_set(namespace)
            
            return {
                "runtime_type": "kubernetes",
                "k8s_version": version_info.git_version,
                "platform": version_info.platform,
                "nodes": len(nodes.items),
                "cpus": total_cpus,
                "memory": total_memory,
                "namespace": namespace,
                "pods": len(pods.items),
                "deployments": len(deployments.items),
                "statefulsets": len(statefulsets.items),
                "daemonsets": len(daemonsets.items),
            }
        except Exception as e:
            logger.error(f"Failed to get host info for host {host_id}: {e}")
            raise
    
    async def list_containers(self, host_id: int, all_containers: bool = True) -> List[Dict[str, Any]]:
        """List all workloads (Deployments, StatefulSets, DaemonSets) in the namespace."""
        try:
            api_client, apps_v1, core_v1 = await self.connect(host_id)
            
            host = self.db.query(models.ContainerHost).filter(
                models.ContainerHost.id == host_id
            ).first()
            namespace = host.namespace or "default"
            
            result = []
            
            # List Deployments
            deployments = apps_v1.list_namespaced_deployment(namespace)
            for deployment in deployments.items:
                containers = deployment.spec.template.spec.containers
                for container in containers:
                    result.append({
                        "id": f"deployment/{deployment.metadata.name}/{container.name}",
                        "short_id": f"{deployment.metadata.name[:8]}",
                        "name": f"{deployment.metadata.name}-{container.name}",
                        "image": container.image,
                        "status": "running" if deployment.status.ready_replicas else "pending",
                        "state": "running" if deployment.status.ready_replicas else "pending",
                        "created": deployment.metadata.creation_timestamp.isoformat() if deployment.metadata.creation_timestamp else None,
                        "labels": deployment.metadata.labels or {},
                        "ports": [{"containerPort": p.container_port, "protocol": p.protocol} for p in (container.ports or [])],
                        "workload_type": "deployment",
                        "replicas": deployment.spec.replicas,
                    })
            
            # List StatefulSets
            statefulsets = apps_v1.list_namespaced_stateful_set(namespace)
            for statefulset in statefulsets.items:
                containers = statefulset.spec.template.spec.containers
                for container in containers:
                    result.append({
                        "id": f"statefulset/{statefulset.metadata.name}/{container.name}",
                        "short_id": f"{statefulset.metadata.name[:8]}",
                        "name": f"{statefulset.metadata.name}-{container.name}",
                        "image": container.image,
                        "status": "running" if statefulset.status.ready_replicas else "pending",
                        "state": "running" if statefulset.status.ready_replicas else "pending",
                        "created": statefulset.metadata.creation_timestamp.isoformat() if statefulset.metadata.creation_timestamp else None,
                        "labels": statefulset.metadata.labels or {},
                        "ports": [{"containerPort": p.container_port, "protocol": p.protocol} for p in (container.ports or [])],
                        "workload_type": "statefulset",
                        "replicas": statefulset.spec.replicas,
                    })
            
            # List DaemonSets
            daemonsets = apps_v1.list_namespaced_daemon_set(namespace)
            for daemonset in daemonsets.items:
                containers = daemonset.spec.template.spec.containers
                for container in containers:
                    result.append({
                        "id": f"daemonset/{daemonset.metadata.name}/{container.name}",
                        "short_id": f"{daemonset.metadata.name[:8]}",
                        "name": f"{daemonset.metadata.name}-{container.name}",
                        "image": container.image,
                        "status": "running" if daemonset.status.number_ready else "pending",
                        "state": "running" if daemonset.status.number_ready else "pending",
                        "created": daemonset.metadata.creation_timestamp.isoformat() if daemonset.metadata.creation_timestamp else None,
                        "labels": daemonset.metadata.labels or {},
                        "ports": [{"containerPort": p.container_port, "protocol": p.protocol} for p in (container.ports or [])],
                        "workload_type": "daemonset",
                    })
            
            return result
        except Exception as e:
            logger.error(f"Failed to list workloads for host {host_id}: {e}")
            raise
    
    async def get_container_details(self, host_id: int, container_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific workload.
        
        container_id format: "workload_type/workload_name/container_name"
        """
        try:
            api_client, apps_v1, core_v1 = await self.connect(host_id)
            
            host = self.db.query(models.ContainerHost).filter(
                models.ContainerHost.id == host_id
            ).first()
            namespace = host.namespace or "default"
            
            # Parse container ID
            parts = container_id.split("/")
            if len(parts) != 3:
                raise ValueError(f"Invalid Kubernetes container ID format: {container_id}")
            
            workload_type, workload_name, container_name = parts
            
            # Get workload based on type
            if workload_type == "deployment":
                workload = apps_v1.read_namespaced_deployment(workload_name, namespace)
                spec = workload.spec.template.spec
            elif workload_type == "statefulset":
                workload = apps_v1.read_namespaced_stateful_set(workload_name, namespace)
                spec = workload.spec.template.spec
            elif workload_type == "daemonset":
                workload = apps_v1.read_namespaced_daemon_set(workload_name, namespace)
                spec = workload.spec.template.spec
            else:
                raise ValueError(f"Unsupported workload type: {workload_type}")
            
            # Find the specific container
            container = None
            for c in spec.containers:
                if c.name == container_name:
                    container = c
                    break
            
            if not container:
                raise ValueError(f"Container {container_name} not found in {workload_type}/{workload_name}")
            
            # Parse image
            image_parts = container.image.split(":")
            image_name = image_parts[0]
            image_tag = image_parts[1] if len(image_parts) > 1 else "latest"
            
            return {
                "id": container_id,
                "short_id": workload_name[:8],
                "name": f"{workload_name}-{container_name}",
                "image": image_name,
                "image_id": container.image,
                "tag": image_tag,
                "status": "running",
                "state": {"Status": "running"},
                "created": workload.metadata.creation_timestamp.isoformat() if workload.metadata.creation_timestamp else None,
                "started": None,
                "labels": workload.metadata.labels or {},
                "environment": [f"{e.name}={e.value}" for e in (container.env or []) if e.value],
                "ports": [{"containerPort": p.container_port, "protocol": p.protocol} for p in (container.ports or [])],
                "volumes": [{"name": v.name} for v in (spec.volumes or [])],
                "networks": [],
                "workload_type": workload_type,
                "namespace": namespace,
            }
        except Exception as e:
            logger.error(f"Failed to get workload details: {e}")
            raise
    
    async def pull_image(self, host_id: int, image: str, tag: str = "latest") -> bool:
        """Pull image - N/A for Kubernetes (images pulled by nodes automatically)."""
        logger.info(f"Image pulling is handled by Kubernetes nodes automatically for {image}:{tag}")
        return True
    
    async def create_container(
        self,
        host_id: int,
        image: str,
        name: str,
        config: Dict[str, Any]
    ) -> str:
        """Create a new Kubernetes deployment."""
        try:
            api_client, apps_v1, core_v1 = await self.connect(host_id)
            
            host = self.db.query(models.ContainerHost).filter(
                models.ContainerHost.id == host_id
            ).first()
            namespace = host.namespace or "default"
            
            # Extract config
            workload_type = config.get("workload_type", "deployment")
            replicas = config.get("replicas", 1)
            labels = config.get("labels", {"app": name})
            
            # Create container spec
            container_spec = client.V1Container(
                name=name,
                image=image,
                ports=[client.V1ContainerPort(container_port=p) for p in config.get("ports", [])]
            )
            
            # Create pod template
            pod_template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=labels),
                spec=client.V1PodSpec(containers=[container_spec])
            )
            
            if workload_type == "deployment":
                # Create deployment
                deployment = client.V1Deployment(
                    api_version="apps/v1",
                    kind="Deployment",
                    metadata=client.V1ObjectMeta(name=name, labels=labels),
                    spec=client.V1DeploymentSpec(
                        replicas=replicas,
                        selector=client.V1LabelSelector(match_labels=labels),
                        template=pod_template
                    )
                )
                
                result = apps_v1.create_namespaced_deployment(namespace, deployment)
                workload_id = f"deployment/{result.metadata.name}/{name}"
            else:
                raise ValueError(f"Unsupported workload type for creation: {workload_type}")
            
            logger.info(f"Created {workload_type} {name}")
            return workload_id
        except Exception as e:
            logger.error(f"Failed to create workload {name}: {e}")
            raise RuntimeError(f"Failed to create workload: {e}")
    
    async def start_container(self, host_id: int, container_id: str) -> bool:
        """Start container - N/A for Kubernetes (managed by controllers)."""
        logger.info(f"Container lifecycle is managed by Kubernetes controllers for {container_id}")
        return True
    
    async def stop_container(self, host_id: int, container_id: str, timeout: int = 10) -> bool:
        """Stop container - scale deployment to 0."""
        try:
            api_client, apps_v1, core_v1 = await self.connect(host_id)
            
            host = self.db.query(models.ContainerHost).filter(
                models.ContainerHost.id == host_id
            ).first()
            namespace = host.namespace or "default"
            
            parts = container_id.split("/")
            workload_type, workload_name = parts[0], parts[1]
            
            if workload_type == "deployment":
                # Scale to 0
                deployment = apps_v1.read_namespaced_deployment(workload_name, namespace)
                deployment.spec.replicas = 0
                apps_v1.patch_namespaced_deployment(workload_name, namespace, deployment)
            
            logger.info(f"Scaled down {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop {container_id}: {e}")
            raise
    
    async def remove_container(self, host_id: int, container_id: str, force: bool = False) -> bool:
        """Remove a Kubernetes workload."""
        try:
            api_client, apps_v1, core_v1 = await self.connect(host_id)
            
            host = self.db.query(models.ContainerHost).filter(
                models.ContainerHost.id == host_id
            ).first()
            namespace = host.namespace or "default"
            
            parts = container_id.split("/")
            workload_type, workload_name = parts[0], parts[1]
            
            if workload_type == "deployment":
                apps_v1.delete_namespaced_deployment(workload_name, namespace)
            elif workload_type == "statefulset":
                apps_v1.delete_namespaced_stateful_set(workload_name, namespace)
            elif workload_type == "daemonset":
                apps_v1.delete_namespaced_daemon_set(workload_name, namespace)
            
            logger.info(f"Deleted {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove {container_id}: {e}")
            raise
    
    async def rename_container(self, host_id: int, container_id: str, new_name: str) -> bool:
        """Rename container - not supported for Kubernetes workloads."""
        raise NotImplementedError("Renaming is not supported for Kubernetes workloads")
    
    async def get_logs(
        self,
        host_id: int,
        container_id: str,
        tail: Optional[int] = None,
        since: Optional[str] = None
    ) -> str:
        """Get logs from a Kubernetes pod."""
        try:
            api_client, apps_v1, core_v1 = await self.connect(host_id)
            
            host = self.db.query(models.ContainerHost).filter(
                models.ContainerHost.id == host_id
            ).first()
            namespace = host.namespace or "default"
            
            parts = container_id.split("/")
            workload_name, container_name = parts[1], parts[2]
            
            # Get pods for the workload
            pods = core_v1.list_namespaced_pod(
                namespace,
                label_selector=f"app={workload_name}"
            )
            
            if not pods.items:
                return "No pods found"
            
            # Get logs from first pod
            pod_name = pods.items[0].metadata.name
            logs = core_v1.read_namespaced_pod_log(
                pod_name,
                namespace,
                container=container_name,
                tail_lines=tail
            )
            
            return logs
        except Exception as e:
            logger.error(f"Failed to get logs for {container_id}: {e}")
            raise
    
    async def get_stats(self, host_id: int, container_id: str) -> Dict[str, Any]:
        """Get resource usage statistics - requires metrics-server."""
        logger.warning("Stats retrieval requires metrics-server to be installed in the cluster")
        return {
            "cpu_stats": {},
            "memory_stats": {},
            "networks": {},
        }
    
    def close_all(self):
        """Close all Kubernetes API client connections."""
        for api_client, _, _ in self._clients.values():
            try:
                api_client.close()
            except Exception as e:
                logger.error(f"Error closing Kubernetes client: {e}")
        self._clients.clear()


# Register Kubernetes provider with the factory (only if kubernetes client is available)
if KUBERNETES_AVAILABLE:
    RuntimeProviderFactory.register_provider("kubernetes", KubernetesProvider)
