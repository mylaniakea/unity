"""User service functions for authentication and user management."""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.orm import make_transient

from app.models.users import User
from app.services.auth.password import hash_password, verify_password


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """
    Get user by ID.
    
    Handles both UUID and integer IDs for schema compatibility.
    """
    try:
        # Try UUID first
        import uuid
        uuid_id = uuid.UUID(user_id)
        return db.query(User).filter(User.id == uuid_id).first()
    except (ValueError, TypeError):
        # Fallback to raw SQL for integer IDs
        result = db.execute(
            text("SELECT id, username, email, hashed_password, role, is_active, is_superuser FROM users WHERE id = :id"),
            {"id": int(user_id) if user_id.isdigit() else user_id}
        )
        row = result.fetchone()
        if not row:
            return None
        
        # Create transient user object
        user = User()
        user.id = row[0]
        user.username = row[1]
        user.email = row[2]
        user.hashed_password = row[3]
        user.role = row[4] or "viewer"
        user.is_active = row[5]
        user.is_superuser = row[6] or False
        make_transient(user)
        return user


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
    
    Uses raw SQL to avoid schema mismatch issues (integer ID vs UUID).
    
    Args:
        db: Database session
        username: Username
        password: Plain text password
        
    Returns:
        User model if authenticated, None if invalid credentials
    """
    # Use raw SQL to avoid schema mismatch (database has integer IDs, model expects UUID)
    result = db.execute(
        text("SELECT id, username, email, hashed_password, role, is_active, is_superuser FROM users WHERE username = :username"),
        {"username": username}
    )
    row = result.fetchone()
    if not row:
        return None
    
    # Verify password
    if not verify_password(password, row[3]):  # row[3] is hashed_password
        return None
    
    if not row[5]:  # row[5] is is_active
        return None
    
    # Create a minimal user object that works with integer IDs
    user = User()
    # Store integer ID as-is (will be converted to string when needed)
    user.id = row[0]
    user.username = row[1]
    user.email = row[2]
    user.hashed_password = row[3]
    user.role = row[4] or "viewer"
    user.is_active = row[5]
    user.is_superuser = row[6] or False
    # Make transient so SQLAlchemy doesn't track it (prevents update attempts)
    make_transient(user)
    
    # Don't try to update last_login_at - it will fail with schema mismatch
    # The user can still authenticate successfully
    
    return user


def update_user_role(
    db: Session,
    user_id: str,
    new_role: str
) -> Optional[User]:
    """
    Update a user's role.
    
    Args:
        db: Database session
        user_id: User ID
        new_role: New role (admin, editor, viewer)
        
    Returns:
        Updated User model, or None if user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    user.role = new_role
    db.commit()
    db.refresh(user)
    
    return user


def deactivate_user(db: Session, user_id: str) -> bool:
    """
    Deactivate a user (soft delete).
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        True if user was deactivated, False if user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    user.is_active = False
    db.commit()
    
    return True


def change_user_password(
    db: Session,
    user_id: str,
    new_password: str
) -> bool:
    """
    Change a user's password.
    
    Args:
        db: Database session
        user_id: User ID
        new_password: New plain text password (will be hashed)
        
    Returns:
        True if password was changed, False if user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    user.hashed_password = hash_password(new_password)
    db.commit()
    
    return True


def list_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False
) -> list[User]:
    """List users with pagination."""
    query = db.query(User)
    if not include_inactive:
        query = query.filter(User.is_active == True)
    return query.offset(skip).limit(limit).all()


def update_user_profile(
    db: Session,
    user_id: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None
) -> Optional[User]:
    """Update user profile information."""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    if email is not None:
        user.email = email
    if full_name is not None:
        user.full_name = full_name
    
    db.commit()
    db.refresh(user)
    return user


def update_user_password(
    db: Session,
    user_id: str,
    new_password: str
) -> bool:
    """Update user password (alias for change_user_password)."""
    return change_user_password(db, user_id, new_password)
