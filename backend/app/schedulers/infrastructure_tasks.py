"""Infrastructure monitoring scheduled tasks for Phase 3.5: Complete BD-Store Integration."""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.infrastructure.collection_task import collect_all_servers
from app.services.infrastructure.data_retention import data_retention_service

logger = logging.getLogger(__name__)


def setup_infrastructure_scheduler(scheduler: AsyncIOScheduler):
    """
    Setup infrastructure monitoring tasks in the APScheduler.
    
    Args:
        scheduler: APScheduler instance
    """
    # Infrastructure data collection every 5 minutes
    scheduler.add_job(
        collect_all_servers,
        'interval',
        minutes=5,
        id='infrastructure_collection',
        name='Collect Infrastructure Data',
        replace_existing=True
    )
    
    # Data retention cleanup daily at 3 AM
    scheduler.add_job(
        data_retention_service.cleanup_all,
        'cron',
        hour=3,
        minute=0,
        id='infrastructure_data_retention',
        name='Infrastructure Data Retention Cleanup',
        replace_existing=True
    )
    
    logger.info("Infrastructure monitoring scheduler tasks configured")
    logger.info("  - Data collection: every 5 minutes")
    logger.info("  - Data retention: daily at 3:00 AM")
