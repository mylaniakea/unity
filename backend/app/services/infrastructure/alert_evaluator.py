"""Alert evaluation engine."""
import logging
from datetime import datetime, timedelta
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.models import Alert, AlertRule, AlertCondition, AlertStatus, ResourceType
from app.models import StorageDevice, StoragePool
from app.models import DatabaseInstance
from app.models import MonitoredServer

logger = logging.getLogger(__name__)


class AlertEvaluator:
    """Evaluates alert rules against current metrics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def evaluate_all_rules(self) -> Tuple[int, int]:
        """
        Evaluate all enabled alert rules.
        
        Returns:
            Tuple of (alerts_triggered, alerts_resolved)
        """
        rules = self.db.query(AlertRule).filter(AlertRule.enabled == True).all()
        
        triggered_count = 0
        resolved_count = 0
        
        for rule in rules:
            try:
                triggered, resolved = self.evaluate_rule(rule)
                triggered_count += triggered
                resolved_count += resolved
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id} ({rule.name}): {e}")
        
        return triggered_count, resolved_count
    
    def evaluate_rule(self, rule: AlertRule) -> Tuple[int, int]:
        """
        Evaluate a single rule against all applicable resources.
        
        Returns:
            Tuple of (alerts_triggered, alerts_resolved)
        """
        triggered = 0
        resolved = 0
        
        # Get resources to check based on resource type
        resources = self._get_resources(rule.resource_type)
        
        for resource in resources:
            # Get metric value
            metric_value = self._get_metric_value(resource, rule.metric_name)
            
            if metric_value is None:
                continue
            
            # Check if condition is met
            condition_met = self._check_condition(
                metric_value,
                rule.condition,
                rule.threshold
            )
            
            if condition_met:
                # Check if we should trigger an alert
                if self._should_trigger_alert(rule, resource):
                    self._trigger_alert(rule, resource, metric_value)
                    triggered += 1
            else:
                # Auto-resolve if condition no longer met
                if self._auto_resolve_alert(rule, resource):
                    resolved += 1
        
        return triggered, resolved
    
    def _get_resources(self, resource_type: ResourceType) -> List:
        """Get all resources of a given type."""
        if resource_type == ResourceType.DEVICE:
            return self.db.query(StorageDevice).all()
        elif resource_type == ResourceType.POOL:
            return self.db.query(StoragePool).all()
        elif resource_type == ResourceType.DATABASE:
            return self.db.query(DatabaseInstance).all()
        elif resource_type == ResourceType.SERVER:
            return self.db.query(MonitoredServer).all()
        else:
            return []
    
    def _get_metric_value(self, resource, metric_name: str):
        """Extract metric value from resource."""
        try:
            return getattr(resource, metric_name, None)
        except Exception as e:
            logger.warning(f"Could not get metric {metric_name} from {resource}: {e}")
            return None
    
    def _check_condition(self, value: float, condition: AlertCondition, threshold: float) -> bool:
        """Check if value meets condition against threshold."""
        if condition == AlertCondition.GT:
            return value > threshold
        elif condition == AlertCondition.LT:
            return value < threshold
        elif condition == AlertCondition.GTE:
            return value >= threshold
        elif condition == AlertCondition.LTE:
            return value <= threshold
        elif condition == AlertCondition.EQ:
            return value == threshold
        elif condition == AlertCondition.NE:
            return value != threshold
        else:
            return False
    
    def _should_trigger_alert(self, rule: AlertRule, resource) -> bool:
        """
        Check if an alert should be triggered (respects cooldown).
        """
        # Check for existing active alert
        existing_alert = self.db.query(Alert).filter(
            Alert.alert_rule_id == rule.id,
            Alert.resource_id == resource.id,
            Alert.status == AlertStatus.ACTIVE
        ).first()
        
        if existing_alert:
            return False  # Already have an active alert
        
        # Check cooldown - has enough time passed since last alert?
        if rule.cooldown_minutes > 0:
            cooldown_time = datetime.now() - timedelta(minutes=rule.cooldown_minutes)
            recent_alert = self.db.query(Alert).filter(
                Alert.alert_rule_id == rule.id,
                Alert.resource_id == resource.id,
                Alert.triggered_at > cooldown_time
            ).first()
            
            if recent_alert:
                return False  # Still in cooldown period
        
        return True
    
    def _trigger_alert(self, rule: AlertRule, resource, metric_value: float):
        """Create a new alert."""
        message = self._format_alert_message(rule, resource, metric_value)
        
        alert = Alert(
            alert_rule_id=rule.id,
            resource_type=rule.resource_type,
            resource_id=resource.id,
            metric_name=rule.metric_name,
            metric_value=metric_value,
            threshold=rule.threshold,
            severity=rule.severity,
            message=message,
            status=AlertStatus.ACTIVE
        )
        
        self.db.add(alert)
        self.db.commit()
        
        logger.warning(f"Alert triggered: {message}")
    
    def _auto_resolve_alert(self, rule: AlertRule, resource) -> bool:
        """
        Auto-resolve alert if condition is no longer met.
        
        Returns:
            True if an alert was resolved
        """
        active_alert = self.db.query(Alert).filter(
            Alert.alert_rule_id == rule.id,
            Alert.resource_id == resource.id,
            Alert.status == AlertStatus.ACTIVE
        ).first()
        
        if active_alert:
            active_alert.status = AlertStatus.RESOLVED
            active_alert.resolved_at = datetime.now()
            active_alert.resolution_notes = "Auto-resolved: condition no longer met"
            self.db.commit()
            
            logger.info(f"Alert {active_alert.id} auto-resolved")
            return True
        
        return False
    
    def _format_alert_message(self, rule: AlertRule, resource, metric_value: float) -> str:
        """Format a human-readable alert message."""
        resource_name = getattr(resource, 'name', None) or getattr(resource, 'hostname', None) or f"ID {resource.id}"
        
        condition_str = {
            AlertCondition.GT: ">",
            AlertCondition.LT: "<",
            AlertCondition.GTE: ">=",
            AlertCondition.LTE: "<=",
            AlertCondition.EQ: "==",
            AlertCondition.NE: "!="
        }.get(rule.condition, str(rule.condition))
        
        return (
            f"{rule.name}: {rule.resource_type.value} '{resource_name}' "
            f"{rule.metric_name}={metric_value:.2f} {condition_str} {rule.threshold:.2f}"
        )
