"""
Dashboard API endpoints.

Provides unified metrics, alerts, and infrastructure data for frontend dashboards.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.services.monitoring import metrics_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
async def get_dashboard_overview(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get complete dashboard overview data.
    
    Returns:
        - Latest system metrics (CPU, memory, disk, network)
        - Alert summary with counts by severity
        - Infrastructure health status
        - Plugin execution status
        - Timestamp
    """
    # Fetch all dashboard data in parallel
    metrics = await metrics_service.get_dashboard_metrics(db)
    alerts = await metrics_service.get_alert_summary(db)
    infrastructure = await metrics_service.get_infrastructure_health(db)
    plugins = await metrics_service.get_plugin_metrics_summary(db)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics,
        "alerts": alerts,
        "infrastructure": infrastructure,
        "plugins": {
            "total": len(plugins),
            "enabled": sum(1 for p in plugins if p["enabled"]),
            "healthy": sum(1 for p in plugins if p["status"] == "success" and not p["is_stale"]),
            "stale": sum(1 for p in plugins if p["is_stale"]),
            "items": plugins
        }
    }


@router.get("/metrics/history")
async def get_metrics_history(
    time_range: str = Query("1h", regex="^(1h|6h|24h|7d)$"),
    db: Session = Depends(get_db)
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get historical time-series data for key metrics.
    
    Args:
        time_range: Time range for historical data (1h, 6h, 24h, 7d)
    
    Returns:
        Dict with metric names as keys and time-series arrays as values.
        Each array contains {timestamp, value} objects.
    """
    # Define key metrics to fetch
    metrics_to_fetch = [
        {"plugin_id": "system_info", "metric_name": "cpu_percent"},
        {"plugin_id": "system_info", "metric_name": "memory_percent"},
        {"plugin_id": "disk_monitor", "metric_name": "disk_usage_percent"},
        {"plugin_id": "network_monitor", "metric_name": "network_bytes_sent"},
        {"plugin_id": "network_monitor", "metric_name": "network_bytes_recv"}
    ]
    
    history = await metrics_service.get_multi_metric_history(
        db, 
        metrics_to_fetch, 
        time_range
    )
    
    return {
        "time_range": time_range,
        "metrics": history,
        "fetched_at": datetime.utcnow().isoformat()
    }


@router.get("/plugins/health")
async def get_plugins_health(
    category: Optional[str] = Query(None, description="Filter by plugin category"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed health status for all plugins.
    
    Args:
        category: Optional category filter (e.g., 'system', 'database', 'network')
    
    Returns:
        List of plugins with execution status, freshness, and metadata.
    """
    plugins = await metrics_service.get_plugin_metrics_summary(db)
    
    # Filter by category if specified
    if category:
        plugins = [p for p in plugins if p.get("category") == category]
    
    # Categorize plugins by status
    healthy = [p for p in plugins if p["status"] == "success" and not p["is_stale"]]
    stale = [p for p in plugins if p["is_stale"]]
    failed = [p for p in plugins if p["status"] == "error"]
    unknown = [p for p in plugins if p["status"] not in ["success", "error"]]
    
    return {
        "total": len(plugins),
        "summary": {
            "healthy": len(healthy),
            "stale": len(stale),
            "failed": len(failed),
            "unknown": len(unknown)
        },
        "plugins": plugins,
        "fetched_at": datetime.utcnow().isoformat()
    }


@router.get("/metrics/{plugin_id}/{metric_name}/history")
async def get_single_metric_history(
    plugin_id: str,
    metric_name: str,
    time_range: str = Query("1h", regex="^(1h|6h|24h|7d)$"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get historical data for a specific plugin metric.
    
    Args:
        plugin_id: Plugin identifier
        metric_name: Metric name
        time_range: Time range (1h, 6h, 24h, 7d)
    
    Returns:
        Time-series data for the specified metric.
    """
    history = await metrics_service.get_metric_history(
        db,
        plugin_id,
        metric_name,
        time_range
    )
    
    return {
        "plugin_id": plugin_id,
        "metric_name": metric_name,
        "time_range": time_range,
        "data": history,
        "count": len(history),
        "fetched_at": datetime.utcnow().isoformat()
    }
