"""Security policy evaluation engine."""

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

import app.models as models

logger = logging.getLogger(__name__)


class SecurityPolicyEngine:
    """Evaluates security policies and determines if updates should proceed."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def evaluate_update(
        self,
        container: models.Container,
        new_scan: models.VulnerabilityScan,
        old_scan: Optional[models.VulnerabilityScan] = None
    ) -> Dict[str, Any]:
        """Evaluate if an update should be allowed based on security policy.
        
        Args:
            container: Container being updated
            new_scan: Scan of the new image
            old_scan: Scan of the current image (if available)
            
        Returns:
            Dict with 'allowed' (bool), 'reason' (str), and 'violations' (list)
        """
        # Get applicable policy
        policy = self._get_policy_for_container(container)
        
        if not policy or not policy.scan_before_update:
            return {
                'allowed': True,
                'reason': 'No security policy enforced',
                'violations': []
            }
        
        violations = []
        
        # Check if scan failed
        if new_scan.scan_status != 'success':
            violations.append({
                'rule': 'scan_required',
                'severity': 'critical',
                'message': f'Security scan failed: {new_scan.error_message or "Unknown error"}'
            })
        
        # Check critical CVEs
        if policy.block_critical_cves and new_scan.critical_count > 0:
            # Filter out exceptions
            exceptions = policy.cve_exceptions or []
            critical_cves = [
                v for v in new_scan.vulnerabilities 
                if v.get('severity') == 'critical' and v.get('cve_id') not in exceptions
            ]
            
            if critical_cves:
                violations.append({
                    'rule': 'block_critical_cves',
                    'severity': 'critical',
                    'message': f'{len(critical_cves)} critical CVE(s) found',
                    'cves': [c.get('cve_id') for c in critical_cves[:5]]  # Limit to 5
                })
        
        # Check high severity threshold
        if policy.max_high_severity is not None:
            exceptions = policy.cve_exceptions or []
            high_cves = [
                v for v in new_scan.vulnerabilities 
                if v.get('severity') == 'high' and v.get('cve_id') not in exceptions
            ]
            
            if len(high_cves) > policy.max_high_severity:
                violations.append({
                    'rule': 'max_high_severity',
                    'severity': 'high',
                    'message': f'{len(high_cves)} high severity CVEs exceeds limit of {policy.max_high_severity}',
                    'count': len(high_cves),
                    'limit': policy.max_high_severity
                })
        
        # Check for security regression
        if policy.block_security_regression and old_scan:
            regression = self._check_regression(old_scan, new_scan, policy.cve_exceptions or [])
            if regression['is_regression']:
                violations.append({
                    'rule': 'security_regression',
                    'severity': 'high',
                    'message': regression['message'],
                    'details': regression
                })
        
        # Check for secrets
        if new_scan.secrets_found:
            violations.append({
                'rule': 'secrets_found',
                'severity': 'critical',
                'message': f'{len(new_scan.secrets_found)} secret(s) found in image',
                'secrets': [s.get('category') for s in new_scan.secrets_found[:5]]
            })
        
        # Determine if allowed
        allowed = len(violations) == 0
        
        # Generate summary reason
        if allowed:
            reason = f'Security check passed (Score: {new_scan.security_score or "N/A"}/100)'
        else:
            critical_violations = [v for v in violations if v['severity'] == 'critical']
            if critical_violations:
                reason = f"Blocked: {critical_violations[0]['message']}"
            else:
                reason = f"Blocked: {violations[0]['message']}"
        
        return {
            'allowed': allowed,
            'reason': reason,
            'violations': violations,
            'policy_id': policy.id if policy else None,
            'scan_id': new_scan.id
        }
    
    def _get_policy_for_container(self, container: models.Container) -> Optional[models.UpdatePolicy]:
        """Get the applicable update policy for a container.
        
        Hierarchy: Container-specific > Host-specific > Global
        """
        # Container-specific policy
        policy = self.db.query(models.UpdatePolicy).filter(
            models.UpdatePolicy.container_id == container.id,
            models.UpdatePolicy.enabled == True
        ).first()
        
        if policy:
            return policy
        
        # Host-specific policy
        policy = self.db.query(models.UpdatePolicy).filter(
            models.UpdatePolicy.host_id == container.host_id,
            models.UpdatePolicy.scope == 'host',
            models.UpdatePolicy.enabled == True
        ).first()
        
        if policy:
            return policy
        
        # Global policy
        policy = self.db.query(models.UpdatePolicy).filter(
            models.UpdatePolicy.scope == 'global',
            models.UpdatePolicy.enabled == True
        ).order_by(models.UpdatePolicy.priority.desc()).first()
        
        return policy
    
    def _check_regression(
        self,
        old_scan: models.VulnerabilityScan,
        new_scan: models.VulnerabilityScan,
        exceptions: List[str]
    ) -> Dict[str, Any]:
        """Check if new scan represents a security regression."""
        regression = {
            'is_regression': False,
            'message': '',
            'score_change': 0,
            'critical_change': 0,
            'high_change': 0,
            'new_critical_cves': []
        }
        
        # Calculate changes
        score_change = (new_scan.security_score or 0) - (old_scan.security_score or 0)
        critical_change = new_scan.critical_count - old_scan.critical_count
        high_change = new_scan.high_count - old_scan.high_count
        
        regression['score_change'] = score_change
        regression['critical_change'] = critical_change
        regression['high_change'] = high_change
        
        # Find new critical CVEs (not in exceptions)
        old_critical_cves = {
            v.get('cve_id') for v in old_scan.vulnerabilities 
            if v.get('severity') == 'critical'
        }
        new_critical_cves = {
            v.get('cve_id') for v in new_scan.vulnerabilities 
            if v.get('severity') == 'critical' and v.get('cve_id') not in exceptions
        }
        
        truly_new_criticals = list(new_critical_cves - old_critical_cves)
        regression['new_critical_cves'] = truly_new_criticals
        
        # Determine if regression
        if truly_new_criticals:
            regression['is_regression'] = True
            regression['message'] = f'New critical CVE(s): {", ".join(truly_new_criticals[:3])}'
        elif score_change < -15:  # Significant score drop
            regression['is_regression'] = True
            regression['message'] = f'Security score dropped by {abs(score_change)} points'
        elif critical_change > 0 or (high_change > 5):  # More vulnerabilities
            regression['is_regression'] = True
            regression['message'] = f'Vulnerability count increased (Critical: +{critical_change}, High: +{high_change})'
        
        return regression
    
    def get_security_summary(self, container_id: int) -> Dict[str, Any]:
        """Get security summary for a container.
        
        Returns:
            Dict with latest scan info and trends
        """
        container = self.db.query(models.Container).filter(
            models.Container.id == container_id
        ).first()
        
        if not container:
            return {'error': 'Container not found'}
        
        # Get latest scan
        latest_scan = self.db.query(models.VulnerabilityScan).filter(
            models.VulnerabilityScan.container_id == container_id
        ).order_by(models.VulnerabilityScan.scanned_at.desc()).first()
        
        if not latest_scan:
            return {
                'container_id': container_id,
                'security_score': None,
                'status': 'never_scanned',
                'message': 'No security scans performed yet'
            }
        
        # Get scan history for trends
        recent_scans = self.db.query(models.VulnerabilityScan).filter(
            models.VulnerabilityScan.container_id == container_id
        ).order_by(models.VulnerabilityScan.scanned_at.desc()).limit(5).all()
        
        # Calculate trend
        trend = 'stable'
        if len(recent_scans) >= 2:
            score_diff = (latest_scan.security_score or 0) - (recent_scans[1].security_score or 0)
            if score_diff > 10:
                trend = 'improving'
            elif score_diff < -10:
                trend = 'degrading'
        
        return {
            'container_id': container_id,
            'security_score': latest_scan.security_score,
            'critical_count': latest_scan.critical_count,
            'high_count': latest_scan.high_count,
            'total_vulnerabilities': latest_scan.total_count,
            'secrets_found': len(latest_scan.secrets_found or []),
            'last_scanned': latest_scan.scanned_at.isoformat() if latest_scan.scanned_at else None,
            'trend': trend,
            'status': 'critical' if latest_scan.critical_count > 0 else 'warning' if latest_scan.high_count > 5 else 'good',
            'scan_id': latest_scan.id
        }
