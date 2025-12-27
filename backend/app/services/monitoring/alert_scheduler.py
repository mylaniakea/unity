"""Alert Scheduler

Scheduled task to periodically evaluate alert rules.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.alert_rules import AlertRule
from app.services.infrastructure.alert_evaluator import AlertEvaluator
from app.services.monitoring.alert_lifecycle import AlertLifecycleService

logger = logging.getLogger(__name__)


class AlertScheduler:
    """Scheduler for periodic alert rule evaluation."""
    
    def __init__(self, interval_seconds: int = 60):
        """
        Initialize the alert scheduler.
        
        Args:
            interval_seconds: Interval between evaluations (default: 60 seconds)
        """
        self.interval_seconds = interval_seconds
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        
    def start(self):
        """Start the alert scheduler."""
        if self.is_running:
            logger.warning("Alert scheduler is already running")
            return
        
        # Add job to scheduler
        self.scheduler.add_job(
            self._evaluate_alerts,
            trigger=IntervalTrigger(seconds=self.interval_seconds),
            id='alert_evaluation',
            name='Evaluate Alert Rules',
            replace_existing=True,
            max_instances=1  # Prevent overlapping executions
        )
        
        self.scheduler.start()
        self.is_running = True
        
        logger.info(f"Alert scheduler started (interval: {self.interval_seconds}s)")
    
    def stop(self):
        """Stop the alert scheduler."""
        if not self.is_running:
            logger.warning("Alert scheduler is not running")
            return
        
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        
        logger.info("Alert scheduler stopped")
    
    def _evaluate_alerts(self):
        """
        Evaluate all enabled alert rules.
        
        This method is called periodically by the scheduler.
        """
        db: Session = SessionLocal()
        
        try:
            start_time = datetime.utcnow()
            logger.debug("Starting alert evaluation")
            
            # Create evaluator and lifecycle service
            evaluator = AlertEvaluator(db)
            lifecycle = AlertLifecycleService(db)
            
            # Get all enabled alert rules
            rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()
            
            if not rules:
                logger.debug("No enabled alert rules to evaluate")
                return
            
            triggered_count = 0
            resolved_count = 0
            error_count = 0
            
            # Evaluate each rule
            for rule in rules:
                try:
                    # Use the evaluator's evaluate_rule method
                    triggered, resolved = evaluator.evaluate_rule(rule)
                    triggered_count += triggered
                    resolved_count += resolved
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error evaluating rule {rule.id} ({rule.name}): {e}", exc_info=True)
            
            # Log summary
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Alert evaluation complete: "
                f"{len(rules)} rules evaluated, "
                f"{triggered_count} triggered, "
                f"{resolved_count} auto-resolved, "
                f"{error_count} errors "
                f"(duration: {duration:.2f}s)"
            )
            
        except Exception as e:
            logger.error(f"Alert evaluation failed: {e}", exc_info=True)
            
        finally:
            db.close()
    
    def trigger_evaluation_now(self):
        """Manually trigger an immediate evaluation (for testing/debugging)."""
        if not self.is_running:
            logger.warning("Cannot trigger evaluation: scheduler is not running")
            return
        
        logger.info("Triggering immediate alert evaluation")
        self._evaluate_alerts()


# Global scheduler instance
_scheduler_instance = None


def get_alert_scheduler(interval_seconds: int = 60) -> AlertScheduler:
    """
    Get or create the global alert scheduler instance.
    
    Args:
        interval_seconds: Interval between evaluations (default: 60 seconds)
        
    Returns:
        The global AlertScheduler instance
    """
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = AlertScheduler(interval_seconds)
    
    return _scheduler_instance
