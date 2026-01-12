"""
Prometheus Metrics for Credential Management

Exports metrics for monitoring certificate expiry, key usage, and API operations.
"""

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.models import SSHKey, Certificate, ServerCredential, CredentialAuditLog


# Define metrics
credentials_api_requests = Counter(
    'credentials_api_requests_total',
    'Total API requests to credential endpoints',
    ['endpoint', 'method', 'status']
)

certificates_total = Gauge(
    'credentials_certificates_total',
    'Total number of certificates'
)

certificates_expiring = Gauge(
    'credentials_certificates_expiring',
    'Number of certificates expiring soon',
    ['days']
)

ssh_keys_total = Gauge(
    'credentials_ssh_keys_total',
    'Total number of SSH keys'
)

ssh_keys_unused = Gauge(
    'credentials_ssh_keys_unused',
    'Number of unused SSH keys'
)

server_credentials_total = Gauge(
    'credentials_server_credentials_total',
    'Total number of server credentials'
)

audit_log_entries = Counter(
    'credentials_audit_log_entries_total',
    'Total audit log entries',
    ['action', 'resource_type', 'success']
)


def update_metrics(db: Session, tenant_id: str = "default"):
    """Update all Prometheus metrics from database"""
    
    # Count totals
    certificates_total.set(db.execute(select(func.count(Certificate.id))).scalar() or 0)
    ssh_keys_total.set(db.execute(select(func.count(SSHKey.id))).scalar() or 0)
    server_credentials_total.set(db.execute(select(func.count(ServerCredential.id))).scalar() or 0)
    
    # Certificates expiring soon
    now = datetime.utcnow()
    for days in [7, 30, 90]:
        threshold = now + timedelta(days=days)
        count = db.execute(
            select(func.count(Certificate.id)).where(Certificate.valid_until <= threshold)
        ).scalar() or 0
        certificates_expiring.labels(days=str(days)).set(count)
    
    # Unused SSH keys
    unused = db.execute(
        select(func.count(SSHKey.id)).where(SSHKey.last_used == None)
    ).scalar() or 0
    ssh_keys_unused.set(unused)


def get_metrics_text(db: Session) -> bytes:
    """
    Generate Prometheus metrics in text format.
    
    Returns:
        Metrics in Prometheus exposition format
    """
    update_metrics(db)
    return generate_latest()
