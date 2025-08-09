"""Configuration management for MCP ADHD Server."""
from typing import Optional

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
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://mcp:password@localhost:5432/mcp_adhd",
        description="Database URL"
    )
    
    # Google Calendar Configuration (Optional)
    google_calendar_credentials_file: Optional[str] = Field(
        default=None, 
        description="Google Calendar credentials file path"
    )
    google_calendar_id: str = Field(default="primary", description="Google Calendar ID")
    
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
    
    # Integration Performance Configuration
    database_performance_threshold: float = Field(
        default=100.0,
        description="Database response time threshold (ms)"
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
        description="JWT secret key"
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


# Global settings instance
settings = Settings()