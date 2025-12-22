"""User management router (admin-only)."""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.users import User
from app.services.auth.user_service import list_users, create_user, get_user_by_id, update_user_profile, deactivate_user, update_user_role, update_user_password, get_user_by_username, get_user_by_email


router = APIRouter(prefix="/users", tags=["User Management"], dependencies=[Depends(require_admin())])


# Request/Response Models
class UserResponse(BaseModel):
    """User response model."""
    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    is_superuser: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Admin user creation request."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: str = Field("viewer", pattern="^(admin|editor|viewer)$")
    is_superuser: bool = False


class UserUpdate(BaseModel):
    """User update request."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserRoleUpdate(BaseModel):
    """Role update request."""
    role: str = Field(..., pattern="^(admin|editor|viewer)$")


class UserPasswordReset(BaseModel):
    """Admin password reset request."""
    new_password: str = Field(..., min_length=8)


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserResponse]
    total: int
    skip: int
    limit: int


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """
    List all users (admin-only).
    
    Supports pagination and filtering by active status.
    """
    users = list_users(
        db=db,
        skip=skip,
        limit=limit,
        include_inactive=include_inactive
    )
    
    # Get total count
    from app.models.users import User as UserModel
    query = db.query(UserModel)
    if not include_inactive:
        query = query.filter(UserModel.is_active == True)
    total = query.count()
    
    return {
        "users": users,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user (admin-only).
    
    Admins can create users with any role, including admin and superuser.
    """
    # Check if username exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email exists
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Create user
    user = create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        role=user_data.role,
        is_superuser=user_data.is_superuser
    )
    
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user details by ID (admin-only)."""
    user = get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user details (admin-only).
    
    Can update email, full name, and active status.
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update email and full_name via service
    if user_data.email is not None or user_data.full_name is not None:
        user = update_user_profile(
            db=db,
            user_id=user_id,
            email=user_data.email,
            full_name=user_data.full_name
        )
    
    # Update is_active directly
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
        db.commit()
        db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Deactivate (soft delete) a user (admin-only).
    
    Users are not permanently deleted, just marked as inactive.
    """
    success = deactivate_user(db, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return None


@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db)
):
    """
    Change a user's role (admin-only).
    
    Available roles: admin, editor, viewer
    """
    user = update_user_role(db, user_id, role_data.role)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/{user_id}/password")
async def reset_user_password(
    user_id: str,
    password_data: UserPasswordReset,
    db: Session = Depends(get_db)
):
    """
    Reset a user's password (admin-only).
    
    This bypasses the current password check.
    """
    success = update_user_password(
        db=db,
        user_id=user_id,
        new_password=password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Password reset successfully"}


@router.get("/{user_id}/audit-logs")
async def get_user_audit_logs(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get audit logs for a specific user (admin-only).
    
    Returns authentication and activity logs for the user.
    """
    from app.services.auth import audit_service
    
    # Verify user exists
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logs = audit_service.get_audit_logs(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=limit
    )
    
    return {
        "user_id": user_id,
        "logs": logs,
        "count": len(logs)
    }
