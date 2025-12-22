"""Redis connection and session management."""
from typing import Optional
import redis
from redis import Redis, ConnectionPool
from app.core.config import settings


# Global Redis connection pool
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


def get_redis_pool() -> ConnectionPool:
    """
    Get or create Redis connection pool.
    
    Returns:
        Redis connection pool instance
    """
    global _redis_pool
    
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True  # Auto-decode bytes to strings
        )
    
    return _redis_pool


def get_redis() -> Redis:
    """
    Get Redis client instance.
    
    This can be used as a FastAPI dependency:
    ```python
    @router.get("/endpoint")
    def endpoint(redis_client: Redis = Depends(get_redis)):
        redis_client.get("key")
    ```
    
    Returns:
        Redis client instance
    """
    global _redis_client
    
    if _redis_client is None:
        pool = get_redis_pool()
        _redis_client = Redis(connection_pool=pool)
    
    return _redis_client


def close_redis():
    """
    Close Redis connection pool.
    
    Should be called on application shutdown.
    """
    global _redis_pool, _redis_client
    
    if _redis_client:
        _redis_client.close()
        _redis_client = None
    
    if _redis_pool:
        _redis_pool.disconnect()
        _redis_pool = None


def health_check() -> bool:
    """
    Check if Redis is accessible.
    
    Returns:
        True if Redis is healthy, False otherwise
    """
    try:
        client = get_redis()
        return client.ping()
    except Exception:
        return False


# Helper functions for common Redis operations
def set_with_expiry(key: str, value: str, expiry_seconds: int) -> bool:
    """Set a key with expiration time."""
    try:
        client = get_redis()
        return client.setex(key, expiry_seconds, value)
    except Exception:
        return False


def get_value(key: str) -> Optional[str]:
    """Get a value by key."""
    try:
        client = get_redis()
        return client.get(key)
    except Exception:
        return None


def delete_key(key: str) -> bool:
    """Delete a key."""
    try:
        client = get_redis()
        return bool(client.delete(key))
    except Exception:
        return False


def increment_counter(key: str, amount: int = 1) -> Optional[int]:
    """Increment a counter."""
    try:
        client = get_redis()
        return client.incr(key, amount)
    except Exception:
        return None
