"""Test container models."""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.containers import (
    ContainerHost, Container, UpdatePolicy, MaintenanceWindow,
    VulnerabilityScan, ContainerBackup, AIRecommendation,
    RuntimeType, ConnectionType, ContainerStatus, PolicyScope
)


class TestContainerHost:
    """Test ContainerHost model."""
    
    def test_create_container_host(self, db: Session):
        """Test creating a container host."""
        host = ContainerHost(
            name="test-docker-host",
            connection_type=ConnectionType.SOCKET,
            connection_string="unix:///var/run/docker.sock",
            runtime_type=RuntimeType.DOCKER,
            description="Test Docker host"
        )
        db.add(host)
        db.commit()
        db.refresh(host)
        
        assert host.id is not None
        assert host.name == "test-docker-host"
        assert host.runtime_type == RuntimeType.DOCKER
        assert host.enabled is True
        assert host.status == "unknown"
    
    def test_container_host_relationships(self, db: Session):
        """Test ContainerHost relationships."""
        host = ContainerHost(
            name="test-host",
            connection_type=ConnectionType.SOCKET,
            connection_string="unix:///var/run/docker.sock"
        )
        db.add(host)
        db.commit()
        
        # Add container
        container = Container(
            host_id=host.id,
            container_id="abc123",
            name="test-container",
            image="nginx:latest",
            status=ContainerStatus.RUNNING
        )
        db.add(container)
        db.commit()
        
        db.refresh(host)
        assert len(host.containers) == 1
        assert host.containers[0].name == "test-container"


class TestContainer:
    """Test Container model."""
    
    def test_create_container(self, db: Session):
        """Test creating a container."""
        host = ContainerHost(
            name="test-host",
            connection_type=ConnectionType.SOCKET,
            connection_string="unix:///var/run/docker.sock"
        )
        db.add(host)
        db.commit()
        
        container = Container(
            host_id=host.id,
            container_id="abc123",
            name="nginx-web",
            image="nginx:1.21",
            image_id="sha256:abc123",
            status=ContainerStatus.RUNNING,
            current_tag="1.21",
            labels={"app": "web", "env": "prod"},
            ports={"80/tcp": 8080}
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        assert container.id is not None
        assert container.name == "nginx-web"
        assert container.status == ContainerStatus.RUNNING
        assert container.labels["app"] == "web"
        assert container.update_available is False
        assert container.auto_update is False
    
    def test_container_update_fields(self, db: Session):
        """Test container update-related fields."""
        host = ContainerHost(name="host", connection_type=ConnectionType.SOCKET, connection_string="test")
        db.add(host)
        db.commit()
        
        container = Container(
            host_id=host.id,
            container_id="abc",
            name="test",
            image="nginx:1.0",
            status=ContainerStatus.RUNNING,
            current_tag="1.0",
            current_digest="sha256:old",
            available_tag="1.1",
            available_digest="sha256:new",
            update_available=True
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        assert container.update_available is True
        assert container.current_tag == "1.0"
        assert container.available_tag == "1.1"


class TestUpdatePolicy:
    """Test UpdatePolicy model."""
    
    def test_create_global_policy(self, db: Session):
        """Test creating a global update policy."""
        policy = UpdatePolicy(
            name="Auto-update stable images",
            description="Automatically update production images",
            scope=PolicyScope.GLOBAL,
            auto_approve=False,
            require_ai_approval=True,
            image_pattern=".*:stable$",
            priority=100
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
        
        assert policy.id is not None
        assert policy.scope == PolicyScope.GLOBAL
        assert policy.auto_approve is False
        assert policy.require_ai_approval is True
        assert policy.enabled is True
    
    def test_policy_with_maintenance_window(self, db: Session):
        """Test policy with maintenance window."""
        window = MaintenanceWindow(
            name="Weekend maintenance",
            cron_expression="0 2 * * 6",  # 2 AM Saturdays
            duration_minutes=120
        )
        db.add(window)
        db.commit()
        
        policy = UpdatePolicy(
            name="Weekend updates",
            scope=PolicyScope.GLOBAL,
            maintenance_window_id=window.id
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
        
        assert policy.maintenance_window is not None
        assert policy.maintenance_window.name == "Weekend maintenance"


class TestVulnerabilityScan:
    """Test VulnerabilityScan model."""
    
    def test_create_vulnerability_scan(self, db: Session):
        """Test creating a vulnerability scan."""
        host = ContainerHost(name="host", connection_type=ConnectionType.SOCKET, connection_string="test")
        db.add(host)
        db.commit()
        
        container = Container(
            host_id=host.id,
            container_id="abc",
            name="test",
            image="nginx:1.0",
            status=ContainerStatus.RUNNING
        )
        db.add(container)
        db.commit()
        
        scan = VulnerabilityScan(
            container_id=container.id,
            image="nginx:1.0",
            scanner="trivy",
            scanner_version="0.45.0",
            critical_count=2,
            high_count=5,
            medium_count=10,
            low_count=3,
            total_count=20,
            security_score=65
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        
        assert scan.id is not None
        assert scan.critical_count == 2
        assert scan.total_count == 20
        assert scan.security_score == 65


class TestAIRecommendation:
    """Test AIRecommendation model."""
    
    def test_create_ai_recommendation(self, db: Session):
        """Test creating an AI recommendation."""
        host = ContainerHost(name="host", connection_type=ConnectionType.SOCKET, connection_string="test")
        db.add(host)
        db.commit()
        
        container = Container(
            host_id=host.id,
            container_id="abc",
            name="test",
            image="nginx:1.0",
            status=ContainerStatus.RUNNING
        )
        db.add(container)
        db.commit()
        
        rec = AIRecommendation(
            container_id=container.id,
            recommendation_type="update",
            severity="medium",
            title="Update to nginx 1.1",
            summary="New features and bug fixes",
            current_version="1.0",
            target_version="1.1",
            risk_level="low",
            breaking_changes=False,
            confidence_score=0.85
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        
        assert rec.id is not None
        assert rec.recommendation_type == "update"
        assert rec.confidence_score == 0.85


# Pytest fixtures
@pytest.fixture
def db():
    """Database session fixture."""
    from app.core.database import SessionLocal, engine
    from app.core.database import Base
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = SessionLocal()
    yield session
    
    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)
