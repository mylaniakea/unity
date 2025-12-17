# Unity Testing Documentation

## Overview

Unity uses pytest for testing with comprehensive fixtures and utilities for testing all layers of the application.

## Test Structure

```
backend/tests/
├── conftest.py                   # Shared fixtures and utilities
├── pytest.ini                    # Pytest configuration
├── test_core_config.py          # Core configuration tests
├── test_api_endpoints.py        # API endpoint tests
├── test_alert_evaluator.py      # Alert evaluation logic tests
├── test_infrastructure_models.py # Infrastructure model tests
└── test_containers/             # Container-related tests
    ├── test_models.py
    └── test_api.py
```

## Running Tests

### Run All Tests
```bash
cd backend
pytest
```

### Run Specific Test File
```bash
pytest tests/test_api_endpoints.py
```

### Run Tests by Marker
```bash
# Run only unit tests (fast)
pytest -m unit

# Run only smoke tests
pytest -m smoke

# Run API tests
pytest -m api

# Run database tests
pytest -m database
```

### Run with Coverage
```bash
# Install pytest-cov first
pip install pytest-cov

# Run with coverage
pytest --cov=app --cov-report=term-missing --cov-report=html
```

### Run Tests in Docker
```bash
# From project root
docker compose exec backend pytest

# With coverage
docker compose exec backend pytest --cov=app
```

## Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration tests (slower, may require services)
- `@pytest.mark.smoke` - Quick smoke tests for CI
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.database` - Database-related tests
- `@pytest.mark.auth` - Authentication/authorization tests
- `@pytest.mark.services` - Service layer tests
- `@pytest.mark.slow` - Tests that take significant time

## Available Fixtures

### Database Fixtures

- `test_db` - In-memory SQLite database for testing
- `sample_monitored_server` - Pre-created monitored server
- `sample_alert_rule` - Pre-created alert rule
- `sample_storage_device` - Pre-created storage device
- `sample_database_instance` - Pre-created database instance

### API Testing Fixtures

- `test_client` - FastAPI TestClient with test database
- `auth_headers` - Authentication headers for regular user
- `admin_headers` - Authentication headers for admin user

## Writing New Tests

### Unit Test Example

```python
import pytest
from app.services.auth.auth_service import create_access_token

@pytest.mark.unit
def test_create_access_token():
    """Test JWT token creation."""
    token = create_access_token(data={"sub": "testuser"})
    assert token is not None
    assert isinstance(token, str)
```

### API Test Example

```python
import pytest

@pytest.mark.api
def test_get_profiles(test_client, auth_headers):
    """Test profiles endpoint."""
    response = test_client.get("/profiles/", headers=auth_headers)
    assert response.status_code == 200
```

### Database Test Example

```python
import pytest
from app import models

@pytest.mark.database
def test_create_server(test_db):
    """Test creating a monitored server."""
    server = models.MonitoredServer(
        hostname="test-server",
        ip_address="192.168.1.1",
        ssh_port=22,
        username="user"
    )
    test_db.add(server)
    test_db.commit()
    
    assert server.id is not None
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest -m "not slow"
```

## Test Coverage Goals

- **Unit Tests**: >80% coverage for business logic
- **Integration Tests**: Critical paths and workflows
- **API Tests**: All public endpoints
- **Smoke Tests**: Quick validation for CI/CD

## Best Practices

1. **Keep tests fast** - Use markers to separate slow tests
2. **Isolate tests** - Each test should be independent
3. **Use fixtures** - Leverage conftest.py fixtures for common setup
4. **Clear assertions** - Use descriptive assertion messages
5. **Test edge cases** - Don't just test happy paths
6. **Mock external services** - Avoid dependencies on external systems

## Troubleshooting

### Import Errors
Ensure you're running tests from the `backend/` directory or add it to PYTHONPATH:
```bash
export PYTHONPATH=/path/to/unity/backend:$PYTHONPATH
pytest
```

### Database Errors
The test suite uses an in-memory SQLite database. If you see database-related errors, ensure:
- SQLAlchemy models are properly imported in conftest.py
- Database fixtures are being used correctly

### Fixture Errors
If fixtures aren't found, ensure:
- conftest.py is in the tests directory
- Fixture names match exactly in test function parameters

## Future Enhancements

- [ ] Add pytest-cov for coverage reports
- [ ] Set up mutation testing
- [ ] Add performance/load tests
- [ ] Expand service layer test coverage
- [ ] Add contract tests for external APIs
