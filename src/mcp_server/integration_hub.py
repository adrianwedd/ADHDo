"""
ADHD Integration Hub - The Brain That Actually Connects Everything
This is where disconnected components become a system.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Types of events that flow through the system."""
    # Time events
    WAKE_UP = "wake_up"
    MORNING_ROUTINE = "morning_routine"
    WORK_START = "work_start"
    BREAK_TIME = "break_time"
    LUNCH_TIME = "lunch_time"
    EVENING_WIND_DOWN = "evening_wind_down"
    BEDTIME = "bedtime"
    
    # Calendar events
    MEETING_IMMINENT = "meeting_imminent"  # 15 min before
    MEETING_SOON = "meeting_soon"  # 1 hour before
    MEETING_STARTING = "meeting_starting"
    MEETING_ENDED = "meeting_ended"
    CALENDAR_EMPTY = "calendar_empty"  # Good time to focus
    
    # Fitness events
    LOW_ACTIVITY = "low_activity"  # <1000 steps by noon
    ACTIVITY_GOAL_MET = "activity_goal_met"
    LONG_SITTING = "long_sitting"  # No movement for 90 min
    
    # Context events
    HIGH_COGNITIVE_LOAD = "high_cognitive_load"
    LOW_ENERGY = "low_energy"
    FOCUS_TIME_AVAILABLE = "focus_time_available"
    TASK_OVERDUE = "task_overdue"
    
    # User events
    VOICE_COMMAND = "voice_command"
    USER_REQUEST = "user_request"
    MANUAL_TRIGGER = "manual_trigger"

@dataclass
class SystemEvent:
    """An event that flows through the system."""
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    source: str  # Which component generated this
    priority: int = 5  # 1-10, higher = more important

@dataclass
class SystemAction:
    """An action the system should take."""
    action: str  # e.g., "send_nudge", "play_music", "create_reminder"
    target: str  # Which component should handle this
    params: Dict[str, Any]
    reason: str  # Why we're doing this (for logging/debugging)

class IntegrationHub:
    """
    The central nervous system that actually makes everything work together.
    """
    
    def __init__(self):
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.components: Dict[str, Any] = {}
        self.context: Dict[str, Any] = {}
        self.running = False
        
        # Register default handlers
        self._register_default_handlers()
    
    def register_component(self, name: str, component: Any):
        """Register a component (calendar, fitness, music, etc.)"""
        self.components[name] = component
        logger.info(f"✅ Registered component: {name}")
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to events."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    async def emit(self, event: SystemEvent):
        """Emit an event into the system."""
        await self.event_queue.put(event)
        logger.debug(f"📤 Event emitted: {event.type.value} from {event.source}")
    
    async def process_events(self):
        """Main event processing loop."""
        logger.info("🧠 Integration hub started")
        self.running = True
        
        while self.running:
            try:
                # Get next event (with timeout to allow shutdown)
                event = await asyncio.wait_for(
                    self.event_queue.get(), 
                    timeout=1.0
                )
                
                # Process the event
                await self._process_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def _process_event(self, event: SystemEvent):
        """Process a single event through all handlers."""
        logger.info(f"⚡ Processing: {event.type.value}")
        
        # Update context
        await self._update_context(event)
        
        # Get handlers for this event type
        handlers = self.handlers.get(event.type, [])
        
        # Execute all handlers
        for handler in handlers:
            try:
                actions = await handler(event, self.context, self.components)
                if actions:
                    await self._execute_actions(actions)
            except Exception as e:
                logger.error(f"Handler error: {e}")
    
    async def _update_context(self, event: SystemEvent):
        """Update system context based on event."""
        self.context['last_event'] = event
        self.context['last_event_time'] = event.timestamp
        
        # Update specific context based on event type
        if event.type in [EventType.MEETING_IMMINENT, EventType.MEETING_SOON]:
            self.context['upcoming_meeting'] = event.data
        elif event.type == EventType.MEETING_ENDED:
            self.context['upcoming_meeting'] = None
        elif event.type == EventType.LOW_ACTIVITY:
            self.context['needs_movement'] = True
        elif event.type == EventType.ACTIVITY_GOAL_MET:
            self.context['needs_movement'] = False
    
    async def _execute_actions(self, actions: List[SystemAction]):
        """Execute a list of actions."""
        for action in actions:
            try:
                logger.info(f"🎯 Executing: {action.action} → {action.target} ({action.reason})")
                
                component = self.components.get(action.target)
                if component:
                    method = getattr(component, action.action, None)
                    if method:
                        await method(**action.params)
                    else:
                        logger.warning(f"Method {action.action} not found on {action.target}")
                else:
                    logger.warning(f"Component {action.target} not registered")
                    
            except Exception as e:
                logger.error(f"Action execution failed: {e}")
    
    def _register_default_handlers(self):
        """Register the default event handlers that make the magic happen."""
        
        # Meeting preparation handler
        async def handle_meeting_prep(event, context, components):
            """Prepare for upcoming meetings."""
            if event.type == EventType.MEETING_IMMINENT:
                meeting = event.data
                actions = []
                
                # Send a nudge
                actions.append(SystemAction(
                    action="send_nudge",
                    target="nest",
                    params={
                        "message": f"Meeting in 15 minutes: {meeting.get('summary', 'Untitled')}",
                        "urgency": "high"
                    },
                    reason="Meeting starting soon"
                ))
                
                # Change music to focus mode
                actions.append(SystemAction(
                    action="play_focus_music",
                    target="music",
                    params={"intensity": "low"},
                    reason="Help transition to meeting mode"
                ))
                
                return actions
        
        self.subscribe(EventType.MEETING_IMMINENT, handle_meeting_prep)
        
        # Low activity handler
        async def handle_low_activity(event, context, components):
            """Encourage movement when activity is low."""
            actions = []
            
            # Check if we're in a meeting
            if not context.get('upcoming_meeting'):
                actions.append(SystemAction(
                    action="send_nudge",
                    target="nest",
                    params={
                        "message": "Time for a movement break! Take a quick walk.",
                        "urgency": "medium"
                    },
                    reason="Low activity detected"
                ))
                
                # Play energizing music
                actions.append(SystemAction(
                    action="play_energizing_music",
                    target="music",
                    params={},
                    reason="Encourage movement"
                ))
            
            return actions
        
        self.subscribe(EventType.LOW_ACTIVITY, handle_low_activity)
        
        # Focus time handler
        async def handle_focus_time(event, context, components):
            """Optimize environment for focus."""
            actions = []
            
            actions.append(SystemAction(
                action="create_focus_event",
                target="calendar",
                params={"duration_minutes": 25},
                reason="Calendar is clear - good time to focus"
            ))
            
            actions.append(SystemAction(
                action="play_focus_music",
                target="music",
                params={"intensity": "medium"},
                reason="Support deep focus"
            ))
            
            actions.append(SystemAction(
                action="send_nudge",
                target="nest",
                params={
                    "message": "Focus time! 25 minutes of deep work starting now.",
                    "urgency": "low"
                },
                reason="Start focus session"
            ))
            
            return actions
        
        self.subscribe(EventType.FOCUS_TIME_AVAILABLE, handle_focus_time)
        
        logger.info("✅ Default handlers registered")

class ContextAnalyzer:
    """
    Analyzes the current context and generates events.
    This is what makes the system "aware" and proactive.
    """
    
    def __init__(self, hub: IntegrationHub):
        self.hub = hub
        self.last_check = datetime.now()
    
    async def analyze_loop(self):
        """Continuously analyze context and generate events."""
        logger.info("🔍 Context analyzer started")
        
        while True:
            try:
                await self._analyze_current_state()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Context analysis error: {e}")
                await asyncio.sleep(60)
    
    async def _analyze_current_state(self):
        """Analyze current state and emit relevant events."""
        now = datetime.now()
        
        # Get components
        calendar = self.hub.components.get('calendar')
        fitness = self.hub.components.get('fitness')
        
        if not calendar or not fitness:
            return
        
        # Check calendar
        if hasattr(calendar, 'get_calendar_events'):
            events = await calendar.get_calendar_events(max_results=5, hours_ahead=2)
            
            if events:
                next_event = events[0]
                minutes_until = next_event.get('time_until_minutes', 999)
                
                if 10 <= minutes_until <= 15:
                    await self.hub.emit(SystemEvent(
                        type=EventType.MEETING_IMMINENT,
                        data=next_event,
                        timestamp=now,
                        source="context_analyzer",
                        priority=8
                    ))
                elif 55 <= minutes_until <= 65:
                    await self.hub.emit(SystemEvent(
                        type=EventType.MEETING_SOON,
                        data=next_event,
                        timestamp=now,
                        source="context_analyzer",
                        priority=6
                    ))
            else:
                # No events in next 2 hours - good focus time
                if now.hour >= 9 and now.hour < 17:  # Work hours
                    await self.hub.emit(SystemEvent(
                        type=EventType.FOCUS_TIME_AVAILABLE,
                        data={"duration_available": 120},
                        timestamp=now,
                        source="context_analyzer",
                        priority=5
                    ))
        
        # Check fitness
        if hasattr(fitness, 'get_today_stats'):
            stats = await fitness.get_today_stats()
            
            if not stats.get('error'):
                steps = stats.get('steps', 0)
                
                # Check for low activity
                if now.hour >= 12 and steps < 1000:
                    await self.hub.emit(SystemEvent(
                        type=EventType.LOW_ACTIVITY,
                        data={"steps": steps},
                        timestamp=now,
                        source="context_analyzer",
                        priority=4
                    ))
                
                # Check for goal met
                if steps >= 8000 and self.hub.context.get('needs_movement'):
                    await self.hub.emit(SystemEvent(
                        type=EventType.ACTIVITY_GOAL_MET,
                        data={"steps": steps},
                        timestamp=now,
                        source="context_analyzer",
                        priority=3
                    ))
        
        # Time-based events
        hour = now.hour
        
        if hour == 8 and (now - self.last_check).seconds > 3000:
            await self.hub.emit(SystemEvent(
                type=EventType.MORNING_ROUTINE,
                data={},
                timestamp=now,
                source="context_analyzer",
                priority=5
            ))
        elif hour == 12 and (now - self.last_check).seconds > 3000:
            await self.hub.emit(SystemEvent(
                type=EventType.LUNCH_TIME,
                data={},
                timestamp=now,
                source="context_analyzer",
                priority=4
            ))
        elif hour == 21 and (now - self.last_check).seconds > 3000:
            await self.hub.emit(SystemEvent(
                type=EventType.EVENING_WIND_DOWN,
                data={},
                timestamp=now,
                source="context_analyzer",
                priority=5
            ))
        
        self.last_check = now

# Global instances
integration_hub: Optional[IntegrationHub] = None
context_analyzer: Optional[ContextAnalyzer] = None

def initialize_integration():
    """Initialize the integration system."""
    global integration_hub, context_analyzer
    
    integration_hub = IntegrationHub()
    context_analyzer = ContextAnalyzer(integration_hub)
    
    logger.info("🚀 Integration hub initialized")
    return integration_hub, context_analyzer