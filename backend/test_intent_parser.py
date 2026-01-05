"""
Test suite for AI Intent Parser

This demonstrates the intent parser's capabilities with various deployment commands.
Run with: python -m pytest test_intent_parser.py -v
Or manually: python test_intent_parser.py
"""

import asyncio
import json
from app.database import SessionLocal
from app.services.orchestration.intent_parser import IntentParser


async def test_intent_parser():
    """Test the intent parser with various commands"""

    # Create database session
    db = SessionLocal()

    try:
        # Initialize parser
        print("\n" + "="*80)
        print("AI INTENT PARSER TEST SUITE")
        print("="*80 + "\n")

        parser = IntentParser(db)

        # Test commands
        test_commands = [
            "install authentik",
            "get postgres running with 10GB storage",
            "scale nginx to 3 replicas",
            "remove redis",
            "deploy traefik with letsencrypt on example.com",
            "update grafana to version 10",
            "restart jenkins",
            "check status of nextcloud",
            "setup mysql with 5GB storage and version 8.0",
            "install home-assistant",
            "deploy portainer",
            "remove uptime-kuma completely",
            "scale down authentik to 1 replica",
            "get minio running for s3 storage"
        ]

        results = []

        for i, command in enumerate(test_commands, 1):
            print(f"\n{'='*80}")
            print(f"TEST {i}/{len(test_commands)}: {command}")
            print('='*80)

            try:
                # Parse command
                intent = await parser.parse_command(command)

                # Generate conversational response
                response = await parser.generate_conversational_response(intent)

                # Build deployment intent
                deployment_intent = parser.build_deployment_intent(intent)

                # Display results
                print(f"\n📋 PARSED INTENT:")
                print(f"   Action:       {intent['action']}")
                print(f"   Application:  {intent['application']}")
                print(f"   Confidence:   {intent['confidence']:.2f}")
                print(f"   Platform:     {intent.get('suggested_platform', 'N/A')}")

                if intent.get('parameters'):
                    print(f"\n⚙️  PARAMETERS:")
                    for key, value in intent['parameters'].items():
                        print(f"   - {key}: {value}")

                if intent.get('dependencies'):
                    print(f"\n🔗 DEPENDENCIES:")
                    for dep in intent['dependencies']:
                        print(f"   - {dep}")

                print(f"\n💭 REASONING:")
                print(f"   {intent.get('reasoning', 'N/A')}")

                if intent.get('clarifications_needed'):
                    print(f"\n❓ CLARIFICATIONS NEEDED:")
                    for q in intent['clarifications_needed']:
                        print(f"   - {q}")

                print(f"\n🤖 CONVERSATIONAL RESPONSE:")
                print("   " + response.replace("\n", "\n   "))

                print(f"\n📦 DEPLOYMENT INTENT:")
                print(f"   ID:              {deployment_intent['intent_id']}")
                print(f"   Status:          {deployment_intent['status']}")
                print(f"   Requires Conf.:  {deployment_intent['requires_confirmation']}")
                print(f"   Namespace:       {deployment_intent['namespace']}")

                results.append({
                    "command": command,
                    "success": True,
                    "intent": intent,
                    "deployment_intent": deployment_intent
                })

            except Exception as e:
                print(f"\n❌ ERROR: {e}")
                results.append({
                    "command": command,
                    "success": False,
                    "error": str(e)
                })

        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80 + "\n")

        success_count = sum(1 for r in results if r['success'])
        total_count = len(results)

        print(f"✅ Successful: {success_count}/{total_count}")
        print(f"❌ Failed:     {total_count - success_count}/{total_count}")

        # Show confidence distribution
        confidences = [r['intent']['confidence'] for r in results if r['success']]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            print(f"\n📊 Average Confidence: {avg_confidence:.2f}")
            print(f"   High (>0.8):   {sum(1 for c in confidences if c > 0.8)}")
            print(f"   Medium (0.5-0.8): {sum(1 for c in confidences if 0.5 <= c <= 0.8)}")
            print(f"   Low (<0.5):    {sum(1 for c in confidences if c < 0.5)}")

        # Show action distribution
        actions = [r['intent']['action'] for r in results if r['success']]
        print(f"\n📈 Actions:")
        for action in set(actions):
            count = actions.count(action)
            print(f"   {action}: {count}")

        print("\n" + "="*80 + "\n")

        return results

    finally:
        db.close()


async def test_specific_methods():
    """Test individual parser methods"""

    print("\n" + "="*80)
    print("TESTING INDIVIDUAL METHODS")
    print("="*80 + "\n")

    db = SessionLocal()
    parser = IntentParser(db)

    try:
        # Test extract_intent
        print("1. Testing extract_intent():")
        command = "scale nginx to 5 replicas"
        action = await parser.extract_intent(command)
        print(f"   Command: {command}")
        print(f"   Action: {action}\n")

        # Test extract_application
        print("2. Testing extract_application():")
        command = "install postgresql with 20GB storage"
        app = await parser.extract_application(command)
        print(f"   Command: {command}")
        print(f"   Application: {app}\n")

        # Test extract_parameters
        print("3. Testing extract_parameters():")
        command = "deploy authentik with 3 replicas on auth.example.com"
        params = await parser.extract_parameters(command)
        print(f"   Command: {command}")
        print(f"   Parameters: {json.dumps(params, indent=2)}\n")

        # Test gather_context
        print("4. Testing gather_context():")
        context = await parser.gather_context()
        print(f"   Cluster: {context.get('cluster_info', {}).get('name', 'N/A')}")
        print(f"   Deployments: {len(context.get('existing_deployments', []))}")
        print(f"   Blueprints: {len(context.get('available_blueprints', []))}\n")

    finally:
        db.close()


async def test_edge_cases():
    """Test edge cases and error handling"""

    print("\n" + "="*80)
    print("TESTING EDGE CASES")
    print("="*80 + "\n")

    db = SessionLocal()
    parser = IntentParser(db)

    edge_cases = [
        "",  # Empty command
        "hello world",  # Nonsense
        "install",  # Missing application
        "postgres",  # Missing action
        "deploy some unknown app that doesn't exist",  # Unknown app
        "!!!###$$$",  # Special characters
        "install postgrs",  # Typo
        "scale to 5",  # Missing application
    ]

    try:
        for i, command in enumerate(edge_cases, 1):
            print(f"\n{i}. Command: '{command}'")
            try:
                intent = await parser.parse_command(command)
                print(f"   Result: {intent['action']} - {intent.get('application', 'N/A')}")
                print(f"   Confidence: {intent['confidence']:.2f}")
                if intent.get('clarifications_needed'):
                    print(f"   Clarifications: {len(intent['clarifications_needed'])}")
            except Exception as e:
                print(f"   Error: {e}")

    finally:
        db.close()


def main():
    """Main test runner"""
    print("\n🚀 Starting Intent Parser Tests...\n")

    # Run all tests
    asyncio.run(test_intent_parser())
    asyncio.run(test_specific_methods())
    asyncio.run(test_edge_cases())

    print("\n✅ All tests completed!\n")


if __name__ == "__main__":
    main()
