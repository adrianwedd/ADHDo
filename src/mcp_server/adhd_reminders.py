"""
ADHD Time-Based Reminder System
Provides scheduled interventions for executive function support
"""
import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class ReminderType(Enum):
    """Types of ADHD-specific reminders."""
    MEDICATION = "medication"
    HYDRATION = "hydration"
    BREAK = "break"
    MEAL = "meal"
    SLEEP = "sleep"
    EXERCISE = "exercise"
    FOCUS = "focus"
    TRANSITION = "transition"
    CUSTOM = "custom"

class ReminderPriority(Enum):
    """Urgency levels for reminders."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Reminder:
    """Individual reminder configuration."""
    id: str
    type: ReminderType
    message: str
    time: Optional[time] = None  # For scheduled reminders
    interval_minutes: Optional[int] = None  # For recurring reminders
    priority: ReminderPriority = ReminderPriority.NORMAL
    enabled: bool = True
    require_acknowledgment: bool = False
    last_triggered: Optional[datetime] = None
    acknowledgment_received: bool = False
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for Redis storage."""
        return {
            'id': self.id,
            'type': self.type.value,
            'message': self.message,
            'time': self.time.isoformat() if self.time else None,
            'interval_minutes': self.interval_minutes,
            'priority': self.priority.value,
            'enabled': self.enabled,
            'require_acknowledgment': self.require_acknowledgment,
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None,
            'acknowledgment_received': self.acknowledgment_received,
            'custom_data': self.custom_data
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Reminder':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            type=ReminderType(data['type']),
            message=data['message'],
            time=time.fromisoformat(data['time']) if data.get('time') else None,
            interval_minutes=data.get('interval_minutes'),
            priority=ReminderPriority(data.get('priority', 'normal')),
            enabled=data.get('enabled', True),
            require_acknowledgment=data.get('require_acknowledgment', False),
            last_triggered=datetime.fromisoformat(data['last_triggered']) if data.get('last_triggered') else None,
            acknowledgment_received=data.get('acknowledgment_received', False),
            custom_data=data.get('custom_data', {})
        )

class ADHDReminderSystem:
    """Manages time-based reminders for ADHD support."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.reminders: Dict[str, Reminder] = {}
        self.scheduler_task: Optional[asyncio.Task] = None
        self.nudge_callback = None  # Will be set to nest_nudges.send_nudge
        
        # Default reminder templates
        self.default_reminders = [
            # Medication reminders
            Reminder(
                id="med_morning",
                type=ReminderType.MEDICATION,
                message="Time for your morning medication! 💊 This helps your focus today.",
                time=time(8, 0),
                priority=ReminderPriority.HIGH,
                require_acknowledgment=True
            ),
            Reminder(
                id="med_afternoon",
                type=ReminderType.MEDICATION,
                message="Afternoon medication time! 💊 Keep your momentum going.",
                time=time(14, 0),
                priority=ReminderPriority.HIGH,
                require_acknowledgment=True
            ),
            
            # Hydration reminders
            Reminder(
                id="hydrate_regular",
                type=ReminderType.HYDRATION,
                message="Hydration check! 💧 Your brain needs water to focus.",
                interval_minutes=90,
                priority=ReminderPriority.LOW
            ),
            
            # Break reminders
            Reminder(
                id="break_pomodoro",
                type=ReminderType.BREAK,
                message="You've been focused for 25 minutes! Time for a 5-minute break. Stand up and stretch!",
                interval_minutes=25,
                priority=ReminderPriority.NORMAL
            ),
            
            # Meal reminders
            Reminder(
                id="meal_breakfast",
                type=ReminderType.MEAL,
                message="Breakfast time! 🍳 Fuel your brain for the day.",
                time=time(7, 30),
                priority=ReminderPriority.NORMAL
            ),
            Reminder(
                id="meal_lunch",
                type=ReminderType.MEAL,
                message="Lunch break! 🥗 Step away from work and nourish yourself.",
                time=time(12, 30),
                priority=ReminderPriority.NORMAL
            ),
            Reminder(
                id="meal_dinner",
                type=ReminderType.MEAL,
                message="Dinner time! 🍽️ End your work day and enjoy a meal.",
                time=time(18, 30),
                priority=ReminderPriority.NORMAL
            ),
            
            # Sleep hygiene
            Reminder(
                id="sleep_winddown",
                type=ReminderType.SLEEP,
                message="Start winding down! 🌙 Blue light off, relaxing activities only.",
                time=time(21, 30),
                priority=ReminderPriority.NORMAL
            ),
            Reminder(
                id="sleep_bedtime",
                type=ReminderType.SLEEP,
                message="Bedtime! 😴 Consistent sleep helps ADHD symptoms tomorrow.",
                time=time(22, 30),
                priority=ReminderPriority.HIGH
            ),
            
            # Exercise reminder
            Reminder(
                id="exercise_daily",
                type=ReminderType.EXERCISE,
                message="Movement time! 🏃 Even 10 minutes helps your focus.",
                time=time(15, 0),
                priority=ReminderPriority.NORMAL
            )
        ]
    
    async def initialize(self, nudge_callback=None) -> bool:
        """Initialize the reminder system."""
        try:
            logger.info("🕐 Initializing ADHD reminder system")
            
            # Set nudge callback
            self.nudge_callback = nudge_callback
            
            # Load saved reminders from Redis or use defaults
            await self._load_reminders()
            
            # Start scheduler
            self.scheduler_task = asyncio.create_task(self._reminder_scheduler())
            
            logger.info(f"✅ Reminder system initialized with {len(self.reminders)} reminders")
            return True
            
        except Exception as e:
            logger.error(f"❌ Reminder initialization failed: {e}")
            return False
    
    async def _load_reminders(self):
        """Load reminders from Redis or use defaults."""
        try:
            if self.redis:
                # Try to load from Redis
                saved_reminders = await self.redis.get("adhd:reminders")
                if saved_reminders:
                    reminder_data = json.loads(saved_reminders)
                    for r_dict in reminder_data:
                        reminder = Reminder.from_dict(r_dict)
                        self.reminders[reminder.id] = reminder
                    logger.info(f"Loaded {len(self.reminders)} reminders from Redis")
                    return
            
            # Use default reminders
            for reminder in self.default_reminders:
                self.reminders[reminder.id] = reminder
            logger.info(f"Loaded {len(self.reminders)} default reminders")
            
        except Exception as e:
            logger.error(f"Error loading reminders: {e}")
            # Fall back to defaults
            for reminder in self.default_reminders:
                self.reminders[reminder.id] = reminder
    
    async def _save_reminders(self):
        """Save reminders to Redis."""
        try:
            if self.redis:
                reminder_data = [r.to_dict() for r in self.reminders.values()]
                await self.redis.set("adhd:reminders", json.dumps(reminder_data))
                logger.debug("Saved reminders to Redis")
        except Exception as e:
            logger.error(f"Error saving reminders: {e}")
    
    async def _reminder_scheduler(self):
        """Main scheduler loop for checking and triggering reminders."""
        logger.info("⏰ Reminder scheduler started")
        
        while True:
            try:
                now = datetime.now()
                current_time = now.time()
                
                for reminder in self.reminders.values():
                    if not reminder.enabled:
                        continue
                    
                    should_trigger = False
                    
                    # Check scheduled reminders
                    if reminder.time:
                        # Check if it's time and hasn't been triggered today
                        if (current_time.hour == reminder.time.hour and 
                            current_time.minute == reminder.time.minute):
                            
                            if not reminder.last_triggered or \
                               reminder.last_triggered.date() < now.date():
                                should_trigger = True
                    
                    # Check interval reminders
                    elif reminder.interval_minutes:
                        if not reminder.last_triggered:
                            should_trigger = True
                        else:
                            time_since = now - reminder.last_triggered
                            if time_since >= timedelta(minutes=reminder.interval_minutes):
                                should_trigger = True
                    
                    # Trigger reminder if needed
                    if should_trigger:
                        await self._trigger_reminder(reminder)
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
    
    async def _trigger_reminder(self, reminder: Reminder):
        """Trigger a specific reminder."""
        try:
            logger.info(f"🔔 Triggering {reminder.type.value} reminder: {reminder.id}")
            
            # Update last triggered time
            reminder.last_triggered = datetime.now()
            reminder.acknowledgment_received = False
            
            # Send nudge if callback is available
            if self.nudge_callback:
                # Adjust urgency based on priority
                urgency_map = {
                    ReminderPriority.LOW: "low",
                    ReminderPriority.NORMAL: "normal",
                    ReminderPriority.HIGH: "high",
                    ReminderPriority.CRITICAL: "urgent"
                }
                
                await self.nudge_callback(
                    message=reminder.message,
                    urgency=urgency_map[reminder.priority],
                    nudge_type="reminder"
                )
                
                # Schedule follow-up if acknowledgment required
                if reminder.require_acknowledgment:
                    asyncio.create_task(self._check_acknowledgment(reminder))
            
            # Save updated state
            await self._save_reminders()
            
        except Exception as e:
            logger.error(f"Error triggering reminder {reminder.id}: {e}")
    
    async def _check_acknowledgment(self, reminder: Reminder, max_attempts: int = 3):
        """Check for acknowledgment and escalate if needed."""
        for attempt in range(1, max_attempts + 1):
            # Wait for acknowledgment
            await asyncio.sleep(300)  # 5 minutes
            
            if reminder.acknowledgment_received:
                logger.info(f"✅ Acknowledgment received for {reminder.id}")
                break
            
            # Escalate reminder
            escalated_message = f"⚠️ REMINDER (attempt {attempt + 1}): {reminder.message}"
            
            if self.nudge_callback:
                await self.nudge_callback(
                    message=escalated_message,
                    urgency="urgent" if attempt == max_attempts else "high",
                    nudge_type="reminder_escalation"
                )
    
    async def acknowledge_reminder(self, reminder_id: str) -> bool:
        """Mark a reminder as acknowledged."""
        if reminder_id in self.reminders:
            self.reminders[reminder_id].acknowledgment_received = True
            await self._save_reminders()
            logger.info(f"✅ Reminder {reminder_id} acknowledged")
            return True
        return False
    
    async def add_custom_reminder(self, message: str, trigger_time: Optional[time] = None,
                                 interval_minutes: Optional[int] = None,
                                 priority: str = "normal") -> str:
        """Add a custom reminder."""
        reminder_id = f"custom_{datetime.now().timestamp()}"
        
        reminder = Reminder(
            id=reminder_id,
            type=ReminderType.CUSTOM,
            message=message,
            time=trigger_time,
            interval_minutes=interval_minutes,
            priority=ReminderPriority(priority)
        )
        
        self.reminders[reminder_id] = reminder
        await self._save_reminders()
        
        logger.info(f"Added custom reminder: {reminder_id}")
        return reminder_id
    
    async def update_reminder(self, reminder_id: str, **kwargs) -> bool:
        """Update an existing reminder."""
        if reminder_id not in self.reminders:
            return False
        
        reminder = self.reminders[reminder_id]
        
        # Update allowed fields
        for key, value in kwargs.items():
            if hasattr(reminder, key):
                setattr(reminder, key, value)
        
        await self._save_reminders()
        logger.info(f"Updated reminder: {reminder_id}")
        return True
    
    async def get_reminders(self, type_filter: Optional[ReminderType] = None) -> List[Dict]:
        """Get all reminders, optionally filtered by type."""
        reminders = []
        for reminder in self.reminders.values():
            if type_filter is None or reminder.type == type_filter:
                reminders.append(reminder.to_dict())
        return reminders
    
    async def cleanup(self):
        """Clean up resources."""
        if self.scheduler_task:
            self.scheduler_task.cancel()
            await asyncio.gather(self.scheduler_task, return_exceptions=True)
        logger.info("🕐 Reminder system shut down")

# Global instance
adhd_reminders: Optional[ADHDReminderSystem] = None

async def initialize_reminders(redis_client=None, nudge_callback=None) -> bool:
    """Initialize the global reminder system."""
    global adhd_reminders
    
    try:
        adhd_reminders = ADHDReminderSystem(redis_client)
        success = await adhd_reminders.initialize(nudge_callback)
        
        if not success:
            adhd_reminders = None
            return False
        
        logger.info("🕐 ADHD reminder system ready")
        return True
        
    except Exception as e:
        logger.error(f"❌ Reminder system initialization failed: {e}")
        adhd_reminders = None
        return False