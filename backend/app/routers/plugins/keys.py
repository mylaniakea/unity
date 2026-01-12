"""
Plugin API Key Management

Admin endpoints for managing API keys for external plugins.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.database import get_db
from app.core.dependencies import get_tenant_id
from app.models import PluginAPIKey, Plugin, User
from app.services.auth import get_current_active_user
from app.services.plugin_security import PluginSecurityService

router = APIRouter(
    prefix="/plugins/keys",
    tags=["plugin-keys"],
    responses={404: {"description": "Not found"}},
)


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key"""
    plugin_id: str = Field(..., description="Plugin ID")
    name: str = Field(..., description="Descriptive name for the key")
    permissions: List[str] = Field(
        default=["report_metrics", "update_health", "get_config"],
        description="Permissions for the key"
    )
    expires_days: Optional[int] = Field(None, description="Days until expiration (None = no expiration)")


class APIKeyResponse(BaseModel):
    """Response with API key details"""
    id: int
    plugin_id: str
    name: str
    permissions: List[str]
    is_active: bool
    created_at: str
    expires_at: Optional[str]
    last_used: Optional[str]
    uses_count: int


class CreateAPIKeyResponse(BaseModel):
    """Response when creating a new API key"""
    api_key: str  # Only returned once
    key_info: APIKeyResponse


@router.post("", response_model=CreateAPIKeyResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key for an external plugin.
    
    **Authentication:** JWT token required
    **Authorization:** Admin only
    
    **Important:** The plain API key is only returned once. Store it securely!
    """
    # Check authorization
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can create API keys"
        )
    
    # Validate plugin ID
    PluginSecurityService.validate_plugin_id(request.plugin_id)
    
    # Verify plugin exists and is external
    stmt = select(Plugin).where(Plugin.id == request.plugin_id)
    result = db.execute(stmt)
    plugin = result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {request.plugin_id} not found"
        )
    
    if not plugin.external:
        raise HTTPException(
            status_code=400,
            detail="API keys can only be created for external plugins"
        )
    
    # Generate API key
    api_key = PluginSecurityService.generate_api_key()
    key_hash = PluginSecurityService.hash_api_key(api_key)
    
    # Calculate expiration
    expires_at = None
    if request.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_days)
    
    # Create key record
    key_record = PluginAPIKey(
        plugin_id=request.plugin_id,
        key_hash=key_hash,
        name=request.name,
        permissions=request.permissions,
        expires_at=expires_at,
        created_by=current_user.id
    )
    
    db.add(key_record)
    db.commit()
    db.refresh(key_record)
    
    # Log action
    PluginSecurityService.log_plugin_action(
        current_user, request.plugin_id, "create_api_key",
        {"key_name": request.name, "permissions": request.permissions}
    )
    
    return CreateAPIKeyResponse(
        api_key=api_key,
        key_info=APIKeyResponse(
            id=key_record.id,
            plugin_id=key_record.plugin_id,
            name=key_record.name,
            permissions=key_record.permissions,
            is_active=key_record.is_active,
            created_at=key_record.created_at.isoformat(),
            expires_at=key_record.expires_at.isoformat() if key_record.expires_at else None,
            last_used=key_record.last_used.isoformat() if key_record.last_used else None,
            uses_count=key_record.uses_count
        )
    )


@router.get("/{plugin_id}", response_model=List[APIKeyResponse])
async def list_plugin_api_keys(
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all API keys for a plugin.
    
    **Authentication:** JWT token required
    **Authorization:** Admin only
    """
    # Check authorization
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can view API keys"
        )
    
    # Validate plugin ID
    PluginSecurityService.validate_plugin_id(plugin_id)
    
    stmt = select(PluginAPIKey).where(PluginAPIKey.plugin_id == plugin_id)
    result = db.execute(stmt)
    keys = result.scalars().all()
    
    return [
        APIKeyResponse(
            id=k.id,
            plugin_id=k.plugin_id,
            name=k.name,
            permissions=k.permissions,
            is_active=k.is_active,
            created_at=k.created_at.isoformat(),
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            last_used=k.last_used.isoformat() if k.last_used else None,
            uses_count=k.uses_count
        )
        for k in keys
    ]


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Revoke an API key.
    
    **Authentication:** JWT token required
    **Authorization:** Admin only
    """
    # Check authorization
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can revoke API keys"
        )
    
    stmt = select(PluginAPIKey).where(PluginAPIKey.id == key_id)
    result = db.execute(stmt)
    key_record = result.scalar_one_or_none()
    
    if not key_record:
        raise HTTPException(
            status_code=404,
            detail=f"API key {key_id} not found"
        )
    
    # Mark as revoked
    key_record.is_active = False
    key_record.revoked_at = datetime.utcnow()
    key_record.revoked_by = current_user.id
    db.commit()
    
    # Log action
    PluginSecurityService.log_plugin_action(
        current_user, key_record.plugin_id, "revoke_api_key",
        {"key_id": key_id, "key_name": key_record.name}
    )
    
    return {
        "success": True,
        "message": f"API key {key_id} revoked"
    }
