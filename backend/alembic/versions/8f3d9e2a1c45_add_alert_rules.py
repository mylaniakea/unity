"""add_alert_rules

Revision ID: 8f3d9e2a1c45
Revises: 12df4f8e6ba9
Create Date: 2025-12-22 15:20:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8f3d9e2a1c45'
down_revision = '12df4f8e6ba9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create alert_rules table
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        # What to monitor
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        # Condition
        sa.Column('condition', sa.String(50), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        # Alert settings
        sa.Column('severity', sa.String(50), nullable=False, server_default='warning'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        # Notification settings
        sa.Column('notification_channels', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default='15'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Add indexes for efficient queries
    op.create_index('ix_alert_rules_enabled_resource', 'alert_rules', ['enabled', 'resource_type'])
    op.create_index('ix_alert_rules_created_at', 'alert_rules', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_alert_rules_created_at', 'alert_rules')
    op.drop_index('ix_alert_rules_enabled_resource', 'alert_rules')
    op.drop_table('alert_rules')
