"""
Email Server Monitor Plugin

Monitors email servers (SMTP/IMAP).
Self-hosting email: brave, possibly foolish, definitely monitored!
"""

import subprocess
import re
from datetime import datetime, timezone
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class EmailServerMonitorPlugin(PluginBase):
    """Monitors email server health"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="email-server-monitor",
            name="Email Server Monitor",
            version="1.0.0",
            description="Monitors email server health including mail queues, service status, and connectivity",
            author="Unity Team",
            category=PluginCategory.NETWORK,
            tags=["email", "smtp", "imap", "postfix", "dovecot", "mail"],
            requires_sudo=False,
            supported_os=["linux"],
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "mta": {
                        "type": "string",
                        "enum": ["postfix", "exim", "sendmail"],
                        "default": "postfix",
                        "description": "Mail transfer agent type"
                    },
                    "check_services": {
                        "type": "boolean",
                        "default": True,
                        "description": "Check systemd service status"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect email server metrics"""
        
        config = self.config or {}
        mta = config.get("mta", "postfix")
        check_services = config.get("check_services", True)
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mta": mta
        }
        
        try:
            # Check mail queue
            if mta == "postfix":
                queue_info = await self._check_postfix_queue()
            elif mta == "exim":
                queue_info = await self._check_exim_queue()
            else:
                queue_info = {"error": f"Unsupported MTA: {mta}"}
            
            results["queue"] = queue_info
            
            # Check service status
            if check_services:
                services_info = await self._check_services(mta)
                results["services"] = services_info
            
            # Calculate summary
            queue_size = queue_info.get("total", 0)
            services_healthy = all(
                s.get("active") for s in results.get("services", {}).values()
            ) if check_services else True
            
            results["summary"] = {
                "queue_size": queue_size,
                "queue_healthy": queue_size < 100,  # Threshold
                "services_healthy": services_healthy,
                "overall_healthy": queue_size < 100 and services_healthy
            }
            
            return results
            
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def _check_postfix_queue(self) -> Dict[str, Any]:
        """Check Postfix mail queue"""
        try:
            result = subprocess.run(
                ["mailq"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout
                
                # Parse queue count
                if "Mail queue is empty" in output:
                    return {"total": 0, "status": "empty"}
                
                # Try to extract count from summary line
                match = re.search(r'-- (\d+) Kbytes in (\d+) Request', output)
                if match:
                    return {
                        "total": int(match.group(2)),
                        "size_kb": int(match.group(1)),
                        "status": "active"
                    }
                
                # Fallback: count message IDs
                message_count = len(re.findall(r'^[A-F0-9]{10,}', output, re.MULTILINE))
                return {"total": message_count, "status": "active"}
            
            return {"error": "Failed to check queue"}
            
        except FileNotFoundError:
            return {"error": "mailq command not found"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _check_exim_queue(self) -> Dict[str, Any]:
        """Check Exim mail queue"""
        try:
            result = subprocess.run(
                ["exim", "-bpc"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                count = int(result.stdout.strip())
                return {
                    "total": count,
                    "status": "empty" if count == 0 else "active"
                }
            
            return {"error": "Failed to check queue"}
            
        except FileNotFoundError:
            return {"error": "exim command not found"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _check_services(self, mta: str) -> Dict[str, Any]:
        """Check systemd service status"""
        services = {}
        
        # Common service names
        service_names = []
        if mta == "postfix":
            service_names = ["postfix", "dovecot"]
        elif mta == "exim":
            service_names = ["exim4", "dovecot"]
        
        for service in service_names:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                services[service] = {
                    "active": result.stdout.strip() == "active"
                }
            except Exception:
                services[service] = {"active": False, "error": "Check failed"}
        
        return services
    
    async def health_check(self) -> bool:
        config = self.config or {}
        mta = config.get("mta", "postfix")
        
        try:
            if mta == "postfix":
                result = subprocess.run(["postconf", "-d"], capture_output=True, timeout=5)
            elif mta == "exim":
                result = subprocess.run(["exim", "-bV"], capture_output=True, timeout=5)
            else:
                return False
            
            return result.returncode == 0
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True  # All config is optional
