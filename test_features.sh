#!/bin/bash

echo "🧪 Testing Lekhak AI Features..."
echo ""

# Test 1: Health check
echo "1️⃣ Testing health endpoint..."
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""

# Test 2: Feature list
echo "2️⃣ Testing feature list..."
curl -s http://localhost:8000/admin/features | python3 -m json.tool
echo ""

# Test 3: Root endpoint
echo "3️⃣ Testing root endpoint..."
curl -s http://localhost:8000/ | python3 -m json.tool
echo ""

echo "✅ All tests complete!"
