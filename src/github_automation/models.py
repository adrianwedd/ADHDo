"""
Database models for GitHub Issue Automation System.

Enterprise-grade data models with comprehensive tracking, audit trails,
and performance optimization for large-scale operations.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, DateTime, Enum as SQLEnum, Float, Integer, String, Text, JSON, 
    ForeignKey, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from mcp_server.database import Base


class IssueStatus(str, Enum):
    """Issue status enumeration."""
    OPEN = "open"
    CLOSED = "closed"
    DRAFT = "draft"


class AutomationAction(str, Enum):
    """Automation action types."""
    CLOSE_ISSUE = "close_issue"
    UPDATE_ISSUE = "update_issue" 
    CREATE_ISSUE = "create_issue"
    LABEL_ISSUE = "label_issue"
    ASSIGN_ISSUE = "assign_issue"
    MILESTONE_ISSUE = "milestone_issue"
    COMMENT_ISSUE = "comment_issue"


class ActionStatus(str, Enum):
    """Action execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class ConfidenceLevel(str, Enum):
    """Confidence level for automated actions."""
    LOW = "low"          # 0-30%
    MEDIUM = "medium"    # 30-70% 
    HIGH = "high"        # 70-90%
    VERY_HIGH = "very_high"  # 90%+


class GitHubIssue(Base):
    """GitHub issue tracking model with comprehensive metadata."""
    __tablename__ = "github_issues"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True,
        default=lambda: str(uuid4())
    )
    
    # GitHub identifiers
    github_issue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    github_issue_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    repository_name: Mapped[str] = mapped_column(String(255), nullable=False)
    repository_owner: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Issue metadata
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[IssueStatus] = mapped_column(
        SQLEnum(IssueStatus), 
        nullable=False, 
        default=IssueStatus.OPEN
    )
    
    # GitHub user info
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    assignees: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Labels and categorization
    labels: Mapped[List[str]] = mapped_column(JSON, default=list)
    milestone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Automation tracking
    automation_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    automation_confidence: Mapped[Optional[ConfidenceLevel]] = mapped_column(
        SQLEnum(ConfidenceLevel), nullable=True
    )
    feature_completion_score: Mapped[float] = mapped_column(
        Float, 
        CheckConstraint("feature_completion_score >= 0.0 AND feature_completion_score <= 1.0", name="ck_github_issues_feature_completion_score"),
        default=0.0
    )
    
    # GitHub timestamps
    github_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    github_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    github_closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Our tracking timestamps
    first_detected: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    last_analyzed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Performance tracking
    analysis_count: Mapped[int] = mapped_column(Integer, default=0)
    last_analysis_duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    automation_actions: Mapped[List["GitHubAutomationAction"]] = relationship(
        "GitHubAutomationAction", back_populates="issue", cascade="all, delete-orphan"
    )
    feature_detections: Mapped[List["FeatureDetection"]] = relationship(
        "FeatureDetection", back_populates="issue", cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_github_issues_repo", "repository_owner", "repository_name"),
        Index("ix_github_issues_status", "status"),
        Index("ix_github_issues_number", "github_issue_number"),
        Index("ix_github_issues_automation", "automation_eligible", "automation_confidence"),
        Index("ix_github_issues_updated", "github_updated_at"),
        UniqueConstraint("github_issue_id", name="uq_github_issues_github_id"),
    )


class GitHubAutomationAction(Base):
    """Tracks individual automation actions with full audit trails."""
    __tablename__ = "github_automation_actions"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    
    # Issue reference
    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("github_issues.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Action details
    action_type: Mapped[AutomationAction] = mapped_column(
        SQLEnum(AutomationAction),
        nullable=False
    )
    status: Mapped[ActionStatus] = mapped_column(
        SQLEnum(ActionStatus),
        nullable=False,
        default=ActionStatus.PENDING
    )
    
    # Execution metadata
    confidence_score: Mapped[float] = mapped_column(
        Float,
        CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="ck_automation_actions_confidence_score"),
        nullable=False
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Dict] = mapped_column(JSON, default=dict)
    
    # Execution tracking
    execution_attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    
    # GitHub API interaction
    github_api_calls: Mapped[int] = mapped_column(Integer, default=0)
    github_rate_limit_remaining: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Results
    success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    github_response: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    
    # Rollback capability
    rollback_data: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    can_rollback: Mapped[bool] = mapped_column(Boolean, default=True)
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False)
    rollback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    issue: Mapped["GitHubIssue"] = relationship("GitHubIssue", back_populates="automation_actions")
    
    # Indexes
    __table_args__ = (
        Index("ix_automation_actions_issue", "issue_id"),
        Index("ix_automation_actions_status", "status"),
        Index("ix_automation_actions_type", "action_type"),
        Index("ix_automation_actions_created", "created_at"),
        Index("ix_automation_actions_confidence", "confidence_score"),
    )


class FeatureDetection(Base):
    """Tracks feature completion detection with evidence and confidence."""
    __tablename__ = "feature_detections"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    
    # Issue reference
    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("github_issues.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Feature identification
    feature_name: Mapped[str] = mapped_column(String(255), nullable=False)
    feature_category: Mapped[str] = mapped_column(String(100), nullable=False)
    completion_status: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint("completion_status IN ('not_started', 'in_progress', 'completed', 'verified')", name="ck_feature_completions_completion_status")
    )
    
    # Detection metadata
    confidence_score: Mapped[float] = mapped_column(
        Float,
        CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="ck_feature_completions_confidence_score"),
        nullable=False
    )
    detection_method: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Evidence
    code_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    commit_evidence: Mapped[List[Dict]] = mapped_column(JSON, default=list)
    test_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    documentation_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Analysis metadata
    analysis_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    false_positive_score: Mapped[float] = mapped_column(
        Float,
        CheckConstraint("false_positive_score >= 0.0 AND false_positive_score <= 1.0", name="ck_feature_completions_false_positive_score"),
        default=0.0
    )
    
    # Timing
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    issue: Mapped["GitHubIssue"] = relationship("GitHubIssue", back_populates="feature_detections")
    
    # Indexes
    __table_args__ = (
        Index("ix_feature_detections_issue", "issue_id"),
        Index("ix_feature_detections_feature", "feature_name"),
        Index("ix_feature_detections_status", "completion_status"),
        Index("ix_feature_detections_confidence", "confidence_score"),
        Index("ix_feature_detections_detected", "detected_at"),
    )


class AutomationMetrics(Base):
    """System-wide automation metrics and performance tracking."""
    __tablename__ = "automation_metrics"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    
    # Metric identification
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_category: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Values
    value: Mapped[float] = mapped_column(Float, nullable=False)
    previous_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Context
    repository_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    time_period: Mapped[str] = mapped_column(String(20), default="daily")
    
    # Metadata
    details: Mapped[Dict] = mapped_column(JSON, default=dict)
    
    # Timing
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_automation_metrics_name", "metric_name"),
        Index("ix_automation_metrics_category", "metric_category"),
        Index("ix_automation_metrics_measured", "measured_at"),
        Index("ix_automation_metrics_repo", "repository_name"),
    )


class WebhookEvent(Base):
    """Tracks GitHub webhook events for audit and replay capabilities."""
    __tablename__ = "webhook_events"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    
    # GitHub webhook metadata
    github_delivery_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Repository context
    repository_owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repository_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Payload
    payload: Mapped[Dict] = mapped_column(JSON, nullable=False)
    headers: Mapped[Dict] = mapped_column(JSON, default=dict)
    
    # Processing status
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Automation triggers
    triggered_actions: Mapped[int] = mapped_column(Integer, default=0)
    automation_results: Mapped[Dict] = mapped_column(JSON, default=dict)
    
    # Timing
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("ix_webhook_events_delivery", "github_delivery_id"),
        Index("ix_webhook_events_type", "event_type"),
        Index("ix_webhook_events_repo", "repository_owner", "repository_name"),
        Index("ix_webhook_events_received", "received_at"),
        Index("ix_webhook_events_processed", "processed"),
    )


class RateLimitTracking(Base):
    """GitHub API rate limit tracking for intelligent request management."""
    __tablename__ = "rate_limit_tracking"
    
    # Primary key  
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    
    # API endpoint
    api_endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    rate_limit_type: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("rate_limit_type IN ('core', 'search', 'graphql', 'integration_manifest')", name="ck_api_rate_limits_rate_limit_type"),
        default="core"
    )
    
    # Rate limit status
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    reset_timestamp: Mapped[int] = mapped_column(Integer, nullable=False)
    used: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Request details
    request_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    request_duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Timing
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_rate_limit_endpoint", "api_endpoint"),
        Index("ix_rate_limit_type", "rate_limit_type"),
        Index("ix_rate_limit_recorded", "recorded_at"),
        Index("ix_rate_limit_reset", "reset_timestamp"),
    )