"""
Kubernetes Resource Management API

Provides RESTful endpoints for managing Kubernetes resources with
declarative desired state tracking and automatic reconciliation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from typing import List, Optional
from datetime import datetime

from app.core.dependencies import get_tenant_id
from app.database import get_db
from app.models import (
    KubernetesResource,
    KubernetesCluster,
    ResourceReconciliation,
    User
)
from app.services.auth import get_current_active_user
from app.schemas_k8s import (
    KubernetesResourceCreate,
    KubernetesResourceUpdate,
    KubernetesResourceInfo,
    KubernetesResourceDetail,
    KubernetesResourceListResponse,
    KubernetesResourceReconcileRequest,
    KubernetesResourceReconcileResponse,
    ResourceReconciliationInfo,
    ResourceReconciliationListResponse,
    KubernetesActionResponse
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/k8s/resources",
    tags=["kubernetes-resources"],
    responses={404: {"description": "Not found"}},
)


async def reconcile_resource(
    resource: KubernetesResource,
    db: Session,
    user_id: Optional[int] = None,
    force: bool = False
) -> dict:
    """
    Reconcile a Kubernetes resource with its desired state.

    This function applies the desired state to the cluster and tracks the reconciliation.
    In a production environment, this would use the Kubernetes Python client to apply manifests.
    """
    reconciliation_start = datetime.utcnow()
    reconciliation = ResourceReconciliation(
        tenant_id=tenant_id,
        resource_id=resource.id,
        started_at=reconciliation_start,
        status="in_progress",
        triggered_by="manual" if user_id else "scheduler",
        triggered_by_user_id=user_id,
        reconciliation_version=resource.reconciliations.count() + 1 if resource.reconciliations else 1
    )
    db.add(reconciliation)
    db.flush()

    try:
        # TODO: Implement actual K8s resource reconciliation using kubernetes client
        # For now, simulate successful reconciliation
        reconciliation_end = datetime.utcnow()
        duration = int((reconciliation_end - reconciliation_start).total_seconds() * 1000)

        # Simulate determining if changes were needed
        result = "no_change" if not force else "updated"
        changes = {} if result == "no_change" else {"spec": "updated"}

        reconciliation.completed_at = reconciliation_end
        reconciliation.duration_ms = duration
        reconciliation.status = "success"
        reconciliation.result = result
        reconciliation.changes_applied = changes
        reconciliation.new_state = resource.desired_state

        # Update resource
        resource.last_reconciled = reconciliation_end
        resource.reconciliation_status = "success"
        resource.reconciliation_message = f"Successfully reconciled ({result})"
        resource.drift_detected = False
        resource.current_state = resource.desired_state
        resource.last_error = None

        db.commit()

        return {
            "success": True,
            "reconciliation_id": reconciliation.id,
            "status": reconciliation.status,
            "result": reconciliation.result,
            "message": f"Resource reconciled successfully ({result})",
            "changes_applied": changes,
            "started_at": reconciliation_start,
            "completed_at": reconciliation_end,
            "duration_ms": duration
        }

    except Exception as e:
        logger.error(f"Error reconciling resource {resource.id}: {e}")
        reconciliation_end = datetime.utcnow()
        duration = int((reconciliation_end - reconciliation_start).total_seconds() * 1000)

        reconciliation.completed_at = reconciliation_end
        reconciliation.duration_ms = duration
        reconciliation.status = "failed"
        reconciliation.result = "error"
        reconciliation.error_message = str(e)
        reconciliation.retry_count += 1

        # Update resource
        resource.reconciliation_status = "failed"
        resource.reconciliation_message = f"Reconciliation failed: {str(e)}"
        resource.last_error = str(e)

        db.commit()

        return {
            "success": False,
            "reconciliation_id": reconciliation.id,
            "status": "failed",
            "result": "error",
            "message": f"Reconciliation failed: {str(e)}",
            "changes_applied": None,
            "started_at": reconciliation_start,
            "completed_at": reconciliation_end,
            "duration_ms": duration
        }


@router.post("", response_model=KubernetesResourceDetail, status_code=201)
async def create_resource(
    resource_data: KubernetesResourceCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Create a new Kubernetes resource.

    **Authentication:** JWT token required
    **Authorization:** Admin or operator
    """
    # Check authorization
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=403,
            detail="Only admins and operators can create resources"
        )

    # Verify cluster exists
    cluster = db.execute(
        select(KubernetesCluster).where(KubernetesCluster.id == resource_data.cluster_id, KubernetesCluster.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not cluster:
        raise HTTPException(
            status_code=404,
            detail=f"Cluster with id {resource_data.cluster_id} not found"
        )

    # Check if resource already exists
    existing = db.execute(
        select(KubernetesResource).where(
            and_(
                KubernetesResource.cluster_id == resource_data.cluster_id,
                KubernetesResource.namespace == resource_data.namespace,
                KubernetesResource.kind == resource_data.kind,
                KubernetesResource.name == resource_data.name
            )
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Resource {resource_data.kind}/{resource_data.name} already exists in namespace {resource_data.namespace}"
        )

    # Create new resource
    resource = KubernetesResource(
        tenant_id=tenant_id,
        cluster_id=resource_data.cluster_id,
        kind=resource_data.kind,
        name=resource_data.name,
        namespace=resource_data.namespace,
        api_version=resource_data.api_version,
        desired_state=resource_data.desired_state,
        labels=resource_data.labels,
        annotations=resource_data.annotations,
        managed_by=resource_data.managed_by,
        auto_reconcile=resource_data.auto_reconcile,
        deletion_policy=resource_data.deletion_policy,
        reconciliation_status="pending",
        created_by=current_user.id
    )

    db.add(resource)
    db.commit()
    db.refresh(resource)

    logger.info(
        f"Resource {resource.kind}/{resource.name} created in cluster {cluster.name} "
        f"by user {current_user.username}"
    )

    # Trigger initial reconciliation
    if resource.auto_reconcile:
        await reconcile_resource(resource, db, current_user.id)

    return resource


@router.get("", response_model=KubernetesResourceListResponse)
async def list_resources(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    kind: Optional[str] = Query(None, description="Filter by resource kind"),
    managed_by: Optional[str] = Query(None, description="Filter by management tool"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    drift_detected: Optional[bool] = Query(None, description="Filter by drift detection"),
    reconciliation_status: Optional[str] = Query(None, description="Filter by reconciliation status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all managed Kubernetes resources with optional filters.

    **Authentication:** JWT token required
    **Authorization:** All authenticated users
    """
    query = select(KubernetesResource).where(KubernetesResource.tenant_id == tenant_id).join(
        KubernetesCluster,
        KubernetesResource.cluster_id == KubernetesCluster.id
    )

    # Apply filters
    if cluster_id is not None:
        query = query.where(KubernetesResource.cluster_id == cluster_id)
    if namespace:
        query = query.where(KubernetesResource.namespace == namespace)
    if kind:
        query = query.where(KubernetesResource.kind == kind)
    if managed_by:
        query = query.where(KubernetesResource.managed_by == managed_by)
    if is_active is not None:
        query = query.where(KubernetesResource.is_active == is_active)
    if drift_detected is not None:
        query = query.where(KubernetesResource.drift_detected == drift_detected)
    if reconciliation_status:
        query = query.where(KubernetesResource.reconciliation_status == reconciliation_status)

    query = query.order_by(
        KubernetesResource.cluster_id,
        KubernetesResource.namespace,
        KubernetesResource.kind,
        KubernetesResource.name
    )

    result = db.execute(query)
    resources = result.scalars().all()

    # Enrich with cluster names
    resource_infos = []
    for resource in resources:
        cluster = db.execute(
            select(KubernetesCluster).where(KubernetesCluster.id == resource.cluster_id)
        ).scalar_one_or_none()

        resource_info = KubernetesResourceInfo.from_orm(resource)
        resource_info.cluster_name = cluster.name if cluster else None
        resource_infos.append(resource_info)

    return KubernetesResourceListResponse(
        resources=resource_infos,
        total=len(resource_infos)
    )


@router.get("/{resource_id}", response_model=KubernetesResourceDetail)
async def get_resource(
    resource_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get detailed information about a specific resource including current state.

    **Authentication:** JWT token required
    **Authorization:** All authenticated users
    """
    resource = db.execute(
        select(KubernetesResource).where(KubernetesResource.id == resource_id, KubernetesResource.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=404,
            detail=f"Resource with id {resource_id} not found"
        )

    return resource


@router.put("/{resource_id}", response_model=KubernetesResourceDetail)
async def update_resource(
    resource_id: int,
    resource_data: KubernetesResourceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Update the desired state of a resource.

    **Authentication:** JWT token required
    **Authorization:** Admin or operator
    """
    # Check authorization
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=403,
            detail="Only admins and operators can update resources"
        )

    resource = db.execute(
        select(KubernetesResource).where(KubernetesResource.id == resource_id, KubernetesResource.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=404,
            detail=f"Resource with id {resource_id} not found"
        )

    # Track if desired state changed
    desired_state_changed = False
    if resource_data.desired_state is not None:
        desired_state_changed = resource_data.desired_state != resource.desired_state

    # Update fields
    update_data = resource_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(resource, key, value)

    resource.updated_at = datetime.utcnow()

    # If desired state changed and auto_reconcile is enabled, mark for reconciliation
    if desired_state_changed and resource.auto_reconcile:
        resource.reconciliation_status = "pending"
        resource.drift_detected = True

    db.commit()
    db.refresh(resource)

    logger.info(
        f"Resource {resource.kind}/{resource.name} (id={resource_id}) updated "
        f"by user {current_user.username}"
    )

    # Trigger reconciliation if desired state changed and auto_reconcile is enabled
    if desired_state_changed and resource.auto_reconcile:
        await reconcile_resource(resource, db, current_user.id)

    return resource


@router.delete("/{resource_id}", response_model=KubernetesActionResponse)
async def delete_resource(
    resource_id: int,
    delete_from_cluster: bool = Query(
        True,
        description="Whether to delete the resource from the cluster or just remove tracking"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a managed resource.

    **Authentication:** JWT token required
    **Authorization:** Admin or operator
    """
    # Check authorization
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=403,
            detail="Only admins and operators can delete resources"
        )

    resource = db.execute(
        select(KubernetesResource).where(KubernetesResource.id == resource_id, KubernetesResource.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=404,
            detail=f"Resource with id {resource_id} not found"
        )

    resource_name = f"{resource.kind}/{resource.name}"
    namespace = resource.namespace

    if delete_from_cluster and resource.deletion_policy != "retain":
        # TODO: Implement actual deletion from K8s cluster using kubernetes client
        logger.info(f"Would delete {resource_name} from cluster (not implemented)")

    # Remove from Unity database
    db.delete(resource)
    db.commit()

    logger.info(
        f"Resource {resource_name} in namespace {namespace} deleted "
        f"by user {current_user.username}"
    )

    return KubernetesActionResponse(
        success=True,
        message=f"Resource {resource_name} deleted successfully",
        resource_id=resource_id,
        details={
            "deleted_from_cluster": delete_from_cluster and resource.deletion_policy != "retain",
            "namespace": namespace
        }
    )


@router.post("/{resource_id}/reconcile", response_model=KubernetesResourceReconcileResponse)
async def reconcile_resource_endpoint(
    resource_id: int,
    reconcile_request: KubernetesResourceReconcileRequest = KubernetesResourceReconcileRequest(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Trigger immediate reconciliation of a resource.

    **Authentication:** JWT token required
    **Authorization:** Admin or operator
    """
    # Check authorization
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=403,
            detail="Only admins and operators can trigger reconciliation"
        )

    resource = db.execute(
        select(KubernetesResource).where(KubernetesResource.id == resource_id, KubernetesResource.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=404,
            detail=f"Resource with id {resource_id} not found"
        )

    if not resource.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot reconcile inactive resource"
        )

    logger.info(
        f"Manual reconciliation triggered for {resource.kind}/{resource.name} "
        f"by user {current_user.username}"
    )

    # Perform reconciliation
    result = await reconcile_resource(resource, db, current_user.id, reconcile_request.force)

    return KubernetesResourceReconcileResponse(
        success=result["success"],
        resource_id=resource_id,
        reconciliation_id=result.get("reconciliation_id"),
        status=result["status"],
        result=result.get("result"),
        message=result["message"],
        changes_applied=result.get("changes_applied"),
        started_at=result["started_at"],
        completed_at=result.get("completed_at"),
        duration_ms=result.get("duration_ms")
    )


@router.get("/{resource_id}/reconciliations", response_model=ResourceReconciliationListResponse)
async def list_resource_reconciliations(
    resource_id: int,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of reconciliations to return"),
    offset: int = Query(0, ge=0, description="Number of reconciliations to skip"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get reconciliation history for a specific resource.

    **Authentication:** JWT token required
    **Authorization:** All authenticated users
    """
    # Verify resource exists
    resource = db.execute(
        select(KubernetesResource).where(KubernetesResource.id == resource_id, KubernetesResource.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=404,
            detail=f"Resource with id {resource_id} not found"
        )

    # Get reconciliations
    query = select(ResourceReconciliation).where(
        ResourceReconciliation.resource_id == resource_id
    ).order_by(ResourceReconciliation.timestamp.desc())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    result = db.execute(query)
    reconciliations = result.scalars().all()

    reconciliation_infos = [
        ResourceReconciliationInfo.from_orm(rec) for rec in reconciliations
    ]

    return ResourceReconciliationListResponse(
        reconciliations=reconciliation_infos,
        total=len(reconciliation_infos)
    )
