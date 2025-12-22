"""Test JWT token handling."""
from app.services.auth.jwt_handler import create_access_token, decode_token, verify_token


def test_create_token():
    """Test JWT token creation."""
    data = {"sub": "user123", "username": "testuser"}
    token = create_access_token(data)
    
    assert isinstance(token, str)
    assert len(token) > 20


def test_decode_token():
    """Test token decoding."""
    data = {"sub": "user123", "username": "testuser"}
    token = create_access_token(data)
    
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user123"
    assert decoded["username"] == "testuser"


def test_verify_token():
    """Test token verification."""
    data = {"sub": "user123"}
    token = create_access_token(data)
    
    assert verify_token(token) is True
    assert verify_token("invalid_token") is False
