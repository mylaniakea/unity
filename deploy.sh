#!/bin/bash
# Unity Production Deployment Script
# This script automates the deployment process for Unity

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
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

# Check and create .env file
setup_env() {
    print_info "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_warn ".env file not found. Creating from .env.example..."
            cp .env.example .env
            print_warn "Please edit .env and set required values before continuing!"
            print_warn "Required values:"
            print_warn "  - POSTGRES_PASSWORD (strong password)"
            print_warn "  - JWT_SECRET_KEY (generate with: openssl rand -hex 32)"
            print_warn "  - ENCRYPTION_KEY (generate with: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\")"
            exit 1
        else
            print_error ".env.example not found. Cannot proceed."
            exit 1
        fi
    fi
    
    # Validate critical environment variables
    source .env 2>/dev/null || true
    
    if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "CHANGE_THIS_STRONG_PASSWORD" ]; then
        print_error "POSTGRES_PASSWORD is not set or still has default value. Please update .env file."
        exit 1
    fi
    
    if [ -z "$JWT_SECRET_KEY" ] || [[ "$JWT_SECRET_KEY" == *"CHANGE_THIS"* ]]; then
        print_error "JWT_SECRET_KEY is not set or still has default value. Please update .env file."
        exit 1
    fi
    
    if [ -z "$ENCRYPTION_KEY" ] || [[ "$ENCRYPTION_KEY" == *"CHANGE_THIS"* ]]; then
        print_error "ENCRYPTION_KEY is not set or still has default value. Please update .env file."
        exit 1
    fi
    
    print_info "Environment configuration validated ✓"
}

# Pull images (for production)
pull_images() {
    print_info "Pulling Docker images..."
    docker compose -f docker-compose.prod.yml pull || {
        print_warn "Failed to pull images from GHCR. Will build locally instead."
        return 1
    }
}

# Build images (if needed)
build_images() {
    print_info "Building Docker images..."
    docker compose -f docker-compose.prod.yml build
}

# Start services
start_services() {
    print_info "Starting services..."
    docker compose -f docker-compose.prod.yml up -d
    
    print_info "Waiting for services to be healthy..."
    sleep 10
    
    # Wait for database to be ready
    print_info "Waiting for database to be ready..."
    timeout=60
    elapsed=0
    while ! docker compose -f docker-compose.prod.yml exec -T db pg_isready -U ${POSTGRES_USER:-homelab_user} &> /dev/null; do
        if [ $elapsed -ge $timeout ]; then
            print_error "Database failed to become ready within $timeout seconds"
            exit 1
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    print_info "Database is ready ✓"
}

# Run migrations
run_migrations() {
    print_info "Running database migrations..."
    
    # Wait a bit more for backend to be ready
    sleep 5
    
    docker compose -f docker-compose.prod.yml exec -T backend python -c "
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
        print_warn "Migrations may have failed or already up to date. Continuing..."
    }
    
    print_info "Database migrations completed ✓"
}

# Verify deployment
verify_deployment() {
    print_info "Verifying deployment..."
    
    # Check backend health
    sleep 5
    if curl -f http://localhost:8000/health &> /dev/null; then
        print_info "Backend health check passed ✓"
    else
        print_warn "Backend health check failed. Service may still be starting..."
    fi
    
    # Check frontend
    if curl -f http://localhost/ &> /dev/null; then
        print_info "Frontend is accessible ✓"
    else
        print_warn "Frontend health check failed. Service may still be starting..."
    fi
    
    print_info "Deployment verification complete"
}

# Print deployment info
print_deployment_info() {
    echo ""
    print_info "=========================================="
    print_info "Unity Deployment Complete!"
    print_info "=========================================="
    echo ""
    print_info "Services are running:"
    echo "  - Frontend: http://localhost"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo ""
    print_info "To view logs:"
    echo "  docker compose -f docker-compose.prod.yml logs -f"
    echo ""
    print_info "To stop services:"
    echo "  docker compose -f docker-compose.prod.yml down"
    echo ""
    print_warn "Next steps:"
    echo "  1. Create an admin user (see DEPLOY.md)"
    echo "  2. Configure plugins via the web interface"
    echo "  3. Set up SSL/TLS if exposing externally"
    echo ""
}

# Main deployment flow
main() {
    echo ""
    print_info "Starting Unity deployment..."
    echo ""
    
    check_prerequisites
    setup_env
    pull_images || build_images
    start_services
    run_migrations
    verify_deployment
    print_deployment_info
}

# Run main function
main "$@"

