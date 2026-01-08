"""
Media Server Monitor Plugin

Monitors Plex, Jellyfin, and Emby media servers.
"Why is Plex buffering?" - Every homelabber, constantly.
"""

import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class MediaServerMonitorPlugin(PluginBase):
    """Monitors Plex, Jellyfin, and Emby media servers"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="media-server-monitor",
            name="Media Server Monitor",
            version="1.0.0",
            description="Monitors Plex, Jellyfin, and Emby media servers including active streams, transcodes, library stats, and user activity",
            author="Unity Team",
            category=PluginCategory.APPLICATION,
            tags=["plex", "jellyfin", "emby", "media", "streaming", "transcode"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["requests"],
            config_schema={
                "type": "object",
                "properties": {
                    "server_type": {
                        "type": "string",
                        "enum": ["plex", "jellyfin", "emby"],
                        "description": "Type of media server"
                    },
                    "api_url": {
                        "type": "string",
                        "description": "Media server API URL"
                    },
                    "api_token": {
                        "type": "string",
                        "description": "API authentication token"
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
                "required": ["server_type", "api_url", "api_token"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect media server metrics"""
        
        config = self.config or {}
        server_type = config.get("server_type", "").lower()
        
        if server_type == "plex":
            return self._monitor_plex(config)
        elif server_type == "jellyfin":
            return self._monitor_jellyfin(config)
        elif server_type == "emby":
            return self._monitor_emby(config)
        else:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Unknown server type: {server_type}",
                "supported_types": ["plex", "jellyfin", "emby"]
            }
    
    def _monitor_plex(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor Plex media server"""
        
        api_url = config.get("api_url", "http://localhost:32400").rstrip("/")
        api_token = config.get("api_token")
        timeout = config.get("timeout_seconds", 10)
        verify_ssl = config.get("verify_ssl", True)
        
        try:
            headers = {"X-Plex-Token": api_token}
            
            # Get sessions (active streams)
            sessions_response = requests.get(
                f"{api_url}/status/sessions",
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            sessions_response.raise_for_status()
            sessions_data = sessions_response.json()
            
            # Get libraries
            libraries_response = requests.get(
                f"{api_url}/library/sections",
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            libraries_response.raise_for_status()
            libraries_data = libraries_response.json()
            
            # Parse sessions
            sessions = []
            transcoding_count = 0
            
            media_container = sessions_data.get("MediaContainer", {})
            for session in media_container.get("Metadata", []):
                is_transcoding = session.get("TranscodeSession") is not None
                if is_transcoding:
                    transcoding_count += 1
                
                sessions.append({
                    "user": session.get("User", {}).get("title", "Unknown"),
                    "title": session.get("title"),
                    "type": session.get("type"),
                    "state": session.get("Player", {}).get("state"),
                    "transcoding": is_transcoding,
                    "video_decision": session.get("TranscodeSession", {}).get("videoDecision") if is_transcoding else "direct"
                })
            
            # Parse libraries
            libraries = []
            total_items = 0
            
            for lib in libraries_data.get("MediaContainer", {}).get("Directory", []):
                item_count = lib.get("count", 0)
                total_items += item_count
                libraries.append({
                    "title": lib.get("title"),
                    "type": lib.get("type"),
                    "count": item_count
                })
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "plex",
                "api_url": api_url,
                "summary": {
                    "active_streams": len(sessions),
                    "transcoding_streams": transcoding_count,
                    "direct_play_streams": len(sessions) - transcoding_count,
                    "total_libraries": len(libraries),
                    "total_items": total_items
                },
                "sessions": sessions,
                "libraries": libraries
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "plex",
                "error": f"Failed to connect to Plex: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "plex",
                "error": str(e),
                "api_url": api_url
            }
    
    def _monitor_jellyfin(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor Jellyfin media server"""
        
        api_url = config.get("api_url", "http://localhost:8096").rstrip("/")
        api_token = config.get("api_token")
        timeout = config.get("timeout_seconds", 10)
        verify_ssl = config.get("verify_ssl", True)
        
        try:
            headers = {"X-Emby-Token": api_token}
            
            # Get sessions
            sessions_response = requests.get(
                f"{api_url}/Sessions",
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            sessions_response.raise_for_status()
            sessions_data = sessions_response.json()
            
            # Get system info
            system_response = requests.get(
                f"{api_url}/System/Info",
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            system_response.raise_for_status()
            system_data = system_response.json()
            
            # Parse sessions
            sessions = []
            transcoding_count = 0
            
            for session in sessions_data:
                now_playing = session.get("NowPlayingItem", {})
                play_state = session.get("PlayState", {})
                transcode_info = session.get("TranscodingInfo", {})
                
                is_transcoding = transcode_info.get("IsVideoDirect") == False
                if is_transcoding:
                    transcoding_count += 1
                
                if now_playing:
                    sessions.append({
                        "user": session.get("UserName", "Unknown"),
                        "title": now_playing.get("Name"),
                        "type": now_playing.get("Type"),
                        "state": "playing" if play_state.get("IsPaused") == False else "paused",
                        "transcoding": is_transcoding,
                        "client": session.get("Client")
                    })
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "jellyfin",
                "api_url": api_url,
                "summary": {
                    "active_streams": len(sessions),
                    "transcoding_streams": transcoding_count,
                    "direct_play_streams": len(sessions) - transcoding_count,
                    "server_name": system_data.get("ServerName"),
                    "version": system_data.get("Version")
                },
                "sessions": sessions
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "jellyfin",
                "error": f"Failed to connect to Jellyfin: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "jellyfin",
                "error": str(e),
                "api_url": api_url
            }
    
    def _monitor_emby(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor Emby media server"""
        
        api_url = config.get("api_url", "http://localhost:8096").rstrip("/")
        api_token = config.get("api_token")
        timeout = config.get("timeout_seconds", 10)
        verify_ssl = config.get("verify_ssl", True)
        
        try:
            headers = {"X-Emby-Token": api_token}
            
            # Get sessions (Emby uses similar API to Jellyfin)
            sessions_response = requests.get(
                f"{api_url}/emby/Sessions",
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            sessions_response.raise_for_status()
            sessions_data = sessions_response.json()
            
            # Parse sessions
            sessions = []
            transcoding_count = 0
            
            for session in sessions_data:
                now_playing = session.get("NowPlayingItem", {})
                play_state = session.get("PlayState", {})
                transcode_info = session.get("TranscodingInfo", {})
                
                is_transcoding = bool(transcode_info)
                if is_transcoding:
                    transcoding_count += 1
                
                if now_playing:
                    sessions.append({
                        "user": session.get("UserName", "Unknown"),
                        "title": now_playing.get("Name"),
                        "type": now_playing.get("Type"),
                        "state": "playing" if not play_state.get("IsPaused") else "paused",
                        "transcoding": is_transcoding,
                        "client": session.get("Client")
                    })
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "emby",
                "api_url": api_url,
                "summary": {
                    "active_streams": len(sessions),
                    "transcoding_streams": transcoding_count,
                    "direct_play_streams": len(sessions) - transcoding_count
                },
                "sessions": sessions
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "emby",
                "error": f"Failed to connect to Emby: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "emby",
                "error": str(e),
                "api_url": api_url
            }
    
    async def health_check(self) -> bool:
        """Check if media server is accessible"""
        
        config = self.config or {}
        api_url = config.get("api_url")
        
        if not api_url:
            return False
        
        try:
            response = requests.get(api_url, timeout=5)
            return response.status_code in [200, 401, 403]
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        
        if not config:
            return False
        
        server_type = config.get("server_type")
        if server_type not in ["plex", "jellyfin", "emby"]:
            return False
        
        api_url = config.get("api_url")
        api_token = config.get("api_token")
        
        if not api_url or not api_token:
            return False
        
        return True
