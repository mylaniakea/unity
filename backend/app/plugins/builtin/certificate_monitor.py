"""
Certificate Expiration Monitor Plugin

Monitors SSL/TLS certificate expiration dates and validity.
Prevents the dreaded "certificate expired on Saturday morning" scenario.
"""

import ssl
import socket
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class CertificateMonitorPlugin(PluginBase):
    """Monitors SSL/TLS certificates for expiration and validity"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="certificate-monitor",
            name="Certificate Expiration Monitor",
            version="1.0.0",
            description="Monitors SSL/TLS certificate expiration dates, chain validation, and security status to prevent outages",
            author="Unity Team",
            category=PluginCategory.SECURITY,
            tags=["ssl", "tls", "certificates", "security", "expiration", "https"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=[],  # Uses built-in ssl module
            config_schema={
                "type": "object",
                "properties": {
                    "domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                        "description": "List of domains to monitor (e.g., ['example.com:443', 'api.example.com'])"
                    },
                    "warning_days": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "default": [30, 14, 7, 1],
                        "description": "Days before expiration to trigger warnings"
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "default": 10,
                        "description": "Connection timeout in seconds"
                    },
                    "verify_chain": {
                        "type": "boolean",
                        "default": True,
                        "description": "Verify certificate chain validity"
                    }
                },
                "required": ["domains"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect certificate expiration data for configured domains"""
        
        config = self.config or {}
        domains = config.get("domains", [])
        warning_days = config.get("warning_days", [30, 14, 7, 1])
        timeout = config.get("timeout_seconds", 10)
        verify_chain = config.get("verify_chain", True)
        
        if not domains:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "No domains configured",
                "certificates": []
            }
        
        certificates = []
        errors = []
        
        for domain_spec in domains:
            try:
                cert_info = self._check_certificate(
                    domain_spec, 
                    timeout, 
                    verify_chain
                )
                
                # Add warning level based on days until expiration
                days_until_expiry = cert_info.get("days_until_expiry")
                if days_until_expiry is not None:
                    cert_info["warning_level"] = self._get_warning_level(
                        days_until_expiry, 
                        warning_days
                    )
                
                certificates.append(cert_info)
                
            except Exception as e:
                error_entry = {
                    "domain": domain_spec,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                errors.append(error_entry)
        
        # Summary statistics
        total = len(certificates)
        expired = sum(1 for c in certificates if c.get("expired", False))
        critical = sum(1 for c in certificates if c.get("warning_level") == "critical")
        warning = sum(1 for c in certificates if c.get("warning_level") == "warning")
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_certificates": total,
                "expired": expired,
                "critical_warnings": critical,
                "warnings": warning,
                "healthy": total - expired - critical - warning,
                "errors": len(errors)
            },
            "certificates": certificates,
            "errors": errors if errors else None
        }
    
    def _check_certificate(
        self, 
        domain_spec: str, 
        timeout: int,
        verify_chain: bool
    ) -> Dict[str, Any]:
        """Check a single certificate"""
        
        # Parse domain and port
        host, port = self._parse_domain(domain_spec)
        
        # Create SSL context
        context = ssl.create_default_context()
        if not verify_chain:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        
        # Connect and get certificate
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                cert_binary = ssock.getpeercert_bin()
                
                # Parse certificate details
                return self._parse_certificate(host, port, cert, cert_binary)
    
    def _parse_domain(self, domain_spec: str) -> tuple:
        """Parse domain specification into host and port"""
        
        # Handle URLs
        if "://" in domain_spec:
            parsed = urlparse(domain_spec)
            host = parsed.hostname
            port = parsed.port or 443
        # Handle host:port format
        elif ":" in domain_spec:
            host, port_str = domain_spec.rsplit(":", 1)
            port = int(port_str)
        # Just hostname
        else:
            host = domain_spec
            port = 443
        
        return host, port
    
    def _parse_certificate(
        self, 
        host: str, 
        port: int, 
        cert: Dict[str, Any],
        cert_binary: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Parse certificate information"""
        
        # Extract expiration date
        not_after = cert.get("notAfter")
        not_before = cert.get("notBefore")
        
        # Parse dates
        expiry_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
        expiry_date = expiry_date.replace(tzinfo=timezone.utc)
        
        start_date = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z")
        start_date = start_date.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        days_until_expiry = (expiry_date - now).days
        
        # Extract subject and issuer
        subject = dict(x[0] for x in cert.get("subject", []))
        issuer = dict(x[0] for x in cert.get("issuer", []))
        
        # Check if Let's Encrypt
        is_letsencrypt = "Let's Encrypt" in issuer.get("organizationName", "")
        
        # Extract SANs (Subject Alternative Names)
        san_list = []
        for san_type, san_value in cert.get("subjectAltName", []):
            if san_type == "DNS":
                san_list.append(san_value)
        
        return {
            "domain": f"{host}:{port}",
            "common_name": subject.get("commonName", host),
            "issuer": issuer.get("organizationName", "Unknown"),
            "issuer_cn": issuer.get("commonName", "Unknown"),
            "is_letsencrypt": is_letsencrypt,
            "valid_from": start_date.isoformat(),
            "valid_until": expiry_date.isoformat(),
            "days_until_expiry": days_until_expiry,
            "expired": days_until_expiry < 0,
            "subject_alternative_names": san_list,
            "serial_number": cert.get("serialNumber"),
            "version": cert.get("version"),
            "checked_at": now.isoformat()
        }
    
    def _get_warning_level(self, days_until_expiry: int, warning_days: List[int]) -> str:
        """Determine warning level based on days until expiry"""
        
        if days_until_expiry < 0:
            return "expired"
        
        # Sort warning days to find the appropriate level
        sorted_days = sorted(warning_days, reverse=True)
        
        for threshold in sorted_days:
            if days_until_expiry <= threshold:
                if threshold <= 7:
                    return "critical"
                elif threshold <= 14:
                    return "warning"
                else:
                    return "info"
        
        return "healthy"
    
    async def health_check(self) -> bool:
        """Check if the plugin is healthy"""
        # Plugin is healthy if we can perform basic SSL operations
        try:
            context = ssl.create_default_context()
            return True
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        
        if not config:
            return False
        
        domains = config.get("domains", [])
        if not domains or not isinstance(domains, list):
            return False
        
        # Validate each domain
        for domain in domains:
            if not isinstance(domain, str) or not domain.strip():
                return False
        
        return True
