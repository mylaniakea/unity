from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.services.ai import AIService
from app.services.system_info import SystemInfoService
from app.services.ssh import SSHService
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import json
from datetime import datetime

from app.services.ai_provider import AIOrchestrator # Import AIOrchestrator
from app.routers.settings import get_settings # Import get_settings
from app.schemas.core import Settings, SettingsUpdate # Import schemas_settings

router = APIRouter(
    prefix="/ai",
    tags=["ai"],
    responses={404: {"description": "Not found"}},
)

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    # Model optional, overrides global setting if provided
    model: Optional[str] = None
    profile_id: Optional[int] = None

class SummaryRequest(BaseModel):
    model: Optional[str] = None
    profile_id: Optional[int] = None

class KnowledgeIngestRequest(BaseModel):
    profile_id: int
    hardware_data: Dict[str, Any]

@router.post("/chat")
async def chat_with_ai(request: ChatRequest, db: Session = Depends(get_db)):
    service = AIService(db)
    
    # Context injection for specific profile if selected
    system_context = None
    if request.profile_id:
        profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == request.profile_id).first()
        if profile:
            # We try to get live data, or fall back to cached data in profile
            try:
                ssh_service = SSHService(profile)
                system_context = await ssh_service.get_system_info()
            except Exception:
                # Fallback to cached info if SSH fails or just use profile metadata
                system_context = {
                    "name": profile.name,
                    "ip": profile.ip_address,
                    "os": profile.os_info,
                    "hardware": profile.hardware_info,
                    "note": "Live connection failed, using cached data."
                }

    response = await service.chat(request.messages, db, system_context=system_context)
    return {"response": response}

@router.get("/models")
async def get_ai_models(db: Session = Depends(get_db)):
    settings_obj = get_settings(db) # Get settings from the database (SQLAlchemy model)
    # Convert to Pydantic model to ensure we have a clean dict structure
    settings_schema = SettingsSettings.model_validate(settings_obj)
    orchestrator = AIOrchestrator(settings_schema.model_dump()) # Initialize orchestrator with dict
    all_models = await orchestrator.get_all_provider_models()
    return {"models": all_models}

@router.post("/ingest-hardware-knowledge")
async def ingest_hardware_knowledge(request: KnowledgeIngestRequest, db: Session = Depends(get_db)):
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == request.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    service = AIService(db)
    
    # Prompt for AI to format the data
    prompt = f"""
    You are a technical documentation assistant. 
    Convert the following raw hardware JSON data for server '{profile.name}' into a structured, readable Knowledge Base entry (Markdown).
    
    Focus on:
    - GPU/Accelerators (Models, quantities)
    - Storage (Disks, Capacities, Models, RAID status)
    - Network Interfaces (Physical links, speeds if known)
    - Key PCI devices
    
    Do not include raw JSON in the output. Use headers, bullet points, and tables.
    
    Raw Data:
    {json.dumps(request.hardware_data, indent=2)}
    """
    
    messages = [{"role": "user", "content": prompt}]
    formatted_content = await service.orchestrator.chat(messages)
    
    # Create Knowledge Item
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    title = f"{profile.name} Hardware Spec {date_str}"
    
    knowledge_item = models.KnowledgeItem(
        title=title,
        content=formatted_content,
        category="hardware",
        tags=[f"server_id:{profile.id}", f"server_name:{profile.name}"]
    )
    
    db.add(knowledge_item)
    db.commit()
    
    return {"status": "success", "title": title}

@router.post("/generate-summary")
async def generate_system_summary(request: SummaryRequest, db: Session = Depends(get_db)):
    # Determine source of truth
    system_info = {}
    
    if request.profile_id:
        profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == request.profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        # Try to get remote info via SSH
        try:
            ssh_service = SSHService(profile)
            system_info = await ssh_service.get_system_info()
            # Enrich with profile metadata
            system_info['profile_name'] = profile.name
            system_info['ip_address'] = profile.ip_address
        except Exception as e:
            # Fallback to cached
            system_info = {
                "hardware": profile.hardware_info,
                "os": profile.os_info,
                "error": f"Live fetch failed: {str(e)}"
            }
    else:
        # Local Host
        system_info = {
            "hardware": SystemInfoService.get_hardware_info(),
            "os": SystemInfoService.get_os_info(),
            "network": SystemInfoService.get_network_info()
        }
    
    service = AIService(db)
    summary = await service.generate_summary(system_info, db=db)
    return {"summary": summary, "system_info": system_info}
