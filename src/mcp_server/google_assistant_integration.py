"""
Google Assistant Broadcast Integration for ADHD Nudges
Uses Google Home devices to broadcast messages that reach connected wearables
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

class BroadcastType(Enum):
    """Types of Google Assistant broadcasts for ADHD support."""
    GENTLE_REMINDER = "gentle"
    FOCUS_TIME = "focus"
    BREAK_TIME = "break"
    CELEBRATION = "celebration"
    TRANSITION = "transition"
    URGENT = "urgent"

class GoogleAssistantBroadcast:
    """Manages ADHD nudges via Google Assistant broadcast to wearables."""
    
    def __init__(self):
        self.is_initialized = False
        self.broadcast_history: List[Dict] = []
        self.google_devices: List[Dict] = []
        
        # ADHD-optimized broadcast templates
        self.broadcast_templates = {
            BroadcastType.GENTLE_REMINDER: [
                "Hey there, just checking in - how's your energy and focus right now?",
                "Gentle reminder: you're doing great, one step at a time",
                "Quick check-in: ready for the next task when you are",
                "No pressure, just wondering how you're feeling about your current task"
            ],
            BroadcastType.FOCUS_TIME: [
                "Time to dive deep! You've got this - let's tackle that important task",
                "Focus mode activated: you're in your zone, let's make some progress",
                "Deep work time! Put on your focus hat and show that task who's boss",
                "It's go time! Channel that ADHD hyperfocus power for good"
            ],
            BroadcastType.BREAK_TIME: [
                "Brain break time! Step away, stretch, and recharge for a few minutes",
                "Your amazing brain earned a rest - take 5 to move and breathe",
                "Break notification: time to be kind to your body and mind",
                "Pause button activated! Go get some water and natural light"
            ],
            BroadcastType.CELEBRATION: [
                "Task completed! Way to go - your persistence paid off beautifully",
                "Victory! Another win in the books. Celebrate this progress",
                "Achievement unlocked! You pushed through and made it happen",
                "Success! That was challenging and you handled it like a champion"
            ],
            BroadcastType.TRANSITION: [
                "Heads up: transition time in 10 minutes. Start wrapping up when ready",
                "Gentle transition warning: almost time to shift to your next thing",
                "Switching gears soon - take a moment to mentally prepare for what's next",
                "Time change coming up: no rush, just a friendly heads up"
            ],
            BroadcastType.URGENT: [
                "Important reminder: this needs your attention when you're ready",
                "Priority nudge: this task is waiting for you",
                "Hey, when you have a moment, there's something important to check",
                "Respectful urgent reminder: this could use your focus today"
            ]
        }
    
    async def initialize(self) -> bool:
        """Initialize Google Assistant broadcast integration."""
        try:
            # Check for available Google devices (reuse from nest nudge system)
            from .nest_nudges import nest_nudge_system
            
            if nest_nudge_system and nest_nudge_system.devices:
                # Filter for Google Home devices that support broadcasts
                self.google_devices = [
                    {
                        "name": device.name,
                        "model": device.model_name,
                        "device": device,
                        "supports_broadcast": "home" in device.model_name.lower() or 
                                           "nest" in device.model_name.lower()
                    }
                    for device in nest_nudge_system.devices
                ]
                
                broadcast_capable = [d for d in self.google_devices if d["supports_broadcast"]]
                
                if broadcast_capable:
                    self.is_initialized = True
                    logger.info(f"✅ Google Assistant broadcast ready with {len(broadcast_capable)} device(s)")
                    return True
                else:
                    logger.warning("⚠️ No broadcast-capable Google devices found")
                    return False
            else:
                logger.warning("⚠️ No Google devices available for broadcasting")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Assistant broadcast: {e}")
            return False
    
    async def send_broadcast_nudge(self, 
                                  broadcast_type: BroadcastType,
                                  custom_message: str = None,
                                  target_device: str = None) -> bool:
        """Send ADHD nudge via Google Assistant broadcast.
        
        Args:
            broadcast_type: Type of broadcast message
            custom_message: Override default message
            target_device: Specific device name, or None for all devices
        """
        if not self.is_initialized:
            logger.warning("Google Assistant broadcast not initialized")
            return False
        
        try:
            # Choose message
            if custom_message:
                message = custom_message
            else:
                import random
                templates = self.broadcast_templates.get(broadcast_type, [])
                message = random.choice(templates) if templates else "ADHD support reminder"
            
            # Convert to broadcast format (simulated TTS audio)
            success = await self._send_assistant_broadcast(
                message=message,
                broadcast_type=broadcast_type,
                target_device=target_device
            )
            
            if success:
                # Log successful broadcast
                self.broadcast_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": broadcast_type.value,
                    "message": message,
                    "target_device": target_device,
                    "success": True
                })
                
                logger.info(f"✅ Sent broadcast nudge ({broadcast_type.value}): {message[:40]}...")
                return True
            else:
                logger.warning(f"❌ Failed to send broadcast nudge ({broadcast_type.value})")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending broadcast nudge: {e}")
            return False
    
    async def _send_assistant_broadcast(self,
                                       message: str,
                                       broadcast_type: BroadcastType,
                                       target_device: str = None) -> bool:
        """Send message via Google Assistant broadcast simulation."""
        try:
            from .nest_nudges import nest_nudge_system
            
            # Create broadcast-style TTS message with natural pacing
            broadcast_message = f"Attention everyone, {message}"
            
            # Send to specified device or all broadcast-capable devices
            target_devices = []
            
            if target_device:
                # Find specific device
                for google_device in self.google_devices:
                    if (google_device["name"] == target_device and 
                        google_device["supports_broadcast"]):
                        target_devices = [google_device["device"]]
                        break
            else:
                # Send to all broadcast-capable devices
                target_devices = [
                    google_device["device"] 
                    for google_device in self.google_devices 
                    if google_device["supports_broadcast"]
                ]
            
            if not target_devices:
                logger.warning("No suitable broadcast devices found")
                return False
            
            # Send broadcast via TTS to Google Home devices
            success_count = 0
            for device in target_devices:
                try:
                    if nest_nudge_system:
                        # Use the correct parameter format for the nest nudge system
                        success = await nest_nudge_system.send_nudge(
                            message=broadcast_message,
                            device_name=device.name
                        )
                        if success:
                            success_count += 1
                except Exception as e:
                    logger.warning(f"Failed to broadcast to {device.name}: {e}")
            
            # Consider success if at least one device worked
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send assistant broadcast: {e}")
            return False
    
    async def broadcast_focus_session(self, duration_minutes: int = 25) -> bool:
        """Start a focus session broadcast."""
        message = f"Focus session starting! Time to dive deep for {duration_minutes} minutes. You've got this!"
        return await self.send_broadcast_nudge(
            BroadcastType.FOCUS_TIME,
            custom_message=message
        )
    
    async def broadcast_break_reminder(self, session_duration: int = 90) -> bool:
        """Send break reminder after focused work."""
        message = f"You've been focused for {session_duration} minutes - time for a well-deserved brain break!"
        return await self.send_broadcast_nudge(
            BroadcastType.BREAK_TIME,
            custom_message=message
        )
    
    async def broadcast_celebration(self, achievement: str) -> bool:
        """Broadcast celebration for completed task."""
        message = f"Celebration time! You just completed: {achievement}. That's awesome progress!"
        return await self.send_broadcast_nudge(
            BroadcastType.CELEBRATION,
            custom_message=message
        )
    
    async def broadcast_transition_warning(self, next_activity: str, minutes: int = 10) -> bool:
        """Broadcast transition warning."""
        message = f"Friendly heads up: {next_activity} is coming up in {minutes} minutes. No pressure, just a gentle transition reminder."
        return await self.send_broadcast_nudge(
            BroadcastType.TRANSITION,
            custom_message=message
        )
    
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available Google Assistant devices."""
        return [
            {
                "name": device["name"],
                "model": device["model"],
                "supports_broadcast": device["supports_broadcast"],
                "type": "google_home" if "home" in device["model"].lower() else "nest_device"
            }
            for device in self.google_devices
        ]
    
    def get_broadcast_stats(self) -> Dict[str, Any]:
        """Get broadcast statistics."""
        if not self.broadcast_history:
            return {
                "total_broadcasts": 0,
                "success_rate": 0,
                "available_devices": len(self.google_devices)
            }
        
        total = len(self.broadcast_history)
        successful = sum(1 for broadcast in self.broadcast_history if broadcast["success"])
        
        # Group by type
        type_counts = {}
        for broadcast in self.broadcast_history:
            broadcast_type = broadcast["type"]
            type_counts[broadcast_type] = type_counts.get(broadcast_type, 0) + 1
        
        return {
            "total_broadcasts": total,
            "successful_broadcasts": successful,
            "success_rate": successful / total if total > 0 else 0,
            "broadcast_types": type_counts,
            "last_broadcast": self.broadcast_history[-1] if self.broadcast_history else None,
            "available_devices": len(self.google_devices),
            "broadcast_capable_devices": len([d for d in self.google_devices if d["supports_broadcast"]]),
            "initialized": self.is_initialized
        }

# Global instance
google_assistant_broadcast = None

async def initialize_google_assistant() -> GoogleAssistantBroadcast:
    """Initialize global Google Assistant broadcast integration."""
    global google_assistant_broadcast
    
    if google_assistant_broadcast is None:
        google_assistant_broadcast = GoogleAssistantBroadcast()
        await google_assistant_broadcast.initialize()
    
    return google_assistant_broadcast