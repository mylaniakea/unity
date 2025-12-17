"""Infrastructure monitoring API endpoints for Phase 3: BD-Store Integration."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import logging

from app.core.database import get_db
from app import models
from app.services.infrastructure.collection_task import collect_server_data, collect_all_servers
from app.services.infrastructure.ssh_service import ssh_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/infrastructure", tags=["infrastructure"])


# ============================================================================
# Monitored Servers Endpoints
# ============================================================================

@router.get("/servers", response_model=List[dict])
def list_monitored_servers(
    skip: int = 0,
    limit: int = 100,
    monitoring_enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List all monitored servers."""
    query = db.query(models.MonitoredServer)
    
    if monitoring_enabled is not None:
        query = query.filter(models.MonitoredServer.monitoring_enabled == monitoring_enabled)
    
    servers = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": s.id,
            "hostname": s.hostname,
            "ip_address": s.ip_address,
            "ssh_port": s.ssh_port,
            "username": s.username,
            "status": s.status.value if s.status else "unknown",
            "monitoring_enabled": s.monitoring_enabled,
            "last_seen": s.last_seen.isoformat() if s.last_seen else None,
            "last_error": s.last_error,
            "ssh_key_id": s.ssh_key_id,
            "credential_id": s.credential_id,
            "description": s.description,
            "tags": s.tags,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        }
        for s in servers
    ]


@router.post("/servers", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_monitored_server(
    hostname: str,
    ip_address: str,
    username: str,
    ssh_port: int = 22,
    ssh_key_id: Optional[int] = None,
    credential_id: Optional[int] = None,
    monitoring_enabled: bool = False,
    description: Optional[str] = None,
    tags: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a new monitored server."""
    # Check if server already exists
    existing = db.query(models.MonitoredServer).filter(
        models.MonitoredServer.hostname == hostname
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Server with hostname '{hostname}' already exists"
        )
    
    server = models.MonitoredServer(
        hostname=hostname,
        ip_address=ip_address,
        ssh_port=ssh_port,
        username=username,
        ssh_key_id=ssh_key_id,
        credential_id=credential_id,
        monitoring_enabled=monitoring_enabled,
        description=description,
        tags=tags,
        status=models.ServerStatus.UNKNOWN
    )
    
    db.add(server)
    db.commit()
    db.refresh(server)
    
    return {"id": server.id, "hostname": server.hostname, "status": "created"}


@router.get("/servers/{server_id}", response_model=dict)
def get_monitored_server(server_id: int, db: Session = Depends(get_db)):
    """Get details of a specific monitored server."""
    server = db.query(models.MonitoredServer).filter(
        models.MonitoredServer.id == server_id
    ).first()
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server {server_id} not found"
        )
    
    return {
        "id": server.id,
        "hostname": server.hostname,
        "ip_address": server.ip_address,
        "ssh_port": server.ssh_port,
        "username": server.username,
        "status": server.status.value if server.status else "unknown",
        "monitoring_enabled": server.monitoring_enabled,
        "collection_interval": server.collection_interval,
        "last_seen": server.last_seen.isoformat() if server.last_seen else None,
        "last_error": server.last_error,
        "ssh_key_id": server.ssh_key_id,
        "credential_id": server.credential_id,
        "description": server.description,
        "tags": server.tags,
        "created_at": server.created_at.isoformat() if server.created_at else None,
        "updated_at": server.updated_at.isoformat() if server.updated_at else None,
        "device_count": len(server.storage_devices),
        "pool_count": len(server.storage_pools),
        "database_count": len(server.database_instances)
    }


@router.patch("/servers/{server_id}", response_model=dict)
def update_monitored_server(
    server_id: int,
    monitoring_enabled: Optional[bool] = None,
    description: Optional[str] = None,
    tags: Optional[str] = None,
    ssh_key_id: Optional[int] = None,
    credential_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Update a monitored server."""
    server = db.query(models.MonitoredServer).filter(
        models.MonitoredServer.id == server_id
    ).first()
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server {server_id} not found"
        )
    
    if monitoring_enabled is not None:
        server.monitoring_enabled = monitoring_enabled
    if description is not None:
        server.description = description
    if tags is not None:
        server.tags = tags
    if ssh_key_id is not None:
        server.ssh_key_id = ssh_key_id
    if credential_id is not None:
        server.credential_id = credential_id
    
    db.commit()
    db.refresh(server)
    
    return {"id": server.id, "hostname": server.hostname, "status": "updated"}


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitored_server(server_id: int, db: Session = Depends(get_db)):
    """Delete a monitored server."""
    server = db.query(models.MonitoredServer).filter(
        models.MonitoredServer.id == server_id
    ).first()
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server {server_id} not found"
        )
    
    db.delete(server)
    db.commit()


@router.post("/servers/{server_id}/collect", response_model=dict)
def collect_server_data_endpoint(server_id: int, db: Session = Depends(get_db)):
    """Trigger data collection for a specific server."""
    server = db.query(models.MonitoredServer).filter(
        models.MonitoredServer.id == server_id
    ).first()
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server {server_id} not found"
        )
    
    success, message = collect_server_data(server_id)
    
    return {
        "server_id": server_id,
        "hostname": server.hostname,
        "success": success,
        "message": message
    }


@router.post("/collect", response_model=dict)
def collect_all_servers_endpoint():
    """Trigger data collection for all enabled servers."""
    results = collect_all_servers()
    return results


# ============================================================================
# Storage Devices Endpoints
# ============================================================================

@router.get("/servers/{server_id}/storage/devices", response_model=List[dict])
def list_storage_devices(server_id: int, db: Session = Depends(get_db)):
    """List storage devices for a server."""
    devices = db.query(models.StorageDevice).filter(
        models.StorageDevice.server_id == server_id
    ).all()
    
    return [
        {
            "id": d.id,
            "device_name": d.device_name,
            "device_path": d.device_path,
            "device_type": d.device_type.value if d.device_type else "unknown",
            "size_bytes": d.size_bytes,
            "smart_status": d.smart_status.value if d.smart_status else "unknown",
            "temperature_celsius": d.temperature_celsius,
            "power_on_hours": d.power_on_hours,
            "wear_level_percent": d.wear_level_percent,
            "last_checked": d.last_checked.isoformat() if d.last_checked else None
        }
        for d in devices
    ]


@router.get("/storage/devices/{device_id}", response_model=dict)
def get_storage_device(device_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a storage device."""
    device = db.query(models.StorageDevice).filter(
        models.StorageDevice.id == device_id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage device {device_id} not found"
        )
    
    return {
        "id": device.id,
        "server_id": device.server_id,
        "device_name": device.device_name,
        "device_path": device.device_path,
        "serial_number": device.serial_number,
        "model": device.model,
        "firmware_version": device.firmware_version,
        "device_type": device.device_type.value if device.device_type else "unknown",
        "size_bytes": device.size_bytes,
        "sector_size": device.sector_size,
        "smart_status": device.smart_status.value if device.smart_status else "unknown",
        "smart_passed": device.smart_passed,
        "temperature_celsius": device.temperature_celsius,
        "power_on_hours": device.power_on_hours,
        "wear_level_percent": device.wear_level_percent,
        "total_bytes_written": device.total_bytes_written,
        "total_bytes_read": device.total_bytes_read,
        "reallocated_sectors": device.reallocated_sectors,
        "pending_sectors": device.pending_sectors,
        "uncorrectable_errors": device.uncorrectable_errors,
        "last_checked": device.last_checked.isoformat() if device.last_checked else None,
        "created_at": device.created_at.isoformat() if device.created_at else None,
        "updated_at": device.updated_at.isoformat() if device.updated_at else None
    }


# ============================================================================
# Storage Pools Endpoints
# ============================================================================

@router.get("/servers/{server_id}/storage/pools", response_model=List[dict])
def list_storage_pools(server_id: int, db: Session = Depends(get_db)):
    """List storage pools for a server."""
    pools = db.query(models.StoragePool).filter(
        models.StoragePool.server_id == server_id
    ).all()
    
    return [
        {
            "id": p.id,
            "pool_name": p.pool_name,
            "pool_type": p.pool_type.value if p.pool_type else "other",
            "total_size_bytes": p.total_size_bytes,
            "used_size_bytes": p.used_size_bytes,
            "available_size_bytes": p.available_size_bytes,
            "health_status": p.health_status.value if p.health_status else "unknown",
            "raid_level": p.raid_level,
            "device_count": p.device_count,
            "last_checked": p.last_checked.isoformat() if p.last_checked else None
        }
        for p in pools
    ]


@router.get("/storage/pools/{pool_id}", response_model=dict)
def get_storage_pool(pool_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a storage pool."""
    pool = db.query(models.StoragePool).filter(
        models.StoragePool.id == pool_id
    ).first()
    
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage pool {pool_id} not found"
        )
    
    return {
        "id": pool.id,
        "server_id": pool.server_id,
        "pool_name": pool.pool_name,
        "pool_type": pool.pool_type.value if pool.pool_type else "other",
        "total_size_bytes": pool.total_size_bytes,
        "used_size_bytes": pool.used_size_bytes,
        "available_size_bytes": pool.available_size_bytes,
        "fragmentation_percent": pool.fragmentation_percent,
        "health_status": pool.health_status.value if pool.health_status else "unknown",
        "status_message": pool.status_message,
        "raid_level": pool.raid_level,
        "device_count": pool.device_count,
        "last_checked": pool.last_checked.isoformat() if pool.last_checked else None,
        "created_at": pool.created_at.isoformat() if pool.created_at else None,
        "updated_at": pool.updated_at.isoformat() if pool.updated_at else None
    }


# ============================================================================
# Database Instances Endpoints
# ============================================================================

@router.get("/servers/{server_id}/databases", response_model=List[dict])
def list_database_instances(server_id: int, db: Session = Depends(get_db)):
    """List database instances for a server."""
    databases = db.query(models.DatabaseInstance).filter(
        models.DatabaseInstance.server_id == server_id
    ).all()
    
    return [
        {
            "id": d.id,
            "db_type": d.db_type.value if d.db_type else "unknown",
            "db_name": d.db_name,
            "host": d.host,
            "port": d.port,
            "version": d.version,
            "status": d.status.value if d.status else "unknown",
            "size_bytes": d.size_bytes,
            "connection_count": d.connection_count,
            "last_checked": d.last_checked.isoformat() if d.last_checked else None
        }
        for d in databases
    ]


@router.get("/databases/{database_id}", response_model=dict)
def get_database_instance(database_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a database instance."""
    database = db.query(models.DatabaseInstance).filter(
        models.DatabaseInstance.id == database_id
    ).first()
    
    if not database:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database instance {database_id} not found"
        )
    
    return {
        "id": database.id,
        "server_id": database.server_id,
        "db_type": database.db_type.value if database.db_type else "unknown",
        "db_name": database.db_name,
        "host": database.host,
        "port": database.port,
        "username": database.username,
        "version": database.version,
        "status": database.status.value if database.status else "unknown",
        "last_checked": database.last_checked.isoformat() if database.last_checked else None,
        "last_error": database.last_error,
        "size_bytes": database.size_bytes,
        "connection_count": database.connection_count,
        "active_queries": database.active_queries,
        "idle_connections": database.idle_connections,
        "max_connections": database.max_connections,
        "slow_queries": database.slow_queries,
        "cache_hit_ratio": database.cache_hit_ratio,
        "uptime_seconds": database.uptime_seconds,
        "last_metrics_collection": database.last_metrics_collection.isoformat() if database.last_metrics_collection else None,
        "created_at": database.created_at.isoformat() if database.created_at else None,
        "updated_at": database.updated_at.isoformat() if database.updated_at else None
    }


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/stats", response_model=dict)
def get_infrastructure_stats(db: Session = Depends(get_db)):
    """Get overall infrastructure monitoring statistics."""
    total_servers = db.query(models.MonitoredServer).count()
    enabled_servers = db.query(models.MonitoredServer).filter(
        models.MonitoredServer.monitoring_enabled == True
    ).count()
    online_servers = db.query(models.MonitoredServer).filter(
        models.MonitoredServer.status == models.ServerStatus.ONLINE
    ).count()
    
    total_devices = db.query(models.StorageDevice).count()
    total_pools = db.query(models.StoragePool).count()
    total_databases = db.query(models.DatabaseInstance).count()
    
    return {
        "servers": {
            "total": total_servers,
            "monitoring_enabled": enabled_servers,
            "online": online_servers
        },
        "storage": {
            "devices": total_devices,
            "pools": total_pools
        },
        "databases": {
            "instances": total_databases
        }
    }


# ============================================================================
# Alert Rule Management Endpoints (Phase 3.5)
# ============================================================================

@router.get("/alert-rules", response_model=List[dict])
def list_alert_rules(
    skip: int = 0,
    limit: int = 100,
    enabled: Optional[bool] = None,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all alert rules."""
    query = db.query(models.AlertRule)
    
    if enabled is not None:
        query = query.filter(models.AlertRule.enabled == enabled)
    if resource_type:
        query = query.filter(models.AlertRule.resource_type == resource_type)
    
    rules = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "resource_type": r.resource_type.value if r.resource_type else None,
            "metric_name": r.metric_name,
            "condition": r.condition.value if r.condition else None,
            "threshold": r.threshold,
            "severity": r.severity.value if r.severity else None,
            "enabled": r.enabled,
            "notification_channels": r.notification_channels,
            "cooldown_minutes": r.cooldown_minutes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None
        }
        for r in rules
    ]


@router.post("/alert-rules", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_alert_rule(
    name: str,
    resource_type: str,
    metric_name: str,
    condition: str,
    threshold: float,
    severity: str = "warning",
    enabled: bool = True,
    description: Optional[str] = None,
    notification_channels: Optional[List[str]] = None,
    cooldown_minutes: int = 15,
    db: Session = Depends(get_db)
):
    """Create a new alert rule."""
    try:
        rule = models.AlertRule(
            name=name,
            description=description,
            resource_type=resource_type,
            metric_name=metric_name,
            condition=condition,
            threshold=threshold,
            severity=severity,
            enabled=enabled,
            notification_channels=notification_channels,
            cooldown_minutes=cooldown_minutes
        )
        
        db.add(rule)
        db.commit()
        db.refresh(rule)
        
        return {"id": rule.id, "name": rule.name, "status": "created"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create alert rule: {str(e)}"
        )


@router.get("/alert-rules/{rule_id}", response_model=dict)
def get_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get details of a specific alert rule."""
    rule = db.query(models.AlertRule).filter(models.AlertRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {rule_id} not found"
        )
    
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "resource_type": rule.resource_type.value if rule.resource_type else None,
        "metric_name": rule.metric_name,
        "condition": rule.condition.value if rule.condition else None,
        "threshold": rule.threshold,
        "severity": rule.severity.value if rule.severity else None,
        "enabled": rule.enabled,
        "notification_channels": rule.notification_channels,
        "cooldown_minutes": rule.cooldown_minutes,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
    }


@router.patch("/alert-rules/{rule_id}", response_model=dict)
def update_alert_rule(
    rule_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    threshold: Optional[float] = None,
    enabled: Optional[bool] = None,
    severity: Optional[str] = None,
    notification_channels: Optional[List[str]] = None,
    cooldown_minutes: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Update an alert rule."""
    rule = db.query(models.AlertRule).filter(models.AlertRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {rule_id} not found"
        )
    
    if name is not None:
        rule.name = name
    if description is not None:
        rule.description = description
    if threshold is not None:
        rule.threshold = threshold
    if enabled is not None:
        rule.enabled = enabled
    if severity is not None:
        rule.severity = severity
    if notification_channels is not None:
        rule.notification_channels = notification_channels
    if cooldown_minutes is not None:
        rule.cooldown_minutes = cooldown_minutes
    
    db.commit()
    db.refresh(rule)
    
    return {"id": rule.id, "name": rule.name, "status": "updated"}


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete an alert rule."""
    rule = db.query(models.AlertRule).filter(models.AlertRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {rule_id} not found"
        )
    
    db.delete(rule)
    db.commit()


@router.post("/alert-rules/{rule_id}/test", response_model=dict)
def test_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    """Test an alert rule evaluation."""
    from app.services.infrastructure.alert_evaluator import AlertEvaluator
    
    rule = db.query(models.AlertRule).filter(models.AlertRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {rule_id} not found"
        )
    
    evaluator = AlertEvaluator(db)
    triggered, resolved = evaluator.evaluate_rule(rule)
    
    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "triggered": triggered,
        "resolved": resolved,
        "message": f"Evaluated rule: {triggered} triggered, {resolved} resolved"
    }


@router.get("/alerts/infrastructure", response_model=List[dict])
def list_infrastructure_alerts(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List infrastructure alerts."""
    query = db.query(models.Alert).filter(
        models.Alert.alert_rule_id.isnot(None)
    )
    
    if status_filter:
        query = query.filter(models.Alert.status == status_filter)
    if severity:
        query = query.filter(models.Alert.severity == severity)
    
    alerts = query.order_by(models.Alert.triggered_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": a.id,
            "alert_rule_id": a.alert_rule_id,
            "resource_type": a.resource_type,
            "resource_id": a.resource_id,
            "metric_name": a.message.split(":")[0] if ":" in a.message else None,
            "metric_value": a.metric_value,
            "threshold": a.threshold,
            "severity": a.severity,
            "message": a.message,
            "status": a.status or ("resolved" if a.resolved else "active"),
            "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            "acknowledged": a.acknowledged,
            "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            "acknowledged_by": a.acknowledged_by,
            "resolved": a.resolved,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None
        }
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/acknowledge", response_model=dict)
def acknowledge_alert(
    alert_id: int,
    acknowledged_by: str = "system",
    db: Session = Depends(get_db)
):
    """Acknowledge an alert."""
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    alert.acknowledged = True
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = acknowledged_by
    alert.status = "acknowledged"
    
    db.commit()
    db.refresh(alert)
    
    return {
        "id": alert.id,
        "status": alert.status,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
    }


@router.post("/alerts/{alert_id}/resolve", response_model=dict)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """Resolve an alert."""
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    alert.resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    alert.status = "resolved"
    
    db.commit()
    db.refresh(alert)
    
    return {
        "id": alert.id,
        "status": alert.status,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
    }


# ============================================================================
# Enhanced Server Management Endpoints (Phase 3.5)
# ============================================================================

@router.post("/servers/{server_id}/test-connection", response_model=dict)
async def test_server_connection(server_id: int, db: Session = Depends(get_db)):
    """Test SSH connection to a server."""
    server = db.query(models.MonitoredServer).filter(
        models.MonitoredServer.id == server_id
    ).first()
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server {server_id} not found"
        )
    
    success, error = await ssh_service.test_connection(server, db)
    
    return {
        "server_id": server.id,
        "hostname": server.hostname,
        "connection_success": success,
        "error": error
    }


@router.post("/servers/bulk-enable", response_model=dict)
def bulk_enable_monitoring(server_ids: List[int], db: Session = Depends(get_db)):
    """Enable monitoring for multiple servers."""
    servers = db.query(models.MonitoredServer).filter(
        models.MonitoredServer.id.in_(server_ids)
    ).all()
    
    for server in servers:
        server.monitoring_enabled = True
    
    db.commit()
    
    return {
        "enabled": len(servers),
        "server_ids": [s.id for s in servers]
    }


@router.post("/servers/bulk-disable", response_model=dict)
def bulk_disable_monitoring(server_ids: List[int], db: Session = Depends(get_db)):
    """Disable monitoring for multiple servers."""
    servers = db.query(models.MonitoredServer).filter(
        models.MonitoredServer.id.in_(server_ids)
    ).all()
    
    for server in servers:
        server.monitoring_enabled = False
    
    db.commit()
    
    return {
        "disabled": len(servers),
        "server_ids": [s.id for s in servers]
    }


# ============================================================================
# Scheduler Control Endpoints (Phase 3.5)
# ============================================================================

@router.post("/scheduler/trigger-collection", response_model=dict)
def trigger_collection():
    """Manually trigger infrastructure data collection for all servers."""
    results = collect_all_servers()
    return results


@router.get("/scheduler/status", response_model=dict)
def get_scheduler_status():
    """Get scheduler status and job information."""
    # This would need to integrate with APScheduler to get real status
    # For now, return a simple status
    return {
        "status": "running",
        "jobs": [
            {
                "id": "infrastructure_collection",
                "name": "Infrastructure Data Collection",
                "interval": "5 minutes",
                "enabled": True
            }
        ]
    }


# ============================================================================
# Health Check Endpoint (Phase 6)
# ============================================================================

@router.get("/health/detailed", response_model=dict)
def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check for infrastructure monitoring system."""
    from datetime import datetime, timezone
    
    try:
        # Check database connectivity
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Get infrastructure statistics
    try:
        total_servers = db.query(models.MonitoredServer).count()
        online_servers = db.query(models.MonitoredServer).filter(
            models.MonitoredServer.status == models.ServerStatus.ONLINE
        ).count()
        enabled_servers = db.query(models.MonitoredServer).filter(
            models.MonitoredServer.monitoring_enabled == True
        ).count()
        
        active_alerts = db.query(models.Alert).filter(
            models.Alert.status == "active"
        ).count()
        
        alert_rules = db.query(models.AlertRule).filter(
            models.AlertRule.enabled == True
        ).count()
        
        infrastructure_stats = {
            "servers": {
                "total": total_servers,
                "online": online_servers,
                "monitoring_enabled": enabled_servers
            },
            "alerts": {
                "active": active_alerts,
                "rules_enabled": alert_rules
            },
            "storage": {
                "devices": db.query(models.StorageDevice).count(),
                "pools": db.query(models.StoragePool).count()
            },
            "databases": {
                "instances": db.query(models.DatabaseInstance).count()
            }
        }
    except Exception as e:
        infrastructure_stats = {"error": str(e)}
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "infrastructure": infrastructure_stats,
        "version": "1.0.0"
    }
