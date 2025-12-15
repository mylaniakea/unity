"""Authentication CRUD operations."""
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional
from . import auth_models, auth_schemas
from . import auth


# Users

def get_user(db: Session, user_id: int) -> Optional[auth_models.User]:
    """Get user by ID."""
    return db.query(auth_models.User).filter(auth_models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[auth_models.User]:
    """Get user by username."""
    return db.query(auth_models.User).filter(auth_models.User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[auth_models.User]:
    """Get all users with pagination."""
    return db.query(auth_models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: auth_schemas.UserCreate) -> auth_models.User:
    """Create a new user."""
    hashed_password = auth.get_password_hash(user.password)
    db_user = auth_models.User(
        username=user.username,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# API Keys

def get_api_key(db: Session, key_id: int) -> Optional[auth_models.APIKey]:
    """Get API key by ID."""
    return db.query(auth_models.APIKey).filter(auth_models.APIKey.id == key_id).first()


def get_all_api_keys(db: Session) -> List[auth_models.APIKey]:
    """Get all API keys (for authentication checks)."""
    return db.query(auth_models.APIKey).filter(auth_models.APIKey.is_active == True).all()


def get_user_api_keys(db: Session, user_id: int) -> List[auth_models.APIKey]:
    """Get all API keys for a specific user."""
    return db.query(auth_models.APIKey).filter(auth_models.APIKey.user_id == user_id).all()


def create_api_key(
    db: Session, 
    api_key_create: auth_schemas.APIKeyCreate, 
    user_id: int
) -> tuple[auth_models.APIKey, str]:
    """
    Create a new API key.
    
    Returns:
        Tuple of (APIKey model, plaintext key)
    """
    # Generate the actual API key
    plaintext_key = auth.generate_api_key()
    
    # Hash the key for storage
    key_hash = auth.get_api_key_hash(plaintext_key)
    
    db_api_key = auth_models.APIKey(
        key_hash=key_hash,
        name=api_key_create.name,
        user_id=user_id,
    )
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    return db_api_key, plaintext_key


def update_api_key_last_used(db: Session, key_id: int) -> None:
    """Update the last_used_at timestamp for an API key."""
    db.query(auth_models.APIKey).filter(auth_models.APIKey.id == key_id).update(
        {"last_used_at": func.now()}
    )
    db.commit()


def deactivate_api_key(db: Session, key_id: int) -> Optional[auth_models.APIKey]:
    """Deactivate an API key (soft delete)."""
    db_api_key = get_api_key(db, key_id)
    if db_api_key:
        db_api_key.is_active = False
        db.commit()
        db.refresh(db_api_key)
    return db_api_key
