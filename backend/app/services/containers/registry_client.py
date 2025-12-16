import httpx
from typing import Optional, Dict, List, Any
import logging
import re

logger = logging.getLogger(__name__)


class RegistryClient:
    """Client for querying container image registries"""
    
    def __init__(self):
        self.timeout = httpx.Timeout(10.0)
    
    def parse_image_name(self, image: str) -> Dict[str, str]:
        """Parse an image name into registry, repository, and tag components"""
        # Default values
        registry = "docker.io"
        repository = image
        tag = "latest"
        
        # Split tag if present
        if ":" in image:
            repository, tag = image.rsplit(":", 1)
        
        # Check for registry in repository
        if "/" in repository:
            parts = repository.split("/")
            # If first part contains a dot or is 'localhost', it's a registry
            if "." in parts[0] or parts[0] == "localhost" or ":" in parts[0]:
                registry = parts[0]
                repository = "/".join(parts[1:])
        
        # Normalize Docker Hub official images (e.g., "postgres" -> "library/postgres")
        if registry == "docker.io" and "/" not in repository:
            repository = f"library/{repository}"
        
        return {
            "registry": registry,
            "repository": repository,
            "tag": tag,
            "full_name": f"{registry}/{repository}:{tag}"
        }
    
    async def get_latest_digest(self, image: str, tag: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the latest digest for an image tag from the registry"""
        parsed = self.parse_image_name(image)
        target_tag = tag if tag else parsed["tag"]
        
        try:
            if parsed["registry"] == "docker.io":
                return await self._get_dockerhub_digest(parsed["repository"], target_tag)
            elif parsed["registry"] == "ghcr.io":
                return await self._get_ghcr_digest(parsed["repository"], target_tag)
            elif parsed["registry"] == "gcr.io":
                return await self._get_gcr_digest(parsed["repository"], target_tag)
            else:
                # Try generic Docker Registry V2 API
                return await self._get_generic_registry_digest(
                    parsed["registry"], parsed["repository"], target_tag
                )
        except Exception as e:
            logger.error(f"Failed to get digest for {image}:{target_tag}: {e}")
            return None
    
    async def _get_dockerhub_digest(self, repository: str, tag: str) -> Optional[Dict[str, Any]]:
        """Get digest from Docker Hub"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # First, get auth token
                auth_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repository}:pull"
                auth_response = await client.get(auth_url)
                auth_response.raise_for_status()
                token = auth_response.json()["token"]
                
                # Get manifest with digest
                manifest_url = f"https://registry-1.docker.io/v2/{repository}/manifests/{tag}"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
                }
                
                manifest_response = await client.get(manifest_url, headers=headers)
                manifest_response.raise_for_status()
                
                digest = manifest_response.headers.get("Docker-Content-Digest")
                manifest = manifest_response.json()
                
                return {
                    "digest": digest,
                    "tag": tag,
                    "registry": "docker.io",
                    "repository": repository,
                    "manifest": manifest,
                    "config_digest": manifest.get("config", {}).get("digest")
                }
        except Exception as e:
            logger.error(f"Docker Hub API error for {repository}:{tag}: {e}")
            return None
    
    async def _get_ghcr_digest(self, repository: str, tag: str) -> Optional[Dict[str, Any]]:
        """Get digest from GitHub Container Registry"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                manifest_url = f"https://ghcr.io/v2/{repository}/manifests/{tag}"
                headers = {
                    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
                }
                
                manifest_response = await client.get(manifest_url, headers=headers)
                manifest_response.raise_for_status()
                
                digest = manifest_response.headers.get("Docker-Content-Digest")
                manifest = manifest_response.json()
                
                return {
                    "digest": digest,
                    "tag": tag,
                    "registry": "ghcr.io",
                    "repository": repository,
                    "manifest": manifest
                }
        except Exception as e:
            logger.error(f"GHCR API error for {repository}:{tag}: {e}")
            return None
    
    async def _get_gcr_digest(self, repository: str, tag: str) -> Optional[Dict[str, Any]]:
        """Get digest from Google Container Registry"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                manifest_url = f"https://gcr.io/v2/{repository}/manifests/{tag}"
                headers = {
                    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
                }
                
                manifest_response = await client.get(manifest_url, headers=headers)
                manifest_response.raise_for_status()
                
                digest = manifest_response.headers.get("Docker-Content-Digest")
                manifest = manifest_response.json()
                
                return {
                    "digest": digest,
                    "tag": tag,
                    "registry": "gcr.io",
                    "repository": repository,
                    "manifest": manifest
                }
        except Exception as e:
            logger.error(f"GCR API error for {repository}:{tag}: {e}")
            return None
    
    async def _get_generic_registry_digest(
        self, registry: str, repository: str, tag: str
    ) -> Optional[Dict[str, Any]]:
        """Get digest from a generic Docker Registry V2 API"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                manifest_url = f"https://{registry}/v2/{repository}/manifests/{tag}"
                headers = {
                    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
                }
                
                manifest_response = await client.get(manifest_url, headers=headers)
                manifest_response.raise_for_status()
                
                digest = manifest_response.headers.get("Docker-Content-Digest")
                manifest = manifest_response.json()
                
                return {
                    "digest": digest,
                    "tag": tag,
                    "registry": registry,
                    "repository": repository,
                    "manifest": manifest
                }
        except Exception as e:
            logger.error(f"Generic registry API error for {registry}/{repository}:{tag}: {e}")
            return None
    
    async def list_tags(self, image: str, limit: int = 10) -> Optional[List[str]]:
        """List available tags for an image"""
        parsed = self.parse_image_name(image)
        
        try:
            if parsed["registry"] == "docker.io":
                return await self._list_dockerhub_tags(parsed["repository"], limit)
            else:
                return await self._list_generic_registry_tags(
                    parsed["registry"], parsed["repository"], limit
                )
        except Exception as e:
            logger.error(f"Failed to list tags for {image}: {e}")
            return None
    
    async def _list_dockerhub_tags(self, repository: str, limit: int) -> Optional[List[str]]:
        """List tags from Docker Hub"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Use Docker Hub API v2
                url = f"https://hub.docker.com/v2/repositories/{repository}/tags?page_size={limit}"
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                tags = [result["name"] for result in data.get("results", [])]
                return tags
        except Exception as e:
            logger.error(f"Docker Hub tags API error for {repository}: {e}")
            return None
    
    async def _list_generic_registry_tags(
        self, registry: str, repository: str, limit: int
    ) -> Optional[List[str]]:
        """List tags from a generic Docker Registry V2 API"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"https://{registry}/v2/{repository}/tags/list"
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                tags = data.get("tags", [])[:limit]
                return tags
        except Exception as e:
            logger.error(f"Generic registry tags API error for {registry}/{repository}: {e}")
            return None
