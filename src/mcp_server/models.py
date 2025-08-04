"""Data models for MCP ADHD Server."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserState(str, Enum):
    """User energy/mood states."""
    ENERGIZED = "energized"
    FOCUSED = "focused" 
    LOW = "low"
    ANXIOUS = "anxious"
    FRAGMENTED = "fragmented"
    HYPERFOCUS = "hyperfocus"
    CRASHED = "crashed"


class TaskPriority(str, Enum):
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SOMEDAY = "someday"


class NudgeTier(int, Enum):
    """Nudge escalation tiers."""
    GENTLE = 0      # "Let's get started?"
    SARCASTIC = 1   # "Still ignoring that thing, huh?"
    SERGEANT = 2    # "Get. Up. And. Do. It."


class ContextType(str, Enum):
    """Types of context data."""
    MEMORY_TRACE = "memory_trace"
    CALENDAR = "calendar"
    USER_STATE = "user_state"
    ENVIRONMENT = "environment"
    TASK = "task"
    ACHIEVEMENT = "achievement"


class ActionType(str, Enum):
    """Types of actions the system can take."""
    NUDGE = "nudge"
    SUGGESTION = "suggestion"
    ENVIRONMENT_CHANGE = "environment_change"
    ACHIEVEMENT = "achievement"
    PUNISHMENT = "punishment"


class FrameContext(BaseModel):
    """Individual context item in an MCP Frame."""
    type: ContextType
    timestamp: datetime
    data: Dict[str, Any]
    source: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class FrameAction(BaseModel):
    """Action to be taken based on context."""
    type: ActionType
    method: str  # telegram, home_assistant, etc.
    payload: Dict[str, Any]
    delay: Optional[int] = None  # seconds to delay action
    conditions: Optional[Dict[str, Any]] = None


class MCPFrame(BaseModel):
    """
    Model Context Protocol Frame - standardized context package for LLM agents.
    
    This is the core data structure that gets passed between agents,
    containing all necessary context for decision-making.
    """
    frame_id: str = Field(default_factory=lambda: f"frame-{uuid4().hex[:8]}")
    user_id: str
    agent_id: str
    task_focus: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Context data
    context: List[FrameContext] = Field(default_factory=list)
    
    # Suggested actions
    actions: List[FrameAction] = Field(default_factory=list)
    
    # Metadata
    priority: TaskPriority = TaskPriority.MEDIUM
    energy_cost: Optional[int] = Field(default=None, ge=1, le=10)
    dopamine_potential: Optional[int] = Field(default=None, ge=1, le=10)
    
    def add_context(
        self, 
        context_type: ContextType, 
        data: Dict[str, Any],
        source: Optional[str] = None,
        confidence: float = 1.0
    ) -> None:
        """Add context item to frame."""
        self.context.append(FrameContext(
            type=context_type,
            timestamp=datetime.utcnow(),
            data=data,
            source=source,
            confidence=confidence
        ))
    
    def add_action(
        self,
        action_type: ActionType,
        method: str,
        payload: Dict[str, Any],
        delay: Optional[int] = None
    ) -> None:
        """Add action to frame."""
        self.actions.append(FrameAction(
            type=action_type,
            method=method,
            payload=payload,
            delay=delay
        ))


class User(BaseModel):
    """User profile and preferences."""
    user_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    timezone: str = "UTC"
    
    # ADHD-specific preferences
    preferred_nudge_methods: List[str] = Field(default_factory=lambda: ["telegram"])
    nudge_hours_start: int = Field(default=7, ge=0, le=23)
    nudge_hours_end: int = Field(default=22, ge=0, le=23)
    max_nudge_tier: NudgeTier = NudgeTier.SARCASTIC
    
    # Energy patterns (learned over time)
    energy_patterns: Dict[str, Any] = Field(default_factory=dict)
    completion_patterns: Dict[str, Any] = Field(default_factory=dict)
    
    # Integrations
    telegram_chat_id: Optional[str] = None
    google_calendar_id: Optional[str] = None
    home_assistant_entities: List[str] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Task(BaseModel):
    """Task/intention tracking."""
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    title: str
    description: Optional[str] = None
    
    # Scheduling
    due_date: Optional[datetime] = None
    estimated_duration: Optional[int] = None  # minutes
    energy_required: Optional[int] = Field(default=None, ge=1, le=10)
    
    # State
    priority: TaskPriority = TaskPriority.MEDIUM
    status: str = "pending"  # pending, active, completed, abandoned
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # ADHD-specific
    dopamine_hooks: List[str] = Field(default_factory=list)
    avoidance_triggers: List[str] = Field(default_factory=list)
    completion_rewards: List[str] = Field(default_factory=list)
    
    # Nudging
    last_nudge: Optional[datetime] = None
    nudge_count: int = 0
    nudge_tier: NudgeTier = NudgeTier.GENTLE
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class TraceMemory(BaseModel):
    """Memory trace for intention vs. action tracking."""
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    
    # What happened
    event_type: str  # intention, action, completion, abandonment
    event_data: Dict[str, Any]
    
    # Context at time of event
    user_state: Optional[UserState] = None
    environment_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Relationships
    task_id: Optional[str] = None
    parent_trace_id: Optional[str] = None
    related_trace_ids: List[str] = Field(default_factory=list)
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "system"  # system, user, agent, integration


class AgentResponse(BaseModel):
    """Response from an LLM agent."""
    agent_id: str
    frame_id: str
    response_text: str
    suggested_actions: List[FrameAction] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NudgeAttempt(BaseModel):
    """Record of a nudge attempt."""
    nudge_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    task_id: str
    
    # Nudge details
    tier: NudgeTier
    method: str  # telegram, home_assistant, etc.
    message: str
    
    # Response tracking
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    delivered: bool = False
    responded: bool = False
    response_time: Optional[int] = None  # seconds
    response_action: Optional[str] = None
    
    # Effectiveness
    led_to_action: bool = False
    effectiveness_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)