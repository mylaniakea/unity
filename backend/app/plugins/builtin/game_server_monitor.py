"""
Game Server Monitor Plugin

Monitors game servers (Minecraft, Valheim, etc.).
Because homelabbing and gaming aren't mutually exclusive!
"""

import socket
import struct
import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class GameServerMonitorPlugin(PluginBase):
    """Monitors game servers"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="game-server-monitor",
            name="Game Server Monitor",
            version="1.0.0",
            description="Monitors game servers including Minecraft, Valheim, and others",
            author="Unity Team",
            category=PluginCategory.APPLICATION,
            tags=["gaming", "minecraft", "valheim", "servers", "multiplayer"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "game": {
                        "type": "string",
                        "enum": ["minecraft", "valheim", "generic"],
                        "description": "Game server type"
                    },
                    "host": {
                        "type": "string",
                        "description": "Server hostname or IP"
                    },
                    "port": {
                        "type": "integer",
                        "description": "Server port"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 5,
                        "description": "Connection timeout in seconds"
                    }
                },
                "required": ["game", "host", "port"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect game server metrics"""
        
        config = self.config or {}
        game = config.get("game")
        host = config.get("host")
        port = config.get("port")
        timeout = config.get("timeout", 5)
        
        if not all([game, host, port]):
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "Game, host, and port required"
            }
        
        if game == "minecraft":
            return await self._check_minecraft(host, port, timeout)
        elif game == "valheim":
            return await self._check_valheim(host, port, timeout)
        elif game == "generic":
            return await self._check_generic(host, port, timeout)
        else:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Unknown game type: {game}"
            }
    
    async def _check_minecraft(self, host: str, port: int, timeout: int) -> Dict[str, Any]:
        """Check Minecraft server using Server List Ping protocol"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            
            # Send handshake and status request (simplified)
            # This is a basic implementation - full protocol is more complex
            handshake = b'\x00'  # Packet ID
            sock.sendall(handshake)
            
            # For simplicity, just check connectivity
            sock.close()
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "game": "minecraft",
                "host": host,
                "port": port,
                "summary": {
                    "online": True,
                    "reachable": True
                }
            }
            
        except socket.timeout:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "game": "minecraft",
                "host": host,
                "port": port,
                "summary": {
                    "online": False,
                    "error": "Connection timeout"
                }
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "game": "minecraft",
                "host": host,
                "port": port,
                "summary": {
                    "online": False,
                    "error": str(e)
                }
            }
    
    async def _check_valheim(self, host: str, port: int, timeout: int) -> Dict[str, Any]:
        """Check Valheim server (Steam query protocol)"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            
            # A2S_INFO query
            query = b'\xFF\xFF\xFF\xFF\x54Source Engine Query\x00'
            sock.sendto(query, (host, port))
            
            data, addr = sock.recvfrom(4096)
            sock.close()
            
            if data:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "game": "valheim",
                    "host": host,
                    "port": port,
                    "summary": {
                        "online": True,
                        "reachable": True
                    }
                }
        except socket.timeout:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "game": "valheim",
                "host": host,
                "port": port,
                "summary": {
                    "online": False,
                    "error": "Connection timeout"
                }
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "game": "valheim",
                "host": host,
                "port": port,
                "summary": {
                    "online": False,
                    "error": str(e)
                }
            }
    
    async def _check_generic(self, host: str, port: int, timeout: int) -> Dict[str, Any]:
        """Generic TCP port check"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            online = result == 0
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "game": "generic",
                "host": host,
                "port": port,
                "summary": {
                    "online": online,
                    "reachable": online
                }
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "game": "generic",
                "host": host,
                "port": port,
                "summary": {
                    "online": False,
                    "error": str(e)
                }
            }
    
    async def health_check(self) -> bool:
        return True  # No external dependencies
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        required = ["game", "host", "port"]
        return all(k in config for k in required)
