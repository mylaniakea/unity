from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app import models
from app.schemas.alerts import Alert, AlertUpdate, AlertChannel, AlertChannelCreate, AlertChannelUpdate, NotificationLogResponse
from app.services.monitoring.alert_channels import get_all_channels

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.get("/", response_model=List[Alert])
def get_alerts(
    limit: int = 100,
    unresolved_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get alerts with optional filtering"""
    query = db.query(models.Alert).order_by(models.Alert.triggered_at.desc())

    if unresolved_only:
        query = query.filter(models.Alert.resolved == False)

    alerts = query.limit(limit).all()
    return alerts

@router.get("/stats")
def get_alert_stats(db: Session = Depends(get_db)):
    """Get alert statistics for dashboard"""
    total = db.query(models.Alert).count()
    unresolved = db.query(models.Alert).filter(models.Alert.resolved == False).count()

    # Count by severity
    critical = db.query(models.Alert).filter(
        and_(models.Alert.severity == "critical", models.Alert.resolved == False)
    ).count()
    warning = db.query(models.Alert).filter(
        and_(models.Alert.severity == "warning", models.Alert.resolved == False)
    ).count()
    info = db.query(models.Alert).filter(
        and_(models.Alert.severity == "info", models.Alert.resolved == False)
    ).count()

    return {
        "total": total,
        "unresolved": unresolved,
        "critical": critical,
        "warning": warning,
        "info": info
    }

@router.put("/{alert_id}", response_model=Alert)
def update_alert(alert_id: int, alert_update: AlertUpdate, db: Session = Depends(get_db)):
    """Update an alert (acknowledge or resolve)"""
    db_alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert_update.acknowledged is not None and alert_update.acknowledged:
        db_alert.acknowledged = True
        db_alert.acknowledged_at = datetime.now()

    if alert_update.resolved is not None and alert_update.resolved:
        db_alert.resolved = True
        db_alert.resolved_at = datetime.now()

    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.post("/{alert_id}/acknowledge", response_model=Alert)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    """Acknowledge an alert"""
    db_alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db_alert.acknowledged = True
    db_alert.acknowledged_at = datetime.now()
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.post("/{alert_id}/resolve", response_model=Alert)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """Resolve an alert"""
    db_alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db_alert.resolved = True
    db_alert.resolved_at = datetime.now()
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.post("/{alert_id}/snooze", response_model=Alert)
def snooze_alert(alert_id: int, snooze_duration_minutes: int, db: Session = Depends(get_db)):
    """Snooze an alert for a specified duration in minutes"""
    db_alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db_alert.snoozed_until = datetime.now() + timedelta(minutes=snooze_duration_minutes)
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.delete("/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """Delete an alert"""
    db_alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.delete(db_alert)
    db.commit()
    return {"message": "Alert deleted successfully"}

@router.post("/acknowledge-all", response_model=List[Alert])
def bulk_acknowledge_alerts(alert_ids: List[int] = [], db: Session = Depends(get_db)):
    """Acknowledge multiple alerts. If alert_ids is empty, acknowledges all unresolved alerts."""
    query = db.query(models.Alert).filter(models.Alert.resolved == False)
    if alert_ids:
        query = query.filter(models.Alert.id.in_(alert_ids))
    
    alerts_to_update = query.all()
    if not alerts_to_update:
        raise HTTPException(status_code=404, detail="No alerts found to acknowledge")

    for alert in alerts_to_update:
        alert.acknowledged = True
        alert.acknowledged_at = datetime.now()
    
    db.commit()
    for alert in alerts_to_update:
        db.refresh(alert)
    return alerts_to_update

@router.post("/resolve-all", response_model=List[Alert])
def bulk_resolve_alerts(alert_ids: List[int] = [], db: Session = Depends(get_db)):
    """Resolve multiple alerts. If alert_ids is empty, resolves all unresolved alerts."""
    query = db.query(models.Alert).filter(models.Alert.resolved == False)
    if alert_ids:
        query = query.filter(models.Alert.id.in_(alert_ids))
    
    alerts_to_update = query.all()
    if not alerts_to_update:
        raise HTTPException(status_code=404, detail="No alerts found to resolve")

    for alert in alerts_to_update:
        alert.resolved = True
        alert.resolved_at = datetime.now()
    
    db.commit()
    for alert in alerts_to_update:
        db.refresh(alert)
    return alerts_to_update

# Alert Channels endpoints
@router.get("/channels/available")
def get_available_channels():
    """Get all available alert channel types"""
    return get_all_channels()

@router.get("/channels/", response_model=List[AlertChannel])
def get_alert_channels(db: Session = Depends(get_db)):
    """Get all configured alert channels"""
    channels = db.query(models.AlertChannel).all()
    return channels

@router.post("/channels/", response_model=AlertChannel)
def create_alert_channel(channel: AlertChannelCreate, db: Session = Depends(get_db)):
    """Create a new alert channel"""
    db_channel = models.AlertChannel(
        name=channel.name,
        channel_type=channel.channel_type,
        enabled=channel.enabled,
        config=channel.config,
        template=channel.template # Include the new template field
    )
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel

@router.put("/channels/{channel_id}", response_model=AlertChannel)
def update_alert_channel(
    channel_id: int,
    channel_update: AlertChannelUpdate,
    db: Session = Depends(get_db)
):
    """Update an alert channel"""
    db_channel = db.query(models.AlertChannel).filter(models.AlertChannel.id == channel_id).first()
    if not db_channel:
        raise HTTPException(status_code=404, detail="Alert channel not found")

    update_data = channel_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_channel, key, value)

    db.commit()
    db.refresh(db_channel)
    return db_channel

@router.delete("/channels/{channel_id}")
def delete_alert_channel(channel_id: int, db: Session = Depends(get_db)):
    """Delete an alert channel"""
    db_channel = db.query(models.AlertChannel).filter(models.AlertChannel.id == channel_id).first()
    if not db_channel:
        raise HTTPException(status_code=404, detail="Alert channel not found")

    db.delete(db_channel)
    db.commit()
    return {"message": "Alert channel deleted successfully"}

@router.get("/notification-logs", response_model=List[NotificationLogResponse])
def get_notification_logs(
    alert_id: Optional[int] = None,
    channel_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get notification logs with optional filtering by alert_id or channel_id"""
    query = db.query(models.NotificationLog).order_by(models.NotificationLog.timestamp.desc())

    if alert_id:
        query = query.filter(models.NotificationLog.alert_id == alert_id)
    if channel_id:
        query = query.filter(models.NotificationLog.channel_id == channel_id)

    logs = query.limit(limit).all()
    return logs

@router.post("/channels/{channel_id}/test")
def test_alert_channel(channel_id: int, db: Session = Depends(get_db)):
    """Send a test alert through the specified channel"""
    db_channel = db.query(models.AlertChannel).filter(models.AlertChannel.id == channel_id).first()
    if not db_channel:
        raise HTTPException(status_code=404, detail="Alert channel not found")

    if not db_channel.enabled:
        raise HTTPException(status_code=400, detail="Channel is not enabled")

    # TODO: Implement actual notification sending
    # For now, just return success
    return {"message": f"Test alert sent via {db_channel.name}", "success": True}
