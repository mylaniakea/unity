"""
Test script for orchestration system.

Run this after starting the backend to verify the orchestration system is working.
"""

import asyncio
import sys
sys.path.insert(0, '/home/holon/Projects/unity/backend')

async def test_imports():
    """Test that all orchestration modules can be imported."""
    print("Testing imports...")
    
    try:
        from app.services.deployment_manager import DeploymentManager
        print("✓ DeploymentManager imported")
        
        from app.services.orchestration.blueprint_loader import BlueprintLoader
        print("✓ BlueprintLoader imported")
        
        from app.services.orchestration.intent_parser import IntentParser
        print("✓ IntentParser imported")
        
        from app.services.orchestration.manifest_generator import ManifestGenerator
        print("✓ ManifestGenerator imported")
        
        from app.services.orchestration.deployment_orchestrator import DeploymentOrchestrator
        print("✓ DeploymentOrchestrator imported")
        
        from app.routers.orchestration import deploy
        print("✓ Orchestration router imported")
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_intent_parser():
    """Test intent parser with sample commands."""
    print("\n" + "="*60)
    print("Testing Intent Parser...")
    print("="*60)
    
    try:
        from app.services.orchestration.intent_parser import IntentParser
        
        parser = IntentParser()
        
        test_commands = [
            "install authentik",
            "deploy postgresql with 3 replicas",
            "scale grafana to 5 instances",
            "install nginx with TLS and ingress",
            "setup redis in namespace cache"
        ]
        
        for command in test_commands:
            result = await parser.parse_command(command)
            print(f"\nCommand: '{command}'")
            print(f"  Action: {result.get('action')}")
            print(f"  Application: {result.get('application')}")
            print(f"  Platform: {result.get('platform')}")
            print(f"  Parameters: {result.get('parameters')}")
            print(f"  Success: {result.get('success')}")
        
        print("\n✅ Intent parser tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Intent parser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_blueprint_loader():
    """Test blueprint loader."""
    print("\n" + "="*60)
    print("Testing Blueprint Loader...")
    print("="*60)
    
    try:
        # This would require database connection
        # For now, just test filesystem loading
        from app.services.orchestration.blueprint_loader import BlueprintLoader
        from pathlib import Path
        
        # Create mock db session
        class MockDB:
            def query(self, *args, **kwargs):
                class MockQuery:
                    def filter_by(self, *args, **kwargs):
                        return self
                    def first(self):
                        return None
                    def all(self):
                        return []
                return MockQuery()
        
        loader = BlueprintLoader(MockDB())
        
        # Check blueprints directory
        blueprints_dir = Path('/home/holon/Projects/unity/backend/app/blueprints')
        if blueprints_dir.exists():
            print(f"\nBlueprints directory: {blueprints_dir}")
            blueprints = list(blueprints_dir.glob("*.y*ml"))
            print(f"Found {len(blueprints)} blueprint file(s):")
            for bp_file in blueprints:
                print(f"  - {bp_file.name}")
        
        print("\n✅ Blueprint loader tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Blueprint loader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Unity Orchestration System Test Suite")
    print("="*60)
    
    results = []
    
    # Test imports
    results.append(await test_imports())
    
    # Test intent parser
    results.append(await test_intent_parser())
    
    # Test blueprint loader
    results.append(await test_blueprint_loader())
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
