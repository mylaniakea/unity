"""Certificate provider abstraction supporting multiple CAs."""
import subprocess
import os
import re
import tempfile
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional
from .config import get_settings
from .logger import get_logger

logger = get_logger(__name__)


def validate_domain(domain: str) -> str:
    """
    Validate domain name to prevent command injection.
    
    Args:
        domain: Domain name to validate
        
    Returns:
        Validated domain name
        
    Raises:
        ValueError: If domain contains invalid characters
    """
    if not re.match(r'^[a-zA-Z0-9\.\-]+$', domain):
        raise ValueError(f"Invalid domain name: {domain}")
    if len(domain) > 253:
        raise ValueError("Domain name too long")
    if domain.startswith('-') or domain.endswith('-'):
        raise ValueError("Domain cannot start or end with hyphen")
    return domain


class CertificateProvider(ABC):
    """Abstract base class for certificate providers."""
    
    @abstractmethod
    def issue_certificate(self, domain: str) -> tuple[str, str]:
        """
        Issue a certificate for the given domain.
        
        Args:
            domain: Domain name for the certificate
            
        Returns:
            Tuple of (certificate, private_key)
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this provider."""
        pass


class StepCAProvider(CertificateProvider):
    """Step-CA certificate provider (production)."""
    
    def get_name(self) -> str:
        return "step-ca"
    
    def issue_certificate(self, domain: str) -> tuple[str, str]:
        """Issue certificate via step-ca."""
        domain = validate_domain(domain)
        settings = get_settings()
        
        cert_file = f"{domain}.crt"
        key_file = f"{domain}.key"
        
        command = [
            "step", "ca", "certificate", domain,
            cert_file, key_file,
            "--provisioner", "admin",
            "--provisioner-password", settings.step_provisioner_password,
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"step-ca certificate issuance failed: {e.stderr}")
            raise
        
        with open(cert_file, "r") as f:
            cert = f.read()
        with open(key_file, "r") as f:
            key = f.read()
        
        os.remove(cert_file)
        os.remove(key_file)
        
        logger.info(f"Certificate issued via step-ca for {domain}")
        return cert, key


class OpenSSHProvider(CertificateProvider):
    """OpenSSH native ssh-keygen provider (testing/simple deployments)."""
    
    def get_name(self) -> str:
        return "openssh"
    
    def issue_certificate(self, domain: str) -> tuple[str, str]:
        """Issue self-signed SSH certificate using ssh-keygen."""
        domain = validate_domain(domain)
        
        logger.warning(f"Using OpenSSH provider for {domain} - suitable for testing/simple setups")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Generate CA key pair
            ca_key = tmppath / "test_ca"
            subprocess.run([
                "ssh-keygen", "-t", "rsa", "-b", "2048",
                "-f", str(ca_key), "-N", "", "-C", "kc-booth-ca"
            ], check=True, capture_output=True)
            
            # Generate host key pair
            host_key = tmppath / "host_key"
            subprocess.run([
                "ssh-keygen", "-t", "rsa", "-b", "2048",
                "-f", str(host_key), "-N", "", "-C", f"{domain}"
            ], check=True, capture_output=True)
            
            # Sign the host public key
            subprocess.run([
                "ssh-keygen", "-s", str(ca_key),
                "-I", f"{domain}",
                "-h",  # Host certificate
                "-n", f"{domain}",
                "-V", "+52w",  # Valid for 1 year
                str(tmppath / "host_key.pub")
            ], check=True, capture_output=True)
            
            cert_content = (tmppath / "host_key-cert.pub").read_text()
            key_content = host_key.read_text()
            
            logger.info(f"Self-signed SSH certificate issued for {domain}")
            return cert_content, key_content


class VaultProvider(CertificateProvider):
    """HashiCorp Vault SSH certificate provider."""
    
    def get_name(self) -> str:
        return "vault"
    
    def issue_certificate(self, domain: str) -> tuple[str, str]:
        """Issue SSH certificate via HashiCorp Vault."""
        domain = validate_domain(domain)
        settings = get_settings()
        
        if not hasattr(settings, 'vault_addr') or not hasattr(settings, 'vault_token'):
            raise ValueError("Vault provider requires VAULT_ADDR and VAULT_TOKEN")
        
        # Set Vault environment variables
        env = os.environ.copy()
        env['VAULT_ADDR'] = settings.vault_addr
        env['VAULT_TOKEN'] = settings.vault_token
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Generate SSH key pair
            key_file = tmppath / "id_rsa"
            subprocess.run([
                "ssh-keygen", "-t", "rsa", "-b", "2048",
                "-f", str(key_file), "-N", "", "-C", f"{domain}"
            ], check=True, capture_output=True)
            
            # Sign public key with Vault
            pub_key = (tmppath / "id_rsa.pub").read_text().strip()
            
            # Vault SSH endpoint (adjust path as needed)
            vault_path = getattr(settings, 'vault_ssh_path', 'ssh/sign/default')
            
            result = subprocess.run([
                "vault", "write", "-field=signed_key",
                vault_path,
                f"public_key={pub_key}",
                f"valid_principals={domain}",
                "ttl=8760h"  # 1 year
            ], env=env, check=True, capture_output=True, text=True)
            
            cert_content = result.stdout.strip()
            key_content = key_file.read_text()
            
            logger.info(f"Vault SSH certificate issued for {domain}")
            return cert_content, key_content


class LetsEncryptProvider(CertificateProvider):
    """Let's Encrypt provider via certbot (for TLS/HTTPS certificates)."""
    
    def get_name(self) -> str:
        return "letsencrypt"
    
    def issue_certificate(self, domain: str) -> tuple[str, str]:
        """
        Issue TLS certificate via Let's Encrypt.
        
        Note: This is for HTTPS/TLS certificates, not SSH certificates.
        Requires DNS or HTTP challenge validation.
        """
        domain = validate_domain(domain)
        
        logger.warning("Let's Encrypt issues TLS/HTTPS certificates, not SSH certificates")
        
        # certbot certonly --standalone -d example.com
        # This requires port 80/443 access for HTTP/TLS challenge
        result = subprocess.run([
            "certbot", "certonly",
            "--standalone",
            "--non-interactive",
            "--agree-tos",
            "--email", "admin@example.com",  # Should be configurable
            "-d", domain
        ], check=True, capture_output=True, text=True)
        
        # Certificates are stored in /etc/letsencrypt/live/{domain}/
        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
        
        with open(cert_path, "r") as f:
            cert = f.read()
        with open(key_path, "r") as f:
            key = f.read()
        
        logger.info(f"Let's Encrypt TLS certificate issued for {domain}")
        return cert, key


# Provider registry
PROVIDERS = {
    "step-ca": StepCAProvider,
    "openssh": OpenSSHProvider,
    "vault": VaultProvider,
    "letsencrypt": LetsEncryptProvider,
}


def get_provider(provider_name: Optional[str] = None) -> CertificateProvider:
    """
    Get certificate provider instance.
    
    Args:
        provider_name: Name of provider (step-ca, openssh, vault, letsencrypt)
                      If None, uses CERT_PROVIDER from config
    
    Returns:
        CertificateProvider instance
        
    Raises:
        ValueError: If provider not found
    """
    settings = get_settings()
    
    if provider_name is None:
        provider_name = getattr(settings, 'cert_provider', 'step-ca')
    
    provider_class = PROVIDERS.get(provider_name)
    if not provider_class:
        available = ', '.join(PROVIDERS.keys())
        raise ValueError(f"Unknown provider '{provider_name}'. Available: {available}")
    
    return provider_class()


# Backward compatibility wrapper
def issue_certificate(domain: str) -> tuple[str, str]:
    """
    Issue certificate using configured provider.
    
    Backward compatible with original step_ca.issue_certificate().
    """
    provider = get_provider()
    logger.info(f"Using certificate provider: {provider.get_name()}")
    return provider.issue_certificate(domain)
