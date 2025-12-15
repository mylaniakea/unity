"""Tests for input validation."""
import pytest
from src.step_ca import validate_domain
from src.crud import validate_hostname, validate_ip_address, validate_username


def test_validate_domain_valid():
    """Test valid domain names."""
    assert validate_domain("example.com") == "example.com"
    assert validate_domain("sub.example.com") == "sub.example.com"
    assert validate_domain("server-1.local") == "server-1.local"
    assert validate_domain("192.168.1.1") == "192.168.1.1"


def test_validate_domain_invalid():
    """Test invalid domain names."""
    with pytest.raises(ValueError):
        validate_domain("example;com")  # Semicolon
    
    with pytest.raises(ValueError):
        validate_domain("example com")  # Space
    
    with pytest.raises(ValueError):
        validate_domain("-example.com")  # Starts with hyphen
    
    with pytest.raises(ValueError):
        validate_domain("example.com-")  # Ends with hyphen
    
    with pytest.raises(ValueError):
        validate_domain("a" * 254)  # Too long


def test_validate_hostname():
    """Test hostname validation."""
    assert validate_hostname("server1") == "server1"
    assert validate_hostname("web-server") == "web-server"
    assert validate_hostname("app.local") == "app.local"


def test_validate_hostname_invalid():
    """Test invalid hostnames."""
    with pytest.raises(ValueError):
        validate_hostname("server;rm -rf")
    
    with pytest.raises(ValueError):
        validate_hostname("$(malicious)")


def test_validate_ip_address():
    """Test IP address validation."""
    assert validate_ip_address("192.168.1.1") == "192.168.1.1"
    assert validate_ip_address("10.0.0.1") == "10.0.0.1"
    assert validate_ip_address("2001:db8::1") == "2001:db8::1"


def test_validate_ip_address_invalid():
    """Test invalid IP addresses."""
    with pytest.raises(ValueError):
        validate_ip_address("999.999.999.999")
    
    with pytest.raises(ValueError):
        validate_ip_address("not-an-ip")
    
    with pytest.raises(ValueError):
        validate_ip_address("192.168.1.1; rm -rf /")


def test_validate_username():
    """Test username validation."""
    assert validate_username("admin") == "admin"
    assert validate_username("user_123") == "user_123"
    assert validate_username("deploy-user") == "deploy-user"


def test_validate_username_invalid():
    """Test invalid usernames."""
    with pytest.raises(ValueError):
        validate_username("user;malicious")
    
    with pytest.raises(ValueError):
        validate_username("$(command)")
    
    with pytest.raises(ValueError):
        validate_username("a" * 256)  # Too long
