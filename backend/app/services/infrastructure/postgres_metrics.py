"""PostgreSQL metrics collection service."""
import logging
import psycopg2
from typing import Dict, Optional
from datetime import datetime

from app.services.core.encryption import EncryptionService

logger = logging.getLogger(__name__)


class PostgreSQLMetricsService:
    """Service for collecting metrics from PostgreSQL databases."""
    
    def __init__(self):
        self.encryption_service = EncryptionService()
        self.timeout = 10  # seconds
    
    def collect_metrics(
        self,
        host: str,
        port: int,
        database: str,
        username: str,
        password_encrypted: Optional[str] = None
    ) -> Dict:
        """
        Collect metrics from a PostgreSQL database.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password_encrypted: Encrypted password
            
        Returns:
            Dictionary with collected metrics
        """
        metrics = {
            "success": False,
            "error": None,
            "size_bytes": None,
            "connection_count": None,
            "active_queries": None,
            "idle_connections": None,
            "max_connections": None,
            "cache_hit_ratio": None,
            "uptime_seconds": None,
            "version": None
        }
        
        # Decrypt password if provided
        password = None
        if password_encrypted:
            try:
                password = self.encryption_service.decrypt(password_encrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt password: {e}")
                metrics["error"] = "Password decryption failed"
                return metrics
        
        conn = None
        try:
            # Establish connection
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=self.timeout
            )
            cur = conn.cursor()
            
            # Database size
            cur.execute(f"SELECT pg_database_size('{database}')")
            metrics["size_bytes"] = cur.fetchone()[0]
            
            # Connection stats
            cur.execute("""
                SELECT 
                    count(*) FILTER (WHERE state = 'active') as active,
                    count(*) FILTER (WHERE state = 'idle') as idle,
                    count(*) as total
                FROM pg_stat_activity
                WHERE datname = %s
            """, (database,))
            row = cur.fetchone()
            metrics["active_queries"] = row[0] if row[0] else 0
            metrics["idle_connections"] = row[1] if row[1] else 0
            metrics["connection_count"] = row[2] if row[2] else 0
            
            # Max connections
            cur.execute("SHOW max_connections")
            metrics["max_connections"] = int(cur.fetchone()[0])
            
            # Cache hit ratio (percentage)
            cur.execute("""
                SELECT 
                    CASE 
                        WHEN (blks_hit + blks_read) > 0 
                        THEN round(100.0 * blks_hit / (blks_hit + blks_read))::integer
                        ELSE 100
                    END as cache_hit_ratio
                FROM pg_stat_database
                WHERE datname = %s
            """, (database,))
            result = cur.fetchone()
            metrics["cache_hit_ratio"] = result[0] if result else None
            
            # Uptime
            cur.execute("SELECT EXTRACT(EPOCH FROM (now() - pg_postmaster_start_time()))::bigint")
            metrics["uptime_seconds"] = cur.fetchone()[0]
            
            # Version
            cur.execute("SELECT version()")
            version_str = cur.fetchone()[0]
            # Extract version number (e.g., "PostgreSQL 14.5")
            import re
            match = re.search(r'PostgreSQL ([\d.]+)', version_str)
            metrics["version"] = match.group(1) if match else version_str[:50]
            
            cur.close()
            metrics["success"] = True
            logger.info(f"Successfully collected metrics from {host}:{port}/{database}")
            
        except psycopg2.OperationalError as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.error(f"PostgreSQL metrics collection failed for {host}:{port}/{database}: {error_msg}")
            metrics["error"] = error_msg
        except psycopg2.Error as e:
            error_msg = f"Query failed: {str(e)}"
            logger.error(f"PostgreSQL metrics query failed for {host}:{port}/{database}: {error_msg}")
            metrics["error"] = error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error collecting PostgreSQL metrics: {error_msg}")
            metrics["error"] = error_msg
        finally:
            if conn:
                conn.close()
        
        return metrics
