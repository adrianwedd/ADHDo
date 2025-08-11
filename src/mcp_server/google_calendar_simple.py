"""
Simple Google Calendar Integration for ADHD Context
Provides calendar awareness and event creation capabilities
"""
import os
import pickle
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Try to import Google Calendar libraries
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("Google Calendar libraries not installed. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

class SimpleCalendarClient:
    """Simple Google Calendar client for ADHD context awareness."""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self, credentials_file: str = None, token_file: str = "token.pickle"):
        self.credentials_file = credentials_file or os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "credentials.json")
        self.token_file = token_file
        self.service = None
        self.creds = None
        self.is_authenticated = False
        
        if GOOGLE_AVAILABLE:
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar."""
        try:
            # Load existing token
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
            
            # Refresh or get new token
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                elif os.path.exists(self.credentials_file):
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    self.creds = flow.run_local_server(port=0)
                else:
                    logger.warning(f"Credentials file not found: {self.credentials_file}")
                    return
                
                # Save token for next run
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.creds, token)
            
            # Build service
            self.service = build('calendar', 'v3', credentials=self.creds)
            self.is_authenticated = True
            logger.info("✅ Google Calendar authenticated successfully")
            
        except Exception as e:
            logger.error(f"❌ Google Calendar authentication failed: {e}")
            self.is_authenticated = False
    
    def get_upcoming_events(self, max_results: int = 10, time_min: datetime = None) -> List[Dict]:
        """Get upcoming calendar events."""
        if not self.is_authenticated:
            return []
        
        try:
            now = time_min or datetime.utcnow()
            
            # Get events from primary calendar
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Process events for ADHD context
            processed_events = []
            for event in events:
                processed = self._process_event_for_adhd(event)
                processed_events.append(processed)
            
            return processed_events
            
        except HttpError as error:
            logger.error(f"Calendar API error: {error}")
            return []
    
    def _process_event_for_adhd(self, event: Dict) -> Dict:
        """Process calendar event with ADHD-relevant information."""
        # Extract basic info
        summary = event.get('summary', 'Untitled Event')
        start = event.get('start', {})
        end = event.get('end', {})
        location = event.get('location', '')
        description = event.get('description', '')
        
        # Parse time
        if 'dateTime' in start:
            start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
        else:
            start_time = datetime.fromisoformat(start.get('date', ''))
        
        if 'dateTime' in end:
            end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
        else:
            end_time = datetime.fromisoformat(end.get('date', ''))
        
        # Calculate ADHD-relevant metrics
        now = datetime.now(timezone.utc)
        time_until = start_time - now
        duration = end_time - start_time
        
        # Determine urgency
        if time_until.total_seconds() < 0:
            urgency = "happening_now"
            urgency_score = 1.0
        elif time_until.total_seconds() < 900:  # 15 minutes
            urgency = "imminent"
            urgency_score = 0.9
        elif time_until.total_seconds() < 3600:  # 1 hour
            urgency = "soon"
            urgency_score = 0.7
        elif time_until.total_seconds() < 86400:  # 1 day
            urgency = "today"
            urgency_score = 0.5
        else:
            urgency = "future"
            urgency_score = 0.3
        
        # Estimate cognitive load based on event type
        cognitive_load = self._estimate_cognitive_load(summary, description, duration)
        
        # Check for ADHD keywords
        adhd_flags = self._check_adhd_flags(summary, description)
        
        return {
            "id": event.get('id'),
            "summary": summary,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "location": location,
            "description": description,
            "urgency": urgency,
            "urgency_score": urgency_score,
            "time_until_minutes": int(time_until.total_seconds() / 60),
            "duration_minutes": int(duration.total_seconds() / 60),
            "cognitive_load": cognitive_load,
            "adhd_flags": adhd_flags,
            "preparation_needed": self._estimate_prep_time(event),
            "transition_buffer": 15 if cognitive_load > 0.7 else 10  # Minutes
        }
    
    def _estimate_cognitive_load(self, summary: str, description: str, duration: timedelta) -> float:
        """Estimate cognitive load of an event."""
        load = 0.5  # Base load
        
        # Meetings are high load
        meeting_keywords = ['meeting', 'call', 'interview', 'presentation', 'review']
        if any(kw in summary.lower() for kw in meeting_keywords):
            load += 0.3
        
        # Long events are draining
        if duration.total_seconds() > 7200:  # 2+ hours
            load += 0.2
        elif duration.total_seconds() > 3600:  # 1+ hour
            load += 0.1
        
        # Complex descriptions indicate complexity
        if len(description) > 200:
            load += 0.1
        
        return min(load, 1.0)
    
    def _check_adhd_flags(self, summary: str, description: str) -> List[str]:
        """Check for ADHD-relevant keywords."""
        flags = []
        text = (summary + " " + description).lower()
        
        if any(kw in text for kw in ['deadline', 'due', 'submit']):
            flags.append("deadline")
        if any(kw in text for kw in ['important', 'critical', 'urgent']):
            flags.append("high_priority")
        if any(kw in text for kw in ['focus', 'concentrate', 'deep work']):
            flags.append("requires_focus")
        if any(kw in text for kw in ['prepare', 'bring', 'remember']):
            flags.append("needs_preparation")
        
        return flags
    
    def _estimate_prep_time(self, event: Dict) -> int:
        """Estimate preparation time needed (in minutes)."""
        summary = event.get('summary', '').lower()
        location = event.get('location', '').lower()
        
        prep_time = 5  # Base prep time
        
        # Add travel time if location is specified
        if location and location != 'online' and 'zoom' not in location:
            prep_time += 30  # Assume 30 min travel
        
        # Meetings need more prep
        if 'meeting' in summary or 'interview' in summary:
            prep_time += 15
        
        # Presentations need lots of prep
        if 'presentation' in summary:
            prep_time += 30
        
        return prep_time
    
    def create_event(self, 
                    summary: str,
                    start_time: datetime,
                    end_time: datetime,
                    description: str = "",
                    location: str = "",
                    reminders: List[int] = None) -> Optional[Dict]:
        """Create a calendar event with ADHD-optimized defaults."""
        if not self.is_authenticated:
            return None
        
        # Default ADHD-friendly reminders (in minutes)
        if reminders is None:
            reminders = [60, 15, 5]  # 1 hour, 15 min, 5 min before
        
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': m} for m in reminders
                ],
            },
        }
        
        try:
            event = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            logger.info(f"✅ Created event: {event.get('htmlLink')}")
            return event
            
        except HttpError as error:
            logger.error(f"Failed to create event: {error}")
            return None
    
    def create_task_reminder(self, task: str, when: datetime, duration_minutes: int = 30) -> Optional[Dict]:
        """Create a task reminder as a calendar event."""
        end_time = when + timedelta(minutes=duration_minutes)
        
        description = f"ADHD Task Reminder\n\nTask: {task}\n\nTips:\n- Break it into small steps\n- Set a timer\n- Remove distractions\n- Reward yourself when done!"
        
        return self.create_event(
            summary=f"📝 Task: {task}",
            start_time=when,
            end_time=end_time,
            description=description,
            reminders=[30, 10, 0]  # More aggressive reminders for tasks
        )
    
    def get_context_for_chat(self) -> Dict[str, Any]:
        """Get calendar context for the chat system."""
        if not self.is_authenticated:
            return {
                "available": False,
                "message": "Calendar not connected"
            }
        
        events = self.get_upcoming_events(max_results=5)
        
        if not events:
            return {
                "available": True,
                "next_event": None,
                "events_today": [],
                "cognitive_load_next_4h": 0.0,
                "recommended_focus_time": "now"
            }
        
        # Analyze events for context
        now = datetime.now(timezone.utc)
        today_end = now.replace(hour=23, minute=59, second=59)
        
        next_event = events[0] if events else None
        events_today = [e for e in events if datetime.fromisoformat(e['start_time']) < today_end]
        
        # Calculate cognitive load for next 4 hours
        four_hours_later = now + timedelta(hours=4)
        upcoming_events = [e for e in events if datetime.fromisoformat(e['start_time']) < four_hours_later]
        total_load = sum(e['cognitive_load'] for e in upcoming_events)
        
        # Find best focus time
        best_focus_time = self._find_focus_window(events)
        
        return {
            "available": True,
            "next_event": next_event,
            "events_today": events_today,
            "cognitive_load_next_4h": min(total_load, 1.0),
            "recommended_focus_time": best_focus_time,
            "busy_periods": self._identify_busy_periods(events),
            "preparation_alerts": self._get_prep_alerts(events)
        }
    
    def _find_focus_window(self, events: List[Dict]) -> str:
        """Find the best time for focus work."""
        if not events:
            return "now - next 2 hours"
        
        now = datetime.now(timezone.utc)
        next_event_time = datetime.fromisoformat(events[0]['start_time'])
        
        gap = next_event_time - now
        if gap.total_seconds() > 7200:  # More than 2 hours
            return "now - next 2 hours"
        elif gap.total_seconds() > 3600:  # More than 1 hour
            return "now - next hour"
        elif gap.total_seconds() > 1800:  # More than 30 min
            return "now - quick 25 min session"
        else:
            return "after your next event"
    
    def _identify_busy_periods(self, events: List[Dict]) -> List[str]:
        """Identify busy periods for cognitive load management."""
        periods = []
        for event in events[:3]:  # Check next 3 events
            if event['cognitive_load'] > 0.7:
                time_str = datetime.fromisoformat(event['start_time']).strftime('%I:%M %p')
                periods.append(f"{time_str} - {event['summary']} (high load)")
        return periods
    
    def _get_prep_alerts(self, events: List[Dict]) -> List[str]:
        """Get preparation alerts for upcoming events."""
        alerts = []
        now = datetime.now(timezone.utc)
        
        for event in events[:3]:
            if 'needs_preparation' in event['adhd_flags']:
                event_time = datetime.fromisoformat(event['start_time'])
                prep_time = event['preparation_needed']
                prep_start = event_time - timedelta(minutes=prep_time)
                
                if prep_start > now and (prep_start - now).total_seconds() < 3600:
                    alerts.append(f"Start preparing for {event['summary']} in {int((prep_start - now).total_seconds() / 60)} minutes")
        
        return alerts


# Global instance
calendar_client: Optional[SimpleCalendarClient] = None

def initialize_calendar(credentials_file: str = None) -> bool:
    """Initialize the global calendar client."""
    global calendar_client
    
    if not GOOGLE_AVAILABLE:
        logger.warning("Google Calendar libraries not available")
        return False
    
    try:
        calendar_client = SimpleCalendarClient(credentials_file=credentials_file)
        if calendar_client.is_authenticated:
            logger.info("📅 Google Calendar initialized successfully")
            return True
        else:
            logger.warning("📅 Google Calendar authentication pending")
            return False
    except Exception as e:
        logger.error(f"Failed to initialize calendar: {e}")
        return False