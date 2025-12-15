"""Tests for certificate providers."""
import pytest
from src.cert_providers import get_provider, PROVIDERS, validate_domain, OpenSSHProvider


def test_provider_registry():
    """Test that all expected providers are registered."""
    expected_providers = ["step-ca", "openssh", "vault", "letsencrypt"]
    for provider_name in expected_providers:
        assert provider_name in PROVIDERS


def test_get_provider_default():
    """Test getting default provider."""
    provider = get_provider("openssh")  # Use openssh for testing
    assert provider is not None
    assert provider.get_name() == "openssh"


def test_get_provider_invalid():
    """Test getting invalid provider raises error."""
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nonexistent-provider")


def test_validate_domain_valid():
    """Test domain validation with valid domains."""
    assert validate_domain("example.com") == "example.com"
    assert validate_domain("sub.domain.com") == "sub.domain.com"
    assert validate_domain("server-1.local") == "server-1.local"


def test_validate_domain_command_injection():
    """Test domain validation prevents command injection."""
    with pytest.raises(ValueError):
        validate_domain("example.com; rm -rf /")
    
    with pytest.raises(ValueError):
        validate_domain("$(malicious)")
    
    with pytest.raises(ValueError):
        validate_domain("`whoami`")


def test_openssh_provider_exists():
    """Test OpenSSH provider can be instantiated."""
    provider = OpenSSHProvider()
    assert provider.get_name() == "openssh"


# Note: Actual certificate generation tests require system dependencies (ssh-keygen, step, vault)
# and are better suited for integration tests
