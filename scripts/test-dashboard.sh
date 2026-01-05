#!/bin/bash
# Dashboard connectivity test

echo "🔍 Testing Unity Dashboard..."
echo ""

# Test 1: Frontend accessible
echo "1. Testing frontend (http://localhost)..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
    echo "   ✅ Frontend responding"
else
    echo "   ❌ Frontend not accessible"
    exit 1
fi

# Test 2: Backend API accessible
echo "2. Testing backend API (http://localhost:8000)..."
RESPONSE=$(curl -s http://localhost:8000/)
if echo "$RESPONSE" | grep -q "Unity"; then
    echo "   ✅ Backend API responding: $RESPONSE"
else
    echo "   ❌ Backend API not responding correctly"
    exit 1
fi

# Test 3: Backend through nginx proxy
echo "3. Testing API proxy through frontend..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/)
if [ "$STATUS" = "200" ] || [ "$STATUS" = "404" ]; then
    echo "   ✅ Nginx proxy working (status: $STATUS)"
else
    echo "   ❌ Nginx proxy not working (status: $STATUS)"
    exit 1
fi

# Test 4: Database connectivity
echo "4. Testing database connection..."
if docker exec homelab-db pg_isready -U homelab_user > /dev/null 2>&1; then
    echo "   ✅ PostgreSQL accessible"
else
    echo "   ❌ PostgreSQL not accessible"
    exit 1
fi

# Test 5: Check some API endpoints
echo "5. Testing API endpoints..."
ENDPOINTS=$(curl -s http://localhost:8000/openapi.json | grep -o '"paths"' | wc -l)
if [ "$ENDPOINTS" -gt 0 ]; then
    echo "   ✅ API documentation available"
else
    echo "   ❌ API documentation not available"
fi

echo ""
echo "✅ All connectivity tests passed!"
echo ""
echo "🌐 Access the dashboard:"
echo "   Frontend: http://localhost"
echo "   API Docs: http://localhost:8000/docs"
echo "   Direct API: http://localhost:8000"
echo ""
echo "📝 To verify the dashboard works:"
echo "   1. Open http://localhost in your browser"
echo "   2. Check for login page or dashboard"
echo "   3. Try logging in (default: admin/admin123)"
echo "   4. Verify you can see system stats and navigation"
