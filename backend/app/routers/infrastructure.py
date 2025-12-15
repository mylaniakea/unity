"""Infrastructure monitoring API endpoints for Phase 3: BD-Store Integration."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import logging

from app.database import get_db
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
