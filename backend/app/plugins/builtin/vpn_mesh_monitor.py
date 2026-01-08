"""
VPN Mesh Monitor Plugin

Monitors VPN mesh networks (WireGuard/Tailscale).
Peer-to-peer networking, professionally monitored!
"""

import subprocess
import json
from datetime import datetime, timezone
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class VPNMeshMonitorPlugin(PluginBase):
    """Monitors VPN mesh networks"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="vpn-mesh-monitor",
            name="VPN Mesh Monitor",
            version="1.0.0",
            description="Monitors VPN mesh networks including WireGuard and Tailscale peer connectivity",
            author="Unity Team",
            category=PluginCategory.NETWORK,
            tags=["vpn", "wireguard", "tailscale", "mesh", "peers"],
            requires_sudo=True,
            supported_os=["linux", "darwin"],
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["wireguard", "tailscale"],
                        "description": "VPN type to monitor"
                    },
                    "interface": {
                        "type": "string",
                        "description": "WireGuard interface name (e.g., wg0)"
                    }
                },
                "required": ["type"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect VPN mesh metrics"""
        
        config = self.config or {}
        vpn_type = config.get("type", "wireguard")
        
        if vpn_type == "wireguard":
            return await self._collect_wireguard()
        elif vpn_type == "tailscale":
            return await self._collect_tailscale()
        else:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Unknown VPN type: {vpn_type}"
            }
    
    async def _collect_wireguard(self) -> Dict[str, Any]:
        """Collect WireGuard metrics"""
        config = self.config or {}
        interface = config.get("interface", "wg0")
        
        try:
            result = subprocess.run(
                ["wg", "show", interface, "dump"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": f"WireGuard interface {interface} not found"
                }
            
            peers = []
            lines = result.stdout.strip().split("\n")
            
            # Skip header line
            for line in lines[1:]:
                parts = line.split("\t")
                if len(parts) >= 5:
                    peers.append({
                        "public_key": parts[0][:16] + "...",  # Truncate
                        "endpoint": parts[2] if parts[2] != "(none)" else "N/A",
                        "latest_handshake": int(parts[4]) if parts[4] != "0" else 0,
                        "transfer_rx": int(parts[5]) if len(parts) > 5 else 0,
                        "transfer_tx": int(parts[6]) if len(parts) > 6 else 0
                    })
            
            # Peers are considered active if handshake < 3 minutes old
            active_peers = sum(1 for p in peers if p["latest_handshake"] < 180)
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "wireguard",
                "interface": interface,
                "summary": {
                    "total_peers": len(peers),
                    "active_peers": active_peers,
                    "inactive_peers": len(peers) - active_peers
                },
                "peers": peers
            }
            
        except FileNotFoundError:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "wg command not found"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def _collect_tailscale(self) -> Dict[str, Any]:
        """Collect Tailscale metrics"""
        try:
            # Get status
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": "Tailscale not running or accessible"
                }
            
            status = json.loads(result.stdout)
            
            peers = []
            for peer_id, peer_info in status.get("Peer", {}).items():
                peers.append({
                    "hostname": peer_info.get("HostName", "unknown"),
                    "tailscale_ip": peer_info.get("TailscaleIPs", ["N/A"])[0],
                    "online": peer_info.get("Online", False),
                    "last_seen": peer_info.get("LastSeen", "N/A"),
                    "os": peer_info.get("OS", "unknown")
                })
            
            online_peers = sum(1 for p in peers if p["online"])
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "tailscale",
                "summary": {
                    "total_peers": len(peers),
                    "online_peers": online_peers,
                    "offline_peers": len(peers) - online_peers,
                    "backend_state": status.get("BackendState", "unknown")
                },
                "self": {
                    "hostname": status.get("Self", {}).get("HostName", "unknown"),
                    "tailscale_ip": status.get("Self", {}).get("TailscaleIPs", ["N/A"])[0]
                },
                "peers": peers
            }
            
        except FileNotFoundError:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "tailscale command not found"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def health_check(self) -> bool:
        config = self.config or {}
        vpn_type = config.get("type", "wireguard")
        
        try:
            if vpn_type == "wireguard":
                result = subprocess.run(["wg", "--version"], capture_output=True, timeout=5)
            else:
                result = subprocess.run(["tailscale", "version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        return "type" in config and config["type"] in ["wireguard", "tailscale"]
