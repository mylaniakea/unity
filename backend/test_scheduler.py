"""
Test script for PluginScheduler.

Registers test plugins and runs the scheduler to verify data collection.
"""
import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from app.core.database import SessionLocal
from app.models import Plugin
from app.services.plugin_scheduler import PluginScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def register_test_plugins():
    """Register some test plugins in the database."""
    db = SessionLocal()
    try:
        # Check if plugins already registered
        existing = db.query(Plugin).count()
        if existing > 0:
            logger.info(f"Found {existing} existing plugins in database")
            return
        
        # Register docker_monitor
        docker_plugin = Plugin(
            id=uuid4(),
            plugin_id='docker_monitor',
            name='Docker Monitor',
            version='1.0.0',
            description='Monitor Docker containers',
            category='containers',
            enabled=True,
            config={'collection_interval': 30}  # Collect every 30s for testing
        )
        db.add(docker_plugin)
        
        # Register system_info
        system_plugin = Plugin(
            id=uuid4(),
            plugin_id='system_info',
            name='System Info',
            version='1.0.0',
            description='System information',
            category='system',
            enabled=True,
            config={'collection_interval': 45}  # Different interval
        )
        db.add(system_plugin)
        
        db.commit()
        logger.info("✅ Registered 2 test plugins")
        
    finally:
        db.close()


async def test_scheduler():
    """Test the scheduler."""
    logger.info("="*60)
    logger.info("Testing Plugin Scheduler")
    logger.info("="*60)
    
    # Register plugins
    await register_test_plugins()
    
    # Create and start scheduler
    scheduler = PluginScheduler()
    await scheduler.start()
    
    logger.info("\n📊 Scheduled Jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job['name']} (next run: {job['next_run']})")
    
    logger.info("\n⏳ Running for 2 minutes to collect data...")
    logger.info("   (Press Ctrl+C to stop early)")
    
    try:
        # Run for 2 minutes
        await asyncio.sleep(120)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
    
    # Stop scheduler
    await scheduler.stop()
    
    # Check results
    db = SessionLocal()
    try:
        from app.models import PluginMetric, PluginExecution, PluginStatus
        
        logger.info("\n" + "="*60)
        logger.info("Results Summary")
        logger.info("="*60)
        
        # Execution count
        executions = db.query(PluginExecution).all()
        logger.info(f"✅ Total executions: {len(executions)}")
        
        for execution in executions:
            status_icon = "✓" if execution.status == 'success' else "✗"
            logger.info(f"  {status_icon} {execution.plugin_id}: {execution.status} ({execution.metrics_count} metrics)")
        
        # Metrics count
        metrics = db.query(PluginMetric).all()
        logger.info(f"\n📈 Total metrics collected: {len(metrics)}")
        
        # Group by plugin
        from collections import Counter
        plugin_counts = Counter([m.plugin_id for m in metrics])
        for plugin_id, count in plugin_counts.items():
            logger.info(f"  - {plugin_id}: {count} metrics")
        
        # Plugin status
        statuses = db.query(PluginStatus).all()
        logger.info(f"\n💚 Plugin Health:")
        for status in statuses:
            health_icon = {"healthy": "✓", "degraded": "⚠", "failing": "✗", "unknown": "?"}.get(status.health_status, "?")
            logger.info(f"  {health_icon} {status.plugin_id}: {status.health_status}")
            if status.last_success:
                logger.info(f"     Last success: {status.last_success}")
            if status.last_error:
                logger.info(f"     Last error: {status.last_error[:50]}...")
        
    finally:
        db.close()
    
    logger.info("\n" + "="*60)
    logger.info("Test Complete!")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(test_scheduler())
