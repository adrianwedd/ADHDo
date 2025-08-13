#!/usr/bin/env python3
"""
Claude with actual tool access - can control music, check calendar, send nudges
This is what should have been built from the start.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple in-memory calendar for now
CALENDAR_EVENTS = []

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    success: bool
    action_taken: Optional[str] = None
    data: Optional[Dict] = None

async def get_calendar_events() -> List[Dict]:
    """Get upcoming calendar events."""
    # For now, return mock data. Later integrate with Google Calendar
    now = datetime.now()
    events = [
        {
            "title": "Bedtime",
            "time": now.replace(hour=22, minute=0).isoformat(),
            "type": "bedtime"
        },
        {
            "title": "Morning Medication", 
            "time": (now + timedelta(days=1)).replace(hour=8, minute=0).isoformat(),
            "type": "medication"
        }
    ]
    
    # Add any dynamic events
    events.extend(CALENDAR_EVENTS)
    
    # Sort by time
    events.sort(key=lambda x: x['time'])
    
    return events

async def control_music(action: str, mood: str = "focus") -> Dict:
    """Control music playback."""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            if action == "play":
                url = f"http://localhost:23444/music/{mood}"
                async with session.post(url) as resp:
                    data = await resp.json()
                    return {
                        "success": data.get("success", False),
                        "message": f"Started {mood} music" if data.get("success") else "Failed to start music"
                    }
                    
            elif action == "stop":
                url = "http://localhost:23444/music/stop"
                async with session.post(url) as resp:
                    data = await resp.json()
                    return {
                        "success": data.get("success", False),
                        "message": "Stopped music" if data.get("success") else "Failed to stop music"
                    }
                    
            elif action == "status":
                url = "http://localhost:23444/music/status"
                async with session.get(url) as resp:
                    data = await resp.json()
                    return data
                    
    except Exception as e:
        logger.error(f"Music control error: {e}")
        return {"success": False, "message": str(e)}

async def send_nudge(message: str, urgency: str = "normal") -> bool:
    """Send a nudge through Nest devices."""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"http://localhost:23444/nudge/send?message={message}&urgency={urgency}"
            async with session.post(url) as resp:
                data = await resp.json()
                return data.get("success", False)
    except Exception as e:
        logger.error(f"Nudge error: {e}")
        return False

async def add_calendar_event(title: str, time_str: str, event_type: str = "task") -> bool:
    """Add an event to the calendar."""
    try:
        # Parse time (accepts "10:30" or "2024-08-12 10:30")
        if " " in time_str:
            event_time = datetime.fromisoformat(time_str)
        else:
            # Assume today if just time given
            hour, minute = map(int, time_str.split(":"))
            event_time = datetime.now().replace(hour=hour, minute=minute, second=0)
            # If time already passed today, assume tomorrow
            if event_time < datetime.now():
                event_time += timedelta(days=1)
        
        CALENDAR_EVENTS.append({
            "title": title,
            "time": event_time.isoformat(),
            "type": event_type
        })
        
        return True
    except Exception as e:
        logger.error(f"Add calendar error: {e}")
        return False

def parse_user_intent(message: str) -> Dict:
    """Parse what the user wants to do."""
    msg_lower = message.lower()
    
    # Music commands
    if any(word in msg_lower for word in ["play music", "start music", "music on", "play focus", "play energy"]):
        mood = "energy" if "energy" in msg_lower else "focus"
        return {"action": "play_music", "mood": mood}
    
    if any(word in msg_lower for word in ["stop music", "music off", "quiet", "silence"]):
        return {"action": "stop_music"}
    
    if "music" in msg_lower and any(word in msg_lower for word in ["status", "playing", "what's playing"]):
        return {"action": "music_status"}
    
    # Calendar commands  
    if any(word in msg_lower for word in ["calendar", "schedule", "events", "what's on", "appointments"]):
        return {"action": "show_calendar"}
    
    if any(word in msg_lower for word in ["add event", "schedule", "remind me", "add reminder"]):
        return {"action": "add_event", "raw_message": message}
    
    # Nudge commands
    if any(word in msg_lower for word in ["nudge", "remind", "tell me", "announce"]):
        return {"action": "send_nudge", "message": message}
    
    # Bedtime
    if "bedtime" in msg_lower:
        if any(word in msg_lower for word in ["set", "change", "update"]):
            return {"action": "set_bedtime", "raw_message": message}
        else:
            return {"action": "bedtime_status"}
    
    # Default - just chat
    return {"action": "chat", "message": message}

@router.post("/claude/tools", response_model=ChatResponse)
async def claude_with_tools(request: ChatRequest):
    """Claude endpoint that can actually do things."""
    try:
        # Parse user intent
        intent = parse_user_intent(request.message)
        action = intent.get("action")
        
        logger.info(f"User intent: {action}")
        
        # Handle different actions
        if action == "play_music":
            result = await control_music("play", intent.get("mood", "focus"))
            return ChatResponse(
                response=result["message"],
                success=result["success"],
                action_taken=f"play_{intent.get('mood')}_music",
                data=result
            )
        
        elif action == "stop_music":
            result = await control_music("stop")
            return ChatResponse(
                response=result["message"],
                success=result["success"],
                action_taken="stop_music",
                data=result
            )
        
        elif action == "music_status":
            result = await control_music("status")
            if result.get("is_playing"):
                response = f"Music is playing: {result.get('current_track', {}).get('name', 'Unknown track')}"
            else:
                response = "No music is currently playing"
            return ChatResponse(
                response=response,
                success=True,
                action_taken="check_music_status",
                data=result
            )
        
        elif action == "show_calendar":
            events = await get_calendar_events()
            if events:
                response = "Upcoming events:\n"
                for event in events[:5]:  # Show next 5 events
                    time_obj = datetime.fromisoformat(event['time'])
                    time_str = time_obj.strftime("%I:%M %p")
                    if time_obj.date() > datetime.now().date():
                        time_str = time_obj.strftime("%b %d %I:%M %p")
                    response += f"• {time_str} - {event['title']}\n"
            else:
                response = "No upcoming events scheduled"
            
            return ChatResponse(
                response=response,
                success=True,
                action_taken="show_calendar",
                data={"events": events}
            )
        
        elif action == "add_event":
            # Simple extraction - look for time patterns
            import re
            
            msg = intent.get("raw_message", "")
            
            # Extract time (matches "10:30", "10:30am", "22:00", etc)
            time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', msg, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                am_pm = time_match.group(3)
                
                if am_pm:
                    if am_pm.lower() == 'pm' and hour < 12:
                        hour += 12
                    elif am_pm.lower() == 'am' and hour == 12:
                        hour = 0
                
                time_str = f"{hour:02d}:{minute:02d}"
                
                # Extract title (everything except the time and command words)
                title = msg
                for word in ["add event", "schedule", "remind me", "at", time_match.group(0)]:
                    title = title.replace(word, "")
                title = title.strip()
                
                if not title:
                    title = "Reminder"
                
                success = await add_calendar_event(title, time_str)
                
                if success:
                    response = f"Added '{title}' at {time_str}"
                else:
                    response = "Failed to add event"
            else:
                response = "Please specify a time (e.g., 'remind me meeting at 2:30pm')"
                success = False
            
            return ChatResponse(
                response=response,
                success=success,
                action_taken="add_calendar_event"
            )
        
        elif action == "send_nudge":
            # Extract the actual message to send
            msg = request.message.replace("nudge", "").replace("announce", "").replace("tell me", "").strip()
            success = await send_nudge(msg)
            
            return ChatResponse(
                response=f"Nudge {'sent' if success else 'failed'}: {msg}",
                success=success,
                action_taken="send_nudge"
            )
        
        elif action == "set_bedtime":
            # Extract time from message
            import re
            time_match = re.search(r'(\d{1,2}):(\d{2})', request.message)
            if time_match:
                bedtime = time_match.group(0)
                # Add bedtime event
                success = await add_calendar_event("Bedtime", bedtime, "bedtime")
                response = f"Bedtime set for {bedtime}. I'll start reminding you 15 minutes before."
            else:
                response = "Please specify a time (e.g., 'set bedtime to 10:30')"
                success = False
                
            return ChatResponse(
                response=response,
                success=success,
                action_taken="set_bedtime"
            )
        
        else:
            # Default chat response
            # In production, this would call Claude API
            # For now, return a helpful message
            response = (
                "I understand you said: " + request.message + "\n\n"
                "I can help you with:\n"
                "• Play/stop music (say 'play focus music' or 'stop music')\n"
                "• Check calendar (say 'what's on my calendar')\n"
                "• Add reminders (say 'remind me meeting at 2:30pm')\n"
                "• Send nudges (say 'nudge: time to take a break')\n"
                "• Set bedtime (say 'set bedtime to 10:30pm')"
            )
            
            return ChatResponse(
                response=response,
                success=True,
                action_taken="chat"
            )
            
    except Exception as e:
        logger.error(f"Claude tools error: {e}")
        return ChatResponse(
            response=f"Sorry, I encountered an error: {str(e)}",
            success=False
        )

# Add this router to the main app in minimal_main.py by adding:
# from mcp_server.claude_with_tools import router as claude_tools_router
# app.include_router(claude_tools_router)