"""
kc-booth - SSH Key and Certificate Management for Homelabs.

This package provides a secure API for managing SSH keys, server credentials,
and TLS certificates with automated rotation.

Main modules:
- main: FastAPI application with API endpoints
- auth: Authentication and authorization
- encryption: At-rest encryption for sensitive data
- config: Centralized configuration management
- scheduler: Automated certificate rotation
- step_ca: Integration with Step-CA certificate authority

For usage and deployment, see:
- README.md: General overview and quick start
- PRODUCTION_DEPLOYMENT.md: Production deployment guide
- SECURITY_HARDENING.md: Security features and hardening
- AUTHENTICATION_IMPLEMENTATION.md: Authentication details
"""

__version__ = "1.0.0"
__author__ = "kc-booth contributors"
