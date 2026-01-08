"""
Kubernetes Cluster Management API

Provides RESTful endpoints for managing Kubernetes cluster connections
and monitoring cluster health.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime

from app.core.dependencies import get_tenant_id
from app.database import get_db
from app.models import KubernetesCluster, KubernetesResource, User
from app.services.auth import get_current_active_user
from app.schemas_k8s import (
    KubernetesClusterCreate,
    KubernetesClusterUpdate,
    KubernetesClusterInfo,
    KubernetesClusterDetail,
    KubernetesClusterListResponse,
    KubernetesClusterHealthResponse,
    KubernetesActionResponse
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/k8s/clusters",
    tags=["kubernetes-clusters"],
    responses={404: {"description": "Not found"}},
)


async def check_cluster_health(cluster: KubernetesCluster) -> dict:
    """
    Check the health of a Kubernetes cluster.

    This function attempts to connect to the cluster and verify its status.
    In a production environment, this would use the Kubernetes Python client.
    """
    try:
        # TODO: Implement actual K8s cluster health check using kubernetes client
        # For now, return a mock response
        return {
            "healthy": True,
            "health_status": "healthy",
            "message": "Cluster is reachable and responding",
            "cluster_version": cluster.cluster_version or "unknown",
            "node_count": 0,
            "namespace_count": 0,
            "details": {}
        }
    except Exception as e:
        logger.error(f"Error checking cluster health for {cluster.name}: {e}")
        return {
            "healthy": False,
            "health_status": "unhealthy",
            "message": f"Failed to connect to cluster: {str(e)}",
            "cluster_version": None,
            "node_count": None,
            "namespace_count": None,
            "details": {"error": str(e)}
        }


@router.post("", response_model=KubernetesClusterDetail, status_code=201)
async def create_cluster(
    cluster_data: KubernetesClusterCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Register a new Kubernetes cluster.

    **Authentication:** JWT token required
    **Authorization:** Admin only
    """
    # Check authorization
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can register clusters"
        )

    # Check if cluster with same name already exists
    existing = db.execute(
        select(KubernetesCluster).where(KubernetesCluster.tenant_id == tenant_id, KubernetesCluster.name == cluster_data.name)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Cluster with name '{cluster_data.name}' already exists"
        )

    # If this is set as default, unset any existing default
    if cluster_data.is_default:
        db.execute(
            select(KubernetesCluster).where(KubernetesCluster.is_default == True)
        )
        for cluster in db.execute(select(KubernetesCluster)).scalars():
            cluster.is_default = False

    # Create new cluster
    cluster = KubernetesCluster(
        tenant_id=tenant_id,
        name=cluster_data.name,
        description=cluster_data.description,
        kubeconfig_path=cluster_data.kubeconfig_path,
        api_server_url=cluster_data.api_server_url,
        context_name=cluster_data.context_name,
        provider=cluster_data.provider,
        is_default=cluster_data.is_default,
        is_active=cluster_data.is_active,
        config=cluster_data.config,
        labels=cluster_data.labels,
        created_by=current_user.id
    )

    db.add(cluster)
    db.commit()
    db.refresh(cluster)

    logger.info(f"Cluster '{cluster.name}' registered by user {current_user.username}")

    return cluster


@router.get("", response_model=KubernetesClusterListResponse)
async def list_clusters(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    List all registered Kubernetes clusters.

    **Authentication:** JWT token required
    **Authorization:** All authenticated users
    """
    query = select(KubernetesCluster).where(KubernetesCluster.tenant_id == tenant_id)

    # Apply filters
    if is_active is not None:
        query = query.where(KubernetesCluster.is_active == is_active)
    if provider:
        query = query.where(KubernetesCluster.provider == provider)

    query = query.order_by(KubernetesCluster.is_default.desc(), KubernetesCluster.name)

    result = db.execute(query)
    clusters = result.scalars().all()

    # Get resource count for each cluster
    cluster_infos = []
    for cluster in clusters:
        resource_count = db.execute(
            select(func.count(KubernetesResource.id)).where(
                KubernetesResource.cluster_id == cluster.id
            )
        ).scalar()

        cluster_info = KubernetesClusterInfo.from_orm(cluster)
        cluster_info.resource_count = resource_count
        cluster_infos.append(cluster_info)

    return KubernetesClusterListResponse(
        clusters=cluster_infos,
        total=len(cluster_infos)
    )


@router.get("/{cluster_id}", response_model=KubernetesClusterDetail)
async def get_cluster(
    cluster_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get detailed information about a specific cluster.

    **Authentication:** JWT token required
    **Authorization:** All authenticated users
    """
    cluster = db.execute(
        select(KubernetesCluster).where(KubernetesCluster.id == cluster_id, KubernetesCluster.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not cluster:
        raise HTTPException(
            status_code=404,
            detail=f"Cluster with id {cluster_id} not found"
        )

    # Update last accessed timestamp
    cluster.last_accessed = datetime.utcnow()
    db.commit()

    return cluster


@router.put("/{cluster_id}", response_model=KubernetesClusterDetail)
async def update_cluster(
    cluster_id: int,
    cluster_data: KubernetesClusterUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Update a Kubernetes cluster.

    **Authentication:** JWT token required
    **Authorization:** Admin only
    """
    # Check authorization
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can update clusters"
        )

    cluster = db.execute(
        select(KubernetesCluster).where(KubernetesCluster.id == cluster_id, KubernetesCluster.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not cluster:
        raise HTTPException(
            status_code=404,
            detail=f"Cluster with id {cluster_id} not found"
        )

    # Check if name is being changed and conflicts with another cluster
    if cluster_data.name and cluster_data.name != cluster.name:
        existing = db.execute(
            select(KubernetesCluster).where(KubernetesCluster.tenant_id == tenant_id, KubernetesCluster.name == cluster_data.name)
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Cluster with name '{cluster_data.name}' already exists"
            )

    # If setting as default, unset any existing default
    if cluster_data.is_default:
        for c in db.execute(select(KubernetesCluster)).scalars():
            if c.id != cluster_id:
                c.is_default = False

    # Update fields
    update_data = cluster_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cluster, key, value)

    cluster.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cluster)

    logger.info(f"Cluster '{cluster.name}' updated by user {current_user.username}")

    return cluster


@router.delete("/{cluster_id}", response_model=KubernetesActionResponse)
async def delete_cluster(
    cluster_id: int,
    force: bool = Query(False, description="Force delete even if resources exist"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove a Kubernetes cluster.

    **Authentication:** JWT token required
    **Authorization:** Admin only
    """
    # Check authorization
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can delete clusters"
        )

    cluster = db.execute(
        select(KubernetesCluster).where(KubernetesCluster.id == cluster_id, KubernetesCluster.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not cluster:
        raise HTTPException(
            status_code=404,
            detail=f"Cluster with id {cluster_id} not found"
        )

    # Check for associated resources
    resource_count = db.execute(
        select(func.count(KubernetesResource.id)).where(
            KubernetesResource.cluster_id == cluster_id
        )
    ).scalar()

    if resource_count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Cluster has {resource_count} associated resources. Use force=true to delete anyway."
        )

    cluster_name = cluster.name
    db.delete(cluster)
    db.commit()

    logger.info(f"Cluster '{cluster_name}' deleted by user {current_user.username}")

    return KubernetesActionResponse(
        success=True,
        message=f"Cluster '{cluster_name}' deleted successfully",
        cluster_id=cluster_id,
        details={"resource_count_deleted": resource_count if force else 0}
    )


@router.get("/{cluster_id}/health", response_model=KubernetesClusterHealthResponse)
async def check_cluster_health_endpoint(
    cluster_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Check cluster connectivity and health status.

    **Authentication:** JWT token required
    **Authorization:** All authenticated users
    """
    cluster = db.execute(
        select(KubernetesCluster).where(KubernetesCluster.id == cluster_id, KubernetesCluster.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not cluster:
        raise HTTPException(
            status_code=404,
            detail=f"Cluster with id {cluster_id} not found"
        )

    # Perform health check
    health_result = await check_cluster_health(cluster)

    # Update cluster health status
    cluster.last_health_check = datetime.utcnow()
    cluster.health_status = health_result["health_status"]
    cluster.health_message = health_result["message"]
    if health_result.get("cluster_version"):
        cluster.cluster_version = health_result["cluster_version"]

    db.commit()

    return KubernetesClusterHealthResponse(
        cluster_id=cluster.id,
        cluster_name=cluster.name,
        healthy=health_result["healthy"],
        health_status=health_result["health_status"],
        message=health_result["message"],
        cluster_version=health_result.get("cluster_version"),
        node_count=health_result.get("node_count"),
        namespace_count=health_result.get("namespace_count"),
        details=health_result.get("details"),
        checked_at=cluster.last_health_check
    )
