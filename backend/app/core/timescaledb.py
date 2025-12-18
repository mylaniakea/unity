"""
TimescaleDB utilities for Unity.

Handles TimescaleDB extension detection, hypertable creation, and optimizations.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class TimescaleDBManager:
    """Manages TimescaleDB-specific operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def is_available(self) -> bool:
        """Check if TimescaleDB extension is available."""
        try:
            result = self.session.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
            )
            return result.fetchone() is not None
        except Exception as e:
            logger.debug(f"TimescaleDB check failed: {e}")
            return False
    
    def enable_extension(self) -> bool:
        """Enable TimescaleDB extension."""
        try:
            self.session.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
            self.session.commit()
            logger.info("TimescaleDB extension enabled")
            return True
        except Exception as e:
            logger.error(f"Failed to enable TimescaleDB: {e}")
            self.session.rollback()
            return False
    
    def create_hypertable(
        self, 
        table_name: str, 
        time_column: str = 'time',
        chunk_time_interval: str = '7 days'
    ) -> bool:
        """
        Convert a table to a hypertable.
        
        Args:
            table_name: Name of the table
            time_column: Name of the time column
            chunk_time_interval: Chunk size for partitioning
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already a hypertable
            result = self.session.execute(
                text("""
                    SELECT 1 FROM timescaledb_information.hypertables 
                    WHERE hypertable_name = :table_name
                """),
                {"table_name": table_name}
            )
            
            if result.fetchone():
                logger.info(f"Table {table_name} is already a hypertable")
                return True
            
            # Create hypertable
            self.session.execute(
                text(f"""
                    SELECT create_hypertable(
                        '{table_name}',
                        '{time_column}',
                        chunk_time_interval => INTERVAL '{chunk_time_interval}',
                        if_not_exists => TRUE
                    )
                """)
            )
            self.session.commit()
            logger.info(f"Created hypertable: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create hypertable {table_name}: {e}")
            self.session.rollback()
            return False
    
    def set_compression(self, table_name: str, compress_after: str = '7 days') -> bool:
        """
        Enable compression on a hypertable.
        
        Args:
            table_name: Name of the hypertable
            compress_after: Time after which to compress chunks
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Enable compression
            self.session.execute(
                text(f"""
                    ALTER TABLE {table_name} SET (
                        timescaledb.compress,
                        timescaledb.compress_segmentby = 'plugin_id'
                    )
                """)
            )
            
            # Add compression policy
            self.session.execute(
                text(f"""
                    SELECT add_compression_policy(
                        '{table_name}',
                        INTERVAL '{compress_after}'
                    )
                """)
            )
            
            self.session.commit()
            logger.info(f"Enabled compression on {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable compression on {table_name}: {e}")
            self.session.rollback()
            return False
    
    def set_retention_policy(self, table_name: str, retain_for: str = '30 days') -> bool:
        """
        Set data retention policy on a hypertable.
        
        Args:
            table_name: Name of the hypertable
            retain_for: How long to retain data
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.session.execute(
                text(f"""
                    SELECT add_retention_policy(
                        '{table_name}',
                        INTERVAL '{retain_for}'
                    )
                """)
            )
            self.session.commit()
            logger.info(f"Set retention policy on {table_name}: {retain_for}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set retention policy on {table_name}: {e}")
            self.session.rollback()
            return False
    
    def setup_plugin_metrics(self) -> bool:
        """Complete setup for plugin_metrics table."""
        if not self.is_available():
            logger.warning("TimescaleDB not available, skipping hypertable setup")
            return False
        
        success = True
        
        # Create hypertable
        success &= self.create_hypertable('plugin_metrics', 'time', '7 days')
        
        # Enable compression (compress after 7 days)
        success &= self.set_compression('plugin_metrics', '7 days')
        
        # Set retention policy (30 days)
        success &= self.set_retention_policy('plugin_metrics', '30 days')
        
        return success
    
    def setup_alert_history(self) -> bool:
        """Complete setup for alert_history table."""
        if not self.is_available():
            logger.warning("TimescaleDB not available, skipping hypertable setup")
            return False
        
        success = True
        
        # Create hypertable
        success &= self.create_hypertable('alert_history', 'time', '7 days')
        
        # Set retention policy (90 days)
        success &= self.set_retention_policy('alert_history', '90 days')
        
        return success
