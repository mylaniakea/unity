"""
Intent Parser - Parses natural language requests using Ollama or other LLM.
"""
import json
import logging
from typing import Dict, List, Any, Optional
from app.services.ai.ai_provider import AIOrchestrator

logger = logging.getLogger(__name__)


class IntentParser:
    """Parses deployment requests in natural language."""
    
    def __init__(self, ai_orchestrator: AIOrchestrator):
        """Initialize with AI orchestrator."""
        self.orchestrator = ai_orchestrator
    
    async def parse(self, request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parse a natural language deployment request.
        
        Args:
            request: User's natural language request (e.g., "Add Authentik")
            context: Optional context about cluster state
        
        Returns:
            Dict with parsed intent containing app, dependencies, config
        """
        context = context or {}
        
        # Build prompt for LLM
        prompt = self._build_prompt(request, context)
        
        # Get response from AI
        try:
            model = self.orchestrator.active_model
            response = await self.orchestrator.chat(
                [{"role": "user", "content": prompt}],
                model
            )
            
            # Parse JSON response
            intent = self._extract_json(response)
            return intent
        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            # Fallback to simple parsing
            return self._fallback_parse(request)
    
    def _build_prompt(self, request: str, context: Dict[str, Any]) -> str:
        """Build prompt for LLM to parse intent."""
        available_apps = json.dumps([
            "authentik", "postgresql", "nginx", "nextcloud", 
            "jellyfin", "plex", "minecraft", "wireguard",
            "openvpn", "mysql", "redis", "mongodb"
        ])
        
        prompt = f"""You are an infrastructure deployment assistant. 
Parse the user's request and extract deployment intent.

User Request: {request}

Cluster Context:
- Available storage: {context.get('storage_available', '100Gi')}
- Available CPU: {context.get('cpu_available', '8')}
- Available memory: {context.get('memory_available', '16Gi')}

Available applications: {available_apps}

Extract and respond with ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "app": "application_name",
  "dependencies": ["dependency1", "dependency2"],
  "namespace": "homelab",
  "config": {{"key": "value"}},
  "storage_gb": 20,
  "cpu_request": "500m",
  "memory_request": "512Mi",
  "expose": true,
  "domain": "app.local"
}}

Be strict: only return JSON, nothing else."""
        
        return prompt
    
    def _extract_json(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        # Try to find JSON in response
        try:
            # Clean response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```"):
                response = response[response.find("{"): response.rfind("}")+1]
            
            # Parse JSON
            intent = json.loads(response)
            return intent
        except Exception as e:
            logger.error(f"Error extracting JSON: {e}, response: {response}")
            return {}
    
    def _fallback_parse(self, request: str) -> Dict[str, Any]:
        """Fallback parsing when AI fails."""
        request_lower = request.lower()
        
        # Simple pattern matching
        intent = {
            "app": None,
            "dependencies": [],
            "namespace": "homelab",
            "config": {},
            "storage_gb": 20,
            "cpu_request": "500m",
            "memory_request": "512Mi",
            "expose": True,
            "domain": None
        }
        
        # Detect main app
        apps = {
            "authentik": "authentik",
            "nextcloud": "nextcloud",
            "jellyfin": "jellyfin",
            "plex": "plex",
            "postgres": "postgresql",
            "mysql": "mysql",
            "mongo": "mongodb",
            "redis": "redis"
        }
        
        for keyword, app_name in apps.items():
            if keyword in request_lower:
                intent["app"] = app_name
                intent["domain"] = f"{app_name}.local"
                break
        
        # Detect dependencies
        if "database" in request_lower or "postgres" in request_lower or "db" in request_lower:
            if intent["app"] != "postgresql":
                intent["dependencies"].append("postgresql")
        
        if "proxy" in request_lower or "nginx" in request_lower or "reverse" in request_lower:
            if intent["app"] != "nginx":
                intent["dependencies"].append("nginx")
        
        return intent if intent["app"] else {"error": "Could not parse application name"}
