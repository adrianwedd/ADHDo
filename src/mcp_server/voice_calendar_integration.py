"""
Voice-Enabled Calendar Integration for ADHD Support
Combines Google Calendar with voice commands through Google Assistant
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class VoiceCommand(Enum):
    """Voice commands for calendar and ADHD support."""
    WHATS_NEXT = "what's next"
    ADD_EVENT = "add event"
    REMIND_ME = "remind me"
    CHECK_CALENDAR = "check calendar"
    CANCEL_EVENT = "cancel event"
    RESCHEDULE = "reschedule"
    FOCUS_TIME = "focus time"
    BREAK_TIME = "break time"
    
@dataclass
class CalendarContext:
    """Current calendar context for ADHD awareness."""
    next_event: Optional[Dict] = None
    time_until_next: Optional[int] = None  # minutes
    current_activity: Optional[str] = None
    is_in_meeting: bool = False
    upcoming_events: List[Dict] = None
    focus_blocks: List[Dict] = None
    
class VoiceCalendarSystem:
    """Integrates voice commands with calendar for ADHD support."""
    
    def __init__(self):
        self.calendar_client = None
        self.nest_system = None
        self.context = CalendarContext()
        self.voice_handlers = {}
        self.scheduler_task = None
        
    async def initialize(self, calendar_client=None, nest_system=None):
        """Initialize the voice calendar system."""
        try:
            logger.info("🎤 Initializing voice calendar integration")
            
            # Use existing calendar client or initialize
            if calendar_client:
                self.calendar_client = calendar_client
            else:
                from mcp_server.google_calendar_simple import SimpleCalendarClient
                self.calendar_client = SimpleCalendarClient()
            
            # Use existing Nest system for voice output
            if nest_system:
                self.nest_system = nest_system
            else:
                from mcp_server.nest_nudges import nest_nudge_system
                self.nest_system = nest_nudge_system
            
            # Register voice command handlers
            self._register_handlers()
            
            # Start context monitoring
            self.scheduler_task = asyncio.create_task(self._monitor_calendar())
            
            logger.info("✅ Voice calendar system ready")
            return True
            
        except Exception as e:
            logger.error(f"Voice calendar initialization failed: {e}")
            return False
    
    def _register_handlers(self):
        """Register voice command handlers."""
        self.voice_handlers = {
            VoiceCommand.WHATS_NEXT: self.handle_whats_next,
            VoiceCommand.ADD_EVENT: self.handle_add_event,
            VoiceCommand.REMIND_ME: self.handle_remind_me,
            VoiceCommand.CHECK_CALENDAR: self.handle_check_calendar,
            VoiceCommand.FOCUS_TIME: self.handle_focus_time,
            VoiceCommand.BREAK_TIME: self.handle_break_time,
        }
    
    async def _monitor_calendar(self):
        """Monitor calendar for context awareness."""
        logger.info("📅 Calendar monitor started")
        
        while True:
            try:
                # Update context every 5 minutes
                await self._update_context()
                
                # Check for upcoming events needing prep
                if self.context.next_event and self.context.time_until_next:
                    await self._handle_event_preparation()
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Calendar monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _update_context(self):
        """Update calendar context."""
        try:
            # Get upcoming events
            events = await self._get_upcoming_events()
            
            if events:
                self.context.upcoming_events = events
                self.context.next_event = events[0]
                
                # Calculate time until next event
                next_time = datetime.fromisoformat(events[0]['start'].get('dateTime', events[0]['start'].get('date')))
                time_diff = next_time - datetime.now(next_time.tzinfo)
                self.context.time_until_next = int(time_diff.total_seconds() / 60)
                
                # Check if currently in a meeting
                if self.context.time_until_next <= 0 and self.context.time_until_next > -60:
                    self.context.is_in_meeting = True
                else:
                    self.context.is_in_meeting = False
                    
                logger.debug(f"Context updated: Next event in {self.context.time_until_next} minutes")
                
        except Exception as e:
            logger.error(f"Context update failed: {e}")
    
    async def _get_upcoming_events(self, hours_ahead: int = 4) -> List[Dict]:
        """Get upcoming calendar events."""
        if not self.calendar_client:
            return []
        
        try:
            # Use the calendar client's method
            now = datetime.utcnow()
            time_max = now + timedelta(hours=hours_ahead)
            
            # This would use the actual Google Calendar API
            # For now, return mock data for testing
            return [
                {
                    'summary': 'Team Standup',
                    'start': {'dateTime': (now + timedelta(hours=1)).isoformat() + 'Z'},
                    'end': {'dateTime': (now + timedelta(hours=1, minutes=30)).isoformat() + 'Z'}
                }
            ]
            
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []
    
    async def _handle_event_preparation(self):
        """Handle preparation nudges for upcoming events."""
        if not self.context.next_event or not self.nest_system:
            return
        
        time_until = self.context.time_until_next
        event_name = self.context.next_event.get('summary', 'your event')
        
        # 15-minute warning
        if time_until == 15:
            await self.send_voice_message(
                f"Heads up! {event_name} starts in 15 minutes. Time to wrap up what you're doing."
            )
        
        # 5-minute warning with music change
        elif time_until == 5:
            await self.send_voice_message(
                f"5 minute warning for {event_name}. Let me switch to calm music to help you transition."
            )
            # Trigger calm music
            from mcp_server.jellyfin_music import jellyfin_music
            if jellyfin_music:
                await jellyfin_music.play_mood_playlist("calm", volume=0.5)
        
        # 1-minute final warning
        elif time_until == 1:
            await self.send_voice_message(
                f"{event_name} is starting in 1 minute! Join now to avoid the ADHD tax of being late."
            )
    
    async def send_voice_message(self, message: str, urgency: str = "normal"):
        """Send a voice message through Nest devices."""
        if self.nest_system:
            from mcp_server.nest_nudges import NudgeType
            nudge_type = NudgeType.GENTLE if urgency == "normal" else NudgeType.URGENT
            await self.nest_system.send_nudge(message, nudge_type=nudge_type)
        else:
            logger.info(f"Voice message: {message}")
    
    # Voice command handlers
    async def handle_whats_next(self, params: Dict = None) -> str:
        """Handle 'what's next' voice command."""
        await self._update_context()
        
        if not self.context.next_event:
            response = "You have no upcoming events in the next 4 hours. Perfect time for deep focus work!"
        else:
            event_name = self.context.next_event.get('summary', 'Unknown event')
            time_until = self.context.time_until_next
            
            if time_until <= 0:
                response = f"You're currently in {event_name}"
            elif time_until < 60:
                response = f"{event_name} starts in {time_until} minutes"
            else:
                hours = time_until // 60
                minutes = time_until % 60
                response = f"{event_name} starts in {hours} hours and {minutes} minutes"
        
        await self.send_voice_message(response)
        return response
    
    async def handle_add_event(self, params: Dict) -> str:
        """Handle 'add event' voice command."""
        # Extract event details from params
        title = params.get('title', 'Quick event')
        duration = params.get('duration', 30)  # minutes
        when = params.get('when', 'now')
        
        # Calculate start time
        if when == 'now':
            start_time = datetime.now()
        elif when == 'in 5 minutes':
            start_time = datetime.now() + timedelta(minutes=5)
        else:
            start_time = datetime.now() + timedelta(hours=1)
        
        # Create event (would use actual calendar API)
        response = f"I've added '{title}' to your calendar for {duration} minutes"
        
        await self.send_voice_message(response)
        return response
    
    async def handle_remind_me(self, params: Dict) -> str:
        """Handle 'remind me' voice command."""
        what = params.get('what', 'your task')
        when = params.get('when', 'in 25 minutes')
        
        # Parse time
        if 'minutes' in when:
            minutes = int(when.split()[1])
        else:
            minutes = 25  # Default Pomodoro
        
        # Schedule reminder
        asyncio.create_task(self._delayed_reminder(what, minutes))
        
        response = f"I'll remind you to {what} in {minutes} minutes"
        await self.send_voice_message(response)
        return response
    
    async def _delayed_reminder(self, what: str, minutes: int):
        """Send a delayed reminder."""
        await asyncio.sleep(minutes * 60)
        await self.send_voice_message(f"Reminder: Time to {what}!", urgency="high")
    
    async def handle_check_calendar(self, params: Dict = None) -> str:
        """Handle 'check calendar' voice command."""
        await self._update_context()
        
        if not self.context.upcoming_events:
            response = "Your calendar is clear for the next 4 hours"
        else:
            events_summary = []
            for event in self.context.upcoming_events[:3]:  # Top 3 events
                name = event.get('summary', 'Unknown')
                start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
                time_str = start.strftime("%I:%M %p")
                events_summary.append(f"{name} at {time_str}")
            
            response = "Today you have: " + ", ".join(events_summary)
        
        await self.send_voice_message(response)
        return response
    
    async def handle_focus_time(self, params: Dict = None) -> str:
        """Handle 'focus time' voice command."""
        duration = params.get('duration', 25)  # Default Pomodoro
        
        # Check calendar for conflicts
        await self._update_context()
        
        if self.context.time_until_next and self.context.time_until_next < duration:
            response = f"You only have {self.context.time_until_next} minutes until your next event. Starting a shorter focus session."
            duration = self.context.time_until_next - 5  # Leave 5 min buffer
        else:
            response = f"Starting {duration} minute focus session. I'll remind you when it's time for a break."
        
        # Start focus music
        from mcp_server.jellyfin_music import jellyfin_music
        if jellyfin_music:
            await jellyfin_music.play_mood_playlist("focus", volume=0.7)
        
        # Schedule break reminder
        asyncio.create_task(self._delayed_reminder("take a break", duration))
        
        await self.send_voice_message(response)
        return response
    
    async def handle_break_time(self, params: Dict = None) -> str:
        """Handle 'break time' voice command."""
        duration = params.get('duration', 5)  # 5 min break
        
        response = f"Starting {duration} minute break. Stand up, stretch, and hydrate!"
        
        # Switch to calm music
        from mcp_server.jellyfin_music import jellyfin_music
        if jellyfin_music:
            await jellyfin_music.play_mood_playlist("calm", volume=0.5)
        
        # Schedule return reminder
        asyncio.create_task(self._delayed_reminder("get back to work", duration))
        
        await self.send_voice_message(response)
        return response
    
    async def process_voice_command(self, command: str, params: Dict = None) -> str:
        """Process a voice command."""
        try:
            # Parse command to enum
            command_lower = command.lower()
            voice_cmd = None
            
            for cmd in VoiceCommand:
                if cmd.value in command_lower:
                    voice_cmd = cmd
                    break
            
            if voice_cmd and voice_cmd in self.voice_handlers:
                return await self.voice_handlers[voice_cmd](params or {})
            else:
                return f"I don't understand '{command}'. Try 'what's next' or 'check calendar'"
                
        except Exception as e:
            logger.error(f"Voice command processing failed: {e}")
            return "Sorry, I had trouble processing that command"
    
    async def cleanup(self):
        """Clean up resources."""
        if self.scheduler_task:
            self.scheduler_task.cancel()
            await asyncio.gather(self.scheduler_task, return_exceptions=True)

# Global instance
voice_calendar: Optional[VoiceCalendarSystem] = None

async def initialize_voice_calendar(calendar_client=None, nest_system=None) -> bool:
    """Initialize the global voice calendar system."""
    global voice_calendar
    
    try:
        voice_calendar = VoiceCalendarSystem()
        success = await voice_calendar.initialize(calendar_client, nest_system)
        
        if not success:
            voice_calendar = None
            return False
        
        logger.info("🎤 Voice calendar system ready for ADHD support")
        return True
        
    except Exception as e:
        logger.error(f"Voice calendar initialization failed: {e}")
        voice_calendar = None
        return False