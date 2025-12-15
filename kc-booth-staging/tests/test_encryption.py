"""Tests for encryption module."""
import pytest
from src.encryption import encrypt, decrypt


def test_encrypt_decrypt_string():
    """Test encrypting and decrypting a string."""
    original = "my-secret-password"
    encrypted = encrypt(original)
    
    assert encrypted != original
    assert encrypted.startswith("gAAAAA")  # Fernet tokens start with this
    
    decrypted = decrypt(encrypted)
    assert decrypted == original


def test_encrypt_decrypt_empty_string():
    """Test encrypting empty string."""
    original = ""
    encrypted = encrypt(original)
    decrypted = decrypt(encrypted)
    assert decrypted == original


def test_encrypt_produces_different_output():
    """Test that encrypting the same value twice produces different ciphertexts."""
    original = "test-value"
    encrypted1 = encrypt(original)
    encrypted2 = encrypt(original)
    
    # Different ciphertexts (Fernet uses random IV)
    assert encrypted1 != encrypted2
    
    # But both decrypt to same value
    assert decrypt(encrypted1) == original
    assert decrypt(encrypted2) == original


def test_decrypt_invalid_token():
    """Test decrypting invalid token raises error."""
    with pytest.raises(Exception):
        decrypt("invalid-token")
