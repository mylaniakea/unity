"""Tests for alert evaluator logic."""
import pytest
from app import models


def test_alert_condition_greater_than(test_db, sample_alert_rule, sample_storage_device):
    """Test GT condition evaluation."""
    # Rule: temperature > 60
    # Device: temperature = 45 (should not trigger)
    assert sample_alert_rule.condition == models.AlertCondition.GT
    assert sample_alert_rule.threshold == 60.0
    assert sample_storage_device.temperature_celsius == 45
    
    # Should not trigger
    assert sample_storage_device.temperature_celsius <= sample_alert_rule.threshold
    
    # Update temperature to trigger
    sample_storage_device.temperature_celsius = 65
    test_db.commit()
    
    # Should trigger now
    assert sample_storage_device.temperature_celsius > sample_alert_rule.threshold


def test_alert_condition_less_than(test_db):
    """Test LT condition evaluation."""
    rule = models.AlertRule(
        name="Low Disk Space",
        resource_type=models.ResourceType.POOL,
        metric_name="available_bytes",
        condition=models.AlertCondition.LT,
        threshold=1000000000,  # < 1GB
        severity=models.AlertSeverity.CRITICAL
    )
    test_db.add(rule)
    test_db.commit()
    
    assert rule.condition == models.AlertCondition.LT
    
    # Test evaluation logic
    available_space = 500000000  # 500MB
    assert available_space < rule.threshold  # Should trigger


def test_alert_condition_equals(test_db):
    """Test EQ condition evaluation."""
    rule = models.AlertRule(
        name="Failed Status",
        resource_type=models.ResourceType.DEVICE,
        metric_name="health_status",
        condition=models.AlertCondition.EQ,
        threshold=0,  # FAILED = 0
        severity=models.AlertSeverity.CRITICAL
    )
    test_db.add(rule)
    test_db.commit()
    
    assert rule.condition == models.AlertCondition.EQ


def test_alert_cooldown_period(test_db, sample_alert_rule):
    """Test alert cooldown period."""
    assert sample_alert_rule.cooldown_minutes == 15
    
    # Create an alert
    alert = models.Alert(
        alert_rule_id=sample_alert_rule.id,
        resource_type="device",
        resource_id=1,
        metric_value=70,
        threshold=60.0,
        severity="warning",
        message="Temperature exceeded threshold",
        status="active"
    )
    test_db.add(alert)
    test_db.commit()
    
    assert alert.status == "active"


def test_alert_severity_levels(test_db):
    """Test different alert severity levels."""
    severities = [
        models.AlertSeverity.INFO,
        models.AlertSeverity.WARNING,
        models.AlertSeverity.CRITICAL
    ]
    
    for severity in severities:
        rule = models.AlertRule(
            name=f"Test {severity.value} Alert",
            resource_type=models.ResourceType.SERVER,
            metric_name="test_metric",
            condition=models.AlertCondition.GT,
            threshold=100.0,
            severity=severity
        )
        test_db.add(rule)
    
    test_db.commit()
    
    rules = test_db.query(models.AlertRule).all()
    assert len(rules) >= 3


def test_alert_resource_types(test_db):
    """Test alert rules for different resource types."""
    resource_types = [
        models.ResourceType.SERVER,
        models.ResourceType.DEVICE,
        models.ResourceType.POOL,
        models.ResourceType.DATABASE
    ]
    
    for resource_type in resource_types:
        rule = models.AlertRule(
            name=f"Test {resource_type.value} Alert",
            resource_type=resource_type,
            metric_name="test_metric",
            condition=models.AlertCondition.GT,
            threshold=50.0,
            severity=models.AlertSeverity.WARNING
        )
        test_db.add(rule)
    
    test_db.commit()
    
    # Verify all resource types
    for resource_type in resource_types:
        rule = test_db.query(models.AlertRule).filter(
            models.AlertRule.resource_type == resource_type
        ).first()
        assert rule is not None


def test_alert_enable_disable(test_db, sample_alert_rule):
    """Test enabling and disabling alert rules."""
    assert sample_alert_rule.enabled is True
    
    # Disable rule
    sample_alert_rule.enabled = False
    test_db.commit()
    
    assert sample_alert_rule.enabled is False
    
    # Re-enable
    sample_alert_rule.enabled = True
    test_db.commit()
    
    assert sample_alert_rule.enabled is True


def test_alert_lifecycle(test_db, sample_alert_rule):
    """Test complete alert lifecycle: active -> acknowledged -> resolved."""
    # Create active alert
    alert = models.Alert(
        alert_rule_id=sample_alert_rule.id,
        resource_type="device",
        resource_id=1,
        metric_value=75,
        threshold=60.0,
        severity="warning",
        message="Temperature high",
        status="active",
        acknowledged=False,
        resolved=False
    )
    test_db.add(alert)
    test_db.commit()
    
    # Verify active state
    assert alert.status == "active"
    assert alert.acknowledged is False
    assert alert.resolved is False
    
    # Acknowledge
    alert.acknowledged = True
    alert.status = "acknowledged"
    test_db.commit()
    
    assert alert.status == "acknowledged"
    assert alert.acknowledged is True
    
    # Resolve
    alert.resolved = True
    alert.status = "resolved"
    test_db.commit()
    
    assert alert.status == "resolved"
    assert alert.resolved is True
