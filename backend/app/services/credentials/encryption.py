"""
Encryption utilities for sensitive data.

Uses Fernet symmetric encryption (AES 128-bit) to encrypt/decrypt
passwords and private keys before storing in the database.
"""
from cryptography.fernet import Fernet
from typing import Optional


class EncryptionService:
    """Manages encryption and decryption of sensitive data."""
    
    def __init__(self, key: bytes):
        """
        Initialize the encryption manager.
        
        Args:
            key: Encryption key as bytes.
        """
        self.fernet = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            return plaintext
        
        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            ciphertext: The encrypted string to decrypt
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            cryptography.fernet.InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        if not ciphertext:
            return ciphertext
        
        decrypted_bytes = self.fernet.decrypt(ciphertext.encode())
        return decrypted_bytes.decode()


# Global encryption manager instance
_encryption_manager: Optional[EncryptionService] = None


def get_encryption_manager() -> EncryptionService:
    """
    Get the global encryption manager instance (singleton pattern).
    
    Returns:
        EncryptionService instance
    """
    global _encryption_manager
    if _encryption_manager is None:
        from .config import get_settings
        settings = get_settings()
        _encryption_manager = EncryptionService(settings.encryption_key.encode())
    return _encryption_manager


def encrypt(plaintext: str) -> str:
    """
    Convenience function to encrypt a string.
    
    Args:
        plaintext: The string to encrypt
        
    Returns:
        Encrypted string
    """
    return get_encryption_manager().encrypt(plaintext)


def decrypt(ciphertext: str) -> str:
    """
    Convenience function to decrypt a string.
    
    Args:
        ciphertext: The encrypted string to decrypt
        
    Returns:
        Decrypted string
    """
    return get_encryption_manager().decrypt(ciphertext)
