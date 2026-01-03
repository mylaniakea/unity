#!/bin/bash
# Quick setup script for local testing

set -e

echo "🔧 Setting up Unity for local testing..."
echo ""

# 1. Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ .env file created"
    echo "⚠️  Note: Using default values for local testing"
else
    echo "✅ .env file already exists"
fi

# 2. Check Docker
echo ""
echo "🐳 Checking Docker..."
if docker info > /dev/null 2>&1; then
    echo "✅ Docker is running"
else
    echo "❌ Docker daemon is not running"
    echo ""
    echo "Please start Docker Desktop or OrbStack, then run this script again."
    exit 1
fi

# 3. Check Docker Compose
echo ""
echo "📦 Checking Docker Compose..."
if docker compose version > /dev/null 2>&1; then
    echo "✅ Docker Compose is available"
else
    echo "❌ Docker Compose not found"
    exit 1
fi

echo ""
echo "✅ Setup complete! You can now run:"
echo "   ./test-local.sh"
echo ""
echo "Or manually:"
echo "   docker compose up -d --build"

