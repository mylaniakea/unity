#!/usr/bin/env python3
"""
Initialize Unity database.

Creates all tables, sets up TimescaleDB hypertables if available,
and prepares the database for use.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base, engine, SessionLocal
from app.core.timescaledb import TimescaleDBManager
from app.core.config import settings
from app.models import *
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize the database with all tables and extensions."""
    
    logger.info(f"Initializing database: {settings.database_url}")
    
    # Create all tables
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tables created")
    
    # Setup TimescaleDB if PostgreSQL
    if settings.is_postgres:
        logger.info("Detected PostgreSQL, checking for TimescaleDB...")
        session = SessionLocal()
        
        try:
            ts_manager = TimescaleDBManager(session)
            
            # Try to enable TimescaleDB
            if ts_manager.enable_extension():
                logger.info("✅ TimescaleDB extension enabled")
                
                # Setup hypertables
                logger.info("Setting up hypertables...")
                
                if ts_manager.setup_plugin_metrics():
                    logger.info("✅ plugin_metrics hypertable configured")
                else:
                    logger.warning("⚠️  Failed to setup plugin_metrics hypertable")
                
                if ts_manager.setup_alert_history():
                    logger.info("✅ alert_history hypertable configured")
                else:
                    logger.warning("⚠️  Failed to setup alert_history hypertable")
            else:
                logger.warning("⚠️  TimescaleDB not available, using standard tables")
        
        finally:
            session.close()
    else:
        logger.info("Using SQLite or MySQL, skipping TimescaleDB setup")
    
    logger.info("\n🎉 Database initialization complete!")
    logger.info(f"Database: {settings.database_url}")
    logger.info("Ready for use!\n")


if __name__ == "__main__":
    init_database()
