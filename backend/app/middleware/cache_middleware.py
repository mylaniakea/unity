"""
Response Caching Middleware

Caches API responses to reduce database load and improve response times.
"""
import hashlib
import json
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.cache import cache

logger = logging.getLogger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware to cache GET request responses."""
    
    def __init__(self, app, cache_ttl: int = 60, excluded_paths: list = None):
        """
        Initialize cache middleware.
        
        Args:
            app: FastAPI application
            cache_ttl: Default cache TTL in seconds
            excluded_paths: Paths to exclude from caching
        """
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/openapi.json",
            "/health",
            "/ws/",  # WebSocket endpoints
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with caching."""
        
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Check if path should be excluded
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to get from cache
        if cache.is_available:
            try:
                cached_response = await cache.get(cache_key)
                if cached_response:
                    logger.debug(f"Cache hit: {cache_key}")
                    return JSONResponse(
                        content=cached_response["data"],
                        status_code=cached_response["status_code"],
                        headers=cached_response.get("headers", {})
                    )
            except Exception as e:
                logger.warning(f"Cache get error: {e}")
        
        # Call the actual endpoint
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200 and cache.is_available:
            try:
                # Read response body (create a copy since iterator can only be read once)
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # Parse JSON if possible
                try:
                    data = json.loads(response_body.decode())
                except:
                    # Not JSON, skip caching - return new response with body
                    return Response(
                        content=response_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )
                
                # Cache the response
                cache_data = {
                    "data": data,
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
                
                # Determine TTL based on path
                ttl = self._get_ttl_for_path(request.url.path)
                
                await cache.set(cache_key, cache_data, ttl=ttl)
                logger.debug(f"Cached response: {cache_key} (TTL: {ttl}s)")
                
                # Return new response with cached data
                return JSONResponse(
                    content=data,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except Exception as e:
                logger.warning(f"Cache set error: {e}")
                # Return new response if caching fails
                return Response(
                    content=response_body if 'response_body' in locals() else b"",
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
        
        return response
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key from request."""
        # Include path and query parameters
        key_parts = [request.url.path]
        
        # Sort query params for consistent keys
        if request.url.query:
            query_params = sorted(request.url.query.split("&"))
            key_parts.extend(query_params)
        
        key_string = "|".join(key_parts)
        
        # Hash for shorter keys
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"api:cache:{key_hash}"
    
    def _get_ttl_for_path(self, path: str) -> int:
        """Get cache TTL based on path."""
        # Dashboard data - short TTL
        if "/dashboard" in path:
            return 60  # 1 minute
        
        # Plugin list - medium TTL
        if "/plugins" in path and "/metrics" not in path:
            return 300  # 5 minutes
        
        # Metrics - short TTL
        if "/metrics" in path:
            return 60  # 1 minute
        
        # Default TTL
        return self.cache_ttl

