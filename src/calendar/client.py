"""
Google Calendar API client with ADHD-optimized features.

This module provides secure Google Calendar integration with:
- OAuth 2.0 authentication flow
- Event CRUD operations
- Real-time change detection via webhooks
- ADHD-specific event processing and analysis
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode

import httpx
import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from mcp_server.config import settings
from .models import CalendarEvent, EventType, EnergyLevel

logger = structlog.get_logger()


class GoogleCalendarAuthError(Exception):
    """Raised when Google Calendar authentication fails."""
    pass


class GoogleCalendarAPIError(Exception):
    """Raised when Google Calendar API operations fail."""
    pass


class CalendarClient:
    """
    Google Calendar API client optimized for ADHD users.
    
    Features:
    - Secure OAuth 2.0 authentication
    - Batch operations for efficiency
    - Error handling and retry logic
    - ADHD-specific event enrichment
    - Webhook support for real-time updates
    """
    
    # OAuth 2.0 scopes required for full calendar access
    SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events',
        'https://www.googleapis.com/auth/calendar.events.readonly'
    ]
    
    def __init__(self):
        self.credentials: Optional[Credentials] = None
        self.service = None
        self.client_config = None
        self._load_client_config()
    
    def _load_client_config(self) -> None:
        """Load Google OAuth 2.0 client configuration."""
        if settings.google_calendar_credentials_file:
            credentials_path = settings.google_calendar_credentials_file
            if os.path.exists(credentials_path):
                try:
                    with open(credentials_path, 'r') as f:
                        self.client_config = json.load(f)
                    logger.info("Loaded Google Calendar credentials file")
                except Exception as e:
                    logger.error("Failed to load Google Calendar credentials", error=str(e))
            else:
                logger.warning("Google Calendar credentials file not found", path=credentials_path)
    
    def get_authorization_url(self, user_id: str, redirect_uri: str) -> str:
        """
        Get authorization URL for OAuth 2.0 flow.
        
        Args:
            user_id: User identifier for state parameter
            redirect_uri: Where Google should redirect after authorization
            
        Returns:
            Authorization URL for user to visit
        """
        if not self.client_config:
            raise GoogleCalendarAuthError("Client configuration not loaded")
        
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.SCOPES,
                state=f"user:{user_id}"
            )
            flow.redirect_uri = redirect_uri
            
            authorization_url, _ = flow.authorization_url(
                access_type='offline',  # Request refresh token
                include_granted_scopes='true',
                prompt='consent'  # Force consent screen to get refresh token
            )
            
            logger.info("Generated authorization URL", user_id=user_id)
            return authorization_url
            
        except Exception as e:
            logger.error("Failed to generate authorization URL", error=str(e), user_id=user_id)
            raise GoogleCalendarAuthError(f"Authorization URL generation failed: {e}")
    
    def exchange_code_for_credentials(self, 
                                    authorization_code: str, 
                                    redirect_uri: str,
                                    state: str) -> Tuple[str, Dict[str, Any]]:
        """
        Exchange authorization code for credentials.
        
        Args:
            authorization_code: Code from Google OAuth callback
            redirect_uri: Original redirect URI used in flow
            state: State parameter containing user_id
            
        Returns:
            Tuple of (user_id, credentials_dict)
        """
        if not self.client_config:
            raise GoogleCalendarAuthError("Client configuration not loaded")
        
        try:
            # Extract user_id from state
            if not state.startswith("user:"):
                raise GoogleCalendarAuthError("Invalid state parameter")
            user_id = state[5:]  # Remove "user:" prefix
            
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.SCOPES,
                state=state
            )
            flow.redirect_uri = redirect_uri
            
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Convert credentials to storable format
            credentials_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
            logger.info("Successfully exchanged authorization code for credentials", user_id=user_id)
            return user_id, credentials_dict
            
        except Exception as e:
            logger.error("Failed to exchange authorization code", error=str(e))
            raise GoogleCalendarAuthError(f"Token exchange failed: {e}")
    
    def load_user_credentials(self, credentials_dict: Dict[str, Any]) -> bool:
        """
        Load user credentials and initialize API service.
        
        Args:
            credentials_dict: Stored credentials data
            
        Returns:
            True if credentials loaded successfully
        """
        try:
            # Handle expiry datetime
            expiry = None
            if credentials_dict.get('expiry'):
                expiry = datetime.fromisoformat(credentials_dict['expiry'])
            
            self.credentials = Credentials(
                token=credentials_dict['token'],
                refresh_token=credentials_dict.get('refresh_token'),
                token_uri=credentials_dict['token_uri'],
                client_id=credentials_dict['client_id'],
                client_secret=credentials_dict['client_secret'],
                scopes=credentials_dict['scopes'],
                expiry=expiry
            )
            
            # Refresh token if expired
            if self.credentials.expired and self.credentials.refresh_token:
                logger.info("Refreshing expired credentials")
                self.credentials.refresh(Request())
            
            # Build API service
            self.service = build('calendar', 'v3', credentials=self.credentials)
            logger.info("Google Calendar service initialized")
            return True
            
        except Exception as e:
            logger.error("Failed to load user credentials", error=str(e))
            return False
    
    def get_updated_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Get updated credentials after refresh.
        
        Returns:
            Updated credentials dictionary if credentials were refreshed
        """
        if not self.credentials:
            return None
        
        return {
            'token': self.credentials.token,
            'refresh_token': self.credentials.refresh_token,
            'token_uri': self.credentials.token_uri,
            'client_id': self.credentials.client_id,
            'client_secret': self.credentials.client_secret,
            'scopes': self.credentials.scopes,
            'expiry': self.credentials.expiry.isoformat() if self.credentials.expiry else None
        }
    
    def list_calendars(self) -> List[Dict[str, Any]]:
        """
        List all calendars accessible to the user.
        
        Returns:
            List of calendar dictionaries
        """
        if not self.service:
            raise GoogleCalendarAPIError("Calendar service not initialized")
        
        try:
            calendars_result = self.service.calendarList().list().execute()
            calendars = calendars_result.get('items', [])
            
            logger.info("Retrieved calendar list", count=len(calendars))
            return calendars
            
        except HttpError as e:
            logger.error("Failed to list calendars", error=str(e))
            raise GoogleCalendarAPIError(f"Calendar list failed: {e}")
    
    def get_events(self, 
                   calendar_id: str = 'primary',
                   time_min: Optional[datetime] = None,
                   time_max: Optional[datetime] = None,
                   max_results: int = 250) -> List[CalendarEvent]:
        """
        Get calendar events with ADHD-specific enrichment.
        
        Args:
            calendar_id: Calendar ID to fetch events from
            time_min: Minimum time for events (default: now)
            time_max: Maximum time for events (default: 30 days from now)
            max_results: Maximum number of events to return
            
        Returns:
            List of enriched CalendarEvent objects
        """
        if not self.service:
            raise GoogleCalendarAPIError("Calendar service not initialized")
        
        # Set default time range if not provided
        if time_min is None:
            time_min = datetime.utcnow()
        if time_max is None:
            time_max = time_min + timedelta(days=30)
        
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            google_events = events_result.get('items', [])
            
            # Convert and enrich events
            calendar_events = []
            for google_event in google_events:
                try:
                    calendar_event = self._convert_google_event(google_event)
                    calendar_events.append(calendar_event)
                except Exception as e:
                    logger.warning("Failed to convert event", event_id=google_event.get('id'), error=str(e))
            
            logger.info("Retrieved and converted events", 
                       count=len(calendar_events), 
                       calendar_id=calendar_id)
            return calendar_events
            
        except HttpError as e:
            logger.error("Failed to get events", error=str(e), calendar_id=calendar_id)
            raise GoogleCalendarAPIError(f"Event retrieval failed: {e}")
    
    def create_event(self, event: CalendarEvent, calendar_id: str = 'primary') -> CalendarEvent:
        """
        Create a new calendar event.
        
        Args:
            event: CalendarEvent to create
            calendar_id: Calendar to create event in
            
        Returns:
            Created CalendarEvent with Google event ID
        """
        if not self.service:
            raise GoogleCalendarAPIError("Calendar service not initialized")
        
        try:
            google_event_data = self._convert_to_google_event(event)
            
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=google_event_data
            ).execute()
            
            # Update the event with Google's event ID
            event.google_event_id = created_event['id']
            event.updated_at = datetime.utcnow()
            
            logger.info("Created calendar event", 
                       event_id=event.event_id,
                       google_event_id=created_event['id'])
            return event
            
        except HttpError as e:
            logger.error("Failed to create event", error=str(e), event_id=event.event_id)
            raise GoogleCalendarAPIError(f"Event creation failed: {e}")
    
    def update_event(self, event: CalendarEvent, calendar_id: str = 'primary') -> CalendarEvent:
        """
        Update an existing calendar event.
        
        Args:
            event: CalendarEvent to update
            calendar_id: Calendar containing the event
            
        Returns:
            Updated CalendarEvent
        """
        if not self.service:
            raise GoogleCalendarAPIError("Calendar service not initialized")
        
        if not event.google_event_id:
            raise GoogleCalendarAPIError("Cannot update event without Google event ID")
        
        try:
            google_event_data = self._convert_to_google_event(event)
            
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event.google_event_id,
                body=google_event_data
            ).execute()
            
            event.updated_at = datetime.utcnow()
            
            logger.info("Updated calendar event",
                       event_id=event.event_id,
                       google_event_id=event.google_event_id)
            return event
            
        except HttpError as e:
            logger.error("Failed to update event", error=str(e), 
                        event_id=event.event_id, google_event_id=event.google_event_id)
            raise GoogleCalendarAPIError(f"Event update failed: {e}")
    
    def delete_event(self, google_event_id: str, calendar_id: str = 'primary') -> bool:
        """
        Delete a calendar event.
        
        Args:
            google_event_id: Google Calendar event ID
            calendar_id: Calendar containing the event
            
        Returns:
            True if deletion was successful
        """
        if not self.service:
            raise GoogleCalendarAPIError("Calendar service not initialized")
        
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=google_event_id
            ).execute()
            
            logger.info("Deleted calendar event", google_event_id=google_event_id)
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning("Event not found for deletion", google_event_id=google_event_id)
                return True  # Already deleted
            logger.error("Failed to delete event", error=str(e), google_event_id=google_event_id)
            raise GoogleCalendarAPIError(f"Event deletion failed: {e}")
    
    def _convert_google_event(self, google_event: Dict[str, Any]) -> CalendarEvent:
        """Convert Google Calendar event to CalendarEvent."""
        # Extract basic information
        title = google_event.get('summary', 'Untitled Event')
        description = google_event.get('description', '')
        location = google_event.get('location', '')
        
        # Handle start and end times
        start = google_event.get('start', {})
        end = google_event.get('end', {})
        
        # Check if it's an all-day event
        all_day = 'date' in start
        
        if all_day:
            start_time = datetime.fromisoformat(start['date'])
            end_time = datetime.fromisoformat(end['date'])
        else:
            start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
        
        # Create CalendarEvent
        event = CalendarEvent(
            google_event_id=google_event['id'],
            title=title,
            description=description,
            location=location,
            start_time=start_time,
            end_time=end_time,
            all_day=all_day,
            user_id="",  # Will be set by caller
            attendees=[attendee.get('email', '') for attendee in google_event.get('attendees', [])]
        )
        
        # Calculate duration
        event.calculate_duration()
        
        # Enrich with ADHD-specific analysis
        self._enrich_event_with_adhd_analysis(event)
        
        return event
    
    def _convert_to_google_event(self, event: CalendarEvent) -> Dict[str, Any]:
        """Convert CalendarEvent to Google Calendar event format."""
        google_event = {
            'summary': event.title,
            'description': self._build_enhanced_description(event),
            'location': event.location or '',
            'start': {},
            'end': {}
        }
        
        if event.all_day:
            google_event['start']['date'] = event.start_time.strftime('%Y-%m-%d')
            google_event['end']['date'] = event.end_time.strftime('%Y-%m-%d')
        else:
            google_event['start']['dateTime'] = event.start_time.isoformat()
            google_event['end']['dateTime'] = event.end_time.isoformat()
        
        # Add attendees if present
        if event.attendees:
            google_event['attendees'] = [{'email': email} for email in event.attendees]
        
        return google_event
    
    def _enrich_event_with_adhd_analysis(self, event: CalendarEvent) -> None:
        """Enrich event with ADHD-specific categorization and requirements."""
        # Analyze event type from title and description
        event.event_type = self._classify_event_type(event)
        
        # Estimate energy and focus requirements
        event.energy_required = self._estimate_energy_requirement(event)
        event.focus_required = self._estimate_focus_requirement(event)
        event.social_intensity = self._estimate_social_intensity(event)
        
        # Set preparation requirements
        event.preparation_time_minutes = self._calculate_preparation_time(event)
        event.travel_time_minutes = self._estimate_travel_time(event)
        
        # Generate preparation checklist
        event.preparation_checklist = self._generate_preparation_checklist(event)
        event.materials_needed = self._identify_materials_needed(event)
    
    def _classify_event_type(self, event: CalendarEvent) -> EventType:
        """Classify event type based on title and description."""
        title_lower = event.title.lower()
        description_lower = (event.description or '').lower()
        
        # Meeting indicators
        if any(word in title_lower for word in ['meeting', 'call', 'sync', 'standup', '1:1']):
            return EventType.MEETING
        
        # Appointment indicators  
        if any(word in title_lower for word in ['appointment', 'doctor', 'dentist', 'therapy']):
            return EventType.APPOINTMENT
        
        # Focus block indicators
        if any(word in title_lower for word in ['focus', 'deep work', 'coding', 'writing']):
            return EventType.FOCUS_BLOCK
        
        # Exercise indicators
        if any(word in title_lower for word in ['gym', 'workout', 'exercise', 'run', 'yoga']):
            return EventType.EXERCISE
        
        # Social indicators
        if any(word in title_lower for word in ['lunch', 'dinner', 'coffee', 'social', 'party']):
            return EventType.SOCIAL
        
        # Travel indicators
        if any(word in title_lower for word in ['travel', 'flight', 'drive', 'commute']):
            return EventType.TRAVEL
        
        return EventType.UNKNOWN
    
    def _estimate_energy_requirement(self, event: CalendarEvent) -> EnergyLevel:
        """Estimate energy requirement based on event characteristics."""
        base_energy = EnergyLevel.MEDIUM
        
        # Duration affects energy requirement
        if event.duration_minutes > 120:  # Long events are draining
            base_energy = EnergyLevel.HIGH
        elif event.duration_minutes < 30:  # Short events are less demanding
            base_energy = EnergyLevel.LOW
        
        # Event type adjustments
        high_energy_types = {EventType.MEETING, EventType.FOCUS_BLOCK, EventType.EXERCISE}
        low_energy_types = {EventType.BREAK, EventType.MEAL, EventType.TRAVEL}
        
        if event.event_type in high_energy_types:
            return EnergyLevel(min(base_energy + 1, EnergyLevel.VERY_HIGH))
        elif event.event_type in low_energy_types:
            return EnergyLevel(max(base_energy - 1, EnergyLevel.VERY_LOW))
        
        return base_energy
    
    def _estimate_focus_requirement(self, event: CalendarEvent) -> int:
        """Estimate focus requirement (1-10 scale)."""
        title_lower = event.title.lower()
        
        high_focus_keywords = ['focus', 'deep work', 'coding', 'analysis', 'planning', 'strategy']
        medium_focus_keywords = ['meeting', 'call', 'discussion', 'review']
        low_focus_keywords = ['break', 'lunch', 'coffee', 'social', 'exercise']
        
        if any(keyword in title_lower for keyword in high_focus_keywords):
            return min(8 + (event.duration_minutes // 60), 10)
        elif any(keyword in title_lower for keyword in medium_focus_keywords):
            return 5 + min(event.duration_minutes // 30, 3)
        elif any(keyword in title_lower for keyword in low_focus_keywords):
            return max(2, 4 - (event.duration_minutes // 60))
        
        return 5  # Default medium focus
    
    def _estimate_social_intensity(self, event: CalendarEvent) -> int:
        """Estimate social intensity (1-10 scale)."""
        attendee_count = len(event.attendees)
        
        if attendee_count == 0:  # Solo activity
            return 1
        elif attendee_count == 1:  # One-on-one
            return 4
        elif attendee_count <= 5:  # Small group
            return 6
        elif attendee_count <= 15:  # Medium group
            return 8
        else:  # Large group
            return 10
    
    def _calculate_preparation_time(self, event: CalendarEvent) -> int:
        """Calculate recommended preparation time in minutes."""
        base_prep = 15  # Default 15 minutes
        
        if event.event_type == EventType.MEETING:
            return base_prep + (5 * len(event.attendees))
        elif event.event_type == EventType.APPOINTMENT:
            return base_prep + 10
        elif event.event_type == EventType.FOCUS_BLOCK:
            return base_prep + 5
        elif event.event_type in [EventType.EXERCISE, EventType.SOCIAL]:
            return base_prep + 20
        
        return base_prep
    
    def _estimate_travel_time(self, event: CalendarEvent) -> int:
        """Estimate travel time based on location."""
        if not event.location:
            return 0
        
        location_lower = event.location.lower()
        
        # Remote meeting indicators
        if any(word in location_lower for word in ['zoom', 'teams', 'meet', 'webex', 'online']):
            return 2  # Just buffer for connection
        
        # If location is provided, assume some travel time
        return 15  # Default 15 minutes travel
    
    def _generate_preparation_checklist(self, event: CalendarEvent) -> List[str]:
        """Generate ADHD-friendly preparation checklist."""
        checklist = []
        
        # General preparation items
        checklist.append("Review event details and agenda")
        checklist.append("Check required materials and documents")
        
        # Event-type specific items
        if event.event_type == EventType.MEETING:
            checklist.extend([
                "Prepare talking points or questions",
                "Test video/audio if remote meeting",
                "Review attendee list and their roles"
            ])
        elif event.event_type == EventType.APPOINTMENT:
            checklist.extend([
                "Gather required documents or IDs",
                "Check appointment location and parking",
                "Prepare questions for the appointment"
            ])
        elif event.event_type == EventType.FOCUS_BLOCK:
            checklist.extend([
                "Clear workspace of distractions",
                "Prepare necessary tools and resources",
                "Set up focus music or environment"
            ])
        
        return checklist[:5]  # Limit to 5 items to prevent overwhelm
    
    def _identify_materials_needed(self, event: CalendarEvent) -> List[str]:
        """Identify materials likely needed for the event."""
        materials = []
        
        if event.event_type == EventType.MEETING:
            materials.extend(["Laptop/device", "Notebook", "Pen"])
        elif event.event_type == EventType.APPOINTMENT:
            materials.extend(["ID/documents", "Insurance cards"])
        elif event.event_type == EventType.EXERCISE:
            materials.extend(["Workout clothes", "Water bottle", "Towel"])
        elif event.event_type == EventType.FOCUS_BLOCK:
            materials.extend(["Laptop", "Headphones", "Coffee/water"])
        
        return materials[:3]  # Limit to prevent overwhelm
    
    def _build_enhanced_description(self, event: CalendarEvent) -> str:
        """Build enhanced description with ADHD-friendly information."""
        parts = []
        
        if event.description:
            parts.append(event.description)
            parts.append("\n" + "="*50)
        
        parts.append("🧠 ADHD OPTIMIZATION")
        parts.append(f"⚡ Energy Required: {event.energy_required.name}")
        parts.append(f"🎯 Focus Level: {event.focus_required}/10")
        parts.append(f"👥 Social Intensity: {event.social_intensity}/10")
        parts.append(f"⏰ Prep Time: {event.preparation_time_minutes} minutes")
        
        if event.preparation_checklist:
            parts.append("\n📋 PREPARATION CHECKLIST:")
            for item in event.preparation_checklist:
                parts.append(f"  • {item}")
        
        if event.materials_needed:
            parts.append("\n🎒 MATERIALS NEEDED:")
            for material in event.materials_needed:
                parts.append(f"  • {material}")
        
        return "\n".join(parts)