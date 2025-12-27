"""Alert Rules Router

REST API endpoints for managing alert rules.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.alert_rules import AlertRule, AlertSeverity, ResourceType, AlertCondition
from app.schemas.alerts import (
    ThresholdRule,
    ThresholdRuleCreate,
    ThresholdRuleUpdate
)
from app.services.infrastructure.alert_evaluator import AlertEvaluator
from app.services.monitoring.alert_lifecycle import AlertLifecycleService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[ThresholdRule])
def list_alert_rules(
    enabled: Optional[bool] = None,
    resource_type: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all alert rules with optional filtering.
    
    Query Parameters:
    - enabled: Filter by enabled status
    - resource_type: Filter by resource type (server, device, pool, database)
    - severity: Filter by severity (info, warning, critical)
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    """
    query = db.query(AlertRule)
    
    if enabled is not None:
        query = query.filter(AlertRule.enabled == enabled)
    
    if resource_type:
        try:
            rt = ResourceType(resource_type)
            query = query.filter(AlertRule.resource_type == rt)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid resource_type: {resource_type}")
    
    if severity:
        try:
            sev = AlertSeverity(severity)
            query = query.filter(AlertRule.severity == sev)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    
    rules = query.offset(skip).limit(limit).all()
    
    # Convert to response schema
    return [_rule_to_threshold_rule(rule) for rule in rules]


@router.post("/", response_model=ThresholdRule, status_code=201)
def create_alert_rule(
    rule_create: ThresholdRuleCreate,
    db: Session = Depends(get_db)
):
    """Create a new alert rule."""
    # Validate resource_type and severity
    try:
        resource_type = ResourceType(rule_create.server_id)  # Note: schema uses server_id, should be resource_type
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid resource_type")
    
    # Create alert rule
    rule = AlertRule(
        name=rule_create.name,
        description=None,  # Not in ThresholdRuleCreate schema
        resource_type=ResourceType.SERVER,  # Default to server for now
        metric_name=rule_create.metric,
        condition=AlertCondition(rule_create.condition),
        threshold=rule_create.threshold_value,
        severity=AlertSeverity(rule_create.severity),
        enabled=rule_create.enabled,
        notification_channels=[],  # Empty by default
        cooldown_minutes=15  # Default cooldown
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    logger.info(f"Created alert rule: {rule.id} - {rule.name}")
    
    return _rule_to_threshold_rule(rule)


@router.get("/{rule_id}", response_model=ThresholdRule)
def get_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific alert rule by ID."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    
    return _rule_to_threshold_rule(rule)


@router.put("/{rule_id}", response_model=ThresholdRule)
def update_alert_rule(
    rule_id: int,
    rule_update: ThresholdRuleUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    
    # Update fields
    if rule_update.name is not None:
        rule.name = rule_update.name
    if rule_update.metric is not None:
        rule.metric_name = rule_update.metric
    if rule_update.condition is not None:
        rule.condition = AlertCondition(rule_update.condition)
    if rule_update.threshold_value is not None:
        rule.threshold = rule_update.threshold_value
    if rule_update.severity is not None:
        rule.severity = AlertSeverity(rule_update.severity)
    if rule_update.enabled is not None:
        rule.enabled = rule_update.enabled
    
    db.commit()
    db.refresh(rule)
    
    logger.info(f"Updated alert rule: {rule.id} - {rule.name}")
    
    return _rule_to_threshold_rule(rule)


@router.delete("/{rule_id}", status_code=204)
def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Delete an alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    
    db.delete(rule)
    db.commit()
    
    logger.info(f"Deleted alert rule: {rule_id}")
    
    return None


@router.post("/{rule_id}/enable", response_model=ThresholdRule)
def enable_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Enable an alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    
    rule.enabled = True
    db.commit()
    db.refresh(rule)
    
    logger.info(f"Enabled alert rule: {rule.id} - {rule.name}")
    
    return _rule_to_threshold_rule(rule)


@router.post("/{rule_id}/disable", response_model=ThresholdRule)
def disable_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Disable an alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    
    rule.enabled = False
    db.commit()
    db.refresh(rule)
    
    logger.info(f"Disabled alert rule: {rule.id} - {rule.name}")
    
    return _rule_to_threshold_rule(rule)


@router.post("/{rule_id}/test")
def test_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually evaluate an alert rule once (for testing).
    
    Returns:
    - triggered: Number of alerts triggered
    - resolved: Number of alerts auto-resolved
    """
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    
    try:
        evaluator = AlertEvaluator(db)
        triggered, resolved = evaluator.evaluate_rule(rule)
        
        return {
            "success": True,
            "rule_id": rule_id,
            "rule_name": rule.name,
            "triggered": triggered,
            "resolved": resolved,
            "message": f"Evaluated rule '{rule.name}': {triggered} triggered, {resolved} resolved"
        }
    except Exception as e:
        logger.error(f"Error testing rule {rule_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to evaluate rule: {str(e)}")


def _rule_to_threshold_rule(rule: AlertRule) -> ThresholdRule:
    """Convert AlertRule model to ThresholdRule schema."""
    return ThresholdRule(
        id=rule.id,
        server_id=0,  # Legacy field, not used
        name=rule.name,
        metric=rule.metric_name,
        condition=rule.condition.value,
        threshold_value=rule.threshold,
        severity=rule.severity.value,
        enabled=rule.enabled,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )
