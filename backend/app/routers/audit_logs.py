"""Audit log viewing router (admin-only)."""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.services.auth.audit_service import get_audit_logs


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
    dependencies=[Depends(require_admin())]
)


# Response Models
class AuditLogResponse(BaseModel):
    """Audit log response model."""
    id: str
    user_id: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    error_message: Optional[str]
    extra_metadata: Optional[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response."""
    logs: List[AuditLogResponse]
    total: int
    skip: int
    limit: int


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List audit logs with optional filtering (admin-only).
    
    Logs are returned in reverse chronological order (newest first).
    """
    logs = get_audit_logs(
        db=db,
        user_id=user_id,
        action=action,
        skip=skip,
        limit=limit
    )
    
    # Get total count with same filters
    from app.models.auth import AuditLog
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    
    total = query.count()
    
    return {
        "logs": logs,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific audit log entry by ID (admin-only)."""
    from app.models.auth import AuditLog
    
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )
    
    return log


@router.get("/actions/list")
async def list_action_types(
    db: Session = Depends(get_db)
):
    """
    Get a list of all distinct action types in audit logs (admin-only).
    
    Useful for filtering and understanding available log types.
    """
    from app.models.auth import AuditLog
    from sqlalchemy import distinct
    
    actions = db.query(distinct(AuditLog.action)).all()
    action_list = [action[0] for action in actions if action[0]]
    
    return {
        "actions": sorted(action_list),
        "count": len(action_list)
    }


@router.get("/stats/summary")
async def get_audit_stats(
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for audit logs (admin-only).
    
    Returns counts by action type and success rate.
    """
    from app.models.auth import AuditLog
    from sqlalchemy import func
    
    # Total logs
    total_logs = db.query(AuditLog).count()
    
    # Successful vs failed
    success_count = db.query(AuditLog).filter(AuditLog.success == True).count()
    failed_count = db.query(AuditLog).filter(AuditLog.success == False).count()
    
    # Logs by action type
    action_counts = db.query(
        AuditLog.action,
        func.count(AuditLog.id).label('count')
    ).group_by(AuditLog.action).all()
    
    # Recent failed logins
    recent_failures = db.query(AuditLog).filter(
        AuditLog.action.like('login%'),
        AuditLog.success == False
    ).order_by(AuditLog.created_at.desc()).limit(10).all()
    
    return {
        "total_logs": total_logs,
        "successful": success_count,
        "failed": failed_count,
        "success_rate": round(success_count / total_logs * 100, 2) if total_logs > 0 else 0,
        "by_action": {action: count for action, count in action_counts},
        "recent_failures": [
            {
                "action": log.action,
                "user_id": log.user_id,
                "ip_address": log.ip_address,
                "created_at": log.created_at,
                "error": log.error_message
            }
            for log in recent_failures
        ]
    }
