"""
Centralized configuration management for Unity application.

This module provides a single source of truth for all configuration values,
loaded from environment variables with sensible defaults.
"""
import os
import json
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables.
    See .env.example for configuration options.
    """
    
    # Application Metadata
    app_name: str = "Unity - Homelab Intelligence Hub"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "info"
    
    # Database Configuration
    database_url: str = "sqlite:///./data/homelab.db"
    
    # Security - JWT
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # Security - Encryption (for credentials storage)
    encryption_key: Optional[str] = None
    
    # SSH Configuration
    ssh_key_path: str = "./data/homelab_id_rsa"
    
    # AI/LLM API Keys (optional)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Web Push Notifications
    vapid_public_key: Optional[str] = None
    vapid_private_key: Optional[str] = None
    vapid_subject: Optional[str] = None
    
    # Container Management
    docker_host: Optional[str] = None  # Defaults to local Unix socket
    compose_project_prefix: str = "unity"
    
    # Scheduler Configuration
    enable_schedulers: bool = True
    snapshot_interval_hours: int = 24
    infrastructure_collection_minutes: int = 5
    container_scan_interval_hours: int = 6
    threshold_check_interval_minutes: int = 1
    
    # API Configuration
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000,http://localhost:80"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if not self.cors_origins:
            return ["http://localhost:3000", "http://localhost:80"]
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    # Data Retention
    retention_days: int = 365
    
    # Feature Flags
    enable_ai_analysis: bool = False
    enable_push_notifications: bool = True
    enable_plugins: bool = True
    disable_auth: bool = False  # Set to True to disable authentication for testing
    
    # Redis Configuration (for session storage)
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 10
    
    # Session Management
    session_expiry_hours: int = 24
    session_cookie_name: str = "unity_session"
    session_cookie_secure: bool = False  # Set to True in production with HTTPS
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"
    
    # API Key Configuration
    api_key_expiry_days: int = 90
    api_key_prefix: str = "unity_"
    
    # Password Policy
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    password_require_special: bool = False
    bcrypt_rounds: int = 12
    
    # Rate Limiting & Security
    max_login_attempts: int = 5
    login_attempt_window_minutes: int = 15
    lockout_duration_minutes: int = 30

    # OAuth2 Configuration
    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    oauth_redirect_uri: str = "http://localhost:8000/api/auth/oauth/callback"


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.database_url.startswith("sqlite")
    
    @property
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL database."""
        return self.database_url.startswith("postgresql")
    
    def get_database_connect_args(self) -> dict:
        """Get database-specific connection arguments."""
        if self.is_sqlite:
            return {"check_same_thread": False}
        return {}


# Global settings instance
settings = Settings()
