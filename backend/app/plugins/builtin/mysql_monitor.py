"""
MySQL/MariaDB Monitor Plugin

Monitors MySQL and MariaDB servers - connections, queries, replication.
Very common in homelabs (Nextcloud, WordPress, etc.)
"""

import pymysql
from datetime import datetime
from typing import Dict, Any, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class MySQLMonitorPlugin(PluginBase):
    """Monitors MySQL/MariaDB server metrics and health"""
    
    def __init__(self):
        super().__init__()
        self._connection: Optional[pymysql.Connection] = None
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="mysql-monitor",
            name="MySQL/MariaDB Monitor",
            version="1.0.0",
            description="Monitors MySQL and MariaDB server metrics including connections, queries, and replication status",
            author="Unity Team",
            category=PluginCategory.DATABASE,
            tags=["mysql", "mariadb", "database", "sql"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["pymysql"],
            config_schema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "default": "localhost",
                        "description": "MySQL server hostname"
                    },
                    "port": {
                        "type": "integer",
                        "default": 3306,
                        "description": "MySQL server port"
                    },
                    "user": {
                        "type": "string",
                        "default": "root",
                        "description": "MySQL username"
                    },
                    "password": {
                        "type": "string",
                        "default": None,
                        "description": "MySQL password"
                    },
                    "database": {
                        "type": "string",
                        "default": None,
                        "description": "Database to connect to (optional)"
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
                    "collect_processlist": {
                        "type": "boolean",
                        "default": True,
                        "description": "Collect running query information"
                    }
                },
                "required": ["host", "user"]
            }
        )
    
    def _get_connection(self) -> pymysql.Connection:
        """Get or create MySQL connection"""
        if self._connection is None or not self._connection.open:
            self._connection = pymysql.connect(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 3306),
                user=self.config.get("user", "root"),
                password=self.config.get("password"),
                database=self.config.get("database"),
                connect_timeout=self.config.get("connect_timeout", 10),
                cursorclass=pymysql.cursors.DictCursor
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
    
    def _get_status_dict(self, conn: pymysql.Connection) -> Dict[str, Any]:
        """Get MySQL status variables as dictionary"""
        cursor = conn.cursor()
        cursor.execute("SHOW GLOBAL STATUS")
        return {row["Variable_name"]: row["Value"] for row in cursor.fetchall()}
    
    def _get_variables_dict(self, conn: pymysql.Connection) -> Dict[str, Any]:
        """Get MySQL variables as dictionary"""
        cursor = conn.cursor()
        cursor.execute("SHOW GLOBAL VARIABLES")
        return {row["Variable_name"]: row["Value"] for row in cursor.fetchall()}
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect MySQL metrics"""
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get status and variables
            status = self._get_status_dict(conn)
            variables = self._get_variables_dict(conn)
            
            # Server info
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()["VERSION()"]
            
            # Uptime
            uptime_seconds = int(status.get("Uptime", 0))
            
            # Connection stats
            connections = {
                "current": int(status.get("Threads_connected", 0)),
                "running": int(status.get("Threads_running", 0)),
                "cached": int(status.get("Threads_cached", 0)),
                "created": int(status.get("Threads_created", 0)),
                "max": int(variables.get("max_connections", 0)),
                "total_created": int(status.get("Connections", 0)),
                "aborted_clients": int(status.get("Aborted_clients", 0)),
                "aborted_connects": int(status.get("Aborted_connects", 0))
            }
            
            # Calculate connection usage percentage
            if connections["max"] > 0:
                connections["usage_percent"] = round(
                    (connections["current"] / connections["max"]) * 100, 2
                )
            
            # Query stats
            queries = {
                "total": int(status.get("Questions", 0)),
                "per_second": round(int(status.get("Questions", 0)) / max(uptime_seconds, 1), 2),
                "slow_queries": int(status.get("Slow_queries", 0)),
                "slow_query_threshold": float(variables.get("long_query_time", 10))
            }
            
            # Command breakdown
            queries["commands"] = {
                "select": int(status.get("Com_select", 0)),
                "insert": int(status.get("Com_insert", 0)),
                "update": int(status.get("Com_update", 0)),
                "delete": int(status.get("Com_delete", 0)),
                "replace": int(status.get("Com_replace", 0))
            }
            
            # Buffer pool stats (InnoDB)
            innodb = {
                "buffer_pool_size": self._format_bytes(int(variables.get("innodb_buffer_pool_size", 0))),
                "buffer_pool_pages_total": int(status.get("Innodb_buffer_pool_pages_total", 0)),
                "buffer_pool_pages_free": int(status.get("Innodb_buffer_pool_pages_free", 0)),
                "buffer_pool_pages_data": int(status.get("Innodb_buffer_pool_pages_data", 0)),
                "buffer_pool_pages_dirty": int(status.get("Innodb_buffer_pool_pages_dirty", 0)),
                "buffer_pool_read_requests": int(status.get("Innodb_buffer_pool_read_requests", 0)),
                "buffer_pool_reads": int(status.get("Innodb_buffer_pool_reads", 0))
            }
            
            # Calculate buffer pool hit ratio
            read_requests = innodb["buffer_pool_read_requests"]
            reads = innodb["buffer_pool_reads"]
            if read_requests > 0:
                innodb["hit_ratio"] = round(((read_requests - reads) / read_requests) * 100, 2)
            else:
                innodb["hit_ratio"] = 0.0
            
            # Table cache
            table_cache = {
                "open_tables": int(status.get("Open_tables", 0)),
                "opened_tables": int(status.get("Opened_tables", 0)),
                "table_open_cache": int(variables.get("table_open_cache", 0))
            }
            
            # Replication status
            replication = None
            try:
                cursor.execute("SHOW SLAVE STATUS")
                slave_status = cursor.fetchone()
                if slave_status:
                    replication = {
                        "role": "slave",
                        "slave_io_running": slave_status.get("Slave_IO_Running") == "Yes",
                        "slave_sql_running": slave_status.get("Slave_SQL_Running") == "Yes",
                        "seconds_behind_master": slave_status.get("Seconds_Behind_Master"),
                        "master_host": slave_status.get("Master_Host"),
                        "master_port": slave_status.get("Master_Port"),
                        "last_error": slave_status.get("Last_Error") or None
                    }
            except:
                # Not a slave or no permissions
                replication = {"role": "master_or_standalone"}
            
            # Database sizes
            databases = []
            cursor.execute("""
                SELECT 
                    table_schema as database_name,
                    SUM(data_length + index_length) as total_size,
                    SUM(data_length) as data_size,
                    SUM(index_length) as index_size,
                    COUNT(*) as table_count
                FROM information_schema.TABLES
                WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
                GROUP BY table_schema
            """)
            
            for row in cursor.fetchall():
                databases.append({
                    "name": row["database_name"],
                    "total_size": self._format_bytes(row["total_size"] or 0),
                    "data_size": self._format_bytes(row["data_size"] or 0),
                    "index_size": self._format_bytes(row["index_size"] or 0),
                    "table_count": row["table_count"]
                })
            
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "connection": {
                    "host": self.config.get("host"),
                    "port": self.config.get("port")
                },
                "version": version,
                "uptime_seconds": uptime_seconds,
                "connections": connections,
                "queries": queries,
                "innodb": innodb,
                "table_cache": table_cache,
                "replication": replication,
                "databases": databases
            }
            
            # Optional: Collect process list
            if self.config.get("collect_processlist", True):
                cursor.execute("SHOW FULL PROCESSLIST")
                processlist = []
                for row in cursor.fetchall():
                    if row.get("Command") != "Sleep":  # Skip idle connections
                        processlist.append({
                            "id": row.get("Id"),
                            "user": row.get("User"),
                            "host": row.get("Host"),
                            "db": row.get("db"),
                            "command": row.get("Command"),
                            "time": row.get("Time"),
                            "state": row.get("State"),
                            "info": row.get("Info")[:100] if row.get("Info") else None  # Truncate long queries
                        })
                
                data["processlist"] = processlist[:20]  # Limit to 20 processes
            
            return data
            
        except pymysql.MySQLError as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "MySQL error",
                "message": str(e),
                "mysql_available": False
            }
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Unexpected error",
                "message": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check MySQL server connectivity and health"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Test connection
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            # Get version
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()["VERSION()"]
            
            # Check if MariaDB
            is_mariadb = "MariaDB" in version
            
            return {
                "healthy": True,
                "message": "MySQL/MariaDB server is accessible",
                "details": {
                    "version": version,
                    "type": "MariaDB" if is_mariadb else "MySQL",
                    "host": self.config.get("host"),
                    "port": self.config.get("port")
                }
            }
            
        except pymysql.MySQLError as e:
            return {
                "healthy": False,
                "message": f"Cannot connect to MySQL: {str(e)}",
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
        """Cleanup MySQL connection"""
        if self._connection:
            try:
                self._connection.close()
            except:
                pass
