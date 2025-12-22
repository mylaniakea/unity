"""Redis-based session management."""
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from redis import Redis
from app.core.config import settings


class SessionManager:
    """Manages user sessions in Redis."""
    
    def __init__(self, redis_client: Redis):
        """
        Initialize session manager.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"
    
    def create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new session.
        
        Args:
            user_id: User ID to create session for
            ip_address: Client IP address
            user_agent: Client user agent string
            metadata: Additional session metadata
            
        Returns:
            Session ID string
        """
        session_id = secrets.token_urlsafe(32)
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata or {}
        }
        
        # Store session with TTL
        session_key = f"{self.session_prefix}{session_id}"
        ttl_seconds = settings.session_expiry_hours * 3600
        
        self.redis.setex(
            session_key,
            ttl_seconds,
            json.dumps(session_data)
        )
        
        # Track session for user (for listing active sessions)
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        self.redis.sadd(user_sessions_key, session_id)
        self.redis.expire(user_sessions_key, ttl_seconds)
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Session data dict if exists, None otherwise
        """
        session_key = f"{self.session_prefix}{session_id}"
        session_data = self.redis.get(session_key)
        
        if session_data:
            return json.loads(session_data)
        return None
    
    def update_activity(self, session_id: str) -> bool:
        """
        Update session last activity timestamp.
        
        Args:
            session_id: Session ID to update
            
        Returns:
            True if updated, False if session doesn't exist
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        session_data["last_activity"] = datetime.utcnow().isoformat()
        
        session_key = f"{self.session_prefix}{session_id}"
        ttl_seconds = settings.session_expiry_hours * 3600
        
        self.redis.setex(
            session_key,
            ttl_seconds,
            json.dumps(session_data)
        )
        
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted, False if didn't exist
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        # Remove from Redis
        session_key = f"{self.session_prefix}{session_id}"
        self.redis.delete(session_key)
        
        # Remove from user's session set
        user_id = session_data.get("user_id")
        if user_id:
            user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
            self.redis.srem(user_sessions_key, session_id)
        
        return True
    
    def get_user_sessions(self, user_id: str) -> list[Dict[str, Any]]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of session data dicts
        """
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        session_ids = self.redis.smembers(user_sessions_key)
        
        sessions = []
        for session_id in session_ids:
            session_data = self.get_session(session_id.decode('utf-8'))
            if session_data:
                session_data["session_id"] = session_id.decode('utf-8')
                sessions.append(session_data)
        
        return sessions
    
    def delete_user_sessions(self, user_id: str) -> int:
        """
        Delete all sessions for a user (e.g., on password change).
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions deleted
        """
        sessions = self.get_user_sessions(user_id)
        count = 0
        
        for session in sessions:
            if self.delete_session(session["session_id"]):
                count += 1
        
        # Clear user sessions set
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        self.redis.delete(user_sessions_key)
        
        return count
