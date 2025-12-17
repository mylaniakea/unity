from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app import models
from app.schemas.core import *
from app.services.core.system_info import SystemInfoService
from app.services.core.ssh import SSHService
from app.services.core.snapshot_service import SnapshotService

router = APIRouter(
    prefix="/profiles",
    tags=["profiles"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=ServerProfile)
def create_profile(profile: ServerProfileCreate, db: Session = Depends(get_db)):
    db_profile = models.ServerProfile(**profile.model_dump())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

@router.get("/", response_model=List[ServerProfile])
def read_profiles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    profiles = db.query(models.ServerProfile).offset(skip).limit(limit).all()
    return profiles

@router.get("/{profile_id}", response_model=ServerProfile)
def read_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == profile_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.delete("/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == profile_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(profile)
    db.commit()
    return {"ok": True}

@router.put("/{profile_id}", response_model=ServerProfile)
def update_profile(profile_id: int, profile_data: ServerProfileUpdate, db: Session = Depends(get_db)):
    db_profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == profile_id).first()
    if db_profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_data = profile_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_profile, key, value)
    
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

@router.post("/{profile_id}/ssh/test")
async def test_ssh_connection(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    ssh_service = SSHService(profile)
    result = await ssh_service.verify_connection()
    return result

@router.post("/{profile_id}/refresh", response_model=ServerProfile)
async def refresh_profile_stats(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # If it's a local profile created via scan-local, maybe just run local system info?
    # For now, we enforce SSH if they hit this endpoint, unless we want a specific 'local' refresh logic.
    # Let's try SSH first.
    
    ssh_service = SSHService(profile)
    try:
        stats = await ssh_service.get_system_info()
        
        # Update profile fields
        # Note: SQLAlchemy requires re-assigning the JSON field to detect change if it's mutable, 
        # or we just assign the new dict.
        if "os" in stats:
            profile.os_info = stats["os"]
        if "hardware" in stats:
            profile.hardware_info = stats["hardware"]
        
        db.add(profile) # Mark as modified
        db.commit()
        db.refresh(profile)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH Refresh Failed: {str(e)}")

from pydantic import BaseModel

class PasswordRequest(BaseModel):
    password: str

@router.post("/{profile_id}/setup-keys")
async def setup_ssh_keys(profile_id: int, request: PasswordRequest, db: Session = Depends(get_db)):
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    ssh_service = SSHService(profile)
    try:
        key_path = await ssh_service.setup_keys(request.password)
        
        # Update profile with the new key path
        profile.ssh_key_path = key_path
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
        return {"success": True, "key_path": key_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Key Setup Failed: {str(e)}")

@router.post("/{profile_id}/scan-hardware", response_model=ServerProfile)
async def scan_hardware_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    ssh_service = SSHService(profile)
    try:
        detailed_info = await ssh_service.get_extended_hardware_info()
        
        # Merge into existing hardware_info or create new
        current_info = dict(profile.hardware_info) if profile.hardware_info else {}
        current_info['detailed'] = detailed_info
        
        # Explicit reassignment for SQLAlchemy tracking
        profile.hardware_info = current_info
        
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hardware Scan Failed: {str(e)}")

@router.post("/scan-local", response_model=ServerProfile)
def create_profile_from_local(db: Session = Depends(get_db)):
    """Auto-generate a profile from the current server's stats"""
    hardware = SystemInfoService.get_hardware_info()
    os_info = SystemInfoService.get_os_info()
    # TODO: Get packages
    
    profile_data = ServerProfileCreate(
        name=os_info.get("hostname", "Local Server"),
        description="Auto-generated from local system",
        ip_address="127.0.0.1", # Placeholder
        hardware_info=hardware,
        os_info=os_info,
        packages=[] 
    )
    
    db_profile = models.ServerProfile(**profile_data.model_dump())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

@router.post("/{profile_id}/snapshot")
async def take_snapshot(profile_id: int, db: Session = Depends(get_db)):
    """Manually trigger a snapshot for a server profile (including plugin data)."""
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    snapshot = await SnapshotService.take_remote_snapshot(db, profile)
    if snapshot:
        return {
            "success": True,
            "snapshot_id": snapshot.id,
            "timestamp": snapshot.timestamp.isoformat(),
            "plugins_collected": list(snapshot.data.get("plugins", {}).keys())
        }
    else:
        raise HTTPException(status_code=500, detail="Snapshot failed")
