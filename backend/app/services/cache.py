"""
Redis Cache Service

Provides caching layer with graceful Redis fallback.
"""
import json
import logging
from typing import Optional, Any
from datetime import timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis cache with graceful fallback.
    
    TTL defaults:
    - Latest metrics: 5 minutes
    - Dashboard data: 1 minute
    - Plugin status: 30 seconds
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize cache service.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None
        self._available = False
        
    async def connect(self):
        """Connect to Redis."""
        try:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.client.ping()
            self._available = True
            logger.info("✅ Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Redis unavailable, caching disabled: {e}")
            self._available = False
            self.client = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            self.client = None
            self._available = False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self._available:
            return None
        
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        if not self._available:
            return
        
        try:
            serialized = json.dumps(value)
            await self.client.setex(key, ttl, serialized)
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
    
    async def delete(self, key: str):
        """
        Delete key from cache.
        
        Args:
            key: Cache key
        """
        if not self._available:
            return
        
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
    
    async def get_latest_metrics(self, plugin_id: str) -> Optional[dict]:
        """
        Get latest metrics for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Latest metrics or None
        """
        return await self.get(f"metrics:latest:{plugin_id}")
    
    async def set_latest_metrics(self, plugin_id: str, metrics: dict):
        """
        Cache latest metrics for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            metrics: Metrics data
        """
        await self.set(f"metrics:latest:{plugin_id}", metrics, ttl=300)  # 5 minutes
    
    async def get_plugin_status(self, plugin_id: str) -> Optional[dict]:
        """
        Get cached plugin status.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Plugin status or None
        """
        return await self.get(f"status:{plugin_id}")
    
    async def set_plugin_status(self, plugin_id: str, status: dict):
        """
        Cache plugin status.
        
        Args:
            plugin_id: Plugin identifier
            status: Status data
        """
        await self.set(f"status:{plugin_id}", status, ttl=30)  # 30 seconds
    
    async def get_dashboard_data(self) -> Optional[dict]:
        """
        Get cached dashboard data.
        
        Returns:
            Dashboard data or None
        """
        return await self.get("dashboard:data")
    
    async def set_dashboard_data(self, data: dict):
        """
        Cache dashboard data.
        
        Args:
            data: Dashboard data
        """
        await self.set("dashboard:data", data, ttl=60)  # 1 minute
    
    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._available


# Global cache instance
cache = CacheService()
