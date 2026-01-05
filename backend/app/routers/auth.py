from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import schemas, models
from app.database import get_db
from app.core.dependencies import get_tenant_id
from app.services.auth import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_active_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = AuthService.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check if email already registered (if provided)
    if user.email:
        db_user_by_email = db.query(models.User).filter(models.User.tenant_id == "default").filter(models.User.email == user.email).first()
        if db_user_by_email:
            raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = AuthService.get_password_hash(user.password)
    db_user = models.User(tenant_id="default", 
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role or "user"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = AuthService.get_user_by_username(db, username=form_data.username)
    if not user or not AuthService.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user


@router.post("/change-password")
async def change_password(
    password_data: schemas.ChangePassword,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Allow user to change their own password (requires current password verification)"""
    # Verify current password
    if not AuthService.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Validate new password (minimum 8 characters)
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )

    # Update password
    current_user.hashed_password = AuthService.get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/admin/reset-password/{user_id}")
async def admin_reset_password(
    user_id: int,
    password_data: schemas.AdminResetPassword,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Allow admin to reset any user's password (no current password required)"""
    # Check if current user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Get target user
    target_user = AuthService.get_user(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Validate new password (minimum 8 characters)
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )

    # Update password
    target_user.hashed_password = AuthService.get_password_hash(password_data.new_password)
    db.commit()

    return {"message": f"Password reset successfully for user {target_user.username}"}
