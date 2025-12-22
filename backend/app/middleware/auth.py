"""Authentication middleware for logging and request context."""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.dependencies import get_current_user
from app.core.database import SessionLocal


class AuthContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and attach authentication context to requests.
    
    This runs before route handlers and populates request.state with:
    - user: Current authenticated user (if any)
    - auth_start_time: Request start time for logging
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add auth context."""
        request.state.auth_start_time = time.time()
        request.state.user = None
        
        # Try to extract user from request
        # Note: This is optional - dependencies will handle auth checks
        try:
            db = SessionLocal()
            try:
                # Call get_current_user dependency manually
                # This is just for logging/context, not authorization
                user = await get_current_user(
                    request=request,
                    authorization=None,  # Will be extracted from headers
                    db=db
                )
                request.state.user = user
            finally:
                db.close()
        except Exception:
            # Silently ignore auth errors in middleware
            # Let the route dependencies handle proper auth checks
            pass
        
        # Process the request
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - request.state.auth_start_time
        response.headers["X-Process-Time"] = str(duration)
        
        return response
