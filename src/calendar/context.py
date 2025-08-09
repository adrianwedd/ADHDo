"""
Calendar context integration for MCP frames.

This module provides calendar-aware context building that enriches
the cognitive loop with time management and scheduling information
specifically designed for ADHD users.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog

from mcp_server.models import ContextType, MCPFrame
from frames.builder import FrameBuilder
from .models import CalendarEvent, CalendarInsight, CalendarPreferences
from .processor import ADHDCalendarProcessor
from .client import CalendarClient

logger = structlog.get_logger()


class CalendarContextBuilder:
    """
    Builds calendar-aware context for MCP frames.
    
    Integrates with the existing frame builder to add:
    - Current and upcoming calendar events
    - Schedule density and overwhelm analysis
    - Transition and preparation requirements
    - Time-based energy and focus recommendations
    """
    
    def __init__(self, calendar_client: CalendarClient, processor: ADHDCalendarProcessor):
        self.calendar_client = calendar_client
        self.processor = processor
        
        # Context importance weights for different calendar contexts
        self.calendar_context_weights = {
            'current_event': 1.0,      # Highest priority - what's happening now
            'next_event': 0.9,         # Very important - immediate preparation needed
            'upcoming_events': 0.7,    # Important - helps with planning
            'schedule_insight': 0.6,   # Useful - provides optimization recommendations
            'time_awareness': 0.8,     # High priority for ADHD users
            'transition_alert': 0.95   # Very high - immediate action needed
        }
    
    async def add_calendar_context(self, 
                                  frame: MCPFrame, 
                                  user_id: str,
                                  calendar_id: str = 'primary',
                                  preferences: Optional[CalendarPreferences] = None) -> None:
        """
        Add calendar context to an MCP frame.
        
        Args:
            frame: MCP frame to enrich with calendar context
            user_id: User identifier
            calendar_id: Google Calendar ID to fetch events from
            preferences: User's calendar preferences
        """
        try:
            current_time = datetime.utcnow()
            
            # Get relevant calendar events (next 7 days)
            time_min = current_time - timedelta(hours=1)  # Include current events
            time_max = current_time + timedelta(days=7)
            
            events = await self._get_user_events(user_id, calendar_id, time_min, time_max)
            
            if not events:
                await self._add_empty_calendar_context(frame, user_id)
                return
            
            # Add different types of calendar context
            await self._add_current_event_context(frame, events, current_time)
            await self._add_upcoming_events_context(frame, events, current_time)
            await self._add_time_awareness_context(frame, events, current_time)
            await self._add_schedule_insight_context(frame, events, user_id, preferences)
            await self._add_transition_context(frame, events, current_time, user_id)
            
            logger.info("Added calendar context to frame", 
                       user_id=user_id, 
                       frame_id=frame.frame_id,
                       event_count=len(events))
            
        except Exception as e:
            logger.error("Failed to add calendar context", 
                        user_id=user_id, 
                        frame_id=frame.frame_id,
                        error=str(e))
            # Add error context instead of failing completely
            frame.add_context(
                ContextType.CALENDAR,
                {
                    'status': 'error',
                    'message': 'Calendar context temporarily unavailable',
                    'error_type': 'calendar_access_failed'
                },
                source="calendar_error",
                confidence=0.9
            )
    
    async def _get_user_events(self, 
                              user_id: str, 
                              calendar_id: str,
                              time_min: datetime, 
                              time_max: datetime) -> List[CalendarEvent]:
        """Get user's calendar events for the specified time range."""
        try:
            # This would typically load user credentials and fetch events
            # For now, we'll simulate with a placeholder
            events = self.calendar_client.get_events(
                calendar_id=calendar_id,
                time_min=time_min,
                time_max=time_max
            )
            
            # Set user_id for all events
            for event in events:
                event.user_id = user_id
            
            return events
            
        except Exception as e:
            logger.error("Failed to fetch user events", 
                        user_id=user_id, 
                        error=str(e))
            return []
    
    async def _add_current_event_context(self, 
                                        frame: MCPFrame, 
                                        events: List[CalendarEvent],
                                        current_time: datetime) -> None:
        """Add context about currently happening events."""
        current_events = [
            event for event in events
            if event.start_time <= current_time <= event.end_time
        ]
        
        if current_events:
            # Sort by priority (meetings > appointments > focus blocks)
            current_events.sort(key=lambda e: (
                e.event_type.value, 
                -e.focus_required, 
                -e.social_intensity
            ))
            
            primary_event = current_events[0]
            
            # Calculate time remaining
            time_remaining = (primary_event.end_time - current_time).total_seconds() / 60
            
            frame.add_context(
                ContextType.CALENDAR,
                {
                    'type': 'current_event',
                    'event': {
                        'title': primary_event.title,
                        'type': primary_event.event_type.value,
                        'location': primary_event.location,
                        'time_remaining_minutes': int(time_remaining),
                        'energy_required': primary_event.energy_required.value,
                        'focus_required': primary_event.focus_required,
                        'social_intensity': primary_event.social_intensity
                    },
                    'additional_events': len(current_events) - 1,
                    'context_priority': 'immediate'
                },
                source="calendar_current",
                confidence=1.0
            )
    
    async def _add_upcoming_events_context(self, 
                                          frame: MCPFrame, 
                                          events: List[CalendarEvent],
                                          current_time: datetime) -> None:
        """Add context about upcoming events needing attention."""
        upcoming_events = [
            event for event in events
            if event.start_time > current_time
        ]
        
        if not upcoming_events:
            return
        
        # Sort by start time
        upcoming_events.sort(key=lambda e: e.start_time)
        
        # Get next few important events
        next_events = upcoming_events[:3]  # Limit to prevent cognitive overload
        
        events_data = []
        for event in next_events:
            minutes_until = (event.start_time - current_time).total_seconds() / 60
            effective_start = event.get_effective_start_time()
            minutes_until_prep = (effective_start - current_time).total_seconds() / 60
            
            event_data = {
                'title': event.title,
                'start_time': event.start_time.isoformat(),
                'minutes_until_start': int(minutes_until),
                'minutes_until_prep': int(minutes_until_prep),
                'preparation_needed': minutes_until_prep <= 60,  # Prep needed within an hour
                'energy_required': event.energy_required.value,
                'preparation_time': event.preparation_time_minutes,
                'travel_time': event.travel_time_minutes
            }
            
            # Add urgency indicators
            if minutes_until <= 15:
                event_data['urgency'] = 'immediate'
            elif minutes_until <= 60:
                event_data['urgency'] = 'soon'
            elif minutes_until <= 240:  # 4 hours
                event_data['urgency'] = 'upcoming'
            else:
                event_data['urgency'] = 'planned'
            
            events_data.append(event_data)
        
        frame.add_context(
            ContextType.CALENDAR,
            {
                'type': 'upcoming_events',
                'events': events_data,
                'next_event_in_minutes': int((next_events[0].start_time - current_time).total_seconds() / 60),
                'preparation_needed': any(e['preparation_needed'] for e in events_data)
            },
            source="calendar_upcoming",
            confidence=0.9
        )
    
    async def _add_time_awareness_context(self, 
                                         frame: MCPFrame, 
                                         events: List[CalendarEvent],
                                         current_time: datetime) -> None:
        """Add time awareness context for ADHD time blindness support."""
        now_hour = current_time.hour
        
        # Categorize current time
        if 6 <= now_hour < 10:
            time_category = "morning"
            energy_level = "building"
        elif 10 <= now_hour < 14:
            time_category = "late_morning"
            energy_level = "peak"
        elif 14 <= now_hour < 18:
            time_category = "afternoon"
            energy_level = "moderate"
        elif 18 <= now_hour < 22:
            time_category = "evening"
            energy_level = "variable"
        else:
            time_category = "night"
            energy_level = "low"
        
        # Count events for rest of day
        rest_of_day = [
            event for event in events
            if event.start_time.date() == current_time.date() 
            and event.start_time > current_time
        ]
        
        # Calculate remaining committed time today
        remaining_minutes = sum(event.duration_minutes for event in rest_of_day)
        
        frame.add_context(
            ContextType.CALENDAR,
            {
                'type': 'time_awareness',
                'current_time': current_time.strftime('%H:%M'),
                'current_date': current_time.strftime('%Y-%m-%d'),
                'day_of_week': current_time.strftime('%A'),
                'time_category': time_category,
                'suggested_energy_level': energy_level,
                'remaining_events_today': len(rest_of_day),
                'remaining_committed_minutes': remaining_minutes,
                'time_until_day_end': (22 - now_hour) * 60 if now_hour < 22 else 0,
                'visual_time_indicator': self._get_visual_time_indicator(current_time)
            },
            source="calendar_time_awareness",
            confidence=1.0
        )
    
    async def _add_schedule_insight_context(self, 
                                          frame: MCPFrame, 
                                          events: List[CalendarEvent],
                                          user_id: str,
                                          preferences: Optional[CalendarPreferences]) -> None:
        """Add schedule analysis insights and recommendations."""
        if len(events) < 2:  # Need multiple events for meaningful analysis
            return
        
        try:
            # Perform ADHD-specific schedule analysis
            insight = self.processor.analyze_schedule(events, user_id, preferences)
            
            # Extract key insights for context
            insight_data = {
                'type': 'schedule_insight',
                'overwhelm_score': insight.overwhelm_score,
                'overwhelm_level': self._categorize_overwhelm(insight.overwhelm_score),
                'total_events': insight.total_events,
                'average_daily_events': round(insight.average_daily_events, 1),
                'back_to_back_meetings': insight.back_to_back_meetings,
                'energy_mismatches': len(insight.energy_mismatches),
                'difficult_transitions': len(insight.difficult_transitions),
                'top_recommendations': insight.recommendations[:3]  # Top 3 recommendations
            }
            
            # Add priority level based on insights
            if insight.overwhelm_score > 7:
                insight_data['priority'] = 'urgent'
                insight_data['action_required'] = True
            elif insight.overwhelm_score > 5 or insight.back_to_back_meetings > 2:
                insight_data['priority'] = 'high'
                insight_data['action_recommended'] = True
            else:
                insight_data['priority'] = 'normal'
            
            confidence = 0.8 if len(events) >= 5 else 0.6  # More events = higher confidence
            
            frame.add_context(
                ContextType.CALENDAR,
                insight_data,
                source="calendar_analysis",
                confidence=confidence
            )
            
        except Exception as e:
            logger.error("Failed to add schedule insight context", error=str(e))
    
    async def _add_transition_context(self, 
                                     frame: MCPFrame, 
                                     events: List[CalendarEvent],
                                     current_time: datetime,
                                     user_id: str) -> None:
        """Add context about upcoming transitions requiring attention."""
        # Get transition alerts for next few hours
        upcoming_events = [
            event for event in events
            if current_time <= event.start_time <= current_time + timedelta(hours=4)
        ]
        
        if not upcoming_events:
            return
        
        alerts = self.processor.generate_transition_alerts(upcoming_events, user_id, current_time)
        
        if alerts:
            # Process alerts for context
            alert_data = []
            for alert in alerts[:3]:  # Limit to prevent overload
                alert_info = {
                    'event_title': alert.event.title,
                    'alert_type': alert.alert_type.value,
                    'minutes_before_event': alert.minutes_before_event,
                    'suggested_actions': alert.suggested_actions[:2],  # Limit actions
                    'urgency': 'high' if alert.minutes_before_event <= 10 else 'medium'
                }
                alert_data.append(alert_info)
            
            frame.add_context(
                ContextType.CALENDAR,
                {
                    'type': 'transition_alerts',
                    'alerts': alert_data,
                    'immediate_action_needed': any(a['urgency'] == 'high' for a in alert_data),
                    'next_transition_in_minutes': min(a['minutes_before_event'] for a in alert_data)
                },
                source="calendar_transitions",
                confidence=0.95  # High confidence for actionable alerts
            )
    
    async def _add_empty_calendar_context(self, frame: MCPFrame, user_id: str) -> None:
        """Add context when no calendar events are available."""
        current_time = datetime.utcnow()
        
        frame.add_context(
            ContextType.CALENDAR,
            {
                'type': 'empty_calendar',
                'status': 'no_events',
                'current_time': current_time.strftime('%H:%M'),
                'suggestion': 'Great time for focused work or planning!',
                'time_category': self._get_time_category(current_time.hour),
                'opportunities': [
                    'Schedule important tasks',
                    'Block time for deep work',
                    'Plan tomorrow\'s priorities'
                ]
            },
            source="calendar_empty",
            confidence=0.7
        )
    
    def _get_visual_time_indicator(self, current_time: datetime) -> Dict[str, Any]:
        """Get visual time indicator data for ADHD time awareness."""
        hour = current_time.hour
        minute = current_time.minute
        
        # Create visual time representation
        progress_through_hour = minute / 60.0
        progress_through_day = (hour * 60 + minute) / (24 * 60)
        
        return {
            'hour_progress': round(progress_through_hour, 2),
            'day_progress': round(progress_through_day, 2),
            'time_blocks_remaining': max(0, 22 - hour),  # Assuming 22:00 end of day
            'visual_format': f"{'█' * int(progress_through_hour * 10)}{'░' * (10 - int(progress_through_hour * 10))}"
        }
    
    def _categorize_overwhelm(self, overwhelm_score: float) -> str:
        """Categorize overwhelm score into human-readable levels."""
        if overwhelm_score >= 8:
            return "very_high"
        elif overwhelm_score >= 6:
            return "high"
        elif overwhelm_score >= 4:
            return "moderate"
        elif overwhelm_score >= 2:
            return "low"
        else:
            return "minimal"
    
    def _get_time_category(self, hour: int) -> str:
        """Get time category for the given hour."""
        if 6 <= hour < 10:
            return "morning"
        elif 10 <= hour < 14:
            return "late_morning"
        elif 14 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"


# Extension to the existing FrameBuilder to include calendar context
class EnhancedFrameBuilder(FrameBuilder):
    """
    Enhanced frame builder with calendar context integration.
    
    Extends the existing FrameBuilder to automatically include
    calendar context when building frames for ADHD users.
    """
    
    def __init__(self, calendar_client: CalendarClient, processor: ADHDCalendarProcessor):
        super().__init__()
        self.calendar_context_builder = CalendarContextBuilder(calendar_client, processor)
        
        # Update context weights to include calendar contexts
        self.context_weights.update({
            ContextType.CALENDAR: 0.85  # High priority for ADHD time management
        })
    
    async def build_frame(self, 
                         user_id: str, 
                         agent_id: str,
                         task_focus: Optional[str] = None,
                         include_patterns: bool = True,
                         include_calendar: bool = True,
                         calendar_preferences: Optional[CalendarPreferences] = None) -> Any:
        """
        Build frame with optional calendar context integration.
        
        Args:
            user_id: User identifier
            agent_id: Agent identifier
            task_focus: Optional task focus
            include_patterns: Include behavioral patterns
            include_calendar: Include calendar context
            calendar_preferences: User's calendar preferences
        """
        # Build base frame using parent method
        contextual_frame = await super().build_frame(user_id, agent_id, task_focus, include_patterns)
        
        # Add calendar context if requested
        if include_calendar:
            try:
                await self.calendar_context_builder.add_calendar_context(
                    contextual_frame.frame,
                    user_id,
                    preferences=calendar_preferences
                )
                
                # Recalculate cognitive load with calendar context
                contextual_frame.cognitive_load = self._calculate_cognitive_load(contextual_frame.frame)
                contextual_frame.accessibility_score = self._calculate_accessibility_score(contextual_frame.frame)
                
            except Exception as e:
                logger.error("Failed to add calendar context to frame", 
                           user_id=user_id, 
                           error=str(e))
        
        return contextual_frame