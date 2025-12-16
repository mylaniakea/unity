"""Unified model imports for backward compatibility."""
from .core import *
from .monitoring import *
from .users import *
from .plugins import *
from .credentials import *
from .infrastructure import *
from .alert_rules import *
from .containers import *

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
    "ResourceType", "AlertCondition", "AlertSeverity", "AlertStatus", "AlertRule",
    # Containers
    "RuntimeType", "ConnectionType", "ContainerStatus", "UpdateStatus", "RecommendationType",
    "Severity", "PolicyScope", "BackupStatus", "NotificationStatus", "ScanStatus",
    "ContainerHost", "Container", "UpdateCheck", "UpdateHistory", "UpdatePolicy",
    "MaintenanceWindow", "VulnerabilityScan", "ContainerVulnerability", "UpdateNotification",
    "ContainerBackup", "AIRecommendation", "RegistryCredential",
]
from .error_tracking import *
