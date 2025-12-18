"""
Kubernetes Monitor Plugin

Monitors Kubernetes clusters running at home.
"I run Kubernetes at home" - Said with pride and exhaustion!
"""

import subprocess
import json
from datetime import datetime, timezone
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class KubernetesMonitorPlugin(PluginBase):
    """Monitors Kubernetes clusters"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="kubernetes-monitor",
            name="Kubernetes Monitor",
            version="1.0.0",
            description="Monitors Kubernetes cluster health including nodes, pods, services, and resource usage",
            author="Unity Team",
            category=PluginCategory.CONTAINER,
            tags=["kubernetes", "k8s", "containers", "orchestration", "pods"],
            requires_sudo=False,
            supported_os=["linux", "darwin"],
            dependencies=[],  # Uses kubectl
            config_schema={
                "type": "object",
                "properties": {
                    "kubeconfig": {
                        "type": "string",
                        "description": "Path to kubeconfig file"
                    },
                    "context": {
                        "type": "string",
                        "description": "Kubernetes context to use"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect Kubernetes metrics"""
        
        config = self.config or {}
        kubeconfig = config.get("kubeconfig")
        context = config.get("context")
        
        try:
            # Build kubectl command base
            kubectl_base = ["kubectl"]
            if kubeconfig:
                kubectl_base.extend(["--kubeconfig", kubeconfig])
            if context:
                kubectl_base.extend(["--context", context])
            
            # Get nodes
            nodes_result = subprocess.run(
                kubectl_base + ["get", "nodes", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            nodes_result.raise_for_status()
            nodes_data = json.loads(nodes_result.stdout)
            
            # Get pods
            pods_result = subprocess.run(
                kubectl_base + ["get", "pods", "--all-namespaces", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            pods_result.raise_for_status()
            pods_data = json.loads(pods_result.stdout)
            
            # Parse nodes
            nodes = []
            for node in nodes_data.get("items", []):
                status = node.get("status", {})
                conditions = {c["type"]: c["status"] for c in status.get("conditions", [])}
                
                nodes.append({
                    "name": node.get("metadata", {}).get("name"),
                    "ready": conditions.get("Ready") == "True",
                    "version": status.get("nodeInfo", {}).get("kubeletVersion"),
                    "os": status.get("nodeInfo", {}).get("osImage"),
                    "capacity_cpu": status.get("capacity", {}).get("cpu"),
                    "capacity_memory": status.get("capacity", {}).get("memory")
                })
            
            # Parse pods
            pod_stats = {"Running": 0, "Pending": 0, "Failed": 0, "Succeeded": 0}
            pods_by_namespace = {}
            
            for pod in pods_data.get("items", []):
                phase = pod.get("status", {}).get("phase", "Unknown")
                if phase in pod_stats:
                    pod_stats[phase] += 1
                
                namespace = pod.get("metadata", {}).get("namespace", "default")
                pods_by_namespace[namespace] = pods_by_namespace.get(namespace, 0) + 1
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_nodes": len(nodes),
                    "ready_nodes": sum(1 for n in nodes if n["ready"]),
                    "total_pods": len(pods_data.get("items", [])),
                    "running_pods": pod_stats["Running"],
                    "pending_pods": pod_stats["Pending"],
                    "failed_pods": pod_stats["Failed"],
                    "namespaces": len(pods_by_namespace)
                },
                "nodes": nodes,
                "pod_stats": pod_stats,
                "pods_by_namespace": pods_by_namespace
            }
            
        except FileNotFoundError:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "kubectl command not found"
            }
        except subprocess.CalledProcessError as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"kubectl error: {e.stderr if e.stderr else str(e)}"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def health_check(self) -> bool:
        try:
            result = subprocess.run(["kubectl", "version", "--client"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True  # All config is optional
