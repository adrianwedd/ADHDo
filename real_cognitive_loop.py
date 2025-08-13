#!/usr/bin/env python3
"""
The REAL Cognitive Loop for ADHD Support
Simple, practical, and actually works.

This is what a cognitive loop should be:
1. Check the time
2. Check what's happening  
3. Check if music should be playing
4. Check if there's something urgent
5. Nudge appropriately
6. Repeat
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class RealCognitiveLoop:
    """The cognitive loop that actually helps ADHD."""
    
    def __init__(self):
        self.base_url = "http://localhost:23444"
        self.last_music_check = None
        self.last_calendar_check = None
        self.last_nudge = None
        self.panic_mode = False
        self.current_context = {}
        
    async def check_music(self) -> Dict:
        """Is music playing? Should it be?"""
        try:
            now = datetime.now()
            hour = now.hour
            
            # Should music be playing? (8am - 10pm)
            should_play = 8 <= hour < 22
            
            # Check current status
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/music/status") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        is_playing = data.get("is_playing", False)
                        
                        if should_play and not is_playing:
                            logger.info("🎵 Music should be playing but isn't. Starting focus music...")
                            # Start music
                            async with session.post(f"{self.base_url}/music/focus") as resp2:
                                if resp2.status == 200:
                                    logger.info("✅ Music started")
                                    return {"action": "started_music", "mood": "focus"}
                        
                        elif not should_play and is_playing:
                            logger.info("🔇 It's quiet time. Stopping music...")
                            async with session.post(f"{self.base_url}/music/stop") as resp2:
                                if resp2.status == 200:
                                    logger.info("✅ Music stopped")
                                    return {"action": "stopped_music"}
                        
                        elif is_playing:
                            return {"status": "music_playing", "track": data.get("current_track")}
                        else:
                            return {"status": "quiet"}
                            
        except Exception as e:
            logger.error(f"Music check failed: {e}")
            
        return {"status": "unknown"}
    
    async def check_calendar(self) -> List[Dict]:
        """What's coming up? Anything urgent?"""
        try:
            async with aiohttp.ClientSession() as session:
                # Use our tools endpoint to get calendar
                async with session.post(
                    f"{self.base_url}/claude/tools",
                    json={"message": "what's on my calendar"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        events = data.get("data", {}).get("events", [])
                        
                        urgent_events = []
                        for event in events:
                            event_time = datetime.fromisoformat(event['time'])
                            time_until = (event_time - datetime.now()).total_seconds() / 60
                            
                            # Urgent if within 15 minutes
                            if 0 <= time_until <= 15:
                                urgent_events.append({
                                    "title": event['title'],
                                    "minutes_until": int(time_until),
                                    "type": event.get('type', 'event')
                                })
                        
                        return urgent_events
                        
        except Exception as e:
            logger.error(f"Calendar check failed: {e}")
            
        return []
    
    async def send_contextual_nudge(self, context: Dict):
        """Send a nudge based on current context."""
        try:
            # Build nudge message based on context
            urgent_events = context.get("urgent_events", [])
            music_status = context.get("music", {})
            time_of_day = context.get("time_of_day", "day")
            
            if urgent_events:
                # PANIC MODE!
                event = urgent_events[0]
                if event['minutes_until'] <= 5:
                    message = f"🚨 URGENT: {event['title']} in {event['minutes_until']} minutes! DROP EVERYTHING!"
                    urgency = "urgent"
                else:
                    message = f"⏰ Reminder: {event['title']} coming up in {event['minutes_until']} minutes"
                    urgency = "high"
                    
            elif time_of_day == "evening" and datetime.now().hour >= 21:
                # Bedtime approaching
                message = "🛏️ Evening reminder: Start winding down for bed soon"
                urgency = "normal"
                
            elif time_of_day == "morning" and datetime.now().hour < 9:
                # Morning routine
                messages = [
                    "☀️ Good morning! Let's tackle today with focus",
                    "🌅 Morning check-in: What's the priority today?",
                    "☕ Rise and shine! Time to get that ADHD brain online"
                ]
                message = random.choice(messages)
                urgency = "normal"
                
            else:
                # Regular check-in
                return None  # No nudge needed
            
            # Send the nudge
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/nudge/send?message={message}&urgency={urgency}"
                async with session.post(url) as resp:
                    if resp.status == 200:
                        logger.info(f"📢 Nudge sent: {message}")
                        self.last_nudge = datetime.now()
                        return {"nudge_sent": message, "urgency": urgency}
                        
        except Exception as e:
            logger.error(f"Nudge failed: {e}")
            
        return None
    
    async def cognitive_check(self):
        """The main cognitive loop - check everything and act."""
        now = datetime.now()
        hour = now.hour
        
        # Determine time of day context
        if hour < 6:
            time_of_day = "night"
        elif hour < 12:
            time_of_day = "morning"
        elif hour < 17:
            time_of_day = "afternoon"
        elif hour < 21:
            time_of_day = "evening"
        else:
            time_of_day = "night"
        
        context = {
            "time": now.isoformat(),
            "time_of_day": time_of_day,
            "hour": hour
        }
        
        # 1. Check music
        music_status = await self.check_music()
        context["music"] = music_status
        
        # 2. Check calendar for urgent stuff
        urgent_events = await self.check_calendar()
        context["urgent_events"] = urgent_events
        
        # 3. Determine if we're in panic mode
        self.panic_mode = len(urgent_events) > 0 and any(
            e['minutes_until'] <= 5 for e in urgent_events
        )
        context["panic_mode"] = self.panic_mode
        
        # 4. Send contextual nudge if needed
        # Don't nudge too often (max every 5 minutes unless panic)
        should_nudge = (
            self.last_nudge is None or 
            (datetime.now() - self.last_nudge).seconds > 300 or
            self.panic_mode
        )
        
        if should_nudge:
            nudge_result = await self.send_contextual_nudge(context)
            if nudge_result:
                context["nudge"] = nudge_result
        
        self.current_context = context
        return context
    
    async def run_loop(self):
        """Run the cognitive loop continuously."""
        logger.info("🧠 Starting REAL Cognitive Loop")
        logger.info("This loop actually does useful things:")
        logger.info("  • Checks if music should be playing")
        logger.info("  • Monitors calendar for urgent events")
        logger.info("  • Sends contextual nudges")
        logger.info("  • Panics appropriately when needed")
        
        while True:
            try:
                # Run cognitive check
                context = await self.cognitive_check()
                
                # Log status every 10 minutes or when something important happens
                if (datetime.now().minute % 10 == 0 or 
                    context.get("panic_mode") or 
                    context.get("nudge")):
                    
                    logger.info(f"🧠 Cognitive Status:")
                    logger.info(f"  Time: {context['time_of_day']} ({context['hour']}:00)")
                    logger.info(f"  Music: {context['music'].get('status', 'unknown')}")
                    logger.info(f"  Urgent: {len(context['urgent_events'])} events")
                    if context.get("panic_mode"):
                        logger.warning("  🚨 PANIC MODE ACTIVE!")
                
                # Check more frequently in panic mode
                if self.panic_mode:
                    await asyncio.sleep(30)  # Every 30 seconds
                else:
                    await asyncio.sleep(60)  # Every minute
                    
            except KeyboardInterrupt:
                logger.info("🛑 Stopping cognitive loop")
                break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                await asyncio.sleep(60)

async def main():
    """Run the real cognitive loop."""
    print("="*60)
    print("🧠 THE REAL COGNITIVE LOOP")
    print("="*60)
    print("What this actually does:")
    print("✓ Ensures music is playing when it should be")
    print("✓ Checks your calendar for urgent stuff")
    print("✓ Sends nudges at appropriate times")
    print("✓ PANICS when you're about to miss something")
    print("="*60)
    
    # Test connection
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:23444/health") as resp:
                if resp.status == 200:
                    print("✅ Server connected")
                else:
                    print("❌ Server not responding")
                    return
    except:
        print("❌ Cannot connect to server at http://localhost:23444")
        print("Start it with: ./start_adhd_support.sh")
        return
    
    loop = RealCognitiveLoop()
    await loop.run_loop()

if __name__ == "__main__":
    asyncio.run(main())