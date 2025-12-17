"""
InfluxDB Monitor Plugin

Monitors InfluxDB time-series databases.
Popular for Grafana, IoT metrics, system monitoring.
"""

from influxdb_client import InfluxDBClient
from influxdb_client.rest import ApiException
from datetime import datetime
from typing import Dict, Any, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class InfluxDBMonitorPlugin(PluginBase):
    """Monitors InfluxDB server metrics and health"""
    
    def __init__(self):
        super().__init__()
        self._client: Optional[InfluxDBClient] = None
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="influxdb-monitor",
            name="InfluxDB Monitor",
            version="1.0.0",
            description="Monitors InfluxDB time-series database including write/query rates, series cardinality, and storage",
            author="Unity Team",
            category=PluginCategory.DATABASE,
            tags=["influxdb", "time-series", "database", "metrics"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["influxdb-client"],
            config_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "default": "http://localhost:8086",
                        "description": "InfluxDB server URL"
                    },
                    "token": {
                        "type": "string",
                        "default": None,
                        "description": "InfluxDB authentication token"
                    },
                    "org": {
                        "type": "string",
                        "default": None,
                        "description": "InfluxDB organization"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 10000,
                        "description": "Request timeout in milliseconds"
                    },
                    "collect_bucket_stats": {
                        "type": "boolean",
                        "default": True,
                        "description": "Collect per-bucket statistics"
                    }
                },
                "required": ["url"]
            }
        )
    
    def _get_client(self) -> InfluxDBClient:
        """Get or create InfluxDB client"""
        if self._client is None:
            self._client = InfluxDBClient(
                url=self.config.get("url", "http://localhost:8086"),
                token=self.config.get("token"),
                org=self.config.get("org"),
                timeout=self.config.get("timeout", 10000)
            )
        return self._client
    
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
        """Collect InfluxDB metrics"""
        
        try:
            client = self._get_client()
            
            # Get health
            health_api = client.health_api()
            health = health_api.get_health()
            
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "connection": {
                    "url": self.config.get("url")
                },
                "health": {
                    "status": health.status,
                    "message": health.message if hasattr(health, 'message') else None,
                    "version": health.version if hasattr(health, 'version') else None
                }
            }
            
            # If we have a token and org, collect more detailed stats
            if self.config.get("token") and self.config.get("org"):
                org = self.config.get("org")
                
                # Get metrics using Flux query
                query_api = client.query_api()
                
                # Query for recent write/query rates
                flux_query = f'''
                from(bucket: "_monitoring")
                    |> range(start: -1m)
                    |> filter(fn: (r) => r["_measurement"] == "query" or r["_measurement"] == "http_request")
                    |> aggregateWindow(every: 1m, fn: count, createEmpty: false)
                '''
                
                try:
                    tables = query_api.query(flux_query, org=org)
                    
                    # Process query results
                    query_count = 0
                    write_count = 0
                    
                    for table in tables:
                        for record in table.records:
                            if record.get_measurement() == "query":
                                query_count += record.get_value()
                            elif record.get_measurement() == "http_request":
                                write_count += record.get_value()
                    
                    data["metrics"] = {
                        "queries_per_minute": query_count,
                        "writes_per_minute": write_count
                    }
                except Exception as e:
                    data["metrics_error"] = f"Could not collect metrics: {str(e)}"
                
                # Get buckets
                if self.config.get("collect_bucket_stats", True):
                    buckets_api = client.buckets_api()
                    buckets = buckets_api.find_buckets(org=org).buckets
                    
                    bucket_info = []
                    for bucket in buckets:
                        bucket_data = {
                            "name": bucket.name,
                            "id": bucket.id,
                            "retention_seconds": bucket.retention_rules[0].every_seconds if bucket.retention_rules else None,
                            "created_at": bucket.created_at.isoformat() if bucket.created_at else None
                        }
                        
                        # Try to get bucket stats via Flux
                        try:
                            stats_query = f'''
                            from(bucket: "{bucket.name}")
                                |> range(start: -24h)
                                |> group()
                                |> count()
                            '''
                            
                            stats_tables = query_api.query(stats_query, org=org)
                            
                            total_points = 0
                            for table in stats_tables:
                                for record in table.records:
                                    total_points += record.get_value()
                            
                            bucket_data["points_last_24h"] = total_points
                        except:
                            bucket_data["points_last_24h"] = None
                        
                        bucket_info.append(bucket_data)
                    
                    data["buckets"] = bucket_info
                
                # Get organizations
                try:
                    orgs_api = client.organizations_api()
                    orgs = orgs_api.find_organizations()
                    
                    data["organizations"] = [
                        {
                            "name": org.name,
                            "id": org.id,
                            "created_at": org.created_at.isoformat() if org.created_at else None
                        }
                        for org in orgs
                    ]
                except Exception as e:
                    data["organizations_error"] = str(e)
            
            return data
            
        except ApiException as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "InfluxDB API error",
                "message": str(e),
                "status_code": e.status if hasattr(e, 'status') else None,
                "influxdb_available": False
            }
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Unexpected error",
                "message": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check InfluxDB server connectivity and health"""
        try:
            client = self._get_client()
            health_api = client.health_api()
            health = health_api.get_health()
            
            return {
                "healthy": health.status == "pass",
                "message": f"InfluxDB status: {health.status}",
                "details": {
                    "status": health.status,
                    "version": health.version if hasattr(health, 'version') else None,
                    "message": health.message if hasattr(health, 'message') else None,
                    "url": self.config.get("url")
                }
            }
            
        except ApiException as e:
            return {
                "healthy": False,
                "message": f"Cannot connect to InfluxDB: {str(e)}",
                "details": {
                    "url": self.config.get("url"),
                    "status_code": e.status if hasattr(e, 'status') else None
                }
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            }
    
    def __del__(self):
        """Cleanup InfluxDB client"""
        if self._client:
            try:
                self._client.close()
            except:
                pass
