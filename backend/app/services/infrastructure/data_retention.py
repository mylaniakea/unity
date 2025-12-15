"""Data retention service for cleaning up old infrastructure monitoring data."""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

logger = logging.getLogger(__name__)


class DataRetentionService:
    """Service for cleaning up old infrastructure monitoring data."""
    
    def __init__(self):
        self.default_retention_days = 90  # 90 days default
        self.alert_retention_days = 365  # Keep alerts for 1 year
    
    def cleanup_all(self) -> dict:
        """
        Run all cleanup tasks.
        
        Returns:
            Dictionary with cleanup statistics
        """
        db = next(get_db())
        
        try:
            results = {
                "alerts_deleted": 0,
                "errors": []
            }
            
            # Cleanup resolved alerts older than retention period
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(days=self.alert_retention_days)
                deleted_count = db.query(models.Alert).filter(
                    models.Alert.resolved == True,
                    models.Alert.resolved_at < cutoff
                ).delete()
                
                db.commit()
                results["alerts_deleted"] = deleted_count
                logger.info(f"Deleted {deleted_count} old resolved alerts")
                
            except Exception as e:
                logger.error(f"Error cleaning up alerts: {e}")
                results["errors"].append(f"Alert cleanup error: {str(e)}")
                db.rollback()
            
            return results
            
        finally:
            db.close()
    
    def cleanup_alerts(self, retention_days: int = None) -> int:
        """
        Cleanup old resolved alerts.
        
        Args:
            retention_days: Number of days to retain alerts (default: 365)
            
        Returns:
            Number of alerts deleted
        """
        if retention_days is None:
            retention_days = self.alert_retention_days
        
        db = next(get_db())
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            deleted_count = db.query(models.Alert).filter(
                models.Alert.resolved == True,
                models.Alert.resolved_at < cutoff
            ).delete()
            
            db.commit()
            logger.info(f"Deleted {deleted_count} resolved alerts older than {retention_days} days")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up alerts: {e}")
            db.rollback()
            raise
        
        finally:
            db.close()


# Global instance
data_retention_service = DataRetentionService()
