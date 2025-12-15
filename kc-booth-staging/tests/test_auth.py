"""Tests for authentication."""
import pytest
from src.auth_crud import hash_password, verify_password


def test_hash_password():
    """Test password hashing."""
    password = "mySecurePassword123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert hashed.startswith("$2b$")  # bcrypt hash prefix
    assert len(hashed) == 60  # bcrypt hash length


def test_verify_password_correct():
    """Test verifying correct password."""
    password = "testPassword456"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test verifying incorrect password."""
    password = "correctPassword"
    wrong_password = "wrongPassword"
    hashed = hash_password(password)
    
    assert verify_password(wrong_password, hashed) is False


def test_hash_same_password_different_hashes():
    """Test that hashing same password produces different hashes (salt)."""
    password = "samePassword"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    
    assert hash1 != hash2
    assert verify_password(password, hash1)
    assert verify_password(password, hash2)
