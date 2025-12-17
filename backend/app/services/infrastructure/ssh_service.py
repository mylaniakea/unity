"""SSH service for infrastructure monitoring - integrates with Unity's credential system."""
import asyncssh
from typing import Optional, Dict
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app import models
from app.services.credentials.encryption import decrypt

logger = logging.getLogger(__name__)


class SSHConnectionError(Exception):
    """Exception raised for SSH connection errors."""
    pass


class SSHCommandError(Exception):
    """Exception raised for SSH command execution errors."""
    pass


class InfrastructureSSHService:
    """SSH service for infrastructure monitoring using Unity's credential system."""
    
    def __init__(self):
        """Initialize SSH service."""
        self._connection_timeout = 30  # 30 seconds
    
    async def execute_command(
        self,
        server: models.MonitoredServer,
        command: str,
        db: Session,
        timeout: int = 30
    ) -> tuple[str, str, int]:
        """
        Execute a command on a monitored server.
        
        Args:
            server: MonitoredServer model instance
            command: Command to execute
            db: Database session for loading credentials
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (stdout, stderr, exit_code)
            
        Raises:
            SSHConnectionError: If connection fails
            SSHCommandError: If command execution fails
        """
        try:
            # Get credentials from Unity's KC-Booth system
            ssh_key = None
            password = None
            
            if server.ssh_key_id:
                ssh_key_obj = db.query(models.SSHKey).filter(
                    models.SSHKey.id == server.ssh_key_id
                ).first()
                if ssh_key_obj and ssh_key_obj.private_key_encrypted:
                    ssh_key = asyncssh.import_private_key(
                        decrypt(ssh_key_obj.private_key_encrypted)
                    )
            
            if server.credential_id:
                cred = db.query(models.ServerCredential).filter(
                    models.ServerCredential.id == server.credential_id
                ).first()
                if cred and cred.credential_value_encrypted:
                    password = decrypt(cred.credential_value_encrypted)
            
            # Fallback to legacy encrypted credentials if Unity creds not available
            if not ssh_key and not password:
                if server.ssh_private_key_encrypted:
                    ssh_key = asyncssh.import_private_key(
                        decrypt(server.ssh_private_key_encrypted)
                    )
                elif server.ssh_password_encrypted:
                    password = decrypt(server.ssh_password_encrypted)
            
            # Connection options
            connect_kwargs = {
                'host': server.ip_address,
                'port': server.ssh_port,
                'username': server.username,
                'known_hosts': None,  # Disable host key checking for lab environments
                'connect_timeout': self._connection_timeout,
            }
            
            # Add authentication method
            if ssh_key:
                connect_kwargs['client_keys'] = [ssh_key]
            elif password:
                connect_kwargs['password'] = password
            else:
                raise SSHConnectionError(
                    f"No credentials available for server {server.hostname}"
                )
            
            # Execute command
            async with await asyncssh.connect(**connect_kwargs) as conn:
                result = await conn.run(command, timeout=timeout, check=False)
                
                return (
                    result.stdout or "",
                    result.stderr or "",
                    result.exit_status or 0
                )
                
        except asyncssh.Error as e:
            logger.error(f"SSH error for server {server.hostname}: {str(e)}")
            raise SSHConnectionError(f"SSH connection failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error for server {server.hostname}: {str(e)}")
            raise SSHCommandError(f"Command execution failed: {str(e)}")
    
    async def test_connection(
        self,
        server: models.MonitoredServer,
        db: Session
    ) -> tuple[bool, Optional[str]]:
        """
        Test SSH connection to a server.
        
        Args:
            server: MonitoredServer model instance
            db: Database session
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            stdout, stderr, exit_code = await self.execute_command(
                server, "echo 'test'", db, timeout=10
            )
            if exit_code == 0:
                return True, None
            else:
                return False, f"Test command failed: {stderr}"
        except (SSHConnectionError, SSHCommandError) as e:
            return False, str(e)


# Global instance
ssh_service = InfrastructureSSHService()
