"""add plugin execution tables

Revision ID: add_plugin_execution
Revises: a1b2c3d4e5f6
Create Date: 2026-01-03 22:15:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'add_plugin_execution'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Create plugin_executions table
    op.create_table(
        'plugin_executions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plugin_id', sa.String(100), nullable=False, index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, index=True, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='running'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metrics_count', sa.Integer(), default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['plugin_id'], ['plugins.id'], ondelete='CASCADE')
    )
    
    # Create plugin_metrics table
    op.create_table(
        'plugin_metrics',
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('plugin_id', sa.String(100), nullable=False),
        sa.Column('metric_name', sa.String(200), nullable=False),
        sa.Column('value', JSONB, nullable=False),
        sa.Column('tags', JSONB, nullable=True),
        sa.PrimaryKeyConstraint('timestamp', 'plugin_id', 'metric_name'),
        sa.ForeignKeyConstraint(['plugin_id'], ['plugins.id'], ondelete='CASCADE')
    )
    
    # Create index for common queries
    op.create_index('idx_metrics_plugin_time', 'plugin_metrics', ['plugin_id', 'timestamp'])
    
    # Create plugin_alerts table
    op.create_table(
        'plugin_alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plugin_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('condition', JSONB, nullable=False),
        sa.Column('severity', sa.String(20), default='warning'),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['plugin_id'], ['plugins.id'], ondelete='CASCADE')
    )


def downgrade():
    op.drop_table('plugin_alerts')
    op.drop_index('idx_metrics_plugin_time')
    op.drop_table('plugin_metrics')
    op.drop_table('plugin_executions')
