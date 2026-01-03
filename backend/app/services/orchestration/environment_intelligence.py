"""
Environment Intelligence Service - Queries the k3s cluster to understand current state.
"""
import logging
from typing import Dict, List, Any, Optional
from kubernetes import client, config as k8s_config
from kubernetes.stream import stream
import os

logger = logging.getLogger(__name__)


class EnvironmentIntelligence:
    """Gathers information about the deployment environment."""
    
    def __init__(self):
        """Initialize Kubernetes client."""
        try:
            k8s_config.load_incluster_config()
        except:
            try:
                k8s_config.load_kube_config()
            except:
                logger.warning("Could not load Kubernetes config, some features will be limited")
        
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.storage_v1 = client.StorageV1Api()
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get overall cluster information."""
        try:
            nodes = self.v1.list_node()
            node_info = {
                "count": len(nodes.items),
                "nodes": []
            }
            
            total_cpu = 0
            total_memory = 0
            
            for node in nodes.items:
                cpu = node.status.allocatable.get("cpu", "0")
                memory = node.status.allocatable.get("memory", "0")
                
                # Parse CPU and memory
                cpu_value = self._parse_cpu(cpu)
                mem_value = self._parse_memory(memory)
                
                total_cpu += cpu_value
                total_memory += mem_value
                
                node_info["nodes"].append({
                    "name": node.metadata.name,
                    "cpu": cpu,
                    "memory": memory,
                    "status": node.status.conditions[-1].type if node.status.conditions else "Unknown"
                })
            
            return {
                "cluster": "k3s",
                "node_info": node_info,
                "total_cpu": total_cpu,
                "total_memory_gb": total_memory // 1024,
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"Error getting cluster info: {e}")
            return {"error": str(e)}
    
    def get_available_storage(self) -> Dict[str, Any]:
        """Get available storage classes and volumes."""
        try:
            pvcs = self.v1.list_persistent_volume_claim_for_all_namespaces()
            storage_classes = self.storage_v1.list_storage_class()
            
            pvc_usage = {}
            for pvc in pvcs.items:
                ns = pvc.metadata.namespace
                if ns not in pvc_usage:
                    pvc_usage[ns] = []
                
                pvc_usage[ns].append({
                    "name": pvc.metadata.name,
                    "size": pvc.spec.resources.requests.get("storage", "unknown") if pvc.spec.resources else "unknown",
                    "storage_class": pvc.spec.storage_class_name
                })
            
            return {
                "storage_classes": [sc.metadata.name for sc in storage_classes.items],
                "pvc_usage": pvc_usage,
                "recommended_size_gb": 20  # Default recommendation
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {"error": str(e)}
    
    def get_deployed_services(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Get information about deployed services."""
        try:
            if namespace:
                services = self.v1.list_namespaced_service(namespace)
            else:
                services = self.v1.list_service_for_all_namespaces()
            
            svc_info = {}
            for svc in services.items:
                ns = svc.metadata.namespace
                if ns not in svc_info:
                    svc_info[ns] = []
                
                ports = []
                if svc.spec.ports:
                    for port in svc.spec.ports:
                        ports.append({
                            "name": port.name,
                            "port": port.port,
                            "target_port": port.target_port
                        })
                
                svc_info[ns].append({
                    "name": svc.metadata.name,
                    "type": svc.spec.type,
                    "cluster_ip": svc.spec.cluster_ip,
                    "ports": ports
                })
            
            return svc_info
        except Exception as e:
            logger.error(f"Error getting services: {e}")
            return {"error": str(e)}
    
    def get_available_ports(self, namespace: str = "homelab") -> Dict[str, Any]:
        """Get available ports (commonly used ones)."""
        try:
            services = self.v1.list_namespaced_service(namespace)
            used_ports = set()
            
            for svc in services.items:
                if svc.spec.ports:
                    for port in svc.spec.ports:
                        if port.port:
                            used_ports.add(port.port)
            
            # Common ports to suggest
            all_ports = set(range(8000, 9000))  # Standard range
            available = list(all_ports - used_ports)[:10]
            
            return {
                "used_ports": sorted(list(used_ports)),
                "available_ports": sorted(available),
                "reserved_ports": [80, 443]  # Don't auto-assign these
            }
        except Exception as e:
            logger.error(f"Error getting available ports: {e}")
            return {"error": str(e)}
    
    def get_environment_summary(self, namespace: str = "homelab") -> Dict[str, Any]:
        """Get a summary of the environment for decision making."""
        cluster = self.get_cluster_info()
        storage = self.get_available_storage()
        ports = self.get_available_ports(namespace)
        
        return {
            "cluster": cluster,
            "storage": storage,
            "networking": ports,
            "ready_to_deploy": True,
            "recommendations": {
                "min_cpu": 1,
                "min_memory_gb": 2,
                "default_storage_gb": 20,
                "default_storage_class": "local-path"
            }
        }
    
    @staticmethod
    def _parse_cpu(cpu_str: str) -> int:
        """Parse CPU string (e.g., '4' or '4000m')."""
        if 'm' in cpu_str:
            return int(cpu_str.replace('m', '')) // 1000
        return int(cpu_str)
    
    @staticmethod
    def _parse_memory(mem_str: str) -> int:
        """Parse memory string (e.g., '8Gi' or '8000Mi')."""
        if 'Gi' in mem_str:
            return int(mem_str.replace('Gi', '')) * 1024
        elif 'Mi' in mem_str:
            return int(mem_str.replace('Mi', ''))
        return 0
