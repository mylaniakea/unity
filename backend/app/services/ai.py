from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.services.ai_provider import AIOrchestrator
from app.services.system_info import SystemInfoService
from typing import List, Dict, Any
import json # Added import for json.dumps

class AIService:
    
    def __init__(self, db: Session):
        settings = db.query(models.Settings).first()
        if not settings:
            # Fallback defaults if no DB settings yet
            self.orchestrator = AIOrchestrator({"providers": {"ollama": {"url": "http://host.docker.internal:11434", "enabled": True}}})
        else:
            # Pydantic model dump or simple dict conversion
            settings_dict = {
                "providers": settings.providers,
                "primary_provider": settings.primary_provider,
                "fallback_provider": settings.fallback_provider,
                "active_model": settings.active_model
            }
            self.orchestrator = AIOrchestrator(settings_dict)

    async def _build_system_prompt(self, db: Session, system_context: Dict[str, Any] = None) -> str:
        # 1. Fetch dynamic settings
        settings = db.query(models.Settings).first()
        base_prompt = settings.system_prompt if settings else "You are a helpful homelab assistant."
        
        # 2. Fetch Knowledge Context
        knowledge_items = db.query(models.KnowledgeItem).filter(models.KnowledgeItem.category != 'homelab').all()
        knowledge_context = "\n".join([f"- {k.title} ({k.category}): {k.content}" for k in knowledge_items])
        
        # 2b. Fetch Homelab Specific Context (Infrastructure)
        homelab_items = db.query(models.KnowledgeItem).filter(models.KnowledgeItem.category == 'homelab').all()
        homelab_context = "\n".join([f"{k.title}: {k.content}" for k in homelab_items])
        
        # 3. Fetch Fleet Context (Server Profiles)
        profiles = db.query(models.ServerProfile).all()
        fleet_context = "\n".join([f"- {p.name} ({p.ip_address}): {p.description or 'No description'} [OS: {p.os_info.get('system', 'Unknown')}]" for p in profiles])

        # 4. Determine Target Telemetry
        if not system_context:
            # Fallback to local
            system_context = {
                "os": SystemInfoService.get_os_info(),
                "hardware": SystemInfoService.get_hardware_info()
            }

        # Safe parsing for varying structures
        hostname = system_context.get('os', {}).get('hostname', 'Unknown Host')
        os_sys = system_context.get('os', {}).get('system', 'Unknown OS')
        
        cpu_pct = 'N/A'
        mem_pct = 'N/A'
        
        if 'hardware' in system_context:
            hw = system_context['hardware']
            if 'cpu' in hw and 'usage_percent' in hw['cpu']:
                cpu_pct = hw['cpu']['usage_percent']
            if 'memory' in hw and 'percent' in hw['memory']:
                mem_pct = hw['memory']['percent']

        return f"""
        {base_prompt}

        [Local Knowledge Base]
        {knowledge_context if knowledge_items else "No specific knowledge items available."}

        [Homelab Environment / Infrastructure]
        {homelab_context if homelab_items else "No manual infrastructure details defined."}

        [Fleet Overview - Other Servers]
        {fleet_context if profiles else "No other servers tracked in profiles."}

        [Active Context / Target Server]
        Host: {hostname}
        OS: {os_sys}
        Stats: CPU {cpu_pct}% | Mem {mem_pct}%
        
        Full Context Data:
        {json.dumps(system_context, indent=2)}
        """

    async def chat(self, messages: List[Dict[str, str]], db: Session, system_context: Dict[str, Any] = None) -> str:
        system_prompt = await self._build_system_prompt(db, system_context)
        
        # Prepend system prompt
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            # Use the active_model from orchestrator settings if not explicitly provided
            return await self.orchestrator.chat(full_messages, model=self.orchestrator.settings.get("active_model"))
        except Exception as e:
            print(f"Chat failed: {e}")
            return "I apologize, but I encountered an error connecting to the intelligence provider."

    async def generate_response(self, prompt: str, system_info: Dict[str, Any], db: Session) -> str:
        # Wrapper for simple generation using chat
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, db)

    async def generate_summary(self, system_info: Dict[str, Any], model: str = None, db: Session = None) -> str:
        prompt = f"""
        Analyze the following server system information and provide a concise summary report. 
        Highlight any potential issues (high usage, low disk space) and give a general health assessment.
        
        System Info:
        {json.dumps(system_info, indent=2)}
        """
        
        # We can skip the full context for this specific task to save tokens/noise
        messages = [
            {"role": "system", "content": "You are an expert Linux System Administrator."},
            {"role": "user", "content": prompt}
        ]
        
        try:
             return await self.orchestrator.chat(messages, model=model)
        except Exception as e:
            return f"Error generating summary: {e}"
