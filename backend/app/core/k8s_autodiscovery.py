"""
Add to backend/app/services/ or backend/app/core/
"""

import os
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import KubernetesCluster

logger = logging.getLogger(__name__)


async def autodiscover_k8s_cluster(db: Session, tenant_id: str = "default"):
    """
    Auto-discover and register the Kubernetes cluster.
    Checks for:
    1. In-cluster service account (running inside K8s)
    2. Mounted kubeconfig file at /app/data/kubeconfig or /root/.kube/config
    """
    kubeconfig_path = None
    provider = "unknown"
    description = "Auto-discovered Kubernetes cluster"
    
    # 1. Check for in-cluster config
    if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
        logger.info("🔍 Detected in-cluster Kubernetes environment")
        kubeconfig_path = "in-cluster"
        provider = "in-cluster"
    
    # 2. Check for mounted kubeconfig (common mount points)
    elif os.path.exists("/app/data/kubeconfig"):
        logger.info("🔍 Detected mounted kubeconfig at /app/data/kubeconfig")
        kubeconfig_path = "/app/data/kubeconfig"
        provider = "imported"
        description = "Imported via /app/data/kubeconfig"
    
    elif os.path.exists("/root/.kube/config"):
        logger.info("🔍 Detected mounted kubeconfig at /root/.kube/config")
        kubeconfig_path = "/root/.kube/config"
        provider = "imported"
        description = "Imported via default location"

    if not kubeconfig_path:
        logger.info("Not running in Kubernetes and no kubeconfig found - skipping cluster auto-discovery")
        return None
    
    logger.info(f"Using kubeconfig: {kubeconfig_path}")
    
    try:
        # Check if cluster already registered
        existing = db.execute(
            select(KubernetesCluster).where(
                KubernetesCluster.tenant_id == tenant_id,
                # We'll match loosely on name 'local-cluster' or if the path matches
                ((KubernetesCluster.name == "local-cluster") | (KubernetesCluster.kubeconfig_path == kubeconfig_path))
            )
        ).scalar_one_or_none()
        
        if existing:
            logger.info(f"✅ Cluster already registered: {existing.name} (ID: {existing.id})")
            return existing
        
        # Get cluster name from environment or default
        cluster_name = os.getenv("CLUSTER_NAME", "local-cluster")
        
        # Create new cluster entry
        cluster = KubernetesCluster(
            tenant_id=tenant_id,
            name=cluster_name,
            description=description,
            kubeconfig_path=kubeconfig_path,
            is_active=True,
            is_default=True,
            provider=provider,
        )
        
        db.add(cluster)
        db.commit()
        db.refresh(cluster)
        
        logger.info(f"✅ Auto-registered Kubernetes cluster: {cluster.name} (ID: {cluster.id})")
        return cluster
        
    except Exception as e:
        logger.error(f"Failed to auto-discover Kubernetes cluster: {e}")
        db.rollback()
        return None
