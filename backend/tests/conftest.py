"""Pytest configuration and fixtures for Unity tests."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app import models


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_monitored_server(test_db):
    """Create a sample monitored server for testing."""
    server = models.MonitoredServer(
        hostname="test-server",
        ip_address="192.168.1.100",
        ssh_port=22,
        username="testuser",
        monitoring_enabled=True,
        status=models.ServerStatus.UNKNOWN
    )
    test_db.add(server)
    test_db.commit()
    test_db.refresh(server)
    return server


@pytest.fixture
def sample_alert_rule(test_db):
    """Create a sample alert rule for testing."""
    rule = models.AlertRule(
        name="Test Temperature Alert",
        description="Alert when temperature exceeds threshold",
        resource_type=models.ResourceType.DEVICE,
        metric_name="temperature_celsius",
        condition=models.AlertCondition.GT,
        threshold=60.0,
        severity=models.AlertSeverity.WARNING,
        enabled=True,
        cooldown_minutes=15
    )
    test_db.add(rule)
    test_db.commit()
    test_db.refresh(rule)
    return rule


@pytest.fixture
def sample_storage_device(test_db, sample_monitored_server):
    """Create a sample storage device for testing."""
    device = models.StorageDevice(
        server_id=sample_monitored_server.id,
        device_name="/dev/sda",
        device_type=models.DeviceType.SSD,
        size_bytes=500000000000,
        smart_status=models.HealthStatus.HEALTHY,
        temperature_celsius=45
    )
    test_db.add(device)
    test_db.commit()
    test_db.refresh(device)
    return device


@pytest.fixture
def sample_database_instance(test_db, sample_monitored_server):
    """Create a sample database instance for testing."""
    db_instance = models.DatabaseInstance(
        server_id=sample_monitored_server.id,
        db_type=models.DatabaseType.POSTGRESQL,
        db_name="testdb",
        host="localhost",
        port=5432,
        username="postgres",
        status=models.DatabaseStatus.ONLINE
    )
    test_db.add(db_instance)
    test_db.commit()
    test_db.refresh(db_instance)
    return db_instance
