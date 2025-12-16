"""
Core schema definitions for Unity.

Server profiles and application settings.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, List, Any
from datetime import datetime


# ============================================================
# Server Profile Schemas
# ============================================================

class ServerProfileBase(BaseModel):
    name: str = "Unknown Server"
    description: Optional[str] = None
    ip_address: Optional[str] = None
    
    # SSH Config
    ssh_port: int = 22
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None
    use_local_agent: bool = False
    
    # Data Plugins
    enabled_plugins: List[str] = []
    detected_plugins: Dict[str, bool] = {}

    hardware_info: Dict[str, Any] = {}
    os_info: Dict[str, Any] = {}
    packages: List[Any] = []


class ServerProfileCreate(ServerProfileBase):
    pass


class ServerProfileUpdate(ServerProfileBase):
    name: Optional[str] = None
    

class ServerProfile(ServerProfileBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Settings Schemas
# ============================================================

class SettingsBase(BaseModel):
    providers: Dict[str, Dict[str, Any]] = {}  # Initialize as empty dict
    active_model: Optional[str] = None  # Make active_model optional
    primary_provider: Optional[str] = None  # Make primary_provider optional
    fallback_provider: Optional[str] = None  # Make fallback_provider optional
    system_prompt: Optional[str] = "You are a helpful Homelab Assistant. You have access to server stats and documentation."
    
    cron_24hr_report: Optional[str] = "0 2 * * *"
    cron_7day_report: Optional[str] = "0 3 * * 1"
    cron_monthly_report: Optional[str] = "0 4 1 * *"

    polling_interval: Optional[int] = 30  # Dashboard polling interval in seconds
    alert_sound_enabled: Optional[bool] = False  # Enable sound notifications for critical alerts
    maintenance_mode_until: Optional[datetime] = None  # Time until maintenance mode is active


class SettingsCreate(SettingsBase):
    pass


class SettingsUpdate(SettingsBase):
    maintenance_mode_until: Optional[datetime] = None  # Allow updating maintenance mode separately


class Settings(SettingsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
