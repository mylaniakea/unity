"""
Git Server Monitor Plugin

Monitors Gitea, Gogs, and GitLab git servers.
Code is precious - git server health is non-negotiable!
"""

import requests
from datetime import datetime, timezone
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class GitServerMonitorPlugin(PluginBase):
    """Monitors Git servers (Gitea, Gogs, GitLab)"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="git-server-monitor",
            name="Git Server Monitor",
            version="1.0.0",
            description="Monitors Gitea, Gogs, and GitLab git servers including repositories, users, and CI/CD pipelines",
            author="Unity Team",
            category=PluginCategory.APPLICATION,
            tags=["git", "gitea", "gogs", "gitlab", "repositories", "ci-cd"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["requests"],
            config_schema={
                "type": "object",
                "properties": {
                    "server_type": {
                        "type": "string",
                        "enum": ["gitea", "gogs", "gitlab"],
                        "description": "Type of git server"
                    },
                    "api_url": {
                        "type": "string",
                        "description": "Git server API URL"
                    },
                    "api_token": {
                        "type": "string",
                        "description": "API access token"
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
        """Collect git server metrics"""
        
        config = self.config or {}
        server_type = config.get("server_type", "").lower()
        
        if server_type == "gitea":
            return self._monitor_gitea(config)
        elif server_type == "gogs":
            return self._monitor_gogs(config)
        elif server_type == "gitlab":
            return self._monitor_gitlab(config)
        else:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Unknown server type: {server_type}",
                "supported_types": ["gitea", "gogs", "gitlab"]
            }
    
    def _monitor_gitea(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor Gitea git server"""
        
        api_url = config.get("api_url", "").rstrip("/")
        api_token = config.get("api_token")
        timeout = config.get("timeout_seconds", 10)
        verify_ssl = config.get("verify_ssl", True)
        
        try:
            headers = {"Authorization": f"token {api_token}"}
            
            # Get repos
            repos_response = requests.get(
                f"{api_url}/api/v1/user/repos",
                headers=headers,
                params={"limit": 100},
                timeout=timeout,
                verify=verify_ssl
            )
            repos_response.raise_for_status()
            repos = repos_response.json()
            
            # Calculate stats
            total_size = sum(r.get("size", 0) for r in repos)
            private_repos = sum(1 for r in repos if r.get("private"))
            public_repos = len(repos) - private_repos
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "gitea",
                "api_url": api_url,
                "summary": {
                    "total_repositories": len(repos),
                    "public_repositories": public_repos,
                    "private_repositories": private_repos,
                    "total_size_kb": total_size
                },
                "repositories": [{
                    "name": r.get("name"),
                    "full_name": r.get("full_name"),
                    "private": r.get("private"),
                    "size_kb": r.get("size"),
                    "stars": r.get("stars_count"),
                    "forks": r.get("forks_count"),
                    "open_issues": r.get("open_issues_count"),
                    "updated_at": r.get("updated_at")
                } for r in repos[:10]]
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "gitea",
                "error": f"Failed to connect to Gitea: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "gitea",
                "error": str(e),
                "api_url": api_url
            }
    
    def _monitor_gogs(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor Gogs git server"""
        
        api_url = config.get("api_url", "").rstrip("/")
        api_token = config.get("api_token")
        timeout = config.get("timeout_seconds", 10)
        verify_ssl = config.get("verify_ssl", True)
        
        try:
            headers = {"Authorization": f"token {api_token}"}
            
            # Get repos
            repos_response = requests.get(
                f"{api_url}/api/v1/user/repos",
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            repos_response.raise_for_status()
            repos = repos_response.json()
            
            # Calculate stats
            private_repos = sum(1 for r in repos if r.get("private"))
            public_repos = len(repos) - private_repos
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "gogs",
                "api_url": api_url,
                "summary": {
                    "total_repositories": len(repos),
                    "public_repositories": public_repos,
                    "private_repositories": private_repos
                },
                "repositories": [{
                    "name": r.get("name"),
                    "full_name": r.get("full_name"),
                    "private": r.get("private"),
                    "stars": r.get("stars_count"),
                    "forks": r.get("forks_count"),
                    "updated_at": r.get("updated_at")
                } for r in repos[:10]]
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "gogs",
                "error": f"Failed to connect to Gogs: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "gogs",
                "error": str(e),
                "api_url": api_url
            }
    
    def _monitor_gitlab(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor GitLab server"""
        
        api_url = config.get("api_url", "").rstrip("/")
        api_token = config.get("api_token")
        timeout = config.get("timeout_seconds", 10)
        verify_ssl = config.get("verify_ssl", True)
        
        try:
            headers = {"PRIVATE-TOKEN": api_token}
            
            # Get projects
            projects_response = requests.get(
                f"{api_url}/api/v4/projects",
                headers=headers,
                params={"membership": True, "per_page": 100},
                timeout=timeout,
                verify=verify_ssl
            )
            projects_response.raise_for_status()
            projects = projects_response.json()
            
            # Calculate stats
            private_projects = sum(1 for p in projects if p.get("visibility") == "private")
            public_projects = sum(1 for p in projects if p.get("visibility") == "public")
            internal_projects = len(projects) - private_projects - public_projects
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "gitlab",
                "api_url": api_url,
                "summary": {
                    "total_projects": len(projects),
                    "public_projects": public_projects,
                    "private_projects": private_projects,
                    "internal_projects": internal_projects
                },
                "projects": [{
                    "name": p.get("name"),
                    "path_with_namespace": p.get("path_with_namespace"),
                    "visibility": p.get("visibility"),
                    "stars": p.get("star_count"),
                    "forks": p.get("forks_count"),
                    "open_issues": p.get("open_issues_count"),
                    "last_activity": p.get("last_activity_at")
                } for p in projects[:10]]
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "gitlab",
                "error": f"Failed to connect to GitLab: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_type": "gitlab",
                "error": str(e),
                "api_url": api_url
            }
    
    async def health_check(self) -> bool:
        """Check if git server is accessible"""
        
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
        if server_type not in ["gitea", "gogs", "gitlab"]:
            return False
        
        api_url = config.get("api_url")
        api_token = config.get("api_token")
        
        return bool(api_url and api_token)
