"""
Docker Host Management API

Provides RESTful endpoints for managing Docker host connections
and monitoring host health.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime

from app.core.dependencies import get_tenant_id
from app.database import get_db
from app.models import DockerHost, User
from app.services.auth import get_current_active_user
from app.schemas_docker import (
    DockerHostCreate,
    DockerHostUpdate,
    DockerHostInfo,
    DockerHostDetail,
    DockerHostListResponse,
    DockerHostHealthResponse,
    DockerActionResponse
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/docker/hosts",
    tags=["docker-hosts"],
    responses={404: {"description": "Not found"}},
)


import docker

async def check_host_health(host: DockerHost) -> dict:
    """
    Check the health of a Docker host.
    """
    try:
        client = docker.DockerClient(base_url=host.host_url)
        info = client.info()
        containers = client.containers.list()
        
        return {
            "healthy": True,
            "health_status": "healthy",
            "message": f"Docker daemon is reachable (v{info.get('ServerVersion', 'unknown')})",
            "container_count": info.get('Containers', 0),
            "details": {
                "version": info.get('ServerVersion'),
                "os": info.get('OperatingSystem'),
                "cpus": info.get('NCPU'),
                "memory": info.get('MemTotal')
            }
        }
    except Exception as e:
        logger.error(f"Error checking Docker host health for {host.name}: {e}")
        return {
            "healthy": False,
            "health_status": "unhealthy",
            "message": f"Failed to connect to Docker daemon: {str(e)}",
            "container_count": 0,
            "details": {"error": str(e)}
        }


@router.post("", response_model=DockerHostDetail, status_code=201)
async def create_host(
    host_data: DockerHostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Register a new Docker host.
    """
    # Check authorization
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can register Docker hosts"
        )

    # Check if host with same name already exists
    existing = db.execute(
        select(DockerHost).where(DockerHost.tenant_id == tenant_id, DockerHost.name == host_data.name)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Docker host with name '{host_data.name}' already exists"
        )

    # Create new host
    host = DockerHost(
        tenant_id=tenant_id,
        name=host_data.name,
        description=host_data.description,
        host_url=host_data.host_url,
        is_active=host_data.is_active,
        config=host_data.config,
        labels=host_data.labels,
        created_by=current_user.id
    )

    db.add(host)
    db.commit()
    db.refresh(host)

    logger.info(f"Docker host '{host.name}' registered by user {current_user.username}")

    return host


@router.get("", response_model=DockerHostListResponse)
async def list_hosts(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    List all registered Docker hosts.
    """
    query = select(DockerHost).where(DockerHost.tenant_id == tenant_id)

    # Apply filters
    if is_active is not None:
        query = query.where(DockerHost.is_active == is_active)

    query = query.order_by(DockerHost.name)

    result = db.execute(query)
    hosts = result.scalars().all()

    return DockerHostListResponse(
        hosts=hosts,
        total=len(hosts)
    )


@router.get("/{host_id}", response_model=DockerHostDetail)
async def get_host(
    host_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get detailed information about a specific Docker host.
    """
    host = db.execute(
        select(DockerHost).where(DockerHost.id == host_id, DockerHost.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not host:
        raise HTTPException(
            status_code=404,
            detail=f"Docker host with id {host_id} not found"
        )

    return host


@router.put("/{host_id}", response_model=DockerHostDetail)
async def update_host(
    host_id: int,
    host_data: DockerHostUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Update a Docker host.
    """
    # Check authorization
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can update Docker hosts"
        )

    host = db.execute(
        select(DockerHost).where(DockerHost.id == host_id, DockerHost.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not host:
        raise HTTPException(
            status_code=404,
            detail=f"Docker host with id {host_id} not found"
        )

    # Update fields
    update_data = host_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(host, key, value)

    host.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(host)

    logger.info(f"Docker host '{host.name}' updated by user {current_user.username}")

    return host


@router.delete("/{host_id}", response_model=DockerActionResponse)
async def delete_host(
    host_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Remove a Docker host.
    """
    # Check authorization
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can delete Docker hosts"
        )

    host = db.execute(
        select(DockerHost).where(DockerHost.id == host_id, DockerHost.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not host:
        raise HTTPException(
            status_code=404,
            detail=f"Docker host with id {host_id} not found"
        )

    host_name = host.name
    db.delete(host)
    db.commit()

    logger.info(f"Docker host '{host_name}' deleted by user {current_user.username}")

    return DockerActionResponse(
        success=True,
        message=f"Docker host '{host_name}' deleted successfully",
        host_id=host_id
    )


@router.get("/{host_id}/health", response_model=DockerHostHealthResponse)
async def check_host_health_endpoint(
    host_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Check Docker host connectivity and health status.
    """
    host = db.execute(
        select(DockerHost).where(DockerHost.id == host_id, DockerHost.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if not host:
        raise HTTPException(
            status_code=404,
            detail=f"Docker host with id {host_id} not found"
        )

    # Perform health check
    health_result = await check_host_health(host)

    # Update host health status
    host.last_health_check = datetime.utcnow()
    host.health_status = health_result["health_status"]
    host.health_message = health_result["message"]
    host.container_count = health_result.get("container_count", 0)

    db.commit()

    return DockerHostHealthResponse(
        host_id=host.id,
        host_name=host.name,
        healthy=health_result["healthy"],
        health_status=health_result["health_status"],
        message=health_result["message"],
        container_count=health_result.get("container_count"),
        details=health_result.get("details"),
        checked_at=host.last_health_check
    )