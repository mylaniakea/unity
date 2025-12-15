"""Infrastructure monitoring scheduled tasks for Phase 3: BD-Store Integration."""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.infrastructure.collection_task import collect_all_servers

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
    
    logger.info("Infrastructure monitoring scheduler tasks configured")
