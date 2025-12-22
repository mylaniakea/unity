"""Authentication router - login, logout, user management."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_user_id
from app.models.users import User
from app.services.auth import jwt_handler
from app.services.auth.user_service import get_user_by_id, get_user_by_username, get_user_by_email, create_user, authenticate_user, update_user_password, update_user_profile
from app.services.auth.audit_service import create_audit_log, log_login_attempt, log_logout, log_password_change
from app.services.auth.password import verify_password


router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response Models
class UserRegister(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class UserResponse(BaseModel):
    """User data response."""
    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    is_superuser: bool
    
    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class ProfileUpdate(BaseModel):
    """Profile update request."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


# Helper functions
def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request."""
    return request.headers.get("User-Agent")


# Endpoints
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    Note: In production, you may want to make this admin-only or disable it entirely.
    """
    # Check if username exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        role="viewer"  # Default role for new users
    )
    
    # Log registration
    create_audit_log(
        db=db,
        action="user_registered",
        user_id=str(user.id),
        resource_type="user",
        resource_id=str(user.id),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        success=True
    )
    
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login with username and password.
    
    Returns JWT access token on success.
    """
    # Authenticate user
    user = authenticate_user(db, login_data.username, login_data.password)
    
    if not user:
        # Log failed attempt
        log_login_attempt(
            db=db,
            username=login_data.username,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False,
            error_message="Invalid credentials"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role
    }
    access_token = jwt_handler.create_access_token(token_data)
    
    # Log successful login
    log_login_attempt(
        db=db,
        username=login_data.username,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        success=True,
        user_id=str(user.id)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800,  # 30 minutes
        "user": user
    }


@router.post("/login/form", response_model=TokenResponse)
async def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login using OAuth2 password flow (for Swagger UI).
    
    This is the same as /login but uses form data instead of JSON.
    """
    # Authenticate user
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        log_login_attempt(
            db=db,
            username=form_data.username,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False,
            error_message="Invalid credentials"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role
    }
    access_token = jwt_handler.create_access_token(token_data)
    
    # Log successful login
    log_login_attempt(
        db=db,
        username=form_data.username,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        success=True,
        user_id=str(user.id)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800,
        "user": user
    }


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout current user.
    
    Note: JWT tokens can't be invalidated, so this just logs the event.
    In a full implementation with sessions, this would invalidate the session.
    """
    log_logout(
        db=db,
        user_id=str(current_user.id),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current authenticated user information."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile."""
    updated_user = update_user_profile(
        db=db,
        user_id=str(current_user.id),
        email=profile_data.email,
        full_name=profile_data.full_name
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return updated_user


@router.put("/me/password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change current user's password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        log_password_change(
            db=db,
            user_id=str(current_user.id),
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    success = update_user_password(
        db=db,
        user_id=str(current_user.id),
        new_password=password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )
    
    # Log password change
    log_password_change(
        db=db,
        user_id=str(current_user.id),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        success=True
    )
    
    return {"message": "Password updated successfully"}
