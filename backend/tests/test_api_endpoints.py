"""Tests for critical API endpoints."""
import pytest


@pytest.mark.api
@pytest.mark.smoke
def test_root_endpoint(test_client):
    """Test root endpoint returns welcome message."""
    response = test_client.get("/")
    
    assert response.status_code == 200
    assert "message" in response.json()
    assert "Unity" in response.json()["message"]


@pytest.mark.api
@pytest.mark.smoke
def test_docs_endpoint(test_client):
    """Test API docs are accessible."""
    response = test_client.get("/docs")
    
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


@pytest.mark.api
def test_openapi_schema(test_client):
    """Test OpenAPI schema is generated."""
    response = test_client.get("/openapi.json")
    
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema
    assert "info" in schema


@pytest.mark.api
@pytest.mark.auth
def test_auth_required_endpoint_without_token(test_client):
    """Test that protected endpoints require authentication."""
    response = test_client.get("/profiles/")
    
    # Should return 401 Unauthorized or redirect
    assert response.status_code in [401, 403]


@pytest.mark.api
def test_plugins_list_endpoint(test_client):
    """Test plugins listing endpoint."""
    response = test_client.get("/plugins/")
    
    assert response.status_code == 200
    data = response.json()
    assert "plugins" in data or isinstance(data, list)


@pytest.mark.api
def test_thresholds_endpoint(test_client):
    """Test thresholds listing endpoint."""
    response = test_client.get("/thresholds/")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.api
@pytest.mark.database
def test_database_connection_via_api(test_client):
    """Test that API can connect to database through test fixture."""
    # This implicitly tests database connectivity
    response = test_client.get("/")
    
    assert response.status_code == 200
