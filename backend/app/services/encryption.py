import os
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Optional

class EncryptionService:
    def __init__(self):
        self.data_dir = Path("data")
        self.key_file = self.data_dir / "encryption.key"
        self.key = self._get_or_create_key()
        self.fernet = Fernet(self.key)

    def _get_or_create_key(self) -> bytes:
        """
        Get the encryption key from environment variable, file, or generate a new one.
        Priority:
        1. Environment Variable (ENCRYPTION_KEY)
        2. File (data/encryption.key)
        3. Generate New & Save to File
        """
        # 1. Try Environment Variable
        env_key = os.environ.get("ENCRYPTION_KEY")
        if env_key:
            print("INFO: Loaded encryption key from environment variable.")
            return env_key.encode()

        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)

        # 2. Try Key File
        if self.key_file.exists():
            try:
                file_key = self.key_file.read_bytes().strip()
                if file_key:
                    print(f"INFO: Loaded encryption key from file: {self.key_file}")
                    return file_key
            except Exception as e:
                print(f"ERROR: Failed to read encryption key file: {e}")

        # 3. Generate New Key
        new_key = Fernet.generate_key()
        try:
            self.key_file.write_bytes(new_key)
            # Set restrictive permissions (read/write for owner only)
            os.chmod(self.key_file, 0o600)
            print(f"WARNING: Generated NEW encryption key and saved to: {self.key_file}")
            print("IMPORTANT: Back up this file! Losing it means losing access to encrypted data.")
        except Exception as e:
            print(f"CRITICAL: Failed to save encryption key to file: {e}")
            # If we can't save it, we return it but warn heavily (ephemeral mode)
            print("WARNING: Using ephemeral key. Data will not be decryptable after restart.")
        
        return new_key

    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        if not data:
            return ""
        try:
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            print(f"Encryption failed: {e}")
            return ""

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        if not encrypted_data:
            return ""
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            # Common error if key mismatch or not encrypted
            # print(f"Decryption failed: {e}") 
            return ""

# Singleton instance
encryption_service = EncryptionService()
