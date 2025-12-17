# Contributing to Unity

Thank you for your interest in contributing to Unity!

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 16

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mylaniakea/unity.git
   cd unity
   ```

2. **Backend setup**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Environment configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Database setup**
   ```bash
   # Using Docker Compose
   docker-compose up -d db
   
   # Or locally
   createdb homelab_db
   ```

## Code Organization

### Backend Structure
```
backend/app/
├── models/              # Domain-organized models
│   ├── core.py         # ServerProfile, Settings
│   ├── credentials.py  # SSH keys, certificates
│   ├── infrastructure.py # MonitoredServer, Storage, DB
│   └── alert_rules.py  # Alert rule system
├── routers/            # API endpoints
├── services/           # Business logic
│   ├── infrastructure/ # Infrastructure monitoring
│   └── credentials/    # Credential management
└── schedulers/         # Background tasks
```

## Testing

### Running Tests
```bash
cd backend
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Specific test file
pytest tests/test_infrastructure_models.py -v
```

### Writing Tests
- Place tests in `backend/tests/`
- Use fixtures from `conftest.py`
- Follow naming convention: `test_*.py`
- Aim for >80% coverage on new features

## Database Migrations

We use Alembic for schema management:

```bash
# Create migration after model changes
alembic revision --autogenerate -m "description"

# Review and apply
alembic upgrade head
```

See `backend/README_ALEMBIC.md` for details.

## Code Style

### Python
- Follow PEP 8
- Use type hints where practical
- Docstrings for public functions
- Keep functions focused and testable

### Git Commits
Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `refactor:` Code restructuring
- `test:` Adding tests
- `docs:` Documentation updates

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write tests for new features
   - Update documentation
   - Follow code style guidelines

3. **Run tests**
   ```bash
   pytest tests/ -v
   ```

4. **Commit with clear messages**
   ```bash
   git commit -m "feat: add storage pool monitoring"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **PR Guidelines**
   - Clear description of changes
   - Reference related issues
   - Include test results
   - Update CHANGELOG if applicable

## Development Workflow

### Adding a New Model
1. Add model to appropriate file in `app/models/`
2. Import in `app/models/__init__.py`
3. Create migration: `alembic revision --autogenerate`
4. Write tests in `tests/test_*_models.py`
5. Apply migration: `alembic upgrade head`

### Adding an API Endpoint
1. Add endpoint to appropriate router in `app/routers/`
2. Write business logic in `app/services/`
3. Add tests in `tests/test_*_api.py`
4. Update API documentation

### Adding a Service
1. Create service in `app/services/`
2. Follow dependency injection pattern
3. Write unit tests
4. Document public methods

## Security

- **Never commit secrets** (API keys, passwords, certificates)
- Use `.env` for configuration
- Follow principle of least privilege
- Encrypt sensitive data at rest
- Use parameterized queries (SQLAlchemy handles this)

## Getting Help

- Check existing issues
- Read documentation in `docs/`
- Ask in discussions

## License

By contributing, you agree that your contributions will be licensed under the project's license.
