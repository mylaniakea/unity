#!/usr/bin/env python3
"""
Production Verification Script

Verifies that Unity is ready for production deployment by checking:
- All imports work
- Database models are registered
- All routers are configured
- Dependencies are installed
"""

import sys
import importlib
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

def check_imports():
    """Check that all critical imports work."""
    print("🔍 Checking imports...")
    
    critical_imports = [
        "app.main",
        "app.core.database",
        "app.core.config",
        "app.models",
        "app.models.dashboard",
        "app.models.plugin_marketplace",
        "app.routers.auth",
        "app.routers.plugins.marketplace",
        "app.routers.dashboard_builder",
        "app.routers.ai_insights",
        "app.services.plugin_scheduler",
        "app.services.cache",
        "app.middleware.cache_middleware",
    ]
    
    failed = []
    for module_name in critical_imports:
        try:
            importlib.import_module(module_name)
            print(f"  ✅ {module_name}")
        except Exception as e:
            print(f"  ❌ {module_name}: {e}")
            failed.append(module_name)
    
    return len(failed) == 0

def check_models():
    """Check that all models are registered."""
    print("\n🔍 Checking database models...")
    
    try:
        from app.models import (
            Dashboard,
            DashboardWidget,
            MarketplacePlugin,
            PluginReview,
            PluginInstallation,
            PluginDownload,
            Plugin,
            User,
            APIKey,
        )
        print("  ✅ All models imported successfully")
        return True
    except Exception as e:
        print(f"  ❌ Model import failed: {e}")
        return False

def check_routers():
    """Check that all routers are configured."""
    print("\n🔍 Checking routers...")
    
    try:
        from app.main import app
        
        routes = [route.path for route in app.routes]
        
        required_routes = [
            "/",
            "/health",
            "/docs",
            "/api/v1/auth",
            "/api/v1/marketplace",
            "/api/v1/dashboards",
            "/api/v1/ai/insights",
        ]
        
        found = []
        missing = []
        
        for required in required_routes:
            # Check if any route starts with the required path
            if any(route.startswith(required) for route in routes):
                found.append(required)
                print(f"  ✅ {required}")
            else:
                missing.append(required)
                print(f"  ⚠️  {required} (not found)")
        
        if missing:
            print(f"\n  ⚠️  Missing routes: {missing}")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Router check failed: {e}")
        return False

def check_dependencies():
    """Check that all required dependencies are installed."""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "alembic",
        "redis",
        "numpy",
        "apscheduler",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (not installed)")
            missing.append(package)
    
    if missing:
        print(f"\n  ⚠️  Missing packages: {missing}")
        print("  Run: pip install -r requirements.txt")
        return False
    
    return True

def check_migration():
    """Check migration status."""
    print("\n🔍 Checking migration status...")
    
    try:
        import subprocess
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True,
            cwd=backend_path
        )
        
        if result.returncode == 0:
            print(f"  ✅ Migration status: {result.stdout.strip()}")
            return True
        else:
            print(f"  ⚠️  Migration check failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ⚠️  Could not check migration: {e}")
        print("  ⚠️  Run manually: alembic upgrade head")
        return False

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Unity Production Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Imports", check_imports),
        ("Models", check_models),
        ("Routers", check_routers),
        ("Migration", check_migration),
    ]
    
    results = {}
    for name, check_func in checks:
        results[name] = check_func()
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20} {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All checks passed! Unity is ready for production.")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix issues before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

