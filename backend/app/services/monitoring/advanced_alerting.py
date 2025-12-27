"""
Advanced Alerting System

Supports multi-condition rules, alert correlation, and automated remediation.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from enum import Enum

from app.models.alert_rules import AlertRule, AlertCondition, AlertSeverity
from app.models.monitoring import Alert, AlertStatus
from app.services.monitoring.alert_lifecycle import AlertLifecycleService

logger = logging.getLogger(__name__)


class LogicalOperator(str, Enum):
    """Logical operators for combining conditions."""
    AND = "and"
    OR = "or"


class ConditionGroup:
    """Represents a group of conditions with a logical operator."""
    
    def __init__(self, conditions: List[Dict[str, Any]], operator: LogicalOperator = LogicalOperator.AND):
        self.conditions = conditions  # List of {metric_name, condition, threshold}
        self.operator = operator
    
    def evaluate(self, metric_values: Dict[str, float]) -> bool:
        """
        Evaluate all conditions in the group.
        
        Args:
            metric_values: Dict of metric_name -> value
            
        Returns:
            True if all conditions are met (for AND) or any condition is met (for OR)
        """
        results = []
        
        for cond in self.conditions:
            metric_name = cond.get("metric_name")
            condition = cond.get("condition")
            threshold = cond.get("threshold")
            
            if metric_name not in metric_values:
                results.append(False)
                continue
            
            value = metric_values[metric_name]
            result = self._check_condition(value, condition, threshold)
            results.append(result)
        
        if self.operator == LogicalOperator.AND:
            return all(results)
        else:  # OR
            return any(results)
    
    @staticmethod
    def _check_condition(value: float, condition: str, threshold: float) -> bool:
        """Check if condition is met."""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lte":
            return value <= threshold
        elif condition == "eq":
            return value == threshold
        elif condition == "ne":
            return value != threshold
        else:
            logger.warning(f"Unknown condition: {condition}")
            return False


class AdvancedAlertEvaluator:
    """Enhanced alert evaluator with multi-condition support."""
    
    def __init__(self, db: Session, lifecycle_service: Optional[AlertLifecycleService] = None):
        self.db = db
        self.lifecycle_service = lifecycle_service or AlertLifecycleService(db)
    
    def evaluate_advanced_rule(
        self,
        rule: AlertRule,
        resource,
        metric_values: Dict[str, float]
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate an advanced alert rule with multi-conditions.
        
        Args:
            rule: Alert rule (may have conditions_json for multi-condition)
            resource: Resource being evaluated
            metric_values: Dict of metric_name -> current value
            
        Returns:
            Tuple of (should_trigger, reason)
        """
        # Check if rule has advanced conditions
        conditions_json = getattr(rule, 'conditions_json', None)
        
        if not conditions_json:
            # Fall back to single condition
            metric_name = rule.metric_name
            if metric_name not in metric_values:
                return False, f"Metric {metric_name} not available"
            
            value = metric_values[metric_name]
            condition_met = self._check_single_condition(value, rule.condition.value, rule.threshold)
            
            return condition_met, None if condition_met else "Single condition not met"
        
        # Parse and evaluate multi-conditions
        try:
            condition_groups = self._parse_conditions(conditions_json)
            
            # Evaluate all groups (groups are combined with AND by default)
            all_groups_met = True
            failed_groups = []
            
            for i, group in enumerate(condition_groups):
                group_met = group.evaluate(metric_values)
                if not group_met:
                    all_groups_met = False
                    failed_groups.append(f"Group {i+1}")
            
            if all_groups_met:
                return True, None
            else:
                return False, f"Conditions not met: {', '.join(failed_groups)}"
                
        except Exception as e:
            logger.error(f"Error evaluating advanced rule {rule.id}: {e}")
            return False, f"Evaluation error: {str(e)}"
    
    def _parse_conditions(self, conditions_json: Dict[str, Any]) -> List[ConditionGroup]:
        """
        Parse conditions JSON into ConditionGroup objects.
        
        Expected format:
        {
            "groups": [
                {
                    "operator": "and",  # or "or"
                    "conditions": [
                        {"metric_name": "cpu_percent", "condition": "gt", "threshold": 80},
                        {"metric_name": "memory_percent", "condition": "gt", "threshold": 90}
                    ]
                }
            ]
        }
        """
        groups = []
        
        if isinstance(conditions_json, dict) and "groups" in conditions_json:
            for group_data in conditions_json["groups"]:
                operator_str = group_data.get("operator", "and").lower()
                operator = LogicalOperator.AND if operator_str == "and" else LogicalOperator.OR
                
                conditions = group_data.get("conditions", [])
                group = ConditionGroup(conditions, operator)
                groups.append(group)
        else:
            # Legacy format: single condition
            if isinstance(conditions_json, list):
                # List of conditions (default to AND)
                group = ConditionGroup(conditions_json, LogicalOperator.AND)
                groups.append(group)
        
        return groups
    
    @staticmethod
    def _check_single_condition(value: float, condition: str, threshold: float) -> bool:
        """Check a single condition."""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lte":
            return value <= threshold
        elif condition == "eq":
            return value == threshold
        elif condition == "ne":
            return value != threshold
        else:
            return False


class AlertCorrelator:
    """Correlates related alerts to reduce noise."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def correlate_alerts(
        self,
        new_alert: Alert,
        time_window_minutes: int = 5
    ) -> List[Alert]:
        """
        Find alerts that are likely related to the new alert.
        
        Args:
            new_alert: The newly triggered alert
            time_window_minutes: Time window to look for related alerts
            
        Returns:
            List of related alerts
        """
        related_alerts = []
        
        # Look for alerts on the same resource
        time_window = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        same_resource = self.db.query(Alert).filter(
            Alert.resource_type == new_alert.resource_type,
            Alert.resource_id == new_alert.resource_id,
            Alert.id != new_alert.id,
            Alert.triggered_at >= time_window,
            Alert.status == AlertStatus.ACTIVE.value
        ).all()
        
        related_alerts.extend(same_resource)
        
        # Look for alerts with similar severity in same time window
        similar_severity = self.db.query(Alert).filter(
            Alert.severity == new_alert.severity,
            Alert.id != new_alert.id,
            Alert.triggered_at >= time_window,
            Alert.status == AlertStatus.ACTIVE.value
        ).limit(10).all()
        
        # Deduplicate
        seen_ids = {new_alert.id}
        for alert in same_resource + similar_severity:
            if alert.id not in seen_ids:
                related_alerts.append(alert)
                seen_ids.add(alert.id)
        
        return related_alerts
    
    def should_suppress_alert(self, alert: Alert, related_alerts: List[Alert]) -> bool:
        """
        Determine if an alert should be suppressed due to correlation.
        
        Args:
            alert: The alert to check
            related_alerts: List of related alerts
            
        Returns:
            True if alert should be suppressed
        """
        # Suppress if there are 3+ related alerts (likely a cascade)
        if len(related_alerts) >= 3:
            logger.info(f"Suppressing alert {alert.id} due to {len(related_alerts)} related alerts")
            return True
        
        return False


class AutomatedRemediation:
    """Handles automated remediation actions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def execute_remediation(
        self,
        alert: Alert,
        action_config: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Execute automated remediation action.
        
        Args:
            alert: The alert that triggered remediation
            action_config: Configuration for the action
            
        Returns:
            Tuple of (success, message)
        """
        action_type = action_config.get("type")
        
        if action_type == "restart_service":
            return await self._restart_service(action_config.get("service_name"))
        elif action_type == "clear_cache":
            return await self._clear_cache(action_config.get("cache_type"))
        elif action_type == "scale_up":
            return await self._scale_up(action_config.get("resource_name"), action_config.get("count", 1))
        elif action_type == "webhook":
            return await self._call_webhook(action_config.get("url"), action_config.get("payload"))
        else:
            return False, f"Unknown action type: {action_type}"
    
    async def _restart_service(self, service_name: str) -> Tuple[bool, str]:
        """Restart a systemd service."""
        try:
            import subprocess
            result = subprocess.run(
                ["systemctl", "restart", service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, f"Service {service_name} restarted successfully"
            else:
                return False, f"Failed to restart service: {result.stderr}"
        except Exception as e:
            return False, f"Error restarting service: {str(e)}"
    
    async def _clear_cache(self, cache_type: str) -> Tuple[bool, str]:
        """Clear cache (placeholder for future implementation)."""
        # TODO: Implement cache clearing
        return False, "Cache clearing not yet implemented"
    
    async def _scale_up(self, resource_name: str, count: int) -> Tuple[bool, str]:
        """Scale up a resource (placeholder for future implementation)."""
        # TODO: Implement scaling
        return False, "Scaling not yet implemented"
    
    async def _call_webhook(self, url: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Call a webhook for custom remediation."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code < 400:
                    return True, f"Webhook called successfully: {response.status_code}"
                else:
                    return False, f"Webhook returned error: {response.status_code}"
        except Exception as e:
            return False, f"Error calling webhook: {str(e)}"

