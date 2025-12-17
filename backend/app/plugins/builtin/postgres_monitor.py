"""
PostgreSQL Monitor Plugin

Monitors PostgreSQL servers - connections, transactions, locks, cache hits.
Popular for modern apps (Immich, Paperless-ngx, Grafana, etc.)
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from typing import Dict, Any, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class PostgreSQLMonitorPlugin(PluginBase):
    """Monitors PostgreSQL server metrics and health"""
    
    def __init__(self):
        super().__init__()
        self._connection: Optional[psycopg2.extensions.connection] = None
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="postgres-monitor",
            name="PostgreSQL Monitor",
            version="1.0.0",
            description="Monitors PostgreSQL server metrics including connections, transactions, locks, and cache performance",
            author="Unity Team",
            category=PluginCategory.DATABASE,
            tags=["postgresql", "postgres", "database", "sql"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["psycopg2-binary"],
            config_schema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "default": "localhost",
                        "description": "PostgreSQL server hostname"
                    },
                    "port": {
                        "type": "integer",
                        "default": 5432,
                        "description": "PostgreSQL server port"
                    },
                    "user": {
                        "type": "string",
                        "default": "postgres",
                        "description": "PostgreSQL username"
                    },
                    "password": {
                        "type": "string",
                        "default": None,
                        "description": "PostgreSQL password"
                    },
                    "database": {
                        "type": "string",
                        "default": "postgres",
                        "description": "Database to connect to"
                    },
                    "connect_timeout": {
                        "type": "integer",
                        "default": 10,
                        "description": "Connection timeout in seconds"
                    },
                    "collect_table_stats": {
                        "type": "boolean",
                        "default": False,
                        "description": "Collect per-table statistics (can be slow)"
                    },
                    "collect_locks": {
                        "type": "boolean",
                        "default": True,
                        "description": "Collect lock information"
                    }
                },
                "required": ["host", "user", "database"]
            }
        )
    
    def _get_connection(self) -> psycopg2.extensions.connection:
        """Get or create PostgreSQL connection"""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 5432),
                user=self.config.get("user", "postgres"),
                password=self.config.get("password"),
                database=self.config.get("database", "postgres"),
                connect_timeout=self.config.get("connect_timeout", 10)
            )
        return self._connection
    
    def _format_bytes(self, bytes_value: int) -> Dict[str, Any]:
        """Format bytes to human-readable form"""
        if bytes_value is None:
            return {"bytes": 0, "formatted": "0 B", "value": 0, "unit": "B"}
        
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(bytes_value)
        unit_index = 0
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
        
        return {
            "bytes": bytes_value,
            "formatted": f"{value:.2f} {units[unit_index]}",
            "value": round(value, 2),
            "unit": units[unit_index]
        }
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect PostgreSQL metrics"""
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Server version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()["version"]
            
            # Connection stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE state = 'active') as active,
                    COUNT(*) FILTER (WHERE state = 'idle') as idle,
                    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
                    COUNT(*) FILTER (WHERE wait_event_type IS NOT NULL) as waiting
                FROM pg_stat_activity
                WHERE pid != pg_backend_pid()
            """)
            conn_stats = cursor.fetchone()
            
            # Max connections
            cursor.execute("SHOW max_connections")
            max_conn = int(cursor.fetchone()["max_connections"])
            
            connections = {
                "total": conn_stats["total"],
                "active": conn_stats["active"],
                "idle": conn_stats["idle"],
                "idle_in_transaction": conn_stats["idle_in_transaction"],
                "waiting": conn_stats["waiting"],
                "max": max_conn,
                "usage_percent": round((conn_stats["total"] / max_conn) * 100, 2) if max_conn > 0 else 0
            }
            
            # Database stats
            cursor.execute("""
                SELECT 
                    datname,
                    numbackends as connections,
                    xact_commit as commits,
                    xact_rollback as rollbacks,
                    blks_read as disk_blocks_read,
                    blks_hit as buffer_blocks_hit,
                    tup_returned as rows_returned,
                    tup_fetched as rows_fetched,
                    tup_inserted as rows_inserted,
                    tup_updated as rows_updated,
                    tup_deleted as rows_deleted,
                    conflicts,
                    temp_files,
                    temp_bytes,
                    deadlocks,
                    blk_read_time as disk_read_time_ms,
                    blk_write_time as disk_write_time_ms
                FROM pg_stat_database
                WHERE datname NOT IN ('template0', 'template1')
                ORDER BY datname
            """)
            
            databases = []
            total_commits = 0
            total_rollbacks = 0
            total_disk_read = 0
            total_buffer_hit = 0
            
            for row in cursor.fetchall():
                db_info = dict(row)
                
                # Calculate cache hit ratio
                disk_read = db_info["disk_blocks_read"] or 0
                buffer_hit = db_info["buffer_blocks_hit"] or 0
                total_blocks = disk_read + buffer_hit
                
                if total_blocks > 0:
                    db_info["cache_hit_ratio"] = round((buffer_hit / total_blocks) * 100, 2)
                else:
                    db_info["cache_hit_ratio"] = 0.0
                
                # Format temp bytes
                if db_info["temp_bytes"]:
                    db_info["temp_size"] = self._format_bytes(db_info["temp_bytes"])
                
                databases.append(db_info)
                
                total_commits += db_info["commits"] or 0
                total_rollbacks += db_info["rollbacks"] or 0
                total_disk_read += disk_read
                total_buffer_hit += buffer_hit
            
            # Calculate overall cache hit ratio
            total_blocks = total_disk_read + total_buffer_hit
            cache_hit_ratio = round((total_buffer_hit / total_blocks) * 100, 2) if total_blocks > 0 else 0.0
            
            # Transaction stats
            transactions = {
                "total_commits": total_commits,
                "total_rollbacks": total_rollbacks,
                "rollback_ratio": round((total_rollbacks / max(total_commits + total_rollbacks, 1)) * 100, 2)
            }
            
            # Database sizes
            cursor.execute("""
                SELECT 
                    datname as database,
                    pg_database_size(datname) as size_bytes
                FROM pg_database
                WHERE datname NOT IN ('template0', 'template1')
                ORDER BY size_bytes DESC
            """)
            
            database_sizes = [
                {
                    "database": row["database"],
                    "size": self._format_bytes(row["size_bytes"])
                }
                for row in cursor.fetchall()
            ]
            
            # Replication status
            replication = None
            try:
                cursor.execute("""
                    SELECT 
                        client_addr,
                        state,
                        sync_state,
                        replay_lag,
                        write_lag,
                        flush_lag
                    FROM pg_stat_replication
                """)
                
                replicas = cursor.fetchall()
                if replicas:
                    replication = {
                        "role": "primary",
                        "replicas": [
                            {
                                "client": row["client_addr"],
                                "state": row["state"],
                                "sync_state": row["sync_state"],
                                "replay_lag_ms": row["replay_lag"].total_seconds() * 1000 if row["replay_lag"] else 0,
                                "write_lag_ms": row["write_lag"].total_seconds() * 1000 if row["write_lag"] else 0,
                                "flush_lag_ms": row["flush_lag"].total_seconds() * 1000 if row["flush_lag"] else 0
                            }
                            for row in replicas
                        ]
                    }
                else:
                    # Check if we're a standby
                    cursor.execute("SELECT pg_is_in_recovery()")
                    is_standby = cursor.fetchone()["pg_is_in_recovery"]
                    replication = {"role": "standby" if is_standby else "standalone"}
            except Exception as e:
                replication = {"error": str(e)}
            
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "connection": {
                    "host": self.config.get("host"),
                    "port": self.config.get("port"),
                    "database": self.config.get("database")
                },
                "version": version,
                "connections": connections,
                "transactions": transactions,
                "cache_hit_ratio": cache_hit_ratio,
                "databases": databases,
                "database_sizes": database_sizes,
                "replication": replication
            }
            
            # Optional: Collect locks
            if self.config.get("collect_locks", True):
                cursor.execute("""
                    SELECT 
                        locktype,
                        database,
                        relation::regclass as relation,
                        mode,
                        COUNT(*) as count
                    FROM pg_locks
                    WHERE NOT granted
                    GROUP BY locktype, database, relation, mode
                    ORDER BY count DESC
                    LIMIT 10
                """)
                
                locks = [dict(row) for row in cursor.fetchall()]
                data["locks"] = locks
            
            # Long running queries
            cursor.execute("""
                SELECT 
                    pid,
                    now() - query_start as duration,
                    state,
                    query
                FROM pg_stat_activity
                WHERE state != 'idle'
                    AND pid != pg_backend_pid()
                    AND query_start IS NOT NULL
                ORDER BY duration DESC
                LIMIT 5
            """)
            
            long_queries = []
            for row in cursor.fetchall():
                long_queries.append({
                    "pid": row["pid"],
                    "duration_seconds": row["duration"].total_seconds() if row["duration"] else 0,
                    "state": row["state"],
                    "query": row["query"][:200]  # Truncate long queries
                })
            
            data["long_running_queries"] = long_queries
            
            return data
            
        except psycopg2.Error as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "PostgreSQL error",
                "message": str(e),
                "postgres_available": False
            }
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Unexpected error",
                "message": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check PostgreSQL server connectivity and health"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Test connection
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            # Get version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            
            # Check if in recovery (standby)
            cursor.execute("SELECT pg_is_in_recovery()")
            is_standby = cursor.fetchone()[0]
            
            return {
                "healthy": True,
                "message": "PostgreSQL server is accessible",
                "details": {
                    "version": version.split(",")[0],  # First part of version string
                    "role": "standby" if is_standby else "primary",
                    "host": self.config.get("host"),
                    "port": self.config.get("port")
                }
            }
            
        except psycopg2.Error as e:
            return {
                "healthy": False,
                "message": f"Cannot connect to PostgreSQL: {str(e)}",
                "details": {
                    "host": self.config.get("host"),
                    "port": self.config.get("port")
                }
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            }
    
    def __del__(self):
        """Cleanup PostgreSQL connection"""
        if self._connection and not self._connection.closed:
            try:
                self._connection.close()
            except:
                pass
