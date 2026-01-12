#!/usr/bin/env python3
"""
Test script for the Application Blueprint System
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.services.orchestration.blueprint_loader import BlueprintLoader

def test_blueprint_loader():
    """Test the blueprint loader functionality"""
    print("=" * 60)
    print("Testing Application Blueprint System")
    print("=" * 60)

    db = SessionLocal()

    try:
        # Initialize loader
        print("\n1. Initializing Blueprint Loader...")
        loader = BlueprintLoader(db)
        print("   ✓ Loader initialized")

        # List blueprints (this will load them)
        print("\n2. Loading blueprints from filesystem...")
        blueprints_list = loader.list_blueprints()
        count = len(blueprints_list)
        print(f"   ✓ Found {count} blueprints")

        # List all blueprints
        print("\n3. Listing all available blueprints:")
        if blueprints_list:
            for bp in blueprints_list:
                name = bp.get('name', 'Unknown')
                category = bp.get('category', 'uncategorized')
                description = bp.get('description', 'No description')
                print(f"   - {name:<15} [{category:<10}] - {description[:50]}...")
        else:
            print("   ⚠ No blueprints found")

        # Test specific blueprint retrieval
        print("\n4. Testing specific blueprint retrieval:")
        test_names = ['postgresql', 'redis', 'authentik', 'nginx', 'traefik', 'mongodb']
        for name in test_names:
            bp = loader.get_blueprint(name)
            if bp:
                print(f"   ✓ {name}: Found")
                print(f"     - Platform: {bp.get('platform', 'N/A')}")
                print(f"     - Type: {bp.get('type', 'N/A')}")
                deps = bp.get('dependencies', [])
                print(f"     - Dependencies: {', '.join(deps) if deps else 'None'}")
                ports = bp.get('ports', [])
                print(f"     - Ports: {len(ports)} configured")
            else:
                print(f"   ✗ {name}: Not found")

        # Test search
        print("\n5. Testing blueprint search:")
        results = loader.search_blueprints(query='data')
        print(f"   Search for 'data' found {len(results)} blueprints:")
        for bp in results:
            name = bp.get('name', 'Unknown')
            category = bp.get('category', 'N/A')
            print(f"     - {name} ({category})")

        # Test category filtering
        print("\n6. Testing category filtering:")
        all_blueprints = loader.list_blueprints()
        categories = list(set(bp.get('category') for bp in all_blueprints if bp.get('category')))
        print(f"   Available categories: {', '.join(categories)}")
        for category in categories:
            results = loader.list_blueprints(category=category)
            print(f"     - {category}: {len(results)} blueprints")

        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

    return True

if __name__ == "__main__":
    success = test_blueprint_loader()
    sys.exit(0 if success else 1)
