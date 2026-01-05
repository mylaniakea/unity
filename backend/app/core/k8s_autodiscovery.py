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
    Auto-discover and register the Kubernetes cluster if running inside one.
    Checks for in-cluster service account and registers if found.
    """
    # Check if running in Kubernetes
    if not os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
        logger.info("Not running in Kubernetes - skipping cluster auto-discovery")
        return None
    
    logger.info("🔍 Detected Kubernetes environment - auto-discovering cluster...")
    
    try:
        # Check if cluster already registered
        existing = db.execute(
            select(KubernetesCluster).where(
                KubernetesCluster.tenant_id == tenant_id,
                KubernetesCluster.name == "local-cluster"
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
            description="Auto-discovered local Kubernetes cluster",
            kubeconfig_path="in-cluster",  # Special marker for in-cluster config
            is_active=True,
            is_default=True,
            provider="k3s",  # Can be detected or set via env var
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
