"""FastAPI dependencies for authentication and authorization."""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Cookie, Query, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.users import User
from app.models.auth import UserRole
from app.services.auth.jwt_handler import decode_token
from app.services.auth.user_service import get_user_by_id
from app.services.auth.api_key_manager import validate_api_key


# HTTP Bearer token scheme for Swagger UI
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_cookie: Optional[str] = Cookie(None, alias="unity_session"),
    api_key_query: Optional[str] = Query(None, alias="api_key"),
    api_key_header: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Extract and validate current user from JWT, session, or API key.
    
    If DISABLE_AUTH is set, returns a mock admin user for testing.
    
    Checks authentication in this order:
    1. Bearer token (JWT) in Authorization header
    2. API key in X-API-Key header
    3. API key in query parameter
    4. Session cookie
    
    Returns:
        User model if authenticated, None if not authenticated
    """
    # Testing mode: bypass authentication
    if settings.disable_auth:
        # Return a mock admin user
        mock_user = User(
            id="00000000-0000-0000-0000-000000000000",
            username="test_admin",
            email="test@example.com",
            full_name="Test Admin",
            is_active=True,
            role=UserRole.ADMIN
        )
        return mock_user
    
    user = None
    
    # 1. Check JWT Bearer token
    if authorization and authorization.credentials:
        token_data = decode_token(authorization.credentials)
        if token_data:
            user_id = token_data.get("sub")
            if user_id:
                user = get_user_by_id(db, user_id)
    
    # 2. Check API key in header
    if not user and api_key_header:
        api_key = validate_api_key(db, api_key_header)
        if api_key:
            user = get_user_by_id(db, str(api_key.user_id))
    
    # 3. Check API key in query parameter
    if not user and api_key_query:
        api_key = validate_api_key(db, api_key_query)
        if api_key:
            user = get_user_by_id(db, str(api_key.user_id))
    
    # 4. Check session cookie (will implement with Redis)
    if not user and session_cookie:
        # TODO: Implement session lookup from Redis
        # For now, skip session validation
        pass
    
    return user


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """
    Require an authenticated and active user.
    
    Raises 401 if not authenticated or user is inactive.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return current_user


def require_role(required_role: str):
    """
    Factory function to create a dependency that requires a specific role or higher.
    
    Role hierarchy: admin > editor > viewer
    
    Args:
        required_role: Minimum required role (admin, editor, viewer)
        
    Returns:
        Dependency function
    """
    role_hierarchy = {
        "viewer": 1,
        "editor": 2,
        "admin": 3
    }
    
    required_level = role_hierarchy.get(required_role, 0)
    
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        user_level = role_hierarchy.get(current_user.role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        
        return current_user
    
    return role_checker


# Convenience functions for common roles
def require_viewer():
    """Require viewer role or higher (any authenticated user)."""
    return require_role("viewer")


def require_editor():
    """Require editor role or higher."""
    return require_role("editor")


def require_admin():
    """Require admin role."""
    return require_role("admin")


async def optional_auth(
    current_user: Optional[User] = Depends(get_current_user)
) -> Optional[User]:
    """
    Optional authentication - returns user if authenticated, None if not.
    
    Useful for endpoints that work with or without authentication.
    """
    return current_user


async def get_current_user_id(
    current_user: User = Depends(get_current_active_user)
) -> str:
    """Get the current user's ID as a string."""
    return str(current_user.id)
