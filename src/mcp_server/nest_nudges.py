"""
Google Nest Nudge System for ADHD Support
Delivers contextual reminders and motivational messages through Nest speakers
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pychromecast
from gtts import gTTS
import tempfile
import os

logger = logging.getLogger(__name__)

class NudgeType(Enum):
    """Types of nudges for different ADHD needs."""
    GENTLE = "gentle"           # Soft reminders
    URGENT = "urgent"           # Time-sensitive alerts
    MOTIVATIONAL = "motivational"  # Dopamine boost messages
    TRANSITION = "transition"    # Task switching help
    BREAK = "break"             # Rest reminders
    FOCUS = "focus"             # Focus mode activation
    CELEBRATION = "celebration"  # Task completion rewards

@dataclass
class Nudge:
    """Represents a nudge to be delivered."""
    message: str
    type: NudgeType
    priority: int = 5  # 1-10, higher is more important
    device: Optional[str] = None  # Specific device or None for all
    volume: float = 0.5  # Volume level for this nudge
    
class NestNudgeSystem:
    """Manages nudge delivery to Google Nest devices."""
    
    def __init__(self):
        self.devices: List[pychromecast.Chromecast] = []
        self.device_map: Dict[str, pychromecast.Chromecast] = {}
        self.nudge_queue: List[Nudge] = []
        self.last_nudge_time: Dict[str, datetime] = {}
        self.min_nudge_interval = timedelta(minutes=5)  # Don't overwhelm
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # ADHD-optimized message templates
        self.templates = {
            NudgeType.GENTLE: [
                "Hey there, just a gentle reminder about {task}",
                "When you're ready, {task} is waiting for you",
                "No pressure, but {task} could use your attention"
            ],
            NudgeType.URGENT: [
                "Important: {task} needs attention soon",
                "Heads up! {task} is time-sensitive",
                "Quick reminder: {task} deadline approaching"
            ],
            NudgeType.MOTIVATIONAL: [
                "You've got this! Ready to tackle {task}?",
                "Perfect time to make progress on {task}",
                "Small step forward: how about {task}?"
            ],
            NudgeType.TRANSITION: [
                "Time to switch gears. Wrapping up current task in 5 minutes",
                "Transition time: Save your work and prepare for {task}",
                "Switching to {task} soon. Start winding down"
            ],
            NudgeType.BREAK: [
                "Break time! Stand up and stretch for a minute",
                "Your brain needs a quick reset. How about a water break?",
                "5 minute movement break will boost your focus"
            ],
            NudgeType.FOCUS: [
                "Entering focus mode. Minimizing distractions",
                "Deep work time. Let's tackle {task} with full attention",
                "Focus session starting. You've got this!"
            ],
            NudgeType.CELEBRATION: [
                "Amazing! You completed {task}!",
                "Victory! {task} is done. Well done!",
                "Celebrate! You crushed {task}!"
            ]
        }
    
    async def initialize(self) -> bool:
        """Initialize connection to Nest devices."""
        try:
            logger.info("🔍 Starting Nest device discovery...")
            
            # Start background discovery to handle timing issues
            asyncio.create_task(self._background_device_discovery())
            
            # Always start scheduler regardless of initial discovery
            self.scheduler_task = asyncio.create_task(self._nudge_scheduler())
            
            logger.info("🎯 Nest nudge system started (devices will connect in background)")
            return True
                
        except Exception as e:
            logger.error(f"❌ Nest initialization failed: {e}")
            return False
    
    async def _background_device_discovery(self):
        """Discover devices in background with retries."""
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts and not self.devices:
            try:
                attempt += 1
                await asyncio.sleep(3 + attempt)  # Progressive delay
                
                logger.info(f"🔍 Device discovery attempt {attempt}/{max_attempts}")
                
                # Run discovery in thread executor for better reliability
                loop = asyncio.get_event_loop()
                chromecasts, browser = await loop.run_in_executor(
                    None, 
                    lambda: pychromecast.get_chromecasts(timeout=20)
                )
                
                # Filter for Nest/Google Home devices
                for cc in chromecasts:
                    model_lower = cc.model_name.lower()
                    if any(nest in model_lower for nest in ['nest', 'google home', 'home mini', 'home max']):
                        self.devices.append(cc)
                        self.device_map[cc.name] = cc
                        logger.info(f"✅ Found Nest device: {cc.name} ({cc.model_name})")
                        
                        # Prioritize Nest Hub Max if found
                        if 'nest hub max' in model_lower:
                            logger.info(f"🎯 Nest Hub Max found - prioritizing for nudges")
                
                # Stop discovery
                browser.stop_discovery()
                
                if self.devices:
                    logger.info(f"🎯 Connected to {len(self.devices)} Nest device(s)")
                    break
                else:
                    logger.info(f"⚠️ No devices found, attempt {attempt}/{max_attempts}")
                    
            except Exception as e:
                logger.warning(f"Discovery attempt {attempt} failed: {e}")
        
        if not self.devices:
            logger.warning("⚠️ No Nest devices found after all attempts")
    
    async def send_nudge(self, 
                         message: str, 
                         nudge_type: NudgeType = NudgeType.GENTLE,
                         device_name: Optional[str] = None,
                         volume: float = 0.5) -> bool:
        """Send a nudge to Nest device(s)."""
        try:
            # Check if we're nudging too frequently
            if not self._can_nudge(device_name):
                logger.info("⏰ Skipping nudge - too soon since last nudge")
                return False
            
            # Select device(s) - prefer Nest Hub Max if no specific device requested
            if device_name and device_name in self.device_map:
                devices = [self.device_map[device_name]]
            else:
                devices = self.devices
                # If no specific device, prefer Nest Hub Max if available
                if not device_name and devices:
                    nest_max = None
                    for device in devices:
                        if 'nest hub max' in device.model_name.lower():
                            nest_max = device
                            break
                    if nest_max:
                        devices = [nest_max]
                        logger.info(f"🎯 Using Nest Hub Max for nudge")
            
            if not devices:
                logger.warning("No devices available for nudge")
                return False
            
            # Generate TTS audio
            tts = gTTS(text=message, lang='en', slow=False)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tts.save(tmp_file.name)
                # Store filename for serving
                self._audio_files = getattr(self, '_audio_files', {})
                self._audio_files[os.path.basename(tmp_file.name)] = tmp_file.name
                audio_url = f"http://192.168.1.100:23443/nudge-audio/{os.path.basename(tmp_file.name)}"
            
            # Send to each device
            for device in devices:
                try:
                    device.wait()
                    mc = device.media_controller
                    
                    # Set volume
                    device.set_volume(volume)
                    
                    # Play the nudge
                    mc.play_media(audio_url, 'audio/mp3')
                    mc.block_until_active()
                    
                    # Update last nudge time
                    self.last_nudge_time[device.name] = datetime.now()
                    
                    logger.info(f"📢 Nudge sent to {device.name}: {message[:50]}...")
                    
                    # Wait for playback to complete (estimate)
                    await asyncio.sleep(len(message) * 0.06)  # Rough TTS duration estimate
                    
                except Exception as e:
                    logger.error(f"Failed to nudge {device.name}: {e}")
            
            # Clean up temp file after a delay
            asyncio.create_task(self._cleanup_audio_file(tmp_file.name, delay=30))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Nudge failed: {e}")
            return False
    
    def _can_nudge(self, device_name: Optional[str]) -> bool:
        """Check if enough time has passed since last nudge."""
        if device_name:
            last_time = self.last_nudge_time.get(device_name)
        else:
            # Check most recent nudge across all devices
            if not self.last_nudge_time:
                return True
            last_time = max(self.last_nudge_time.values())
        
        if not last_time:
            return True
            
        return datetime.now() - last_time >= self.min_nudge_interval
    
    async def _cleanup_audio_file(self, filepath: str, delay: int = 30):
        """Clean up temporary audio file after delay."""
        await asyncio.sleep(delay)
        try:
            os.remove(filepath)
        except:
            pass
    
    async def nudge_task_reminder(self, task: str, urgency: str = "normal") -> bool:
        """Send a task reminder nudge."""
        if urgency == "high":
            nudge_type = NudgeType.URGENT
            volume = 0.6
        elif urgency == "low":
            nudge_type = NudgeType.GENTLE
            volume = 0.4
        else:
            nudge_type = NudgeType.MOTIVATIONAL
            volume = 0.5
        
        # Select random template
        templates = self.templates[nudge_type]
        template = random.choice(templates)
        message = template.format(task=task)
        
        return await self.send_nudge(message, nudge_type, volume=volume)
    
    async def nudge_break_time(self) -> bool:
        """Remind user to take a break."""
        message = random.choice(self.templates[NudgeType.BREAK])
        return await self.send_nudge(message, NudgeType.BREAK, volume=0.4)
    
    async def nudge_transition(self, next_task: str) -> bool:
        """Help with task transitions."""
        template = random.choice(self.templates[NudgeType.TRANSITION])
        message = template.format(task=next_task)
        return await self.send_nudge(message, NudgeType.TRANSITION, volume=0.5)
    
    async def nudge_celebration(self, completed_task: str) -> bool:
        """Celebrate task completion for dopamine boost."""
        template = random.choice(self.templates[NudgeType.CELEBRATION])
        message = template.format(task=completed_task)
        return await self.send_nudge(message, NudgeType.CELEBRATION, volume=0.6)
    
    async def _nudge_scheduler(self):
        """Background task to manage scheduled nudges."""
        logger.info("⏰ Nudge scheduler started")
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Process queued nudges
                if self.nudge_queue:
                    nudge = self.nudge_queue.pop(0)
                    await self.send_nudge(
                        nudge.message,
                        nudge.type,
                        nudge.device,
                        nudge.volume
                    )
                
                # Check for scheduled nudges based on time
                current_hour = datetime.now().hour
                current_minute = datetime.now().minute
                
                # Morning routine nudge
                if current_hour == 9 and current_minute == 0:
                    await self.send_nudge(
                        "Good morning! Ready to start your day? What's your main focus today?",
                        NudgeType.MOTIVATIONAL,
                        volume=0.5
                    )
                
                # Lunch break reminder
                elif current_hour == 12 and current_minute == 30:
                    await self.send_nudge(
                        "Lunch time! Take a proper break to recharge",
                        NudgeType.BREAK,
                        volume=0.4
                    )
                
                # Afternoon focus session
                elif current_hour == 14 and current_minute == 0:
                    await self.send_nudge(
                        "Afternoon focus session. What's your priority for the next 2 hours?",
                        NudgeType.FOCUS,
                        volume=0.5
                    )
                
                # End of day wrap-up
                elif current_hour == 17 and current_minute == 30:
                    await self.send_nudge(
                        "Wrapping up the day. Quick wins to finish?",
                        NudgeType.TRANSITION,
                        volume=0.4
                    )
                    
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
    
    def queue_nudge(self, nudge: Nudge):
        """Add a nudge to the queue."""
        self.nudge_queue.append(nudge)
        self.nudge_queue.sort(key=lambda x: x.priority, reverse=True)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.scheduler_task:
            self.scheduler_task.cancel()
        
        for device in self.devices:
            try:
                device.disconnect()
            except:
                pass

# Global instance
nest_nudge_system: Optional[NestNudgeSystem] = None

async def initialize_nest_nudges() -> bool:
    """Initialize the Nest nudge system."""
    global nest_nudge_system
    
    try:
        nest_nudge_system = NestNudgeSystem()
        success = await nest_nudge_system.initialize()
        
        if success:
            logger.info("🎯 Nest nudge system ready")
            return True
        else:
            nest_nudge_system = None
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize Nest nudges: {e}")
        nest_nudge_system = None
        return False