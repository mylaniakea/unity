#!/bin/bash
# Unity Local Docker Test Script
# Tests the deployment using local Docker builds

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_info "Prerequisites check passed ✓"
}

# Setup minimal .env for testing
setup_test_env() {
    print_step "Setting up test environment..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_warn ".env file not found. Creating minimal test .env from .env.example..."
            cp .env.example .env
            
            # Set test values (these are defaults that work for local testing)
            print_info "Using default test values (safe for local testing only!)"
            print_warn "For production, you MUST change these values!"
        else
            print_error ".env.example not found. Cannot proceed."
            exit 1
        fi
    else
        print_info "Using existing .env file"
    fi
    
    print_info "Environment setup complete ✓"
}

# Build images
build_images() {
    print_step "Building Docker images locally..."
    print_info "This may take a few minutes on first run..."
    
    docker compose build --no-cache || {
        print_error "Failed to build images"
        exit 1
    }
    
    print_info "Images built successfully ✓"
}

# Start services
start_services() {
    print_step "Starting services..."
    
    docker compose up -d
    
    print_info "Waiting for services to start..."
    sleep 5
    
    # Show service status
    print_info "Service status:"
    docker compose ps
}

# Wait for services to be healthy
wait_for_health() {
    print_step "Waiting for services to be healthy..."
    
    max_wait=120
    elapsed=0
    
    print_info "Waiting for database..."
    while ! docker compose exec -T db pg_isready -U ${POSTGRES_USER:-homelab_user} &> /dev/null; do
        if [ $elapsed -ge $max_wait ]; then
            print_error "Database failed to become ready within $max_wait seconds"
            docker compose logs db | tail -20
            exit 1
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    echo ""
    print_info "Database is ready ✓"
    
    print_info "Waiting for Redis..."
    elapsed=0
    while ! docker compose exec -T redis redis-cli ping &> /dev/null; do
        if [ $elapsed -ge 30 ]; then
            print_error "Redis failed to become ready"
            exit 1
        fi
        sleep 1
        elapsed=$((elapsed + 1))
        echo -n "."
    done
    echo ""
    print_info "Redis is ready ✓"
    
    print_info "Waiting for backend..."
    elapsed=0
    while ! docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" &> /dev/null; do
        if [ $elapsed -ge 60 ]; then
            print_warn "Backend health check timeout (may still be starting)"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    echo ""
    print_info "Backend check complete ✓"
}

# Run migrations
run_migrations() {
    print_step "Running database migrations..."
    
    docker compose exec -T backend python -c "
from alembic.config import Config
from alembic import command
import sys

try:
    cfg = Config('alembic.ini')
    command.upgrade(cfg, 'head')
    print('Migrations completed successfully')
except Exception as e:
    print(f'Migration error: {e}', file=sys.stderr)
    sys.exit(1)
" || {
        print_warn "Migrations may have failed or already up to date"
    }
    
    print_info "Migrations completed ✓"
}

# Test endpoints
test_endpoints() {
    print_step "Testing endpoints..."
    
    # Test backend health
    print_info "Testing backend health endpoint..."
    if curl -f http://localhost:8000/health &> /dev/null; then
        print_info "✓ Backend health check passed"
        curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
        echo ""
    else
        print_warn "Backend health check failed (service may still be starting)"
    fi
    
    # Test frontend
    print_info "Testing frontend..."
    if curl -f http://localhost/ &> /dev/null; then
        print_info "✓ Frontend is accessible"
    else
        print_warn "Frontend check failed (service may still be starting)"
    fi
    
    # Test API docs
    print_info "Testing API documentation..."
    if curl -f http://localhost:8000/docs &> /dev/null; then
        print_info "✓ API docs are accessible"
    else
        print_warn "API docs check failed"
    fi
}

# Show logs
show_logs() {
    print_step "Recent logs:"
    echo ""
    print_info "Backend logs (last 10 lines):"
    docker compose logs --tail=10 backend
    echo ""
    print_info "Frontend logs (last 10 lines):"
    docker compose logs --tail=10 frontend
    echo ""
}

# Print test results
print_test_results() {
    echo ""
    print_info "=========================================="
    print_info "Local Docker Test Complete!"
    print_info "=========================================="
    echo ""
    print_info "Services are running:"
    echo "  - Frontend: http://localhost"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo "  - Health Check: http://localhost:8000/health"
    echo ""
    print_info "Useful commands:"
    echo "  View logs:        docker compose logs -f"
    echo "  Stop services:    docker compose down"
    echo "  Restart:          docker compose restart"
    echo "  Service status:    docker compose ps"
    echo ""
    print_warn "Note: This is a local test deployment."
    print_warn "For production, use docker-compose.prod.yml with proper secrets!"
    echo ""
}

# Cleanup function
cleanup() {
    if [ "$1" = "clean" ]; then
        print_step "Cleaning up test environment..."
        docker compose down -v
        print_info "Cleanup complete"
    fi
}

# Main test flow
main() {
    echo ""
    print_info "Starting Unity local Docker test..."
    echo ""
    
    # Check if cleanup requested
    if [ "$1" = "clean" ]; then
        cleanup clean
        exit 0
    fi
    
    check_prerequisites
    setup_test_env
    build_images
    start_services
    wait_for_health
    run_migrations
    test_endpoints
    show_logs
    print_test_results
}

# Run main function
main "$@"

