"""Middleware for request correlation ID tracking."""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from . import logger as log_module


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to each request."""
    
    async def dispatch(self, request: Request, call_next):
        # Get or generate correlation ID
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        
        # Set in context for logging
        log_module.set_correlation_id(correlation_id)
        
        try:
            response = await call_next(request)
            # Add correlation ID to response headers
            response.headers['X-Correlation-ID'] = correlation_id
            return response
        finally:
            # Clear context after request
            log_module.clear_correlation_id()
