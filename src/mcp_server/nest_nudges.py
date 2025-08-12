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
        self.min_nudge_interval = timedelta(minutes=5)  # Don't overwhelm ADHD users
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
                
                # Filter for Nest/Google Home devices (prioritize Nest Mini for nudges)
                for cc in chromecasts:
                    model_lower = cc.model_name.lower()
                    if any(nest in model_lower for nest in ['nest mini', 'google home mini', 'nest hub', 'google home']):
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
        """Send a nudge to Nest device(s) with thread-safe device handling."""
        try:
            # Check if we're nudging too frequently
            if not self._can_nudge(device_name):
                logger.info("⏰ Skipping nudge - too soon since last nudge")
                return False
            
            # If no devices discovered yet, try immediate discovery
            if not self.devices:
                logger.info("🔍 No devices available, attempting immediate discovery...")
                success = await self._immediate_device_discovery()
                if not success:
                    logger.warning("❌ No devices found for nudge")
                    return False
            
            # Select target device (simplified approach)
            target_device = None
            if device_name:
                # Find specific device by name
                for device in self.devices:
                    if device.name == device_name:
                        target_device = device
                        break
            else:
                # Prefer Nest Hub Max if available
                for device in self.devices:
                    if 'nest hub max' in device.model_name.lower():
                        target_device = device
                        logger.info(f"🎯 Using Nest Hub Max for nudge")
                        break
                
                # Fallback to first available device
                if not target_device and self.devices:
                    target_device = self.devices[0]
            
            if not target_device:
                logger.warning("No suitable device found for nudge")
                return False
            
            # Use Google TTS directly (external URL works, local URLs don't)
            import urllib.parse
            encoded_message = urllib.parse.quote(message)
            audio_url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded_message}&tl=en&client=tw-ob"
            logger.info(f"🌐 Using external TTS URL (workaround for network issue): {audio_url[:80]}...")
            
            # Send nudge using fresh discovery approach (like working direct test)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._send_nudge_fresh_discovery,
                audio_url,
                volume,
                message,
                target_device.name  # Just pass the device name for targeting
            )
            
            if result:
                # Update last nudge time
                self.last_nudge_time[target_device.name] = datetime.now()
                logger.info(f"📢 Nudge sent to {target_device.name}: {message[:50]}...")
                return True
            else:
                logger.error(f"Failed to send nudge to {target_device.name}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Nudge failed: {e}")
            return False
    
    async def _immediate_device_discovery(self) -> bool:
        """Perform immediate device discovery for API requests."""
        try:
            loop = asyncio.get_event_loop()
            chromecasts, browser = await loop.run_in_executor(
                None, 
                lambda: pychromecast.get_chromecasts(timeout=10)
            )
            
            # Filter for Nest/Google Home devices (avoid duplicates)
            for cc in chromecasts:
                model_lower = cc.model_name.lower()
                if any(nest in model_lower for nest in ['nest', 'google home', 'home mini', 'home max']):
                    # Check if already in devices list to avoid duplicates
                    if not any(existing.name == cc.name for existing in self.devices):
                        self.devices.append(cc)
                        self.device_map[cc.name] = cc
                        logger.info(f"✅ Found Nest device: {cc.name} ({cc.model_name})")
            
            # Stop discovery
            browser.stop_discovery()
            
            return len(self.devices) > 0
            
        except Exception as e:
            logger.error(f"Immediate device discovery failed: {e}")
            return False
    
    def _send_nudge_fresh_discovery(self, audio_url: str, volume: float, message: str, target_device_name: str) -> bool:
        """Send nudge with fresh discovery (mimics working direct test approach)."""
        try:
            import time
            
            logger.info(f"🔍 Fresh discovery for nudge to {target_device_name}")
            
            # Fresh discovery (exactly like direct test that works)
            chromecasts, browser = pychromecast.get_chromecasts(timeout=15)
            
            # Filter out non-Nest devices first (CRITICAL: Exclude Chromecast Audio!)
            nest_only = []
            for cc in chromecasts:
                model_lower = cc.model_name.lower()
                # Skip Chromecast Audio and media devices
                if 'chromecast audio' in model_lower or 'shield' in model_lower or cc.name == 'Shack Speakers':
                    logger.debug(f"⏭️ Skipping media device: {cc.name} ({cc.model_name})")
                    continue
                # Only include Nest and Google Home devices
                if 'nest' in model_lower or 'google home' in model_lower or 'home mini' in model_lower:
                    nest_only.append(cc)
                    logger.debug(f"✅ Found Nest device: {cc.name} ({cc.model_name})")
            
            target_cast = None
            # If specific device requested, find it in Nest-only list
            if target_device_name:
                for cc in nest_only:
                    if cc.name == target_device_name:
                        target_cast = cc
                        logger.info(f"✅ Found target device: {cc.name}")
                        break
            
            # Otherwise prefer Nest Mini for nudges
            if not target_cast:
                for cc in nest_only:
                    if 'nest mini' in cc.model_name.lower() or 'google home mini' in cc.model_name.lower():
                        target_cast = cc
                        logger.info(f"✅ Using Nest Mini for nudge: {cc.name}")
                        break
            
            # Fallback to any Nest device
            if not target_cast and nest_only:
                target_cast = nest_only[0]
                logger.info(f"✅ Using Nest device for nudge: {target_cast.name}")
            
            if not target_cast:
                logger.error(f"❌ Target device {target_device_name} not found in fresh discovery")
                browser.stop_discovery()
                return False
            
            # Connect and send (exactly like working direct test)
            logger.info(f"🎯 Connecting to {target_cast.name}...")
            target_cast.wait()
            mc = target_cast.media_controller
            
            # Set volume
            target_cast.set_volume(volume)
            logger.info(f"🔊 Volume set to {int(volume * 100)}%")
            
            # Check if this is a Nest Hub (has screen)
            has_screen = 'nest hub' in target_cast.model_name.lower()
            
            if has_screen:
                # Send visual message to Nest Hub display
                logger.info(f"📺 Sending visual message to {target_cast.name}")
                success = self._send_visual_message(target_cast, message)
                if success:
                    logger.info(f"✅ Visual message sent to {target_cast.name}")
                    # Wait for visual to display before audio
                    time.sleep(1)
            
            # Play the nudge
            logger.info(f"🎵 Playing nudge...")
            mc.play_media(audio_url, 'audio/mpeg')
            mc.block_until_active()
            time.sleep(2)  # Give it time to start
            
            logger.info(f"✅ Nudge sent successfully to {target_cast.name}")
            
            # Clean up
            browser.stop_discovery()
            
            return True
            
        except Exception as e:
            logger.error(f"Fresh discovery nudge failed: {e}")
            return False
    
    def _send_visual_message(self, cast_device, message: str) -> bool:
        """Send a visual message to Nest Hub display."""
        try:
            from datetime import datetime
            import html
            
            # Create HTML content for the message
            timestamp = datetime.now().strftime("%I:%M %p")
            escaped_message = html.escape(message)
            
            html_content = f"""
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        font-family: 'Segoe UI', Arial, sans-serif;
                        margin: 0;
                        padding: 40px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        text-align: center;
                        box-sizing: border-box;
                    }}
                    .container {{
                        background: rgba(255, 255, 255, 0.1);
                        backdrop-filter: blur(10px);
                        border-radius: 20px;
                        padding: 30px;
                        max-width: 80%;
                        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                        border: 1px solid rgba(255, 255, 255, 0.18);
                    }}
                    .title {{
                        font-size: 32px;
                        font-weight: bold;
                        margin-bottom: 20px;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                    }}
                    .message {{
                        font-size: 28px;
                        line-height: 1.4;
                        margin-bottom: 20px;
                        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
                    }}
                    .timestamp {{
                        font-size: 20px;
                        opacity: 0.8;
                        margin-top: 20px;
                    }}
                    .icon {{
                        font-size: 48px;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="icon">🧠</div>
                    <div class="title">ADHD Support</div>
                    <div class="message">{escaped_message}</div>
                    <div class="timestamp">{timestamp}</div>
                </div>
                <script>
                    // Auto-refresh to show message for ~30 seconds
                    setTimeout(function() {{
                        document.body.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:Arial;color:#666;font-size:24px;">Message displayed</div>';
                    }}, 30000);
                </script>
            </body>
            </html>
            """
            
            # Create a data URL for the HTML content
            import base64
            import urllib.parse
            
            encoded_html = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
            data_url = f"data:text/html;charset=utf-8;base64,{encoded_html}"
            
            # Try Default Media Receiver first (more reliable)
            try:
                # Use Default Media Receiver app
                media_controller = cast_device.media_controller
                
                # Create a simple image with text (this works better than HTML)
                image_url = self._create_text_image_url(message)
                
                # Display as an image
                media_controller.play_media(
                    image_url,
                    'image/png',
                    title="ADHD Support",
                    subtitle=message
                )
                media_controller.block_until_active()
                logger.info(f"📺 Visual message displayed on {cast_device.name}")
                return True
                
            except Exception as e:
                logger.warning(f"Media receiver approach failed: {e}")
                
                # Fallback to web app approach
                try:
                    web_controller = cast_device.start_app('CC1AD845')  # Default Media Receiver
                    if web_controller:
                        web_controller.load_url(data_url)
                        logger.info(f"📺 Visual content loaded via web app on {cast_device.name}")
                        return True
                    else:
                        logger.warning(f"Failed to start media receiver on {cast_device.name}")
                        return False
                except Exception as e2:
                    logger.warning(f"Web app fallback also failed: {e2}")
                    return False
                
        except Exception as e:
            logger.error(f"Visual message failed: {e}")
            return False
    
    def _create_text_image_url(self, message: str) -> str:
        """Create a URL for an image with text (using a simple text-to-image service)."""
        try:
            import urllib.parse
            from datetime import datetime
            
            # Use a simple approach - create a URL that generates an image with text
            # This uses a public API that creates images from text
            encoded_message = urllib.parse.quote(message)
            timestamp = datetime.now().strftime("%I:%M %p")
            
            # Create a simple image URL (this is a fallback)
            # In production, you'd want to host your own image generation service
            image_url = f"https://via.placeholder.com/800x600/4A90E2/FFFFFF?text=🧠%20ADHD%20Support%0A%0A{encoded_message}%0A%0A{timestamp}"
            
            return image_url
            
        except Exception as e:
            logger.error(f"Failed to create text image URL: {e}")
            # Fallback to a simple placeholder
            return "https://via.placeholder.com/800x600/4A90E2/FFFFFF?text=ADHD%20Support%20Message"

    def _send_to_existing_device_sync(self, device, audio_url: str, volume: float, message: str) -> bool:
        """Synchronously send nudge to existing device (runs in thread executor)."""
        try:
            import time
            
            # Wait for device to be fully connected
            logger.info(f"Waiting for device {device.name} to be ready...")
            max_connect_wait = 15  # Wait up to 15 seconds for connection
            for i in range(max_connect_wait):
                if device.socket_client.is_connected:
                    logger.info(f"Device {device.name} is connected after {i} seconds")
                    break
                time.sleep(1)
            else:
                # Try explicit wait
                device.wait(timeout=10)
            
            # Double-check connection
            if not device.socket_client.is_connected:
                logger.error(f"Device {device.name} failed to connect properly")
                return False
            
            # Use existing device connection
            mc = device.media_controller
            
            # Set volume first
            device.set_volume(volume)
            time.sleep(0.5)  # Give volume change time to apply
            
            # Play the nudge
            mc.play_media(audio_url, 'audio/mpeg')
            time.sleep(1)  # Give media controller time to start
            
            # Wait for playback to begin
            max_wait = 10  # Wait up to 10 seconds for playback to start
            for i in range(max_wait):
                if mc.status.player_state != 'IDLE':
                    break
                time.sleep(1)
            
            logger.info(f"Nudge playback started on {device.name}")
            return True
            
        except Exception as e:
            logger.error(f"Sync device send failed: {e}")
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