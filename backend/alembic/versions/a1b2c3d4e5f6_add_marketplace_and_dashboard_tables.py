"""Add marketplace and dashboard tables

Revision ID: marketplace_dashboard_001
Revises: 
Create Date: 2025-12-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '8f3d9e2a1c45'  # Latest: add_alert_rules
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Marketplace tables
    op.create_table(
        'marketplace_plugins',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('author', sa.String(255), nullable=False),
        sa.Column('author_email', sa.String(255)),
        sa.Column('author_url', sa.String(500)),
        sa.Column('category', sa.String(50)),
        sa.Column('tags', sa.JSON().with_variant(postgresql.JSONB, 'postgresql')),
        sa.Column('dependencies', sa.JSON().with_variant(postgresql.JSONB, 'postgresql')),
        sa.Column('requirements', sa.JSON().with_variant(postgresql.JSONB, 'postgresql')),
        sa.Column('source_type', sa.String(50), server_default='github'),
        sa.Column('source_url', sa.String(1000)),
        sa.Column('source_path', sa.String(500)),
        sa.Column('install_count', sa.Integer(), server_default='0'),
        sa.Column('download_count', sa.Integer(), server_default='0'),
        sa.Column('rating_average', sa.Float(), server_default='0.0'),
        sa.Column('rating_count', sa.Integer(), server_default='0'),
        sa.Column('verified', sa.Boolean(), server_default='false'),
        sa.Column('featured', sa.Boolean(), server_default='false'),
        sa.Column('deprecated', sa.Boolean(), server_default='false'),
        sa.Column('readme', sa.Text()),
        sa.Column('changelog', sa.Text()),
        sa.Column('license', sa.String(100)),
        sa.Column('homepage_url', sa.String(500)),
        sa.Column('documentation_url', sa.String(500)),
        sa.Column('published_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('last_synced_at', sa.DateTime(timezone=True)),
    )
    
    op.create_table(
        'plugin_reviews',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('plugin_id', sa.String(100), sa.ForeignKey('marketplace_plugins.id'), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('user_name', sa.String(255)),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255)),
        sa.Column('review_text', sa.Text()),
        sa.Column('helpful_count', sa.Integer(), server_default='0'),
        sa.Column('verified_purchase', sa.Boolean(), server_default='false'),
        sa.Column('approved', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    op.create_table(
        'plugin_installations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('marketplace_plugin_id', sa.String(100), sa.ForeignKey('marketplace_plugins.id'), nullable=False),
        sa.Column('installed_plugin_id', sa.String(100), sa.ForeignKey('plugins.id')),
        sa.Column('installed_by', sa.String(255)),
        sa.Column('version_installed', sa.String(50)),
        sa.Column('installation_method', sa.String(50), server_default='marketplace'),
        sa.Column('active', sa.Boolean(), server_default='true'),
        sa.Column('auto_update', sa.Boolean(), server_default='false'),
        sa.Column('installed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('uninstalled_at', sa.DateTime(timezone=True)),
    )
    
    op.create_table(
        'plugin_downloads',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('plugin_id', sa.String(100), sa.ForeignKey('marketplace_plugins.id'), nullable=False),
        sa.Column('version', sa.String(50)),
        sa.Column('download_type', sa.String(50), server_default='install'),
        sa.Column('user_id', sa.String(255)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('downloaded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Dashboard tables
    op.create_table(
        'dashboards',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('user_id', sa.String(255)),
        sa.Column('layout', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False),
        sa.Column('widgets', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default='false'),
        sa.Column('is_shared', sa.Boolean(), server_default='false'),
        sa.Column('refresh_interval', sa.Integer(), server_default='30'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    op.create_table(
        'dashboard_widgets',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('dashboard_id', sa.Integer(), sa.ForeignKey('dashboards.id'), nullable=False),
        sa.Column('widget_type', sa.String(100), nullable=False),
        sa.Column('widget_id', sa.String(100), nullable=False),
        sa.Column('x', sa.Integer(), nullable=False),
        sa.Column('y', sa.Integer(), nullable=False),
        sa.Column('w', sa.Integer(), nullable=False),
        sa.Column('h', sa.Integer(), nullable=False),
        sa.Column('config', sa.JSON().with_variant(postgresql.JSONB, 'postgresql')),
        sa.Column('title', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Add conditions_json to alert_rules for advanced alerting
    op.add_column('alert_rules', sa.Column('conditions_json', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True))
    
    # Create indexes
    op.create_index('idx_marketplace_category', 'marketplace_plugins', ['category'])
    op.create_index('idx_marketplace_rating', 'marketplace_plugins', ['rating_average'])
    op.create_index('idx_reviews_plugin', 'plugin_reviews', ['plugin_id'])
    op.create_index('idx_installations_plugin', 'plugin_installations', ['marketplace_plugin_id'])
    op.create_index('idx_dashboards_user', 'dashboards', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_dashboards_user', 'dashboards')
    op.drop_index('idx_installations_plugin', 'plugin_installations')
    op.drop_index('idx_reviews_plugin', 'plugin_reviews')
    op.drop_index('idx_marketplace_rating', 'marketplace_plugins')
    op.drop_index('idx_marketplace_category', 'marketplace_plugins')
    
    op.drop_column('alert_rules', 'conditions_json')
    
    op.drop_table('dashboard_widgets')
    op.drop_table('dashboards')
    op.drop_table('plugin_downloads')
    op.drop_table('plugin_installations')
    op.drop_table('plugin_reviews')
    op.drop_table('marketplace_plugins')

