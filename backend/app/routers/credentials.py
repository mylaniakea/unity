"""
Credential Management API Routes

Secure REST API for SSH keys, certificates, and server credentials.
Integrated from KC-Booth with Unity's authentication and audit systems.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List
import os

from app.database import get_db
from app.models import User, SSHKey, Certificate, ServerCredential
from app.services.auth import get_current_active_user as get_current_user
from app.schemas_credentials import (
    # SSH Key schemas
    SSHKeyCreate, SSHKeyGenerate, SSHKeyResponse, SSHKeyWithPrivateKey,
    # Certificate schemas
    CertificateCreate, CertificateGenerateSelfSigned, CertificateResponse,
    CertificateWithPrivateKey, CertificateRenewalRequest,
    # Server credential schemas
    ServerCredentialCreate, ServerCredentialUpdate,
    ServerCredentialResponse, ServerCredentialWithSecrets,
    # Audit and stats
    CredentialAuditLogResponse, CredentialStats
)
from app.services.credentials import (
    EncryptionService,
    SSHKeyService,
    CertificateService,
    ServerCredentialService,
    CredentialAuditService,
    audit_ssh_key_created,
    audit_ssh_key_used,
    audit_ssh_key_deleted,
    audit_certificate_created,
    audit_certificate_renewed,
    audit_credential_created,
    audit_credential_used,
)

router = APIRouter(prefix="/api/credentials", tags=["credentials"])

# Initialize encryption service
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise RuntimeError("ENCRYPTION_KEY environment variable not set")
encryption_service = EncryptionService(ENCRYPTION_KEY)


def get_client_info(request: Request) -> tuple[str, str]:
    """Extract client IP and user agent from request"""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", None)
    return ip_address, user_agent


# ============================================================
# SSH Key Endpoints
# ============================================================

@router.post("/ssh-keys", response_model=SSHKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_ssh_key(
    key_data: SSHKeyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new SSH key by uploading an existing key pair.
    
    Requires authentication.
    """
    try:
        # Check for duplicate name
        existing = SSHKeyService.get_ssh_key_by_name(db, key_data.name, encryption_service, decrypt=False)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SSH key with name '{key_data.name}' already exists"
            )
        
        # Create SSH key with encryption
        ssh_key = SSHKeyService.create_ssh_key(
            db=db,
            name=key_data.name,
            description=key_data.description,
            private_key=key_data.private_key,
            public_key=key_data.public_key,
            key_type=key_data.key_type,
            key_size=key_data.key_size,
            created_by=current_user.id,
            encryption_service=encryption_service
        )
        
        # Audit log
        ip_address, user_agent = get_client_info(request)
        audit_ssh_key_created(db, ssh_key.id, current_user.id, ip_address, user_agent)
        
        return ssh_key
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/ssh-keys/generate", response_model=SSHKeyWithPrivateKey, status_code=status.HTTP_201_CREATED)
async def generate_ssh_key(
    gen_data: SSHKeyGenerate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a new SSH key pair.
    
    Returns the generated key pair including the private key (one-time only).
    Requires authentication.
    """
    try:
        # Check for duplicate name
        existing = SSHKeyService.get_ssh_key_by_name(db, gen_data.name, encryption_service, decrypt=False)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SSH key with name '{gen_data.name}' already exists"
            )
        
        # Generate key pair
        private_key, public_key = SSHKeyService.generate_key_pair(
            key_type=gen_data.key_type,
            key_size=gen_data.key_size
        )
        
        # Store with encryption
        ssh_key = SSHKeyService.create_ssh_key(
            db=db,
            name=gen_data.name,
            description=gen_data.description,
            private_key=private_key,
            public_key=public_key,
            key_type=gen_data.key_type,
            key_size=gen_data.key_size,
            created_by=current_user.id,
            encryption_service=encryption_service
        )
        
        # Audit log
        ip_address, user_agent = get_client_info(request)
        audit_ssh_key_created(db, ssh_key.id, current_user.id, ip_address, user_agent)
        
        # Return with decrypted private key (one-time access)
        ssh_key_dict = SSHKeyWithPrivateKey.model_validate(ssh_key).model_dump()
        ssh_key_dict["private_key"] = private_key
        return ssh_key_dict
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/ssh-keys", response_model=List[SSHKeyResponse])
async def list_ssh_keys(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all SSH keys (private keys excluded)."""
    keys = SSHKeyService.list_ssh_keys(db, skip=skip, limit=limit)
    return keys


@router.get("/ssh-keys/{key_id}", response_model=SSHKeyResponse)
async def get_ssh_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get SSH key by ID (private key excluded)."""
    ssh_key = SSHKeyService.get_ssh_key(db, key_id, encryption_service, decrypt=False)
    if not ssh_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSH key not found")
    return ssh_key


@router.get("/ssh-keys/{key_id}/private", response_model=SSHKeyWithPrivateKey)
async def get_ssh_key_with_private(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get SSH key with decrypted private key.
    
    Requires authentication. Use sparingly and securely.
    """
    ssh_key = SSHKeyService.get_ssh_key(db, key_id, encryption_service, decrypt=True)
    if not ssh_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSH key not found")
    
    # Audit log
    ip_address, user_agent = get_client_info(request)
    audit_ssh_key_used(db, ssh_key.id, current_user.id, ip_address, user_agent, "Private key accessed")
    
    # Update last_used
    SSHKeyService.update_last_used(db, key_id)
    
    return ssh_key


@router.delete("/ssh-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ssh_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete SSH key. Requires authentication."""
    success = SSHKeyService.delete_ssh_key(db, key_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSH key not found")
    
    # Audit log
    ip_address, user_agent = get_client_info(request)
    audit_ssh_key_deleted(db, key_id, current_user.id, ip_address, user_agent)
    
    return None


# ============================================================
# Certificate Endpoints
# ============================================================

@router.post("/certificates", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
async def create_certificate(
    cert_data: CertificateCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new certificate by uploading an existing cert.
    
    Requires authentication.
    """
    try:
        # Check for duplicate name
        existing = CertificateService.get_certificate_by_name(db, cert_data.name, encryption_service, decrypt=False)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Certificate with name '{cert_data.name}' already exists"
            )
        
        # Create certificate with encryption
        cert = CertificateService.create_certificate(
            db=db,
            name=cert_data.name,
            description=cert_data.description,
            certificate=cert_data.certificate,
            private_key=cert_data.private_key,
            chain=cert_data.chain,
            provider=cert_data.provider,
            auto_renew=cert_data.auto_renew,
            renewal_days=cert_data.renewal_days,
            created_by=current_user.id,
            encryption_service=encryption_service
        )
        
        # Audit log
        ip_address, user_agent = get_client_info(request)
        audit_certificate_created(db, cert.id, current_user.id, ip_address, user_agent)
        
        return cert
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/certificates/generate-self-signed", response_model=CertificateWithPrivateKey, status_code=status.HTTP_201_CREATED)
async def generate_self_signed_certificate(
    gen_data: CertificateGenerateSelfSigned,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a new self-signed certificate.
    
    Returns the certificate with private key (one-time only).
    Requires authentication.
    """
    try:
        # Check for duplicate name
        existing = CertificateService.get_certificate_by_name(db, gen_data.name, encryption_service, decrypt=False)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Certificate with name '{gen_data.name}' already exists"
            )
        
        # Generate self-signed certificate
        cert_pem, key_pem = CertificateService.generate_self_signed_cert(
            common_name=gen_data.common_name,
            organization=gen_data.organization,
            validity_days=gen_data.validity_days
        )
        
        # Store with encryption
        cert = CertificateService.create_certificate(
            db=db,
            name=gen_data.name,
            description=gen_data.description,
            certificate=cert_pem,
            private_key=key_pem,
            chain=None,
            provider="self-signed",
            auto_renew=False,
            renewal_days=30,
            created_by=current_user.id,
            encryption_service=encryption_service
        )
        
        # Audit log
        ip_address, user_agent = get_client_info(request)
        audit_certificate_created(db, cert.id, current_user.id, ip_address, user_agent)
        
        # Return with decrypted private key (one-time access)
        cert_dict = CertificateWithPrivateKey.model_validate(cert).model_dump()
        cert_dict["private_key"] = key_pem
        return cert_dict
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/certificates", response_model=List[CertificateResponse])
async def list_certificates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all certificates (private keys excluded)."""
    certs = CertificateService.list_certificates(db, skip=skip, limit=limit)
    return certs


@router.get("/certificates/expiring", response_model=List[CertificateResponse])
async def get_expiring_certificates(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get certificates expiring within specified days."""
    certs = CertificateService.get_expiring_soon(db, days=days)
    return certs


@router.get("/certificates/{cert_id}", response_model=CertificateResponse)
async def get_certificate(
    cert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get certificate by ID (private key excluded)."""
    cert = CertificateService.get_certificate(db, cert_id, encryption_service, decrypt=False)
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    return cert


@router.get("/certificates/{cert_id}/private", response_model=CertificateWithPrivateKey)
async def get_certificate_with_private(
    cert_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get certificate with decrypted private key.
    
    Requires authentication. Use sparingly and securely.
    """
    cert = CertificateService.get_certificate(db, cert_id, encryption_service, decrypt=True)
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    
    # Audit log
    ip_address, user_agent = get_client_info(request)
    CredentialAuditService.log_action(
        db=db,
        action="use",
        resource_type="certificate",
        resource_id=cert.id,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        details="Private key accessed"
    )
    
    return cert


@router.put("/certificates/{cert_id}/renew", response_model=CertificateResponse)
async def renew_certificate(
    cert_id: int,
    renewal_data: CertificateRenewalRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Renew a certificate with new certificate data.
    
    Requires authentication.
    """
    try:
        cert = CertificateService.update_certificate(
            db=db,
            cert_id=cert_id,
            certificate=renewal_data.certificate,
            private_key=renewal_data.private_key,
            chain=renewal_data.chain,
            encryption_service=encryption_service
        )
        
        if not cert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
        
        # Audit log
        ip_address, user_agent = get_client_info(request)
        audit_certificate_renewed(db, cert.id, current_user.id, ip_address, user_agent)
        
        return cert
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/certificates/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certificate(
    cert_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete certificate. Requires authentication."""
    success = CertificateService.delete_certificate(db, cert_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    
    # Audit log
    ip_address, user_agent = get_client_info(request)
    CredentialAuditService.log_action(
        db=db,
        action="delete",
        resource_type="certificate",
        resource_id=cert_id,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return None


# ============================================================
# Server Credential Endpoints
# ============================================================

@router.post("/server-credentials", response_model=ServerCredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_server_credential(
    cred_data: ServerCredentialCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new server credential.
    
    Links to Unity's ServerProfile. Requires authentication.
    """
    try:
        # Verify server profile exists
        if not ServerCredentialService.verify_server_exists(db, cred_data.server_profile_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server profile {cred_data.server_profile_id} not found"
            )
        
        # Check for existing credential
        existing = ServerCredentialService.get_credential_by_server(db, cred_data.server_profile_id, encryption_service, decrypt=False)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Credential for server {cred_data.server_profile_id} already exists"
            )
        
        # Create credential with encryption
        credential = ServerCredentialService.create_credential(
            db=db,
            server_profile_id=cred_data.server_profile_id,
            username=cred_data.username,
            password=cred_data.password,
            ssh_key_id=cred_data.ssh_key_id,
            sudo_password=cred_data.sudo_password,
            created_by=current_user.id,
            encryption_service=encryption_service
        )
        
        # Audit log
        ip_address, user_agent = get_client_info(request)
        audit_credential_created(db, credential.id, current_user.id, ip_address, user_agent)
        
        return credential
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/server-credentials", response_model=List[ServerCredentialResponse])
async def list_server_credentials(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all server credentials (passwords excluded)."""
    credentials = ServerCredentialService.list_credentials(db, skip=skip, limit=limit)
    return credentials


@router.get("/server-credentials/{cred_id}", response_model=ServerCredentialResponse)
async def get_server_credential(
    cred_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get server credential by ID (passwords excluded)."""
    credential = ServerCredentialService.get_credential(db, cred_id, encryption_service, decrypt=False)
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server credential not found")
    return credential


@router.get("/server-credentials/server/{server_profile_id}", response_model=ServerCredentialResponse)
async def get_credential_by_server(
    server_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get credential for a specific server (passwords excluded)."""
    credential = ServerCredentialService.get_credential_by_server(db, server_profile_id, encryption_service, decrypt=False)
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server credential not found")
    return credential


@router.get("/server-credentials/{cred_id}/secrets", response_model=ServerCredentialWithSecrets)
async def get_server_credential_with_secrets(
    cred_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get server credential with decrypted passwords.
    
    Requires authentication. Use sparingly and securely.
    """
    credential = ServerCredentialService.get_credential(db, cred_id, encryption_service, decrypt=True)
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server credential not found")
    
    # Audit log
    ip_address, user_agent = get_client_info(request)
    audit_credential_used(db, credential.id, current_user.id, ip_address, user_agent, "Secrets accessed")
    
    # Update last_used
    ServerCredentialService.update_last_used(db, cred_id)
    
    return credential


@router.put("/server-credentials/{cred_id}", response_model=ServerCredentialResponse)
async def update_server_credential(
    cred_id: int,
    update_data: ServerCredentialUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update server credential. Requires authentication."""
    try:
        credential = ServerCredentialService.update_credential(
            db=db,
            credential_id=cred_id,
            username=update_data.username,
            password=update_data.password,
            ssh_key_id=update_data.ssh_key_id,
            sudo_password=update_data.sudo_password,
            encryption_service=encryption_service
        )
        
        if not credential:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server credential not found")
        
        # Audit log
        ip_address, user_agent = get_client_info(request)
        CredentialAuditService.log_action(
            db=db,
            action="update",
            resource_type="credential",
            resource_id=cred_id,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return credential
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/server-credentials/{cred_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server_credential(
    cred_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete server credential. Requires authentication."""
    success = ServerCredentialService.delete_credential(db, cred_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server credential not found")
    
    # Audit log
    ip_address, user_agent = get_client_info(request)
    CredentialAuditService.log_action(
        db=db,
        action="delete",
        resource_type="credential",
        resource_id=cred_id,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return None


# ============================================================
# Audit Log Endpoints
# ============================================================

@router.get("/audit-logs", response_model=List[CredentialAuditLogResponse])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recent credential audit logs. Requires authentication."""
    logs = CredentialAuditService.get_recent_logs(db, skip=skip, limit=limit)
    return logs


@router.get("/audit-logs/resource/{resource_type}/{resource_id}", response_model=List[CredentialAuditLogResponse])
async def get_audit_logs_by_resource(
    resource_type: str,
    resource_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get audit logs for a specific resource."""
    logs = CredentialAuditService.get_logs_by_resource(db, resource_type, resource_id, skip=skip, limit=limit)
    return logs


# ============================================================
# Statistics Endpoint
# ============================================================

@router.get("/stats", response_model=CredentialStats)
async def get_credential_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get credential statistics."""
    # Count totals
    total_ssh_keys = db.execute(select(func.count(SSHKey.id))).scalar() or 0
    total_certificates = db.execute(select(func.count(Certificate.id))).scalar() or 0
    total_credentials = db.execute(select(func.count(ServerCredential.id))).scalar() or 0
    
    # Count expiring certificates (30 days)
    expiring_certs = len(CertificateService.get_expiring_soon(db, days=30))
    
    # Count unused keys (never used)
    stmt = select(func.count(SSHKey.id)).where(SSHKey.last_used == None)
    unused_keys = db.execute(stmt).scalar() or 0
    
    return CredentialStats(
        total_ssh_keys=total_ssh_keys,
        total_certificates=total_certificates,
        total_credentials=total_credentials,
        expiring_certificates=expiring_certs,
        unused_keys=unused_keys
    )
