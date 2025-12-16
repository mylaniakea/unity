"""Container management models for Uptainer integration."""
import enum
from sqlalchemy import BigInteger, Enum, Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class RuntimeType(str, enum.Enum):
    """Container runtime type."""
    DOCKER = "docker"
    PODMAN = "podman"
    KUBERNETES = "kubernetes"


class ConnectionType(str, enum.Enum):
    """Host connection type."""
    SOCKET = "socket"
    TCP = "tcp"
    SSH = "ssh"


class ContainerStatus(str, enum.Enum):
    """Container runtime status."""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    RESTARTING = "restarting"
    DEAD = "dead"
    CREATED = "created"
    EXITED = "exited"
    UNKNOWN = "unknown"


class UpdateStatus(str, enum.Enum):
    """Update execution status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RecommendationType(str, enum.Enum):
    """AI recommendation type."""
    UPDATE = "update"
    HOLD = "hold"
    REVIEW = "review"
    CONFIG_CHANGE = "config_change"


class Severity(str, enum.Enum):
    """Severity level for recommendations and vulnerabilities."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyScope(str, enum.Enum):
    """Update policy scope."""
    GLOBAL = "global"
    HOST = "host"
    CONTAINER = "container"


class BackupStatus(str, enum.Enum):
    """Backup execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationStatus(str, enum.Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class ScanStatus(str, enum.Enum):
    """Vulnerability scan status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ContainerHost(Base):
    """Container host configuration (Docker, Podman, Kubernetes)."""
    __tablename__ = "container_hosts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Link to BD-Store's MonitoredServer for infrastructure integration
    monitored_server_id = Column(Integer, ForeignKey('monitored_servers.id'), nullable=True, index=True)
    
    # Connection Configuration
    connection_type = Column(Enum(ConnectionType), default=ConnectionType.SOCKET)
    connection_string = Column(String)  # e.g., "unix:///var/run/docker.sock", "tcp://host:2376"
    
    # Runtime Configuration
    runtime_type = Column(Enum(RuntimeType), default=RuntimeType.DOCKER)
    
    # Kubernetes-specific Configuration
    kubeconfig_path = Column(String, nullable=True)
    namespace = Column(String, default="default", nullable=True)
    context = Column(String, nullable=True)
    
    # Multi-namespace Configuration
    namespaces = Column(JSONB, default=lambda: ["default"])  # Array of namespaces to scan
    namespace_selector = Column(String, nullable=True)  # Label selector for namespaces
    namespace_exclude = Column(JSONB, default=lambda: [])  # Namespaces to exclude
    gitops_tool = Column(String, nullable=True)  # 'argocd', 'flux', or null
    gitops_config = Column(JSONB, default=lambda: {})  # GitOps tool configuration
    
    # SSH Configuration (if connection_type == "ssh")
    ssh_host = Column(String, nullable=True)
    ssh_port = Column(Integer, default=22, nullable=True)
    ssh_username = Column(String, nullable=True)
    ssh_key_path = Column(String, nullable=True)
    
    # TLS Configuration (if connection_type == "tcp")
    tls_enabled = Column(Boolean, default=False)
    tls_verify = Column(Boolean, default=True)
    tls_cert_path = Column(String, nullable=True)
    
    # Status
    enabled = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="unknown")  # "online", "offline", "error", "unknown"
    status_message = Column(Text, nullable=True)
    
    # Security Policy Fields
    block_critical_cves = Column(Boolean, default=True)
    max_high_severity = Column(Integer, default=10)
    block_security_regression = Column(Boolean, default=True)
    scan_before_update = Column(Boolean, default=True)
    cve_exceptions = Column(JSONB, default=lambda: [])  # List of CVE IDs to ignore
    
    # Metadata
    host_info = Column(JSONB, default=lambda: {})  # Docker version, OS, architecture, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    monitored_server = relationship("MonitoredServer", foreign_keys=[monitored_server_id])
    containers = relationship("Container", back_populates="host", cascade="all, delete-orphan")
    update_policies = relationship("UpdatePolicy", back_populates="host", cascade="all, delete-orphan")


class Container(Base):
    """Container state and metadata."""
    __tablename__ = "containers"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(String, index=True)  # Docker/Podman container ID
    host_id = Column(Integer, ForeignKey('container_hosts.id'), index=True, nullable=False)
    
    # Container Info
    name = Column(String, index=True, nullable=False)
    image = Column(String, index=True)
    image_id = Column(String)
    status = Column(Enum(ContainerStatus), default=ContainerStatus.UNKNOWN)
    
    # Image Version Info
    current_tag = Column(String)
    current_digest = Column(String, nullable=True)
    available_tag = Column(String, nullable=True)
    available_digest = Column(String, nullable=True)
    update_available = Column(Boolean, default=False)
    
    # Container Configuration
    labels = Column(JSONB, default=lambda: {})
    environment = Column(JSONB, default=lambda: {})
    ports = Column(JSONB, default=lambda: {})
    volumes = Column(JSONB, default=lambda: {})
    networks = Column(JSONB, default=lambda: [])
    
    # Kubernetes & Helm Fields
    namespace = Column(String, nullable=True)  # K8s namespace
    resource_type = Column(String, default="deployment")  # deployment/statefulset/daemonset/crd
    crd_group = Column(String, nullable=True)  # For CRDs
    crd_version = Column(String, nullable=True)  # For CRDs
    helm_release = Column(String, nullable=True)  # Helm release name
    helm_chart = Column(String, nullable=True)  # Chart name
    helm_chart_version = Column(String, nullable=True)  # Chart version
    helm_values = Column(JSONB, default=lambda: {})  # Custom values
    helm_revision = Column(Integer, nullable=True)  # Helm revision number
    dependencies = Column(JSONB, default=lambda: [])  # Dependent service IDs
    
    # Security Fields
    last_scan_id = Column(Integer, ForeignKey("vulnerability_scans.id"), nullable=True)
    security_score = Column(Integer, nullable=True)  # 0-100, lower is worse
    critical_cves = Column(Integer, default=0)
    high_cves = Column(Integer, default=0)
    last_scanned_at = Column(DateTime(timezone=True), nullable=True)
    
    # Update Policy
    auto_update = Column(Boolean, default=False)
    update_schedule = Column(String, nullable=True)  # Cron expression
    exclude_from_updates = Column(Boolean, default=False)
    
    # Timestamps
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_checked = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    host = relationship("ContainerHost", back_populates="containers")
    update_checks = relationship("UpdateCheck", back_populates="container", cascade="all, delete-orphan")
    update_history = relationship("UpdateHistory", back_populates="container", cascade="all, delete-orphan")
    vulnerability_scans = relationship("VulnerabilityScan", back_populates="container", foreign_keys="[VulnerabilityScan.container_id]", cascade="all, delete-orphan")
    backups = relationship("ContainerBackup", back_populates="container", cascade="all, delete-orphan")
    recommendations = relationship("AIRecommendation", back_populates="container", cascade="all, delete-orphan")
    notifications = relationship("UpdateNotification", back_populates="container", cascade="all, delete-orphan")


class UpdateCheck(Base):
    """History of update checks performed."""
    __tablename__ = "update_checks"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(Integer, ForeignKey('containers.id'), index=True, nullable=False)
    
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    update_available = Column(Boolean, default=False)
    
    current_tag = Column(String)
    current_digest = Column(String, nullable=True)
    available_tag = Column(String, nullable=True)
    available_digest = Column(String, nullable=True)
    
    # Registry response data
    registry_data = Column(JSONB, default=lambda: {})
    
    # Relationships
    container = relationship("Container", back_populates="update_checks")


class UpdateHistory(Base):
    """Container update execution history."""
    __tablename__ = "update_history"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(Integer, ForeignKey('containers.id'), index=True, nullable=False)
    
    # Update Details
    from_tag = Column(String)
    from_digest = Column(String, nullable=True)
    to_tag = Column(String)
    to_digest = Column(String, nullable=True)
    
    # Execution Status
    status = Column(Enum(UpdateStatus), default=UpdateStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Results
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    execution_log = Column(Text, nullable=True)
    
    # Backup & Rollback
    backup_id = Column(Integer, ForeignKey('container_backups.id'), nullable=True)
    rollback_available = Column(Boolean, default=False)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    triggered_by = Column(String, nullable=True)  # "manual", "auto", "policy", "user:id"
    dry_run = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    container = relationship("Container", back_populates="update_history")
    backup = relationship("ContainerBackup", foreign_keys=[backup_id])


class UpdatePolicy(Base):
    """Automated update policies."""
    __tablename__ = "update_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Scope
    scope = Column(Enum(PolicyScope), default=PolicyScope.GLOBAL)
    host_id = Column(Integer, ForeignKey('container_hosts.id'), nullable=True, index=True)
    container_id = Column(Integer, ForeignKey('containers.id'), nullable=True, index=True)
    
    # Container Selection (for global/host scope)
    image_pattern = Column(String, nullable=True)  # Regex pattern to match image names
    label_selector = Column(JSONB, default=lambda: {})  # Label-based selection
    namespace_pattern = Column(String, nullable=True)  # K8s namespace pattern
    
    # Update Rules
    auto_approve = Column(Boolean, default=False)
    require_ai_approval = Column(Boolean, default=False)
    allowed_versions = Column(String, nullable=True)  # Version constraint (e.g., "^1.0.0")
    exclude_versions = Column(JSONB, default=lambda: [])  # Versions to skip
    
    # Scheduling
    maintenance_window_id = Column(Integer, ForeignKey('maintenance_windows.id'), nullable=True)
    update_schedule = Column(String, nullable=True)  # Cron expression
    
    # Notifications
    notify_on_update = Column(Boolean, default=True)
    notify_on_failure = Column(Boolean, default=True)
    notification_channels = Column(JSONB, default=lambda: [])
    
    # Security
    require_security_scan = Column(Boolean, default=False)
    block_critical_cves = Column(Boolean, default=True)
    max_high_severity = Column(Integer, default=10)
    
    # Priority
    priority = Column(Integer, default=100)  # Higher number = higher priority
    
    # Status
    enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    host = relationship("ContainerHost", back_populates="update_policies")
    container = relationship("Container", foreign_keys=[container_id])
    maintenance_window = relationship("MaintenanceWindow", back_populates="policies")


class MaintenanceWindow(Base):
    """Scheduled maintenance windows for updates."""
    __tablename__ = "maintenance_windows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Schedule
    cron_expression = Column(String, nullable=True)  # Cron schedule
    start_time = Column(DateTime(timezone=True), nullable=True)  # One-time start
    end_time = Column(DateTime(timezone=True), nullable=True)  # One-time end
    duration_minutes = Column(Integer, nullable=True)  # Duration for cron-based windows
    
    # Timezone
    timezone = Column(String, default="UTC")
    
    # Security Requirements
    block_critical_cves = Column(Boolean, default=True)
    max_high_severity = Column(Integer, default=10)
    require_approval = Column(Boolean, default=False)
    
    # Status
    enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    policies = relationship("UpdatePolicy", back_populates="maintenance_window")


class VulnerabilityScan(Base):
    """Container vulnerability scan results (Trivy)."""
    __tablename__ = "vulnerability_scans"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(Integer, ForeignKey('containers.id'), index=True, nullable=False)
    
    # Scan Info
    scanner = Column(String, default="trivy")
    scanner_version = Column(String, nullable=True)
    scanned_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Image Info
    image = Column(String)
    image_digest = Column(String, nullable=True)
    
    # Vulnerability Counts
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    
    # Security Score
    security_score = Column(Integer, nullable=True)  # 0-100, lower is worse
    
    # Scan Status
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING)
    error_message = Column(Text, nullable=True)
    
    # Full Results
    scan_results = Column(JSONB, default=lambda: {})  # Complete Trivy JSON output
    
    # AI Analysis
    ai_summary = Column(Text, nullable=True)
    ai_risk_level = Column(Enum(Severity), nullable=True)
    ai_recommendations = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    container = relationship("Container", back_populates="vulnerability_scans")
    vulnerabilities = relationship("ContainerVulnerability", back_populates="scan", cascade="all, delete-orphan")


class ContainerVulnerability(Base):
    """Individual CVE records from scans."""
    __tablename__ = "container_vulnerabilities"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey('vulnerability_scans.id'), index=True, nullable=False)
    
    # CVE Info
    cve_id = Column(String, index=True)
    severity = Column(Enum(Severity))
    
    # Package Info
    package_name = Column(String)
    installed_version = Column(String)
    fixed_version = Column(String, nullable=True)
    
    # Details
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    references = Column(JSONB, default=lambda: [])
    
    # CVSS Scores
    cvss_score = Column(Float, nullable=True)
    cvss_vector = Column(String, nullable=True)
    
    # Status
    ignored = Column(Boolean, default=False)
    ignore_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    scan = relationship("VulnerabilityScan", back_populates="vulnerabilities")


class UpdateNotification(Base):
    """Container update notifications."""
    __tablename__ = "update_notifications"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(Integer, ForeignKey('containers.id'), index=True, nullable=True)
    update_history_id = Column(Integer, ForeignKey('update_history.id'), nullable=True, index=True)
    
    # Notification Details
    notification_type = Column(String)  # "update_available", "update_executed", "scan_complete", etc.
    title = Column(String, nullable=False)
    message = Column(Text)
    severity = Column(Enum(Severity), default=Severity.LOW)
    
    # Delivery
    channels = Column(JSONB, default=lambda: [])  # ["email", "slack", "webhook"]
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    notification_metadata = Column(JSONB, default=lambda: {})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    container = relationship("Container", back_populates="notifications")
    update_history = relationship("UpdateHistory", foreign_keys=[update_history_id])


class ContainerBackup(Base):
    """Container backup metadata."""
    __tablename__ = "container_backups"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(Integer, ForeignKey('containers.id'), index=True, nullable=False)
    
    # Backup Details
    backup_type = Column(String)  # "config", "volumes", "full"
    backup_path = Column(String)
    size_bytes = Column(BigInteger, nullable=True)
    
    # Backup Metadata
    container_name = Column(String)
    image = Column(String)
    image_digest = Column(String, nullable=True)
    config_snapshot = Column(JSONB, default=lambda: {})
    
    # Status
    status = Column(Enum(BackupStatus), default=BackupStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Retention
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    container = relationship("Container", back_populates="backups")


class AIRecommendation(Base):
    """AI-generated recommendations for container updates."""
    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(Integer, ForeignKey('containers.id'), index=True, nullable=False)
    
    # Recommendation Details
    recommendation_type = Column(Enum(RecommendationType))
    severity = Column(Enum(Severity))
    title = Column(String, nullable=False)
    summary = Column(Text)
    detailed_analysis = Column(Text)
    
    # Context
    current_version = Column(String)
    target_version = Column(String, nullable=True)
    changelog_summary = Column(Text, nullable=True)
    
    # Risk Assessment
    risk_level = Column(Enum(Severity))
    breaking_changes = Column(Boolean, default=False)
    rollback_available = Column(Boolean, default=True)
    
    # AI Metadata
    ai_model = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)  # 0.0 - 1.0
    
    # Status
    status = Column(String, default="pending")  # "pending", "accepted", "rejected", "expired"
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    container = relationship("Container", back_populates="recommendations")


class RegistryCredential(Base):
    """Private registry credentials."""
    __tablename__ = "registry_credentials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Registry Details
    registry_url = Column(String, nullable=False)  # e.g., "ghcr.io", "docker.io"
    username = Column(String)
    password = Column(String)  # Should be encrypted
    email = Column(String, nullable=True)
    
    # Auth Token (alternative to username/password)
    auth_token = Column(String, nullable=True)  # Should be encrypted
    
    # Status
    enabled = Column(Boolean, default=True)
    last_validated = Column(DateTime(timezone=True), nullable=True)
    validation_status = Column(String, default="unknown")  # "valid", "invalid", "unknown"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
