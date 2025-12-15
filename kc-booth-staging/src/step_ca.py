"""
Backward compatibility wrapper for step_ca module.

This module now imports from cert_providers for multi-provider support.
"""
from .cert_providers import (
    issue_certificate,
    validate_domain,
    get_provider,
    PROVIDERS
)

# For backward compatibility
def get_root_fingerprint() -> str:
    """Get step-ca root fingerprint (step-ca specific)."""
    import subprocess
    command = ["step", "ca", "fingerprint"]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout.strip()

__all__ = ['issue_certificate', 'validate_domain', 'get_provider', 'get_root_fingerprint', 'PROVIDERS']
