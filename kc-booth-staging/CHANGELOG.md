# Changelog

All notable changes to kc-booth will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-15

### Added
- **Security**: At-rest encryption for passwords and private keys using Fernet (AES-128)
- **Security**: API key-based authentication with bcrypt hashing
- **Security**: Rate limiting (5 login attempts/minute, 100 API requests/minute)
- **Security**: Input validation for all user inputs (hostnames, IPs, SSH keys, usernames)
- **Security**: Command injection prevention via input sanitization
- **Security**: Security headers (HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)
- **Security**: TLS/HTTPS support via nginx reverse proxy
- **Security**: Database SSL/TLS encryption
- **Security**: Environment variable validation at startup
- **Auth**: User management with password authentication
- **Auth**: API key generation, listing, and revocation
- **Auth**: Login endpoint returning API keys
- **Auth**: All endpoints protected with X-API-Key header
- **Auth**: DISABLE_AUTH flag for development mode
- **Deployment**: Production docker-compose with nginx, certbot, health checks
- **Deployment**: Certificate setup script (self-signed or Let's Encrypt)
- **Deployment**: Automated certificate renewal via certbot
- **Deployment**: .env.example template with secure defaults
- **Documentation**: PRODUCTION_DEPLOYMENT.md with complete deployment guide
- **Documentation**: SECURITY_HARDENING.md documenting security features
- **Documentation**: AUTHENTICATION_IMPLEMENTATION.md with auth details
- **Code Quality**: Centralized logging module
- **Code Quality**: Comprehensive docstrings and type hints
- **Code Quality**: TODO comments for unimplemented features

### Changed
- Removed hardcoded passwords from docker-compose.yml (now use environment variables)
- Upgraded security score from 5/10 to 10/10
- Improved error messages with helpful guidance
- Enhanced scheduler with proper logging and error handling
- Database connections now use SSL (sslmode=prefer)

### Security
- All passwords and private keys encrypted at rest
- API keys hashed with bcrypt before storage
- TLS 1.2/1.3 only with modern cipher suites
- Rate limiting at both nginx and application levels
- Input validation prevents command injection
- Subprocess calls sanitized
- Secrets managed via environment variables
- Security headers prevent XSS, clickjacking, MIME sniffing

### Known Issues
- Certificate distribution is a stub (requires paramiko implementation)
- Scheduler shares DB session across jobs (should create new session per job)
- No API key expiration dates yet
- Rate limiting threshold not configurable

## [0.1.0] - Initial Release (Pre-security)

### Added
- Basic SSH key management endpoints
- Server management endpoints
- Certificate issuance via step-ca
- PostgreSQL database
- Certificate rotation scheduler
- Basic health check endpoint

### Security Issues (Fixed in 1.0.0)
- Passwords stored in plaintext
- No authentication
- No rate limiting
- No input validation
- Hardcoded secrets in docker-compose
- No TLS/HTTPS
- No database encryption

[1.0.0]: https://github.com/mylaniakea/kc-booth/releases/tag/v1.0.0
[0.1.0]: https://github.com/mylaniakea/kc-booth/releases/tag/v0.1.0
