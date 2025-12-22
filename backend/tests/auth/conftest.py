"""Test fixtures for authentication tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.main import app

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """Create test client."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    from app.services.auth import user_service
    user = user_service.create_user(
        db=db,
        username="testuser",
        email="test@example.com",
        password="testpass123",
        role="viewer"
    )
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    from app.services.auth import user_service
    user = user_service.create_user(
        db=db,
        username="admin",
        email="admin@example.com",
        password="adminpass123",
        role="admin",
        is_superuser=True
    )
    return user
