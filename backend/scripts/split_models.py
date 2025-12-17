#!/usr/bin/env python3
"""Script to split models.py into organized domain modules."""
import re
from pathlib import Path

models_file = Path("app/models.py")
models_dir = Path("app/models")

# Read the entire models.py
with open(models_file) as f:
    content = f.read()

# Extract imports (everything before first class)
imports_match = re.search(r'^(.*?)(?=class\s+\w+)', content, re.DOTALL)
base_imports = imports_match.group(1) if imports_match else ""

# Model mappings by domain
domains = {
    "core.py": ["ServerProfile", "Settings", "Report", "KnowledgeItem", "ServerSnapshot"],
    "monitoring.py": ["ThresholdRule", "Alert", "AlertChannel", "PushSubscription", "NotificationLog"],
    "users.py": ["User"],
    "plugins.py": ["Plugin", "PluginMetric", "PluginExecution", "PluginAPIKey"],
    "credentials.py": ["SSHKey", "Certificate", "ServerCredential", "StepCAConfig", "CredentialAuditLog"],
    "infrastructure.py": [
        "ServerStatus", "DeviceType", "HealthStatus", "PoolType", "DatabaseType", "DatabaseStatus",
        "MonitoredServer", "StorageDevice", "StoragePool", "DatabaseInstance"
    ],
    "alert_rules.py": [
        "ResourceType", "AlertCondition", "AlertSeverity", "AlertStatus", "AlertRule"
    ]
}

# Extract each class definition
def extract_class(content, class_name):
    # Pattern to match class definition until next class or end
    pattern = rf'(^class {class_name}[^\n]*\n(?:.*?\n)*?)(?=^class\s+\w+|\Z)'
    match = re.search(pattern, content, re.MULTILINE)
    return match.group(1).rstrip() + "\n" if match else None

# Create each domain file
for filename, class_names in domains.items():
    filepath = models_dir / filename
    with open(filepath, 'w') as f:
        f.write(base_imports)
        f.write("\n\n")
        
        for class_name in class_names:
            class_def = extract_class(content, class_name)
            if class_def:
                f.write(class_def)
                f.write("\n\n")
    
    print(f"✅ Created {filename} with {len(class_names)} models")

# Create __init__.py that imports everything
init_content = '''"""Unified model imports for backward compatibility."""
from .core import *
from .monitoring import *
from .users import *
from .plugins import *
from .credentials import *
from .infrastructure import *
from .alert_rules import *

__all__ = [
    # Core
    "ServerProfile", "Settings", "Report", "KnowledgeItem", "ServerSnapshot",
    # Monitoring
    "ThresholdRule", "Alert", "AlertChannel", "PushSubscription", "NotificationLog",
    # Users
    "User",
    # Plugins
    "Plugin", "PluginMetric", "PluginExecution", "PluginAPIKey",
    # Credentials
    "SSHKey", "Certificate", "ServerCredential", "StepCAConfig", "CredentialAuditLog",
    # Infrastructure
    "ServerStatus", "DeviceType", "HealthStatus", "PoolType", "DatabaseType", "DatabaseStatus",
    "MonitoredServer", "StorageDevice", "StoragePool", "DatabaseInstance",
    # Alert Rules
    "ResourceType", "AlertCondition", "AlertSeverity", "AlertStatus", "AlertRule"
]
'''

with open(models_dir / "__init__.py", 'w') as f:
    f.write(init_content)

print("✅ Created __init__.py with all exports")
print("\n✅ Model split complete! Run 'mv app/models.py app/models_old.py' to backup original.")
