"""
MongoDB Monitor Plugin

Monitors MongoDB servers - operations, connections, replication.
Popular for UniFi Controller, document databases.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ConfigurationError
from datetime import datetime
from typing import Dict, Any, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class MongoDBMonitorPlugin(PluginBase):
    """Monitors MongoDB server metrics and health"""
    
    def __init__(self):
        super().__init__()
        self._client: Optional[MongoClient] = None
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="mongodb-monitor",
            name="MongoDB Monitor",
            version="1.0.0",
            description="Monitors MongoDB server metrics including connections, operations, and replication status",
            author="Unity Team",
            category=PluginCategory.DATABASE,
            tags=["mongodb", "database", "nosql", "document-store"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["pymongo"],
            config_schema={
                "type": "object",
                "properties": {
                    "connection_string": {
                        "type": "string",
                        "default": "mongodb://localhost:27017/",
                        "description": "MongoDB connection string (mongodb://host:port/)"
                    },
                    "username": {
                        "type": "string",
                        "default": None,
                        "description": "MongoDB username (if authentication required)"
                    },
                    "password": {
                        "type": "string",
                        "default": None,
                        "description": "MongoDB password"
                    },
                    "auth_source": {
                        "type": "string",
                        "default": "admin",
                        "description": "Authentication database"
                    },
                    "server_timeout_ms": {
                        "type": "integer",
                        "default": 5000,
                        "description": "Server selection timeout in milliseconds"
                    },
                    "collect_db_stats": {
                        "type": "boolean",
                        "default": True,
                        "description": "Collect database statistics"
                    },
                    "max_databases": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of databases to collect stats for"
                    }
                },
                "required": ["connection_string"]
            }
        )
    
    def _get_client(self) -> MongoClient:
        """Get or create MongoDB client"""
        if self._client is None:
            conn_string = self.config.get("connection_string", "mongodb://localhost:27017/")
            username = self.config.get("username")
            password = self.config.get("password")
            auth_source = self.config.get("auth_source", "admin")
            timeout_ms = self.config.get("server_timeout_ms", 5000)
            
            if username and password:
                self._client = MongoClient(
                    conn_string,
                    username=username,
                    password=password,
                    authSource=auth_source,
                    serverSelectionTimeoutMS=timeout_ms
                )
            else:
                self._client = MongoClient(
                    conn_string,
                    serverSelectionTimeoutMS=timeout_ms
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
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect MongoDB metrics"""
        
        try:
            client = self._get_client()
            
            # Force connection
            client.admin.command('ping')
            
            # Get server status
            server_status = client.admin.command('serverStatus')
            
            # Parse server info
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "connection": {
                    "string": self.config.get("connection_string")
                },
                "version": server_status.get("version"),
                "process": server_status.get("process"),
                "uptime_seconds": server_status.get("uptime"),
                "connections": {
                    "current": server_status.get("connections", {}).get("current", 0),
                    "available": server_status.get("connections", {}).get("available", 0),
                    "total_created": server_status.get("connections", {}).get("totalCreated", 0)
                },
                "network": {
                    "bytes_in": self._format_bytes(server_status.get("network", {}).get("bytesIn", 0)),
                    "bytes_out": self._format_bytes(server_status.get("network", {}).get("bytesOut", 0)),
                    "requests": server_status.get("network", {}).get("numRequests", 0)
                },
                "operations": {
                    "insert": server_status.get("opcounters", {}).get("insert", 0),
                    "query": server_status.get("opcounters", {}).get("query", 0),
                    "update": server_status.get("opcounters", {}).get("update", 0),
                    "delete": server_status.get("opcounters", {}).get("delete", 0),
                    "getmore": server_status.get("opcounters", {}).get("getmore", 0),
                    "command": server_status.get("opcounters", {}).get("command", 0)
                },
                "memory": {
                    "resident": self._format_bytes(server_status.get("mem", {}).get("resident", 0) * 1024 * 1024),
                    "virtual": self._format_bytes(server_status.get("mem", {}).get("virtual", 0) * 1024 * 1024),
                    "mapped": self._format_bytes(server_status.get("mem", {}).get("mapped", 0) * 1024 * 1024) if "mapped" in server_status.get("mem", {}) else None
                },
                "locks": {
                    "global": server_status.get("globalLock", {}).get("currentQueue", {}),
                    "active_clients": server_status.get("globalLock", {}).get("activeClients", {})
                }
            }
            
            # Add replication info if available
            if "repl" in server_status:
                repl_info = server_status["repl"]
                data["replication"] = {
                    "is_master": repl_info.get("ismaster", False),
                    "secondary": repl_info.get("secondary", False),
                    "set_name": repl_info.get("setName"),
                    "hosts": repl_info.get("hosts", []),
                    "primary": repl_info.get("primary")
                }
                
                # Add replication lag if this is a secondary
                if repl_info.get("secondary"):
                    try:
                        rs_status = client.admin.command('replSetGetStatus')
                        # Calculate replication lag
                        primary_optime = None
                        secondary_optime = None
                        
                        for member in rs_status.get("members", []):
                            if member.get("stateStr") == "PRIMARY":
                                primary_optime = member.get("optime", {}).get("ts")
                            elif member.get("self"):
                                secondary_optime = member.get("optime", {}).get("ts")
                        
                        if primary_optime and secondary_optime:
                            lag = primary_optime.time - secondary_optime.time
                            data["replication"]["lag_seconds"] = lag
                    except Exception as e:
                        data["replication"]["lag_error"] = str(e)
            
            # Collect database statistics if enabled
            if self.config.get("collect_db_stats", True):
                max_dbs = self.config.get("max_databases", 10)
                db_names = client.list_database_names()[:max_dbs]
                
                databases = []
                for db_name in db_names:
                    if db_name not in ["admin", "local", "config"]:  # Skip system databases
                        try:
                            db_stats = client[db_name].command('dbStats')
                            databases.append({
                                "name": db_name,
                                "collections": db_stats.get("collections", 0),
                                "views": db_stats.get("views", 0),
                                "objects": db_stats.get("objects", 0),
                                "data_size": self._format_bytes(db_stats.get("dataSize", 0)),
                                "storage_size": self._format_bytes(db_stats.get("storageSize", 0)),
                                "indexes": db_stats.get("indexes", 0),
                                "index_size": self._format_bytes(db_stats.get("indexSize", 0))
                            })
                        except Exception as e:
                            databases.append({
                                "name": db_name,
                                "error": str(e)
                            })
                
                data["databases"] = databases
            
            return data
            
        except ConnectionFailure as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Connection failed",
                "message": str(e),
                "mongodb_available": False
            }
        except OperationFailure as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Operation failed (check permissions)",
                "message": str(e),
                "mongodb_available": True
            }
        except ConfigurationError as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Configuration error",
                "message": str(e)
            }
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Unexpected error",
                "message": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check MongoDB server connectivity and health"""
        try:
            client = self._get_client()
            
            # Test connection with ping
            result = client.admin.command('ping')
            
            if result.get('ok') == 1:
                # Get server info
                server_info = client.server_info()
                
                return {
                    "healthy": True,
                    "message": "MongoDB server is accessible",
                    "details": {
                        "version": server_info.get("version"),
                        "max_bson_object_size": server_info.get("maxBsonObjectSize")
                    }
                }
            else:
                return {
                    "healthy": False,
                    "message": "PING command did not return OK"
                }
                
        except ConnectionFailure as e:
            return {
                "healthy": False,
                "message": f"Cannot connect to MongoDB: {str(e)}",
                "details": {
                    "connection_string": self.config.get("connection_string")
                }
            }
        except OperationFailure as e:
            return {
                "healthy": False,
                "message": f"Authentication or permission error: {str(e)}"
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            }
    
    def __del__(self):
        """Cleanup MongoDB client"""
        if self._client:
            try:
                self._client.close()
            except:
                pass
