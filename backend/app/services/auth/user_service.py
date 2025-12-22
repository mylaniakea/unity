"""User management service."""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.users import User
from app.services.auth.password import hash_password, verify_password
from app.core.config import settings


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    role: str = "viewer",
    is_superuser: bool = False
) -> User:
    """
    Create a new user.
    
    Args:
        db: Database session
        username: Unique username
        email: User email
        password: Plain text password (will be hashed)
        full_name: Optional full name
        role: User role (admin, editor, viewer)
        is_superuser: Whether user is superuser
        
    Returns:
        Created User model
    """
    hashed_password = hash_password(password)
    
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role=role,
        is_active=True,
        is_superuser=is_superuser
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password.
    
    Args:
        db: Database session
        username: Username
        password: Plain text password
        
    Returns:
        User model if authenticated, None if invalid credentials
    """
    user = get_user_by_username(db, username)
    
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    return user


def update_user_password(db: Session, user_id: str, new_password: str) -> bool:
    """
    Update user password.
    
    Args:
        db: Database session
        user_id: User ID
        new_password: New plain text password
        
    Returns:
        True if updated, False if user not found
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return False
    
    user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return True


def update_user_profile(
    db: Session,
    user_id: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None
) -> Optional[User]:
    """
    Update user profile information.
    
    Args:
        db: Database session
        user_id: User ID
        email: New email (optional)
        full_name: New full name (optional)
        
    Returns:
        Updated User model or None if not found
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return None
    
    if email is not None:
        user.email = email
    
    if full_name is not None:
        user.full_name = full_name
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user


def list_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False
) -> list[User]:
    """
    List users with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        include_inactive: Whether to include inactive users
        
    Returns:
        List of User models
    """
    query = db.query(User)
    
    if not include_inactive:
        query = query.filter(User.is_active == True)
    
    return query.offset(skip).limit(limit).all()


def deactivate_user(db: Session, user_id: str) -> bool:
    """
    Deactivate (soft delete) a user.
    
    Args:
        db: Database session
        user_id: User ID to deactivate
        
    Returns:
        True if deactivated, False if not found
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return False
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return True


def update_user_role(db: Session, user_id: str, new_role: str) -> Optional[User]:
    """
    Update user role.
    
    Args:
        db: Database session
        user_id: User ID
        new_role: New role (admin, editor, viewer)
        
    Returns:
        Updated User model or None if not found
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return None
    
    user.role = new_role
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user
