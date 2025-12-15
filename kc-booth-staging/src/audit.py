"""Audit logging for compliance and security tracking."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import Session
from .database import Base
from .logger import get_logger

logger = get_logger(__name__)


class AuditLog(Base):
    """Audit log model for tracking user actions."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    user_id = Column(Integer, nullable=True)  # None for system actions
    username = Column(String(255), nullable=True)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT
    resource_type = Column(String(50), nullable=False)  # server, ssh_key, certificate, api_key, user
    resource_id = Column(Integer, nullable=True)
    resource_name = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)  # JSON string with additional details
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    correlation_id = Column(String(36), nullable=True)  # Request correlation ID


def log_audit_event(
    db: Session,
    action: str,
    resource_type: str,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    resource_id: Optional[int] = None,
    resource_name: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> AuditLog:
    """
    Log an audit event to the database.
    
    Args:
        db: Database session
        action: Action performed (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.)
        resource_type: Type of resource (server, ssh_key, certificate, api_key, user)
        user_id: ID of user who performed the action
        username: Username of user who performed the action
        resource_id: ID of the resource affected
        resource_name: Name of the resource affected
        details: Additional details as JSON string
        ip_address: IP address of the request
        correlation_id: Request correlation ID for tracing
    
    Returns:
        Created AuditLog instance
    """
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            ip_address=ip_address,
            correlation_id=correlation_id
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        
        logger.info(
            f"Audit: {action} {resource_type} "
            f"(id={resource_id}, name={resource_name}) by user={username}"
        )
        
        return audit_entry
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}", exc_info=True)
        db.rollback()
        raise


def get_audit_logs(
    db: Session,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> list[AuditLog]:
    """
    Query audit logs with optional filters.
    
    Args:
        db: Database session
        user_id: Filter by user ID
        resource_type: Filter by resource type
        action: Filter by action
        limit: Maximum number of results
        offset: Number of results to skip
    
    Returns:
        List of AuditLog instances
    """
    query = db.query(AuditLog)
    
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if action:
        query = query.filter(AuditLog.action == action)
    
    return query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset).all()


def get_resource_audit_trail(
    db: Session,
    resource_type: str,
    resource_id: int
) -> list[AuditLog]:
    """
    Get complete audit trail for a specific resource.
    
    Args:
        db: Database session
        resource_type: Type of resource
        resource_id: ID of resource
    
    Returns:
        List of AuditLog instances for the resource
    """
    return (
        db.query(AuditLog)
        .filter(AuditLog.resource_type == resource_type)
        .filter(AuditLog.resource_id == resource_id)
        .order_by(AuditLog.timestamp.asc())
        .all()
    )
