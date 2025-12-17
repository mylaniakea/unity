"""Kubernetes namespace management utilities."""

import logging
from typing import List, Set
from kubernetes import client

logger = logging.getLogger(__name__)


class NamespaceManager:
    """Manages namespace discovery and filtering for Kubernetes."""
    
    def __init__(self, core_v1_api: client.CoreV1Api):
        self.core_v1 = core_v1_api
    
    def get_namespaces_to_scan(
        self,
        namespaces_config: List[str],
        namespace_selector: str = None,
        namespace_exclude: List[str] = None
    ) -> Set[str]:
        """Get the list of namespaces to scan based on configuration.
        
        Args:
            namespaces_config: List of namespace names or ["*"] for all
            namespace_selector: Label selector for filtering namespaces
            namespace_exclude: List of namespaces to exclude
            
        Returns:
            Set of namespace names to scan
        """
        namespace_exclude = namespace_exclude or []
        
        # If wildcard, get all namespaces
        if "*" in namespaces_config:
            all_namespaces = self._get_all_namespaces(namespace_selector)
            return set(all_namespaces) - set(namespace_exclude)
        
        # Otherwise use explicit list, filtering out excludes
        return set(namespaces_config) - set(namespace_exclude)
    
    def _get_all_namespaces(self, label_selector: str = None) -> List[str]:
        """Get all namespace names in the cluster.
        
        Args:
            label_selector: Optional label selector to filter namespaces
            
        Returns:
            List of namespace names
        """
        try:
            if label_selector:
                namespaces = self.core_v1.list_namespace(label_selector=label_selector)
            else:
                namespaces = self.core_v1.list_namespace()
            
            return [ns.metadata.name for ns in namespaces.items]
        except Exception as e:
            logger.error(f"Failed to list namespaces: {e}")
            return ["default"]  # Fallback to default namespace
    
    def detect_helm_release(self, namespace: str, labels: dict) -> dict:
        """Detect if a workload is managed by Helm.
        
        Args:
            namespace: Namespace to check
            labels: Workload labels
            
        Returns:
            Dict with helm_release, helm_chart, helm_chart_version, or empty dict
        """
        helm_info = {}
        
        # Check for Helm v3 labels
        if "app.kubernetes.io/managed-by" in labels and labels["app.kubernetes.io/managed-by"] == "Helm":
            helm_info["helm_release"] = labels.get("app.kubernetes.io/instance", labels.get("release"))
            helm_info["helm_chart"] = labels.get("app.kubernetes.io/name", labels.get("chart"))
            helm_info["helm_chart_version"] = labels.get("app.kubernetes.io/version", labels.get("heritage"))
            
            # Try to get revision from secrets
            if helm_info.get("helm_release"):
                try:
                    secrets = self.core_v1.list_namespaced_secret(
                        namespace,
                        label_selector=f"owner=helm,name={helm_info['helm_release']}"
                    )
                    if secrets.items:
                        # Get the latest revision
                        revisions = [int(s.metadata.labels.get("version", 0)) for s in secrets.items]
                        helm_info["helm_revision"] = max(revisions) if revisions else None
                except Exception as e:
                    logger.debug(f"Could not get Helm revision: {e}")
        
        return helm_info
