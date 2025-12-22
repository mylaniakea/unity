"""
API Test Script

Tests REST endpoints and WebSocket connections.
"""
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


async def test_rest_endpoints():
    """Test all REST API endpoints."""
    print("="*60)
    print("Testing REST API Endpoints")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        # Test root endpoint
        print("\n1. Testing root endpoint...")
        response = await client.get(f"{BASE_URL}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test health check
        print("\n2. Testing health check...")
        response = await client.get(f"{BASE_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test list plugins
        print("\n3. Testing list plugins...")
        response = await client.get(f"{BASE_URL}/api/plugins")
        plugins = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Found {len(plugins)} plugins")
        if plugins:
            print(f"   First plugin: {plugins[0]['plugin_id']}")
        
        # Test get plugin details
        if plugins:
            plugin_id = plugins[0]['plugin_id']
            print(f"\n4. Testing get plugin details ({plugin_id})...")
            response = await client.get(f"{BASE_URL}/api/plugins/{plugin_id}")
            print(f"   Status: {response.status_code}")
            print(f"   Plugin: {response.json()['name']}")
            
            # Test plugin status
            print(f"\n5. Testing plugin status ({plugin_id})...")
            response = await client.get(f"{BASE_URL}/api/plugins/{plugin_id}/status")
            if response.status_code == 200:
                status = response.json()
                print(f"   Status: {response.status_code}")
                print(f"   Health: {status['health_status']}")
            else:
                print(f"   Status: {response.status_code} (no status yet - needs collection)")
            
            # Test plugin metrics
            print(f"\n6. Testing plugin metrics ({plugin_id})...")
            response = await client.get(f"{BASE_URL}/api/plugins/{plugin_id}/metrics?limit=5")
            if response.status_code == 200:
                metrics = response.json()
                print(f"   Status: {response.status_code}")
                print(f"   Metrics count: {len(metrics)}")
                if metrics:
                    print(f"   Latest metric: {metrics[0]['metric_name']} at {metrics[0]['time']}")
            else:
                print(f"   Status: {response.status_code} (no metrics yet)")
            
            # Test plugin executions
            print(f"\n7. Testing plugin executions ({plugin_id})...")
            response = await client.get(f"{BASE_URL}/api/plugins/{plugin_id}/executions?limit=5")
            if response.status_code == 200:
                executions = response.json()
                print(f"   Status: {response.status_code}")
                print(f"   Executions count: {len(executions)}")
                if executions:
                    print(f"   Latest: {executions[0]['status']} at {executions[0]['started_at']}")
            else:
                print(f"   Status: {response.status_code}")
        
        # Test stats summary
        print("\n8. Testing stats summary...")
        response = await client.get(f"{BASE_URL}/api/plugins/stats/summary")
        print(f"   Status: {response.status_code}")
        stats = response.json()
        print(f"   Total plugins: {stats['total_plugins']}")
        print(f"   Enabled: {stats['enabled_plugins']}")
        print(f"   Total metrics: {stats['total_metrics']}")
        print(f"   Total executions: {stats['total_executions']}")
        
        # Test categories
        print("\n9. Testing categories list...")
        response = await client.get(f"{BASE_URL}/api/plugins/categories/list")
        print(f"   Status: {response.status_code}")
        categories = response.json()['categories']
        print(f"   Categories: {', '.join(categories)}")


async def test_websocket():
    """Test WebSocket connection."""
    print("\n" + "="*60)
    print("Testing WebSocket Connection")
    print("="*60)
    
    try:
        import websockets
    except ImportError:
        print("⚠️  websockets package not installed. Run: pip install websockets")
        return
    
    try:
        uri = "ws://localhost:8000/ws/metrics"
        print(f"\nConnecting to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Receive welcome message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"\n📨 Received: {data['type']}")
            print(f"   Message: {data.get('message', 'N/A')}")
            
            # Send ping
            print("\n📤 Sending ping...")
            await websocket.send(json.dumps({"type": "ping"}))
            
            # Wait for pong
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📨 Received: {data['type']}")
            
            # Listen for events (30 seconds)
            print("\n⏳ Listening for events (30 seconds)...")
            print("   (Metrics will appear when plugins collect data)")
            
            try:
                for i in range(3):  # Listen for 3 messages or 30s
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    
                    if data['type'] == 'metrics:update':
                        print(f"\n📊 Metrics Update:")
                        print(f"   Plugin: {data['plugin_id']}")
                        print(f"   Metrics keys: {list(data['metrics'].keys())[:5]}")
                    elif data['type'] == 'execution:complete':
                        print(f"\n✅ Execution Complete:")
                        print(f"   Plugin: {data['plugin_id']}")
                        print(f"   Status: {data['execution']['status']}")
                        print(f"   Metrics count: {data['execution']['metrics_count']}")
                    elif data['type'] == 'heartbeat':
                        print(f"💓 Heartbeat received")
                    else:
                        print(f"\n📨 Event: {data['type']}")
                        
            except asyncio.TimeoutError:
                print("\n⏱️  Timeout waiting for events (this is normal if no plugins are collecting)")
            
            print("\n✅ WebSocket test complete")
            
    except Exception as e:
        print(f"\n❌ WebSocket error: {e}")
        print("   Make sure the API server is running!")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Unity API Test Suite")
    print("="*60)
    print(f"Started at: {datetime.now()}")
    print(f"Target: {BASE_URL}")
    
    try:
        # Test REST endpoints
        await test_rest_endpoints()
        
        # Test WebSocket
        await test_websocket()
        
        print("\n" + "="*60)
        print("✅ All Tests Complete!")
        print("="*60)
        
    except httpx.ConnectError:
        print("\n❌ Connection Error!")
        print("   Make sure the API server is running:")
        print("   cd backend && python3 app/main.py")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
