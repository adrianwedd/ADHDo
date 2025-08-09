"""
Calendar-based nudge system for ADHD time management.

This module extends the existing nudge engine with calendar-specific
nudging capabilities including:
- Transition warnings and preparation reminders
- Time blindness compensation
- Context switching assistance
- Hyperfocus break reminders
- Overwhelm prevention alerts
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog

from mcp_server.models import User, NudgeTier
from mcp_server.exception_handlers import ADHDFeatureException
from nudge.engine import NudgeMethod, nudge_engine
from .models import (
    CalendarEvent, TransitionAlert, CalendarPreferences,
    AlertType, EventType, EnergyLevel
)

logger = structlog.get_logger()


class CalendarNudger(NudgeMethod):
    """
    Calendar-specific nudging system for ADHD time management.
    
    Provides context-aware nudges for:
    - Event preparation and transitions
    - Time awareness and estimation
    - Schedule overwhelm prevention
    - Executive function support
    """
    
    def __init__(self):
        # Active calendar-based nudge sequences
        self.active_calendar_nudges: Dict[str, Dict[str, Any]] = {}
        
        # Nudge message templates for different scenarios
        self.nudge_templates = {
            AlertType.TRANSITION_WARNING: {
                NudgeTier.GENTLE: [
                    "🌱 Hey, '{event_title}' is coming up in {minutes} minutes. Ready to start transitioning?",
                    "✨ Gentle reminder: time to wrap up and get ready for '{event_title}'",
                    "🕐 '{event_title}' begins soon. Want to start your prep routine?"
                ],
                NudgeTier.SARCASTIC: [
                    "🙄 Unless you're planning to teleport, you might want to start getting ready for '{event_title}'",
                    "⏰ Time flies when you're having fun, but '{event_title}' starts in {minutes} minutes",
                    "🤨 That thing called '{event_title}' is happening soon. Just saying."
                ],
                NudgeTier.SERGEANT: [
                    "⚡ ATTENTION! '{event_title}' STARTS IN {minutes} MINUTES. MOVE!",
                    "🚨 THIS IS NOT A DRILL. GET READY FOR '{event_title}' RIGHT NOW!",
                    "💥 DROP EVERYTHING. '{event_title}' PREP TIME IS NOW!"
                ]
            },
            AlertType.PREPARATION_REMINDER: {
                NudgeTier.GENTLE: [
                    "📋 Time for a quick prep check for '{event_title}'. What do you need to gather?",
                    "🎒 '{event_title}' preparation time. Let's get organized!",
                    "✅ Preparation mode: '{event_title}' needs your attention"
                ],
                NudgeTier.SARCASTIC: [
                    "📝 Pop quiz: What do you need for '{event_title}'? (Hint: probably more than just your charming personality)",
                    "🎭 Time to put on your adult pants and prep for '{event_title}'",
                    "🧩 Missing something for '{event_title}'? Check your prep list!"
                ],
                NudgeTier.SERGEANT: [
                    "📋 PREP LIST FOR '{event_title}' - EXECUTE NOW!",
                    "🎯 PREPARATION PROTOCOL INITIATED FOR '{event_title}'",
                    "⚡ GET YOUR GEAR! '{event_title}' PREP TIME!"
                ]
            },
            AlertType.TRAVEL_TIME: {
                NudgeTier.GENTLE: [
                    "🚗 Time to head to {location} for '{event_title}'. Safe travels!",
                    "🗺️ Navigation time! '{event_title}' at {location} awaits",
                    "✈️ Time to make your way to '{event_title}'"
                ],
                NudgeTier.SARCASTIC: [
                    "🚗 Unless you've mastered teleportation, it's time to leave for '{event_title}'",
                    "⏱️ Traffic doesn't care about your schedule. Time to go to '{event_title}'!",
                    "🗺️ GPS says go. '{event_title}' won't wait for you."
                ],
                NudgeTier.SERGEANT: [
                    "🚨 DEPARTURE TIME FOR '{event_title}'! MOVE OUT!",
                    "⚡ TRAVEL WINDOW CLOSING! GO TO '{event_title}' NOW!",
                    "🚗 ENGINE START! '{event_title}' DEPARTURE TIME!"
                ]
            },
            AlertType.HYPERFOCUS_BREAK: {
                NudgeTier.GENTLE: [
                    "🌊 You've been in the zone for a while. Maybe time for a quick break?",
                    "☕ Hyperfocus detected! Your brain might appreciate a short break",
                    "🧘 Deep work session noted. Consider a mindful pause"
                ],
                NudgeTier.SARCASTIC: [
                    "🔍 I see you there, hyperfocusing. Remember food? Water? The outside world?",
                    "⏰ You've been in hyperfocus prison. Time for parole!",
                    "🤖 Beep beep! Your human maintenance is overdue"
                ],
                NudgeTier.SERGEANT: [
                    "⚡ HYPERFOCUS BREAK MANDATORY! STAND UP NOW!",
                    "🚨 HUMAN MAINTENANCE REQUIRED! BREAK TIME!",
                    "💥 STEP AWAY FROM THE WORK! BREAK PROTOCOL INITIATED!"
                ]
            },
            AlertType.OVERWHELM_WARNING: {
                NudgeTier.GENTLE: [
                    "🌱 Your schedule looks pretty packed. Want to review and maybe adjust?",
                    "💙 Busy day ahead. Remember to breathe and take things one at a time",
                    "🌿 Schedule density alert. Consider what's truly essential today"
                ],
                NudgeTier.SARCASTIC: [
                    "📅 Did you clone yourself? This schedule seems ambitious even for you",
                    "🤹 Unless you're a professional juggler, this schedule might be too much",
                    "⏰ Your calendar is busier than a bee convention. Maybe dial it back?"
                ],
                NudgeTier.SERGEANT: [
                    "🚨 OVERWHELM ALERT! REDUCE SCHEDULE IMMEDIATELY!",
                    "⚡ CALENDAR OVERLOAD! PRIORITIZE AND ELIMINATE!",
                    "💥 SCHEDULE INTERVENTION REQUIRED! TAKE ACTION!"
                ]
            }
        }
    
    async def send_nudge(self, 
                        user: User, 
                        message: str, 
                        tier: NudgeTier,
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Send calendar-specific nudge using existing nudge methods."""
        # Use the global nudge engine to send via user's preferred methods
        success_count = 0
        total_methods = 0
        
        for method_name in user.preferred_nudge_methods:
            total_methods += 1
            try:
                # Get the nudge method from the global engine
                if method_name in nudge_engine.methods:
                    method = nudge_engine.methods[method_name]
                    success = await method.send_nudge(user, message, tier, metadata)
                    if success:
                        success_count += 1
                    
            except Exception as e:
                logger.error("Calendar nudge method failed", 
                           method=method_name, 
                           user_id=user.user_id, 
                           error=str(e))
                # Don't raise immediately - try other methods first
        
        return success_count > 0
    
    async def send_transition_alert(self, 
                                   user: User, 
                                   alert: TransitionAlert,
                                   tier: NudgeTier = NudgeTier.GENTLE) -> bool:
        """Send transition alert nudge."""
        try:
            message = self._format_transition_message(alert, tier)
            
            # Add calendar-specific metadata
            metadata = {
                'alert_type': alert.alert_type.value,
                'event_id': alert.event.event_id,
                'event_title': alert.event.title,
                'minutes_before': alert.minutes_before_event,
                'suggested_actions': alert.suggested_actions,
                'calendar_nudge': True
            }
            
            success = await self.send_nudge(user, message, tier, metadata)
            
            if success:
                alert.sent_at = datetime.utcnow()
                logger.info("Sent transition alert", 
                           user_id=user.user_id,
                           alert_type=alert.alert_type.value,
                           event_title=alert.event.title,
                           tier=tier.name)
            
            return success
            
        except Exception as e:
            logger.error("Failed to send transition alert", 
                        user_id=user.user_id, 
                        alert_id=alert.alert_id,
                        error=str(e))
            # Raise ADHD-friendly error for handling by the API layer
            raise ADHDFeatureException("transition_alert", f"Unable to send transition alert: {str(e)}", recoverable=True)
    
    async def send_overwhelm_warning(self, 
                                   user: User, 
                                   overwhelm_score: float,
                                   recommendations: List[str],
                                   tier: NudgeTier = NudgeTier.GENTLE) -> bool:
        """Send overwhelm prevention warning."""
        try:
            templates = self.nudge_templates[AlertType.OVERWHELM_WARNING][tier]
            message = templates[0]  # Use first template
            
            # Add specific recommendations
            if recommendations:
                message += "\n\nSuggestions:"
                for i, rec in enumerate(recommendations[:3]):  # Limit to 3
                    message += f"\n• {rec}"
            
            metadata = {
                'alert_type': 'overwhelm_warning',
                'overwhelm_score': overwhelm_score,
                'recommendations': recommendations[:3],
                'calendar_nudge': True
            }
            
            success = await self.send_nudge(user, message, tier, metadata)
            
            if success:
                logger.info("Sent overwhelm warning", 
                           user_id=user.user_id,
                           overwhelm_score=overwhelm_score,
                           tier=tier.name)
            
            return success
            
        except Exception as e:
            logger.error("Failed to send overwhelm warning", 
                        user_id=user.user_id, 
                        error=str(e))
            raise ADHDFeatureException("overwhelm_warning", f"Unable to send overwhelm warning: {str(e)}", recoverable=True)
    
    async def send_hyperfocus_break_reminder(self, 
                                           user: User, 
                                           duration_minutes: int,
                                           current_activity: Optional[str] = None,
                                           tier: NudgeTier = NudgeTier.GENTLE) -> bool:
        """Send hyperfocus break reminder."""
        try:
            templates = self.nudge_templates[AlertType.HYPERFOCUS_BREAK][tier]
            import random
            message = random.choice(templates)
            
            # Add duration context
            if duration_minutes > 60:
                hours = duration_minutes // 60
                minutes = duration_minutes % 60
                duration_str = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
            else:
                duration_str = f"{duration_minutes}m"
            
            message += f"\n⏱️ Focus duration: {duration_str}"
            
            if current_activity:
                message += f"\n🎯 Current activity: {current_activity}"
            
            metadata = {
                'alert_type': 'hyperfocus_break',
                'duration_minutes': duration_minutes,
                'current_activity': current_activity,
                'calendar_nudge': True
            }
            
            success = await self.send_nudge(user, message, tier, metadata)
            
            if success:
                logger.info("Sent hyperfocus break reminder", 
                           user_id=user.user_id,
                           duration_minutes=duration_minutes,
                           tier=tier.name)
            
            return success
            
        except Exception as e:
            logger.error("Failed to send hyperfocus break reminder", 
                        user_id=user.user_id, 
                        error=str(e))
            raise ADHDFeatureException("hyperfocus_break", f"Unable to send hyperfocus break reminder: {str(e)}", recoverable=True)
    
    async def start_event_monitoring(self, 
                                   user: User, 
                                   events: List[CalendarEvent],
                                   preferences: Optional[CalendarPreferences] = None) -> None:
        """Start monitoring calendar events for nudge opportunities."""
        sequence_id = f"calendar:{user.user_id}"
        
        # Stop existing monitoring for this user
        if sequence_id in self.active_calendar_nudges:
            await self.stop_event_monitoring(user.user_id)
        
        # Initialize monitoring sequence
        self.active_calendar_nudges[sequence_id] = {
            'user': user,
            'events': events,
            'preferences': preferences,
            'started_at': datetime.utcnow(),
            'last_check': None,
            'sent_alerts': set()
        }
        
        # Start monitoring task
        asyncio.create_task(self._monitor_calendar_events(sequence_id))
        
        logger.info("Started calendar event monitoring", 
                   user_id=user.user_id, 
                   event_count=len(events))
    
    async def stop_event_monitoring(self, user_id: str) -> None:
        """Stop calendar event monitoring for user."""
        sequence_id = f"calendar:{user_id}"
        
        if sequence_id in self.active_calendar_nudges:
            del self.active_calendar_nudges[sequence_id]
            logger.info("Stopped calendar event monitoring", user_id=user_id)
    
    async def _monitor_calendar_events(self, sequence_id: str) -> None:
        """Monitor calendar events and send timely nudges."""
        try:
            while sequence_id in self.active_calendar_nudges:
                sequence = self.active_calendar_nudges[sequence_id]
                user = sequence['user']
                events = sequence['events']
                preferences = sequence.get('preferences')
                sent_alerts = sequence['sent_alerts']
                
                current_time = datetime.utcnow()
                
                # Check each event for nudge opportunities
                for event in events:
                    if event.event_id in sent_alerts:
                        continue  # Already sent alert for this event
                    
                    # Check if event needs transition alert
                    if self._should_send_transition_alert(event, current_time, preferences):
                        alert_type = self._determine_alert_type(event, current_time)
                        tier = self._determine_nudge_tier(event, current_time, preferences)
                        
                        # Create and send alert
                        from .processor import ADHDCalendarProcessor
                        processor = ADHDCalendarProcessor()
                        alert = processor._create_transition_alert(event, user.user_id, current_time)
                        
                        if alert:
                            success = await self.send_transition_alert(user, alert, tier)
                            if success:
                                sent_alerts.add(event.event_id)
                
                # Check for hyperfocus situations
                await self._check_hyperfocus_situation(user, current_time, preferences)
                
                # Update last check time
                sequence['last_check'] = current_time
                
                # Wait before next check (check every 2 minutes for responsiveness)
                await asyncio.sleep(120)
                
        except asyncio.CancelledError:
            logger.info("Calendar monitoring cancelled", sequence_id=sequence_id)
        except Exception as e:
            logger.error("Calendar monitoring error", sequence_id=sequence_id, error=str(e))
            # Clean up failed monitoring
            if sequence_id in self.active_calendar_nudges:
                del self.active_calendar_nudges[sequence_id]
    
    def _should_send_transition_alert(self, 
                                     event: CalendarEvent, 
                                     current_time: datetime,
                                     preferences: Optional[CalendarPreferences]) -> bool:
        """Determine if transition alert should be sent for event."""
        effective_start = event.get_effective_start_time()
        minutes_until_prep = (effective_start - current_time).total_seconds() / 60
        
        # Check if within alert window
        alert_times = (preferences.default_alert_times if preferences 
                      else event.custom_alerts)
        
        for alert_time in alert_times:
            if abs(minutes_until_prep - alert_time) <= 2:  # Within 2 minutes of alert time
                return True
        
        # Emergency alert if very close to start time
        minutes_until_start = (event.start_time - current_time).total_seconds() / 60
        if 0 <= minutes_until_start <= 5:
            return True
        
        return False
    
    def _determine_alert_type(self, event: CalendarEvent, current_time: datetime) -> AlertType:
        """Determine the type of alert needed."""
        effective_start = event.get_effective_start_time()
        minutes_until_prep = (effective_start - current_time).total_seconds() / 60
        minutes_until_start = (event.start_time - current_time).total_seconds() / 60
        
        if minutes_until_start <= 5:
            return AlertType.TRANSITION_WARNING
        elif minutes_until_prep <= event.preparation_time_minutes:
            return AlertType.PREPARATION_REMINDER
        elif event.travel_time_minutes > 0 and minutes_until_prep <= event.travel_time_minutes:
            return AlertType.TRAVEL_TIME
        else:
            return AlertType.PREPARATION_REMINDER
    
    def _determine_nudge_tier(self, 
                            event: CalendarEvent, 
                            current_time: datetime,
                            preferences: Optional[CalendarPreferences]) -> NudgeTier:
        """Determine appropriate nudge tier based on urgency and user preferences."""
        minutes_until_start = (event.start_time - current_time).total_seconds() / 60
        
        # Emergency tier for very close events
        if minutes_until_start <= 2:
            return NudgeTier.SERGEANT
        elif minutes_until_start <= 5:
            return NudgeTier.SARCASTIC
        else:
            return NudgeTier.GENTLE
    
    async def _check_hyperfocus_situation(self, 
                                        user: User, 
                                        current_time: datetime,
                                        preferences: Optional[CalendarPreferences]) -> None:
        """Check for hyperfocus situations and send break reminders."""
        if not preferences or not preferences.hyperfocus_break_reminders:
            return
        
        # This would typically check user activity patterns
        # For now, we'll skip implementation as it requires activity monitoring
        pass
    
    def _format_transition_message(self, alert: TransitionAlert, tier: NudgeTier) -> str:
        """Format transition alert message based on tier."""
        templates = self.nudge_templates.get(alert.alert_type, {}).get(tier, [])
        
        if not templates:
            # Fallback message
            return f"Reminder: '{alert.event.title}' is coming up!"
        
        # Use first template and format it
        import random
        template = random.choice(templates)
        
        # Replace placeholders
        message = template.format(
            event_title=alert.event.title,
            minutes=alert.minutes_before_event,
            location=alert.event.location or "your location"
        )
        
        # Add suggested actions if available
        if alert.suggested_actions:
            message += "\n\n📋 Quick prep:"
            for action in alert.suggested_actions[:3]:  # Limit to 3
                message += f"\n• {action}"
        
        return message


# Global calendar nudger instance
calendar_nudger = CalendarNudger()