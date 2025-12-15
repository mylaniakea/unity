"""Authentication utilities and dependencies."""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from . import auth_models, auth_crud
from .database import SessionLocal
from .config import get_settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# API Key header security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

settings = get_settings()


def get_db():
    """Database dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: The plaintext password
        hashed_password: The hashed password to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plaintext password to hash
        
    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


def generate_api_key() -> str:
    """
    Generate a cryptographically secure API key.
    
    Returns:
        A 64-character hexadecimal API key
    """
    return secrets.token_hex(32)


def get_api_key_hash(api_key: str) -> str:
    """
    Hash an API key for secure storage.
    
    Args:
        api_key: The API key to hash
        
    Returns:
        The hashed API key
    """
    return pwd_context.hash(api_key)


def verify_api_key(api_key: str, hashed_api_key: str) -> bool:
    """
    Verify an API key against its hash.
    
    Args:
        api_key: The plaintext API key
        hashed_api_key: The hashed API key to verify against
        
    Returns:
        True if API key matches, False otherwise
    """
    return pwd_context.verify(api_key, hashed_api_key)


def authenticate_user(db: Session, username: str, password: str) -> Optional[auth_models.User]:
    """
    Authenticate a user by username and password.
    
    Args:
        db: Database session
        username: Username to authenticate
        password: Password to verify
        
    Returns:
        User object if authentication succeeds, None otherwise
    """
    user = auth_crud.get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def get_current_user(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> auth_models.User:
    """
    Dependency to get the current authenticated user from API key.
    
    Args:
        api_key: API key from X-API-Key header
        db: Database session
        
    Returns:
        Authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    # Check if authentication is disabled (for development/testing)
    if hasattr(settings, 'disable_auth') and settings.disable_auth:
        # Return a mock user for unauthenticated access
        mock_user = auth_models.User(
            id=0,
            username="dev_user",
            hashed_password="",
            is_active=True
        )
        return mock_user
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Find matching API key
    api_keys = auth_crud.get_all_api_keys(db)
    db_api_key = None
    
    for key in api_keys:
        if key.is_active and verify_api_key(api_key, key.key_hash):
            db_api_key = key
            break
    
    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Update last used timestamp
    auth_crud.update_api_key_last_used(db, db_api_key.id)
    
    # Get the user associated with this API key
    user = auth_crud.get_user(db, db_api_key.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    return user
