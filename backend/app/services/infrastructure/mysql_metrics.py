"""MySQL metrics collection service."""
import logging
import pymysql
from typing import Dict, Optional

from app.services.encryption import EncryptionService

logger = logging.getLogger(__name__)


class MySQLMetricsService:
    """Service for collecting metrics from MySQL/MariaDB databases."""
    
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
        Collect metrics from a MySQL database.
        
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
            "max_connections": None,
            "slow_queries": None,
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
            conn = pymysql.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=self.timeout
            )
            cur = conn.cursor()
            
            # Database size
            cur.execute(f"""
                SELECT SUM(data_length + index_length)
                FROM information_schema.TABLES
                WHERE table_schema = '{database}'
            """)
            result = cur.fetchone()
            metrics["size_bytes"] = result[0] if result and result[0] else 0
            
            # Active connections (threads connected)
            cur.execute("SHOW STATUS LIKE 'Threads_connected'")
            result = cur.fetchone()
            metrics["connection_count"] = int(result[1]) if result else 0
            
            # Running threads (active queries)
            cur.execute("SHOW STATUS LIKE 'Threads_running'")
            result = cur.fetchone()
            metrics["active_queries"] = int(result[1]) if result else 0
            
            # Max connections
            cur.execute("SHOW VARIABLES LIKE 'max_connections'")
            result = cur.fetchone()
            metrics["max_connections"] = int(result[1]) if result else None
            
            # Slow queries
            cur.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries'")
            result = cur.fetchone()
            metrics["slow_queries"] = int(result[1]) if result else 0
            
            # Uptime in seconds
            cur.execute("SHOW STATUS LIKE 'Uptime'")
            result = cur.fetchone()
            metrics["uptime_seconds"] = int(result[1]) if result else None
            
            # Version
            cur.execute("SELECT VERSION()")
            version_str = cur.fetchone()[0]
            # Extract version number
            import re
            match = re.search(r'([\d.]+)', version_str)
            metrics["version"] = match.group(1) if match else version_str[:50]
            
            cur.close()
            metrics["success"] = True
            logger.info(f"Successfully collected metrics from {host}:{port}/{database}")
            
        except pymysql.OperationalError as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.error(f"MySQL metrics collection failed for {host}:{port}/{database}: {error_msg}")
            metrics["error"] = error_msg
        except pymysql.Error as e:
            error_msg = f"Query failed: {str(e)}"
            logger.error(f"MySQL metrics query failed for {host}:{port}/{database}: {error_msg}")
            metrics["error"] = error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error collecting MySQL metrics: {error_msg}")
            metrics["error"] = error_msg
        finally:
            if conn:
                conn.close()
        
        return metrics
