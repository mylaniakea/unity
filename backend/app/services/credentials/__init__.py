"""
Credential Management Services

Unified service layer for KC-Booth credential management in Unity.
Handles SSH keys, certificates, and server credentials with encryption.
"""

from .encryption import EncryptionService
from .ssh_keys import SSHKeyService
from .certificates import CertificateService
from .server_credentials import ServerCredentialService
from .audit import (
    CredentialAuditService,
    audit_ssh_key_created,
    audit_ssh_key_used,
    audit_ssh_key_deleted,
    audit_certificate_created,
    audit_certificate_renewed,
    audit_credential_created,
    audit_credential_used
)

__all__ = [
    # Core services
    "EncryptionService",
    "SSHKeyService",
    "CertificateService",
    "ServerCredentialService",
    "CredentialAuditService",
    
    # Audit convenience functions
    "audit_ssh_key_created",
    "audit_ssh_key_used",
    "audit_ssh_key_deleted",
    "audit_certificate_created",
    "audit_certificate_renewed",
    "audit_credential_created",
    "audit_credential_used",
]
