"""Credential background tasks for APScheduler"""
from datetime import datetime
from app.core.database import get_db
from app.services.credentials.cert_providers import CertificateRenewalService
from app.services.credentials.ssh_keys import SSHKeyService

async def check_expiring_certificates_job():
    """Daily: Check expiring certificates"""
    db = next(get_db())
    try:
        expiring = CertificateRenewalService.check_expiring_certificates(db, 30)
        if expiring:
            print(f"⚠️  {len(expiring)} certificates expiring soon")
    finally:
        db.close()

async def check_unused_ssh_keys_job():
    """Weekly: Check unused SSH keys"""  
    print("🔑 Checking unused SSH keys...")
