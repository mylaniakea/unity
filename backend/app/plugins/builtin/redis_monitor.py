"""
Redis Monitor Plugin

Monitors Redis servers - memory usage, keyspace stats, replication.
Popular for caching, Home Assistant, session storage.
"""

import redis
from datetime import datetime
from typing import Dict, Any, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class RedisMonitorPlugin(PluginBase):
    """Monitors Redis server metrics and health"""
    
    def __init__(self):
        super().__init__()
        self._client: Optional[redis.Redis] = None
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="redis-monitor",
            name="Redis Monitor",
            version="1.0.0",
            description="Monitors Redis server metrics including memory, connections, and keyspace statistics",
            author="Unity Team",
            category=PluginCategory.DATABASE,
            tags=["redis", "database", "cache", "memory"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["redis"],
            config_schema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "default": "localhost",
                        "description": "Redis server hostname"
                    },
                    "port": {
                        "type": "integer",
                        "default": 6379,
                        "description": "Redis server port"
                    },
                    "password": {
                        "type": "string",
                        "default": None,
                        "description": "Redis password (if required)"
                    },
                    "db": {
                        "type": "integer",
                        "default": 0,
                        "description": "Redis database number"
                    },
                    "socket_timeout": {
                        "type": "number",
                        "default": 5.0,
                        "description": "Socket timeout in seconds"
                    },
                    "collect_slowlog": {
                        "type": "boolean",
                        "default": True,
                        "description": "Collect slow query log entries"
                    },
                    "collect_client_list": {
                        "type": "boolean",
                        "default": False,
                        "description": "Collect connected client list (can be expensive)"
                    }
                },
                "required": ["host", "port"]
            }
        )
    
    def _get_client(self) -> redis.Redis:
        """Get or create Redis client"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 6379),
                password=self.config.get("password"),
                db=self.config.get("db", 0),
                socket_timeout=self.config.get("socket_timeout", 5.0),
                decode_responses=True
            )
        return self._client
    
    def _format_bytes(self, bytes_value: int) -> Dict[str, Any]:
        """Format bytes to human-readable form"""
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
    
    def _parse_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Redis INFO output into structured data"""
        
        data = {
            "server": {
                "version": info.get("redis_version"),
                "mode": info.get("redis_mode"),
                "os": info.get("os"),
                "arch_bits": info.get("arch_bits"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "uptime_days": info.get("uptime_in_days")
            },
            "clients": {
                "connected": info.get("connected_clients", 0),
                "blocked": info.get("blocked_clients", 0),
                "tracking": info.get("tracking_clients", 0)
            },
            "memory": {
                "used": self._format_bytes(info.get("used_memory", 0)),
                "used_rss": self._format_bytes(info.get("used_memory_rss", 0)),
                "used_peak": self._format_bytes(info.get("used_memory_peak", 0)),
                "total_system": self._format_bytes(info.get("total_system_memory", 0)),
                "fragmentation_ratio": info.get("mem_fragmentation_ratio", 0),
                "fragmentation_bytes": self._format_bytes(info.get("mem_fragmentation_bytes", 0))
            },
            "stats": {
                "total_connections_received": info.get("total_connections_received", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                "rejected_connections": info.get("rejected_connections", 0),
                "expired_keys": info.get("expired_keys", 0),
                "evicted_keys": info.get("evicted_keys", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            },
            "persistence": {
                "loading": info.get("loading", 0) == 1,
                "rdb_changes_since_last_save": info.get("rdb_changes_since_last_save", 0),
                "rdb_last_save_time": info.get("rdb_last_save_time", 0),
                "rdb_last_bgsave_status": info.get("rdb_last_bgsave_status", "unknown"),
                "aof_enabled": info.get("aof_enabled", 0) == 1,
                "aof_last_rewrite_status": info.get("aof_last_rewrite_status", "unknown") if info.get("aof_enabled") else None
            },
            "replication": {
                "role": info.get("role"),
                "connected_slaves": info.get("connected_slaves", 0),
                "master_link_status": info.get("master_link_status") if info.get("role") == "slave" else None,
                "master_last_io_seconds_ago": info.get("master_last_io_seconds_ago") if info.get("role") == "slave" else None
            },
            "cpu": {
                "used_cpu_sys": info.get("used_cpu_sys", 0),
                "used_cpu_user": info.get("used_cpu_user", 0)
            }
        }
        
        # Calculate hit ratio
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total > 0:
            data["stats"]["hit_ratio"] = round((hits / total) * 100, 2)
        else:
            data["stats"]["hit_ratio"] = 0.0
        
        return data
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect Redis metrics"""
        
        try:
            client = self._get_client()
            
            # Get comprehensive server info
            info = client.info("all")
            parsed_data = self._parse_info(info)
            
            # Get keyspace info
            keyspace = {}
            for key, value in info.items():
                if key.startswith("db"):
                    # Parse db0 format: keys=N,expires=M,avg_ttl=X
                    db_stats = {}
                    for stat in value.split(","):
                        stat_key, stat_value = stat.split("=")
                        db_stats[stat_key] = int(stat_value)
                    keyspace[key] = db_stats
            
            parsed_data["keyspace"] = keyspace
            
            # Collect slowlog if enabled
            if self.config.get("collect_slowlog", True):
                try:
                    slowlog = client.slowlog_get(10)  # Get last 10 slow queries
                    parsed_data["slowlog"] = [
                        {
                            "id": entry["id"],
                            "duration_microseconds": entry["duration"],
                            "command": " ".join(entry["command"]),
                            "timestamp": entry["start_time"]
                        }
                        for entry in slowlog
                    ]
                except Exception as e:
                    parsed_data["slowlog_error"] = str(e)
            
            # Collect client list if enabled (can be expensive)
            if self.config.get("collect_client_list", False):
                try:
                    clients = client.client_list()
                    parsed_data["client_details"] = [
                        {
                            "addr": c.get("addr"),
                            "name": c.get("name"),
                            "age": c.get("age"),
                            "idle": c.get("idle"),
                            "db": c.get("db"),
                            "sub": c.get("sub"),
                            "cmd": c.get("cmd")
                        }
                        for c in clients[:20]  # Limit to 20 clients
                    ]
                except Exception as e:
                    parsed_data["client_list_error"] = str(e)
            
            result = {
                "timestamp": datetime.utcnow().isoformat(),
                "connection": {
                    "host": self.config.get("host"),
                    "port": self.config.get("port"),
                    "db": self.config.get("db", 0)
                },
                "metrics": parsed_data
            }
            
            return result
            
        except redis.ConnectionError as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Connection failed",
                "message": str(e),
                "redis_available": False
            }
        except redis.AuthenticationError as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Authentication failed",
                "message": str(e),
                "redis_available": False
            }
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Unexpected error",
                "message": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis server connectivity and health"""
        try:
            client = self._get_client()
            
            # Test connection with PING
            response = client.ping()
            
            if response:
                # Get basic info
                info = client.info("server")
                
                return {
                    "healthy": True,
                    "message": "Redis server is accessible",
                    "details": {
                        "version": info.get("redis_version"),
                        "mode": info.get("redis_mode"),
                        "uptime_seconds": info.get("uptime_in_seconds")
                    }
                }
            else:
                return {
                    "healthy": False,
                    "message": "PING command failed"
                }
                
        except redis.ConnectionError as e:
            return {
                "healthy": False,
                "message": f"Cannot connect to Redis: {str(e)}",
                "details": {
                    "host": self.config.get("host"),
                    "port": self.config.get("port")
                }
            }
        except redis.AuthenticationError:
            return {
                "healthy": False,
                "message": "Redis authentication failed - check password"
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            }
    
    def __del__(self):
        """Cleanup Redis client"""
        if self._client:
            try:
                self._client.close()
            except:
                pass
