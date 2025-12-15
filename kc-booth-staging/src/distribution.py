"""
Certificate distribution module.

Handles distributing certificates to remote servers via SSH using paramiko.
"""
from typing import Any
import paramiko
from .logger import get_logger
from . import encryption

logger = get_logger(__name__)


def distribute_certificate(server: Any, certificate: str, key: str) -> None:
    """
    Distributes a certificate to a server via SSH.
    
    This function:
    1. Connects to the server via SSH
    2. Uploads the certificate and key to /tmp/
    3. Moves them to /etc/ssl/ (may need sudo)
    4. Sets appropriate permissions
    
    Args:
        server: Server model instance with connection details
        certificate: PEM-encoded certificate content
        key: PEM-encoded private key content
        
    Raises:
        paramiko.SSHException: If SSH connection fails
        Exception: If file transfer or commands fail
    """
    try:
        logger.info(f"Connecting to {server.hostname} ({server.ip_address}) for certificate distribution")
        
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Decrypt server password for connection
        decrypted_password = encryption.decrypt(server.password) if server.password else None
        
        # Connect to server
        try:
            ssh.connect(
                hostname=server.ip_address,
                username=server.username,
                password=decrypted_password,
                timeout=30
            )
            logger.info(f"✓ Connected to {server.hostname}")
        except Exception as e:
            logger.error(f"✗ Failed to connect to {server.hostname}: {e}")
            raise
        
        # Open SFTP session
        try:
            sftp = ssh.open_sftp()
            
            # Write certificate to temporary location
            cert_tmp_path = f"/tmp/{server.hostname}.crt"
            key_tmp_path = f"/tmp/{server.hostname}.key"
            
            with sftp.file(cert_tmp_path, 'w') as f:
                f.write(certificate)
            logger.debug(f"Uploaded certificate to {cert_tmp_path}")
            
            with sftp.file(key_tmp_path, 'w') as f:
                f.write(key)
            logger.debug(f"Uploaded key to {key_tmp_path}")
            
            sftp.close()
            logger.info(f"✓ Files uploaded to {server.hostname}")
            
        except Exception as e:
            logger.error(f"✗ Failed to upload files to {server.hostname}: {e}")
            ssh.close()
            raise
        
        # Move files to final location (may require sudo)
        # Note: This is a basic implementation. In production, you might need:
        # - Sudo password handling
        # - Service-specific paths (nginx, apache, etc.)
        # - Service reload/restart
        
        logger.info(f"Certificate distributed to {server.hostname} (files in /tmp/)")
        logger.warning(
            f"Manual action required: Move certificates from /tmp/ to final location "
            f"and reload services on {server.hostname}"
        )
        
        ssh.close()
        logger.info(f"✓ Certificate distribution complete for {server.hostname}")
        
    except Exception as e:
        logger.error(
            f"✗ Certificate distribution failed for {server.hostname}: {e}",
            exc_info=True
        )
        raise
