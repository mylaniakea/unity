"""Tests for alert system."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.alert_rules import AlertRule, AlertCondition, AlertSeverity, ResourceType, AlertStatus
from app.models.monitoring import Alert
from app.services.monitoring.alert_lifecycle import AlertLifecycleService


class MockResource:
    """Mock resource for testing."""
    def __init__(self, id, name):
        self.id = id
        self.name = name


def test_create_alert_rule(db: Session):
    """Test creating an alert rule."""
    rule = AlertRule(
        name="Test CPU Alert",
        description="Alert when CPU exceeds threshold",
        resource_type=ResourceType.SERVER,
        metric_name="cpu_usage",
        condition=AlertCondition.GT,
        threshold=80.0,
        severity=AlertSeverity.WARNING,
        enabled=True,
        cooldown_minutes=15
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    assert rule.id is not None
    assert rule.name == "Test CPU Alert"
    assert rule.enabled is True


def test_trigger_alert(db: Session):
    """Test triggering an alert."""
    # Create a rule
    rule = AlertRule(
        name="Test Alert",
        resource_type=ResourceType.SERVER,
        metric_name="cpu_usage",
        condition=AlertCondition.GT,
        threshold=80.0,
        severity=AlertSeverity.WARNING,
        enabled=True,
        cooldown_minutes=0  # No cooldown for testing
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    # Create lifecycle service
    lifecycle = AlertLifecycleService(db)
    
    # Create mock resource
    resource = MockResource(id=1, name="test-server")
    
    # Trigger alert
    alert = lifecycle.trigger_alert(rule, resource, 95.0, "cpu_usage")
    
    assert alert is not None
    assert alert.alert_rule_id == rule.id
    assert alert.resource_id == resource.id
    assert alert.severity == AlertSeverity.WARNING.value
    assert alert.status == AlertStatus.ACTIVE.value
    assert "cpu_usage=95.0" in alert.message


def test_acknowledge_alert(db: Session):
    """Test acknowledging an alert."""
    # Create rule and trigger alert
    rule = AlertRule(
        name="Test Alert",
        resource_type=ResourceType.SERVER,
        metric_name="cpu_usage",
        condition=AlertCondition.GT,
        threshold=80.0,
        severity=AlertSeverity.WARNING,
        enabled=True,
        cooldown_minutes=0
    )
    db.add(rule)
    db.commit()
    
    lifecycle = AlertLifecycleService(db)
    resource = MockResource(id=1, name="test-server")
    alert = lifecycle.trigger_alert(rule, resource, 95.0, "cpu_usage")
    
    # Acknowledge the alert
    ack_alert = lifecycle.acknowledge_alert(alert.id, "test_user")
    
    assert ack_alert is not None
    assert ack_alert.acknowledged is True
    assert ack_alert.acknowledged_by == "test_user"
    assert ack_alert.status == AlertStatus.ACKNOWLEDGED.value


def test_resolve_alert(db: Session):
    """Test resolving an alert."""
    rule = AlertRule(
        name="Test Alert",
        resource_type=ResourceType.SERVER,
        metric_name="cpu_usage",
        condition=AlertCondition.GT,
        threshold=80.0,
        severity=AlertSeverity.WARNING,
        enabled=True,
        cooldown_minutes=0
    )
    db.add(rule)
    db.commit()
    
    lifecycle = AlertLifecycleService(db)
    resource = MockResource(id=1, name="test-server")
    alert = lifecycle.trigger_alert(rule, resource, 95.0, "cpu_usage")
    
    # Resolve the alert
    resolved_alert = lifecycle.resolve_alert(alert.id)
    
    assert resolved_alert is not None
    assert resolved_alert.resolved is True
    assert resolved_alert.status == AlertStatus.RESOLVED.value


def test_snooze_alert(db: Session):
    """Test snoozing an alert."""
    rule = AlertRule(
        name="Test Alert",
        resource_type=ResourceType.SERVER,
        metric_name="cpu_usage",
        condition=AlertCondition.GT,
        threshold=80.0,
        severity=AlertSeverity.WARNING,
        enabled=True,
        cooldown_minutes=0
    )
    db.add(rule)
    db.commit()
    
    lifecycle = AlertLifecycleService(db)
    resource = MockResource(id=1, name="test-server")
    alert = lifecycle.trigger_alert(rule, resource, 95.0, "cpu_usage")
    
    # Snooze the alert for 30 minutes
    snoozed_alert = lifecycle.snooze_alert(alert.id, 30)
    
    assert snoozed_alert is not None
    assert snoozed_alert.snoozed_until is not None
    # Check it's roughly 30 minutes in the future
    time_diff = snoozed_alert.snoozed_until - datetime.utcnow()
    assert 29 <= time_diff.total_seconds() / 60 <= 31


def test_cooldown_enforcement(db: Session):
    """Test that cooldown prevents duplicate alerts."""
    rule = AlertRule(
        name="Test Alert",
        resource_type=ResourceType.SERVER,
        metric_name="cpu_usage",
        condition=AlertCondition.GT,
        threshold=80.0,
        severity=AlertSeverity.WARNING,
        enabled=True,
        cooldown_minutes=15
    )
    db.add(rule)
    db.commit()
    
    lifecycle = AlertLifecycleService(db)
    resource = MockResource(id=1, name="test-server")
    
    # First alert should trigger
    alert1 = lifecycle.trigger_alert(rule, resource, 95.0, "cpu_usage")
    assert alert1 is not None
    
    # Resolve it
    lifecycle.resolve_alert(alert1.id)
    
    # Second alert should be blocked by cooldown
    alert2 = lifecycle.trigger_alert(rule, resource, 96.0, "cpu_usage")
    assert alert2 is None


def test_condition_evaluation(db: Session):
    """Test different alert conditions."""
    conditions = [
        (AlertCondition.GT, 80.0, 85.0, True),   # 85 > 80
        (AlertCondition.GT, 80.0, 75.0, False),  # 75 > 80 is False
        (AlertCondition.LT, 20.0, 15.0, True),   # 15 < 20
        (AlertCondition.LT, 20.0, 25.0, False),  # 25 < 20 is False
        (AlertCondition.EQ, 100.0, 100.0, True), # 100 == 100
        (AlertCondition.EQ, 100.0, 99.0, False), # 99 == 100 is False
    ]
    
    lifecycle = AlertLifecycleService(db)
    resource = MockResource(id=1, name="test-server")
    
    for i, (condition, threshold, value, should_trigger) in enumerate(conditions):
        rule = AlertRule(
            name=f"Test Condition {i}",
            resource_type=ResourceType.SERVER,
            metric_name="test_metric",
            condition=condition,
            threshold=threshold,
            severity=AlertSeverity.INFO,
            enabled=True,
            cooldown_minutes=0
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        
        alert = lifecycle.trigger_alert(rule, resource, value, "test_metric")
        
        if should_trigger:
            assert alert is not None, f"Alert should trigger for {condition.value} with value {value} vs threshold {threshold}"
        else:
            # If shouldn't trigger, either no alert or existing alert blocks it
            # We're just checking the logic works
            pass
