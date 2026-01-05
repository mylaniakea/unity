"""add tenant support

Revision ID: tenant_support_001
Revises: e1d0454ae532
Create Date: 2026-01-05 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'tenant_support_001'
down_revision = 'e1d0454ae532'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('schema_name', sa.String(63), nullable=True, comment='For schema-per-tenant mode'),
        sa.Column('plan', sa.String(50), nullable=False, server_default='free'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('resource_quota', postgresql.JSONB, nullable=True, comment='CPU, memory, storage limits'),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deleted_at', sa.TIMESTAMP, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True, comment='Custom tenant properties'),
    )
    op.create_index('idx_tenants_status', 'tenants', ['status'])
    
    # Create user_tenant_memberships junction table
    op.create_table(
        'user_tenant_memberships',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, comment='admin, member, viewer'),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'tenant_id', name='uq_user_tenant')
    )
    op.create_index('idx_user_tenant_user', 'user_tenant_memberships', ['user_id'])
    op.create_index('idx_user_tenant_tenant', 'user_tenant_memberships', ['tenant_id'])
    
    # Insert default tenant
    op.execute("""
        INSERT INTO tenants (id, name, plan, status, resource_quota)
        VALUES (
            'default',
            'Default Tenant',
            'unlimited',
            'active',
            '{"kubernetes_clusters": 999, "plugins": 999, "users": 999, "api_calls_per_hour": 999999}'::jsonb
        )
    """)
    
    # List of all tables that need tenant_id
    tables = [
        'users',
        'plugins',
        'plugin_executions',
        'plugin_metrics',
        'plugin_api_keys',
        'kubernetes_clusters',
        'kubernetes_resources',
        'deployment_intents',
        'application_blueprints',
        'resource_reconciliations',
        'server_profiles',
        'server_snapshots',
        'server_credentials',
        'ssh_keys',
        'certificates',
        'credential_audit_logs',
        'step_ca_config',
        'alerts',
        'alert_channels',
        'threshold_rules',
        'notification_logs',
        'knowledge',
        'reports',
        'settings',
        'push_subscriptions',
    ]
    
    # Add tenant_id column to all tables
    for table in tables:
        op.add_column(table, sa.Column('tenant_id', sa.String(50), nullable=True))
        
    # Set existing rows to default tenant
    for table in tables:
        op.execute(f"UPDATE {table} SET tenant_id = 'default' WHERE tenant_id IS NULL")
    
    # Make tenant_id NOT NULL and add foreign key
    for table in tables:
        op.alter_column(table, 'tenant_id', nullable=False)
        op.create_foreign_key(
            f'fk_{table}_tenant',
            table, 'tenants',
            ['tenant_id'], ['id'],
            ondelete='RESTRICT'
        )
        op.create_index(f'idx_{table}_tenant', table, ['tenant_id'])
    
    # Migrate existing users to default tenant
    op.execute("""
        INSERT INTO user_tenant_memberships (user_id, tenant_id, role)
        SELECT id, 'default', 'admin'
        FROM users
        WHERE id NOT IN (SELECT user_id FROM user_tenant_memberships)
    """)


def downgrade() -> None:
    # List of all tables that have tenant_id
    tables = [
        'users', 'plugins', 'plugin_executions', 'plugin_metrics', 'plugin_api_keys',
        'kubernetes_clusters', 'kubernetes_resources', 'deployment_intents',
        'application_blueprints', 'resource_reconciliations', 'server_profiles',
        'server_snapshots', 'server_credentials', 'ssh_keys', 'certificates',
        'credential_audit_logs', 'step_ca_config', 'alerts', 'alert_channels',
        'threshold_rules', 'notification_logs', 'knowledge', 'reports',
        'settings', 'push_subscriptions',
    ]
    
    # Drop foreign keys, indexes, and columns
    for table in tables:
        op.drop_constraint(f'fk_{table}_tenant', table, type_='foreignkey')
        op.drop_index(f'idx_{table}_tenant', table)
        op.drop_column(table, 'tenant_id')
    
    # Drop user_tenant_memberships table
    op.drop_index('idx_user_tenant_tenant', 'user_tenant_memberships')
    op.drop_index('idx_user_tenant_user', 'user_tenant_memberships')
    op.drop_table('user_tenant_memberships')
    
    # Drop tenants table
    op.drop_index('idx_tenants_status', 'tenants')
    op.drop_table('tenants')
