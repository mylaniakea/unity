"""
Database setup script for plugin tables.

This script creates the plugin-related tables in the database.
Run this once to set up the plugin system tables.

Usage:
    python create_plugin_tables.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models import Plugin, PluginMetric, PluginExecution, PluginAPIKey

def create_tables():
    """Create all plugin-related tables"""
    print("=" * 60)
    print("Unity Plugin System - Database Setup")
    print("=" * 60)
    print()
    
    print("Creating plugin tables...")
    print("  - plugins")
    print("  - plugin_metrics")
    print("  - plugin_executions")
    print("  - plugin_api_keys")
    print()
    
    try:
        # Create all tables defined in Base
        Base.metadata.create_all(bind=engine)
        print("✅ Plugin tables created successfully!")
        print()
        print("Tables ready:")
        print("  ✓ plugins - Plugin registry")
        print("  ✓ plugin_metrics - Time-series metrics")
        print("  ✓ plugin_executions - Execution history")
        print("  ✓ plugin_api_keys - API key management")
        print()
        print("=" * 60)
        print("Plugin system database setup complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        print()
        print("If tables already exist, this is normal.")
        print("SQLAlchemy will skip existing tables automatically.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(create_tables())
