"""GitHub Automation System Database Schema

Revision ID: 002_github_automation_schema
Revises: 001_initial_schema
Create Date: 2025-08-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_github_automation_schema'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create GitHub automation tables."""
    
    # GitHub Issues table
    op.create_table(
        'github_issues',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('github_issue_number', sa.Integer(), nullable=False),
        sa.Column('github_issue_id', sa.Integer(), nullable=False, unique=True),
        sa.Column('repository_name', sa.String(255), nullable=False),
        sa.Column('repository_owner', sa.String(255), nullable=False),
        sa.Column('title', sa.String(1000), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('open', 'closed', 'draft', name='issuestatus'), nullable=False, default='open'),
        sa.Column('author', sa.String(255), nullable=False),
        sa.Column('assignees', postgresql.JSON(), default=list),
        sa.Column('labels', postgresql.JSON(), default=list),
        sa.Column('milestone', sa.String(255), nullable=True),
        sa.Column('automation_eligible', sa.Boolean(), default=True),
        sa.Column('automation_confidence', sa.Enum('low', 'medium', 'high', 'very_high', name='confidencelevel'), nullable=True),
        sa.Column('feature_completion_score', sa.Float(), default=0.0),
        sa.Column('github_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('github_updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('github_closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_detected', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_analyzed', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('analysis_count', sa.Integer(), default=0),
        sa.Column('last_analysis_duration_ms', sa.Float(), nullable=True),
        
        # Constraints
        sa.CheckConstraint('feature_completion_score >= 0.0 AND feature_completion_score <= 1.0', name='ck_github_issues_completion_score'),
        sa.UniqueConstraint('github_issue_id', name='uq_github_issues_github_id'),
    )
    
    # Indexes for github_issues
    op.create_index('ix_github_issues_repo', 'github_issues', ['repository_owner', 'repository_name'])
    op.create_index('ix_github_issues_status', 'github_issues', ['status'])
    op.create_index('ix_github_issues_number', 'github_issues', ['github_issue_number'])
    op.create_index('ix_github_issues_automation', 'github_issues', ['automation_eligible', 'automation_confidence'])
    op.create_index('ix_github_issues_updated', 'github_issues', ['github_updated_at'])
    
    # GitHub Automation Actions table
    op.create_table(
        'github_automation_actions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('issue_id', sa.String(36), sa.ForeignKey('github_issues.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.Enum(
            'close_issue', 'update_issue', 'create_issue', 'label_issue', 
            'assign_issue', 'milestone_issue', 'comment_issue', 
            name='automationaction'
        ), nullable=False),
        sa.Column('status', sa.Enum(
            'pending', 'in_progress', 'completed', 'failed', 'rolled_back', 'cancelled',
            name='actionstatus'
        ), nullable=False, default='pending'),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=False),
        sa.Column('evidence', postgresql.JSON(), default=dict),
        sa.Column('execution_attempts', sa.Integer(), default=0),
        sa.Column('max_attempts', sa.Integer(), default=3),
        sa.Column('github_api_calls', sa.Integer(), default=0),
        sa.Column('github_rate_limit_remaining', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('github_response', postgresql.JSON(), nullable=True),
        sa.Column('rollback_data', postgresql.JSON(), nullable=True),
        sa.Column('can_rollback', sa.Boolean(), default=True),
        sa.Column('rolled_back', sa.Boolean(), default=False),
        sa.Column('rollback_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        
        # Constraints
        sa.CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 1.0', name='ck_automation_actions_confidence'),
    )
    
    # Indexes for github_automation_actions
    op.create_index('ix_automation_actions_issue', 'github_automation_actions', ['issue_id'])
    op.create_index('ix_automation_actions_status', 'github_automation_actions', ['status'])
    op.create_index('ix_automation_actions_type', 'github_automation_actions', ['action_type'])
    op.create_index('ix_automation_actions_created', 'github_automation_actions', ['created_at'])
    op.create_index('ix_automation_actions_confidence', 'github_automation_actions', ['confidence_score'])
    
    # Feature Detection table
    op.create_table(
        'feature_detections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('issue_id', sa.String(36), sa.ForeignKey('github_issues.id', ondelete='CASCADE'), nullable=False),
        sa.Column('feature_name', sa.String(255), nullable=False),
        sa.Column('feature_category', sa.String(100), nullable=False),
        sa.Column('completion_status', sa.String(50)),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('detection_method', sa.String(100), nullable=False),
        sa.Column('code_evidence', postgresql.JSON(), default=list),
        sa.Column('commit_evidence', postgresql.JSON(), default=list),
        sa.Column('test_evidence', postgresql.JSON(), default=list),
        sa.Column('documentation_evidence', postgresql.JSON(), default=list),
        sa.Column('analysis_version', sa.String(20), default='1.0.0'),
        sa.Column('false_positive_score', sa.Float(), default=0.0),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        
        # Constraints
        sa.CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 1.0', name='ck_feature_detections_confidence'),
        sa.CheckConstraint('false_positive_score >= 0.0 AND false_positive_score <= 1.0', name='ck_feature_detections_false_positive'),
        sa.CheckConstraint("completion_status IN ('not_started', 'in_progress', 'completed', 'verified')", name='ck_feature_detections_status'),
    )
    
    # Indexes for feature_detections
    op.create_index('ix_feature_detections_issue', 'feature_detections', ['issue_id'])
    op.create_index('ix_feature_detections_feature', 'feature_detections', ['feature_name'])
    op.create_index('ix_feature_detections_status', 'feature_detections', ['completion_status'])
    op.create_index('ix_feature_detections_confidence', 'feature_detections', ['confidence_score'])
    op.create_index('ix_feature_detections_detected', 'feature_detections', ['detected_at'])
    
    # Automation Metrics table
    op.create_table(
        'automation_metrics',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_category', sa.String(50), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('previous_value', sa.Float(), nullable=True),
        sa.Column('change_percentage', sa.Float(), nullable=True),
        sa.Column('repository_name', sa.String(255), nullable=True),
        sa.Column('time_period', sa.String(20), default='daily'),
        sa.Column('details', postgresql.JSON(), default=dict),
        sa.Column('measured_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Indexes for automation_metrics
    op.create_index('ix_automation_metrics_name', 'automation_metrics', ['metric_name'])
    op.create_index('ix_automation_metrics_category', 'automation_metrics', ['metric_category'])
    op.create_index('ix_automation_metrics_measured', 'automation_metrics', ['measured_at'])
    op.create_index('ix_automation_metrics_repo', 'automation_metrics', ['repository_name'])
    
    # Webhook Events table
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('github_delivery_id', sa.String(255), nullable=False, unique=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=True),
        sa.Column('repository_owner', sa.String(255), nullable=False),
        sa.Column('repository_name', sa.String(255), nullable=False),
        sa.Column('payload', postgresql.JSON(), nullable=False),
        sa.Column('headers', postgresql.JSON(), default=dict),
        sa.Column('processed', sa.Boolean(), default=False),
        sa.Column('processing_duration_ms', sa.Float(), nullable=True),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('triggered_actions', sa.Integer(), default=0),
        sa.Column('automation_results', postgresql.JSON(), default=dict),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Indexes for webhook_events
    op.create_index('ix_webhook_events_delivery', 'webhook_events', ['github_delivery_id'])
    op.create_index('ix_webhook_events_type', 'webhook_events', ['event_type'])
    op.create_index('ix_webhook_events_repo', 'webhook_events', ['repository_owner', 'repository_name'])
    op.create_index('ix_webhook_events_received', 'webhook_events', ['received_at'])
    op.create_index('ix_webhook_events_processed', 'webhook_events', ['processed'])
    
    # Rate Limit Tracking table
    op.create_table(
        'rate_limit_tracking',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('api_endpoint', sa.String(255), nullable=False),
        sa.Column('rate_limit_type', sa.String(20), default='core'),
        sa.Column('limit', sa.Integer(), nullable=False),
        sa.Column('remaining', sa.Integer(), nullable=False),
        sa.Column('reset_timestamp', sa.Integer(), nullable=False),
        sa.Column('used', sa.Integer(), nullable=False),
        sa.Column('request_url', sa.String(1000), nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=False),
        sa.Column('request_duration_ms', sa.Float(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Constraints
        sa.CheckConstraint("rate_limit_type IN ('core', 'search', 'graphql', 'integration_manifest')", name='ck_rate_limit_type'),
    )
    
    # Indexes for rate_limit_tracking
    op.create_index('ix_rate_limit_endpoint', 'rate_limit_tracking', ['api_endpoint'])
    op.create_index('ix_rate_limit_type', 'rate_limit_tracking', ['rate_limit_type'])
    op.create_index('ix_rate_limit_recorded', 'rate_limit_tracking', ['recorded_at'])
    op.create_index('ix_rate_limit_reset', 'rate_limit_tracking', ['reset_timestamp'])


def downgrade() -> None:
    """Drop GitHub automation tables."""
    
    # Drop tables in reverse dependency order
    op.drop_table('rate_limit_tracking')
    op.drop_table('webhook_events')
    op.drop_table('automation_metrics')
    op.drop_table('feature_detections')
    op.drop_table('github_automation_actions')
    op.drop_table('github_issues')
    
    # Drop custom enums
    sa.Enum(name='issuestatus').drop(op.get_bind())
    sa.Enum(name='confidencelevel').drop(op.get_bind())
    sa.Enum(name='automationaction').drop(op.get_bind())
    sa.Enum(name='actionstatus').drop(op.get_bind())