"""
Intent Parser

Uses AI to parse natural language deployment commands into structured intents.
"""

import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class IntentParser:
    """
    Parses natural language deployment commands using AI and pattern matching.

    Examples:
    - "install authentik" -> {action: "install", application: "authentik", platform: "kubernetes"}
    - "deploy postgres with 3 replicas" -> {action: "install", application: "postgresql", parameters: {replicas: 3}}
    - "scale grafana to 5 instances" -> {action: "scale", application: "grafana", parameters: {replicas: 5}}
    """

    def __init__(self):
        self.logger = logger

    async def parse_command(self, command_text: str) -> Dict[str, Any]:
        """
        Parse natural language command into structured intent.

        Args:
            command_text: Natural language command

        Returns:
            Dict with parsed intent:
            {
                "success": bool,
                "action": str,  # install, update, remove, scale
                "application": str,
                "platform": str,  # kubernetes, docker
                "namespace": str,
                "parameters": dict,
                "raw_command": str
            }
        """
        try:
            command_lower = command_text.lower().strip()

            # Determine action
            action = self._extract_action(command_lower)
            
            # Determine application
            application = self._extract_application(command_lower)
            
            # Determine platform
            platform = self._extract_platform(command_lower)
            
            # Extract parameters
            parameters = self._extract_parameters(command_lower)
            
            # Extract namespace
            namespace = self._extract_namespace(command_lower, parameters)

            if not application:
                return {
                    "success": False,
                    "error": "Could not determine application from command",
                    "raw_command": command_text
                }

            return {
                "success": True,
                "action": action,
                "application": application,
                "platform": platform,
                "namespace": namespace,
                "parameters": parameters,
                "raw_command": command_text
            }

        except Exception as e:
            self.logger.error(f"Failed to parse command: {e}")
            return {
                "success": False,
                "error": str(e),
                "raw_command": command_text
            }

    def _extract_action(self, command: str) -> str:
        """Extract action from command."""
        if any(word in command for word in ["install", "deploy", "setup", "create", "add"]):
            return "install"
        elif any(word in command for word in ["update", "upgrade", "modify"]):
            return "update"
        elif any(word in command for word in ["remove", "delete", "uninstall", "destroy"]):
            return "remove"
        elif any(word in command for word in ["scale"]):
            return "scale"
        else:
            return "install"  # Default action

    def _extract_application(self, command: str) -> Optional[str]:
        """Extract application name from command."""
        # List of known applications
        known_apps = [
            "authentik", "postgresql", "postgres", "redis", "grafana", 
            "prometheus", "nginx", "traefik", "mysql", "mongodb",
            "nextcloud", "wordpress", "jellyfin", "plex", "sonarr",
            "radarr", "lidarr", "bazarr", "prowlarr", "overseerr",
            "homeassistant", "home-assistant", "adguard", "pihole"
        ]

        # Check for known applications
        for app in known_apps:
            if app in command:
                # Normalize some app names
                if app == "postgres":
                    return "postgresql"
                elif app == "home-assistant":
                    return "homeassistant"
                return app

        # Try to extract from patterns like "install X" or "deploy X"
        patterns = [
            r"(?:install|deploy|setup|create)\s+([a-z0-9-]+)",
            r"([a-z0-9-]+)\s+(?:instance|deployment|service|app|application)"
        ]

        for pattern in patterns:
            match = re.search(pattern, command)
            if match:
                return match.group(1)

        return None

    def _extract_platform(self, command: str) -> str:
        """Extract target platform from command."""
        if any(word in command for word in ["kubernetes", "k8s", "k3s", "cluster"]):
            return "kubernetes"
        elif any(word in command for word in ["docker", "compose", "container"]):
            return "docker"
        else:
            return "kubernetes"  # Default platform

    def _extract_parameters(self, command: str) -> Dict[str, Any]:
        """Extract parameters from command."""
        parameters = {}

        # Extract replicas/instances
        replica_match = re.search(r"(\d+)\s+(?:replicas?|instances?|copies)", command)
        if replica_match:
            parameters["replicas"] = int(replica_match.group(1))

        # Extract domain
        domain_match = re.search(r"(?:domain|host|hostname)\s+([a-z0-9.-]+)", command)
        if domain_match:
            parameters["domain"] = domain_match.group(1)

        # Extract storage size
        storage_match = re.search(r"(\d+)\s*(gb|gi|gib|mb|mi|mib)", command)
        if storage_match:
            size = storage_match.group(1)
            unit = storage_match.group(2).upper()
            parameters["storage_size"] = f"{size}{unit}"

        # Extract port
        port_match = re.search(r"port\s+(\d+)", command)
        if port_match:
            parameters["port"] = int(port_match.group(1))

        # Extract with TLS/SSL
        if any(word in command for word in ["tls", "ssl", "https", "cert-manager"]):
            parameters["tls_enabled"] = True

        # Extract with ingress
        if "ingress" in command:
            parameters["ingress_enabled"] = True

        # Extract with database
        if any(word in command for word in ["with database", "with db", "with postgres", "with mysql"]):
            parameters["database_enabled"] = True
            if "postgres" in command:
                parameters["database_type"] = "postgresql"
            elif "mysql" in command:
                parameters["database_type"] = "mysql"

        # Extract with cache/redis
        if any(word in command for word in ["with cache", "with redis"]):
            parameters["cache_enabled"] = True

        return parameters

    def _extract_namespace(self, command: str, parameters: Dict[str, Any]) -> str:
        """Extract namespace from command."""
        # Check explicit namespace
        namespace_match = re.search(r"namespace\s+([a-z0-9-]+)", command)
        if namespace_match:
            return namespace_match.group(1)

        # Check in parameters
        if "namespace" in parameters:
            return parameters["namespace"]

        return "default"
