"""
ADHD-specific calendar event processor.

This module provides advanced analysis and processing of calendar events
specifically designed for ADHD executive function support:
- Schedule density analysis and overwhelm detection
- Energy level matching and optimization
- Transition difficulty assessment
- Time estimation and buffer recommendations
- Pattern recognition for personalization
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import statistics
from collections import defaultdict

import structlog

from .models import (
    CalendarEvent, CalendarInsight, TransitionAlert, ScheduleOptimizationSuggestion,
    EventType, EnergyLevel, AlertType, TransitionType, CalendarPreferences
)

logger = structlog.get_logger()


class ADHDCalendarProcessor:
    """
    Advanced processor for ADHD-optimized calendar management.
    
    This processor analyzes calendar events to:
    - Detect potential overwhelm situations
    - Recommend optimal scheduling patterns
    - Generate proactive transition alerts
    - Provide executive function support
    """
    
    def __init__(self):
        # Overwhelm detection thresholds
        self.max_daily_events_default = 8
        self.max_continuous_meeting_minutes = 120
        self.min_break_between_meetings = 15
        
        # Energy management parameters
        self.energy_peak_hours = [9, 10, 11]  # Default peak hours
        self.energy_low_hours = [13, 14, 15]  # Default low energy hours
        
        # Transition difficulty weights
        self.transition_weights = {
            (TransitionType.PHYSICAL, EventType.MEETING, EventType.MEETING): 0.3,
            (TransitionType.MENTAL, EventType.FOCUS_BLOCK, EventType.MEETING): 0.8,
            (TransitionType.ENERGY, EventType.EXERCISE, EventType.FOCUS_BLOCK): 0.6,
            (TransitionType.SOCIAL, EventType.SOCIAL, EventType.FOCUS_BLOCK): 0.7,
        }
    
    def analyze_schedule(self, 
                        events: List[CalendarEvent], 
                        user_id: str,
                        preferences: Optional[CalendarPreferences] = None) -> CalendarInsight:
        """
        Perform comprehensive ADHD-focused schedule analysis.
        
        Args:
            events: List of calendar events to analyze
            user_id: User identifier
            preferences: User's calendar preferences
            
        Returns:
            CalendarInsight with analysis results and recommendations
        """
        if not events:
            return self._create_empty_insight(user_id)
        
        # Sort events by start time
        events.sort(key=lambda e: e.start_time)
        
        # Determine analysis period
        analysis_start = events[0].start_time
        analysis_end = events[-1].end_time
        
        logger.info("Analyzing schedule", 
                   user_id=user_id, 
                   event_count=len(events),
                   period_days=(analysis_end - analysis_start).days)
        
        # Create insight object
        insight = CalendarInsight(
            user_id=user_id,
            analysis_start=analysis_start,
            analysis_end=analysis_end,
            total_events=len(events)
        )
        
        # Perform different types of analysis
        self._analyze_schedule_density(events, insight, preferences)
        self._analyze_overwhelm_indicators(events, insight, preferences)
        self._analyze_energy_management(events, insight, preferences)
        self._analyze_transitions(events, insight)
        self._generate_recommendations(insight, preferences)
        
        logger.info("Schedule analysis completed", 
                   user_id=user_id,
                   overwhelm_score=insight.overwhelm_score,
                   recommendations=len(insight.recommendations))
        
        return insight
    
    def _analyze_schedule_density(self, 
                                 events: List[CalendarEvent], 
                                 insight: CalendarInsight,
                                 preferences: Optional[CalendarPreferences]) -> None:
        """Analyze schedule density and time commitments."""
        total_hours = sum(event.duration_minutes for event in events) / 60.0
        analysis_days = max(1, (insight.analysis_end - insight.analysis_start).days)
        
        insight.total_committed_hours = total_hours
        insight.average_daily_events = len(events) / max(1, analysis_days)
        
        # Find busiest day
        daily_events = defaultdict(int)
        for event in events:
            day_key = event.start_time.strftime('%Y-%m-%d')
            daily_events[day_key] += 1
        
        if daily_events:
            busiest_day = max(daily_events.items(), key=lambda x: x[1])
            insight.busiest_day = busiest_day[0]
        
        # Find longest continuous block
        insight.longest_continuous_block = self._find_longest_continuous_block(events)
    
    def _analyze_overwhelm_indicators(self, 
                                    events: List[CalendarEvent], 
                                    insight: CalendarInsight,
                                    preferences: Optional[CalendarPreferences]) -> None:
        """Detect indicators of potential overwhelm."""
        max_daily_events = (preferences.max_daily_events if preferences 
                           else self.max_daily_events_default)
        min_break = (preferences.min_break_between_meetings if preferences 
                    else self.min_break_between_meetings)
        
        # Group events by day
        daily_events = defaultdict(list)
        for event in events:
            day_key = event.start_time.strftime('%Y-%m-%d')
            daily_events[day_key].append(event)
        
        overwhelm_factors = []
        
        for day, day_events in daily_events.items():
            day_events.sort(key=lambda e: e.start_time)
            
            # Check for too many events in a day
            if len(day_events) > max_daily_events:
                overwhelm_factors.append(2.0)  # High impact
                insight.high_density_periods.append({
                    'date': day,
                    'event_count': len(day_events),
                    'reason': f'More than {max_daily_events} events in one day'
                })
            
            # Check for insufficient breaks between meetings
            for i in range(len(day_events) - 1):
                current_event = day_events[i]
                next_event = day_events[i + 1]
                
                gap_minutes = (next_event.start_time - current_event.end_time).total_seconds() / 60
                
                if gap_minutes < min_break:
                    overwhelm_factors.append(1.0)
                    if gap_minutes <= 0:
                        insight.back_to_back_meetings += 1
                    
                    insight.insufficient_breaks.append({
                        'event1': current_event.title,
                        'event2': next_event.title,
                        'gap_minutes': int(gap_minutes),
                        'date': day
                    })
            
            # Check for continuous meeting blocks
            continuous_time = 0
            for i, event in enumerate(day_events):
                if event.event_type in [EventType.MEETING, EventType.APPOINTMENT]:
                    continuous_time += event.duration_minutes
                    
                    # Check if next event continues the block
                    if i < len(day_events) - 1:
                        next_event = day_events[i + 1]
                        gap_minutes = (next_event.start_time - event.end_time).total_seconds() / 60
                        if gap_minutes > min_break or next_event.event_type not in [EventType.MEETING, EventType.APPOINTMENT]:
                            # Block ended
                            if continuous_time > self.max_continuous_meeting_minutes:
                                overwhelm_factors.append(1.5)
                            continuous_time = 0
                else:
                    continuous_time = 0
        
        # Calculate overall overwhelm score
        if overwhelm_factors:
            base_score = min(sum(overwhelm_factors) / len(daily_events), 8.0)
            # Add bonus for event density
            density_bonus = min(insight.average_daily_events / max_daily_events * 2, 2.0)
            insight.overwhelm_score = min(base_score + density_bonus, 10.0)
        else:
            insight.overwhelm_score = max(insight.average_daily_events / max_daily_events * 3, 0.0)
    
    def _analyze_energy_management(self, 
                                 events: List[CalendarEvent], 
                                 insight: CalendarInsight,
                                 preferences: Optional[CalendarPreferences]) -> None:
        """Analyze energy level mismatches and requirements."""
        peak_hours = (preferences.peak_energy_hours if preferences 
                     else self.energy_peak_hours)
        low_hours = (preferences.low_energy_hours if preferences 
                    else self.energy_low_hours)
        
        for event in events:
            event_hour = event.start_time.hour
            
            # Check for energy mismatches
            if (event.energy_required in [EnergyLevel.HIGH, EnergyLevel.VERY_HIGH] 
                and event_hour in low_hours):
                insight.energy_mismatches.append({
                    'event': event.title,
                    'time': event.start_time.strftime('%H:%M'),
                    'date': event.start_time.strftime('%Y-%m-%d'),
                    'required_energy': event.energy_required.name,
                    'time_slot_energy': 'LOW',
                    'mismatch_severity': 'HIGH'
                })
            
            elif (event.energy_required == EnergyLevel.VERY_LOW 
                  and event_hour in peak_hours):
                insight.energy_mismatches.append({
                    'event': event.title,
                    'time': event.start_time.strftime('%H:%M'),
                    'date': event.start_time.strftime('%Y-%m-%d'),
                    'required_energy': event.energy_required.name,
                    'time_slot_energy': 'PEAK',
                    'mismatch_severity': 'MEDIUM'
                })
        
        # Recommend optimal energy blocks
        for hour in peak_hours:
            insight.recommended_energy_blocks.append({
                'time': f'{hour:02d}:00-{hour+1:02d}:00',
                'energy_level': 'PEAK',
                'recommended_activities': ['Deep work', 'Important meetings', 'Complex tasks'],
                'avoid': ['Administrative tasks', 'Low-priority items']
            })
    
    def _analyze_transitions(self, events: List[CalendarEvent], insight: CalendarInsight) -> None:
        """Analyze transition difficulty between events."""
        for i in range(len(events) - 1):
            current_event = events[i]
            next_event = events[i + 1]
            
            transition_difficulty = self._calculate_transition_difficulty(current_event, next_event)
            
            if transition_difficulty > 0.6:  # High difficulty threshold
                insight.difficult_transitions.append({
                    'from_event': current_event.title,
                    'to_event': next_event.title,
                    'transition_time': (next_event.start_time - current_event.end_time).total_seconds() / 60,
                    'difficulty_score': transition_difficulty,
                    'difficulty_factors': self._identify_transition_factors(current_event, next_event)
                })
            
            # Check for travel time warnings
            if (next_event.location and current_event.location 
                and next_event.location != current_event.location):
                gap_minutes = (next_event.start_time - current_event.end_time).total_seconds() / 60
                if gap_minutes < next_event.travel_time_minutes:
                    insight.travel_time_warnings.append({
                        'from_location': current_event.location,
                        'to_location': next_event.location,
                        'available_time': int(gap_minutes),
                        'required_time': next_event.travel_time_minutes,
                        'shortfall': next_event.travel_time_minutes - int(gap_minutes)
                    })
    
    def _generate_recommendations(self, 
                                insight: CalendarInsight,
                                preferences: Optional[CalendarPreferences]) -> None:
        """Generate ADHD-specific scheduling recommendations."""
        recommendations = []
        
        # Overwhelm recommendations
        if insight.overwhelm_score > 7:
            recommendations.append("🚨 High overwhelm risk detected. Consider reducing daily event count or adding more buffer time.")
        elif insight.overwhelm_score > 5:
            recommendations.append("⚠️ Moderate overwhelm risk. Schedule more breaks between activities.")
        
        # Back-to-back meeting recommendations
        if insight.back_to_back_meetings > 0:
            recommendations.append(f"📅 Found {insight.back_to_back_meetings} back-to-back meetings. Add 5-10 minute buffers for better transitions.")
        
        # Energy management recommendations
        if len(insight.energy_mismatches) > 0:
            recommendations.append(f"⚡ {len(insight.energy_mismatches)} energy mismatches found. Consider rescheduling high-energy tasks to peak hours.")
        
        # Difficult transitions
        if len(insight.difficult_transitions) > 2:
            recommendations.append("🔄 Multiple difficult transitions detected. Add transition time and preparation buffers.")
        
        # Travel time warnings
        if len(insight.travel_time_warnings) > 0:
            recommendations.append("🚗 Travel time conflicts detected. Allow more time for location changes.")
        
        # Density-specific recommendations
        if insight.average_daily_events > 6:
            recommendations.append("📊 High daily event density. Consider time-blocking or batching similar activities.")
        
        # General ADHD recommendations
        if insight.total_events > 20:  # For longer analysis periods
            recommendations.extend([
                "🧠 Schedule 'focus blocks' for deep work during your peak energy hours",
                "⏰ Use visual time indicators and countdown timers for better time awareness",
                "🎯 Group similar activities together to reduce context switching"
            ])
        
        insight.recommendations = recommendations[:8]  # Limit to prevent overwhelm
    
    def generate_transition_alerts(self, 
                                  events: List[CalendarEvent], 
                                  user_id: str,
                                  current_time: datetime) -> List[TransitionAlert]:
        """Generate proactive transition alerts for upcoming events."""
        alerts = []
        upcoming_events = [
            event for event in events 
            if event.start_time > current_time 
            and event.start_time <= current_time + timedelta(hours=4)  # Next 4 hours
        ]
        
        for event in upcoming_events:
            if event.needs_transition_alert(current_time):
                alert = self._create_transition_alert(event, user_id, current_time)
                if alert:
                    alerts.append(alert)
        
        return alerts
    
    def generate_optimization_suggestions(self, 
                                        events: List[CalendarEvent],
                                        insight: CalendarInsight,
                                        user_id: str) -> List[ScheduleOptimizationSuggestion]:
        """Generate specific suggestions for schedule optimization."""
        suggestions = []
        
        # Address high overwhelm situations
        if insight.overwhelm_score > 7:
            suggestion = ScheduleOptimizationSuggestion(
                user_id=user_id,
                issue_type="overwhelm",
                severity=int(insight.overwhelm_score),
                description="Schedule density is creating overwhelm risk",
                suggestion_type="reschedule",
                suggested_action="Move 2-3 non-critical events to less busy days",
                expected_benefits=["Reduced cognitive load", "Better focus", "Less stress"],
                energy_improvement=3,
                overwhelm_reduction=4,
                implementation_difficulty=6
            )
            suggestions.append(suggestion)
        
        # Address energy mismatches
        for mismatch in insight.energy_mismatches[:3]:  # Top 3 mismatches
            suggestion = ScheduleOptimizationSuggestion(
                user_id=user_id,
                issue_type="energy_mismatch",
                severity=8 if mismatch['mismatch_severity'] == 'HIGH' else 5,
                description=f"High-energy event '{mismatch['event']}' scheduled during low-energy time",
                suggestion_type="reschedule",
                suggested_action=f"Move to peak energy hours (9-11 AM)",
                affected_events=[mismatch['event']],
                expected_benefits=["Better performance", "Reduced fatigue", "Improved focus"],
                energy_improvement=4,
                implementation_difficulty=4,
                requires_coordination=True
            )
            suggestions.append(suggestion)
        
        # Address difficult transitions
        for transition in insight.difficult_transitions[:2]:  # Top 2 difficult transitions
            suggestion = ScheduleOptimizationSuggestion(
                user_id=user_id,
                issue_type="poor_transitions",
                severity=7,
                description=f"Difficult transition from '{transition['from_event']}' to '{transition['to_event']}'",
                suggestion_type="add_buffer",
                suggested_action=f"Add 15-minute buffer between events for transition preparation",
                affected_events=[transition['from_event'], transition['to_event']],
                expected_benefits=["Smoother transitions", "Less anxiety", "Better preparation"],
                implementation_difficulty=3,
                automated_implementation=True
            )
            suggestions.append(suggestion)
        
        return suggestions[:5]  # Limit to prevent overwhelm
    
    def _create_empty_insight(self, user_id: str) -> CalendarInsight:
        """Create empty insight for when no events are provided."""
        return CalendarInsight(
            user_id=user_id,
            analysis_start=datetime.utcnow(),
            analysis_end=datetime.utcnow(),
            total_events=0,
            total_committed_hours=0.0,
            average_daily_events=0.0,
            overwhelm_score=0.0,
            recommendations=["No events found. Consider scheduling some focus blocks for productivity!"]
        )
    
    def _find_longest_continuous_block(self, events: List[CalendarEvent]) -> int:
        """Find the longest continuous block of events in minutes."""
        if not events:
            return 0
        
        max_block = 0
        current_block = 0
        
        for i, event in enumerate(events):
            current_block = event.duration_minutes
            
            # Look for consecutive events
            j = i + 1
            while j < len(events):
                gap = (events[j].start_time - events[j-1].end_time).total_seconds() / 60
                if gap <= self.min_break_between_meetings:  # Continuous block
                    current_block += events[j].duration_minutes
                    j += 1
                else:
                    break
            
            max_block = max(max_block, current_block)
        
        return max_block
    
    def _calculate_transition_difficulty(self, 
                                       from_event: CalendarEvent, 
                                       to_event: CalendarEvent) -> float:
        """Calculate difficulty score for transitioning between two events."""
        difficulty_factors = []
        
        # Location change difficulty
        if from_event.location and to_event.location:
            if from_event.location != to_event.location:
                difficulty_factors.append(0.3)  # Physical transition required
        
        # Energy level change difficulty
        energy_diff = abs(from_event.energy_required.value - to_event.energy_required.value)
        difficulty_factors.append(energy_diff * 0.1)
        
        # Focus level change difficulty
        focus_diff = abs(from_event.focus_required - to_event.focus_required)
        difficulty_factors.append(focus_diff * 0.05)
        
        # Social intensity change difficulty
        social_diff = abs(from_event.social_intensity - to_event.social_intensity)
        difficulty_factors.append(social_diff * 0.03)
        
        # Event type transition difficulty
        type_transition = (TransitionType.MENTAL, from_event.event_type, to_event.event_type)
        if type_transition in self.transition_weights:
            difficulty_factors.append(self.transition_weights[type_transition])
        
        # Time gap factor (too little time makes it harder)
        gap_minutes = (to_event.start_time - from_event.end_time).total_seconds() / 60
        if gap_minutes < 10:
            difficulty_factors.append(0.4)
        elif gap_minutes < 5:
            difficulty_factors.append(0.6)
        
        return min(sum(difficulty_factors), 1.0)
    
    def _identify_transition_factors(self, 
                                   from_event: CalendarEvent, 
                                   to_event: CalendarEvent) -> List[str]:
        """Identify specific factors making a transition difficult."""
        factors = []
        
        if from_event.location and to_event.location and from_event.location != to_event.location:
            factors.append("Location change required")
        
        energy_diff = abs(from_event.energy_required.value - to_event.energy_required.value)
        if energy_diff >= 2:
            factors.append("Significant energy level change")
        
        focus_diff = abs(from_event.focus_required - to_event.focus_required)
        if focus_diff >= 4:
            factors.append("Major focus requirement change")
        
        gap_minutes = (to_event.start_time - from_event.end_time).total_seconds() / 60
        if gap_minutes < 5:
            factors.append("Insufficient transition time")
        
        return factors
    
    def _create_transition_alert(self, 
                               event: CalendarEvent, 
                               user_id: str,
                               current_time: datetime) -> Optional[TransitionAlert]:
        """Create a transition alert for an upcoming event."""
        effective_start = event.get_effective_start_time()
        minutes_until_prep = (effective_start - current_time).total_seconds() / 60
        
        if minutes_until_prep <= 0:
            return None  # Too late for preparation alert
        
        # Determine alert type and message
        if minutes_until_prep <= 5:
            alert_type = AlertType.TRANSITION_WARNING
            message = f"⚡ Transition time! '{event.title}' starts in {event.preparation_time_minutes + event.travel_time_minutes} minutes. Start preparing now."
        elif minutes_until_prep <= 15:
            alert_type = AlertType.PREPARATION_REMINDER
            message = f"🎯 Time to prep for '{event.title}'. You have {int(minutes_until_prep)} minutes to get ready."
        else:
            return None  # Not time for alert yet
        
        # Generate suggested actions
        suggested_actions = []
        if event.preparation_checklist:
            suggested_actions.extend(event.preparation_checklist[:3])
        
        if event.travel_time_minutes > 0:
            suggested_actions.append(f"Leave for {event.location} in {event.preparation_time_minutes} minutes")
        
        return TransitionAlert(
            user_id=user_id,
            event=event,
            alert_type=alert_type,
            transition_type=TransitionType.MENTAL,  # Default
            message=message,
            minutes_before_event=int(minutes_until_prep),
            suggested_actions=suggested_actions,
            preparation_items=event.materials_needed,
            scheduled_time=current_time
        )