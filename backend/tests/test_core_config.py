"""Tests for core configuration module."""
import pytest
from app.core.config import Settings


@pytest.mark.unit
def test_settings_defaults():
    """Test that settings have sensible defaults."""
    settings = Settings()
    
    assert settings.app_name == "Unity"
    assert settings.app_version is not None
    assert settings.database_url is not None
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_access_token_expire_minutes > 0


@pytest.mark.unit
def test_settings_with_env_override(monkeypatch):
    """Test that environment variables override defaults."""
    monkeypatch.setenv("APP_NAME", "Test Unity")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    
    settings = Settings()
    
    assert settings.app_name == "Test Unity"
    assert settings.jwt_access_token_expire_minutes == 60


@pytest.mark.unit
def test_database_url_validation():
    """Test database URL format."""
    settings = Settings()
    
    # Should start with postgresql:// or sqlite://
    assert settings.database_url.startswith(("postgresql://", "sqlite://"))


@pytest.mark.unit
def test_jwt_secret_key_exists():
    """Test that JWT secret key is set."""
    settings = Settings()
    
    assert settings.jwt_secret_key is not None
    assert len(settings.jwt_secret_key) > 0
