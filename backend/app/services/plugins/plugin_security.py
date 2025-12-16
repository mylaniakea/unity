"""
Plugin Security Service

Handles security for the plugin system:
- API key authentication for external plugins
- Authorization checks
- Input validation and sanitization
- Audit logging
- Rate limiting
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from fastapi import HTTPException, status

from app.models import Plugin, User

logger = logging.getLogger(__name__)


class PluginSecurityService:
    """Security service for plugin operations"""
    
    # Dangerous patterns in plugin IDs and names
    DANGEROUS_PATTERNS = [
        "../", "..\\", "/etc/", "\\windows\\", "~", 
        "<script", "javascript:", "eval(", "exec(",
        "import os", "import sys", "__import__"
    ]
    
    # Maximum sizes for various inputs
    MAX_PLUGIN_ID_LENGTH = 100
    MAX_PLUGIN_NAME_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_CONFIG_SIZE_KB = 100
    MAX_METRICS_SIZE_KB = 500
    
    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure API key for external plugins.
        
        Returns:
            Secure random API key
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash an API key for storage.
        
        Args:
            api_key: Plain API key
            
        Returns:
            Hashed API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def verify_api_key(api_key: str, hashed_key: str) -> bool:
        """
        Verify an API key against its hash.
        
        Args:
            api_key: Plain API key to verify
            hashed_key: Stored hash
            
        Returns:
            True if valid
        """
        return PluginSecurityService.hash_api_key(api_key) == hashed_key
    
    @staticmethod
    def validate_plugin_id(plugin_id: str) -> bool:
        """
        Validate plugin ID for security.
        
        Args:
            plugin_id: Plugin identifier to validate
            
        Returns:
            True if valid
            
        Raises:
            HTTPException: If invalid
        """
        if not plugin_id or len(plugin_id) > PluginSecurityService.MAX_PLUGIN_ID_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plugin ID must be 1-{PluginSecurityService.MAX_PLUGIN_ID_LENGTH} characters"
            )
        
        # Check for dangerous patterns
        plugin_id_lower = plugin_id.lower()
        for pattern in PluginSecurityService.DANGEROUS_PATTERNS:
            if pattern in plugin_id_lower:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Plugin ID contains invalid pattern: {pattern}"
                )
        
        # Only allow alphanumeric, dash, underscore
        if not all(c.isalnum() or c in ['-', '_'] for c in plugin_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plugin ID can only contain letters, numbers, dash, and underscore"
            )
        
        return True
    
    @staticmethod
    def validate_plugin_metadata(metadata: Dict[str, Any]) -> bool:
        """
        Validate plugin metadata for security.
        
        Args:
            metadata: Plugin metadata dictionary
            
        Returns:
            True if valid
            
        Raises:
            HTTPException: If invalid
        """
        # Validate required fields
        if not metadata.get("id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plugin metadata must include 'id'"
            )
        
        if not metadata.get("name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plugin metadata must include 'name'"
            )
        
        # Validate ID
        PluginSecurityService.validate_plugin_id(metadata["id"])
        
        # Validate name length
        if len(metadata["name"]) > PluginSecurityService.MAX_PLUGIN_NAME_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plugin name too long (max {PluginSecurityService.MAX_PLUGIN_NAME_LENGTH} chars)"
            )
        
        # Validate description length
        if metadata.get("description") and len(metadata["description"]) > PluginSecurityService.MAX_DESCRIPTION_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Description too long (max {PluginSecurityService.MAX_DESCRIPTION_LENGTH} chars)"
            )
        
        return True
    
    @staticmethod
    def validate_plugin_config(config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration for security.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if valid
            
        Raises:
            HTTPException: If invalid
        """
        import json
        
        # Check size
        config_json = json.dumps(config)
        size_kb = len(config_json.encode('utf-8')) / 1024
        
        if size_kb > PluginSecurityService.MAX_CONFIG_SIZE_KB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Configuration too large (max {PluginSecurityService.MAX_CONFIG_SIZE_KB}KB)"
            )
        
        # Scan for dangerous patterns
        config_str = str(config).lower()
        for pattern in PluginSecurityService.DANGEROUS_PATTERNS:
            if pattern in config_str:
                logger.warning(f"Dangerous pattern detected in config: {pattern}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Configuration contains potentially dangerous content"
                )
        
        return True
    
    @staticmethod
    def validate_metrics_data(data: Dict[str, Any]) -> bool:
        """
        Validate metrics data for security.
        
        Args:
            data: Metrics data dictionary
            
        Returns:
            True if valid
            
        Raises:
            HTTPException: If invalid
        """
        import json
        
        # Check size
        data_json = json.dumps(data)
        size_kb = len(data_json.encode('utf-8')) / 1024
        
        if size_kb > PluginSecurityService.MAX_METRICS_SIZE_KB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Metrics data too large (max {PluginSecurityService.MAX_METRICS_SIZE_KB}KB)"
            )
        
        return True
    
    @staticmethod
    def check_user_plugin_permission(
        user: User, 
        plugin_id: str, 
        action: str,
        db: Session
    ) -> bool:
        """
        Check if user has permission to perform action on plugin.
        
        Args:
            user: User object
            plugin_id: Plugin identifier
            action: Action to perform (view, enable, disable, configure, delete)
            db: Database session
            
        Returns:
            True if authorized
            
        Raises:
            HTTPException: If unauthorized
        """
        # Admins can do anything
        if user.role == "admin":
            return True
        
        # Get plugin
        stmt = select(Plugin).where(Plugin.id == plugin_id)
        result = db.execute(stmt)
        plugin = result.scalar_one_or_none()
        
        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin {plugin_id} not found"
            )
        
        # External plugins can only be managed by admins
        if plugin.external and action in ["enable", "disable", "configure", "delete"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can manage external plugins"
            )
        
        # Regular users can view all plugins
        if action == "view":
            return True
        
        # For other actions, check role
        if user.role not in ["admin", "operator"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for action: {action}"
            )
        
        return True
    
    @staticmethod
    def log_plugin_action(
        user: Optional[User],
        plugin_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True
    ):
        """
        Log plugin action for audit trail.
        
        Args:
            user: User performing action (None for external plugins)
            plugin_id: Plugin identifier
            action: Action performed
            details: Additional details
            success: Whether action succeeded
        """
        username = user.username if user else "external_plugin"
        status_str = "SUCCESS" if success else "FAILED"
        
        log_message = f"PLUGIN_AUDIT: [{status_str}] user={username} plugin={plugin_id} action={action}"
        
        if details:
            log_message += f" details={details}"
        
        if success:
            logger.info(log_message)
        else:
            logger.warning(log_message)


class RateLimiter:
    """Simple in-memory rate limiter for plugin operations"""
    
    def __init__(self):
        self._requests: Dict[str, list] = {}
        self._limits = {
            "plugin_execution": (10, 60),      # 10 per minute
            "metric_reporting": (100, 60),     # 100 per minute
            "health_check": (30, 60),          # 30 per minute
            "config_update": (5, 60),          # 5 per minute
        }
    
    def check_rate_limit(self, key: str, operation: str) -> bool:
        """
        Check if rate limit is exceeded.
        
        Args:
            key: Identifier (plugin_id or user_id)
            operation: Operation type
            
        Returns:
            True if within limit
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        if operation not in self._limits:
            return True
        
        limit, window = self._limits[operation]
        now = datetime.utcnow()
        rate_key = f"{key}:{operation}"
        
        # Initialize or clean old requests
        if rate_key not in self._requests:
            self._requests[rate_key] = []
        
        # Remove requests outside window
        cutoff = now - timedelta(seconds=window)
        self._requests[rate_key] = [
            ts for ts in self._requests[rate_key] if ts > cutoff
        ]
        
        # Check limit
        if len(self._requests[rate_key]) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {operation}: {limit} per {window}s"
            )
        
        # Add current request
        self._requests[rate_key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()
