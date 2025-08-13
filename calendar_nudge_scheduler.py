#!/usr/bin/env python3
"""
Calendar-Based Context-Aware Nudge Scheduler
Reads Google Calendar events and generates smart nudges based on context
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = os.environ.get("BASE_URL", "http://localhost:23444")
CHECK_INTERVAL = 60  # Check every minute
NUDGE_ADVANCE_MINUTES = 15  # Start nudging 15 minutes before events

# Predefined context-aware nudge templates
NUDGE_TEMPLATES = {
    "bedtime": {
        "pre_nudges": [
            "🛏️ Heads up! Bedtime in {minutes} minutes. Time to start winding down.",
            "🌙 {minutes} minutes until bedtime. Save your work and prep for tomorrow!",
            "💤 Bedtime approaching in {minutes} min. ADHD brains need good sleep!"
        ],
        "escalations": [
            "⏰ It's bedtime! Your ADHD brain needs consistent sleep for executive function.",
            "🚨 Past bedtime! Every minute late makes tomorrow harder. Let's go!",
            "❗ Seriously, bed NOW! Your future self will thank you.",
            "🔴 FINAL CALL: Sleep deprivation wrecks ADHD symptoms. BED. NOW.",
            "💀 You're sabotaging tomorrow. I'm playing annoying music until you sleep."
        ]
    },
    "meeting": {
        "pre_nudges": [
            "📅 Meeting '{title}' in {minutes} minutes. Prep time!",
            "🎯 {minutes} min until '{title}'. Gather materials & thoughts.",
            "⚡ '{title}' starts in {minutes} min. Bathroom break now!"
        ],
        "escalations": [
            "🚨 '{title}' starting NOW! Join immediately!",
            "❗ You're LATE for '{title}'! Join now!",
            "🔴 Missing '{title}' - this is important!"
        ]
    },
    "task": {
        "pre_nudges": [
            "📝 Task '{title}' due in {minutes} minutes. How's progress?",
            "⏰ {minutes} min left for '{title}'. Focus time!",
            "🎯 '{title}' deadline in {minutes} min. Final push!"
        ],
        "escalations": [
            "⚠️ '{title}' is DUE NOW! Submit what you have!",
            "🚨 OVERDUE: '{title}' needed immediate attention!",
            "❗ '{title}' is late - communicate status NOW!"
        ]
    },
    "medication": {
        "pre_nudges": [
            "💊 Medication time in {minutes} minutes. Get water ready.",
            "🏥 {minutes} min until meds. Don't forget!",
            "⏰ Medication reminder: {minutes} minutes."
        ],
        "escalations": [
            "💊 MEDICATION TIME! Take your meds NOW!",
            "🚨 MEDS OVERDUE! This affects your whole day!",
            "❗ TAKE YOUR MEDICATION! Executive function depends on it!"
        ]
    },
    "break": {
        "pre_nudges": [
            "🌟 Break time in {minutes} minutes. Wrap up current task.",
            "☕ {minutes} min until break. Good stopping point?",
            "🏃 Break coming in {minutes} min. Save your work!"
        ],
        "escalations": [
            "🎯 BREAK TIME! Step away from work NOW!",
            "⚡ You NEED this break! Hyperfocus isn't healthy!",
            "🚨 MANDATORY BREAK! Your brain needs rest!"
        ]
    }
}

class CalendarEvent:
    """Simple calendar event representation."""
    def __init__(self, title: str, start_time: datetime, event_type: str = "task", 
                 description: str = "", location: str = ""):
        self.title = title
        self.start_time = start_time
        self.event_type = event_type
        self.description = description
        self.location = location
        self.nudge_count = 0
        self.last_nudge = None
        self.acknowledged = False

class CalendarNudgeScheduler:
    """Manages calendar-based nudging with context awareness."""
    
    def __init__(self):
        self.events: List[CalendarEvent] = []
        self.active_nudges: Dict[str, CalendarEvent] = {}
        
    async def send_nudge(self, message: str, urgency: str = "normal"):
        """Send a nudge through the API."""
        try:
            async with aiohttp.ClientSession() as session:
                # Try Nest nudge first
                url = f"{BASE_URL}/nudge/send?message={message}&urgency={urgency}"
                async with session.post(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success"):
                            logger.info(f"✅ Nudge sent: {message[:50]}...")
                            return True
                    
                # Fallback to simple log
                logger.info(f"📢 NUDGE: {message}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send nudge: {e}")
            logger.info(f"📢 NUDGE (offline): {message}")
            return False
    
    def get_nudge_message(self, event: CalendarEvent, minutes_until: int) -> tuple[str, str]:
        """Get appropriate nudge message based on context."""
        templates = NUDGE_TEMPLATES.get(event.event_type, NUDGE_TEMPLATES["task"])
        
        if minutes_until > 0:
            # Pre-event nudges
            nudge_index = min(event.nudge_count, len(templates["pre_nudges"]) - 1)
            template = templates["pre_nudges"][nudge_index]
            urgency = "normal"
        else:
            # Post-event escalations
            escalation_index = min(event.nudge_count, len(templates["escalations"]) - 1)
            template = templates["escalations"][escalation_index]
            urgency = "urgent" if event.nudge_count > 2 else "high"
        
        # Format the message
        message = template.format(
            title=event.title,
            minutes=abs(minutes_until),
            description=event.description[:50] if event.description else ""
        )
        
        return message, urgency
    
    def load_sample_events(self):
        """Load sample calendar events for testing."""
        now = datetime.now()
        
        # Add sample events
        self.events = [
            # Bedtime routine
            CalendarEvent(
                "Bedtime", 
                now.replace(hour=22, minute=0, second=0, microsecond=0),
                "bedtime",
                "Consistent sleep schedule for ADHD management"
            ),
            
            # Morning medication
            CalendarEvent(
                "Morning Medication",
                now.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1),
                "medication",
                "Take ADHD medication with breakfast"
            ),
            
            # Work breaks every 2 hours
            CalendarEvent(
                "Stretch Break",
                now + timedelta(hours=2),
                "break",
                "5-minute movement break to reset focus"
            ),
            
            # Example meeting
            CalendarEvent(
                "Team Standup",
                now.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1),
                "meeting",
                "Daily team sync"
            )
        ]
        
        logger.info(f"📅 Loaded {len(self.events)} calendar events")
    
    async def check_and_nudge(self):
        """Check all events and send appropriate nudges."""
        now = datetime.now()
        
        for event in self.events:
            if event.acknowledged:
                continue
                
            # Calculate time until event
            time_diff = event.start_time - now
            minutes_until = int(time_diff.total_seconds() / 60)
            
            # Check if we should nudge
            should_nudge = False
            
            if -60 <= minutes_until <= NUDGE_ADVANCE_MINUTES:
                # We're in the nudge window
                if event.last_nudge is None:
                    should_nudge = True
                else:
                    # Check if enough time passed for next nudge
                    mins_since_last = (now - event.last_nudge).total_seconds() / 60
                    
                    if minutes_until > 0:
                        # Pre-event: nudge every 5 minutes
                        should_nudge = mins_since_last >= 5
                    else:
                        # Post-event: escalate gradually
                        escalation_delays = [2, 5, 10, 15, 30]
                        delay_index = min(event.nudge_count - 1, len(escalation_delays) - 1)
                        should_nudge = mins_since_last >= escalation_delays[delay_index]
            
            if should_nudge:
                message, urgency = self.get_nudge_message(event, minutes_until)
                await self.send_nudge(message, urgency)
                
                event.nudge_count += 1
                event.last_nudge = now
                
                # Auto-acknowledge after too many nudges
                if event.nudge_count >= 8:
                    event.acknowledged = True
                    logger.info(f"🔇 Auto-acknowledged {event.title} after {event.nudge_count} nudges")
    
    async def add_bedtime_schedule(self, bedtime: str = "22:00"):
        """Add or update bedtime schedule."""
        try:
            hour, minute = map(int, bedtime.split(':'))
            
            # Remove existing bedtime
            self.events = [e for e in self.events if e.event_type != "bedtime"]
            
            # Add new bedtime for today
            now = datetime.now()
            bedtime_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If bedtime already passed today, set for tomorrow
            if bedtime_today < now:
                bedtime_today += timedelta(days=1)
            
            self.events.append(CalendarEvent(
                "Bedtime",
                bedtime_today,
                "bedtime",
                "ADHD-optimized sleep schedule"
            ))
            
            logger.info(f"✅ Bedtime set for {bedtime_today.strftime('%H:%M')}")
            
            # Send confirmation nudge
            await self.send_nudge(
                f"🛏️ Bedtime scheduled for {bedtime}. I'll start reminding you 15 minutes before.",
                "normal"
            )
            
        except Exception as e:
            logger.error(f"Failed to set bedtime: {e}")
    
    async def run_scheduler(self):
        """Main scheduling loop."""
        logger.info("📅 Starting calendar-based nudge scheduler")
        
        while True:
            try:
                await self.check_and_nudge()
                
                # Clean up old events (more than 2 hours past)
                now = datetime.now()
                self.events = [
                    e for e in self.events 
                    if e.start_time > now - timedelta(hours=2)
                ]
                
                # Log status every 10 minutes
                if now.minute % 10 == 0:
                    active_count = sum(1 for e in self.events if not e.acknowledged)
                    logger.info(f"📊 Tracking {active_count} active events")
                
                await asyncio.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(CHECK_INTERVAL)

async def main():
    """Main entry point."""
    print("="*60)
    print("📅 CALENDAR-BASED CONTEXT-AWARE NUDGE SCHEDULER")
    print("="*60)
    
    scheduler = CalendarNudgeScheduler()
    
    # Load sample events (replace with real calendar integration)
    scheduler.load_sample_events()
    
    # Add bedtime for tonight
    await scheduler.add_bedtime_schedule("22:00")
    
    # Show upcoming events
    print("\n📅 Upcoming Events:")
    for event in sorted(scheduler.events, key=lambda e: e.start_time)[:5]:
        time_str = event.start_time.strftime("%H:%M")
        print(f"  • {time_str} - {event.title} ({event.event_type})")
    
    print("\n✅ Scheduler running. Press Ctrl+C to stop.\n")
    
    try:
        await scheduler.run_scheduler()
    except KeyboardInterrupt:
        print("\n👋 Scheduler stopped")

if __name__ == "__main__":
    asyncio.run(main())