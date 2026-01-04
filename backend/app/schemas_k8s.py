"""
Pydantic schemas for Kubernetes Control Plane API
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ==================
# CLUSTER SCHEMAS
# ==================

class KubernetesClusterBase(BaseModel):
    """Base Kubernetes cluster schema"""
    name: str = Field(..., description="Cluster name")
    description: Optional[str] = Field(None, description="Cluster description")
    kubeconfig_path: Optional[str] = Field(None, description="Path to kubeconfig file")
    api_server_url: Optional[str] = Field(None, description="API server URL")
    context_name: Optional[str] = Field(None, description="Kubeconfig context name")
    provider: Optional[str] = Field(None, description="Cluster provider (k3s, eks, gke, etc.)")
    is_default: bool = Field(False, description="Whether this is the default cluster")
    is_active: bool = Field(True, description="Whether cluster is actively monitored")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional cluster-specific config")
    labels: Dict[str, Any] = Field(default_factory=dict, description="User-defined labels")


class KubernetesClusterCreate(KubernetesClusterBase):
    """Schema for creating a new Kubernetes cluster"""
    pass


class KubernetesClusterUpdate(BaseModel):
    """Schema for updating a Kubernetes cluster"""
    name: Optional[str] = None
    description: Optional[str] = None
    kubeconfig_path: Optional[str] = None
    api_server_url: Optional[str] = None
    context_name: Optional[str] = None
    provider: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, Any]] = None


class KubernetesClusterInfo(KubernetesClusterBase):
    """Basic Kubernetes cluster information"""
    id: int
    cluster_version: Optional[str] = None
    health_status: str
    health_message: Optional[str] = None
    last_health_check: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    resource_count: Optional[int] = Field(0, description="Number of managed resources in this cluster")

    class Config:
        from_attributes = True


class KubernetesClusterDetail(KubernetesClusterInfo):
    """Detailed Kubernetes cluster information"""
    created_by: Optional[int] = None


class KubernetesClusterListResponse(BaseModel):
    """Response for listing clusters"""
    clusters: List[KubernetesClusterInfo]
    total: int


class KubernetesClusterHealthResponse(BaseModel):
    """Cluster health check response"""
    cluster_id: int
    cluster_name: str
    healthy: bool
    health_status: str
    message: Optional[str] = None
    cluster_version: Optional[str] = None
    node_count: Optional[int] = None
    namespace_count: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    checked_at: datetime


# ==================
# RESOURCE SCHEMAS
# ==================

class KubernetesResourceBase(BaseModel):
    """Base Kubernetes resource schema"""
    kind: str = Field(..., description="Resource kind (Deployment, Service, etc.)")
    name: str = Field(..., description="Resource name")
    namespace: str = Field("default", description="Kubernetes namespace")
    api_version: str = Field("v1", description="API version (v1, apps/v1, etc.)")
    desired_state: Dict[str, Any] = Field(..., description="Full K8s resource manifest")
    labels: Dict[str, Any] = Field(default_factory=dict, description="Kubernetes labels")
    annotations: Dict[str, Any] = Field(default_factory=dict, description="Kubernetes annotations")
    managed_by: str = Field("unity", description="Management tool (unity, helm, terraform, etc.)")
    auto_reconcile: bool = Field(True, description="Whether to automatically reconcile drift")
    deletion_policy: str = Field("delete", description="Deletion policy (delete, retain, orphan)")


class KubernetesResourceCreate(KubernetesResourceBase):
    """Schema for creating a new Kubernetes resource"""
    cluster_id: int = Field(..., description="ID of the cluster to create the resource in")


class KubernetesResourceUpdate(BaseModel):
    """Schema for updating a Kubernetes resource"""
    desired_state: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, Any]] = None
    annotations: Optional[Dict[str, Any]] = None
    auto_reconcile: Optional[bool] = None
    deletion_policy: Optional[str] = None
    is_active: Optional[bool] = None


class KubernetesResourceInfo(KubernetesResourceBase):
    """Basic Kubernetes resource information"""
    id: int
    cluster_id: int
    cluster_name: Optional[str] = None
    reconciliation_status: str
    reconciliation_message: Optional[str] = None
    drift_detected: bool
    is_active: bool
    last_reconciled: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KubernetesResourceDetail(KubernetesResourceInfo):
    """Detailed Kubernetes resource information"""
    current_state: Optional[Dict[str, Any]] = None
    created_by: Optional[int] = None


class KubernetesResourceListResponse(BaseModel):
    """Response for listing resources"""
    resources: List[KubernetesResourceInfo]
    total: int


class KubernetesResourceReconcileRequest(BaseModel):
    """Request to trigger manual reconciliation"""
    force: bool = Field(False, description="Force reconciliation even if no drift detected")


class KubernetesResourceReconcileResponse(BaseModel):
    """Response for reconciliation request"""
    success: bool
    resource_id: int
    reconciliation_id: Optional[int] = None
    status: str
    result: Optional[str] = None
    message: Optional[str] = None
    changes_applied: Optional[Dict[str, Any]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


# ==================
# RECONCILIATION SCHEMAS
# ==================

class ResourceReconciliationInfo(BaseModel):
    """Reconciliation history information"""
    id: int
    resource_id: int
    timestamp: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    status: str
    result: Optional[str] = None
    changes_applied: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retry_count: int
    triggered_by: str
    triggered_by_user_id: Optional[int] = None
    reconciliation_version: int
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ResourceReconciliationListResponse(BaseModel):
    """Response for listing reconciliations"""
    reconciliations: List[ResourceReconciliationInfo]
    total: int


# ==================
# FILTER AND QUERY SCHEMAS
# ==================

class KubernetesResourceFilter(BaseModel):
    """Filters for querying resources"""
    cluster_id: Optional[int] = None
    namespace: Optional[str] = None
    kind: Optional[str] = None
    managed_by: Optional[str] = None
    is_active: Optional[bool] = None
    drift_detected: Optional[bool] = None
    reconciliation_status: Optional[str] = None


# ==================
# ACTION RESPONSE SCHEMAS
# ==================

class KubernetesActionResponse(BaseModel):
    """Generic action response"""
    success: bool
    message: str
    cluster_id: Optional[int] = None
    resource_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
