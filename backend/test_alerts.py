from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app import models
import pytest

# Setup the test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the tables in the test database
models.Base.metadata.create_all(bind=engine)

# Override the get_db dependency to use the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    # Create a new database session for each test
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # Clean up the database after each test
        for table in reversed(models.Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
        db.close()

def test_get_alert_stats_multitenancy(db_session):
    # Create alerts for tenant_1
    db_session.add(models.Alert(tenant_id="tenant_1", name="Test Alert 1", severity="critical", resolved=False))
    db_session.add(models.Alert(tenant_id="tenant_1", name="Test Alert 2", severity="warning", resolved=True))
    
    # Create alerts for tenant_2
    db_session.add(models.Alert(tenant_id="tenant_2", name="Test Alert 3", severity="info", resolved=False))
    db_session.commit()

    # Make a request to the endpoint for tenant_1
    response = client.get("/alerts/stats", headers={"X-Tenant-ID": "tenant_1"})
    
    # Assert the response
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["unresolved"] == 1
    assert data["critical"] == 1
    assert data["warning"] == 0
    assert data["info"] == 0

    # Make a request to the endpoint for tenant_2
    response = client.get("/alerts/stats", headers={"X-Tenant-ID": "tenant_2"})

    # Assert the response
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["unresolved"] == 1
    assert data["critical"] == 0
    assert data["warning"] == 0
    assert data["info"] == 1
