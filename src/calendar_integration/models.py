"""
Calendar models for ADHD-specific time management features.

These models extend basic calendar functionality with ADHD-specific
features like transition support, overwhelm detection, and executive
function assistance.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of calendar events for ADHD processing."""
    MEETING = "meeting"
    APPOINTMENT = "appointment"
    TASK = "task"
    BREAK = "break"
    TRAVEL = "travel"
    FOCUS_BLOCK = "focus_block"
    SOCIAL = "social"
    EXERCISE = "exercise"
    MEAL = "meal"
    PERSONAL = "personal"
    WORK = "work"
    UNKNOWN = "unknown"


class TransitionType(str, Enum):
    """Types of transitions between activities."""
    PHYSICAL = "physical"  # Moving between locations
    MENTAL = "mental"     # Switching between different types of tasks
    ENERGY = "energy"     # High to low energy activities or vice versa
    SOCIAL = "social"     # Solo to group activities or vice versa
    FOCUS = "focus"       # Deep work to meetings or vice versa


class AlertType(str, Enum):
    """Types of ADHD-specific alerts."""
    TRANSITION_WARNING = "transition_warning"
    PREPARATION_REMINDER = "preparation_reminder"
    TRAVEL_TIME = "travel_time"
    BREAK_REMINDER = "break_reminder"
    OVERWHELM_WARNING = "overwhelm_warning"
    HYPERFOCUS_BREAK = "hyperfocus_break"
    ENERGY_MISMATCH = "energy_mismatch"


class EnergyLevel(int, Enum):
    """Energy levels for event matching."""
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5


class CalendarEvent(BaseModel):
    """Enhanced calendar event with ADHD-specific features."""
    
    # Basic event data
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    google_event_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    
    # Timing
    start_time: datetime
    end_time: datetime
    duration_minutes: int = Field(default=0)
    all_day: bool = Field(default=False)
    
    # ADHD-specific categorization
    event_type: EventType = EventType.UNKNOWN
    energy_required: EnergyLevel = EnergyLevel.MEDIUM
    focus_required: int = Field(default=5, ge=1, le=10)
    social_intensity: int = Field(default=1, ge=1, le=10)
    
    # Preparation and transition
    preparation_time_minutes: int = Field(default=15)
    travel_time_minutes: int = Field(default=0)
    buffer_time_minutes: int = Field(default=5)
    
    # ADHD accommodations
    preparation_checklist: List[str] = Field(default_factory=list)
    materials_needed: List[str] = Field(default_factory=list)
    transition_notes: Optional[str] = None
    
    # Attendees and context
    attendees: List[str] = Field(default_factory=list)
    is_recurring: bool = Field(default=False)
    recurrence_pattern: Optional[str] = None
    
    # User customization
    user_id: str
    custom_alerts: List[int] = Field(default_factory=lambda: [15, 5])  # minutes before
    overwhelm_weight: float = Field(default=1.0, ge=0.1, le=5.0)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_alerted: Optional[datetime] = None
    
    def calculate_duration(self) -> None:
        """Calculate and set duration in minutes."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)
    
    def get_effective_start_time(self) -> datetime:
        """Get start time including preparation and travel time."""
        total_prep_time = self.preparation_time_minutes + self.travel_time_minutes
        return self.start_time - timedelta(minutes=total_prep_time)
    
    def get_total_time_commitment(self) -> int:
        """Get total time commitment in minutes including prep, travel, and buffer."""
        return (
            self.preparation_time_minutes + 
            self.travel_time_minutes + 
            self.duration_minutes + 
            self.buffer_time_minutes
        )
    
    def needs_transition_alert(self, current_time: datetime) -> bool:
        """Check if event needs transition alert at current time."""
        if self.last_alerted and (current_time - self.last_alerted).total_seconds() < 300:
            return False  # Don't spam alerts
        
        effective_start = self.get_effective_start_time()
        time_until_prep = (effective_start - current_time).total_seconds() / 60
        
        return time_until_prep <= max(self.custom_alerts) and time_until_prep > 0


class TransitionAlert(BaseModel):
    """Alert for helping with ADHD transitions between activities."""
    
    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    event: CalendarEvent
    
    # Alert details
    alert_type: AlertType
    transition_type: TransitionType
    message: str
    minutes_before_event: int
    
    # Context for the alert
    current_activity: Optional[str] = None
    suggested_actions: List[str] = Field(default_factory=list)
    preparation_items: List[str] = Field(default_factory=list)
    
    # Timing
    scheduled_time: datetime
    sent_at: Optional[datetime] = None
    acknowledged: bool = Field(default=False)
    snoozed_until: Optional[datetime] = None
    
    # Effectiveness tracking
    was_helpful: Optional[bool] = None
    user_feedback: Optional[str] = None
    led_to_action: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CalendarInsight(BaseModel):
    """ADHD-specific insights about calendar patterns and scheduling."""
    
    insight_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    
    # Time period for analysis
    analysis_start: datetime
    analysis_end: datetime
    
    # Schedule density analysis
    total_events: int
    total_committed_hours: float
    average_daily_events: float
    busiest_day: Optional[str] = None
    longest_continuous_block: int = Field(default=0)  # minutes
    
    # Overwhelm indicators
    overwhelm_score: float = Field(default=0.0, ge=0.0, le=10.0)
    high_density_periods: List[Dict[str, Any]] = Field(default_factory=list)
    insufficient_breaks: List[Dict[str, Any]] = Field(default_factory=list)
    back_to_back_meetings: int = Field(default=0)
    
    # Energy management
    energy_mismatches: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_energy_blocks: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Transition analysis
    difficult_transitions: List[Dict[str, Any]] = Field(default_factory=list)
    travel_time_warnings: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    suggested_buffer_adjustments: List[Dict[str, Any]] = Field(default_factory=list)
    optimal_scheduling_windows: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Pattern recognition
    preferred_meeting_times: List[str] = Field(default_factory=list)
    problematic_time_slots: List[str] = Field(default_factory=list)
    successful_scheduling_patterns: List[str] = Field(default_factory=list)
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ScheduleOptimizationSuggestion(BaseModel):
    """Suggestion for optimizing calendar scheduling for ADHD users."""
    
    suggestion_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    
    # The issue being addressed
    issue_type: str  # "overwhelm", "poor_transitions", "energy_mismatch", etc.
    severity: int = Field(ge=1, le=10)
    description: str
    
    # The suggested change
    suggestion_type: str  # "reschedule", "add_buffer", "break_block", etc.
    suggested_action: str
    
    # If rescheduling is suggested
    affected_events: List[str] = Field(default_factory=list)  # event_ids
    suggested_new_times: List[datetime] = Field(default_factory=list)
    
    # Benefits of implementing the suggestion
    expected_benefits: List[str] = Field(default_factory=list)
    energy_improvement: Optional[int] = Field(default=None, ge=1, le=10)
    overwhelm_reduction: Optional[int] = Field(default=None, ge=1, le=10)
    
    # Implementation details
    implementation_difficulty: int = Field(default=5, ge=1, le=10)
    requires_coordination: bool = Field(default=False)
    automated_implementation: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    implemented: bool = Field(default=False)
    user_feedback: Optional[str] = None


class CalendarPreferences(BaseModel):
    """User preferences for ADHD calendar management."""
    
    user_id: str
    
    # Alert preferences
    default_alert_times: List[int] = Field(default_factory=lambda: [15, 5])  # minutes
    transition_alert_enabled: bool = Field(default=True)
    travel_time_alerts: bool = Field(default=True)
    preparation_reminders: bool = Field(default=True)
    
    # Overwhelm prevention
    max_daily_events: Optional[int] = Field(default=8)
    min_break_between_meetings: int = Field(default=15)  # minutes
    preferred_break_duration: int = Field(default=15)  # minutes
    max_continuous_meeting_time: int = Field(default=120)  # minutes
    
    # Energy management
    peak_energy_hours: List[int] = Field(default_factory=lambda: [9, 10, 11])  # 24-hour format
    low_energy_hours: List[int] = Field(default_factory=lambda: [13, 14, 15])
    avoid_scheduling_during_low_energy: bool = Field(default=True)
    
    # Focus and social preferences
    max_focus_intensity_events_per_day: int = Field(default=3)
    max_social_intensity_per_day: int = Field(default=50)
    prefer_grouped_meetings: bool = Field(default=True)
    
    # Buffer and preparation time defaults
    default_preparation_time: int = Field(default=15)  # minutes
    default_travel_buffer: int = Field(default=10)  # minutes
    default_post_meeting_buffer: int = Field(default=5)  # minutes
    
    # Notification channels
    notification_methods: List[str] = Field(default_factory=lambda: ["calendar", "telegram"])
    quiet_hours_start: int = Field(default=22)  # 24-hour format
    quiet_hours_end: int = Field(default=7)
    
    # Advanced features
    automatic_scheduling_optimization: bool = Field(default=False)
    hyperfocus_break_reminders: bool = Field(default=True)
    context_switching_assistance: bool = Field(default=True)
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)