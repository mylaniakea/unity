"""Add plugins table

Revision ID: 00001_add_plugins
Revises: 8f3d9e2a1c45
Create Date: 2026-01-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '00001_add_plugins'
down_revision = '8f3d9e2a1c45'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'plugins',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=50)),
        sa.Column('category', sa.String(length=50)),
        sa.Column('description', sa.Text()),
        sa.Column('author', sa.String(length=255)),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('external', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('plugin_metadata', postgresql.JSON(astext_type=sa.Text())),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text())),
        sa.Column('last_health_check', sa.DateTime(timezone=True)),
        sa.Column('health_status', sa.String(length=50)),
        sa.Column('health_message', sa.Text()),
        sa.Column('last_error', sa.Text()),
        sa.Column('installed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('plugins')
