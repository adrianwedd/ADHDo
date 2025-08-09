"""Configuration management for MCP ADHD Server."""
from typing import Optional, List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Server Configuration
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port") 
    debug: bool = Field(default=True, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model")
    openai_max_tokens: int = Field(default=1500, description="Max tokens per request")
    
    # Telegram Configuration
    telegram_bot_token: Optional[str] = Field(default=None, description="Telegram bot token")
    telegram_chat_id: Optional[str] = Field(default=None, description="Telegram chat ID")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_max_connections: int = Field(default=20, description="Maximum Redis connections")
    redis_retry_on_timeout: bool = Field(default=True, description="Retry on Redis timeout")
    redis_health_check_interval: int = Field(default=30, description="Redis health check interval")
    
    # Background Processing Configuration
    background_processing_enabled: bool = Field(
        default=True, 
        description="Enable background task processing"
    )
    background_worker_count: int = Field(
        default=5, 
        description="Number of background workers per priority level"
    )
    background_task_timeout: int = Field(
        default=300, 
        description="Default task timeout in seconds"
    )
    background_max_retries: int = Field(
        default=3, 
        description="Maximum task retry attempts"
    )
    background_retry_delay: int = Field(
        default=60, 
        description="Delay between retries in seconds"
    )
    
    # Multi-Layer Caching Configuration
    cache_enabled: bool = Field(default=True, description="Enable multi-layer caching")
    cache_memory_size_mb: int = Field(default=100, description="In-memory cache size in MB")
    cache_redis_hot_db: int = Field(default=1, description="Redis database for hot cache")
    cache_redis_warm_db: int = Field(default=2, description="Redis database for warm cache")
    cache_redis_external_db: int = Field(default=3, description="Redis database for external cache")
    cache_compression_enabled: bool = Field(default=True, description="Enable cache compression")
    cache_compression_threshold: int = Field(default=1024, description="Compression threshold in bytes")
    
    # Cache TTL Configuration (ADHD-optimized)
    cache_crisis_ttl: int = Field(default=3600, description="Crisis data cache TTL (seconds)")
    cache_user_interaction_ttl: int = Field(default=300, description="User interaction cache TTL (seconds)")
    cache_background_ttl: int = Field(default=3600, description="Background data cache TTL (seconds)")
    cache_analytics_ttl: int = Field(default=7200, description="Analytics cache TTL (seconds)")
    cache_maintenance_ttl: int = Field(default=86400, description="Maintenance cache TTL (seconds)")
    
    # Cache Warming Configuration
    cache_warming_enabled: bool = Field(default=True, description="Enable predictive cache warming")
    cache_warming_peak_hours: List[int] = Field(
        default=[9, 10, 11, 14, 15, 16], 
        description="Peak ADHD attention hours for cache warming"
    )
    cache_warming_batch_size: int = Field(default=50, description="Cache warming batch size")
    cache_warming_max_patterns: int = Field(default=1000, description="Maximum patterns to track")
    
    # Performance Targets (ADHD-optimized)
    performance_crisis_response_ms: int = Field(
        default=100, 
        description="Crisis response time target (milliseconds)"
    )
    performance_user_response_ms: int = Field(
        default=1000, 
        description="User interaction response time target (milliseconds)"
    )
    performance_background_resource_limit: float = Field(
        default=0.7, 
        description="Background processing resource limit (0.0-1.0)"
    )
    performance_memory_cache_ms: float = Field(
        default=1.0, 
        description="Memory cache access time target (milliseconds)"
    )
    performance_redis_hot_ms: float = Field(
        default=10.0, 
        description="Redis hot cache access time target (milliseconds)"
    )
    performance_redis_warm_ms: float = Field(
        default=100.0, 
        description="Redis warm cache access time target (milliseconds)"
    )
    
    # Database Configuration - PostgreSQL Enforced in Production
    database_url: str = Field(
        default="postgresql+asyncpg://mcp:password@localhost:5432/mcp_adhd",
        description="Database URL - PostgreSQL required in production"
    )
    database_pool_size: int = Field(
        default=20,
        description="Database connection pool size (production optimized)"
    )
    database_pool_max_overflow: int = Field(
        default=10, 
        description="Maximum overflow connections beyond pool size"
    )
    database_pool_timeout: int = Field(
        default=5,
        description="Connection pool timeout in seconds (ADHD optimized)"
    )
    database_pool_recycle: int = Field(
        default=3600,
        description="Connection recycle time in seconds (1 hour)"
    )
    database_query_timeout: int = Field(
        default=30,
        description="Individual query timeout in seconds"
    )
    database_health_check_interval: int = Field(
        default=30,
        description="Database health check interval in seconds"
    )
    # Environment Detection
    environment: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
    enforce_postgresql: bool = Field(
        default=True,
        description="Enforce PostgreSQL in production environments"
    )
    
    # Google Calendar Configuration (Optional)
    google_calendar_credentials_file: Optional[str] = Field(
        default=None, 
        description="Google Calendar credentials file path"
    )
    google_calendar_id: str = Field(default="primary", description="Google Calendar ID")
    google_calendar_redirect_uri: str = Field(
        default="http://localhost:8000/api/calendar/callback",
        description="OAuth redirect URI for calendar authentication"
    )
    google_calendar_enabled: bool = Field(
        default=False,
        description="Enable Google Calendar integration"
    )
    
    # Home Assistant Configuration (Optional)
    home_assistant_url: Optional[str] = Field(
        default=None,
        description="Home Assistant URL"
    )
    home_assistant_token: Optional[str] = Field(
        default=None,
        description="Home Assistant long-lived access token"
    )
    
    # Nudge Engine Configuration
    nudge_tier_0_delay: int = Field(default=300, description="Tier 0 nudge delay (seconds)")
    nudge_tier_1_delay: int = Field(default=900, description="Tier 1 nudge delay (seconds)")
    nudge_tier_2_delay: int = Field(default=1800, description="Tier 2 nudge delay (seconds)")
    nudge_max_attempts: int = Field(default=5, description="Maximum nudge attempts")
    
    # Context Configuration
    context_window_size: int = Field(default=4000, description="Context window size (tokens)")
    trace_memory_retention_days: int = Field(
        default=90, 
        description="Trace memory retention period (days)"
    )
    frame_cache_ttl: int = Field(default=3600, description="Frame cache TTL (seconds)")
    
    # System Health Configuration
    disk_warning_threshold: float = Field(
        default=85.0, 
        description="Disk usage warning threshold (%)"
    )
    disk_critical_threshold: float = Field(
        default=95.0, 
        description="Disk usage critical threshold (%)"
    )
    redis_performance_threshold: float = Field(
        default=50.0, 
        description="Redis response time threshold (ms)"
    )
    
    # Database Performance Monitoring
    database_performance_threshold: float = Field(
        default=100.0,
        description="Database response time threshold (ms)"
    )
    database_slow_query_threshold: float = Field(
        default=200.0,
        description="Slow query alert threshold (ms)"
    )
    database_connection_timeout_threshold: float = Field(
        default=1000.0,
        description="Connection timeout alert threshold (ms)"
    )
    database_backup_enabled: bool = Field(
        default=True,
        description="Enable automated database backups"
    )
    database_backup_interval_hours: int = Field(
        default=6,
        description="Database backup interval in hours"
    )
    database_backup_retention_days: int = Field(
        default=30,
        description="Database backup retention period in days"
    )
    integration_efficiency_threshold: float = Field(
        default=70.0,
        description="Minimum integration efficiency threshold (%)"
    )
    parallel_operations_enabled: bool = Field(
        default=True,
        description="Enable parallel data operations for better integration"
    )
    
    # Agent Configuration
    default_agent_temperature: float = Field(
        default=0.7, 
        description="Default agent temperature"
    )
    agent_max_retries: int = Field(default=3, description="Maximum agent retries")
    agent_timeout: int = Field(default=30, description="Agent timeout (seconds)")
    
    # Authentication Configuration
    admin_username: Optional[str] = Field(default=None, description="Admin username")
    admin_password: Optional[str] = Field(default=None, description="Admin password")
    session_duration_hours: int = Field(default=24, description="Session duration (hours)")
    jwt_secret: str = Field(
        default="your-secret-key-change-in-production", 
        description="JWT secret key (DEPRECATED - use JWT rotation)"
    )
    
    # Enhanced Security Configuration
    master_encryption_key: str = Field(
        default="change-me-in-production-use-strong-key",
        description="Master encryption key for JWT secrets (use environment variable)"
    )
    jwt_rotation_days: int = Field(default=30, description="JWT secret rotation period (days)")
    max_failed_login_attempts: int = Field(default=15, description="Max failed login attempts before lockout")
    account_lockout_duration_minutes: int = Field(default=1440, description="Account lockout duration (minutes)")
    session_cleanup_interval_hours: int = Field(default=6, description="Session cleanup interval (hours)")
    require_email_verification: bool = Field(default=True, description="Require email verification for new accounts")
    
    # Rate Limiting Configuration
    rate_limit_requests_per_minute: int = Field(default=60, description="Rate limit requests per minute per user")
    rate_limit_requests_per_hour: int = Field(default=1000, description="Rate limit requests per hour per user")
    rate_limit_window_size_seconds: int = Field(default=3600, description="Rate limit window size (seconds)")
    
    # Security Monitoring
    security_log_retention_days: int = Field(default=90, description="Security log retention period (days)")
    session_activity_log_retention_days: int = Field(default=30, description="Session activity log retention (days)")
    enable_security_alerts: bool = Field(default=True, description="Enable security event alerting")
    
    # Multi-Factor Authentication (Future)
    mfa_issuer_name: str = Field(default="MCP ADHD Server", description="MFA issuer name")
    mfa_backup_codes_count: int = Field(default=10, description="Number of MFA backup codes")
    
    # Session Security
    csrf_token_expiry_hours: int = Field(default=8, description="CSRF token expiry (hours)")
    device_fingerprint_enabled: bool = Field(default=True, description="Enable device fingerprinting")
    session_ip_validation: bool = Field(default=True, description="Validate session IP addresses")
    
    # Crisis Support Access (ADHD-Specific)
    crisis_bypass_auth: bool = Field(default=True, description="Allow crisis support access without full auth")
    crisis_keywords: List[str] = Field(
        default=["crisis", "emergency", "suicide", "self-harm", "help"],
        description="Keywords that trigger crisis support bypass"
    )
    
    # Feature Flags
    enable_voice_input: bool = Field(default=False, description="Enable voice input")
    enable_screen_monitoring: bool = Field(
        default=False, 
        description="Enable screen monitoring"
    )
    enable_punishment_mode: bool = Field(
        default=False, 
        description="Enable punishment mode"
    )
    enable_energy_tracking: bool = Field(
        default=True, 
        description="Enable energy tracking"
    )
    
    # Monitoring and Observability Configuration
    sentry_dsn: Optional[str] = Field(
        default=None, 
        description="Sentry DSN for error tracking"
    )
    sentry_environment: str = Field(
        default="development",
        description="Sentry environment name"
    )
    sentry_traces_sample_rate: float = Field(
        default=0.1,
        description="Sentry traces sample rate (0.0 to 1.0)"
    )
    sentry_profiles_sample_rate: float = Field(
        default=0.1,
        description="Sentry profiling sample rate (0.0 to 1.0)"
    )
    
    # OpenTelemetry Configuration
    otel_service_name: str = Field(
        default="mcp-adhd-server",
        description="OpenTelemetry service name"
    )
    otel_service_version: str = Field(
        default="1.0.0",
        description="OpenTelemetry service version"
    )
    otel_exporter_jaeger_endpoint: Optional[str] = Field(
        default=None,
        description="Jaeger exporter endpoint"
    )
    otel_exporter_prometheus_endpoint: str = Field(
        default="http://localhost:9090",
        description="Prometheus exporter endpoint"
    )
    otel_traces_exporter: str = Field(
        default="console",
        description="OpenTelemetry traces exporter (console, jaeger, otlp)"
    )
    otel_metrics_exporter: str = Field(
        default="prometheus",
        description="OpenTelemetry metrics exporter (console, prometheus, otlp)"
    )
    otel_resource_attributes: str = Field(
        default="service.name=mcp-adhd-server,service.version=1.0.0",
        description="OpenTelemetry resource attributes"
    )
    
    # ADHD-Specific Monitoring Configuration
    adhd_response_time_target: float = Field(
        default=3.0,
        description="Target response time for ADHD users (seconds)"
    )
    adhd_attention_span_tracking: bool = Field(
        default=True,
        description="Enable attention span tracking"
    )
    adhd_cognitive_load_monitoring: bool = Field(
        default=True,
        description="Enable cognitive load monitoring"
    )
    adhd_crisis_detection_enabled: bool = Field(
        default=True,
        description="Enable crisis detection monitoring"
    )
    adhd_hyperfocus_detection_enabled: bool = Field(
        default=True,
        description="Enable hyperfocus session detection"
    )
    
    # Performance Monitoring Configuration
    performance_monitoring_enabled: bool = Field(
        default=True,
        description="Enable performance monitoring"
    )
    database_query_monitoring: bool = Field(
        default=True,
        description="Enable database query performance monitoring"
    )
    api_endpoint_monitoring: bool = Field(
        default=True,
        description="Enable API endpoint monitoring"
    )
    memory_monitoring_enabled: bool = Field(
        default=True,
        description="Enable memory usage monitoring"
    )
    cpu_monitoring_enabled: bool = Field(
        default=True,
        description="Enable CPU usage monitoring"
    )
    
    # Alerting Configuration
    alerting_enabled: bool = Field(
        default=True,
        description="Enable alerting system"
    )
    critical_error_alert_threshold: int = Field(
        default=5,
        description="Critical error count threshold for alerting"
    )
    response_time_alert_threshold: float = Field(
        default=5.0,
        description="Response time threshold for alerting (seconds)"
    )
    memory_usage_alert_threshold: float = Field(
        default=85.0,
        description="Memory usage alert threshold (%)"
    )
    cpu_usage_alert_threshold: float = Field(
        default=80.0,
        description="CPU usage alert threshold (%)"
    )
    
    # Business Intelligence Metrics
    user_engagement_tracking: bool = Field(
        default=True,
        description="Enable user engagement tracking"
    )
    feature_adoption_tracking: bool = Field(
        default=True,
        description="Enable feature adoption tracking"
    )
    nudge_effectiveness_tracking: bool = Field(
        default=True,
        description="Enable nudge effectiveness tracking"
    )
    calendar_integration_analytics: bool = Field(
        default=True,
        description="Enable calendar integration analytics"
    )
    crisis_intervention_analytics: bool = Field(
        default=True,
        description="Enable crisis intervention effectiveness tracking"
    )


# Global settings instance
settings = Settings()