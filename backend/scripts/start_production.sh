#!/bin/bash
# Production startup script for Unity backend

set -e  # Exit on error

echo "🚀 Starting Unity Production Server..."

# Check if virtual environment exists
if [ ! -d ".venv" ] && [ ! -d ".venv_new" ]; then
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv .venv
fi

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d ".venv_new" ]; then
    source .venv_new/bin/activate
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️  Please edit .env and set required values before continuing!"
        exit 1
    else
        echo "❌ .env.example not found. Cannot proceed."
        exit 1
    fi
fi

# Check if database migration is needed
echo "📊 Checking database migration status..."
if command -v alembic &> /dev/null; then
    CURRENT_REV=$(alembic current 2>/dev/null | grep -oP '^\w+' || echo "none")
    HEAD_REV=$(alembic heads 2>/dev/null | grep -oP '^\w+' || echo "none")
    
    if [ "$CURRENT_REV" != "$HEAD_REV" ]; then
        echo "⚠️  Database migration needed. Current: $CURRENT_REV, Head: $HEAD_REV"
        echo "📦 Running database migration..."
        alembic upgrade head
        echo "✅ Migration complete"
    else
        echo "✅ Database is up to date"
    fi
else
    echo "⚠️  Alembic not found. Skipping migration check."
fi

# Check dependencies
echo "📦 Checking dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the server
echo "🎉 Starting Unity API server..."
echo "📍 API will be available at: http://0.0.0.0:8000"
echo "📚 API docs will be available at: http://0.0.0.0:8000/docs"
echo ""

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    --no-access-log

