"""
Download Manager Monitor Plugin

Monitors qBittorrent, Transmission, and SABnzbd download managers.
Automation is beautiful until you realize nothing downloaded all week.
"""

import requests
import base64
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class DownloadManagerMonitorPlugin(PluginBase):
    """Monitors download managers (qBittorrent, Transmission, SABnzbd)"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="download-manager-monitor",
            name="Download Manager Monitor",
            version="1.0.0",
            description="Monitors qBittorrent, Transmission, and SABnzbd download managers including active downloads, queue, speeds, and disk space",
            author="Unity Team",
            category=PluginCategory.APPLICATION,
            tags=["downloads", "qbittorrent", "transmission", "sabnzbd", "torrents", "usenet"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["requests"],
            config_schema={
                "type": "object",
                "properties": {
                    "manager_type": {
                        "type": "string",
                        "enum": ["qbittorrent", "transmission", "sabnzbd"],
                        "description": "Type of download manager"
                    },
                    "api_url": {
                        "type": "string",
                        "description": "Download manager API URL"
                    },
                    "username": {
                        "type": "string",
                        "description": "Authentication username"
                    },
                    "password": {
                        "type": "string",
                        "description": "Authentication password"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "API key (for SABnzbd)"
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "default": 10,
                        "description": "API request timeout"
                    }
                },
                "required": ["manager_type", "api_url"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect download manager metrics"""
        
        config = self.config or {}
        manager_type = config.get("manager_type", "").lower()
        
        if manager_type == "qbittorrent":
            return self._monitor_qbittorrent(config)
        elif manager_type == "transmission":
            return self._monitor_transmission(config)
        elif manager_type == "sabnzbd":
            return self._monitor_sabnzbd(config)
        else:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Unknown manager type: {manager_type}",
                "supported_types": ["qbittorrent", "transmission", "sabnzbd"]
            }
    
    def _monitor_qbittorrent(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor qBittorrent"""
        
        api_url = config.get("api_url", "http://localhost:8080").rstrip("/")
        username = config.get("username", "admin")
        password = config.get("password", "")
        timeout = config.get("timeout_seconds", 10)
        
        try:
            # Login
            session = requests.Session()
            login_response = session.post(
                f"{api_url}/api/v2/auth/login",
                data={"username": username, "password": password},
                timeout=timeout
            )
            login_response.raise_for_status()
            
            # Get torrents
            torrents_response = session.get(
                f"{api_url}/api/v2/torrents/info",
                timeout=timeout
            )
            torrents_response.raise_for_status()
            torrents = torrents_response.json()
            
            # Get transfer info
            transfer_response = session.get(
                f"{api_url}/api/v2/transfer/info",
                timeout=timeout
            )
            transfer_response.raise_for_status()
            transfer = transfer_response.json()
            
            # Calculate stats
            downloading = [t for t in torrents if t.get("state") in ["downloading", "stalledDL", "metaDL"]]
            uploading = [t for t in torrents if t.get("state") in ["uploading", "stalledUP"]]
            paused = [t for t in torrents if t.get("state") == "pausedDL"]
            completed = [t for t in torrents if t.get("state") in ["uploading", "stalledUP"] and t.get("progress") == 1]
            
            total_size_downloading = sum(t.get("size", 0) for t in downloading)
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "manager_type": "qbittorrent",
                "api_url": api_url,
                "summary": {
                    "total_torrents": len(torrents),
                    "downloading": len(downloading),
                    "uploading": len(uploading),
                    "paused": len(paused),
                    "completed": len(completed),
                    "download_speed_bytes": transfer.get("dl_info_speed", 0),
                    "upload_speed_bytes": transfer.get("up_info_speed", 0),
                    "total_downloaded_bytes": transfer.get("dl_info_data", 0),
                    "total_uploaded_bytes": transfer.get("up_info_data", 0)
                },
                "torrents": [{
                    "name": t.get("name"),
                    "state": t.get("state"),
                    "progress": round(t.get("progress", 0) * 100, 1),
                    "size_bytes": t.get("size"),
                    "download_speed": t.get("dlspeed"),
                    "upload_speed": t.get("upspeed"),
                    "eta_seconds": t.get("eta")
                } for t in torrents[:10]]  # Limit to 10 recent
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "manager_type": "qbittorrent",
                "error": f"Failed to connect to qBittorrent: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "manager_type": "qbittorrent",
                "error": str(e),
                "api_url": api_url
            }
    
    def _monitor_transmission(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor Transmission"""
        
        api_url = config.get("api_url", "http://localhost:9091").rstrip("/")
        username = config.get("username")
        password = config.get("password")
        timeout = config.get("timeout_seconds", 10)
        
        try:
            session = requests.Session()
            if username and password:
                session.auth = (username, password)
            
            # Get session ID
            response = session.get(f"{api_url}/transmission/rpc", timeout=timeout)
            session_id = response.headers.get("X-Transmission-Session-Id")
            
            headers = {"X-Transmission-Session-Id": session_id}
            
            # Get torrent list
            rpc_request = {
                "method": "torrent-get",
                "arguments": {
                    "fields": ["id", "name", "status", "percentDone", "rateDownload", "rateUpload", 
                              "totalSize", "eta", "uploadRatio"]
                }
            }
            
            torrents_response = session.post(
                f"{api_url}/transmission/rpc",
                json=rpc_request,
                headers=headers,
                timeout=timeout
            )
            torrents_response.raise_for_status()
            torrents_data = torrents_response.json()
            
            # Get session stats
            stats_request = {"method": "session-stats"}
            stats_response = session.post(
                f"{api_url}/transmission/rpc",
                json=stats_request,
                headers=headers,
                timeout=timeout
            )
            stats_response.raise_for_status()
            stats_data = stats_response.json()
            
            torrents = torrents_data.get("arguments", {}).get("torrents", [])
            stats = stats_data.get("arguments", {})
            
            # Calculate stats
            downloading = [t for t in torrents if t.get("status") == 4]  # Downloading
            seeding = [t for t in torrents if t.get("status") == 6]  # Seeding
            paused = [t for t in torrents if t.get("status") == 0]  # Stopped
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "manager_type": "transmission",
                "api_url": api_url,
                "summary": {
                    "total_torrents": len(torrents),
                    "downloading": len(downloading),
                    "seeding": len(seeding),
                    "paused": len(paused),
                    "download_speed_bytes": stats.get("downloadSpeed", 0),
                    "upload_speed_bytes": stats.get("uploadSpeed", 0),
                    "active_count": stats.get("activeTorrentCount", 0)
                },
                "torrents": [{
                    "name": t.get("name"),
                    "status": t.get("status"),
                    "progress": round(t.get("percentDone", 0) * 100, 1),
                    "size_bytes": t.get("totalSize"),
                    "download_speed": t.get("rateDownload"),
                    "upload_speed": t.get("rateUpload"),
                    "eta_seconds": t.get("eta")
                } for t in torrents[:10]]
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "manager_type": "transmission",
                "error": f"Failed to connect to Transmission: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "manager_type": "transmission",
                "error": str(e),
                "api_url": api_url
            }
    
    def _monitor_sabnzbd(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor SABnzbd"""
        
        api_url = config.get("api_url", "http://localhost:8080").rstrip("/")
        api_key = config.get("api_key")
        timeout = config.get("timeout_seconds", 10)
        
        if not api_key:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "manager_type": "sabnzbd",
                "error": "API key is required for SABnzbd"
            }
        
        try:
            # Get queue
            queue_response = requests.get(
                f"{api_url}/api",
                params={"mode": "queue", "apikey": api_key, "output": "json"},
                timeout=timeout
            )
            queue_response.raise_for_status()
            queue_data = queue_response.json()
            
            queue = queue_data.get("queue", {})
            slots = queue.get("slots", [])
            
            # Calculate stats
            downloading = [s for s in slots if s.get("status") == "Downloading"]
            paused = [s for s in slots if s.get("status") == "Paused"]
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "manager_type": "sabnzbd",
                "api_url": api_url,
                "summary": {
                    "total_jobs": len(slots),
                    "downloading": len(downloading),
                    "paused": len(paused),
                    "download_speed_bytes": queue.get("kbpersec", 0) * 1024,
                    "queue_size_mb": round(queue.get("mbleft", 0), 2),
                    "disk_space_gb": round(queue.get("diskspace1", 0), 2),
                    "state": queue.get("status", "unknown")
                },
                "jobs": [{
                    "filename": s.get("filename"),
                    "status": s.get("status"),
                    "progress": round(s.get("percentage", 0), 1),
                    "size_mb": round(s.get("mb", 0), 2),
                    "remaining_mb": round(s.get("mbleft", 0), 2),
                    "eta": s.get("timeleft")
                } for s in slots[:10]]
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "manager_type": "sabnzbd",
                "error": f"Failed to connect to SABnzbd: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "manager_type": "sabnzbd",
                "error": str(e),
                "api_url": api_url
            }
    
    async def health_check(self) -> bool:
        """Check if download manager is accessible"""
        
        config = self.config or {}
        api_url = config.get("api_url")
        
        if not api_url:
            return False
        
        try:
            response = requests.get(api_url, timeout=5)
            return response.status_code in [200, 401, 403, 409]
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        
        if not config:
            return False
        
        manager_type = config.get("manager_type")
        if manager_type not in ["qbittorrent", "transmission", "sabnzbd"]:
            return False
        
        api_url = config.get("api_url")
        if not api_url:
            return False
        
        # SABnzbd requires API key
        if manager_type == "sabnzbd" and not config.get("api_key"):
            return False
        
        return True
