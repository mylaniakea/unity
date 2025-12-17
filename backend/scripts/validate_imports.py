#!/usr/bin/env python3
"""Validate that all infrastructure services import correctly."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

errors = []

print("Validating infrastructure service imports...")

try:
    from app.services.infrastructure import ssh_service
    print("✅ ssh_service")
except Exception as e:
    errors.append(f"ssh_service: {e}")
    print(f"❌ ssh_service: {e}")

try:
    from app.services.infrastructure import collection_task
    print("✅ collection_task")
except Exception as e:
    errors.append(f"collection_task: {e}")
    print(f"❌ collection_task: {e}")

try:
    from app.services.infrastructure import alert_evaluator
    print("✅ alert_evaluator")
except Exception as e:
    errors.append(f"alert_evaluator: {e}")
    print(f"❌ alert_evaluator: {e}")

try:
    from app.services.infrastructure import storage_discovery
    print("✅ storage_discovery")
except Exception as e:
    errors.append(f"storage_discovery: {e}")
    print(f"❌ storage_discovery: {e}")

try:
    from app.services.infrastructure import pool_discovery
    print("✅ pool_discovery")
except Exception as e:
    errors.append(f"pool_discovery: {e}")
    print(f"❌ pool_discovery: {e}")

try:
    from app.services.infrastructure import database_discovery
    print("✅ database_discovery")
except Exception as e:
    errors.append(f"database_discovery: {e}")
    print(f"❌ database_discovery: {e}")

try:
    from app.services.infrastructure import mysql_metrics
    print("✅ mysql_metrics")
except Exception as e:
    errors.append(f"mysql_metrics: {e}")
    print(f"❌ mysql_metrics: {e}")

try:
    from app.services.infrastructure import postgres_metrics
    print("✅ postgres_metrics")
except Exception as e:
    errors.append(f"postgres_metrics: {e}")
    print(f"❌ postgres_metrics: {e}")

try:
    from app.services.infrastructure import data_retention
    print("✅ data_retention")
except Exception as e:
    errors.append(f"data_retention: {e}")
    print(f"❌ data_retention: {e}")

try:
    from app.services.infrastructure import mdadm_discovery
    print("✅ mdadm_discovery")
except Exception as e:
    errors.append(f"mdadm_discovery: {e}")
    print(f"❌ mdadm_discovery: {e}")

print("\n" + "="*50)
if errors:
    print(f"❌ {len(errors)} import(s) failed:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("✅ All infrastructure imports successful!")
    sys.exit(0)
