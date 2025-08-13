"""
Claude Context Builder for ADHD Support System.
Builds rich, structured context for Claude to provide better ADHD-specific responses.
Now with REAL Google Calendar, Tasks, and Fitness data!
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Import Google integration
try:
    from .google_integration import get_google_integration
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    
logger = logging.getLogger(__name__)

class ClaudeContextBuilder:
    """Builds structured context for Claude to understand user's ADHD situation."""
    
    def __init__(self):
        self.context_template = {
            "timestamp": None,
            "user_state": {},
            "environment": {},
            "upcoming_events": [],
            "recent_patterns": {},
            "support_needed": {}
        }
        # Initialize Google integration if available
        self.google = get_google_integration() if GOOGLE_AVAILABLE else None
        if self.google:
            logger.info("✅ Google integration available for Claude context")
    
    def build_context(
        self,
        user_id: str,
        current_task: Optional[str] = None,
        energy_level: Optional[str] = None,
        calendar_events: Optional[List[Dict]] = None,
        music_status: Optional[Dict] = None,
        recent_interactions: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Build comprehensive context for Claude with real Google data."""
        
        # Get real Google data if available
        google_context = {}
        if self.google:
            try:
                google_context = self.google.get_adhd_context()
                logger.info("📊 Enriched context with real Google data")
            except Exception as e:
                logger.error(f"Failed to get Google context: {e}")
        
        # Use Google calendar events if available, otherwise use provided ones
        if google_context.get("calendar", {}).get("events_today"):
            calendar_events = google_context["calendar"]["events_today"]
        
        context = {
            "timestamp": datetime.now().isoformat(),
            "time_context": self._get_time_context(),
            "user_state": self._build_user_state(energy_level, current_task),
            "environment": self._build_environment(music_status),
            "upcoming_events": self._format_events(calendar_events),
            "interaction_history": self._summarize_interactions(recent_interactions),
            "adhd_considerations": self._get_adhd_considerations(),
            # Add Google-specific context
            "google_insights": {
                "next_event": google_context.get("calendar", {}).get("next_event"),
                "urgent_tasks": google_context.get("tasks", {}).get("urgent_tasks", []),
                "fitness": google_context.get("fitness", {}),
                "smart_recommendations": google_context.get("recommendations", [])
            }
        }
        
        return context
    
    def _get_time_context(self) -> Dict[str, Any]:
        """Get time-based context."""
        now = datetime.now()
        hour = now.hour
        
        return {
            "current_time": now.strftime("%H:%M"),
            "day_part": self._get_day_part(hour),
            "typical_energy": self._get_typical_energy(hour),
            "meal_timing": self._get_meal_context(hour)
        }
    
    def _get_day_part(self, hour: int) -> str:
        """Determine part of day."""
        if hour < 6:
            return "early_morning"
        elif hour < 12:
            return "morning"
        elif hour < 14:
            return "midday"
        elif hour < 17:
            return "afternoon"
        elif hour < 20:
            return "evening"
        else:
            return "night"
    
    def _get_typical_energy(self, hour: int) -> str:
        """Get typical ADHD energy patterns."""
        if hour in [10, 11, 15, 16]:
            return "typically_high"
        elif hour in [13, 14, 20, 21]:
            return "typically_low"
        else:
            return "variable"
    
    def _get_meal_context(self, hour: int) -> str:
        """Get meal-related context."""
        if 7 <= hour < 9:
            return "breakfast_time"
        elif 12 <= hour < 14:
            return "lunch_time"
        elif 18 <= hour < 20:
            return "dinner_time"
        else:
            return "between_meals"
    
    def _build_user_state(self, energy_level: Optional[str], current_task: Optional[str]) -> Dict:
        """Build user state information."""
        return {
            "energy_level": energy_level or "unknown",
            "current_task": current_task or "not_specified",
            "needs_break": self._check_break_needed(),
            "hydration_reminder": self._check_hydration()
        }
    
    def _build_environment(self, music_status: Optional[Dict]) -> Dict:
        """Build environment context."""
        env = {
            "music_playing": False,
            "music_type": None
        }
        
        if music_status:
            env["music_playing"] = music_status.get("is_playing", False)
            if env["music_playing"]:
                env["music_type"] = music_status.get("mood", "focus")
                env["current_track"] = music_status.get("current_track", {}).get("name")
        
        return env
    
    def _format_events(self, calendar_events: Optional[List[Dict]]) -> List[Dict]:
        """Format upcoming calendar events."""
        if not calendar_events:
            return []
        
        formatted = []
        now = datetime.now()
        
        for event in calendar_events[:3]:  # Limit to next 3 events
            event_time = event.get("time")
            if event_time:
                try:
                    event_dt = datetime.fromisoformat(event_time)
                    minutes_until = int((event_dt - now).total_seconds() / 60)
                    
                    formatted.append({
                        "title": event.get("title"),
                        "time": event_dt.strftime("%H:%M"),
                        "minutes_until": minutes_until,
                        "type": event.get("type", "general"),
                        "prep_needed": minutes_until < 30
                    })
                except:
                    pass
        
        return formatted
    
    def _summarize_interactions(self, recent_interactions: Optional[List[Dict]]) -> Dict:
        """Summarize recent interaction patterns."""
        if not recent_interactions:
            return {"pattern": "first_interaction"}
        
        # Analyze patterns
        topics = []
        for interaction in recent_interactions[-5:]:  # Last 5 interactions
            if "focus" in interaction.get("message", "").lower():
                topics.append("focus_issues")
            elif "task" in interaction.get("message", "").lower():
                topics.append("task_management")
            elif "time" in interaction.get("message", "").lower():
                topics.append("time_management")
        
        return {
            "recent_topics": list(set(topics)),
            "interaction_count": len(recent_interactions)
        }
    
    def _get_adhd_considerations(self) -> Dict:
        """Get ADHD-specific considerations."""
        return {
            "common_challenges": [
                "task_initiation",
                "time_blindness",
                "working_memory",
                "emotional_regulation"
            ],
            "helpful_strategies": [
                "break_into_tiny_steps",
                "use_timers",
                "external_reminders",
                "body_doubling",
                "gamification"
            ],
            "response_style": {
                "max_steps": 3,
                "be_specific": True,
                "validate_struggle": True,
                "offer_easier_alternative": True
            }
        }
    
    def _check_break_needed(self) -> bool:
        """Check if user likely needs a break."""
        # This would check actual activity logs
        # For now, suggest break every 45 minutes
        return datetime.now().minute % 45 < 5
    
    def _check_hydration(self) -> bool:
        """Check if hydration reminder needed."""
        # Every 30 minutes
        return datetime.now().minute % 30 < 2
    
    def format_prompt_with_context(self, user_message: str, context: Dict) -> str:
        """Create a structured prompt for Claude with context."""
        
        prompt = f"""You are an ADHD executive function assistant. Be specific, kind, and actionable.

CONTEXT:
- Time: {context['time_context']['current_time']} ({context['time_context']['day_part']})
- Energy: {context['user_state']['energy_level']}
- Current task: {context['user_state']['current_task']}
- Environment: {"Music playing" if context['environment']['music_playing'] else "Quiet"}

UPCOMING EVENTS:
{self._format_events_text(context['upcoming_events'])}

USER MESSAGE: {user_message}

Respond with:
1. ONE specific action they can do right now (make it tiny!)
2. Why this helps ADHD brains specifically
3. What to do if that feels too hard

Keep response under 3 sentences. Be encouraging and understanding."""
        
        return prompt
    
    def _format_events_text(self, events: List[Dict]) -> str:
        """Format events as text."""
        if not events:
            return "- No urgent events"
        
        lines = []
        for event in events:
            urgency = "⚠️" if event['minutes_until'] < 30 else "📅"
            lines.append(f"{urgency} {event['title']} in {event['minutes_until']} minutes")
        
        return "\n".join(lines)
    
    def parse_claude_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's response into actionable components."""
        
        # Try to extract action items
        lines = response.split('.')
        
        return {
            "primary_action": lines[0] if lines else response,
            "full_response": response,
            "suggested_timer": self._extract_timer(response),
            "needs_nudge": "check" in response.lower() or "remind" in response.lower()
        }
    
    def _extract_timer(self, text: str) -> Optional[int]:
        """Extract timer duration from text."""
        import re
        
        # Look for patterns like "15 minutes", "5 min", etc.
        pattern = r'(\d+)\s*(?:minutes?|mins?)'
        match = re.search(pattern, text.lower())
        
        if match:
            return int(match.group(1))
        
        return None


# Global instance
claude_context_builder = ClaudeContextBuilder()