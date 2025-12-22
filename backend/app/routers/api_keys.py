"""API key management router."""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.users import User
from app.models.auth import APIKey
from app.services.auth.api_key_manager import create_api_key, list_user_api_keys, revoke_api_key
from app.services.auth.audit_service import log_api_key_creation, log_api_key_revocation


router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# Request/Response Models
class APIKeyCreate(BaseModel):
    """API key creation request."""
    name: str = Field(..., min_length=1, max_length=100, description="Descriptive name for the key")
    scopes: Optional[List[str]] = Field(None, description="Optional permission scopes")
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="Expiration in days (1-365)")


class APIKeyResponse(BaseModel):
    """API key response (without plaintext key)."""
    id: str
    name: str
    scopes: Optional[List[str]]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class APIKeyCreated(BaseModel):
    """Response when API key is created (includes plaintext key)."""
    api_key: str = Field(..., description="Plaintext API key - save this, it won't be shown again!")
    key_info: APIKeyResponse


class APIKeyUpdate(BaseModel):
    """API key update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    scopes: Optional[List[str]] = None


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent."""
    return request.headers.get("User-Agent")


@router.post("", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key for the current user.
    
    The plaintext key is only returned once during creation.
    Store it securely - you won't be able to retrieve it again.
    """
    # Create API key
    api_key_model, plaintext_key = create_api_key(
        db=db,
        user_id=str(current_user.id),
        name=key_data.name,
        scopes=key_data.scopes,
        expires_days=key_data.expires_days
    )
    
    # Log creation
    log_api_key_creation(
        db=db,
        user_id=str(current_user.id),
        api_key_id=str(api_key_model.id),
        api_key_name=key_data.name,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return {
        "api_key": plaintext_key,
        "key_info": api_key_model
    }


@router.get("", response_model=List[APIKeyResponse])
async def list_api_keys(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current user.
    
    By default, only active (non-revoked) keys are returned.
    """
    keys = list_user_api_keys(
        db=db,
        user_id=str(current_user.id),
        include_inactive=include_inactive
    )
    
    return keys


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific API key."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return api_key


@router.put("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    key_data: APIKeyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an API key's name or scopes.
    
    Note: The key itself cannot be changed. If you need a new key, revoke this one and create a new one.
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Update fields
    if key_data.name is not None:
        api_key.name = key_data.name
    
    if key_data.scopes is not None:
        api_key.scopes = key_data.scopes
    
    db.commit()
    db.refresh(api_key)
    
    return api_key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Revoke (deactivate) an API key.
    
    Revoked keys cannot be reactivated. Create a new key if needed.
    """
    success = revoke_api_key(
        db=db,
        key_id=key_id,
        user_id=str(current_user.id)
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Log revocation
    log_api_key_revocation(
        db=db,
        user_id=str(current_user.id),
        api_key_id=key_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return None
