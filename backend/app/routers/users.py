from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.core import *
from app.schemas.users import *
from app import models
from app.database import get_db
from app.services.auth import AuthService, get_current_active_user

router = APIRouter(prefix="/users", tags=["users"])


async def get_current_admin(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    """Dependency to require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/", response_model=List[User])
async def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """List all users (admin only)"""
    users = db.query(models.User).all()
    return users


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Create a new user (admin only)"""
    # Check if username already exists
    db_user = AuthService.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists (if provided)
    if user.email:
        db_user_by_email = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user_by_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Validate password length
    if len(user.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    # Validate role
    if user.role not in ["admin", "user", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'admin', 'user', or 'viewer'"
        )

    # Create user
    hashed_password = AuthService.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role or "user",
        is_superuser=(user.role == "admin")  # Keep is_superuser in sync
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Get user details (admin only)"""
    user = AuthService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Update user (admin only)"""
    # Get target user
    user = AuthService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admin from changing their own role
    if user.id == current_user.id and user_update.role is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )

    # Update email if provided
    if user_update.email is not None:
        # Check if email already exists
        if user_update.email:
            existing = db.query(models.User).filter(
                models.User.email == user_update.email,
                models.User.id != user_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        user.email = user_update.email

    # Update role if provided
    if user_update.role is not None:
        if user_update.role not in ["admin", "user", "viewer"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be 'admin', 'user', or 'viewer'"
            )
        user.role = user_update.role
        user.is_superuser = (user_update.role == "admin")  # Keep is_superuser in sync

    # Update is_active if provided
    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Delete user (admin only)"""
    # Get target user
    user = AuthService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    db.delete(user)
    db.commit()

    return {"message": f"User {user.username} deleted successfully"}
