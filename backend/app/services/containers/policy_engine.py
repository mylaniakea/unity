import logging
from datetime import datetime, time
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from croniter import croniter
import pytz
import app.models as models

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Service for evaluating update policies and determining if updates should be auto-approved"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_applicable_policies(self, container_id: int) -> List[models.UpdatePolicy]:
        """
        Get all applicable policies for a container, ordered by priority.
        Policies are inherited: container-specific > host-specific > global
        """
        container = self.db.query(models.Container).filter(
            models.Container.id == container_id
        ).first()
        
        if not container:
            raise ValueError(f"Container with ID {container_id} not found")
        
        policies = []
        
        # Get container-specific policies
        container_policies = self.db.query(models.UpdatePolicy).filter(
            models.UpdatePolicy.scope == "container",
            models.UpdatePolicy.container_id == container_id,
            models.UpdatePolicy.enabled == True
        ).all()
        policies.extend(container_policies)
        
        # Get host-specific policies
        host_policies = self.db.query(models.UpdatePolicy).filter(
            models.UpdatePolicy.scope == "host",
            models.UpdatePolicy.host_id == container.host_id,
            models.UpdatePolicy.enabled == True
        ).all()
        policies.extend(host_policies)
        
        # Get global policies
        global_policies = self.db.query(models.UpdatePolicy).filter(
            models.UpdatePolicy.scope == "global",
            models.UpdatePolicy.enabled == True
        ).all()
        policies.extend(global_policies)
        
        # Sort by priority (highest first)
        policies.sort(key=lambda p: p.priority, reverse=True)
        
        return policies
    
    def should_auto_approve(
        self,
        container_id: int,
        update_info: Optional[Dict[str, Any]] = None,
        ai_recommendation: Optional[models.AIRecommendation] = None
    ) -> Dict[str, Any]:
        """
        Determine if an update should be auto-approved based on policies.
        
        Returns:
            Dict with:
                - approved: bool
                - reason: str
                - policy_id: int (if applicable)
                - requires_maintenance_window: bool
        """
        policies = self.get_applicable_policies(container_id)
        
        if not policies:
            logger.info(f"No policies found for container {container_id}, defaulting to manual approval")
            return {
                "approved": False,
                "reason": "No applicable policy found",
                "policy_id": None,
                "requires_maintenance_window": False
            }
        
        # Use the highest priority policy
        policy = policies[0]
        
        # Check if auto-approve is enabled
        if not policy.auto_approve:
            return {
                "approved": False,
                "reason": f"Policy '{policy.name}' requires manual approval",
                "policy_id": policy.id,
                "requires_maintenance_window": policy.maintenance_window_id is not None
            }
        
        # Check AI recommendation if required
        if policy.require_ai_approval and ai_recommendation:
            # Check risk level
            risk_level_order = {"low": 0, "medium": 1, "high": 2}
            max_risk = risk_level_order.get(policy.max_risk_level, 0)
            current_risk = risk_level_order.get(ai_recommendation.risk_level.lower(), 2)
            
            if current_risk > max_risk:
                return {
                    "approved": False,
                    "reason": f"Risk level '{ai_recommendation.risk_level}' exceeds policy maximum '{policy.max_risk_level}'",
                    "policy_id": policy.id,
                    "requires_maintenance_window": policy.maintenance_window_id is not None
                }
            
            # Check breaking changes
            if ai_recommendation.breaking_changes and not policy.allow_breaking_changes:
                return {
                    "approved": False,
                    "reason": "Update contains breaking changes not allowed by policy",
                    "policy_id": policy.id,
                    "requires_maintenance_window": policy.maintenance_window_id is not None
                }
        
        # Check version update rules if update_info provided
        if update_info:
            current_tag = update_info.get("current_tag", "")
            available_tag = update_info.get("available_tag", "")
            
            # Parse semantic versions (simplified)
            version_change = self._determine_version_change(current_tag, available_tag)
            
            if version_change == "major" and not policy.update_on_major:
                return {
                    "approved": False,
                    "reason": "Major version updates not allowed by policy",
                    "policy_id": policy.id,
                    "requires_maintenance_window": policy.maintenance_window_id is not None
                }
            
            if version_change == "minor" and not policy.update_on_minor:
                return {
                    "approved": False,
                    "reason": "Minor version updates not allowed by policy",
                    "policy_id": policy.id,
                    "requires_maintenance_window": policy.maintenance_window_id is not None
                }
            
            if version_change == "patch" and not policy.update_on_patch:
                return {
                    "approved": False,
                    "reason": "Patch version updates not allowed by policy",
                    "policy_id": policy.id,
                    "requires_maintenance_window": policy.maintenance_window_id is not None
                }
        
        # All checks passed, approve the update
        return {
            "approved": True,
            "reason": f"Auto-approved by policy '{policy.name}'",
            "policy_id": policy.id,
            "requires_maintenance_window": policy.maintenance_window_id is not None
        }
    
    def is_in_maintenance_window(self, maintenance_window_id: int) -> bool:
        """Check if current time is within the maintenance window"""
        window = self.db.query(models.MaintenanceWindow).filter(
            models.MaintenanceWindow.id == maintenance_window_id,
            models.MaintenanceWindow.enabled == True
        ).first()
        
        if not window:
            logger.warning(f"Maintenance window {maintenance_window_id} not found or disabled")
            return False
        
        # Get current time in the window's timezone
        tz = pytz.timezone(window.timezone)
        now = datetime.now(tz)
        
        # Check cron schedule if defined
        if window.cron_schedule:
            try:
                cron = croniter(window.cron_schedule, now)
                # Check if we're within the duration of the last occurrence
                last_occurrence = cron.get_prev(datetime)
                next_occurrence = cron.get_next(datetime)
                
                # Calculate if we're within the window
                window_end = last_occurrence.replace(
                    minute=last_occurrence.minute + window.duration_minutes
                )
                
                if last_occurrence <= now <= window_end:
                    return True
            except Exception as e:
                logger.error(f"Error parsing cron schedule '{window.cron_schedule}': {e}")
        
        # Check time range if defined
        if window.start_time and window.end_time:
            try:
                start_time = datetime.strptime(window.start_time, "%H:%M").time()
                end_time = datetime.strptime(window.end_time, "%H:%M").time()
                current_time = now.time()
                
                # Check day of week if allowed_days is set
                if window.allowed_days:
                    current_day = now.strftime("%A").lower()
                    if current_day not in [day.lower() for day in window.allowed_days]:
                        return False
                
                # Check if current time is in range
                if start_time <= end_time:
                    # Normal range (e.g., 02:00 - 04:00)
                    if start_time <= current_time <= end_time:
                        return True
                else:
                    # Overnight range (e.g., 22:00 - 02:00)
                    if current_time >= start_time or current_time <= end_time:
                        return True
            except Exception as e:
                logger.error(f"Error parsing time range: {e}")
        
        return False
    
    def _determine_version_change(self, current: str, available: str) -> str:
        """
        Determine if the version change is major, minor, or patch.
        Simplified semantic version parsing.
        """
        try:
            # Strip common prefixes
            current = current.lstrip("v")
            available = available.lstrip("v")
            
            # Split versions
            current_parts = current.split(".")
            available_parts = available.split(".")
            
            # Pad to 3 parts
            while len(current_parts) < 3:
                current_parts.append("0")
            while len(available_parts) < 3:
                available_parts.append("0")
            
            # Convert to integers (handle non-numeric parts)
            def to_int(s):
                try:
                    # Remove any non-numeric suffix (e.g., "1-alpine" -> "1")
                    return int(s.split("-")[0])
                except (ValueError, IndexError):
                    return 0
            
            current_major, current_minor, current_patch = [to_int(p) for p in current_parts[:3]]
            available_major, available_minor, available_patch = [to_int(p) for p in available_parts[:3]]
            
            # Determine change type
            if available_major > current_major:
                return "major"
            elif available_minor > current_minor:
                return "minor"
            elif available_patch > current_patch:
                return "patch"
            else:
                return "unknown"
        except Exception as e:
            logger.warning(f"Failed to parse versions '{current}' -> '{available}': {e}")
            return "unknown"
    
    def get_notification_settings(self, policy_id: int) -> Dict[str, bool]:
        """Get notification settings from a policy"""
        policy = self.db.query(models.UpdatePolicy).filter(
            models.UpdatePolicy.id == policy_id
        ).first()
        
        if not policy:
            # Default settings
            return {
                "notify_on_available": True,
                "notify_on_start": True,
                "notify_on_success": True,
                "notify_on_failure": True
            }
        
        return {
            "notify_on_available": policy.notify_on_available,
            "notify_on_start": policy.notify_on_start,
            "notify_on_success": policy.notify_on_success,
            "notify_on_failure": policy.notify_on_failure
        }
