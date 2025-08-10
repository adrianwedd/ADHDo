"""
FastAPI routes for Google Calendar integration with ADHD time management features.

This module provides REST API endpoints for:
- Google Calendar OAuth authentication
- Calendar event management (CRUD operations)
- ADHD-specific calendar insights and analysis
- Transition alerts and time management support
- Schedule optimization recommendations
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
import structlog

from mcp_server.auth import get_current_user
from mcp_server.config import settings
from mcp_server.models import User
from calendar_integration.client import CalendarClient, GoogleCalendarAuthError, GoogleCalendarAPIError
from calendar_integration.models import (
    CalendarEvent, CalendarInsight, CalendarPreferences, 
    ScheduleOptimizationSuggestion, TransitionAlert
)
from calendar_integration.processor import ADHDCalendarProcessor
from calendar_integration.nudges import calendar_nudger
from calendar_integration.context import CalendarContextBuilder

logger = structlog.get_logger()

# Initialize calendar system components
calendar_client = CalendarClient()
calendar_processor = ADHDCalendarProcessor()
calendar_context_builder = CalendarContextBuilder(calendar_client, calendar_processor)

# Create router
router = APIRouter(prefix="/api/calendar", tags=["Calendar"])

# Add calendar setup page route
from fastapi.responses import FileResponse

@router.get("/setup", include_in_schema=False)
async def calendar_setup_page():
    """Serve the calendar setup page for users."""
    try:
        return FileResponse(
            path="static/calendar-setup.html",
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache"
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Calendar setup page not found")


# Request/Response Models
class CalendarAuthRequest(BaseModel):
    """Request model for calendar authentication."""
    redirect_uri: str = Field(..., description="OAuth redirect URI")


class CalendarAuthResponse(BaseModel):
    """Response model for calendar authentication."""
    authorization_url: str = Field(..., description="URL for Google OAuth authorization")
    state: str = Field(..., description="State parameter for OAuth flow")


class CalendarTokenRequest(BaseModel):
    """Request model for OAuth token exchange."""
    authorization_code: str = Field(..., description="Authorization code from Google")
    state: str = Field(..., description="State parameter from OAuth flow")
    redirect_uri: str = Field(..., description="Original redirect URI")


class CalendarTokenResponse(BaseModel):
    """Response model for OAuth token exchange."""
    success: bool = Field(..., description="Whether token exchange was successful")
    message: str = Field(..., description="Success or error message")


class EventCreateRequest(BaseModel):
    """Request model for creating calendar events."""
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    location: Optional[str] = Field(None, description="Event location")
    attendees: List[str] = Field(default_factory=list, description="Attendee email addresses")
    preparation_time_minutes: int = Field(default=15, description="Preparation time in minutes")
    travel_time_minutes: int = Field(default=0, description="Travel time in minutes")
    custom_alerts: List[int] = Field(default_factory=lambda: [15, 5], description="Alert times in minutes")


class EventUpdateRequest(BaseModel):
    """Request model for updating calendar events."""
    title: Optional[str] = Field(None, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    start_time: Optional[datetime] = Field(None, description="Event start time")
    end_time: Optional[datetime] = Field(None, description="Event end time")
    location: Optional[str] = Field(None, description="Event location")
    preparation_time_minutes: Optional[int] = Field(None, description="Preparation time in minutes")
    travel_time_minutes: Optional[int] = Field(None, description="Travel time in minutes")


class CalendarInsightsRequest(BaseModel):
    """Request model for calendar insights analysis."""
    days_ahead: int = Field(default=7, ge=1, le=30, description="Number of days to analyze")
    include_optimization_suggestions: bool = Field(default=True, description="Include optimization suggestions")


class NudgeConfigRequest(BaseModel):
    """Request model for configuring calendar-based nudges."""
    enabled: bool = Field(..., description="Enable calendar nudges")
    default_alert_times: List[int] = Field(..., description="Default alert times in minutes")
    transition_alerts: bool = Field(default=True, description="Enable transition alerts")
    preparation_reminders: bool = Field(default=True, description="Enable preparation reminders")
    overwhelm_warnings: bool = Field(default=True, description="Enable overwhelm warnings")


# Authentication Endpoints
@router.post("/connect", response_model=CalendarAuthResponse)
async def initiate_calendar_connection(
    request: CalendarAuthRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Initiate Google Calendar OAuth connection.
    
    Returns authorization URL for user to visit and grant calendar access.
    """
    try:
        authorization_url = calendar_client.get_authorization_url(
            current_user.user_id,
            request.redirect_uri
        )
        
        logger.info("Generated calendar authorization URL", 
                   user_id=current_user.user_id)
        
        return CalendarAuthResponse(
            authorization_url=authorization_url,
            state=f"user:{current_user.user_id}"
        )
        
    except GoogleCalendarAuthError as e:
        logger.error("Calendar auth error", user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error in calendar connection", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to initiate calendar connection")


@router.post("/callback", response_model=CalendarTokenResponse)
async def handle_calendar_callback(
    request: CalendarTokenRequest,
    background_tasks: BackgroundTasks
):
    """
    Handle Google Calendar OAuth callback and exchange code for tokens.
    
    This endpoint is called by Google after user grants calendar access.
    """
    try:
        user_id, credentials_dict = calendar_client.exchange_code_for_credentials(
            request.authorization_code,
            request.redirect_uri,
            request.state
        )
        
        # Store credentials securely (in production, encrypt and store in database)
        # For now, we'll just load them into the client
        calendar_client.load_user_credentials(credentials_dict)
        
        # Start background calendar monitoring
        background_tasks.add_task(
            _start_calendar_monitoring,
            user_id
        )
        
        logger.info("Calendar connection successful", user_id=user_id)
        
        return CalendarTokenResponse(
            success=True,
            message="Calendar connected successfully! ADHD time management features are now active."
        )
        
    except GoogleCalendarAuthError as e:
        logger.error("Calendar callback auth error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error in calendar callback", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to complete calendar connection")


@router.delete("/disconnect")
async def disconnect_calendar(current_user: User = Depends(get_current_user)):
    """Disconnect Google Calendar integration."""
    try:
        # Stop calendar monitoring
        await calendar_nudger.stop_event_monitoring(current_user.user_id)
        
        # In production, remove stored credentials from database
        
        logger.info("Calendar disconnected", user_id=current_user.user_id)
        
        return {"success": True, "message": "Calendar disconnected successfully"}
        
    except Exception as e:
        logger.error("Error disconnecting calendar", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to disconnect calendar")


# Event Management Endpoints
@router.get("/events", response_model=List[CalendarEvent])
async def get_calendar_events(
    days_ahead: int = Query(default=7, ge=1, le=30, description="Days to fetch ahead"),
    calendar_id: str = Query(default="primary", description="Google Calendar ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get calendar events with ADHD-specific enrichment.
    
    Returns calendar events enhanced with preparation time, energy requirements,
    and transition analysis.
    """
    try:
        time_min = datetime.utcnow()
        time_max = time_min + timedelta(days=days_ahead)
        
        events = calendar_client.get_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max
        )
        
        # Set user_id for all events
        for event in events:
            event.user_id = current_user.user_id
        
        logger.info("Retrieved calendar events", 
                   user_id=current_user.user_id, 
                   event_count=len(events))
        
        return events
        
    except GoogleCalendarAPIError as e:
        logger.error("Calendar API error", user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving events", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve calendar events")


@router.post("/events", response_model=CalendarEvent)
async def create_calendar_event(
    request: EventCreateRequest,
    calendar_id: str = Query(default="primary", description="Google Calendar ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new calendar event with ADHD-optimized features.
    
    Automatically calculates preparation time, travel buffers, and generates
    preparation checklists based on event type.
    """
    try:
        # Create CalendarEvent from request
        event = CalendarEvent(
            title=request.title,
            description=request.description,
            start_time=request.start_time,
            end_time=request.end_time,
            location=request.location,
            attendees=request.attendees,
            preparation_time_minutes=request.preparation_time_minutes,
            travel_time_minutes=request.travel_time_minutes,
            custom_alerts=request.custom_alerts,
            user_id=current_user.user_id
        )
        
        # Calculate duration and perform ADHD analysis
        event.calculate_duration()
        
        # Create the event in Google Calendar
        created_event = calendar_client.create_event(event, calendar_id)
        
        logger.info("Created calendar event", 
                   user_id=current_user.user_id,
                   event_id=created_event.event_id,
                   title=created_event.title)
        
        return created_event
        
    except GoogleCalendarAPIError as e:
        logger.error("Calendar API error creating event", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating event", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create calendar event")


@router.put("/events/{event_id}", response_model=CalendarEvent)
async def update_calendar_event(
    event_id: str,
    request: EventUpdateRequest,
    calendar_id: str = Query(default="primary", description="Google Calendar ID"),
    current_user: User = Depends(get_current_user)
):
    """Update an existing calendar event."""
    try:
        # First, get the existing event
        events = calendar_client.get_events(calendar_id=calendar_id)
        existing_event = next((e for e in events if e.google_event_id == event_id), None)
        
        if not existing_event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Update fields that were provided
        if request.title is not None:
            existing_event.title = request.title
        if request.description is not None:
            existing_event.description = request.description
        if request.start_time is not None:
            existing_event.start_time = request.start_time
        if request.end_time is not None:
            existing_event.end_time = request.end_time
        if request.location is not None:
            existing_event.location = request.location
        if request.preparation_time_minutes is not None:
            existing_event.preparation_time_minutes = request.preparation_time_minutes
        if request.travel_time_minutes is not None:
            existing_event.travel_time_minutes = request.travel_time_minutes
        
        # Recalculate duration and update timestamps
        existing_event.calculate_duration()
        existing_event.updated_at = datetime.utcnow()
        
        # Update the event in Google Calendar
        updated_event = calendar_client.update_event(existing_event, calendar_id)
        
        logger.info("Updated calendar event", 
                   user_id=current_user.user_id,
                   event_id=event_id,
                   title=updated_event.title)
        
        return updated_event
        
    except GoogleCalendarAPIError as e:
        logger.error("Calendar API error updating event", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error updating event", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update calendar event")


@router.delete("/events/{event_id}")
async def delete_calendar_event(
    event_id: str,
    calendar_id: str = Query(default="primary", description="Google Calendar ID"),
    current_user: User = Depends(get_current_user)
):
    """Delete a calendar event."""
    try:
        success = calendar_client.delete_event(event_id, calendar_id)
        
        if success:
            logger.info("Deleted calendar event", 
                       user_id=current_user.user_id, 
                       event_id=event_id)
            return {"success": True, "message": "Event deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Event not found or already deleted")
            
    except GoogleCalendarAPIError as e:
        logger.error("Calendar API error deleting event", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error deleting event", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete calendar event")


# ADHD Insights and Analysis Endpoints
@router.post("/insights", response_model=CalendarInsight)
async def get_calendar_insights(
    request: CalendarInsightsRequest,
    calendar_id: str = Query(default="primary", description="Google Calendar ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get ADHD-specific calendar insights and analysis.
    
    Provides overwhelm detection, energy management analysis, and
    scheduling optimization recommendations.
    """
    try:
        # Get calendar events for analysis period
        time_min = datetime.utcnow()
        time_max = time_min + timedelta(days=request.days_ahead)
        
        events = calendar_client.get_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max
        )
        
        # Set user_id for all events
        for event in events:
            event.user_id = current_user.user_id
        
        # Perform ADHD-specific analysis
        insight = calendar_processor.analyze_schedule(
            events, 
            current_user.user_id
        )
        
        logger.info("Generated calendar insights", 
                   user_id=current_user.user_id,
                   overwhelm_score=insight.overwhelm_score,
                   recommendation_count=len(insight.recommendations))
        
        return insight
        
    except Exception as e:
        logger.error("Error generating calendar insights", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate calendar insights")


@router.get("/optimization-suggestions", response_model=List[ScheduleOptimizationSuggestion])
async def get_optimization_suggestions(
    days_ahead: int = Query(default=7, ge=1, le=14, description="Days to analyze"),
    calendar_id: str = Query(default="primary", description="Google Calendar ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get schedule optimization suggestions for ADHD time management.
    
    Provides actionable recommendations for reducing overwhelm,
    improving energy management, and optimizing transitions.
    """
    try:
        # Get calendar events
        time_min = datetime.utcnow()
        time_max = time_min + timedelta(days=days_ahead)
        
        events = calendar_client.get_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max
        )
        
        # Set user_id for all events
        for event in events:
            event.user_id = current_user.user_id
        
        # Analyze schedule
        insight = calendar_processor.analyze_schedule(events, current_user.user_id)
        
        # Generate optimization suggestions
        suggestions = calendar_processor.generate_optimization_suggestions(
            events, insight, current_user.user_id
        )
        
        logger.info("Generated optimization suggestions", 
                   user_id=current_user.user_id,
                   suggestion_count=len(suggestions))
        
        return suggestions
        
    except Exception as e:
        logger.error("Error generating optimization suggestions", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate optimization suggestions")


# Nudge Configuration Endpoints
@router.post("/nudges/configure")
async def configure_calendar_nudges(
    request: NudgeConfigRequest,
    current_user: User = Depends(get_current_user)
):
    """Configure calendar-based nudge settings."""
    try:
        # In production, this would update user preferences in database
        preferences = CalendarPreferences(
            user_id=current_user.user_id,
            default_alert_times=request.default_alert_times,
            transition_alert_enabled=request.transition_alerts,
            preparation_reminders=request.preparation_reminders
        )
        
        # If nudges are enabled, start monitoring
        if request.enabled:
            # Get upcoming events
            events = calendar_client.get_events(
                time_min=datetime.utcnow(),
                time_max=datetime.utcnow() + timedelta(days=7)
            )
            
            # Set user_id for all events
            for event in events:
                event.user_id = current_user.user_id
            
            # Start monitoring
            await calendar_nudger.start_event_monitoring(
                current_user, events, preferences
            )
        else:
            # Stop monitoring
            await calendar_nudger.stop_event_monitoring(current_user.user_id)
        
        logger.info("Updated calendar nudge configuration", 
                   user_id=current_user.user_id, 
                   enabled=request.enabled)
        
        return {
            "success": True, 
            "message": f"Calendar nudges {'enabled' if request.enabled else 'disabled'} successfully"
        }
        
    except Exception as e:
        logger.error("Error configuring calendar nudges", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to configure calendar nudges")


@router.post("/nudges/manual")
async def trigger_manual_nudge(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """Manually trigger a transition nudge for a specific event."""
    try:
        # Get the event
        events = calendar_client.get_events()
        event = next((e for e in events if e.google_event_id == event_id), None)
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        event.user_id = current_user.user_id
        current_time = datetime.utcnow()
        
        # Create transition alert
        alert = calendar_processor._create_transition_alert(
            event, current_user.user_id, current_time
        )
        
        if alert:
            success = await calendar_nudger.send_transition_alert(
                current_user, alert
            )
            
            if success:
                return {"success": True, "message": "Transition nudge sent successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to send nudge")
        else:
            return {"success": False, "message": "No nudge needed for this event at this time"}
            
    except Exception as e:
        logger.error("Error sending manual nudge", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to send manual nudge")


# Webhook Endpoints for Real-time Calendar Updates
@router.post("/webhook/notifications")
async def handle_calendar_webhook(
    request: dict,
    background_tasks: BackgroundTasks
):
    """
    Handle Google Calendar webhook notifications for real-time updates.
    
    This endpoint receives notifications when calendar events are created,
    updated, or deleted, allowing for immediate ADHD support adjustments.
    """
    try:
        # Extract notification details
        channel_id = request.get('channelId')
        resource_id = request.get('resourceId') 
        resource_uri = request.get('resourceUri')
        
        if not channel_id or not resource_id:
            raise HTTPException(status_code=400, detail="Missing required webhook parameters")
        
        logger.info("Received calendar webhook notification", 
                   channel_id=channel_id,
                   resource_id=resource_id)
        
        # Process the webhook in background to avoid blocking
        background_tasks.add_task(
            _process_calendar_webhook,
            channel_id,
            resource_id,
            resource_uri
        )
        
        # Return 200 OK to acknowledge webhook
        return {"status": "received", "processed": True}
        
    except Exception as e:
        logger.error("Error handling calendar webhook", error=str(e))
        # Still return 200 to avoid Google retry storms
        return {"status": "error", "message": str(e)}


@router.post("/webhook/setup")
async def setup_calendar_webhook(
    calendar_id: str = Query(default="primary", description="Calendar ID to watch"),
    current_user: User = Depends(get_current_user)
):
    """
    Set up webhook notifications for calendar changes.
    
    Registers a webhook channel with Google Calendar to receive
    real-time notifications about calendar events.
    """
    try:
        # Generate unique channel ID
        channel_id = f"adhd-calendar-{current_user.user_id}-{uuid4().hex[:8]}"
        
        # Set up Google Calendar watch request
        watch_request = {
            'id': channel_id,
            'type': 'web_hook',
            'address': f"{settings.google_calendar_redirect_uri.replace('/callback', '/webhook/notifications')}",
            'token': current_user.user_id  # Include user ID for identification
        }
        
        # In production, this would call Google Calendar API to set up the watch
        # For now, we'll simulate the setup
        logger.info("Set up calendar webhook", 
                   user_id=current_user.user_id,
                   channel_id=channel_id,
                   calendar_id=calendar_id)
        
        return {
            "success": True,
            "channel_id": channel_id,
            "message": "Calendar webhook notifications enabled for real-time ADHD support"
        }
        
    except Exception as e:
        logger.error("Error setting up calendar webhook", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to set up calendar webhook")


@router.delete("/webhook/{channel_id}")
async def stop_calendar_webhook(
    channel_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stop calendar webhook notifications."""
    try:
        # In production, this would call Google Calendar API to stop the watch
        logger.info("Stopped calendar webhook", 
                   user_id=current_user.user_id,
                   channel_id=channel_id)
        
        return {
            "success": True,
            "message": "Calendar webhook notifications stopped"
        }
        
    except Exception as e:
        logger.error("Error stopping calendar webhook", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to stop calendar webhook")


# Utility Functions
async def _start_calendar_monitoring(user_id: str) -> None:
    """Start calendar monitoring for a user (background task)."""
    try:
        # Get user object (in production, fetch from database)
        user = User(user_id=user_id, name="Unknown")  # Placeholder
        
        # Get upcoming events
        events = calendar_client.get_events(
            time_min=datetime.utcnow(),
            time_max=datetime.utcnow() + timedelta(days=7)
        )
        
        # Set user_id for all events
        for event in events:
            event.user_id = user_id
        
        # Start monitoring with default preferences
        preferences = CalendarPreferences(user_id=user_id)
        await calendar_nudger.start_event_monitoring(user, events, preferences)
        
        logger.info("Started calendar monitoring", user_id=user_id)
        
    except Exception as e:
        logger.error("Failed to start calendar monitoring", 
                    user_id=user_id, error=str(e))


async def _process_calendar_webhook(channel_id: str, resource_id: str, resource_uri: Optional[str]) -> None:
    """Process calendar webhook notification in background."""
    try:
        logger.info("Processing calendar webhook", 
                   channel_id=channel_id,
                   resource_id=resource_id)
        
        # Extract user_id from channel_id or webhook token
        # Format: adhd-calendar-{user_id}-{random}
        if channel_id.startswith("adhd-calendar-"):
            parts = channel_id.split("-")
            if len(parts) >= 3:
                user_id = parts[2]
            else:
                logger.warning("Invalid channel ID format", channel_id=channel_id)
                return
        else:
            logger.warning("Unknown channel ID format", channel_id=channel_id) 
            return
        
        # Get updated calendar events
        try:
            events = calendar_client.get_events(
                time_min=datetime.utcnow(),
                time_max=datetime.utcnow() + timedelta(days=7)
            )
            
            # Set user_id for all events
            for event in events:
                event.user_id = user_id
            
            # Update calendar monitoring with new events
            user = User(user_id=user_id, name="Unknown")  # Placeholder
            preferences = CalendarPreferences(user_id=user_id)
            
            # Stop existing monitoring
            await calendar_nudger.stop_event_monitoring(user_id)
            
            # Start monitoring with updated events
            await calendar_nudger.start_event_monitoring(user, events, preferences)
            
            # Check for immediate transition alerts
            current_time = datetime.utcnow()
            alerts = calendar_processor.generate_transition_alerts(events, user_id, current_time)
            
            # Send any urgent alerts
            for alert in alerts:
                if alert.minutes_before_event <= 15:  # Urgent alerts only
                    await calendar_nudger.send_transition_alert(user, alert)
            
            logger.info("Updated calendar monitoring from webhook", 
                       user_id=user_id, 
                       event_count=len(events),
                       urgent_alerts=len([a for a in alerts if a.minutes_before_event <= 15]))
            
        except Exception as e:
            logger.error("Error updating calendar monitoring from webhook",
                        user_id=user_id, error=str(e))
        
    except Exception as e:
        logger.error("Error processing calendar webhook", 
                    channel_id=channel_id, error=str(e))