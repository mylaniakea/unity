"""
Metrics aggregation service for dashboard.

Provides unified access to metrics from plugins, alerts, and infrastructure.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, desc
from app.models.plugin import Plugin, PluginMetric, PluginExecution
from app.models.monitoring import Alert
from app.models.alert_rules import AlertRule, AlertSeverity, AlertStatus
from app.models.infrastructure import MonitoredServer, StorageDevice, DatabaseInstance
import logging

logger = logging.getLogger(__name__)


async def get_dashboard_metrics(db: Session) -> Dict[str, Any]:
    """
    Aggregate key system metrics from plugins for dashboard overview.
    
    Returns latest metrics for: CPU, Memory, Disk, Network
    """
    metrics = {
        "cpu": None,
        "memory": None,
        "disk": None,
        "network": None,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Get latest CPU metric from system_info plugin
        cpu_metric = db.execute(
            select(PluginMetric)
            .where(and_(
                PluginMetric.plugin_id == "system_info",
                PluginMetric.metric_name == "cpu_percent"
            ))
            .order_by(PluginMetric.time.desc())
            .limit(1)
        ).scalar_one_or_none()
        
        if cpu_metric:
            metrics["cpu"] = {
                "value": cpu_metric.value,
                "timestamp": cpu_metric.time.isoformat()
            }
        
        # Get latest Memory metric
        mem_metric = db.execute(
            select(PluginMetric)
            .where(and_(
                PluginMetric.plugin_id == "system_info",
                PluginMetric.metric_name == "memory_percent"
            ))
            .order_by(PluginMetric.time.desc())
            .limit(1)
        ).scalar_one_or_none()
        
        if mem_metric:
            metrics["memory"] = {
                "value": mem_metric.value,
                "timestamp": mem_metric.time.isoformat()
            }
        
        # Get latest Disk metric
        disk_metric = db.execute(
            select(PluginMetric)
            .where(and_(
                PluginMetric.plugin_id == "disk_monitor",
                PluginMetric.metric_name == "disk_usage_percent"
            ))
            .order_by(PluginMetric.time.desc())
            .limit(1)
        ).scalar_one_or_none()
        
        if disk_metric:
            metrics["disk"] = {
                "value": disk_metric.value,
                "timestamp": disk_metric.time.isoformat()
            }
        
        # Get latest Network metric
        net_metric = db.execute(
            select(PluginMetric)
            .where(and_(
                PluginMetric.plugin_id == "network_monitor",
                PluginMetric.metric_name == "network_bytes_sent"
            ))
            .order_by(PluginMetric.time.desc())
            .limit(1)
        ).scalar_one_or_none()
        
        if net_metric:
            metrics["network"] = {
                "value": net_metric.value,
                "timestamp": net_metric.time.isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {e}")
    
    return metrics


async def get_plugin_metrics_summary(db: Session) -> List[Dict[str, Any]]:
    """
    Get summary of all enabled plugins with their latest execution status.
    
    Returns plugin metadata + last execution time and status.
    """
    plugins = []
    
    try:
        # Get all enabled plugins
        stmt = select(Plugin).where(Plugin.enabled == True)
        enabled_plugins = db.execute(stmt).scalars().all()
        
        for plugin in enabled_plugins:
            # Get latest execution
            last_exec = db.execute(
                select(PluginExecution)
                .where(PluginExecution.plugin_id == plugin.plugin_id)
                .order_by(PluginExecution.timestamp.desc())
                .limit(1)
            ).scalar_one_or_none()
            
            plugin_data = {
                "plugin_id": plugin.plugin_id,
                "name": plugin.name,
                "category": plugin.category,
                "enabled": plugin.enabled,
                "last_execution": None,
                "status": "unknown",
                "is_stale": False
            }
            
            if last_exec:
                plugin_data["last_execution"] = last_exec.timestamp.isoformat()
                plugin_data["status"] = last_exec.status
                
                # Consider stale if no execution in last 10 minutes
                if datetime.utcnow() - last_exec.timestamp > timedelta(minutes=10):
                    plugin_data["is_stale"] = True
            else:
                plugin_data["is_stale"] = True
                plugin_data["status"] = "never_run"
            
            plugins.append(plugin_data)
    
    except Exception as e:
        logger.error(f"Error fetching plugin metrics summary: {e}")
    
    return plugins


async def get_alert_summary(db: Session) -> Dict[str, Any]:
    """
    Get alert statistics and recent alerts for dashboard.
    
    Returns counts by severity + list of recent unresolved alerts.
    """
    summary = {
        "total": 0,
        "unresolved": 0,
        "by_severity": {
            "critical": 0,
            "warning": 0,
            "info": 0
        },
        "recent_alerts": []
    }
    
    try:
        # Total alerts
        summary["total"] = db.query(Alert).count()
        
        # Unresolved alerts
        summary["unresolved"] = db.query(Alert).filter(
            Alert.status != AlertStatus.RESOLVED
        ).count()
        
        # Count by severity (unresolved only)
        for severity in [AlertSeverity.CRITICAL, AlertSeverity.WARNING, AlertSeverity.INFO]:
            count = db.query(Alert).filter(
                and_(
                    Alert.severity == severity,
                    Alert.status != AlertStatus.RESOLVED
                )
            ).count()
            summary["by_severity"][severity.value] = count
        
        # Recent unresolved alerts (last 5)
        recent = db.query(Alert).filter(
            Alert.status != AlertStatus.RESOLVED
        ).order_by(Alert.triggered_at.desc()).limit(5).all()
        
        summary["recent_alerts"] = [
            {
                "id": alert.id,
                "title": alert.title,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "triggered_at": alert.triggered_at.isoformat(),
                "resource_type": alert.resource_type.value if alert.resource_type else None,
                "resource_id": alert.resource_id
            }
            for alert in recent
        ]
        
    except Exception as e:
        logger.error(f"Error fetching alert summary: {e}")
    
    return summary


async def get_infrastructure_health(db: Session) -> Dict[str, Any]:
    """
    Get health summary of infrastructure resources.
    
    Returns counts and status for servers, storage, databases.
    """
    health = {
        "servers": {
            "total": 0,
            "healthy": 0,
            "unhealthy": 0
        },
        "storage": {
            "total": 0,
            "devices": 0,
            "pools": 0
        },
        "databases": {
            "total": 0,
            "online": 0,
            "offline": 0
        }
    }
    
    try:
        # Servers
        all_servers = db.query(MonitoredServer).all()
        health["servers"]["total"] = len(all_servers)
        health["servers"]["healthy"] = sum(1 for s in all_servers if s.status == "healthy")
        health["servers"]["unhealthy"] = sum(1 for s in all_servers if s.status != "healthy")
        
        # Storage devices
        all_storage = db.query(StorageDevice).all()
        health["storage"]["total"] = len(all_storage)
        health["storage"]["devices"] = len(all_storage)
        
        # Databases
        all_databases = db.query(DatabaseInstance).all()
        health["databases"]["total"] = len(all_databases)
        health["databases"]["online"] = sum(1 for d in all_databases if d.status == "online")
        health["databases"]["offline"] = sum(1 for d in all_databases if d.status != "online")
        
    except Exception as e:
        logger.error(f"Error fetching infrastructure health: {e}")
    
    return health


async def get_metric_history(
    db: Session,
    plugin_id: str,
    metric_name: str,
    time_range: str = "1h"
) -> List[Dict[str, Any]]:
    """
    Get historical time-series data for a specific metric.
    
    Args:
        plugin_id: Plugin identifier
        metric_name: Name of the metric
        time_range: Time range (1h, 6h, 24h, 7d)
    
    Returns:
        List of {timestamp, value} points in chronological order
    """
    # Parse time range
    range_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7)
    }
    
    delta = range_map.get(time_range, timedelta(hours=1))
    start_time = datetime.utcnow() - delta
    
    history = []
    
    try:
        # Query metrics within time range
        metrics = db.execute(
            select(PluginMetric)
            .where(and_(
                PluginMetric.plugin_id == plugin_id,
                PluginMetric.metric_name == metric_name,
                PluginMetric.time >= start_time
            ))
            .order_by(PluginMetric.time.asc())
        ).scalars().all()
        
        history = [
            {
                "timestamp": m.time.isoformat(),
                "value": m.value
            }
            for m in metrics
        ]
        
    except Exception as e:
        logger.error(f"Error fetching metric history: {e}")
    
    return history


async def get_multi_metric_history(
    db: Session,
    metrics: List[Dict[str, str]],
    time_range: str = "1h"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get historical data for multiple metrics at once.
    
    Args:
        metrics: List of {plugin_id, metric_name} dicts
        time_range: Time range (1h, 6h, 24h, 7d)
    
    Returns:
        Dict mapping metric keys to history arrays
    """
    result = {}
    
    for metric_spec in metrics:
        plugin_id = metric_spec.get("plugin_id")
        metric_name = metric_spec.get("metric_name")
        key = f"{plugin_id}.{metric_name}"
        
        history = await get_metric_history(db, plugin_id, metric_name, time_range)
        result[key] = history
    
    return result
