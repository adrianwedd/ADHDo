"""
API endpoints for the integration hub - so the UI can see what's happening
"""
from fastapi import APIRouter
from typing import Dict, List, Any, Optional
from datetime import datetime

router = APIRouter(prefix="/integration", tags=["integration"])

@router.get("/status")
async def get_integration_status():
    """Get current integration hub status."""
    from mcp_server.minimal_main import hub, analyzer
    
    if not hub:
        return {"error": "Integration hub not initialized"}
    
    return {
        "running": hub.running,
        "components": list(hub.components.keys()),
        "context": hub.context,
        "queue_size": hub.event_queue.qsize()
    }

@router.get("/events/recent")
async def get_recent_events():
    """Get recent events processed by the hub."""
    from mcp_server.minimal_main import hub
    
    if not hub:
        return {"error": "Integration hub not initialized"}
    
    # Get last event from context
    last_event = hub.context.get('last_event')
    if last_event:
        return {
            "last_event": {
                "type": last_event.type.value,
                "data": last_event.data,
                "timestamp": last_event.timestamp.isoformat(),
                "source": last_event.source
            },
            "needs_movement": hub.context.get('needs_movement', False),
            "upcoming_meeting": hub.context.get('upcoming_meeting')
        }
    
    return {"message": "No events processed yet"}

@router.get("/activity")
async def get_activity_summary():
    """Get summary of system activity."""
    from mcp_server.minimal_main import hub, oauth_mgr
    
    if not hub:
        return {"error": "Integration hub not initialized"}
    
    summary = {
        "integration_active": hub.running,
        "last_activity": None,
        "current_state": {},
        "recommendations": []
    }
    
    # Get last event time
    if hub.context.get('last_event_time'):
        summary['last_activity'] = hub.context['last_event_time'].isoformat()
    
    # Get current state from components
    if oauth_mgr and oauth_mgr.is_authenticated():
        try:
            # Get fitness stats
            stats = await oauth_mgr.get_today_stats()
            summary['current_state']['steps'] = stats.get('steps', 0)
            summary['current_state']['calories'] = stats.get('calories', 0)
            
            # Get calendar
            events = await oauth_mgr.get_calendar_events(max_results=1)
            if events:
                summary['current_state']['next_event'] = events[0].get('summary', 'Unknown')
                summary['current_state']['next_event_time'] = events[0].get('start_time')
        except:
            pass
    
    # Generate recommendations based on context
    if hub.context.get('needs_movement'):
        summary['recommendations'].append("🚶 Take a movement break - low activity detected")
    
    if hub.context.get('upcoming_meeting'):
        summary['recommendations'].append("📅 Meeting coming up - prepare materials")
    
    return summary

@router.post("/trigger")
async def trigger_event(event_type: str, data: Dict[str, Any] = {}):
    """Manually trigger an event for testing."""
    from mcp_server.minimal_main import hub
    from mcp_server.integration_hub import SystemEvent, EventType
    
    if not hub:
        return {"error": "Integration hub not initialized"}
    
    # Map string to EventType
    try:
        event_enum = EventType[event_type.upper()]
    except KeyError:
        return {"error": f"Unknown event type: {event_type}"}
    
    # Emit the event
    await hub.emit(SystemEvent(
        type=event_enum,
        data=data,
        timestamp=datetime.now(),
        source="manual_trigger",
        priority=5
    ))
    
    return {"success": True, "event": event_type}