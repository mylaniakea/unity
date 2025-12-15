"""
Centralized configuration management for kc-booth.

Validates all required environment variables at startup and provides
type-safe access to configuration values.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional
from cryptography.fernet import Fernet


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database configuration
    database_url: str = Field(
        ...,
        description="PostgreSQL database connection URL",
        examples=["postgresql://user:password@localhost:5432/kc-booth-db"]
    )
    
    # Security configuration
    encryption_key: str = Field(
        ...,
        description="Fernet encryption key for sensitive data",
        min_length=40  # Fernet keys are 44 characters base64-encoded
    )
    
    # Step-CA configuration
    step_provisioner_password: str = Field(
        ...,
        description="Password for Step-CA provisioner"
    )
    
    step_ca_url: str = Field(
        default="http://step-ca:9000",
        description="Step-CA server URL"
    )
    
    # Application configuration
    allow_origins: str = Field(
        default="*",
        description="CORS allowed origins (comma-separated)"
    )
    
    # Authentication configuration
    disable_auth: bool = Field(

    # Testing configuration
    test_mode: bool = Field(

    # Certificate provider configuration
    cert_provider: str = Field(
        default="step-ca",
        description="Certificate provider (step-ca, openssh, vault, letsencrypt)"
    )
    
    # Vault configuration (if using vault provider)
    vault_addr: str = Field(
        default="http://vault:8200",
        description="HashiCorp Vault address"
    )
    vault_token: str = Field(
        default="",
        description="Vault authentication token"
    )
    vault_ssh_path: str = Field(
        default="ssh/sign/default",
        description="Vault SSH signing endpoint path"
    )
        default=False,
        description="Enable test mode (self-signed SSH certs, use only for dev/testing)"
    )
        default=False,

    # Testing configuration
    test_mode: bool = Field(

    # Certificate provider configuration
    cert_provider: str = Field(
        default="step-ca",
        description="Certificate provider (step-ca, openssh, vault, letsencrypt)"
    )
    
    # Vault configuration (if using vault provider)
    vault_addr: str = Field(
        default="http://vault:8200",
        description="HashiCorp Vault address"
    )
    vault_token: str = Field(
        default="",
        description="Vault authentication token"
    )
    vault_ssh_path: str = Field(
        default="ssh/sign/default",
        description="Vault SSH signing endpoint path"
    )
        default=False,
        description="Enable test mode (self-signed SSH certs, use only for dev/testing)"
    )
        description="Disable authentication (for development/testing only)"

    # Testing configuration
    test_mode: bool = Field(

    # Certificate provider configuration
    cert_provider: str = Field(
        default="step-ca",
        description="Certificate provider (step-ca, openssh, vault, letsencrypt)"
    )
    
    # Vault configuration (if using vault provider)
    vault_addr: str = Field(
        default="http://vault:8200",
        description="HashiCorp Vault address"
    )
    vault_token: str = Field(
        default="",
        description="Vault authentication token"
    )
    vault_ssh_path: str = Field(
        default="ssh/sign/default",
        description="Vault SSH signing endpoint path"
    )
        default=False,
        description="Enable test mode (self-signed SSH certs, use only for dev/testing)"
    )
    )
    
    # Rate limiting configuration
    rate_limit_login: str = Field(
        default="5/minute",
        description="Rate limit for login endpoint (format: N/period)"
    )
    
    rate_limit_api: str = Field(
        default="100/minute",
        description="Rate limit for API endpoints (format: N/period)"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Validate that the encryption key is a valid Fernet key."""
        try:
            # Attempt to create a Fernet instance to validate the key
            Fernet(v.encode())
        except Exception as e:
            raise ValueError(
                f"Invalid encryption key format. Must be a valid Fernet key. "
                f"Generate one using: python3 generate_encryption_key.py. Error: {e}"
            )
        return v
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate that the database URL starts with postgresql."""
        if not v.startswith("postgresql"):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string starting with 'postgresql://'"
            )
        return v


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance (singleton pattern).
    
    Returns:
        Settings instance
        
    Raises:
        ValidationError: If required environment variables are missing or invalid
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience function to reset settings (useful for testing)
def reset_settings() -> None:
    """Reset the global settings instance. Primarily for testing."""
    global _settings
    _settings = None
