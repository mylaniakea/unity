"""
Plugin Scheduler Service

Schedules and orchestrates plugin data collection using APScheduler.
Manages periodic plugin execution with configurable intervals.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from sqlalchemy import select
import inspect

from app.models import Plugin, PluginExecution, PluginStatus, PluginMetric
from app.plugins.loader import PluginLoader
from app.plugins.base import PluginBase
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class PluginScheduler:
    """
    Manages scheduled plugin execution.
    
    Responsibilities:
    - Load enabled plugins from database
    - Schedule periodic collection (default: 60s)
    - Spread execution to avoid thundering herd
    - Track execution status
    """
    
    def __init__(self, db_session_factory=SessionLocal):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.db_session_factory = db_session_factory
        self.loader = PluginLoader()
        self.plugin_instances: Dict[str, PluginBase] = {}
        self._running = False
        
    async def initialize(self):
        """
        Initialize the scheduler.
        
        - Discover plugins
        - Load enabled plugins from database
        - Schedule collection jobs
        """
        logger.info("Initializing plugin scheduler...")
        
        # Discover all available plugins
        self.loader.discover_all()
        logger.info(f"Discovered {len(self.loader.list_plugins())} plugins")
        
        # Load enabled plugins from database
        await self._load_enabled_plugins()
        
        # Schedule plugin collection
        await self._schedule_plugins()
        
        logger.info(f"Scheduler initialized with {len(self.plugin_instances)} enabled plugins")
    
    async def _load_enabled_plugins(self):
        """Load enabled plugins from database."""
        db = self.db_session_factory()
        try:
            # Query enabled plugins
            result = db.execute(
                select(Plugin).where(Plugin.enabled == True)
            )
            enabled_plugins = result.scalars().all()
            
            logger.info(f"Found {len(enabled_plugins)} enabled plugins in database")
            
            # Instantiate each enabled plugin
            for plugin_record in enabled_plugins:
                plugin_id = plugin_record.plugin_id
                plugin_class = self.loader.get_plugin_class(plugin_id)
                
                if not plugin_class:
                    logger.warning(f"Plugin class not found for {plugin_id}")
                    continue
                
                try:
                    # Check if plugin accepts config parameter
                    config = plugin_record.config or {}
                    sig = inspect.signature(plugin_class.__init__)
                    
                    if 'config' in sig.parameters:
                        # Plugin supports config
                        plugin_instance = plugin_class(config=config)
                    elif 'hub_client' in sig.parameters:
                        # Plugin expects hub_client first, then config
                        plugin_instance = plugin_class(hub_client=None, config=config)
                    else:
                        # Legacy plugin without config support
                        plugin_instance = plugin_class()
                        logger.debug(f"Plugin {plugin_id} doesn't support config parameter")
                    
                    self.plugin_instances[plugin_id] = plugin_instance
                    logger.info(f"Loaded plugin: {plugin_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to instantiate plugin {plugin_id}: {e}")
                    
        finally:
            db.close()
    
    async def _schedule_plugins(self):
        """Schedule periodic collection for all enabled plugins."""
        if not self.plugin_instances:
            logger.warning("No enabled plugins to schedule")
            return
        
        # Calculate offset to spread execution
        interval_seconds = 60  # Default collection interval
        offset_per_plugin = interval_seconds / len(self.plugin_instances)
        
        for idx, (plugin_id, plugin_instance) in enumerate(self.plugin_instances.items()):
            # Get plugin-specific interval if configured
            db = self.db_session_factory()
            try:
                result = db.execute(
                    select(Plugin).where(Plugin.plugin_id == plugin_id)
                )
                plugin_record = result.scalar_one_or_none()
                
                if plugin_record and plugin_record.config:
                    interval_seconds = plugin_record.config.get('collection_interval', 60)
            finally:
                db.close()
            
            # Calculate start time offset to spread load
            start_offset = timedelta(seconds=idx * offset_per_plugin)
            start_time = datetime.now() + start_offset
            
            # Schedule the plugin
            trigger = IntervalTrigger(seconds=interval_seconds, start_date=start_time)
            self.scheduler.add_job(
                self._execute_plugin,
                trigger=trigger,
                args=[plugin_id],
                id=f"plugin_{plugin_id}",
                name=f"Collect: {plugin_id}",
                replace_existing=True
            )
            
            logger.info(f"Scheduled {plugin_id} every {interval_seconds}s (starting in {offset_per_plugin * idx:.1f}s)")
    
    async def _execute_plugin(self, plugin_id: str):
        """
        Execute a single plugin and store results.
        
        Args:
            plugin_id: Plugin identifier
        """
        plugin_instance = self.plugin_instances.get(plugin_id)
        if not plugin_instance:
            logger.error(f"Plugin instance not found: {plugin_id}")
            return
        
        db = self.db_session_factory()
        execution_record = None
        
        try:
            # Create execution record
            execution_record = PluginExecution(
                plugin_id=plugin_id,
                started_at=datetime.now(),
                status='running'
            )
            db.add(execution_record)
            db.commit()
            db.refresh(execution_record)
            
            logger.debug(f"Collecting data from {plugin_id}...")
            
            # Collect data from plugin
            data = await plugin_instance.collect_data()
            
            if not data:
                raise ValueError("Plugin returned no data")
            
            # Store metrics
            metrics_count = await self._store_metrics(db, plugin_id, data)
            
            # Update execution record
            execution_record.completed_at = datetime.now()
            execution_record.status = 'success'
            execution_record.metrics_count = metrics_count
            db.commit()
            
            # Update plugin status
            await self._update_plugin_status(db, plugin_id, success=True)
            
            logger.info(f"✅ {plugin_id}: collected {metrics_count} metrics")
            
        except Exception as e:
            logger.error(f"❌ {plugin_id}: {e}")
            
            # Update execution record
            if execution_record:
                execution_record.completed_at = datetime.now()
                execution_record.status = 'failed'
                execution_record.error_message = str(e)
                db.commit()
            
            # Update plugin status
            await self._update_plugin_status(db, plugin_id, success=False, error=str(e))
            
        finally:
            db.close()
    
    async def _store_metrics(self, db: Session, plugin_id: str, data: dict) -> int:
        """
        Store plugin metrics in database.
        
        Args:
            db: Database session
            plugin_id: Plugin identifier
            data: Plugin data
            
        Returns:
            Number of metrics stored
        """
        metrics_count = 0
        timestamp = datetime.now()
        
        # Extract metrics from plugin data
        # Each top-level key becomes a metric
        for metric_name, metric_value in data.items():
            if metric_name == 'timestamp':
                continue
            
            metric = PluginMetric(
                time=timestamp,
                plugin_id=plugin_id,
                metric_name=metric_name,
                value=metric_value,
                tags={'source': 'unity'}
            )
            db.add(metric)
            metrics_count += 1
        
        db.commit()
        return metrics_count
    
    async def _update_plugin_status(self, db: Session, plugin_id: str, 
                                   success: bool, error: Optional[str] = None):
        """
        Update plugin status tracking.
        
        Args:
            db: Database session
            plugin_id: Plugin identifier
            success: Whether execution was successful
            error: Error message if failed
        """
        # Get or create status record
        status = db.query(PluginStatus).filter_by(plugin_id=plugin_id).first()
        
        if not status:
            status = PluginStatus(plugin_id=plugin_id)
            db.add(status)
        
        # Update status fields
        status.last_run = datetime.now()
        
        if success:
            status.last_success = datetime.now()
            status.consecutive_errors = 0
            status.health_status = 'healthy'
        else:
            status.error_count += 1
            status.consecutive_errors += 1
            status.last_error = error
            
            # Determine health status based on consecutive errors
            if status.consecutive_errors >= 5:
                status.health_status = 'failing'
            elif status.consecutive_errors >= 2:
                status.health_status = 'degraded'
            else:
                status.health_status = 'unhealthy'
        
        db.commit()
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        await self.initialize()
        self.scheduler.start()
        self._running = True
        logger.info("🚀 Plugin scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        if not self._running:
            return
        
        self.scheduler.shutdown()
        self._running = False
        logger.info("🛑 Plugin scheduler stopped")
    
    def get_jobs(self) -> List[dict]:
        """Get list of scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time
            })
        return jobs
