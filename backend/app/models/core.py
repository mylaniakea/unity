from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, PrimaryKeyConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship # Import relationship for ORM
from app.core.database import Base



class ServerProfile(Base):
    __tablename__ = "server_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, default="Unknown Server")
    description = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)

    # SSH Configuration
    ssh_port = Column(Integer, default=22)
    ssh_username = Column(String, nullable=True)
    ssh_key_path = Column(String, nullable=True) # Path to local key file
    use_local_agent = Column(Boolean, default=False)
    
    # Data Plugins
    enabled_plugins = Column(JSON().with_variant(JSONB, "postgresql"), default=[])   # List of enabled plugin IDs ["lm-sensors", "smartctl"]
    detected_plugins = Column(JSON().with_variant(JSONB, "postgresql"), default={})  # Detected plugins with status {"lm-sensors": True, "smartctl": False}
    
    # Store complex data as JSON for PostgreSQL
    hardware_info = Column(JSON().with_variant(JSONB, "postgresql"), default={})
    os_info = Column(JSON().with_variant(JSONB, "postgresql"), default={})
    packages = Column(JSON().with_variant(JSONB, "postgresql"), default=[])
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to Reports
    reports = relationship("Report", back_populates="server_profile")


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True) # Singleton, always ID 1
    
    # Store provider keys/configs securely (encrypted in future, plain for now)
    providers = Column(JSON().with_variant(JSONB, "postgresql"), default={
        "ollama": {"url": "http://host.docker.internal:11434", "enabled": True},
        "openai": {"api_key": "", "enabled": False},
        "anthropic": {"api_key": "", "enabled": False},
        "google": {"api_key": "", "enabled": False}
    })
    
    # Configuration
    active_model = Column(String, nullable=True)
    primary_provider = Column(String, nullable=True) 
    fallback_provider = Column(String, nullable=True)
    system_prompt = Column(Text, default="You are a helpful Homelab Assistant. You have access to server stats and documentation.")
    
    # Cron settings for reports
    cron_24hr_report = Column(String, default="0 2 * * *") # Daily at 02:00 UTC
    cron_7day_report = Column(String, default="0 3 * * 1") # Mondays at 03:00 UTC
    cron_monthly_report = Column(String, default="0 4 1 * *") # 1st of each month at 04:00 UTC

    # Polling settings
    polling_interval = Column(Integer, default=30) # Dashboard polling interval in seconds (default: 30s)
    alert_sound_enabled = Column(Boolean, default=False) # Enable sound notifications for critical alerts
    maintenance_mode_until = Column(DateTime(timezone=True), nullable=True) # New: Time until maintenance mode is active

    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('server_profiles.id'), index=True) # Link to ServerProfile
    report_type = Column(String, index=True) # e.g., "24-hour", "7-day", "monthly"
    start_time = Column(DateTime(timezone=True), index=True)
    end_time = Column(DateTime(timezone=True), index=True)
    aggregated_data = Column(JSON().with_variant(JSONB, "postgresql"), default={}) # Store aggregated metrics, charts data etc.
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to ServerProfile
    server_profile = relationship("ServerProfile", back_populates="reports")


class KnowledgeItem(Base):
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    category = Column(String, index=True) # network, hardware, manual
    tags = Column(JSON().with_variant(JSONB, "postgresql"), default=[]) # Use JSON for tags
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ServerSnapshot(Base):
    __tablename__ = "server_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('server_profiles.id'), index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    data = Column(JSON().with_variant(JSONB, "postgresql"), default={}) # Comprehensive snapshot data

    server_profile = relationship("ServerProfile", backref="snapshots")


