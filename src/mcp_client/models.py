"""
MCP Client Data Models

Core data structures for the Model Context Protocol client.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ToolType(str, Enum):
    """Types of tools available in the MCP ecosystem."""
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity" 
    CALENDAR = "calendar"
    EMAIL = "email"
    FILES = "files"
    CODE = "code"
    HEALTH = "health"
    SMART_HOME = "smart_home"
    FINANCE = "finance"
    NOTES = "notes"
    TASKS = "tasks"
    HABITS = "habits"
    FOCUS = "focus"


class ToolCapability(str, Enum):
    """Capabilities that tools can provide."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    SEARCH = "search"
    SUBSCRIBE = "subscribe"
    WEBHOOK = "webhook"
    REALTIME = "realtime"


class AuthType(str, Enum):
    """Authentication methods supported."""
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC = "basic"
    BEARER = "bearer"
    CUSTOM = "custom"


class ToolStatus(str, Enum):
    """Tool registration and availability status."""
    REGISTERED = "registered"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected" 
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"


class ResourceType(str, Enum):
    """Types of resources that tools can provide."""
    DATA = "data"
    FILE = "file"
    STREAM = "stream"
    EVENT = "event"
    WEBHOOK = "webhook"
    SUBSCRIPTION = "subscription"


class ToolConfig(BaseModel):
    """Configuration for registering a tool with the MCP client."""
    tool_id: str = Field(..., description="Unique identifier for the tool")
    name: str = Field(..., description="Human-readable tool name")
    description: str = Field(..., description="Tool description and capabilities")
    tool_type: ToolType = Field(..., description="Category of tool")
    version: str = Field(default="1.0.0", description="Tool version")
    
    # Connection details
    endpoint_url: Optional[str] = Field(None, description="Tool endpoint URL")
    websocket_url: Optional[str] = Field(None, description="WebSocket URL for realtime")
    
    # Authentication
    auth_type: AuthType = Field(AuthType.API_KEY, description="Authentication method")
    auth_config: Dict[str, Any] = Field(default_factory=dict, description="Auth configuration")
    
    # Capabilities
    capabilities: List[ToolCapability] = Field(default_factory=list, description="Tool capabilities")
    supported_operations: List[str] = Field(default_factory=list, description="Supported operations")
    
    # Rate limiting
    rate_limit: Optional[int] = Field(None, description="Max requests per minute")
    burst_limit: Optional[int] = Field(None, description="Burst request limit")
    
    # ADHD-specific settings
    cognitive_load: float = Field(default=0.5, description="Cognitive load of using this tool (0-1)")
    adhd_friendly: bool = Field(default=True, description="Tool is ADHD-optimized")
    focus_safe: bool = Field(default=True, description="Safe to use during focus time")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tool tags for discovery")
    priority: int = Field(default=5, description="Tool priority (1-10)")
    enabled: bool = Field(default=True, description="Tool is enabled")


class ToolResult(BaseModel):
    """Result from a tool invocation."""
    success: bool = Field(..., description="Operation succeeded")
    data: Optional[Any] = Field(None, description="Result data")
    message: Optional[str] = Field(None, description="Human-readable message")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    # Metadata
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    tokens_used: Optional[int] = Field(None, description="API tokens consumed")
    rate_limit_remaining: Optional[int] = Field(None, description="Remaining rate limit")
    
    # ADHD context
    cognitive_load_impact: Optional[float] = Field(None, description="Cognitive load of this result")
    follow_up_suggested: bool = Field(default=False, description="Follow-up action suggested")
    focus_disruption_level: float = Field(default=0.0, description="How disruptive this was (0-1)")


class ToolError(BaseModel):
    """Error information from tool operations."""
    error_type: str = Field(..., description="Error category")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    retryable: bool = Field(default=False, description="Error is retryable")
    suggested_action: Optional[str] = Field(None, description="Suggested user action")


class Tool(BaseModel):
    """A registered tool in the MCP client."""
    config: ToolConfig = Field(..., description="Tool configuration")
    status: ToolStatus = Field(ToolStatus.REGISTERED, description="Current status")
    
    # Connection state
    connected_at: Optional[datetime] = Field(None, description="When tool was connected")
    last_used: Optional[datetime] = Field(None, description="Last successful use")
    last_error: Optional[ToolError] = Field(None, description="Most recent error")
    
    # Usage statistics
    total_invocations: int = Field(default=0, description="Total times invoked")
    successful_invocations: int = Field(default=0, description="Successful invocations")
    average_response_time_ms: Optional[float] = Field(None, description="Average response time")
    
    # ADHD metrics
    user_satisfaction_score: Optional[float] = Field(None, description="User satisfaction (1-5)")
    focus_friendly_score: Optional[float] = Field(None, description="Focus impact score (1-5)")
    cognitive_load_score: Optional[float] = Field(None, description="Cognitive load (1-5)")


class ResourceConfig(BaseModel):
    """Configuration for a resource provided by a tool."""
    resource_id: str = Field(..., description="Unique resource identifier")
    resource_type: ResourceType = Field(..., description="Type of resource")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Resource description")
    
    # Access control
    read_access: bool = Field(default=True, description="Resource can be read")
    write_access: bool = Field(default=False, description="Resource can be modified")
    subscribe_access: bool = Field(default=False, description="Can subscribe to changes")
    
    # Caching
    cacheable: bool = Field(default=True, description="Resource can be cached")
    cache_ttl_seconds: Optional[int] = Field(None, description="Cache TTL in seconds")
    
    # ADHD considerations
    cognitive_load: float = Field(default=0.3, description="Load of accessing this resource")
    priority: int = Field(default=5, description="Resource priority (1-10)")


class Resource(BaseModel):
    """A resource provided by a tool."""
    config: ResourceConfig = Field(..., description="Resource configuration")
    tool_id: str = Field(..., description="Tool providing this resource")
    
    # State
    available: bool = Field(default=True, description="Resource is available")
    last_accessed: Optional[datetime] = Field(None, description="Last access time")
    access_count: int = Field(default=0, description="Number of times accessed")
    
    # Caching
    cached_data: Optional[Any] = Field(None, description="Cached resource data")
    cache_expires_at: Optional[datetime] = Field(None, description="Cache expiration")


class ResourceResult(BaseModel):
    """Result from accessing a resource."""
    success: bool = Field(..., description="Access succeeded")
    data: Optional[Any] = Field(None, description="Resource data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Resource metadata")
    
    # Caching info
    from_cache: bool = Field(default=False, description="Data served from cache")
    cache_age_seconds: Optional[int] = Field(None, description="Cache age in seconds")
    
    # Performance
    access_time_ms: Optional[float] = Field(None, description="Access time in milliseconds")
    error: Optional[ToolError] = Field(None, description="Error if access failed")


class ContextFrame(BaseModel):
    """ADHD context frame for tool operations."""
    frame_id: str = Field(..., description="Unique frame identifier")
    user_id: str = Field(..., description="User this frame belongs to")
    
    # Current context
    current_task: Optional[str] = Field(None, description="Current task description")
    focus_level: float = Field(default=0.5, description="Current focus level (0-1)")
    energy_level: float = Field(default=0.5, description="Current energy level (0-1)")
    cognitive_load: float = Field(default=0.3, description="Current cognitive load (0-1)")
    
    # Time context
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Frame creation time")
    time_of_day: str = Field(..., description="Time context (morning, afternoon, evening)")
    time_zone: str = Field(default="UTC", description="User timezone")
    
    # Environment
    location: Optional[str] = Field(None, description="Current location context")
    environment: Optional[str] = Field(None, description="Work environment (home, office, etc)")
    distractions_level: float = Field(default=0.3, description="Current distraction level (0-1)")
    
    # User state
    mood: Optional[str] = Field(None, description="Current mood")
    stress_level: float = Field(default=0.3, description="Stress level (0-1)")
    hyperfocus_risk: float = Field(default=0.2, description="Risk of hyperfocus (0-1)")
    
    # Tool context
    active_tools: List[str] = Field(default_factory=list, description="Currently active tools")
    recent_tool_results: List[ToolResult] = Field(default_factory=list, description="Recent results")
    tool_usage_pattern: Dict[str, Any] = Field(default_factory=dict, description="Tool usage patterns")


class WorkflowStep(BaseModel):
    """A step in an MCP workflow."""
    step_id: str = Field(..., description="Unique step identifier")
    tool_id: str = Field(..., description="Tool to invoke")
    operation: str = Field(..., description="Operation to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")
    
    # Flow control
    condition: Optional[str] = Field(None, description="Condition to execute this step")
    retry_count: int = Field(default=0, description="Number of retries allowed")
    timeout_seconds: Optional[int] = Field(None, description="Step timeout")
    
    # Dependencies
    depends_on: List[str] = Field(default_factory=list, description="Step dependencies")
    parallel: bool = Field(default=False, description="Can run in parallel")
    
    # ADHD considerations
    cognitive_load_budget: Optional[float] = Field(None, description="Max cognitive load for step")
    focus_required: bool = Field(default=False, description="Requires focused attention")
    interruption_safe: bool = Field(default=True, description="Safe to interrupt")


class Integration(BaseModel):
    """An integration combining multiple tools for ADHD workflows."""
    integration_id: str = Field(..., description="Unique integration identifier")
    name: str = Field(..., description="Integration name")
    description: str = Field(..., description="Integration description")
    
    # Components
    tools: List[str] = Field(..., description="Tools used in this integration")
    workflow_steps: List[WorkflowStep] = Field(..., description="Workflow definition")
    
    # ADHD optimization
    adhd_optimized: bool = Field(default=True, description="Optimized for ADHD users")
    max_cognitive_load: float = Field(default=0.7, description="Max cognitive load threshold")
    focus_mode_compatible: bool = Field(default=True, description="Works in focus mode")
    
    # State
    enabled: bool = Field(default=True, description="Integration is enabled")
    last_used: Optional[datetime] = Field(None, description="Last execution time")
    success_rate: Optional[float] = Field(None, description="Success rate (0-1)")
    
    # User customization
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User-specific settings")
    custom_parameters: Dict[str, Any] = Field(default_factory=dict, description="Custom parameters")