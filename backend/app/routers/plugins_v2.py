"""
Plugin Management API (v2) - New Plugin Architecture

Endpoints for managing plugins with the new plugin system.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Plugin, PluginMetric, PluginExecution
from app.services.plugin_manager import PluginManager
from app.schemas_plugins import (
    PluginListResponse,
    PluginInfo,
    PluginDetailInfo,
    PluginRegisterRequest,
    PluginConfigUpdate,
    PluginMetricData,
    PluginMetricsResponse,
    PluginHealthResponse,
    PluginExecutionResponse,
    PluginActionResponse
)

router = APIRouter(
    prefix="/plugins/v2",
    tags=["plugins-v2"],
    responses={404: {"description": "Not found"}},
)


def get_plugin_manager(db: Session = Depends(get_db)) -> PluginManager:
    """Dependency to get PluginManager instance."""
    return PluginManager(db)


@router.get("", response_model=PluginListResponse)
async def list_plugins(
    category: Optional[str] = None,
    enabled: Optional[bool] = None,
    external: Optional[bool] = None,
    manager: PluginManager = Depends(get_plugin_manager)
):
    """
    List all registered plugins.
    
    Query parameters:
    - category: Filter by category
    - enabled: Filter by enabled status
    - external: Filter by external/built-in
    """
    plugins = manager.list_plugins()
    
    # Apply filters
    if category:
        plugins = [p for p in plugins if p.get("category") == category]
    if enabled is not None:
        plugins = [p for p in plugins if p.get("enabled") == enabled]
    if external is not None:
        plugins = [p for p in plugins if p.get("external") == external]
    
    return PluginListResponse(
        plugins=[PluginInfo(**p) for p in plugins],
        total=len(plugins)
    )


@router.post("/register", response_model=PluginActionResponse)
async def register_external_plugin(
    request: PluginRegisterRequest,
    manager: PluginManager = Depends(get_plugin_manager)
):
    """
    Register an external plugin with the hub.
    
    External plugins should call this endpoint to register themselves
    before they can report metrics or receive configuration.
    """
    success = await manager.register_external_plugin(request.dict())
    
    if success:
        return PluginActionResponse(
            success=True,
            message=f"Plugin {request.id} registered successfully",
            plugin_id=request.id
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to register plugin {request.id}"
        )


@router.get("/{plugin_id}", response_model=PluginDetailInfo)
async def get_plugin(
    plugin_id: str,
    manager: PluginManager = Depends(get_plugin_manager)
):
    """Get detailed information about a specific plugin."""
    plugin_info = manager.get_plugin_info(plugin_id)
    
    if not plugin_info:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin_id} not found"
        )
    
    return PluginDetailInfo(**plugin_info)


@router.post("/{plugin_id}/enable", response_model=PluginActionResponse)
async def enable_plugin(
    plugin_id: str,
    manager: PluginManager = Depends(get_plugin_manager)
):
    """Enable a plugin."""
    success = await manager.enable_plugin(plugin_id)
    
    if success:
        return PluginActionResponse(
            success=True,
            message=f"Plugin {plugin_id} enabled",
            plugin_id=plugin_id
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to enable plugin {plugin_id}"
        )


@router.post("/{plugin_id}/disable", response_model=PluginActionResponse)
async def disable_plugin(
    plugin_id: str,
    manager: PluginManager = Depends(get_plugin_manager)
):
    """Disable a plugin."""
    success = await manager.disable_plugin(plugin_id)
    
    if success:
        return PluginActionResponse(
            success=True,
            message=f"Plugin {plugin_id} disabled",
            plugin_id=plugin_id
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to disable plugin {plugin_id}"
        )


@router.post("/{plugin_id}/execute", response_model=PluginExecutionResponse)
async def execute_plugin(
    plugin_id: str,
    manager: PluginManager = Depends(get_plugin_manager)
):
    """
    Execute a plugin manually (on-demand).
    
    Useful for testing or triggering data collection outside of scheduled runs.
    """
    result = await manager.execute_plugin(plugin_id)
    
    return PluginExecutionResponse(
        success=result.get("success", False),
        plugin_id=plugin_id,
        timestamp=result.get("timestamp", datetime.utcnow().isoformat()),
        data=result.get("data"),
        error=result.get("error")
    )


@router.get("/{plugin_id}/config")
async def get_plugin_config(
    plugin_id: str,
    manager: PluginManager = Depends(get_plugin_manager)
):
    """Get plugin configuration."""
    plugin_info = manager.get_plugin_info(plugin_id)
    
    if not plugin_info:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin_id} not found"
        )
    
    return {
        "plugin_id": plugin_id,
        "config": plugin_info.get("config", {})
    }


@router.put("/{plugin_id}/config", response_model=PluginActionResponse)
async def update_plugin_config(
    plugin_id: str,
    request: PluginConfigUpdate,
    manager: PluginManager = Depends(get_plugin_manager)
):
    """Update plugin configuration."""
    success = await manager.update_plugin_config(plugin_id, request.config)
    
    if success:
        return PluginActionResponse(
            success=True,
            message=f"Configuration updated for plugin {plugin_id}",
            plugin_id=plugin_id
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update configuration for plugin {plugin_id}"
        )


@router.get("/{plugin_id}/health", response_model=PluginHealthResponse)
async def get_plugin_health(
    plugin_id: str,
    manager: PluginManager = Depends(get_plugin_manager)
):
    """Check plugin health status."""
    health = await manager.check_plugin_health(plugin_id)
    
    return PluginHealthResponse(
        plugin_id=plugin_id,
        healthy=health.get("healthy", False),
        message=health.get("message", "Unknown"),
        details=health.get("details"),
        checked_at=datetime.utcnow().isoformat()
    )


@router.post("/{plugin_id}/health", response_model=PluginActionResponse)
async def update_plugin_health(
    plugin_id: str,
    health_data: dict,
    db: Session = Depends(get_db)
):
    """
    Update plugin health status (for external plugins).
    
    External plugins can report their health status via this endpoint.
    """
    stmt = select(Plugin).where(Plugin.id == plugin_id)
    result = db.execute(stmt)
    plugin = result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin_id} not found"
        )
    
    plugin.last_health_check = datetime.utcnow()
    plugin.health_status = "healthy" if health_data.get("healthy") else "unhealthy"
    plugin.health_message = health_data.get("message")
    db.commit()
    
    return PluginActionResponse(
        success=True,
        message="Health status updated",
        plugin_id=plugin_id
    )


@router.post("/{plugin_id}/metrics", response_model=PluginActionResponse)
async def report_plugin_metrics(
    plugin_id: str,
    metric_data: PluginMetricData,
    db: Session = Depends(get_db)
):
    """
    Report plugin metrics (for external plugins).
    
    External plugins use this endpoint to send their collected metrics to the hub.
    """
    stmt = select(Plugin).where(Plugin.id == plugin_id)
    result = db.execute(stmt)
    plugin = result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin_id} not found"
        )
    
    # Store metrics
    metric = PluginMetric(
        plugin_id=plugin_id,
        timestamp=metric_data.timestamp or datetime.utcnow(),
        data=metric_data.data
    )
    db.add(metric)
    db.commit()
    
    return PluginActionResponse(
        success=True,
        message="Metrics recorded",
        plugin_id=plugin_id
    )


@router.get("/{plugin_id}/metrics", response_model=PluginMetricsResponse)
async def get_plugin_metrics(
    plugin_id: str,
    start_time: Optional[datetime] = Query(None, description="Start time for metrics query"),
    end_time: Optional[datetime] = Query(None, description="End time for metrics query"),
    limit: int = Query(100, description="Maximum number of metrics to return"),
    db: Session = Depends(get_db)
):
    """
    Get plugin metrics.
    
    Query parameters:
    - start_time: Filter metrics after this time
    - end_time: Filter metrics before this time
    - limit: Maximum number of metrics to return (default: 100)
    """
    # Build query
    query = select(PluginMetric).where(PluginMetric.plugin_id == plugin_id)
    
    if start_time:
        query = query.where(PluginMetric.timestamp >= start_time)
    if end_time:
        query = query.where(PluginMetric.timestamp <= end_time)
    
    query = query.order_by(PluginMetric.timestamp.desc()).limit(limit)
    
    result = db.execute(query)
    metrics = result.scalars().all()
    
    return PluginMetricsResponse(
        plugin_id=plugin_id,
        metrics=[
            {
                "timestamp": m.timestamp.isoformat(),
                "data": m.data
            }
            for m in metrics
        ],
        total=len(metrics),
        start_time=start_time.isoformat() if start_time else None,
        end_time=end_time.isoformat() if end_time else None
    )


@router.get("/{plugin_id}/executions")
async def get_plugin_executions(
    plugin_id: str,
    limit: int = Query(50, description="Maximum number of executions to return"),
    db: Session = Depends(get_db)
):
    """Get plugin execution history."""
    query = select(PluginExecution).where(
        PluginExecution.plugin_id == plugin_id
    ).order_by(PluginExecution.started_at.desc()).limit(limit)
    
    result = db.execute(query)
    executions = result.scalars().all()
    
    return {
        "plugin_id": plugin_id,
        "executions": [
            {
                "id": e.id,
                "started_at": e.started_at.isoformat(),
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "status": e.status,
                "error_message": e.error_message,
                "metrics_count": e.metrics_count
            }
            for e in executions
        ],
        "total": len(executions)
    }
