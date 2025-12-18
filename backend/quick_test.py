"""Quick test - just 35 seconds."""
import asyncio
import logging
from uuid import uuid4
from app.core.database import SessionLocal
from app.models import Plugin
from app.services.plugin_scheduler import PluginScheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    # Register plugins
    db = SessionLocal()
    existing = db.query(Plugin).count()
    if existing == 0:
        docker_plugin = Plugin(id=uuid4(), plugin_id='docker_monitor', name='Docker Monitor', 
                              category='containers', enabled=True, config={'collection_interval': 15})
        system_plugin = Plugin(id=uuid4(), plugin_id='system_info', name='System Info',
                              category='system', enabled=True, config={'collection_interval': 15})
        db.add_all([docker_plugin, system_plugin])
        db.commit()
        logger.info("✅ Registered plugins")
    db.close()
    
    # Start scheduler
    scheduler = PluginScheduler()
    await scheduler.start()
    
    logger.info("\n📊 Jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job['name']}")
    
    logger.info("\n⏳ Running for 35 seconds...")
    await asyncio.sleep(35)
    
    await scheduler.stop()
    
    # Show results
    db = SessionLocal()
    from app.models import PluginMetric, PluginExecution
    execs = db.query(PluginExecution).all()
    metrics = db.query(PluginMetric).all()
    logger.info(f"\n✅ Executions: {len(execs)}, Metrics: {len(metrics)}")
    for e in execs:
        logger.info(f"  - {e.plugin_id}: {e.status} ({e.metrics_count} metrics)")
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
