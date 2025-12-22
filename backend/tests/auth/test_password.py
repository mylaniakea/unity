"""Test password hashing."""
from app.services.auth.password import hash_password, verify_password, needs_rehash


def test_hash_password():
    """Test password hashing."""
    password = "mypassword123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 20


def test_verify_password():
    """Test password verification."""
    password = "mypassword123"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_needs_rehash():
    """Test rehash detection."""
    password = "mypassword123"
    hashed = hash_password(password)
    
    # Should not need rehash with same settings
    assert needs_rehash(hashed) is False
