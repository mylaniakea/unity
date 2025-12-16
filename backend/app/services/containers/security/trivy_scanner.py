"""Trivy vulnerability scanner integration."""

import json
import logging
import shutil
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

import app.models as models

logger = logging.getLogger(__name__)


class TrivyScanner:
    """Wrapper for Trivy vulnerability scanner."""
    
    def __init__(self, db: Session, use_docker: bool = False):
        """Initialize Trivy scanner.
        
        Args:
            db: Database session
            use_docker: If True, use Trivy Docker image instead of binary
        """
        self.db = db
        self.use_docker = use_docker
        self._trivy_available = None
    
    def is_available(self) -> bool:
        """Check if Trivy is available."""
        if self._trivy_available is not None:
            return self._trivy_available
        
        if self.use_docker:
            # Check if Docker is available
            self._trivy_available = shutil.which('docker') is not None
        else:
            # Check if Trivy binary is available
            self._trivy_available = shutil.which('trivy') is not None
        
        return self._trivy_available
    
    def scan_image(
        self,
        image: str,
        container_id: Optional[int] = None,
        scan_type: str = "manual",
        timeout: int = 300
    ) -> models.VulnerabilityScan:
        """Scan an image for vulnerabilities.
        
        Args:
            image: Image name with tag (e.g., "nginx:latest")
            container_id: Optional container ID to associate scan with
            scan_type: Type of scan ('pre-update', 'post-update', 'scheduled', 'manual')
            timeout: Scan timeout in seconds
            
        Returns:
            VulnerabilityScan model with results
        """
        if not self.is_available():
            raise RuntimeError("Trivy is not available. Install with: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin")
        
        logger.info(f"Scanning image: {image}")
        start_time = time.time()
        
        try:
            # Execute Trivy scan
            scan_result = self._execute_scan(image, timeout)
            duration = time.time() - start_time
            
            # Parse results
            vulnerabilities, counts = self._parse_vulnerabilities(scan_result)
            secrets = self._parse_secrets(scan_result)
            misconfigs = self._parse_misconfigurations(scan_result)
            
            # Calculate security score
            security_score = self._calculate_security_score(counts, len(secrets))
            
            # Get scanner version
            scanner_version = self._get_trivy_version()
            
            # Create scan record
            scan = models.VulnerabilityScan(
                container_id=container_id,
                image=image,
                scan_type=scan_type,
                scanner="trivy",
                scanner_version=scanner_version,
                critical_count=counts['critical'],
                high_count=counts['high'],
                medium_count=counts['medium'],
                low_count=counts['low'],
                unknown_count=counts['unknown'],
                total_count=counts['total'],
                scan_duration_seconds=duration,
                scan_status="success",
                vulnerabilities=vulnerabilities,
                secrets_found=secrets,
                misconfigurations=misconfigs,
                scanned_at=datetime.utcnow()
            )
            
            # Save to database
            self.db.add(scan)
            self.db.commit()
            self.db.refresh(scan)
            
            # Update container if provided
            if container_id:
                container = self.db.query(models.Container).filter(
                    models.Container.id == container_id
                ).first()
                if container:
                    container.last_scan_id = scan.id
                    container.security_score = security_score
                    container.critical_cves = counts['critical']
                    container.high_cves = counts['high']
                    container.last_scanned_at = datetime.utcnow()
                    self.db.commit()
            
            logger.info(f"Scan completed: {counts['total']} vulnerabilities found (Critical: {counts['critical']}, High: {counts['high']})")
            return scan
            
        except subprocess.TimeoutExpired:
            logger.error(f"Scan timeout after {timeout}s for image: {image}")
            scan = models.VulnerabilityScan(
                container_id=container_id,
                image=image,
                scan_type=scan_type,
                scanner="trivy",
                scan_duration_seconds=timeout,
                scan_status="timeout",
                error_message=f"Scan exceeded {timeout}s timeout"
            )
            self.db.add(scan)
            self.db.commit()
            self.db.refresh(scan)
            return scan
            
        except Exception as e:
            logger.error(f"Scan failed for image {image}: {e}")
            scan = models.VulnerabilityScan(
                container_id=container_id,
                image=image,
                scan_type=scan_type,
                scanner="trivy",
                scan_duration_seconds=time.time() - start_time,
                scan_status="failed",
                error_message=str(e)
            )
            self.db.add(scan)
            self.db.commit()
            self.db.refresh(scan)
            return scan
    
    def _execute_scan(self, image: str, timeout: int) -> Dict[str, Any]:
        """Execute Trivy scan and return JSON results."""
        if self.use_docker:
            cmd = [
                'docker', 'run', '--rm',
                '-v', '/var/run/docker.sock:/var/run/docker.sock',
                'aquasec/trivy:latest',
                'image', '--format', 'json', '--quiet', image
            ]
        else:
            cmd = ['trivy', 'image', '--format', 'json', '--quiet', image]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )
        
        return json.loads(result.stdout)
    
    def _parse_vulnerabilities(self, scan_result: Dict[str, Any]) -> tuple[List[Dict], Dict[str, int]]:
        """Parse vulnerabilities from Trivy output."""
        vulnerabilities = []
        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'unknown': 0, 'total': 0}
        
        results = scan_result.get('Results', [])
        for result in results:
            vulns = result.get('Vulnerabilities', [])
            for vuln in vulns:
                severity = vuln.get('Severity', 'UNKNOWN').lower()
                counts[severity] = counts.get(severity, 0) + 1
                counts['total'] += 1
                
                vulnerabilities.append({
                    'cve_id': vuln.get('VulnerabilityID'),
                    'package': vuln.get('PkgName'),
                    'installed_version': vuln.get('InstalledVersion'),
                    'fixed_version': vuln.get('FixedVersion'),
                    'severity': severity,
                    'title': vuln.get('Title'),
                    'description': vuln.get('Description'),
                    'references': vuln.get('References', []),
                    'cvss_score': vuln.get('CVSS', {}).get('nvd', {}).get('V3Score')
                })
        
        return vulnerabilities, counts
    
    def _parse_secrets(self, scan_result: Dict[str, Any]) -> List[Dict]:
        """Parse secrets found in the image."""
        secrets = []
        results = scan_result.get('Results', [])
        for result in results:
            found_secrets = result.get('Secrets', [])
            for secret in found_secrets:
                secrets.append({
                    'rule_id': secret.get('RuleID'),
                    'category': secret.get('Category'),
                    'severity': secret.get('Severity', 'UNKNOWN').lower(),
                    'title': secret.get('Title'),
                    'match': secret.get('Match')[:100]  # Truncate for safety
                })
        return secrets
    
    def _parse_misconfigurations(self, scan_result: Dict[str, Any]) -> List[Dict]:
        """Parse misconfigurations found in the image."""
        misconfigs = []
        results = scan_result.get('Results', [])
        for result in results:
            configs = result.get('Misconfigurations', [])
            for config in configs:
                misconfigs.append({
                    'id': config.get('ID'),
                    'title': config.get('Title'),
                    'severity': config.get('Severity', 'UNKNOWN').lower(),
                    'message': config.get('Message'),
                    'resolution': config.get('Resolution')
                })
        return misconfigs
    
    def _calculate_security_score(self, counts: Dict[str, int], secrets_count: int) -> int:
        """Calculate 0-100 security score.
        
        100 = No vulnerabilities
        0 = Critical vulnerabilities or secrets found
        """
        score = 100
        
        # Penalize by severity
        score -= counts.get('critical', 0) * 20
        score -= counts.get('high', 0) * 5
        score -= counts.get('medium', 0) * 1
        score -= counts.get('low', 0) * 0.1
        
        # Secrets are critical
        score -= secrets_count * 25
        
        return max(0, min(100, int(score)))
    
    def _get_trivy_version(self) -> str:
        """Get Trivy version."""
        try:
            if self.use_docker:
                cmd = ['docker', 'run', '--rm', 'aquasec/trivy:latest', '--version']
            else:
                cmd = ['trivy', '--version']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.stdout.strip().split('\n')[0]
        except Exception:
            return "unknown"
    
    def compare_scans(
        self,
        old_scan: models.VulnerabilityScan,
        new_scan: models.VulnerabilityScan
    ) -> Dict[str, Any]:
        """Compare two scans to detect security regression.
        
        Returns:
            Dict with comparison results and regression flag
        """
        comparison = {
            'is_regression': False,
            'score_change': new_scan.security_score - (old_scan.security_score or 0) if new_scan.security_score and old_scan.security_score else 0,
            'critical_change': new_scan.critical_count - old_scan.critical_count,
            'high_change': new_scan.high_count - old_scan.high_count,
            'total_change': new_scan.total_count - old_scan.total_count,
            'new_criticals': [],
            'fixed_criticals': []
        }
        
        # Check for regression
        if comparison['critical_change'] > 0 or comparison['score_change'] < -10:
            comparison['is_regression'] = True
        
        # Find new critical CVEs
        old_cves = {v['cve_id'] for v in old_scan.vulnerabilities if v.get('severity') == 'critical'}
        new_cves = {v['cve_id'] for v in new_scan.vulnerabilities if v.get('severity') == 'critical'}
        
        comparison['new_criticals'] = list(new_cves - old_cves)
        comparison['fixed_criticals'] = list(old_cves - new_cves)
        
        return comparison
