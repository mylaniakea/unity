"""Test container API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.containers import ContainerHost, Container, RuntimeType, ConnectionType, ContainerStatus
from app.models.users import User


class TestContainerHostAPI:
    """Test container host API endpoints."""
    
    def test_list_hosts_unauthorized(self, client: TestClient):
        """Test listing hosts without authentication."""
        response = client.get("/api/containers/hosts")
        assert response.status_code == 401
    
    def test_create_host_as_admin(self, client: TestClient, admin_token: str):
        """Test creating a container host as admin."""
        response = client.post(
            "/api/containers/hosts",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={
                "name": "docker-prod",
                "connection_type": "socket",
                "connection_string": "unix:///var/run/docker.sock",
                "runtime_type": "docker",
                "description": "Production Docker host"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "docker-prod"
        assert data["runtime_type"] == "docker"
    
    def test_create_host_as_user_forbidden(self, client: TestClient, user_token: str):
        """Test creating a host as regular user (should fail)."""
        response = client.post(
            "/api/containers/hosts",
            headers={"Authorization": f"Bearer {user_token}"},
            params={
                "name": "test-host",
                "connection_type": "socket",
                "connection_string": "unix:///var/run/docker.sock"
            }
        )
        assert response.status_code == 403
    
    def test_list_hosts_authenticated(self, client: TestClient, user_token: str, db: Session):
        """Test listing hosts as authenticated user."""
        # Create test host
        host = ContainerHost(
            name="test-host",
            connection_type=ConnectionType.SOCKET,
            connection_string="unix:///var/run/docker.sock"
        )
        db.add(host)
        db.commit()
        
        response = client.get(
            "/api/containers/hosts",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(h["name"] == "test-host" for h in data["hosts"])
    
    def test_get_host_details(self, client: TestClient, user_token: str, db: Session):
        """Test getting host details."""
        host = ContainerHost(
            name="test-host",
            connection_type=ConnectionType.SOCKET,
            connection_string="unix:///var/run/docker.sock",
            description="Test host"
        )
        db.add(host)
        db.commit()
        
        response = client.get(
            f"/api/containers/hosts/{host.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-host"
        assert data["description"] == "Test host"
    
    def test_get_host_stats(self, client: TestClient, user_token: str, db: Session):
        """Test getting host statistics."""
        host = ContainerHost(
            name="test-host",
            connection_type=ConnectionType.SOCKET,
            connection_string="test"
        )
        db.add(host)
        db.commit()
        
        # Add containers
        for i in range(3):
            container = Container(
                host_id=host.id,
                container_id=f"abc{i}",
                name=f"container-{i}",
                image="nginx:latest",
                status=ContainerStatus.RUNNING if i < 2 else ContainerStatus.STOPPED,
                update_available=i == 0
            )
            db.add(container)
        db.commit()
        
        response = client.get(
            f"/api/containers/hosts/{host.id}/stats",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_containers"] == 3
        assert data["running_containers"] == 2
        assert data["updates_available"] == 1


class TestContainerAPI:
    """Test container API endpoints."""
    
    def test_list_containers(self, client: TestClient, user_token: str, db: Session):
        """Test listing containers."""
        host = ContainerHost(name="host", connection_type=ConnectionType.SOCKET, connection_string="test")
        db.add(host)
        db.commit()
        
        container = Container(
            host_id=host.id,
            container_id="abc123",
            name="nginx-web",
            image="nginx:1.21",
            status=ContainerStatus.RUNNING
        )
        db.add(container)
        db.commit()
        
        response = client.get(
            "/api/containers",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
    
    def test_get_container_details(self, client: TestClient, user_token: str, db: Session):
        """Test getting container details."""
        host = ContainerHost(name="host", connection_type=ConnectionType.SOCKET, connection_string="test")
        db.add(host)
        db.commit()
        
        container = Container(
            host_id=host.id,
            container_id="abc123",
            name="nginx-web",
            image="nginx:1.21",
            status=ContainerStatus.RUNNING,
            labels={"app": "web"}
        )
        db.add(container)
        db.commit()
        
        response = client.get(
            f"/api/containers/{container.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "nginx-web"
        assert data["labels"]["app"] == "web"
    
    def test_list_available_updates(self, client: TestClient, user_token: str, db: Session):
        """Test listing containers with available updates."""
        host = ContainerHost(name="host", connection_type=ConnectionType.SOCKET, connection_string="test")
        db.add(host)
        db.commit()
        
        # Container with update
        container1 = Container(
            host_id=host.id,
            container_id="abc1",
            name="nginx-old",
            image="nginx:1.0",
            status=ContainerStatus.RUNNING,
            update_available=True
        )
        # Container without update
        container2 = Container(
            host_id=host.id,
            container_id="abc2",
            name="nginx-new",
            image="nginx:latest",
            status=ContainerStatus.RUNNING,
            update_available=False
        )
        db.add_all([container1, container2])
        db.commit()
        
        response = client.get(
            "/api/containers/updates",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["containers"][0]["name"] == "nginx-old"


class TestPolicyAPI:
    """Test update policy API endpoints."""
    
    def test_list_policies(self, client: TestClient, user_token: str):
        """Test listing update policies."""
        response = client.get(
            "/api/containers/policies",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
    
    def test_create_policy_as_admin(self, client: TestClient, admin_token: str):
        """Test creating an update policy as admin."""
        response = client.post(
            "/api/containers/policies",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={
                "name": "Auto-update stable",
                "scope": "global",
                "auto_approve": False
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Auto-update stable"
        assert data["scope"] == "global"


# Pytest fixtures
@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def db():
    """Database session fixture."""
    from app.core.database import SessionLocal, engine, Base
    
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def admin_token(db: Session):
    """Admin user token fixture."""
    from app.services.auth import AuthService
    
    # Create admin user
    admin = User(
        username="admin",
        email="admin@test.com",
        role="admin"
    )
    admin.password_hash = AuthService.hash_password("admin123")
    db.add(admin)
    db.commit()
    
    # Generate token
    token = AuthService.create_access_token(data={"sub": admin.username})
    return token


@pytest.fixture
def user_token(db: Session):
    """Regular user token fixture."""
    from app.services.auth import AuthService
    
    # Create user
    user = User(
        username="user",
        email="user@test.com",
        role="user"
    )
    user.password_hash = AuthService.hash_password("user123")
    db.add(user)
    db.commit()
    
    # Generate token
    token = AuthService.create_access_token(data={"sub": user.username})
    return token
