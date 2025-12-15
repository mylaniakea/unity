"""
Credential Audit Logging Service

Comprehensive audit trail for all credential operations.
Merges with Unity's existing plugin audit system.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime

from app.models import CredentialAuditLog


class CredentialAuditService:
    """Service for credential audit logging"""
    
    @staticmethod
    def log_action(
        db: Session,
        action: str,
        resource_type: str,
        resource_id: int,
        user_id: Optional[int],
        ip_address: Optional[str],
        user_agent: Optional[str],
        details: Optional[str] = None,
        success: bool = True
    ) -> CredentialAuditLog:
        """
        Log a credential-related action.
        
        Args:
            action: Action performed (create, read, update, delete, use)
            resource_type: Type of resource (ssh_key, certificate, credential)
            resource_id: ID of the resource
            user_id: ID of user performing action
            ip_address: IP address of requester
            user_agent: User agent string
            details: Additional details (optional)
            success: Whether action was successful
        """
        
        audit_log = CredentialAuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            success=success
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        return audit_log
    
    @staticmethod
    def get_logs_by_resource(
        db: Session,
        resource_type: str,
        resource_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[CredentialAuditLog]:
        """Get audit logs for a specific resource"""
        
        stmt = select(CredentialAuditLog).where(
            CredentialAuditLog.resource_type == resource_type,
            CredentialAuditLog.resource_id == resource_id
        ).order_by(CredentialAuditLog.timestamp.desc()).offset(skip).limit(limit)
        
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    def get_logs_by_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[CredentialAuditLog]:
        """Get audit logs for a specific user"""
        
        stmt = select(CredentialAuditLog).where(
            CredentialAuditLog.user_id == user_id
        ).order_by(CredentialAuditLog.timestamp.desc()).offset(skip).limit(limit)
        
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    def get_logs_by_action(
        db: Session,
        action: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[CredentialAuditLog]:
        """Get audit logs for a specific action type"""
        
        stmt = select(CredentialAuditLog).where(
            CredentialAuditLog.action == action
        ).order_by(CredentialAuditLog.timestamp.desc()).offset(skip).limit(limit)
        
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    def get_failed_logs(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[CredentialAuditLog]:
        """Get failed action audit logs"""
        
        stmt = select(CredentialAuditLog).where(
            CredentialAuditLog.success == False
        ).order_by(CredentialAuditLog.timestamp.desc()).offset(skip).limit(limit)
        
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    def get_recent_logs(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[CredentialAuditLog]:
        """Get recent audit logs"""
        
        stmt = select(CredentialAuditLog).order_by(
            CredentialAuditLog.timestamp.desc()
        ).offset(skip).limit(limit)
        
        result = db.execute(stmt)
        return list(result.scalars().all())


# Convenience functions for common audit operations

def audit_ssh_key_created(
    db: Session,
    key_id: int,
    user_id: Optional[int],
    ip_address: Optional[str],
    user_agent: Optional[str]
):
    """Audit SSH key creation"""
    return CredentialAuditService.log_action(
        db=db,
        action="create",
        resource_type="ssh_key",
        resource_id=key_id,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )


def audit_ssh_key_used(
    db: Session,
    key_id: int,
    user_id: Optional[int],
    ip_address: Optional[str],
    user_agent: Optional[str],
    details: Optional[str] = None
):
    """Audit SSH key usage"""
    return CredentialAuditService.log_action(
        db=db,
        action="use",
        resource_type="ssh_key",
        resource_id=key_id,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details
    )


def audit_ssh_key_deleted(
    db: Session,
    key_id: int,
    user_id: Optional[int],
    ip_address: Optional[str],
    user_agent: Optional[str]
):
    """Audit SSH key deletion"""
    return CredentialAuditService.log_action(
        db=db,
        action="delete",
        resource_type="ssh_key",
        resource_id=key_id,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )


def audit_certificate_created(
    db: Session,
    cert_id: int,
    user_id: Optional[int],
    ip_address: Optional[str],
    user_agent: Optional[str]
):
    """Audit certificate creation"""
    return CredentialAuditService.log_action(
        db=db,
        action="create",
        resource_type="certificate",
        resource_id=cert_id,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )


def audit_certificate_renewed(
    db: Session,
    cert_id: int,
    user_id: Optional[int],
    ip_address: Optional[str],
    user_agent: Optional[str]
):
    """Audit certificate renewal"""
    return CredentialAuditService.log_action(
        db=db,
        action="renew",
        resource_type="certificate",
        resource_id=cert_id,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )


def audit_credential_created(
    db: Session,
    cred_id: int,
    user_id: Optional[int],
    ip_address: Optional[str],
    user_agent: Optional[str]
):
    """Audit server credential creation"""
    return CredentialAuditService.log_action(
        db=db,
        action="create",
        resource_type="credential",
        resource_id=cred_id,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )


def audit_credential_used(
    db: Session,
    cred_id: int,
    user_id: Optional[int],
    ip_address: Optional[str],
    user_agent: Optional[str],
    details: Optional[str] = None
):
    """Audit server credential usage"""
    return CredentialAuditService.log_action(
        db=db,
        action="use",
        resource_type="credential",
        resource_id=cred_id,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details
    )
