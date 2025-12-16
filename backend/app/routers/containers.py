"""Container management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.containers import (
    ContainerHost, Container, UpdateHistory, UpdatePolicy,
    MaintenanceWindow, VulnerabilityScan, ContainerBackup,
    AIRecommendation, UpdateNotification, RegistryCredential
)
from app.services.auth.auth_service import get_current_active_user as get_current_user
from app.models.users import User

router = APIRouter(prefix="/api/containers", tags=["containers"])

async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency to require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# ============================================================================
# Host Management Endpoints
# ============================================================================

@router.get("/hosts")
async def list_hosts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enabled: Optional[bool] = None,
    runtime_type: Optional[str] = None
):
    """List all container hosts."""
    query = db.query(ContainerHost)
    if enabled is not None:
        query = query.filter(ContainerHost.enabled == enabled)
    if runtime_type:
        query = query.filter(ContainerHost.runtime_type == runtime_type)
    hosts = query.all()
    return {"hosts": hosts, "total": len(hosts)}


@router.post("/hosts", status_code=status.HTTP_201_CREATED)
async def create_host(
    name: str,
    connection_type: str,
    connection_string: str,
    runtime_type: str = "docker",
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Create a new container host."""
    # Check if name already exists
    existing = db.query(ContainerHost).filter(ContainerHost.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Host with this name already exists")
    
    host = ContainerHost(
        name=name,
        connection_type=connection_type,
        connection_string=connection_string,
        runtime_type=runtime_type,
        description=description
    )
    db.add(host)
    db.commit()
    db.refresh(host)
    return host


@router.get("/hosts/{host_id}")
async def get_host(
    host_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get container host details."""
    host = db.query(ContainerHost).filter(ContainerHost.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.put("/hosts/{host_id}")
async def update_host(
    host_id: int,
    name: Optional[str] = None,
    enabled: Optional[bool] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update container host."""
    host = db.query(ContainerHost).filter(ContainerHost.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    if name is not None:
        host.name = name
    if enabled is not None:
        host.enabled = enabled
    if description is not None:
        host.description = description
    
    db.commit()
    db.refresh(host)
    return host


@router.delete("/hosts/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_host(
    host_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Delete container host."""
    host = db.query(ContainerHost).filter(ContainerHost.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    db.delete(host)
    db.commit()
    return None


@router.post("/hosts/{host_id}/sync")
async def sync_host(
    host_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Force sync containers from host."""
    host = db.query(ContainerHost).filter(ContainerHost.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # TODO: Implement container discovery
    return {"message": "Sync initiated", "host_id": host_id}


@router.get("/hosts/{host_id}/stats")
async def get_host_stats(
    host_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get host statistics."""
    host = db.query(ContainerHost).filter(ContainerHost.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    total_containers = db.query(Container).filter(Container.host_id == host_id).count()
    running = db.query(Container).filter(
        Container.host_id == host_id,
        Container.status == "running"
    ).count()
    updates_available = db.query(Container).filter(
        Container.host_id == host_id,
        Container.update_available == True
    ).count()
    
    return {
        "host_id": host_id,
        "total_containers": total_containers,
        "running_containers": running,
        "updates_available": updates_available
    }


# ============================================================================
# Container Management Endpoints
# ============================================================================

@router.get("")
async def list_containers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    host_id: Optional[int] = None,
    status: Optional[str] = None,
    update_available: Optional[bool] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0
):
    """List all containers."""
    query = db.query(Container)
    
    if host_id is not None:
        query = query.filter(Container.host_id == host_id)
    if status:
        query = query.filter(Container.status == status)
    if update_available is not None:
        query = query.filter(Container.update_available == update_available)
    
    total = query.count()
    containers = query.offset(offset).limit(limit).all()
    
    return {
        "containers": containers,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{container_id}")
async def get_container(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get container details."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    return container


@router.post("/{container_id}/start")
async def start_container(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start container."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    # TODO: Implement container start via runtime provider
    return {"message": "Container start initiated", "container_id": container_id}


@router.post("/{container_id}/stop")
async def stop_container(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stop container."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    # TODO: Implement container stop via runtime provider
    return {"message": "Container stop initiated", "container_id": container_id}


@router.post("/{container_id}/restart")
async def restart_container(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restart container."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    # TODO: Implement container restart via runtime provider
    return {"message": "Container restart initiated", "container_id": container_id}


# ============================================================================
# Update Management Endpoints
# ============================================================================

@router.get("/updates")
async def list_available_updates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    host_id: Optional[int] = None
):
    """List containers with available updates."""
    query = db.query(Container).filter(Container.update_available == True)
    
    if host_id is not None:
        query = query.filter(Container.host_id == host_id)
    
    containers = query.all()
    return {"containers": containers, "total": len(containers)}


@router.post("/updates/check")
async def check_for_updates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    host_id: Optional[int] = None,
    container_id: Optional[int] = None
):
    """Check for updates."""
    # TODO: Implement update checking
    return {"message": "Update check initiated"}


@router.post("/updates/{container_id}/execute")
async def execute_update(
    container_id: int,
    dry_run: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute container update."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    if not container.update_available:
        raise HTTPException(status_code=400, detail="No update available")
    
    # Create update history record
    update = UpdateHistory(
        container_id=container_id,
        from_tag=container.current_tag,
        from_digest=container.current_digest,
        to_tag=container.available_tag,
        to_digest=container.available_digest,
        dry_run=dry_run,
        triggered_by=f"user:{current_user.id}"
    )
    db.add(update)
    db.commit()
    
    # TODO: Implement actual update execution
    
    return {"message": "Update initiated", "update_id": update.id, "dry_run": dry_run}


@router.get("/updates/history")
async def get_update_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    container_id: Optional[int] = None,
    limit: int = Query(50, le=500)
):
    """Get update history."""
    query = db.query(UpdateHistory).order_by(UpdateHistory.created_at.desc())
    
    if container_id is not None:
        query = query.filter(UpdateHistory.container_id == container_id)
    
    history = query.limit(limit).all()
    return {"history": history, "total": len(history)}


# ============================================================================
# Policy Management Endpoints
# ============================================================================

@router.get("/policies")
async def list_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enabled: Optional[bool] = None
):
    """List update policies."""
    query = db.query(UpdatePolicy)
    if enabled is not None:
        query = query.filter(UpdatePolicy.enabled == enabled)
    
    policies = query.all()
    return {"policies": policies, "total": len(policies)}


@router.post("/policies", status_code=status.HTTP_201_CREATED)
async def create_policy(
    name: str,
    scope: str,
    auto_approve: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Create update policy."""
    policy = UpdatePolicy(
        name=name,
        scope=scope,
        auto_approve=auto_approve
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/policies/{policy_id}")
async def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get policy details."""
    policy = db.query(UpdatePolicy).filter(UpdatePolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.put("/policies/{policy_id}")
async def update_policy(
    policy_id: int,
    enabled: Optional[bool] = None,
    auto_approve: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update policy."""
    policy = db.query(UpdatePolicy).filter(UpdatePolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if enabled is not None:
        policy.enabled = enabled
    if auto_approve is not None:
        policy.auto_approve = auto_approve
    
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Delete policy."""
    policy = db.query(UpdatePolicy).filter(UpdatePolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    db.delete(policy)
    db.commit()
    return None


# ============================================================================
# Security & Scanning Endpoints
# ============================================================================

@router.post("/security/scan/{container_id}")
async def scan_container(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Scan container for vulnerabilities."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    # Create scan record
    scan = VulnerabilityScan(
        container_id=container_id,
        image=container.image,
        image_digest=container.current_digest
    )
    db.add(scan)
    db.commit()
    
    # TODO: Implement Trivy scan
    
    return {"message": "Scan initiated", "scan_id": scan.id}


@router.get("/security/scans")
async def list_scans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    container_id: Optional[int] = None,
    limit: int = Query(50, le=500)
):
    """List vulnerability scans."""
    query = db.query(VulnerabilityScan).order_by(VulnerabilityScan.scanned_at.desc())
    
    if container_id is not None:
        query = query.filter(VulnerabilityScan.container_id == container_id)
    
    scans = query.limit(limit).all()
    return {"scans": scans, "total": len(scans)}


@router.get("/security/scans/{scan_id}")
async def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get scan details."""
    scan = db.query(VulnerabilityScan).filter(VulnerabilityScan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/security/summary")
async def get_security_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get security summary across all containers."""
    total_containers = db.query(Container).count()
    scanned = db.query(Container).filter(Container.last_scan_id.isnot(None)).count()
    
    critical_cves = db.query(Container).filter(Container.critical_cves > 0).count()
    high_cves = db.query(Container).filter(Container.high_cves > 0).count()
    
    return {
        "total_containers": total_containers,
        "scanned_containers": scanned,
        "containers_with_critical": critical_cves,
        "containers_with_high": high_cves
    }


# ============================================================================
# Backup & Restore Endpoints
# ============================================================================

@router.post("/backup/{container_id}")
async def create_backup(
    container_id: int,
    backup_type: str = "config",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create container backup."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    backup = ContainerBackup(
        container_id=container_id,
        backup_type=backup_type,
        container_name=container.name,
        image=container.image,
        image_digest=container.current_digest,
        backup_path=f"/backups/{container.name}_{datetime.now().isoformat()}"
    )
    db.add(backup)
    db.commit()
    
    # TODO: Implement backup execution
    
    return {"message": "Backup initiated", "backup_id": backup.id}


@router.get("/backups")
async def list_backups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    container_id: Optional[int] = None,
    limit: int = Query(50, le=500)
):
    """List backups."""
    query = db.query(ContainerBackup).order_by(ContainerBackup.created_at.desc())
    
    if container_id is not None:
        query = query.filter(ContainerBackup.container_id == container_id)
    
    backups = query.limit(limit).all()
    return {"backups": backups, "total": len(backups)}


@router.get("/backups/{backup_id}")
async def get_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get backup details."""
    backup = db.query(ContainerBackup).filter(ContainerBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    return backup


@router.post("/restore/{backup_id}")
async def restore_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Restore from backup."""
    backup = db.query(ContainerBackup).filter(ContainerBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    # TODO: Implement backup restore
    
    return {"message": "Restore initiated", "backup_id": backup_id}


@router.delete("/backups/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Delete backup."""
    backup = db.query(ContainerBackup).filter(ContainerBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    db.delete(backup)
    db.commit()
    return None


# ============================================================================
# AI & Notifications Endpoints
# ============================================================================

@router.get("/recommendations/{container_id}")
async def get_recommendations(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AI recommendations for container."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    recommendations = db.query(AIRecommendation).filter(
        AIRecommendation.container_id == container_id,
        AIRecommendation.status == "pending"
    ).all()
    
    return {"recommendations": recommendations, "total": len(recommendations)}


@router.get("/notifications")
async def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    container_id: Optional[int] = None,
    limit: int = Query(50, le=500)
):
    """List notifications."""
    query = db.query(UpdateNotification).order_by(UpdateNotification.created_at.desc())
    
    if container_id is not None:
        query = query.filter(UpdateNotification.container_id == container_id)
    
    notifications = query.limit(limit).all()
    return {"notifications": notifications, "total": len(notifications)}


# ============================================================================
# Registry Credentials Endpoints
# ============================================================================

@router.get("/registries")
async def list_registries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List registry credentials."""
    registries = db.query(RegistryCredential).all()
    # Don't return sensitive fields
    return {"registries": [
        {
            "id": r.id,
            "name": r.name,
            "registry_url": r.registry_url,
            "username": r.username,
            "enabled": r.enabled,
            "validation_status": r.validation_status
        }
        for r in registries
    ]}


@router.post("/registries", status_code=status.HTTP_201_CREATED)
async def create_registry(
    name: str,
    registry_url: str,
    username: str,
    password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Create registry credential."""
    registry = RegistryCredential(
        name=name,
        registry_url=registry_url,
        username=username,
        password=password  # TODO: Encrypt
    )
    db.add(registry)
    db.commit()
    db.refresh(registry)
    return {"id": registry.id, "name": registry.name}
