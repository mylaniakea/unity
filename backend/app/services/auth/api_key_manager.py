"""API key generation and validation."""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.auth import APIKey
from app.core.config import settings


def generate_api_key() -> str:
    """
    Generate a secure random API key.
    
    Returns:
        API key string with prefix
    """
    random_part = secrets.token_urlsafe(32)
    return f"{settings.api_key_prefix}{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.
    
    Args:
        api_key: Plain text API key
        
    Returns:
        Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def create_api_key(
    db: Session,
    user_id: str,
    name: str,
    scopes: Optional[list[str]] = None,
    expires_days: Optional[int] = None
) -> tuple[APIKey, str]:
    """
    Create a new API key for a user.
    
    Args:
        db: Database session
        user_id: User ID to create key for
        name: Descriptive name for the key
        scopes: Optional list of permission scopes
        expires_days: Optional expiration in days (default from settings)
        
    Returns:
        Tuple of (APIKey model, plaintext_key)
        Note: Plaintext key is only returned once!
    """
    # Generate and hash the key
    plaintext_key = generate_api_key()
    key_hash = hash_api_key(plaintext_key)
    
    # Calculate expiration
    expires_at = None
    if expires_days is not None:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
    elif settings.api_key_expiry_days > 0:
        expires_at = datetime.utcnow() + timedelta(days=settings.api_key_expiry_days)
    
    # Create database record
    api_key = APIKey(
        user_id=user_id,
        key_hash=key_hash,
        name=name,
        scopes=scopes,
        expires_at=expires_at,
        is_active=True
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return api_key, plaintext_key


def validate_api_key(db: Session, api_key: str) -> Optional[APIKey]:
    """
    Validate an API key and return the associated key record.
    
    Args:
        db: Database session
        api_key: Plain text API key to validate
        
    Returns:
        APIKey model if valid, None if invalid/expired/inactive
    """
    key_hash = hash_api_key(api_key)
    
    # Query for the key
    db_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()
    
    if not db_key:
        return None
    
    # Check expiration
    if db_key.expires_at and db_key.expires_at < datetime.utcnow():
        return None
    
    # Update last used timestamp
    db_key.last_used_at = datetime.utcnow()
    db.commit()
    
    return db_key


def revoke_api_key(db: Session, key_id: str, user_id: str) -> bool:
    """
    Revoke (deactivate) an API key.
    
    Args:
        db: Database session
        key_id: API key ID to revoke
        user_id: User ID (for authorization check)
        
    Returns:
        True if revoked, False if not found or unauthorized
    """
    db_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user_id
    ).first()
    
    if not db_key:
        return False
    
    db_key.is_active = False
    db.commit()
    
    return True


def list_user_api_keys(db: Session, user_id: str, include_inactive: bool = False) -> list[APIKey]:
    """
    List all API keys for a user.
    
    Args:
        db: Database session
        user_id: User ID
        include_inactive: Whether to include revoked keys
        
    Returns:
        List of APIKey models
    """
    query = db.query(APIKey).filter(APIKey.user_id == user_id)
    
    if not include_inactive:
        query = query.filter(APIKey.is_active == True)
    
    return query.order_by(APIKey.created_at.desc()).all()
