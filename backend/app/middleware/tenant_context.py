"""
Tenant Context Middleware

Extracts tenant_id from JWT token or API key and injects it into request.state
for use in tenant-scoped queries throughout the application.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from typing import Optional
from jose import jwt, JWTError
import logging

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and inject tenant context into requests.
    
    For multi-tenant mode:
    - Extracts tenant_id from JWT token (claim: tenant_id)
    - Extracts tenant_id from API key format (uk_{tenant_id}_{random})
    - Falls back to 'default' tenant if not found
    
    For single-tenant mode (backward compatibility):
    - Always uses 'default' tenant
    """
    
    def __init__(self, app, multi_tenancy_enabled: bool = False):
        super().__init__(app)
        self.multi_tenancy_enabled = multi_tenancy_enabled
    
    async def dispatch(self, request: Request, call_next):
        # Extract tenant_id
        tenant_id = await self._extract_tenant_id(request)
        
        # Inject into request state
        request.state.tenant_id = tenant_id
        
        # Add to logs for debugging
        logger.debug(f"Request to {request.url.path} for tenant: {tenant_id}")
        
        response = await call_next(request)
        
        # Add tenant header to response for debugging
        response.headers["X-Tenant-ID"] = tenant_id
        
        return response
    
    async def _extract_tenant_id(self, request: Request) -> str:
        """Extract tenant_id from request (JWT, API key, or default)"""
        
        # If multi-tenancy is disabled, always use default
        if not self.multi_tenancy_enabled:
            return "default"
        
        # Try to extract from Authorization header (JWT)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            tenant_id = self._extract_from_jwt(token)
            if tenant_id:
                return tenant_id
        
        # Try to extract from API key header
        api_key = request.headers.get("X-API-Key", "")
        if api_key.startswith("uk_"):
            tenant_id = self._extract_from_api_key(api_key)
            if tenant_id:
                return tenant_id
        
        # Default tenant for backward compatibility
        return "default"
    
    def _extract_from_jwt(self, token: str) -> Optional[str]:
        """Extract tenant_id from JWT token"""
        try:
            # Decode without verification for now (verification happens in auth)
            # In production, you should verify the signature
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("tenant_id")
        except Exception as e:
            logger.debug(f"Failed to decode JWT: {e}")
            return None
    
    def _extract_from_api_key(self, api_key: str) -> Optional[str]:
        """
        Extract tenant_id from API key format: uk_{tenant_id}_{random}
        Example: uk_acme_corp_a7x9k2m3...
        """
        try:
            parts = api_key.split("_")
            if len(parts) >= 3 and parts[0] == "uk":
                # Handle tenant IDs that may contain underscores
                # Everything between uk_ and the last _ (random part)
                tenant_id = "_".join(parts[1:-1])
                return tenant_id
        except Exception as e:
            logger.debug(f"Failed to parse API key: {e}")
            return None
        
        return None
