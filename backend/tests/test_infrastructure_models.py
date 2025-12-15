"""Tests for infrastructure monitoring models."""
import pytest
from app import models


def test_monitored_server_creation(test_db):
    """Test creating a monitored server."""
    server = models.MonitoredServer(
        hostname="test-server",
        ip_address="10.0.0.1",
        ssh_port=22,
        username="admin",
        monitoring_enabled=True
    )
    test_db.add(server)
    test_db.commit()
    
    assert server.id is not None
    assert server.hostname == "test-server"
    assert server.status == models.ServerStatus.UNKNOWN
    assert server.monitoring_enabled is True


def test_monitored_server_with_credentials(test_db):
    """Test monitored server with SSH key reference."""
    # Create SSH key
    ssh_key = models.SSHKey(
        name="test-key",
        key_type="rsa",
        public_key_encrypted="test-public",
        private_key_encrypted="test-private"
    )
    test_db.add(ssh_key)
    test_db.commit()
    
    # Create server with key
    server = models.MonitoredServer(
        hostname="test-server",
        ip_address="10.0.0.1",
        username="admin",
        ssh_key_id=ssh_key.id
    )
    test_db.add(server)
    test_db.commit()
    
    assert server.ssh_key_id == ssh_key.id


def test_storage_device_relationships(test_db, sample_monitored_server):
    """Test storage device relationship with server."""
    device = models.StorageDevice(
        server_id=sample_monitored_server.id,
        device_name="/dev/nvme0n1",
        device_type=models.DeviceType.NVME,
        size_bytes=1000000000000
    )
    test_db.add(device)
    test_db.commit()
    
    assert device.server_id == sample_monitored_server.id
    assert len(sample_monitored_server.storage_devices) == 1
    assert sample_monitored_server.storage_devices[0].device_name == "/dev/nvme0n1"


def test_storage_pool_creation(test_db, sample_monitored_server):
    """Test creating a storage pool."""
    pool = models.StoragePool(
        server_id=sample_monitored_server.id,
        pool_name="tank",
        pool_type=models.PoolType.ZFS,
        total_size_bytes=5000000000000,
        used_size_bytes=2000000000000,
        available_size_bytes=3000000000000,
        health_status=models.HealthStatus.HEALTHY
    )
    test_db.add(pool)
    test_db.commit()
    
    assert pool.id is not None
    assert pool.pool_name == "tank"
    assert pool.pool_type == models.PoolType.ZFS
    assert pool.health_status == models.HealthStatus.HEALTHY


def test_database_instance_creation(test_db, sample_monitored_server):
    """Test creating a database instance."""
    db_instance = models.DatabaseInstance(
        server_id=sample_monitored_server.id,
        db_type=models.DatabaseType.MYSQL,
        db_name="production",
        host="localhost",
        port=3306,
        username="root"
    )
    test_db.add(db_instance)
    test_db.commit()
    
    assert db_instance.id is not None
    assert db_instance.db_type == models.DatabaseType.MYSQL
    assert db_instance.port == 3306


def test_alert_rule_creation(test_db):
    """Test creating an alert rule."""
    rule = models.AlertRule(
        name="High CPU Alert",
        resource_type=models.ResourceType.SERVER,
        metric_name="cpu_usage",
        condition=models.AlertCondition.GT,
        threshold=80.0,
        severity=models.AlertSeverity.CRITICAL
    )
    test_db.add(rule)
    test_db.commit()
    
    assert rule.id is not None
    assert rule.name == "High CPU Alert"
    assert rule.condition == models.AlertCondition.GT
    assert rule.threshold == 80.0


def test_alert_rule_enums(test_db):
    """Test all alert rule enum values."""
    # Test ResourceType
    assert models.ResourceType.SERVER == "server"
    assert models.ResourceType.DEVICE == "device"
    assert models.ResourceType.POOL == "pool"
    assert models.ResourceType.DATABASE == "database"
    
    # Test AlertCondition
    assert models.AlertCondition.GT == "gt"
    assert models.AlertCondition.LT == "lt"
    assert models.AlertCondition.EQ == "eq"
    
    # Test AlertSeverity
    assert models.AlertSeverity.INFO == "info"
    assert models.AlertSeverity.WARNING == "warning"
    assert models.AlertSeverity.CRITICAL == "critical"


def test_server_cascade_delete(test_db, sample_monitored_server):
    """Test that deleting a server cascades to devices."""
    device = models.StorageDevice(
        server_id=sample_monitored_server.id,
        device_name="/dev/sda",
        device_type=models.DeviceType.HDD
    )
    test_db.add(device)
    test_db.commit()
    
    server_id = sample_monitored_server.id
    test_db.delete(sample_monitored_server)
    test_db.commit()
    
    # Device should be deleted via cascade
    deleted_device = test_db.query(models.StorageDevice).filter(
        models.StorageDevice.server_id == server_id
    ).first()
    assert deleted_device is None


def test_monitored_server_status_enum(test_db):
    """Test ServerStatus enum values."""
    server = models.MonitoredServer(
        hostname="test",
        ip_address="10.0.0.1",
        username="admin",
        status=models.ServerStatus.ONLINE
    )
    test_db.add(server)
    test_db.commit()
    
    assert server.status == models.ServerStatus.ONLINE
    
    server.status = models.ServerStatus.OFFLINE
    test_db.commit()
    assert server.status == models.ServerStatus.OFFLINE
