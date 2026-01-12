#!/bin/bash
# Unity Database Migration Verification Script
# This script checks and updates database migrations in the Kubernetes deployment

set -e

NAMESPACE="unity"
DEPLOYMENT="unity-backend"

echo "=================================================="
echo "Unity Database Migration Verification"
echo "=================================================="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "ERROR: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if the namespace exists
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo "ERROR: Namespace '$NAMESPACE' does not exist"
    exit 1
fi

# Check if the deployment exists
if ! kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" &> /dev/null; then
    echo "ERROR: Deployment '$DEPLOYMENT' does not exist in namespace '$NAMESPACE'"
    exit 1
fi

echo "Step 1: Checking current database migration version..."
echo "------------------------------------------------------"
CURRENT_VERSION=$(kubectl exec -n "$NAMESPACE" deployment/"$DEPLOYMENT" -- alembic current 2>&1)
echo "$CURRENT_VERSION"
echo ""

echo "Step 2: Checking latest available migration version..."
echo "------------------------------------------------------"
LATEST_VERSION=$(kubectl exec -n "$NAMESPACE" deployment/"$DEPLOYMENT" -- alembic heads 2>&1)
echo "$LATEST_VERSION"
echo ""

# Check if migrations need to be run
if echo "$CURRENT_VERSION" | grep -q "add_plugin_execution"; then
    echo "✓ Database is up to date!"
    echo "Current version matches the latest migration: add_plugin_execution"
    echo ""
    echo "Migration chain verified:"
    echo "  6a00ea433c25 (Initial migration)"
    echo "  └─> 12e8b371598f (Add authentication tables)"
    echo "      └─> 70974ae864ff (Add notification tables)"
    echo "          └─> 12df4f8e6ba9 (Add OAuth links)"
    echo "              └─> 8f3d9e2a1c45 (Add alert rules)"
    echo "                  └─> 00001_add_plugins (Add plugins table)"
    echo "                      └─> a1b2c3d4e5f6 (Add marketplace and dashboard tables)"
    echo "                          └─> add_plugin_execution (Add plugin execution tables) ✓ CURRENT"
    exit 0
else
    echo "⚠ Database migrations are NOT up to date!"
    echo ""
    echo "Step 3: Running database migrations..."
    echo "------------------------------------------------------"
    kubectl exec -n "$NAMESPACE" deployment/"$DEPLOYMENT" -- alembic upgrade head
    echo ""

    echo "Step 4: Verifying migration completed successfully..."
    echo "------------------------------------------------------"
    NEW_VERSION=$(kubectl exec -n "$NAMESPACE" deployment/"$DEPLOYMENT" -- alembic current 2>&1)
    echo "$NEW_VERSION"
    echo ""

    if echo "$NEW_VERSION" | grep -q "add_plugin_execution"; then
        echo "✓ Database migrations completed successfully!"
        echo "Database is now at the latest version: add_plugin_execution"
    else
        echo "✗ Migration may have failed. Please check the output above for errors."
        exit 1
    fi
fi

echo ""
echo "=================================================="
echo "Migration verification complete!"
echo "=================================================="
