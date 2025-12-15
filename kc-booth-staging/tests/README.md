# kc-booth Tests

## Running Tests

### All Tests
```bash
pytest
```

### Specific Test File
```bash
pytest tests/test_encryption.py
pytest tests/test_auth.py
pytest tests/test_validation.py
```

### With Coverage
```bash
pytest --cov=src --cov-report=html
# View coverage report: open htmlcov/index.html
```

### Verbose Output
```bash
pytest -v
```

## Test Organization

- `test_main.py` - API endpoint tests
- `test_encryption.py` - Encryption/decryption tests
- `test_auth.py` - Authentication and password hashing tests
- `test_validation.py` - Input validation and security tests
- `test_cert_providers.py` - Certificate provider tests

## Test Coverage Areas

### ✅ Implemented
- Health check endpoint
- Encryption/decryption
- Password hashing and verification
- Input validation (domains, hostnames, IPs, usernames)
- Certificate provider registry
- Command injection prevention

### 🚧 To Add (Integration Tests)
- Full API endpoint tests with database
- Rate limiting tests
- Authentication flow tests
- CRUD operations tests
- Certificate issuance tests (requires external services)

## Environment Setup for Tests

Tests use the same `.env` configuration as the application. For isolated testing:

```bash
# Create test environment file
cp .env .env.test

# Set test-specific values
echo "DATABASE_URL=postgresql://user:pass@localhost/kc-booth-test" >> .env.test
echo "DISABLE_AUTH=true" >> .env.test
echo "CERT_PROVIDER=openssh" >> .env.test

# Run tests with test env
ENV_FILE=.env.test pytest
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
      - run: pytest --cov=src
```

## Writing New Tests

### Test Structure
```python
"""Tests for <module>."""
import pytest
from src.<module> import <function>

def test_<feature>():
    """Test <description>."""
    # Arrange
    input_data = "test"
    
    # Act
    result = <function>(input_data)
    
    # Assert
    assert result == expected
```

### Security Test Guidelines
- Always test with malicious input
- Test command injection attempts
- Test SQL injection attempts (if applicable)
- Test path traversal attempts
- Test buffer overflow scenarios

### Example Security Test
```python
def test_prevents_command_injection():
    """Test that validation prevents command injection."""
    malicious_inputs = [
        "value; rm -rf /",
        "$(whoami)",
        "`command`",
        "value && malicious",
        "value | cat /etc/passwd"
    ]
    
    for malicious in malicious_inputs:
        with pytest.raises(ValueError):
            validate_function(malicious)
```
