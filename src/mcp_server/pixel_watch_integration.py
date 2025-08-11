"""
Pixel Watch Integration via Home Assistant
Uses Home Assistant Companion App notifications for wearable ADHD nudges
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from .home_assistant_integration import HomeAssistantClient

logger = logging.getLogger(__name__)

class WearableNudgeType(Enum):
    """ADHD-optimized wearable nudge types."""
    GENTLE_REMINDER = "gentle"
    FOCUS_NUDGE = "focus"
    BREAK_REMINDER = "break"
    TASK_COMPLETION = "completion"
    ENERGY_CHECK = "energy"
    HYPERFOCUS_INTERRUPT = "hyperfocus"
    TRANSITION_WARNING = "transition"

class PixelWatchNudgeSystem:
    """Manages ADHD nudges via Pixel Watch through Home Assistant."""
    
    def __init__(self, ha_client: HomeAssistantClient = None):
        self.ha_client = ha_client or HomeAssistantClient()
        self.nudge_history: List[Dict] = []
        self.is_initialized = False
        self.wearable_device_id = None
        
        # ADHD-optimized nudge templates for wearables
        self.nudge_templates = {
            WearableNudgeType.GENTLE_REMINDER: {
                "title": "🤏 Gentle nudge",
                "messages": [
                    "Time for a quick check-in?",
                    "How's your energy right now?",
                    "Ready for the next step?",
                    "What's on your mind?"
                ]
            },
            WearableNudgeType.FOCUS_NUDGE: {
                "title": "🎯 Focus time",
                "messages": [
                    "Let's tackle that task!",
                    "You've got this - one step at a time",
                    "Deep work mode: ON",
                    "Time to dive in!"
                ]
            },
            WearableNudgeType.BREAK_REMINDER: {
                "title": "☕ Break time",
                "messages": [
                    "Your brain earned a break!",
                    "Step away for 5 minutes",
                    "Stretch, breathe, reset",
                    "Movement = better thinking"
                ]
            },
            WearableNudgeType.TASK_COMPLETION: {
                "title": "✅ Task done!",
                "messages": [
                    "Nice work! What's next?",
                    "Progress! Keep the momentum",
                    "Another win in the books",
                    "Celebrate, then continue"
                ]
            },
            WearableNudgeType.ENERGY_CHECK: {
                "title": "⚡ Energy check",
                "messages": [
                    "High energy? Tackle hard tasks",
                    "Low energy? Try easier wins",
                    "Match tasks to your energy",
                    "Energy first, tasks second"
                ]
            },
            WearableNudgeType.HYPERFOCUS_INTERRUPT: {
                "title": "🛑 Hyperfocus break",
                "messages": [
                    "Been focused for 2+ hours - hydrate!",
                    "Great focus! Now take care of yourself",
                    "Hyperfocus detected - time for basics",
                    "Amazing work. Body break needed!"
                ]
            },
            WearableNudgeType.TRANSITION_WARNING: {
                "title": "🔄 Transition coming",
                "messages": [
                    "10 min until your next thing",
                    "Start wrapping up this task",
                    "Transition warning: prepare to switch",
                    "Almost time to move on"
                ]
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize the Pixel Watch integration."""
        try:
            if not await self.ha_client.initialize():
                logger.warning("Home Assistant not available for wearable notifications")
                return False
            
            # Try to detect wearable-capable devices
            await self._detect_wearable_devices()
            
            self.is_initialized = True
            logger.info("✅ Pixel Watch integration initialized via Home Assistant")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Pixel Watch integration: {e}")
            return False
    
    async def _detect_wearable_devices(self):
        """Detect Home Assistant devices that support wearable notifications."""
        try:
            devices = await self.ha_client.get_devices()
            
            # Look for mobile devices with HA Companion app
            for device in devices.get('devices', []):
                device_name = device.get('name', '').lower()
                device_model = device.get('model', '').lower()
                
                if any(keyword in device_name or keyword in device_model 
                       for keyword in ['pixel', 'android', 'mobile', 'phone']):
                    self.wearable_device_id = device.get('id')
                    logger.info(f"🎯 Found potential wearable device: {device.get('name')}")
                    break
                    
        except Exception as e:
            logger.warning(f"Could not detect wearable devices: {e}")
    
    async def send_adhd_nudge(self, 
                             nudge_type: WearableNudgeType,
                             custom_message: str = None,
                             priority: str = "normal") -> bool:
        """Send ADHD-optimized nudge to Pixel Watch via Home Assistant.
        
        Args:
            nudge_type: Type of nudge to send
            custom_message: Override default message
            priority: normal, high, or critical
        """
        if not self.is_initialized:
            logger.warning("Pixel Watch integration not initialized")
            return False
        
        try:
            # Get template for this nudge type
            template = self.nudge_templates.get(nudge_type)
            if not template:
                logger.error(f"Unknown nudge type: {nudge_type}")
                return False
            
            # Choose message
            if custom_message:
                message = custom_message
            else:
                import random
                message = random.choice(template["messages"])
            
            title = template["title"]
            
            # Send via Home Assistant with wearable-optimized settings
            success = await self._send_wearable_notification(
                title=title,
                message=message,
                priority=priority,
                nudge_type=nudge_type
            )
            
            if success:
                # Log successful nudge
                self.nudge_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": nudge_type.value,
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "success": True
                })
                
                logger.info(f"✅ Sent {nudge_type.value} nudge to Pixel Watch: {message[:30]}...")
                return True
            else:
                logger.warning(f"❌ Failed to send {nudge_type.value} nudge")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending wearable nudge: {e}")
            return False
    
    async def _send_wearable_notification(self,
                                        title: str,
                                        message: str,
                                        priority: str = "normal",
                                        nudge_type: WearableNudgeType = None) -> bool:
        """Send optimized notification for wearable devices."""
        try:
            # Enhanced notification payload for wearables
            notification_data = {
                "message": message,
                "title": title,
                "data": {
                    # Android Wear / Wear OS specific
                    "priority": "high" if priority == "high" else "normal",
                    "ttl": 300,  # 5 minutes
                    "channel": "adhd_nudges",
                    
                    # Wearable-specific enhancements
                    "actions": [
                        {
                            "action": "DONE",
                            "title": "✓ Done"
                        },
                        {
                            "action": "REMIND_LATER", 
                            "title": "⏰ Later"
                        }
                    ],
                    
                    # Visual enhancements for watch
                    "color": self._get_nudge_color(nudge_type),
                    "vibrationPattern": self._get_vibration_pattern(nudge_type),
                    
                    # Keep it short for watch screens
                    "subtitle": message if len(message) <= 50 else message[:47] + "...",
                    
                    # Category for proper grouping
                    "tag": f"adhd_{nudge_type.value if nudge_type else 'general'}",
                    "group": "adhd_support"
                }
            }
            
            # Send through Home Assistant notify service
            result = await self.ha_client.session.post(
                f"{self.ha_client.ha_url}/api/services/notify/mobile_app_{self.wearable_device_id or 'pixel_watch'}",
                headers=self.ha_client.headers,
                json=notification_data
            ) if self.wearable_device_id else await self.ha_client.send_notification(message, title)
            
            return result.status == 200 if hasattr(result, 'status') else result
            
        except Exception as e:
            logger.error(f"Failed to send wearable notification: {e}")
            return False
    
    def _get_nudge_color(self, nudge_type: WearableNudgeType) -> str:
        """Get color for nudge type."""
        color_map = {
            WearableNudgeType.GENTLE_REMINDER: "#4CAF50",  # Green
            WearableNudgeType.FOCUS_NUDGE: "#2196F3",      # Blue
            WearableNudgeType.BREAK_REMINDER: "#FF9800",   # Orange
            WearableNudgeType.TASK_COMPLETION: "#4CAF50",  # Green
            WearableNudgeType.ENERGY_CHECK: "#FFEB3B",     # Yellow
            WearableNudgeType.HYPERFOCUS_INTERRUPT: "#F44336",  # Red
            WearableNudgeType.TRANSITION_WARNING: "#9C27B0"     # Purple
        }
        return color_map.get(nudge_type, "#2196F3")
    
    def _get_vibration_pattern(self, nudge_type: WearableNudgeType) -> List[int]:
        """Get vibration pattern for nudge type."""
        patterns = {
            WearableNudgeType.GENTLE_REMINDER: [100, 50, 100],
            WearableNudgeType.FOCUS_NUDGE: [200, 100, 200],
            WearableNudgeType.BREAK_REMINDER: [300, 200, 300],
            WearableNudgeType.HYPERFOCUS_INTERRUPT: [500, 200, 500, 200, 500],
            WearableNudgeType.TRANSITION_WARNING: [100, 100, 100, 100, 100]
        }
        return patterns.get(nudge_type, [200, 100, 200])
    
    async def send_quick_checkin(self) -> bool:
        """Send a quick ADHD check-in nudge."""
        return await self.send_adhd_nudge(
            WearableNudgeType.ENERGY_CHECK,
            "Quick check: How's your focus and energy right now? 🎯⚡"
        )
    
    async def send_hyperfocus_break(self, duration_hours: float) -> bool:
        """Send hyperfocus interruption nudge."""
        return await self.send_adhd_nudge(
            WearableNudgeType.HYPERFOCUS_INTERRUPT,
            f"You've been hyperfocused for {duration_hours:.1f} hours! Time for water, movement, and a mental break. 💧🚶",
            priority="high"
        )
    
    async def send_transition_warning(self, next_activity: str, minutes: int = 10) -> bool:
        """Send transition warning nudge."""
        return await self.send_adhd_nudge(
            WearableNudgeType.TRANSITION_WARNING,
            f"{minutes} min until: {next_activity}. Start wrapping up! 🔄"
        )
    
    async def get_nudge_stats(self) -> Dict[str, Any]:
        """Get statistics about sent nudges."""
        if not self.nudge_history:
            return {"total_nudges": 0, "success_rate": 0}
        
        total = len(self.nudge_history)
        successful = sum(1 for nudge in self.nudge_history if nudge["success"])
        
        # Group by type
        type_counts = {}
        for nudge in self.nudge_history:
            nudge_type = nudge["type"]
            type_counts[nudge_type] = type_counts.get(nudge_type, 0) + 1
        
        return {
            "total_nudges": total,
            "successful_nudges": successful,
            "success_rate": successful / total if total > 0 else 0,
            "nudge_types": type_counts,
            "last_nudge": self.nudge_history[-1] if self.nudge_history else None,
            "wearable_connected": self.is_initialized,
            "device_id": self.wearable_device_id
        }

# Global instance for easy access
pixel_watch_nudges = None

async def initialize_pixel_watch() -> PixelWatchNudgeSystem:
    """Initialize global Pixel Watch integration."""
    global pixel_watch_nudges
    
    if pixel_watch_nudges is None:
        pixel_watch_nudges = PixelWatchNudgeSystem()
        await pixel_watch_nudges.initialize()
    
    return pixel_watch_nudges