"""
VPN Monitor Plugin

Monitors WireGuard and OpenVPN connections, tunnels, and bandwidth.
Remote access is critical - knowing your VPN is healthy means peace of mind.
"""

import subprocess
import re
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class VPNMonitorPlugin(PluginBase):
    """Monitors WireGuard and OpenVPN connections"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="vpn-monitor",
            name="VPN Monitor",
            version="1.0.0",
            description="Monitors WireGuard and OpenVPN VPN connections including tunnels, peers, bandwidth, and connection status",
            author="Unity Team",
            category=PluginCategory.SECURITY,
            tags=["vpn", "wireguard", "openvpn", "tunnel", "remote-access", "security"],
            requires_sudo=True,  # WireGuard and OpenVPN commands often need sudo
            supported_os=["linux", "darwin"],
            dependencies=[],  # Uses system commands
            config_schema={
                "type": "object",
                "properties": {
                    "vpn_type": {
                        "type": "string",
                        "enum": ["wireguard", "openvpn"],
                        "description": "Type of VPN to monitor"
                    },
                    "interface": {
                        "type": "string",
                        "description": "VPN interface name (e.g., wg0 for WireGuard, tun0 for OpenVPN)"
                    },
                    "management_socket": {
                        "type": "string",
                        "description": "OpenVPN management socket path (for OpenVPN only)"
                    }
                },
                "required": ["vpn_type"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect VPN metrics"""
        
        config = self.config or {}
        vpn_type = config.get("vpn_type", "").lower()
        
        if vpn_type == "wireguard":
            return self._monitor_wireguard(config)
        elif vpn_type == "openvpn":
            return self._monitor_openvpn(config)
        else:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Unknown VPN type: {vpn_type}",
                "supported_types": ["wireguard", "openvpn"]
            }
    
    def _monitor_wireguard(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor WireGuard VPN"""
        
        interface = config.get("interface")
        
        try:
            # Get WireGuard status
            cmd = ["sudo", "wg", "show"]
            if interface:
                cmd.append(interface)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "vpn_type": "wireguard",
                    "error": "Failed to get WireGuard status",
                    "stderr": result.stderr
                }
            
            # Parse WireGuard output
            interfaces = self._parse_wireguard_output(result.stdout)
            
            # Calculate summary
            total_interfaces = len(interfaces)
            total_peers = sum(len(iface.get("peers", [])) for iface in interfaces)
            active_peers = sum(
                sum(1 for peer in iface.get("peers", []) if peer.get("latest_handshake_seconds", float('inf')) < 180)
                for iface in interfaces
            )
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "vpn_type": "wireguard",
                "summary": {
                    "total_interfaces": total_interfaces,
                    "total_peers": total_peers,
                    "active_peers": active_peers,
                    "inactive_peers": total_peers - active_peers
                },
                "interfaces": interfaces
            }
            
        except FileNotFoundError:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "vpn_type": "wireguard",
                "error": "wg command not found - is WireGuard installed?"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "vpn_type": "wireguard",
                "error": str(e)
            }
    
    def _parse_wireguard_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse wg show output"""
        
        interfaces = []
        current_interface = None
        current_peer = None
        
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
            
            # Interface line
            if line.startswith("interface:"):
                if current_interface:
                    interfaces.append(current_interface)
                current_interface = {
                    "name": line.split(":")[1].strip(),
                    "peers": []
                }
                current_peer = None
            
            # Public key (interface)
            elif line.strip().startswith("public key:") and current_interface and not current_peer:
                current_interface["public_key"] = line.split(":")[1].strip()
            
            # Private key
            elif line.strip().startswith("private key:"):
                current_interface["private_key"] = "(hidden)"
            
            # Listening port
            elif line.strip().startswith("listening port:"):
                current_interface["port"] = int(line.split(":")[1].strip())
            
            # Peer
            elif line.startswith("peer:"):
                if current_peer:
                    current_interface["peers"].append(current_peer)
                current_peer = {
                    "public_key": line.split(":")[1].strip()
                }
            
            # Peer endpoint
            elif line.strip().startswith("endpoint:") and current_peer:
                current_peer["endpoint"] = line.split(":")[1].strip()
            
            # Peer allowed IPs
            elif line.strip().startswith("allowed ips:") and current_peer:
                current_peer["allowed_ips"] = line.split(":")[1].strip()
            
            # Latest handshake
            elif line.strip().startswith("latest handshake:") and current_peer:
                handshake_str = line.split(":")[1].strip()
                current_peer["latest_handshake"] = handshake_str
                # Parse seconds ago
                if "seconds ago" in handshake_str or "second ago" in handshake_str:
                    seconds = int(re.search(r'(\d+)', handshake_str).group(1))
                    current_peer["latest_handshake_seconds"] = seconds
                elif "minutes ago" in handshake_str or "minute ago" in handshake_str:
                    minutes = int(re.search(r'(\d+)', handshake_str).group(1))
                    current_peer["latest_handshake_seconds"] = minutes * 60
            
            # Transfer stats
            elif line.strip().startswith("transfer:") and current_peer:
                transfer = line.split(":")[1].strip()
                parts = transfer.split(",")
                if len(parts) == 2:
                    current_peer["transfer_rx"] = parts[0].strip().split()[0]
                    current_peer["transfer_tx"] = parts[1].strip().split()[0]
        
        # Add last peer and interface
        if current_peer:
            current_interface["peers"].append(current_peer)
        if current_interface:
            interfaces.append(current_interface)
        
        return interfaces
    
    def _monitor_openvpn(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor OpenVPN"""
        
        management_socket = config.get("management_socket")
        
        if management_socket:
            return self._monitor_openvpn_socket(management_socket)
        else:
            return self._monitor_openvpn_ps()
    
    def _monitor_openvpn_socket(self, socket_path: str) -> Dict[str, Any]:
        """Monitor OpenVPN via management socket"""
        
        # This would require socket connection implementation
        # For now, return not implemented
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vpn_type": "openvpn",
            "error": "Management socket monitoring not yet implemented",
            "note": "Use process monitoring fallback"
        }
    
    def _monitor_openvpn_ps(self) -> Dict[str, Any]:
        """Monitor OpenVPN via process status"""
        
        try:
            # Check for OpenVPN processes
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            openvpn_procs = []
            for line in result.stdout.split('\n'):
                if 'openvpn' in line.lower() and 'grep' not in line:
                    openvpn_procs.append(line.strip())
            
            # Get tunnel interfaces
            ip_result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            tunnels = []
            for line in ip_result.stdout.split('\n'):
                if 'tun' in line or 'tap' in line:
                    match = re.search(r'(\d+): (\w+):', line)
                    if match:
                        tunnels.append({
                            "index": match.group(1),
                            "name": match.group(2),
                            "status": "UP" if "UP" in line else "DOWN"
                        })
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "vpn_type": "openvpn",
                "summary": {
                    "running_processes": len(openvpn_procs),
                    "active_tunnels": len([t for t in tunnels if t["status"] == "UP"]),
                    "total_tunnels": len(tunnels)
                },
                "processes": openvpn_procs,
                "tunnels": tunnels
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "vpn_type": "openvpn",
                "error": str(e)
            }
    
    async def health_check(self) -> bool:
        """Check if VPN monitoring is available"""
        
        config = self.config or {}
        vpn_type = config.get("vpn_type", "").lower()
        
        try:
            if vpn_type == "wireguard":
                result = subprocess.run(
                    ["wg", "version"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            elif vpn_type == "openvpn":
                result = subprocess.run(
                    ["which", "openvpn"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
        except Exception:
            return False
        
        return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        
        if not config:
            return False
        
        vpn_type = config.get("vpn_type")
        if vpn_type not in ["wireguard", "openvpn"]:
            return False
        
        return True
