#!/usr/bin/env python3
"""
Validation script to check tenant filtering coverage across the codebase.
Reports which files/functions need tenant filtering updates.
"""
import os
import re
from collections import defaultdict

BASE = '/home/holon/Projects/unity/backend/app'

TENANT_SCOPED_MODELS = [
    'ServerProfile', 'Settings', 'Report', 'KnowledgeItem', 'ServerSnapshot',
    'ThresholdRule', 'Alert', 'AlertChannel', 'PushSubscription', 'NotificationLog',
    'User', 'Plugin', 'PluginMetric', 'PluginExecution', 'PluginAPIKey',
    'SSHKey', 'Certificate', 'ServerCredential', 'StepCAConfig', 'CredentialAuditLog',
    'KubernetesCluster', 'KubernetesResource', 'ResourceReconciliation',
    'ApplicationBlueprint', 'DeploymentIntent'
]

def check_file(filepath):
    """Check a file for tenant filtering coverage"""
    with open(filepath, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    issues = []
    
    # Check 1: Has get_tenant_id import?
    has_import = 'from app.core.dependencies import get_tenant_id' in content
    
    # Check 2: Find route handlers with db: Session but no tenant_id
    route_pattern = r'@router\.(get|post|put|delete|patch)\('
    for i, line in enumerate(lines):
        if re.search(route_pattern, line):
            # Found a route, check next ~20 lines for function signature
            func_lines = '\n'.join(lines[i:i+20])
            if 'db: Session' in func_lines and 'tenant_id' not in func_lines:
                issues.append({
                    'line': i+1,
                    'type': 'missing_tenant_param',
                    'context': lines[i+1] if i+1 < len(lines) else ''
                })
    
    # Check 3: Find select() queries without .where(tenant_id)
    for i, line in enumerate(lines):
        if 'select(' in line:
            # Check if any model is in this line or next few lines
            context = '\n'.join(lines[i:min(i+3, len(lines))])
            for model in TENANT_SCOPED_MODELS:
                if model in context:
                    # Check if tenant_id filter exists nearby
                    extended = '\n'.join(lines[max(0,i-2):min(i+10, len(lines))])
                    if 'tenant_id' not in extended and '.where(' not in extended:
                        issues.append({
                            'line': i+1,
                            'type': 'missing_tenant_filter',
                            'model': model,
                            'context': line.strip()[:60]
                        })
                    break
    
    return {
        'has_import': has_import,
        'issues': issues
    }

def main():
    print("=" * 80)
    print("TENANT FILTERING VALIDATION REPORT")
    print("=" * 80)
    
    all_files = []
    for subdir in ['routers', 'services']:
        dir_path = os.path.join(BASE, subdir)
        for root, dirs, files in os.walk(dir_path):
            for f in files:
                if f.endswith('.py') and not f.startswith('__'):
                    all_files.append(os.path.join(root, f))
    
    total_files = len(all_files)
    files_with_issues = 0
    total_issues = 0
    
    by_type = defaultdict(int)
    
    print(f"\nScanning {total_files} files...\n")
    
    for filepath in sorted(all_files):
        result = check_file(filepath)
        if result['issues']:
            files_with_issues += 1
            total_issues += len(result['issues'])
            
            rel_path = filepath.replace(BASE + '/', '')
            print(f"⚠️  {rel_path}")
            if not result['has_import']:
                print(f"    - Missing get_tenant_id import")
            
            for issue in result['issues'][:3]:  # Show max 3 per file
                by_type[issue['type']] += 1
                if issue['type'] == 'missing_tenant_param':
                    func_name = issue['context'].strip().split('(')[0].replace('async def ', '').replace('def ', '')
                    print(f"    - Line {issue['line']}: Route handler '{func_name}' needs tenant_id param")
                elif issue['type'] == 'missing_tenant_filter':
                    print(f"    - Line {issue['line']}: Query on {issue['model']} needs tenant filter")
            
            if len(result['issues']) > 3:
                print(f"    ... and {len(result['issues']) - 3} more issues")
            print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files scanned: {total_files}")
    print(f"Files needing updates: {files_with_issues}")
    print(f"Total issues found: {total_issues}")
    print(f"\nBreakdown by type:")
    for issue_type, count in sorted(by_type.items()):
        print(f"  - {issue_type}: {count}")
    
    coverage = ((total_files - files_with_issues) / total_files) * 100 if total_files > 0 else 0
    print(f"\nEstimated coverage: {coverage:.1f}%")
    print("=" * 80)

if __name__ == '__main__':
    main()
