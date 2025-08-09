"""Enhanced Authentication Security

Revision ID: 003_authentication_security
Revises: 002_github_automation_schema
Create Date: 2025-08-09 12:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_authentication_security'
down_revision: Union[str, None] = '002_github_automation_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema for enhanced authentication security."""
    
    # 1. Enhance existing users table
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), default=False, nullable=False))
    op.add_column('users', sa.Column('email_verification_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_verification_expires', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('password_reset_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), default=False, nullable=False))
    op.add_column('users', sa.Column('mfa_secret', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('backup_codes', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), default=0, nullable=False))
    op.add_column('users', sa.Column('account_locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add indexes for new user columns
    op.create_index('ix_users_email_verification_token', 'users', ['email_verification_token'], unique=True)
    op.create_index('ix_users_password_reset_token', 'users', ['password_reset_token'], unique=True)
    op.create_index('ix_users_account_locked', 'users', ['account_locked_until'], unique=False)
    
    # 2. Create JWT secrets rotation table
    op.create_table('jwt_secrets',
        sa.Column('secret_id', sa.String(255), nullable=False),
        sa.Column('secret_key', sa.String(512), nullable=False),  # Encrypted secret
        sa.Column('algorithm', sa.String(20), nullable=False, default='HS256'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('rotation_reason', sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint('secret_id', name=op.f('pk_jwt_secrets')),
        sa.CheckConstraint("algorithm IN ('HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512')", 
                          name='ck_jwt_secrets_algorithm_values')
    )
    op.create_index('ix_jwt_secrets_active', 'jwt_secrets', ['is_active', 'expires_at'], unique=False)
    op.create_index('ix_jwt_secrets_expires', 'jwt_secrets', ['expires_at'], unique=False)
    
    # 3. Enhance sessions table with security features
    op.add_column('sessions', sa.Column('session_token_hash', sa.String(255), nullable=True))
    op.add_column('sessions', sa.Column('csrf_token', sa.String(255), nullable=True))
    op.add_column('sessions', sa.Column('device_fingerprint', sa.String(255), nullable=True))
    op.add_column('sessions', sa.Column('login_method', sa.String(50), nullable=False, default='password'))
    op.add_column('sessions', sa.Column('two_factor_verified', sa.Boolean(), default=False, nullable=False))
    op.add_column('sessions', sa.Column('security_flags', sa.JSON(), nullable=True))
    op.add_column('sessions', sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('sessions', sa.Column('revocation_reason', sa.String(100), nullable=True))
    
    # Add session security indexes
    op.create_index('ix_sessions_token_hash', 'sessions', ['session_token_hash'], unique=True)
    op.create_index('ix_sessions_device_fingerprint', 'sessions', ['user_id', 'device_fingerprint'], unique=False)
    op.create_index('ix_sessions_revoked', 'sessions', ['revoked_at'], unique=False)
    
    # 4. Create session activity log
    op.create_table('session_activities',
        sa.Column('activity_id', sa.String(255), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('activity_type', sa.String(50), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('endpoint', sa.String(255), nullable=True),
        sa.Column('request_method', sa.String(10), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('risk_score', sa.Float(), default=0.0, nullable=False),
        sa.Column('security_alerts', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], 
                               name=op.f('fk_session_activities_session_id_sessions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], 
                               name=op.f('fk_session_activities_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('activity_id', name=op.f('pk_session_activities')),
        sa.CheckConstraint("activity_type IN ('login', 'logout', 'api_call', 'password_change', 'profile_update', 'suspicious')", 
                          name='ck_session_activities_type_values'),
        sa.CheckConstraint('risk_score >= 0.0 AND risk_score <= 10.0', 
                          name='ck_session_activities_risk_score_range')
    )
    op.create_index('ix_session_activities_session_time', 'session_activities', ['session_id', 'created_at'], unique=False)
    op.create_index('ix_session_activities_user_time', 'session_activities', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_session_activities_risk', 'session_activities', ['risk_score'], unique=False)
    op.create_index('ix_session_activities_type_time', 'session_activities', ['activity_type', 'created_at'], unique=False)
    
    # 5. Create security events log
    op.create_table('security_events',
        sa.Column('event_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('event_metadata', sa.JSON(), nullable=True),
        sa.Column('resolved', sa.Boolean(), default=False, nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], 
                               name=op.f('fk_security_events_user_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], 
                               name=op.f('fk_security_events_session_id_sessions'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('event_id', name=op.f('pk_security_events')),
        sa.CheckConstraint("event_type IN ('failed_login', 'account_lockout', 'suspicious_activity', 'password_reset', 'session_hijack', 'rate_limit_exceeded', 'unauthorized_access')", 
                          name='ck_security_events_type_values'),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", 
                          name='ck_security_events_severity_values')
    )
    op.create_index('ix_security_events_user_time', 'security_events', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_security_events_severity_time', 'security_events', ['severity', 'created_at'], unique=False)
    op.create_index('ix_security_events_type_time', 'security_events', ['event_type', 'created_at'], unique=False)
    op.create_index('ix_security_events_unresolved', 'security_events', ['resolved', 'created_at'], unique=False)
    
    # 6. Create rate limiting table
    op.create_table('rate_limits',
        sa.Column('limit_id', sa.String(255), nullable=False),
        sa.Column('identifier', sa.String(255), nullable=False),  # user_id, ip, or api_key
        sa.Column('limit_type', sa.String(50), nullable=False),   # 'user', 'ip', 'api_key'
        sa.Column('endpoint_pattern', sa.String(255), nullable=True),
        sa.Column('requests_count', sa.Integer(), default=0, nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('limit_exceeded', sa.Boolean(), default=False, nullable=False),
        sa.Column('last_request_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('limit_id', name=op.f('pk_rate_limits')),
        sa.CheckConstraint("limit_type IN ('user', 'ip', 'api_key', 'session')", 
                          name='ck_rate_limits_type_values')
    )
    op.create_index('ix_rate_limits_identifier_type', 'rate_limits', ['identifier', 'limit_type'], unique=False)
    op.create_index('ix_rate_limits_window_end', 'rate_limits', ['window_end'], unique=False)
    op.create_index('ix_rate_limits_exceeded', 'rate_limits', ['limit_exceeded', 'window_end'], unique=False)
    
    # 7. Create user roles table (for future RBAC)
    op.create_table('user_roles',
        sa.Column('role_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('role_name', sa.String(100), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False),
        sa.Column('granted_by', sa.String(255), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], 
                               name=op.f('fk_user_roles_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', name=op.f('pk_user_roles')),
        sa.CheckConstraint("role_name IN ('admin', 'user', 'beta_tester', 'moderator', 'readonly')", 
                          name='ck_user_roles_name_values')
    )
    op.create_index('ix_user_roles_user_active', 'user_roles', ['user_id', 'is_active'], unique=False)
    op.create_index('ix_user_roles_name', 'user_roles', ['role_name'], unique=False)
    
    # 8. Create OAuth providers table (for future OAuth integration)
    op.create_table('oauth_providers',
        sa.Column('provider_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('provider_name', sa.String(50), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('access_token_hash', sa.String(255), nullable=True),
        sa.Column('refresh_token_hash', sa.String(255), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('profile_data', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], 
                               name=op.f('fk_oauth_providers_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('provider_id', name=op.f('pk_oauth_providers')),
        sa.CheckConstraint("provider_name IN ('google', 'github', 'microsoft', 'discord')", 
                          name='ck_oauth_providers_name_values')
    )
    op.create_index('ix_oauth_providers_user_provider', 'oauth_providers', ['user_id', 'provider_name'], unique=True)
    op.create_index('ix_oauth_providers_external_id', 'oauth_providers', ['provider_name', 'provider_user_id'], unique=True)


def downgrade() -> None:
    """Downgrade database schema - remove enhanced authentication tables."""
    
    # Drop new tables
    op.drop_table('oauth_providers')
    op.drop_table('user_roles')
    op.drop_table('rate_limits')
    op.drop_table('security_events')
    op.drop_table('session_activities')
    op.drop_table('jwt_secrets')
    
    # Remove columns from sessions table
    op.drop_column('sessions', 'revocation_reason')
    op.drop_column('sessions', 'revoked_at')
    op.drop_column('sessions', 'security_flags')
    op.drop_column('sessions', 'two_factor_verified')
    op.drop_column('sessions', 'login_method')
    op.drop_column('sessions', 'device_fingerprint')
    op.drop_column('sessions', 'csrf_token')
    op.drop_column('sessions', 'session_token_hash')
    
    # Remove columns from users table
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'account_locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'backup_codes')
    op.drop_column('users', 'mfa_secret')
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'email_verification_expires')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'email_verified')