"""
SSH Key Distribution Service

Automatically distributes SSH keys to servers and manages authorized_keys.
Integrates with Unity's SSH service and ServerProfile system.
"""

import asyncssh
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models import SSHKey, ServerProfile, ServerCredential
from app.services.ssh import SSHService
from .ssh_keys import SSHKeyService
from .audit import CredentialAuditService
from .encryption import EncryptionService


class SSHKeyDistributionService:
    """Service for distributing SSH keys to servers"""
    
    @staticmethod
    async def distribute_key_to_servers(
        db: Session,
        key_id: int,
        server_profile_ids: List[int],
        encryption_service: EncryptionService,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Distribute an SSH key to multiple servers.
        
        Args:
            db: Database session
            key_id: SSH key ID to distribute
            server_profile_ids: List of server profile IDs
            encryption_service: Encryption service for decrypting key
            user_id: User performing the action
            ip_address: IP address of requester
            user_agent: User agent of requester
            
        Returns:
            Dict with distribution results for each server
        """
        
        # Get the SSH key with decrypted private key
        ssh_key = SSHKeyService.get_ssh_key(db, key_id, encryption_service, decrypt=True)
        if not ssh_key:
            raise ValueError(f"SSH key {key_id} not found")
        
        results = {
            "key_id": key_id,
            "key_name": ssh_key.name,
            "servers": {},
            "success_count": 0,
            "failure_count": 0
        }
        
        # Distribute to each server
        for server_id in server_profile_ids:
            try:
                result = await SSHKeyDistributionService._distribute_to_server(
                    db=db,
                    ssh_key=ssh_key,
                    server_profile_id=server_id,
                    encryption_service=encryption_service
                )
                
                results["servers"][server_id] = result
                
                if result["success"]:
                    results["success_count"] += 1
                    
                    # Audit log for successful distribution
                    CredentialAuditService.log_action(
                        db=db,
                        action="distribute",
                        resource_type="ssh_key",
                        resource_id=key_id,
                        user_id=user_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        details=f"Distributed to server {server_id}: {result['server_hostname']}",
                        success=True
                    )
                else:
                    results["failure_count"] += 1
                    
                    # Audit log for failed distribution
                    CredentialAuditService.log_action(
                        db=db,
                        action="distribute",
                        resource_type="ssh_key",
                        resource_id=key_id,
                        user_id=user_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        details=f"Failed to distribute to server {server_id}: {result.get('error', 'Unknown error')}",
                        success=False
                    )
                    
            except Exception as e:
                results["servers"][server_id] = {
                    "success": False,
                    "error": str(e),
                    "server_id": server_id
                }
                results["failure_count"] += 1
        
        # Update last_used timestamp
        SSHKeyService.update_last_used(db, key_id)
        
        return results
    
    @staticmethod
    async def _distribute_to_server(
        db: Session,
        ssh_key: SSHKey,
        server_profile_id: int,
        encryption_service: EncryptionService
    ) -> Dict[str, Any]:
        """Distribute a single key to a single server"""
        
        # Get server profile
        stmt = select(ServerProfile).where(ServerProfile.id == server_profile_id)
        result = db.execute(stmt)
        server_profile = result.scalar_one_or_none()
        
        if not server_profile:
            return {
                "success": False,
                "error": f"Server profile {server_profile_id} not found",
                "server_id": server_profile_id
            }
        
        # Get server credentials for authentication
        stmt = select(ServerCredential).where(
            ServerCredential.server_profile_id == server_profile_id
        )
        result = db.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if not credential:
            return {
                "success": False,
                "error": f"No credentials found for server {server_profile_id}",
                "server_id": server_profile_id,
                "server_hostname": server_profile.hostname
            }
        
        try:
            # Decrypt password if available
            password = None
            if credential.password:
                password = encryption_service.decrypt(credential.password)
            
            # Connect to server
            username = credential.username or server_profile.ssh_username or "root"
            
            async with asyncssh.connect(
                server_profile.ip_address,
                port=server_profile.ssh_port or 22,
                username=username,
                password=password,
                known_hosts=None  # For homelab; use strict checking in production
            ) as conn:
                
                # Create .ssh directory if it doesn't exist
                await conn.run("mkdir -p ~/.ssh && chmod 700 ~/.ssh")
                
                # Read current authorized_keys
                result = await conn.run("cat ~/.ssh/authorized_keys 2>/dev/null || true")
                current_keys = result.stdout
                
                # Check if key already exists
                if ssh_key.public_key.strip() in current_keys:
                    return {
                        "success": True,
                        "message": "Key already exists on server",
                        "server_id": server_profile_id,
                        "server_hostname": server_profile.hostname,
                        "already_existed": True
                    }
                
                # Backup current authorized_keys
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_path = f"~/.ssh/authorized_keys.backup.{timestamp}"
                if current_keys.strip():
                    await conn.run(f"cp ~/.ssh/authorized_keys {backup_path}")
                
                # Append new key
                escaped_key = ssh_key.public_key.strip().replace("'", "'\"'\"'")
                await conn.run(
                    f"echo '{escaped_key}' >> ~/.ssh/authorized_keys && "
                    f"chmod 600 ~/.ssh/authorized_keys"
                )
                
                # Verify key was added
                result = await conn.run("cat ~/.ssh/authorized_keys")
                if ssh_key.public_key.strip() not in result.stdout:
                    # Rollback
                    if current_keys.strip():
                        await conn.run(f"mv {backup_path} ~/.ssh/authorized_keys")
                    raise Exception("Key verification failed after installation")
                
                return {
                    "success": True,
                    "message": "Key distributed successfully",
                    "server_id": server_profile_id,
                    "server_hostname": server_profile.hostname,
                    "backup_path": backup_path if current_keys.strip() else None,
                    "already_existed": False
                }
                
        except asyncssh.Error as e:
            return {
                "success": False,
                "error": f"SSH connection error: {str(e)}",
                "server_id": server_profile_id,
                "server_hostname": server_profile.hostname
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "server_id": server_profile_id,
                "server_hostname": server_profile.hostname
            }
    
    @staticmethod
    async def remove_key_from_servers(
        db: Session,
        key_id: int,
        server_profile_ids: List[int],
        encryption_service: EncryptionService,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Remove an SSH key from multiple servers.
        
        Args:
            db: Database session
            key_id: SSH key ID to remove
            server_profile_ids: List of server profile IDs
            encryption_service: Encryption service
            user_id: User performing the action
            ip_address: IP address of requester
            user_agent: User agent of requester
            
        Returns:
            Dict with removal results for each server
        """
        
        # Get the SSH key
        ssh_key = SSHKeyService.get_ssh_key(db, key_id, encryption_service, decrypt=False)
        if not ssh_key:
            raise ValueError(f"SSH key {key_id} not found")
        
        results = {
            "key_id": key_id,
            "key_name": ssh_key.name,
            "servers": {},
            "success_count": 0,
            "failure_count": 0
        }
        
        # Remove from each server
        for server_id in server_profile_ids:
            try:
                result = await SSHKeyDistributionService._remove_from_server(
                    db=db,
                    ssh_key=ssh_key,
                    server_profile_id=server_id,
                    encryption_service=encryption_service
                )
                
                results["servers"][server_id] = result
                
                if result["success"]:
                    results["success_count"] += 1
                    
                    # Audit log
                    CredentialAuditService.log_action(
                        db=db,
                        action="remove_distribution",
                        resource_type="ssh_key",
                        resource_id=key_id,
                        user_id=user_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        details=f"Removed from server {server_id}: {result['server_hostname']}",
                        success=True
                    )
                else:
                    results["failure_count"] += 1
                    
            except Exception as e:
                results["servers"][server_id] = {
                    "success": False,
                    "error": str(e),
                    "server_id": server_id
                }
                results["failure_count"] += 1
        
        return results
    
    @staticmethod
    async def _remove_from_server(
        db: Session,
        ssh_key: SSHKey,
        server_profile_id: int,
        encryption_service: EncryptionService
    ) -> Dict[str, Any]:
        """Remove a single key from a single server"""
        
        # Get server profile
        stmt = select(ServerProfile).where(ServerProfile.id == server_profile_id)
        result = db.execute(stmt)
        server_profile = result.scalar_one_or_none()
        
        if not server_profile:
            return {
                "success": False,
                "error": f"Server profile {server_profile_id} not found",
                "server_id": server_profile_id
            }
        
        # Get credentials
        stmt = select(ServerCredential).where(
            ServerCredential.server_profile_id == server_profile_id
        )
        result = db.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if not credential:
            return {
                "success": False,
                "error": f"No credentials found for server {server_profile_id}",
                "server_id": server_profile_id,
                "server_hostname": server_profile.hostname
            }
        
        try:
            # Decrypt password
            password = None
            if credential.password:
                password = encryption_service.decrypt(credential.password)
            
            username = credential.username or server_profile.ssh_username or "root"
            
            async with asyncssh.connect(
                server_profile.ip_address,
                port=server_profile.ssh_port or 22,
                username=username,
                password=password,
                known_hosts=None
            ) as conn:
                
                # Backup authorized_keys
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_path = f"~/.ssh/authorized_keys.backup.{timestamp}"
                await conn.run(f"cp ~/.ssh/authorized_keys {backup_path} 2>/dev/null || true")
                
                # Remove the key using grep -v
                key_fingerprint = ssh_key.public_key.split()[1][:20] if len(ssh_key.public_key.split()) > 1 else ""
                await conn.run(
                    f"grep -v '{key_fingerprint}' ~/.ssh/authorized_keys > ~/.ssh/authorized_keys.tmp && "
                    f"mv ~/.ssh/authorized_keys.tmp ~/.ssh/authorized_keys || true"
                )
                
                return {
                    "success": True,
                    "message": "Key removed successfully",
                    "server_id": server_profile_id,
                    "server_hostname": server_profile.hostname,
                    "backup_path": backup_path
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "server_id": server_profile_id,
                "server_hostname": server_profile.hostname
            }
    
    @staticmethod
    async def get_distribution_status(
        db: Session,
        key_id: int,
        server_profile_id: int,
        encryption_service: EncryptionService
    ) -> Dict[str, Any]:
        """
        Check if an SSH key is installed on a server.
        
        Returns:
            Dict with status information
        """
        
        # Get the SSH key
        ssh_key = SSHKeyService.get_ssh_key(db, key_id, encryption_service, decrypt=False)
        if not ssh_key:
            raise ValueError(f"SSH key {key_id} not found")
        
        # Get server profile
        stmt = select(ServerProfile).where(ServerProfile.id == server_profile_id)
        result = db.execute(stmt)
        server_profile = result.scalar_one_or_none()
        
        if not server_profile:
            return {
                "installed": False,
                "error": f"Server profile {server_profile_id} not found"
            }
        
        try:
            # Get credentials
            stmt = select(ServerCredential).where(
                ServerCredential.server_profile_id == server_profile_id
            )
            result = db.execute(stmt)
            credential = result.scalar_one_or_none()
            
            if not credential:
                return {
                    "installed": False,
                    "error": "No credentials found for server"
                }
            
            # Decrypt password
            password = None
            if credential.password:
                password = encryption_service.decrypt(credential.password)
            
            username = credential.username or server_profile.ssh_username or "root"
            
            async with asyncssh.connect(
                server_profile.ip_address,
                port=server_profile.ssh_port or 22,
                username=username,
                password=password,
                known_hosts=None
            ) as conn:
                
                # Check if key exists
                result = await conn.run("cat ~/.ssh/authorized_keys 2>/dev/null || true")
                installed = ssh_key.public_key.strip() in result.stdout
                
                return {
                    "installed": installed,
                    "server_hostname": server_profile.hostname,
                    "server_id": server_profile_id,
                    "key_name": ssh_key.name,
                    "checked_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                "installed": False,
                "error": str(e),
                "server_hostname": server_profile.hostname,
                "server_id": server_profile_id
            }
