from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
import os
import logging
import app.models as models
from app.services.containers.ai.anthropic_provider import AnthropicProvider
from app.services.containers.ai.openai_provider import OpenAIProvider
from app.services.containers.ai.ollama_provider import OllamaProvider
from app.services.containers.ai.google_provider import GoogleProvider

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Service for AI-powered container analysis"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _get_provider(self, use_fallback: bool = False):
        """Get the configured AI provider"""
        settings = self.db.query(models.Settings).first()
        
        if not settings:
            raise ValueError("Settings not found. Please configure AI provider settings.")
        
        # Get provider from settings or environment
        active_provider = settings.fallback_provider if use_fallback else settings.primary_provider
        
        if not active_provider:
            raise ValueError(f"{'Fallback' if use_fallback else 'Primary'} provider not configured")
        
        if active_provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY") or settings.providers.get("anthropic", {}).get("api_key")
            if not api_key:
                raise ValueError("Anthropic API key not configured")
            return AnthropicProvider(api_key=api_key, model=settings.active_model)
        
        elif active_provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY") or settings.providers.get("openai", {}).get("api_key")
            if not api_key:
                raise ValueError("OpenAI API key not configured")
            return OpenAIProvider(api_key=api_key, model=settings.active_model)
        
        elif active_provider == "ollama":
            base_url = os.environ.get("OLLAMA_BASE_URL") or settings.providers.get("ollama", {}).get("url", "http://host.docker.internal:11434")
            return OllamaProvider(model=settings.active_model, base_url=base_url)
        
        elif active_provider == "google":
            api_key = os.environ.get("GOOGLE_API_KEY") or settings.providers.get("google", {}).get("api_key")
            if not api_key:
                raise ValueError("Google API key not configured")
            return GoogleProvider(api_key=api_key, model=settings.active_model)
        
        else:
            raise ValueError(f"Unknown or unconfigured AI provider: {active_provider}")
    
    async def analyze_container(self, container_id: int) -> Dict[str, Any]:
        """Analyze a specific container with AI"""
        container = self.db.query(models.Container).filter(
            models.Container.id == container_id
        ).first()
        
        if not container:
            raise ValueError(f"Container with ID {container_id} not found")
        
        # Get latest update check
        latest_check = self.db.query(models.UpdateCheck).filter(
            models.UpdateCheck.container_id == container_id
        ).order_by(models.UpdateCheck.checked_at.desc()).first()
        
        # Prepare container data
        container_data = {
            "id": container.id,
            "name": container.name,
            "image": container.image,
            "current_tag": container.current_tag,
            "status": container.status,
            "labels": container.labels,
            "environment": container.environment,
            "ports": container.ports,
            "volumes": container.volumes,
            "networks": container.networks
        }
        
        update_info = None
        if latest_check:
            update_info = {
                "update_available": latest_check.update_available,
                "current_digest": latest_check.current_digest,
                "available_digest": latest_check.available_digest,
                "checked_at": latest_check.checked_at.isoformat() if latest_check.checked_at else None
            }
        
        # Try primary provider first, fallback to secondary on error
        provider = None
        analysis = None
        
        try:
            provider = self._get_provider(use_fallback=False)
            logger.info(f"Analyzing container {container.name} with primary provider: {provider.get_model_info()['provider']}")
            analysis = await provider.analyze_container(container_data, update_info)
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}")
            try:
                provider = self._get_provider(use_fallback=True)
                logger.info(f"Trying fallback provider: {provider.get_model_info()['provider']}")
                analysis = await provider.analyze_container(container_data, update_info)
            except Exception as fallback_error:
                logger.error(f"Fallback provider also failed: {fallback_error}")
                raise ValueError(f"Both primary and fallback providers failed. Primary: {e}, Fallback: {fallback_error}")
        
        # Store recommendation in database
        recommendation = models.AIRecommendation(
            container_id=container.id,
            recommendation_type=analysis.get("recommendation_type", "review"),
            severity=analysis.get("risk_level", "MEDIUM").lower(),
            title=analysis.get("title", "Container Analysis"),
            summary=analysis.get("summary", ""),
            detailed_analysis=analysis.get("detailed_analysis", ""),
            current_version=container.current_tag,
            target_version=container.available_tag,
            risk_level=analysis.get("risk_level", "MEDIUM"),
            breaking_changes=analysis.get("breaking_changes", False),
            dependencies_affected=analysis.get("dependencies_affected", []),
            ai_provider=analysis.get("provider", "unknown"),
            ai_model=analysis.get("model", "unknown"),
            status="pending"
        )
        
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)
        
        return {
            "recommendation_id": recommendation.id,
            "container_id": container.id,
            "container_name": container.name,
            **analysis
        }
    
    async def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """General purpose chat with AI"""
        # Build context if provided
        context_text = ""
        if context:
            if "containers" in context:
                context_text += f"Container Count: {context['containers']}\n"
            if "hosts" in context:
                context_text += f"Docker Hosts: {context['hosts']}\n"
        
        full_message = f"{context_text}\n{message}" if context_text else message
        messages = [{"role": "user", "content": full_message}]
        system_prompt = "You are Uptainer AI, an expert assistant for Docker container management and updates. Provide helpful, accurate advice."
        
        # Try primary provider first, fallback to secondary on error
        try:
            provider = self._get_provider(use_fallback=False)
            logger.info(f"Chat with primary provider: {provider.get_model_info()['provider']}")
            response = await provider.chat(messages, system_prompt=system_prompt)
            model_info = provider.get_model_info()
            return {
                "response": response,
                "provider": model_info["provider"],
                "model": model_info["model"]
            }
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}")
            try:
                provider = self._get_provider(use_fallback=True)
                logger.info(f"Trying fallback provider: {provider.get_model_info()['provider']}")
                response = await provider.chat(messages, system_prompt=system_prompt)
                model_info = provider.get_model_info()
                return {
                    "response": response,
                    "provider": model_info["provider"],
                    "model": model_info["model"]
                }
            except Exception as fallback_error:
                logger.error(f"Fallback provider also failed: {fallback_error}")
                raise ValueError(f"Both primary and fallback providers failed. Primary: {e}, Fallback: {fallback_error}")
    
    async def analyze_vulnerability_scan(
        self, 
        scan_id: int,
        use_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze a vulnerability scan using AI to provide plain-language insights.
        
        Args:
            scan_id: VulnerabilityScan database ID
            use_fallback: Whether to try fallback provider on error
        
        Returns:
            Dict with security analysis results
        """
        from app.models.containers import VulnerabilityScan
        
        # Load scan from database
        scan = self.db.query(VulnerabilityScan).filter(
            VulnerabilityScan.id == scan_id
        ).first()
        
        if not scan:
            raise ValueError(f"Vulnerability scan with ID {scan_id} not found")
        
        logger.info(f"Analyzing vulnerability scan {scan_id} for container {scan.container_id}")
        
        # Prepare scan data for AI
        scan_data = {
            "scan_id": scan.id,
            "container_id": scan.container_id,
            "image": scan.image,
            "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
            "security_score": scan.security_score,
            "critical_count": scan.critical_count,
            "high_count": scan.high_count,
            "medium_count": scan.medium_count,
            "low_count": scan.low_count,
            "secrets_found": scan.secrets_found,
            "misconfigurations_found": scan.misconfigurations_found,
            "vulnerabilities": scan.scan_results.get("vulnerabilities", []) if scan.scan_results else []
        }
        
        # Get AI provider
        active_provider = self.settings.ai_provider if self.settings else "anthropic"
        provider = self._get_provider(active_provider)
        
        if not provider:
            raise RuntimeError(f"No AI provider configured for {active_provider}")
        
        # Call AI for security analysis
        try:
            logger.info(f"Using {active_provider} for security analysis")
            analysis = await provider.analyze_security(scan_data)
            
            logger.info(f"Security analysis complete via {active_provider}")
            return {
                "scan_id": scan_id,
                "container_id": scan.container_id,
                "image": scan.image,
                "scan_score": scan.security_score,
                "scanned_at": scan.scanned_at,
                **analysis
            }
            
        except Exception as e:
            logger.error(f"Security analysis failed with {active_provider}: {e}")
            
            # Try fallback provider if enabled
            if use_fallback and self.settings and self.settings.ai_fallback_provider:
                fallback_provider_name = self.settings.ai_fallback_provider
                logger.warning(f"Attempting security analysis with fallback provider: {fallback_provider_name}")
                
                try:
                    fallback_provider = self._get_provider(fallback_provider_name)
                    if fallback_provider:
                        analysis = await fallback_provider.analyze_security(scan_data)
                        logger.info(f"Security analysis succeeded via fallback ({fallback_provider_name})")
                        return {
                            "scan_id": scan_id,
                            "container_id": scan.container_id,
                            "image": scan.image,
                            "scan_score": scan.security_score,
                            "scanned_at": scan.scanned_at,
                            **analysis
                        }
                except Exception as fallback_error:
                    logger.error(f"Fallback security analysis also failed: {fallback_error}")
                    raise RuntimeError(
                        f"Both primary and fallback providers failed. "
                        f"Primary: {e}, Fallback: {fallback_error}"
                    )
            
            raise
