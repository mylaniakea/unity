import os
import sys
from pathlib import Path

# Add the current directory to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.encryption import encryption_service

def migrate_keys():
    data_dir = Path("data")
    if not data_dir.exists():
        print("Data directory not found.")
        return

    print("=== Starting SSH Key Encryption Migration ===")
    
    # Find all potential private keys (usually end in _rsa, _ed25519, or no extension but paired with .pub)
    # For this project we specifically look for our generated keys
    key_files = list(data_dir.glob("*_rsa")) + list(data_dir.glob("*_ed25519")) + list(data_dir.glob("*.pem"))
    
    count = 0
    encrypted_count = 0
    skipped_count = 0
    
    for key_file in key_files:
        if key_file.suffix == ".pub":
            continue
            
        print(f"Checking key: {key_file.name}...")
        
        try:
            content = key_file.read_text().strip()
            
            # 1. Try to decrypt
            decrypted = encryption_service.decrypt(content)
            
            if decrypted:
                print(f"  -> Already encrypted. Skipping.")
                skipped_count += 1
            else:
                # 2. Decryption failed, assume plain text. Encrypt it.
                print(f"  -> Detected plain text. Encrypting...")
                
                encrypted_content = encryption_service.encrypt(content)
                if encrypted_content:
                    key_file.write_text(encrypted_content)
                    print(f"  -> Successfully encrypted and saved.")
                    encrypted_count += 1
                else:
                    print(f"  -> Error: Encryption returned empty string.")
                    
        except Exception as e:
            print(f"  -> Error processing file: {e}")
            
        count += 1

    print("\n=== Migration Summary ===")
    print(f"Total keys scanned: {count}")
    print(f"Keys encrypted: {encrypted_count}")
    print(f"Keys skipped (already encrypted): {skipped_count}")

if __name__ == "__main__":
    migrate_keys()
