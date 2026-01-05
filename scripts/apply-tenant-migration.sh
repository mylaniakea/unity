#!/bin/bash
# Apply tenant support migration to Unity database
# This adds tenant_id to all tables for multi-tenancy support

set -e

echo "⚠️  This will modify your database schema to add tenant support."
echo "   A backup will be created first."
echo ""
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "1. Creating backup..."
./scripts/backup-database.sh

echo ""
echo "2. Applying tenant migration (this may take a few minutes)..."
echo "   Creating tenants table..."
docker exec homelab-db psql -U homelab_user -d homelab_db -c "
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'free',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    resource_quota JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
INSERT INTO tenants (id, name, plan, status) VALUES ('default', 'Default Tenant', 'unlimited', 'active') 
ON CONFLICT DO NOTHING;
" 

echo "   Adding tenant_id columns (25 tables)..."
for table in users plugins plugin_executions plugin_metrics plugin_api_keys kubernetes_clusters kubernetes_resources deployment_intents application_blueprints resource_reconciliations server_profiles server_snapshots server_credentials ssh_keys certificates credential_audit_logs step_ca_config alerts alert_channels threshold_rules notification_logs knowledge reports settings push_subscriptions; do
    echo "     - $table"
    docker exec homelab-db psql -U homelab_user -d homelab_db -c "
        ALTER TABLE $table ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50);
        UPDATE $table SET tenant_id = 'default' WHERE tenant_id IS NULL;
        ALTER TABLE $table ALTER COLUMN tenant_id SET NOT NULL;
        ALTER TABLE $table ADD CONSTRAINT IF NOT EXISTS fk_${table}_tenant 
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
        CREATE INDEX IF NOT EXISTS idx_${table}_tenant ON $table(tenant_id);
    " 2>&1 | grep -v "already exists" || true
done

echo ""
echo "3. Creating user_tenant_memberships table..."
docker exec homelab-db psql -U homelab_user -d homelab_db -c "
CREATE TABLE IF NOT EXISTS user_tenant_memberships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, tenant_id)
);
CREATE INDEX IF NOT EXISTS idx_user_tenant_user ON user_tenant_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tenant_tenant ON user_tenant_memberships(tenant_id);

INSERT INTO user_tenant_memberships (user_id, tenant_id, role)
SELECT id, 'default', 'admin' FROM users
WHERE id NOT IN (SELECT user_id FROM user_tenant_memberships);
"

echo ""
echo "4. Updating Alembic version..."
docker exec homelab-db psql -U homelab_user -d homelab_db -c "
UPDATE alembic_version SET version_num = 'tenant_support_001';
"

echo ""
echo "✅ Tenant migration complete!"
echo ""
echo "Verify with:"
echo "  docker exec homelab-db psql -U homelab_user -d homelab_db -c '\\dt'"
echo "  docker exec homelab-db psql -U homelab_user -d homelab_db -c 'SELECT * FROM tenants;'"
