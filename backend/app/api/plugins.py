"""
Plugin API Endpoints

REST API for plugin management, metrics, and status.
"""
import logging
from typing import List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models import Plugin, PluginMetric, PluginExecution
from app.services.cache import cache
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


# Pydantic models for request/response
class PluginResponse(BaseModel):
    id: str  # Plugin ID is a string like 'network-monitor'
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    enabled: bool
    config: Optional[dict] = None
    author: Optional[str] = None

    class Config:
        from_attributes = True
        from_attributes = True


# class PluginStatusResponse(BaseModel):
#     plugin_id: str
#     last_run: Optional[datetime]
#     last_success: Optional[datetime]
#     last_error: Optional[str]
#     error_count: int
#     consecutive_errors: int
#     health_status: str
# 
#     class Config:
        from_attributes = True


class PluginExecutionResponse(BaseModel):
    id: int
    plugin_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    error_message: Optional[str]
    metrics_count: int

    class Config:
        from_attributes = True


class MetricResponse(BaseModel):
    time: datetime
    plugin_id: str
    metric_name: str
    value: Any
    tags: Optional[dict]

    class Config:
        from_attributes = True


class EnablePluginRequest(BaseModel):
    enabled: bool


@router.get("", response_model=List[PluginResponse])
async def list_plugins(
    enabled: Optional[bool] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all plugins with optional filters.
    
    Args:
        enabled: Filter by enabled status
        category: Filter by category
    """
    query = select(Plugin)
    
    if enabled is not None:
        query = query.where(Plugin.enabled == enabled)
    
    if category:
        query = query.where(Plugin.category == category)
    
    result = db.execute(query)
    plugins = result.scalars().all()
    
    return [PluginResponse.model_validate(p) for p in plugins]


@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(plugin_id: str, db: Session = Depends(get_db)):
    """Get plugin details by ID."""
    result = db.execute(
        select(Plugin).where(Plugin.plugin_id == plugin_id)
    )
    plugin = result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return PluginResponse.model_validate(plugin)


@router.post("/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    request: EnablePluginRequest,
    db: Session = Depends(get_db)
):
    """Enable or disable a plugin."""
    result = db.execute(
        select(Plugin).where(Plugin.plugin_id == plugin_id)
    )
    plugin = result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    plugin.enabled = request.enabled
    plugin.updated_at = datetime.now()
    db.commit()
    
    # Clear cache
    await cache.delete(f"plugin:{plugin_id}")
    
    return {
        "success": True,
        "plugin_id": plugin_id,
        "enabled": request.enabled,
        "message": f"Plugin {'enabled' if request.enabled else 'disabled'} successfully"
    }


# @router.get("/{plugin_id}/status", response_model=PluginStatusResponse)
# async def get_plugin_status(plugin_id: str, db: Session = Depends(get_db)):
#     """Get plugin health status."""
#     # Check cache first
#     cached = await cache.get_plugin_status(plugin_id)
#     if cached:
#         return cached
#     
#     # Query database
#     status = db.query(PluginStatus).filter_by(plugin_id=plugin_id).first()
#     
#     if not status:
#         raise HTTPException(status_code=404, detail="Plugin status not found")
#     
#     response = PluginStatusResponse.model_validate(status)
#     
    # Cache the response
    await cache.set_plugin_status(plugin_id, response.model_dump())
    
    return response


@router.get("/{plugin_id}/metrics", response_model=List[MetricResponse])
async def get_plugin_metrics(
    plugin_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get latest metrics for a plugin.
    
    Args:
        plugin_id: Plugin identifier
        limit: Maximum number of metrics to return (default: 100, max: 1000)
    """
    # Check cache for latest metrics
    if limit <= 10:
        cached = await cache.get_latest_metrics(plugin_id)
        if cached:
            return cached[:limit]
    
    # Query database
    result = db.execute(
        select(PluginMetric)
        .where(PluginMetric.plugin_id == plugin_id)
        .order_by(desc(PluginMetric.time))
        .limit(limit)
    )
    metrics = result.scalars().all()
    
    if not metrics:
        return []
    
    response = [MetricResponse.model_validate(m) for m in metrics]
    
    # Cache latest 10 metrics
    if len(response) >= 10:
        await cache.set_latest_metrics(plugin_id, [m.model_dump() for m in response[:10]])
    
    return response


@router.get("/{plugin_id}/metrics/history")
async def get_plugin_metrics_history(
    plugin_id: str,
    metric_name: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),  # Default 24h, max 7 days
    db: Session = Depends(get_db)
):
    """
    Get historical metrics for a plugin.
    
    Args:
        plugin_id: Plugin identifier
        metric_name: Filter by specific metric name
        hours: Number of hours of history (default: 24, max: 168)
    """
    since = datetime.now() - timedelta(hours=hours)
    
    query = select(PluginMetric).where(
        PluginMetric.plugin_id == plugin_id,
        PluginMetric.time >= since
    )
    
    if metric_name:
        query = query.where(PluginMetric.metric_name == metric_name)
    
    query = query.order_by(desc(PluginMetric.time))
    
    result = db.execute(query)
    metrics = result.scalars().all()
    
    return {
        "plugin_id": plugin_id,
        "metric_name": metric_name,
        "hours": hours,
        "count": len(metrics),
        "metrics": [MetricResponse.model_validate(m) for m in metrics]
    }


@router.get("/{plugin_id}/executions", response_model=List[PluginExecutionResponse])
async def get_plugin_executions(
    plugin_id: str,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get execution history for a plugin.
    
    Args:
        plugin_id: Plugin identifier
        limit: Maximum number of executions to return (default: 50, max: 500)
    """
    result = db.execute(
        select(PluginExecution)
        .where(PluginExecution.plugin_id == plugin_id)
        .order_by(desc(PluginExecution.started_at))
        .limit(limit)
    )
    executions = result.scalars().all()
    
    return [PluginExecutionResponse.model_validate(e) for e in executions]


@router.get("/categories/list")
async def list_categories(db: Session = Depends(get_db)):
    """Get list of all plugin categories."""
    result = db.execute(
        select(Plugin.category).distinct().where(Plugin.category.isnot(None))
    )
    categories = [row[0] for row in result.all()]
    
    return {"categories": sorted(categories)}


@router.get("/stats/summary")
async def get_stats_summary(db: Session = Depends(get_db)):
    """Get overall plugin statistics."""
    total_plugins = db.query(Plugin).count()
    enabled_plugins = db.query(Plugin).filter_by(enabled=True).count()
    total_metrics = db.query(PluginMetric).count()
    total_executions = db.query(PluginExecution).count()
    
    # Count by health status
#     healthy = db.query(PluginStatus).filter_by(health_status='healthy').count()
#     degraded = db.query(PluginStatus).filter_by(health_status='degraded').count()
#     failing = db.query(PluginStatus).filter_by(health_status='failing').count()
    
    return {
        "total_plugins": total_plugins,
        "enabled_plugins": enabled_plugins,
        "disabled_plugins": total_plugins - enabled_plugins,
        "total_metrics": total_metrics,
        "total_executions": total_executions,
        "health": {
            "healthy": healthy,
            "degraded": degraded,
            "failing": failing
        }
    }
