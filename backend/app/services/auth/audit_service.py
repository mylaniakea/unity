"""Audit logging service."""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.auth import AuditLog


def create_audit_log(
    db: Session,
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Create an audit log entry.
    
    Args:
        db: Database session
        action: Action performed (e.g., 'login', 'logout', 'api_key_created')
        user_id: User ID who performed the action
        resource_type: Type of resource affected
        resource_id: ID of resource affected
        ip_address: Client IP address
        user_agent: Client user agent
        success: Whether action succeeded
        error_message: Error message if action failed
        extra_metadata: Additional metadata
        
    Returns:
        Created AuditLog model
    """
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        error_message=error_message,
        extra_metadata=extra_metadata
    )
    
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    
    return audit_log


def log_login_attempt(
    db: Session,
    username: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
    success: bool,
    user_id: Optional[str] = None,
    error_message: Optional[str] = None
) -> AuditLog:
    """Log a login attempt."""
    return create_audit_log(
        db=db,
        action="login_attempt" if not success else "login_success",
        user_id=user_id,
        resource_type="user",
        resource_id=username,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        error_message=error_message
    )


def log_logout(
    db: Session,
    user_id: str,
    ip_address: Optional[str],
    user_agent: Optional[str]
) -> AuditLog:
    """Log a logout event."""
    return create_audit_log(
        db=db,
        action="logout",
        user_id=user_id,
        resource_type="user",
        ip_address=ip_address,
        user_agent=user_agent,
        success=True
    )


def log_password_change(
    db: Session,
    user_id: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
    success: bool = True
) -> AuditLog:
    """Log a password change."""
    return create_audit_log(
        db=db,
        action="password_change",
        user_id=user_id,
        resource_type="user",
        ip_address=ip_address,
        user_agent=user_agent,
        success=success
    )


def log_api_key_creation(
    db: Session,
    user_id: str,
    api_key_id: str,
    api_key_name: str,
    ip_address: Optional[str],
    user_agent: Optional[str]
) -> AuditLog:
    """Log API key creation."""
    return create_audit_log(
        db=db,
        action="api_key_created",
        user_id=user_id,
        resource_type="api_key",
        resource_id=str(api_key_id),
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
        extra_metadata={"key_name": api_key_name}
    )


def log_api_key_revocation(
    db: Session,
    user_id: str,
    api_key_id: str,
    ip_address: Optional[str],
    user_agent: Optional[str]
) -> AuditLog:
    """Log API key revocation."""
    return create_audit_log(
        db=db,
        action="api_key_revoked",
        user_id=user_id,
        resource_type="api_key",
        resource_id=str(api_key_id),
        ip_address=ip_address,
        user_agent=user_agent,
        success=True
    )


def get_audit_logs(
    db: Session,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> list[AuditLog]:
    """
    Get audit logs with filtering.
    
    Args:
        db: Database session
        user_id: Filter by user ID
        action: Filter by action type
        skip: Number of records to skip
        limit: Maximum number of records
        
    Returns:
        List of AuditLog models
    """
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
