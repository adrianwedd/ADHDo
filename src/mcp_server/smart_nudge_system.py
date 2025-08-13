#!/usr/bin/env python3
"""
Smart Nudge System with Google API Integration
Provides context-aware nudges based on real calendar, tasks, and fitness data
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from dataclasses import dataclass

# Import our Google integration
try:
    from .google_integration import get_google_integration, GoogleEvent, GoogleTask, FitnessData
    from .nest_nudges import send_nudge_to_device, get_available_devices
    INTEGRATIONS_AVAILABLE = True
except ImportError:
    INTEGRATIONS_AVAILABLE = False

logger = logging.getLogger(__name__)

class NudgeType(Enum):
    """Types of nudges for different ADHD needs."""
    MEETING_REMINDER = "meeting"
    TASK_REMINDER = "task"
    MOVEMENT_BREAK = "movement"
    MEDICATION_REMINDER = "medication"
    FOCUS_TIME = "focus"
    BEDTIME = "bedtime"
    HYDRATION = "hydration"
    TRANSITION_WARNING = "transition"

class NudgeUrgency(Enum):
    """Urgency levels for nudges."""
    INFO = "info"        # Gentle suggestion
    REMINDER = "reminder" # Standard reminder
    URGENT = "urgent"    # Important - needs attention
    CRITICAL = "critical" # Must act now

@dataclass
class SmartNudge:
    """A context-aware nudge."""
    id: str
    type: NudgeType
    urgency: NudgeUrgency
    message: str
    context: Dict[str, Any]
    devices: List[str]  # Which devices to send to
    scheduled_time: datetime
    created_at: datetime
    
    def should_send_now(self) -> bool:
        """Check if nudge should be sent now."""
        return datetime.now() >= self.scheduled_time

class SmartNudgeSystem:
    """Intelligent nudge system using real Google data."""
    
    def __init__(self):
        self.google = get_google_integration() if INTEGRATIONS_AVAILABLE else None
        self.pending_nudges: List[SmartNudge] = []
        self.sent_nudges: List[SmartNudge] = []
        self.running = False
        
    async def start_monitoring(self):
        """Start the smart nudge monitoring loop."""
        if not self.google:
            logger.error("Google integration not available - falling back to basic nudges")
            return
            
        self.running = True
        logger.info("🧠 Smart nudge system started")
        
        while self.running:
            try:
                await self._check_and_send_nudges()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in nudge monitoring: {e}")
                await asyncio.sleep(60)
    
    def stop_monitoring(self):
        """Stop the nudge monitoring."""
        self.running = False
        logger.info("Smart nudge system stopped")
    
    async def _check_and_send_nudges(self):
        """Check conditions and generate/send appropriate nudges."""
        
        # Get fresh context from Google
        try:
            context = self.google.get_adhd_context()
        except Exception as e:
            logger.error(f"Failed to get Google context: {e}")
            return
        
        # Generate new nudges based on context
        new_nudges = []
        
        # 1. MEETING REMINDERS
        next_event = context.get("calendar", {}).get("next_event")
        if next_event:
            minutes_until = next_event.get("minutes_until", 999)
            
            # Critical: 5 minutes before
            if 3 <= minutes_until <= 5:
                new_nudges.append(self._create_meeting_nudge(
                    next_event, NudgeUrgency.CRITICAL, 
                    f"🚨 MEETING IN {minutes_until} MINUTES: {next_event['title']}"
                ))
            
            # Urgent: 15 minutes before
            elif 13 <= minutes_until <= 15:
                new_nudges.append(self._create_meeting_nudge(
                    next_event, NudgeUrgency.URGENT,
                    f"⏰ Meeting in {minutes_until} minutes: {next_event['title']} - wrap up what you're doing"
                ))
            
            # Reminder: 30 minutes before
            elif 28 <= minutes_until <= 30:
                new_nudges.append(self._create_meeting_nudge(
                    next_event, NudgeUrgency.REMINDER,
                    f"📅 Heads up: {next_event['title']} in {minutes_until} minutes"
                ))
        
        # 2. TASK REMINDERS
        urgent_tasks = context.get("tasks", {}).get("urgent_tasks", [])
        if len(urgent_tasks) > 3:
            new_nudges.append(SmartNudge(
                id=f"task_overload_{datetime.now().hour}",
                type=NudgeType.TASK_REMINDER,
                urgency=NudgeUrgency.URGENT,
                message=f"⚠️ {len(urgent_tasks)} urgent tasks detected! Pick ONE to focus on for the next 25 minutes.",
                context={"urgent_tasks": urgent_tasks},
                devices=["Nest Hub Max"],  # Use display for task list
                scheduled_time=datetime.now(),
                created_at=datetime.now()
            ))
        
        # 3. MOVEMENT BREAKS
        fitness = context.get("fitness", {})
        if fitness.get("needs_movement", False):
            last_activity = fitness.get("last_activity_minutes", 0)
            if last_activity > 90:  # Haven't moved in 1.5 hours
                message = f"🚶‍♂️ Time for a movement break! You haven't moved in {last_activity} minutes. Take a 5-minute walk."
                
                # If there's a meeting soon, adjust message
                if next_event and next_event.get("minutes_until", 999) < 45:
                    message += f" Perfect timing before your {next_event['title']} meeting!"
                
                new_nudges.append(SmartNudge(
                    id=f"movement_{datetime.now().hour}_{datetime.now().minute}",
                    type=NudgeType.MOVEMENT_BREAK,
                    urgency=NudgeUrgency.REMINDER,
                    message=message,
                    context=fitness,
                    devices=["Nest Mini", "Nest Hub Max"],
                    scheduled_time=datetime.now(),
                    created_at=datetime.now()
                ))
        
        # 4. MEDICATION REMINDERS (check for med tasks)
        for task in urgent_tasks:
            if any(word in task.get("title", "").lower() for word in ["med", "medication", "pills", "patch"]):
                new_nudges.append(SmartNudge(
                    id=f"medication_{task['title']}",
                    type=NudgeType.MEDICATION_REMINDER,
                    urgency=NudgeUrgency.URGENT,
                    message=f"💊 Don't forget: {task['title']} - this is on your urgent task list!",
                    context={"task": task},
                    devices=["Nest Hub Max", "Nest Mini"],
                    scheduled_time=datetime.now(),
                    created_at=datetime.now()
                ))
        
        # 5. TRANSITION WARNINGS (before meetings when doing focused work)
        if next_event and 18 <= next_event.get("minutes_until", 999) <= 22:
            steps_last_hour = fitness.get("steps_last_hour", 0)
            if steps_last_hour < 50:  # Been sitting/focused
                new_nudges.append(SmartNudge(
                    id=f"transition_{next_event['title']}",
                    type=NudgeType.TRANSITION_WARNING,
                    urgency=NudgeUrgency.REMINDER,
                    message=f"🔄 Transition time! {next_event['title']} in 20 minutes. Good time to save work and take a quick break.",
                    context={"next_event": next_event, "fitness": fitness},
                    devices=["Nest Hub Max"],
                    scheduled_time=datetime.now(),
                    created_at=datetime.now()
                ))
        
        # Add new nudges to pending (avoid duplicates)
        for nudge in new_nudges:
            if not any(existing.id == nudge.id for existing in self.pending_nudges):
                self.pending_nudges.append(nudge)
        
        # Send ready nudges
        ready_nudges = [n for n in self.pending_nudges if n.should_send_now()]
        for nudge in ready_nudges:
            await self._send_nudge(nudge)
            self.pending_nudges.remove(nudge)
            self.sent_nudges.append(nudge)
    
    def _create_meeting_nudge(self, event: Dict, urgency: NudgeUrgency, message: str) -> SmartNudge:
        """Create a meeting reminder nudge."""
        return SmartNudge(
            id=f"meeting_{event['title']}_{urgency.value}",
            type=NudgeType.MEETING_REMINDER,
            urgency=urgency,
            message=message,
            context={"event": event},
            devices=["Nest Hub Max", "Nest Mini"] if urgency == NudgeUrgency.CRITICAL else ["Nest Hub Max"],
            scheduled_time=datetime.now(),
            created_at=datetime.now()
        )
    
    async def _send_nudge(self, nudge: SmartNudge):
        """Send a nudge to the specified devices."""
        try:
            logger.info(f"📢 Sending {nudge.urgency.value} nudge: {nudge.message}")
            
            # Send to each device
            for device in nudge.devices:
                try:
                    if INTEGRATIONS_AVAILABLE:
                        await send_nudge_to_device(device, nudge.message)
                    else:
                        logger.info(f"Would send to {device}: {nudge.message}")
                except Exception as e:
                    logger.error(f"Failed to send nudge to {device}: {e}")
            
            # Log the context for debugging
            if nudge.context:
                logger.debug(f"Nudge context: {json.dumps(nudge.context, indent=2, default=str)}")
                
        except Exception as e:
            logger.error(f"Failed to send nudge: {e}")
    
    def get_recent_nudges(self, hours: int = 24) -> List[Dict]:
        """Get recent nudges for debugging/review."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [n for n in self.sent_nudges if n.created_at > cutoff]
        
        return [
            {
                "time": n.created_at.strftime("%H:%M"),
                "type": n.type.value,
                "urgency": n.urgency.value,
                "message": n.message,
                "devices": n.devices
            }
            for n in recent
        ]
    
    def get_pending_nudges(self) -> List[Dict]:
        """Get pending nudges for review."""
        return [
            {
                "scheduled_for": n.scheduled_time.strftime("%H:%M"),
                "type": n.type.value,
                "urgency": n.urgency.value,
                "message": n.message,
                "devices": n.devices
            }
            for n in self.pending_nudges
        ]

# Global nudge system instance
_nudge_system = None

def get_nudge_system() -> SmartNudgeSystem:
    """Get or create the global nudge system."""
    global _nudge_system
    if _nudge_system is None:
        _nudge_system = SmartNudgeSystem()
    return _nudge_system

# For testing
if __name__ == "__main__":
    async def test():
        nudge_system = get_nudge_system()
        
        # Run one check
        await nudge_system._check_and_send_nudges()
        
        print("Recent nudges:")
        for nudge in nudge_system.get_recent_nudges():
            print(f"  {nudge}")
        
        print("\nPending nudges:")
        for nudge in nudge_system.get_pending_nudges():
            print(f"  {nudge}")
    
    asyncio.run(test())