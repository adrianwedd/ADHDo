"""Fix SQLite compatibility for datetime defaults

Revision ID: 31c23c36a519
Revises: 002_github_automation_schema
Create Date: 2025-08-09 17:20:36.774868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31c23c36a519'
down_revision: Union[str, Sequence[str], None] = '002_github_automation_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix SQLite compatibility by dropping and recreating tables with proper defaults."""
    
    # Drop the current tables that have PostgreSQL-specific now() functions
    op.drop_table('system_health')
    
    # Recreate system_health table with SQLite-compatible CURRENT_TIMESTAMP
    op.create_table('system_health',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('component', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('error_rate', sa.Float(), nullable=True),
        sa.Column('uptime_seconds', sa.Integer(), nullable=True),
        sa.Column('memory_usage_mb', sa.Float(), nullable=True),
        sa.Column('cpu_usage_percent', sa.Float(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('measured_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("component IN ('redis', 'database', 'llm', 'telegram', 'system', 'application', 'overall')", name='ck_system_health_component_values'),
        sa.CheckConstraint("status IN ('healthy', 'degraded', 'unhealthy', 'unknown')", name='ck_system_health_status_values'),
        sa.CheckConstraint('error_rate >= 0.0 AND error_rate <= 1.0', name='ck_system_health_error_rate_range'),
        sa.CheckConstraint('cpu_usage_percent >= 0.0 AND cpu_usage_percent <= 100.0', name='ck_system_health_cpu_range'),
        sa.PrimaryKeyConstraint('id', name='pk_system_health')
    )
    op.create_index('ix_system_health_component_time', 'system_health', ['component', 'measured_at'])
    op.create_index('ix_system_health_status', 'system_health', ['status'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the fixed table
    op.drop_index('ix_system_health_status', table_name='system_health')
    op.drop_index('ix_system_health_component_time', table_name='system_health')
    op.drop_table('system_health')
    
    # Recreate the original table (this will fail in SQLite due to now() but that's the point)
    op.create_table('system_health',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('component', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('error_rate', sa.Float(), nullable=True),
        sa.Column('uptime_seconds', sa.Integer(), nullable=True),
        sa.Column('memory_usage_mb', sa.Float(), nullable=True),
        sa.Column('cpu_usage_percent', sa.Float(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('measured_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("component IN ('redis', 'database', 'llm', 'telegram', 'overall')", name='ck_system_health_component_values'),
        sa.CheckConstraint("status IN ('healthy', 'degraded', 'unhealthy')", name='ck_system_health_status_values'),
        sa.CheckConstraint('error_rate >= 0.0 AND error_rate <= 1.0', name='ck_system_health_error_rate_range'),
        sa.CheckConstraint('cpu_usage_percent >= 0.0 AND cpu_usage_percent <= 100.0', name='ck_system_health_cpu_range'),
        sa.PrimaryKeyConstraint('id', name='pk_system_health')
    )
    op.create_index('ix_system_health_component_time', 'system_health', ['component', 'measured_at'])
    op.create_index('ix_system_health_status', 'system_health', ['status'])
