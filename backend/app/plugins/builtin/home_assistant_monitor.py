"""
Home Assistant Monitor Plugin

Monitors Home Assistant instance health and status.
HA is the brain of smart homes - brain health matters!
"""

import requests
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class HomeAssistantMonitorPlugin(PluginBase):
    """Monitors Home Assistant instance"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="home-assistant-monitor",
            name="Home Assistant Monitor",
            version="1.0.0",
            description="Monitors Home Assistant instance including entity counts, automation status, integration errors, and system health",
            author="Unity Team",
            category=PluginCategory.IOT,
            tags=["home-assistant", "iot", "smart-home", "automation", "entities"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["requests"],
            config_schema={
                "type": "object",
                "properties": {
                    "api_url": {
                        "type": "string",
                        "default": "http://homeassistant.local:8123",
                        "description": "Home Assistant API URL"
                    },
                    "api_token": {
                        "type": "string",
                        "description": "Long-lived access token"
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "default": 10,
                        "description": "API request timeout"
                    },
                    "verify_ssl": {
                        "type": "boolean",
                        "default": True,
                        "description": "Verify SSL certificates"
                    }
                },
                "required": ["api_url", "api_token"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect Home Assistant metrics"""
        
        config = self.config or {}
        api_url = config.get("api_url", "http://homeassistant.local:8123").rstrip("/")
        api_token = config.get("api_token")
        timeout = config.get("timeout_seconds", 10)
        verify_ssl = config.get("verify_ssl", True)
        
        if not api_token:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "API token is required"
            }
        
        try:
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }
            
            # Get config
            config_response = requests.get(
                f"{api_url}/api/config",
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            config_response.raise_for_status()
            ha_config = config_response.json()
            
            # Get states (all entities)
            states_response = requests.get(
                f"{api_url}/api/states",
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            states_response.raise_for_status()
            states = states_response.json()
            
            # Get services
            services_response = requests.get(
                f"{api_url}/api/services",
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            services_response.raise_for_status()
            services = services_response.json()
            
            # Analyze entities
            entity_counts = {}
            unavailable_entities = []
            
            for entity in states:
                domain = entity.get("entity_id", "").split(".")[0]
                entity_counts[domain] = entity_counts.get(domain, 0) + 1
                
                if entity.get("state") == "unavailable":
                    unavailable_entities.append(entity.get("entity_id"))
            
            # Count automations
            automation_entities = [e for e in states if e.get("entity_id", "").startswith("automation.")]
            automations_on = sum(1 for a in automation_entities if a.get("state") == "on")
            
            # Count integrations (domains in services)
            integration_count = len(services)
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "api_url": api_url,
                "summary": {
                    "version": ha_config.get("version"),
                    "location_name": ha_config.get("location_name"),
                    "total_entities": len(states),
                    "unavailable_entities": len(unavailable_entities),
                    "total_automations": len(automation_entities),
                    "active_automations": automations_on,
                    "integrations": integration_count,
                    "unit_system": ha_config.get("unit_system", {}).get("length"),
                    "time_zone": ha_config.get("time_zone")
                },
                "entity_counts_by_domain": entity_counts,
                "unavailable_entities": unavailable_entities[:20],  # Limit to 20
                "config": {
                    "latitude": ha_config.get("latitude"),
                    "longitude": ha_config.get("longitude"),
                    "elevation": ha_config.get("elevation"),
                    "internal_url": ha_config.get("internal_url"),
                    "external_url": ha_config.get("external_url")
                }
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Failed to connect to Home Assistant: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "api_url": api_url
            }
    
    async def health_check(self) -> bool:
        """Check if Home Assistant is accessible"""
        
        config = self.config or {}
        api_url = config.get("api_url")
        
        if not api_url:
            return False
        
        try:
            response = requests.get(api_url, timeout=5)
            return response.status_code in [200, 401]
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        
        if not config:
            return False
        
        api_url = config.get("api_url")
        api_token = config.get("api_token")
        
        return bool(api_url and api_token)
