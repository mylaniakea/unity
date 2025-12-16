"""
Plugins Router - API endpoints for managing data collection plugins.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel

from app.core.database import get_db
from app import models
from app.services.plugins.plugin_registry import PLUGINS, PLUGIN_CATEGORIES, get_all_plugins, get_plugin
from app.services.core.ssh import SSHService

router = APIRouter(
    prefix="/plugins",
    tags=["plugins"],
    responses={404: {"description": "Not found"}},
)


class PluginToggleRequest(BaseModel):
    plugin_id: str
    enabled: bool


class InstallPluginRequest(BaseModel):
    plugin_id: str
    distro: str = "debian"  # debian, rhel, arch


# --- GET ALL AVAILABLE PLUGINS ---
@router.get("/")
def list_plugins():
    """List all available plugins with their definitions."""
    return {
        "plugins": get_all_plugins(),
        "categories": PLUGIN_CATEGORIES
    }


# --- GET PLUGIN BY ID ---
@router.get("/{plugin_id}")
def get_plugin_details(plugin_id: str):
    """Get details for a specific plugin."""
    plugin = get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    return plugin


# --- CHECK PLUGIN AVAILABILITY ON SERVER ---
@router.get("/check/{server_id}")
async def check_plugins_on_server(server_id: int, db: Session = Depends(get_db)):
    """Check which plugins are available (tools installed) on a server."""
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == server_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Server profile not found")
    
    ssh_service = SSHService(profile)
    detected = {}
    
    for plugin_id, plugin in PLUGINS.items():
        check_cmd = plugin.get("check_cmd", "")
        if check_cmd:
            try:
                _, _, exit_code = await ssh_service.execute_command(check_cmd)
                detected[plugin_id] = (exit_code == 0)
            except Exception:
                detected[plugin_id] = False
        else:
            detected[plugin_id] = False
    
    # Update the profile's detected_plugins field
    profile.detected_plugins = detected
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return {
        "server_id": server_id,
        "detected_plugins": detected,
        "enabled_plugins": profile.enabled_plugins or []
    }


# --- TOGGLE PLUGIN FOR SERVER ---
@router.post("/toggle/{server_id}")
def toggle_plugin(server_id: int, request: PluginToggleRequest, db: Session = Depends(get_db)):
    """Enable or disable a plugin for a specific server."""
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == server_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Server profile not found")
    
    plugin = get_plugin(request.plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{request.plugin_id}' not found")
    
    current_plugins = list(profile.enabled_plugins or [])
    
    if request.enabled:
        if request.plugin_id not in current_plugins:
            current_plugins.append(request.plugin_id)
    else:
        if request.plugin_id in current_plugins:
            current_plugins.remove(request.plugin_id)
    
    profile.enabled_plugins = current_plugins
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return {
        "server_id": server_id,
        "enabled_plugins": profile.enabled_plugins
    }


# --- GET SERVER PLUGIN STATUS ---
@router.get("/status/{server_id}")
def get_server_plugin_status(server_id: int, db: Session = Depends(get_db)):
    """Get enabled and detected plugins for a server."""
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == server_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Server profile not found")
    
    return {
        "server_id": server_id,
        "server_name": profile.name,
        "enabled_plugins": profile.enabled_plugins or [],
        "detected_plugins": profile.detected_plugins or {}
    }


# --- INSTALL PLUGIN ON SERVER ---
@router.post("/install/{server_id}")
async def install_plugin(server_id: int, request: InstallPluginRequest, db: Session = Depends(get_db)):
    """Execute install script for a plugin on a server."""
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == server_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Server profile not found")
    
    plugin = get_plugin(request.plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{request.plugin_id}' not found")
    
    install_scripts = plugin.get("install_script", {})
    if not install_scripts:
        raise HTTPException(status_code=400, detail="This plugin does not have an install script")
    
    script = install_scripts.get(request.distro)
    if not script:
        raise HTTPException(status_code=400, detail=f"No install script for distro '{request.distro}'")
    
    # Check if it's just a comment (manual install required)
    if script.startswith("#"):
        return {
            "success": False,
            "manual_required": True,
            "message": script,
            "output": ""
        }
    
    ssh_service = SSHService(profile)
    
    try:
        # Install scripts almost always need sudo (apt-get, yum, pacman)
        # Prefix with sudo unless already present
        if not script.strip().startswith("sudo"):
            script = f"sudo {script}"
        
        output, stderr, exit_code = await ssh_service.execute_command(script)
        
        success = (exit_code == 0)
        
        # If successful, update detected status and enable plugin
        if success:
            detected = dict(profile.detected_plugins or {})
            detected[request.plugin_id] = True
            profile.detected_plugins = detected
            
            enabled = list(profile.enabled_plugins or [])
            if request.plugin_id not in enabled:
                enabled.append(request.plugin_id)
            profile.enabled_plugins = enabled
            
            db.add(profile)
            db.commit()
            db.refresh(profile)
        
        return {
            "success": success,
            "exit_code": exit_code,
            "output": output,
            "stderr": stderr
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Installation failed: {str(e)}")


# --- GET INSTALL SCRIPT PREVIEW ---
@router.get("/install-script/{plugin_id}")
def get_install_script(plugin_id: str, distro: str = "debian"):
    """Get the install script for a plugin (for preview before execution)."""
    plugin = get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    
    install_scripts = plugin.get("install_script", {})
    script = install_scripts.get(distro, "# No install script available for this distro")
    
    return {
        "plugin_id": plugin_id,
        "plugin_name": plugin.get("name"),
        "distro": distro,
        "script": script,
        "requires_sudo": plugin.get("requires_sudo", False)
    }
