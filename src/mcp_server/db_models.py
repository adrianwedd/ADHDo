"""Database models for MCP ADHD Server."""
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Boolean, DateTime, Float, Integer, String, Text, JSON, 
    ForeignKey, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from mcp_server.database import Base


class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    # Primary key
    user_id: Mapped[str] = mapped_column(
        String(255), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Authentication
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    email_verification_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Multi-factor authentication
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    backup_codes: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Account security
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    account_locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # ADHD-specific settings
    preferred_nudge_methods: Mapped[List[str]] = mapped_column(
        JSON, default=lambda: ["web", "telegram"]
    )
    nudge_timing_preferences: Mapped[dict] = mapped_column(
        JSON, default=lambda: {"morning": "09:00", "evening": "18:00"}
    )
    energy_patterns: Mapped[dict] = mapped_column(
        JSON, default=lambda: {"peak_hours": [9, 10, 11, 14, 15, 16]}
    )
    hyperfocus_indicators: Mapped[List[str]] = mapped_column(
        JSON, default=lambda: ["long_sessions", "delayed_responses"]
    )
    
    # Integration settings
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    google_calendar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    home_assistant_entity_prefix: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP')
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Relationships
    tasks: Mapped[List["Task"]] = relationship(
        "Task", back_populates="user", cascade="all, delete-orphan"
    )
    traces: Mapped[List["TraceMemory"]] = relationship(
        "TraceMemory", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )


class Task(Base):
    """Task/intention model."""
    __tablename__ = "tasks"
    
    # Primary key
    task_id: Mapped[str] = mapped_column(
        String(255), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    
    # Foreign key
    user_id: Mapped[str] = mapped_column(
        String(255), 
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Task details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(
        Integer, 
        CheckConstraint("priority >= 1 AND priority <= 5", name="ck_tasks_priority_range"), 
        default=3
    )
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), 
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'cancelled')", name="ck_tasks_status_values"),
        default="pending"
    )
    completion_percentage: Mapped[float] = mapped_column(
        Float, 
        CheckConstraint("completion_percentage >= 0.0 AND completion_percentage <= 1.0", name="ck_tasks_completion_range"),
        default=0.0
    )
    
    # ADHD-specific fields
    estimated_focus_time: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True  # in minutes
    )
    energy_required: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("energy_required IN ('low', 'medium', 'high')", name="ck_tasks_energy_values"),
        default="medium"
    )
    dopamine_reward_tier: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("dopamine_reward_tier >= 1 AND dopamine_reward_tier <= 5", name="ck_tasks_dopamine_range"),
        default=3
    )
    hyperfocus_compatible: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Context
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    context_triggers: Mapped[List[str]] = mapped_column(
        JSON, default=lambda: ["location", "time", "energy"]
    )
    
    # Scheduling
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    preferred_time_blocks: Mapped[List[str]] = mapped_column(
        JSON, default=lambda: ["morning", "afternoon"]
    )
    
    # Nudge tracking
    nudge_count: Mapped[int] = mapped_column(Integer, default=0)
    last_nudge_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    nudge_effectiveness: Mapped[dict] = mapped_column(
        JSON, default=lambda: {"total_nudges": 0, "successful_nudges": 0}
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP')
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tasks")
    
    # Indexes
    __table_args__ = (
        Index("ix_tasks_user_status", "user_id", "status"),
        Index("ix_tasks_due_date", "due_date"),
        Index("ix_tasks_priority", "priority"),
    )


class TraceMemory(Base):
    """Context trace and memory model."""
    __tablename__ = "trace_memories"
    
    # Primary key
    trace_id: Mapped[str] = mapped_column(
        String(255), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    
    # Foreign key
    user_id: Mapped[str] = mapped_column(
        String(255), 
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Trace details
    trace_type: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint("trace_type IN ('user_input', 'system_response', 'context_update', 'nudge', 'completion')", name="ck_trace_memories_type_values"),
        nullable=False
    )
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Context
    task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    frame_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Metrics
    processing_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cognitive_load: Mapped[Optional[float]] = mapped_column(
        Float, 
        CheckConstraint("cognitive_load >= 0.0 AND cognitive_load <= 1.0", name="ck_trace_memories_cognitive_load_range"),
        nullable=True
    )
    
    # Success tracking
    was_successful: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Metadata
    source: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint("source IN ('web', 'telegram', 'api', 'webhook', 'system')", name="ck_trace_memories_source_values"),
        default="system"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="traces")
    
    # Indexes
    __table_args__ = (
        Index("ix_trace_memories_user_created", "user_id", "created_at"),
        Index("ix_trace_memories_task", "task_id"),
        Index("ix_trace_memories_type", "trace_type"),
        Index("ix_trace_memories_session", "session_id"),
    )


class Session(Base):
    """User session model for authentication."""
    __tablename__ = "sessions"
    
    # Primary key
    session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    
    # Foreign key
    user_id: Mapped[str] = mapped_column(
        String(255), 
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Session details
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    # Security features
    session_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    csrf_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    login_method: Mapped[str] = mapped_column(String(50), default="password")
    two_factor_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    security_flags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Session lifecycle
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_accessed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP')
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    
    # Indexes
    __table_args__ = (
        Index("ix_sessions_user_active", "user_id", "is_active"),
        Index("ix_sessions_expires", "expires_at"),
    )


class APIKey(Base):
    """API key model for authentication."""
    __tablename__ = "api_keys"
    
    # Primary key
    key_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    
    # Foreign key
    user_id: Mapped[str] = mapped_column(
        String(255), 
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # API key details
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Permissions
    permissions: Mapped[List[str]] = mapped_column(
        JSON, default=lambda: ["chat", "tasks", "context"]
    )
    
    # Rate limiting
    requests_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    requests_per_day: Mapped[int] = mapped_column(Integer, default=1000)
    
    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")
    
    # Indexes
    __table_args__ = (
        Index("ix_api_keys_user_active", "user_id", "is_active"),
        Index("ix_api_keys_hash", "key_hash"),
    )


class SystemHealth(Base):
    """System health metrics model."""
    __tablename__ = "system_health"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Metrics
    component: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint("component IN ('redis', 'database', 'llm', 'telegram', 'overall')", name="ck_system_health_component_values"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status IN ('healthy', 'degraded', 'unhealthy')", name="ck_system_health_status_values"),
        nullable=False
    )
    
    # Performance metrics
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_rate: Mapped[Optional[float]] = mapped_column(
        Float,
        CheckConstraint("error_rate >= 0.0 AND error_rate <= 1.0", name="ck_system_health_error_rate_range"),
        nullable=True
    )
    uptime_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Resource usage
    memory_usage_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(
        Float,
        CheckConstraint("cpu_usage_percent >= 0.0 AND cpu_usage_percent <= 100.0", name="ck_system_health_cpu_range"),
        nullable=True
    )
    
    # Additional details
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_system_health_component_time", "component", "measured_at"),
        Index("ix_system_health_status", "status"),
    )


class JWTSecret(Base):
    """JWT secret rotation model."""
    __tablename__ = "jwt_secrets"
    
    # Primary key
    secret_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    
    # Secret details
    secret_key: Mapped[str] = mapped_column(String(512), nullable=False)  # Encrypted
    algorithm: Mapped[str] = mapped_column(String(20), default="HS256")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotation_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("ix_jwt_secrets_active", "is_active", "expires_at"),
        Index("ix_jwt_secrets_expires", "expires_at"),
        CheckConstraint("algorithm IN ('HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512')", 
                       name="ck_jwt_secrets_algorithm_values"),
    )


class SessionActivity(Base):
    """Session activity log for security monitoring."""
    __tablename__ = "session_activities"
    
    # Primary key
    activity_id: Mapped[str] = mapped_column(
        String(255), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    
    # Foreign keys
    session_id: Mapped[str] = mapped_column(
        String(255), 
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(255), 
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Activity details
    activity_type: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint("activity_type IN ('login', 'logout', 'api_call', 'password_change', 'profile_update', 'suspicious')", 
                       name="ck_session_activities_type_values"),
        nullable=False
    )
    
    # Request details
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    endpoint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    request_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Security metrics
    risk_score: Mapped[float] = mapped_column(
        Float, 
        CheckConstraint("risk_score >= 0.0 AND risk_score <= 10.0", 
                       name="ck_session_activities_risk_score_range"),
        default=0.0
    )
    security_alerts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_session_activities_session_time", "session_id", "created_at"),
        Index("ix_session_activities_user_time", "user_id", "created_at"),
        Index("ix_session_activities_risk", "risk_score"),
        Index("ix_session_activities_type_time", "activity_type", "created_at"),
    )


class SecurityEvent(Base):
    """Security events log for monitoring and alerting."""
    __tablename__ = "security_events"
    
    # Primary key
    event_id: Mapped[str] = mapped_column(
        String(255), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    
    # Optional foreign keys
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        ForeignKey("sessions.session_id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Event details
    event_type: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint("event_type IN ('failed_login', 'account_lockout', 'suspicious_activity', 'password_reset', 'session_hijack', 'rate_limit_exceeded', 'unauthorized_access')", 
                       name="ck_security_events_type_values"),
        nullable=False
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", 
                       name="ck_security_events_severity_values"),
        nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Resolution tracking
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_security_events_user_time", "user_id", "created_at"),
        Index("ix_security_events_severity_time", "severity", "created_at"),
        Index("ix_security_events_type_time", "event_type", "created_at"),
        Index("ix_security_events_unresolved", "resolved", "created_at"),
    )


class RateLimit(Base):
    """Rate limiting tracking for users, IPs, and API keys."""
    __tablename__ = "rate_limits"
    
    # Primary key
    limit_id: Mapped[str] = mapped_column(
        String(255), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    
    # Rate limit details
    identifier: Mapped[str] = mapped_column(String(255), nullable=False)  # user_id, ip, or api_key
    limit_type: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint("limit_type IN ('user', 'ip', 'api_key', 'session')", 
                       name="ck_rate_limits_type_values"),
        nullable=False
    )
    endpoint_pattern: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Counters
    requests_count: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    limit_exceeded: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    last_request_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP')
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_rate_limits_identifier_type", "identifier", "limit_type"),
        Index("ix_rate_limits_window_end", "window_end"),
        Index("ix_rate_limits_exceeded", "limit_exceeded", "window_end"),
    )


class UserRole(Base):
    """User roles for RBAC system."""
    __tablename__ = "user_roles"
    
    # Primary key
    role_id: Mapped[str] = mapped_column(
        String(255), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    
    # Foreign key
    user_id: Mapped[str] = mapped_column(
        String(255), 
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Role details
    role_name: Mapped[str] = mapped_column(
        String(100),
        CheckConstraint("role_name IN ('admin', 'user', 'beta_tester', 'moderator', 'readonly')", 
                       name="ck_user_roles_name_values"),
        nullable=False
    )
    permissions: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    
    # Grant tracking
    granted_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Indexes
    __table_args__ = (
        Index("ix_user_roles_user_active", "user_id", "is_active"),
        Index("ix_user_roles_name", "role_name"),
    )


class OAuthProvider(Base):
    """OAuth provider integrations."""
    __tablename__ = "oauth_providers"
    
    # Primary key
    provider_id: Mapped[str] = mapped_column(
        String(255), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    
    # Foreign key
    user_id: Mapped[str] = mapped_column(
        String(255), 
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Provider details
    provider_name: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint("provider_name IN ('google', 'github', 'microsoft', 'discord')", 
                       name="ck_oauth_providers_name_values"),
        nullable=False
    )
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Tokens (hashed for security)
    access_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Profile data
    profile_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP')
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP')
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_oauth_providers_user_provider", "user_id", "provider_name", unique=True),
        Index("ix_oauth_providers_external_id", "provider_name", "provider_user_id", unique=True),
    )