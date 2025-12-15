#!/usr/bin/env python3
"""
Generate an encryption key for kc-booth.

This script generates a Fernet encryption key that should be stored
in the ENCRYPTION_KEY environment variable.

SECURITY WARNING: Keep this key secure! Anyone with access to this key
can decrypt all passwords and private keys stored in the database.
"""
from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = Fernet.generate_key()
    print("=" * 70)
    print("Generated Encryption Key for kc-booth")
    print("=" * 70)
    print()
    print("Add this to your environment variables:")
    print()
    print(f"ENCRYPTION_KEY={key.decode()}")
    print()
    print("=" * 70)
    print("SECURITY WARNINGS:")
    print("- Store this key securely (use a secrets manager in production)")
    print("- Never commit this key to version control")
    print("- If you lose this key, you cannot decrypt existing data")
    print("- If this key is compromised, rotate it immediately")
    print("=" * 70)
