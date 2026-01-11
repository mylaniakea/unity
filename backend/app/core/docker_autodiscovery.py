"""
Docker Host Auto-discovery
"""

import os
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import DockerHost

logger = logging.getLogger(__name__)

async def autodiscover_docker_host(db: Session, tenant_id: str = "default"):
    """
    Auto-discover and register the local Docker socket if available.
    """
    socket_path = "/var/run/docker.sock"
    
    # Check if socket exists
    if not os.path.exists(socket_path):
        return None
    
    try:
        # Check if already registered
        existing = db.execute(
            select(DockerHost).where(
                DockerHost.tenant_id == tenant_id,
                DockerHost.host_url == f"unix://{socket_path}"
            )
        ).scalar_one_or_none()
        
        if existing:
            return existing
        
        # Create new host entry
        host = DockerHost(
            tenant_id=tenant_id,
            name="Local Docker",
            description="Auto-discovered local Docker socket",
            host_url=f"unix://{socket_path}",
            is_active=True,
            container_count=0
        )
        
        db.add(host)
        db.commit()
        db.refresh(host)
        
        return host
        
    except Exception as e:
        logger.error(f"Failed to auto-discover Docker host: {e}")
        db.rollback()
        return None
