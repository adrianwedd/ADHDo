"""
Google Nest Tool - MCP Implementation

ADHD-optimized smart home integration for Nest Hub Max and Nest Mini devices.
Provides ambient nudges, visual dashboards, and environmental ADHD support.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

import structlog
import aiohttp
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from mcp_client.models import (
    Tool, ToolConfig, ToolResult, ToolError, ToolType, 
    AuthType, ToolCapability, ContextFrame
)

logger = structlog.get_logger()


class NudgeType(str, Enum):
    """Types of ADHD nudges for Nest devices."""
    GENTLE_REMINDER = "gentle_reminder"
    FOCUS_START = "focus_start"
    FOCUS_END = "focus_end"
    BREAK_REMINDER = "break_reminder"
    HYPERFOCUS_ALERT = "hyperfocus_alert"
    TASK_CELEBRATION = "task_celebration"
    TRANSITION_WARNING = "transition_warning"
    OVERWHELM_SUPPORT = "overwhelm_support"
    SLEEP_TRANSITION = "sleep_transition"
    WAKE_UP_ROUTINE = "wake_up_routine"


class DeviceType(str, Enum):
    """Types of Nest devices."""
    HUB_MAX = "hub_max"
    HUB = "hub"
    MINI = "mini"
    AUDIO = "audio"
    DISPLAY = "display"


class FocusState(str, Enum):
    """ADHD focus states for ambient indication."""
    FOCUS = "focus"          # Deep work mode
    BREAK = "break"          # Scheduled break
    TRANSITION = "transition" # Between tasks
    OVERWHELM = "overwhelm"   # High stress/cognitive load
    CELEBRATION = "celebration" # Task completion
    SLEEP = "sleep"          # Wind down/sleep prep


class NestDevice:
    """Represents a Google Nest device."""
    
    def __init__(self, device_data: Dict[str, Any]):
        self.device_id = device_data.get('id')
        self.name = device_data.get('name', 'Unknown Device')
        self.room = device_data.get('room', 'Unknown Room')
        self.device_type = self._determine_device_type(device_data)
        self.capabilities = device_data.get('capabilities', [])
        self.is_online = device_data.get('online', False)
        
        # ADHD-specific settings
        self.nudge_enabled = True
        self.max_nudge_frequency = 4  # Max nudges per hour
        self.last_nudge_time = None
        self.preferred_nudge_types = []
        self.quiet_hours = {'start': '22:00', 'end': '07:00'}
        
    def _determine_device_type(self, device_data: Dict[str, Any]) -> DeviceType:
        """Determine device type from device data."""
        model = device_data.get('model', '').lower()
        capabilities = device_data.get('capabilities', [])
        
        if 'display' in capabilities and 'camera' in capabilities:
            return DeviceType.HUB_MAX
        elif 'display' in capabilities:
            return DeviceType.HUB
        elif 'speaker' in capabilities:
            return DeviceType.MINI
        else:
            return DeviceType.AUDIO
    
    def can_send_nudge(self) -> bool:
        """Check if device can receive nudges right now."""
        if not self.nudge_enabled or not self.is_online:
            return False
        
        # Check quiet hours
        now = datetime.now().time()
        quiet_start = datetime.strptime(self.quiet_hours['start'], '%H:%M').time()
        quiet_end = datetime.strptime(self.quiet_hours['end'], '%H:%M').time()
        
        if quiet_start <= now <= quiet_end or now <= quiet_end:
            return False
        
        # Check frequency limits
        if self.last_nudge_time:
            time_since_last = datetime.now() - self.last_nudge_time
            if time_since_last < timedelta(minutes=15):  # Min 15 min between nudges
                return False
        
        return True
    
    def has_capability(self, capability: str) -> bool:
        """Check if device has a specific capability."""
        return capability in self.capabilities


class NestTool:
    """Google Nest integration tool for ADHD smart home support."""
    
    def __init__(self, user_id: str):
        """Initialize Nest tool."""
        self.user_id = user_id
        self.credentials = None
        self.devices: Dict[str, NestDevice] = {}
        self.room_mappings: Dict[str, str] = {}  # room_name -> primary_device_id
        
        # ADHD nudge engine
        self.active_focus_mode = False
        self.current_focus_state = FocusState.TRANSITION
        self.nudge_queue = []
        self.celebration_sounds = [
            "Great job! Task completed! 🎉",
            "Way to go! You're crushing it! ⭐",
            "Awesome work! Keep it up! 💪",
            "Fantastic! Another win! 🏆"
        ]
        
        # Audio assets for different nudge types
        self.nudge_audio = {
            NudgeType.GENTLE_REMINDER: "Gentle chime with soft message",
            NudgeType.FOCUS_START: "Calming bell - Focus time beginning",
            NudgeType.FOCUS_END: "Satisfying chime - Focus session complete",
            NudgeType.BREAK_REMINDER: "Friendly tone - Time for a break",
            NudgeType.HYPERFOCUS_ALERT: "Gentle attention sound - Hyperfocus detected",
            NudgeType.TASK_CELEBRATION: "Happy celebration sound",
            NudgeType.TRANSITION_WARNING: "Soft preparation tone",
            NudgeType.OVERWHELM_SUPPORT: "Calming breathing guide",
            NudgeType.SLEEP_TRANSITION: "Peaceful wind-down sounds",
            NudgeType.WAKE_UP_ROUTINE: "Energizing morning sounds"
        }
    
    def get_tool_config(self) -> ToolConfig:
        """Get tool configuration for MCP registration."""
        return ToolConfig(
            tool_id="google_nest",
            name="Google Nest Smart Home",
            description="ADHD-optimized smart home integration with Nest Hub Max and Nest Mini for ambient nudges, focus support, and environmental awareness.",
            tool_type=ToolType.SMART_HOME,
            version="1.0.0",
            auth_type=AuthType.OAUTH2,
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.EXECUTE,
                ToolCapability.REALTIME
            ],
            supported_operations=[
                "discover_devices",
                "send_nudge",
                "set_focus_mode",
                "display_dashboard", 
                "set_ambient_mode",
                "send_celebration",
                "start_focus_session",
                "end_focus_session",
                "emergency_calm",
                "room_announcement",
                "set_sleep_mode",
                "morning_routine"
            ],
            cognitive_load=0.2,  # Low cognitive load - ambient support
            adhd_friendly=True,
            focus_safe=True,  # Ambient support doesn't break focus
            tags=["smart_home", "nudges", "ambient", "adhd", "nest", "google"],
            priority=9
        )
    
    async def initialize(self, credentials_dict: Dict[str, Any]) -> bool:
        """Initialize Nest tool with credentials."""
        try:
            # Create credentials from dict
            self.credentials = Credentials.from_authorized_user_info(credentials_dict)
            
            # Discover devices
            await self.discover_devices()
            
            logger.info("Nest tool initialized", 
                       user_id=self.user_id,
                       device_count=len(self.devices))
            
            return True
            
        except Exception as e:
            logger.error("Nest initialization failed", 
                        user_id=self.user_id, 
                        error=str(e))
            return False
    
    async def invoke(
        self,
        operation: str,
        parameters: Dict[str, Any],
        context: Optional[ContextFrame] = None
    ) -> ToolResult:
        """Invoke a Nest operation."""
        try:
            # Route to appropriate method
            if operation == "discover_devices":
                return await self._discover_devices(parameters, context)
            elif operation == "send_nudge":
                return await self._send_nudge(parameters, context)
            elif operation == "set_focus_mode":
                return await self._set_focus_mode(parameters, context)
            elif operation == "display_dashboard":
                return await self._display_dashboard(parameters, context)
            elif operation == "set_ambient_mode":
                return await self._set_ambient_mode(parameters, context)
            elif operation == "send_celebration":
                return await self._send_celebration(parameters, context)
            elif operation == "start_focus_session":
                return await self._start_focus_session(parameters, context)
            elif operation == "end_focus_session":
                return await self._end_focus_session(parameters, context)
            elif operation == "emergency_calm":
                return await self._emergency_calm(parameters, context)
            elif operation == "room_announcement":
                return await self._room_announcement(parameters, context)
            elif operation == "set_sleep_mode":
                return await self._set_sleep_mode(parameters, context)
            elif operation == "morning_routine":
                return await self._morning_routine(parameters, context)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown operation: {operation}"
                )
            
        except Exception as e:
            logger.error("Nest operation failed", 
                        operation=operation, 
                        error=str(e))
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    # Core Nest Operations
    
    async def _discover_devices(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Discover and map Nest devices."""
        try:
            await self.discover_devices()
            
            devices_info = []
            for device in self.devices.values():
                devices_info.append({
                    'device_id': device.device_id,
                    'name': device.name,
                    'room': device.room,
                    'type': device.device_type.value,
                    'online': device.is_online,
                    'capabilities': device.capabilities,
                    'nudge_enabled': device.nudge_enabled,
                    'can_send_nudge': device.can_send_nudge()
                })
            
            return ToolResult(
                success=True,
                data={
                    'devices': devices_info,
                    'total_devices': len(devices_info),
                    'online_devices': len([d for d in devices_info if d['online']]),
                    'rooms': list(set(d['room'] for d in devices_info)),
                    'room_mappings': self.room_mappings
                },
                message=f"Discovered {len(devices_info)} Nest devices across {len(set(d['room'] for d in devices_info))} rooms",
                cognitive_load_impact=0.1
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Device discovery failed: {str(e)}"
            )
    
    async def _send_nudge(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Send an ADHD-optimized nudge to Nest device(s)."""
        try:
            nudge_type = parameters.get('nudge_type', NudgeType.GENTLE_REMINDER)
            message = parameters.get('message', '')
            room = parameters.get('room')
            device_id = parameters.get('device_id')
            urgency = parameters.get('urgency', 'normal')  # gentle, normal, urgent
            
            # Determine target devices
            target_devices = []
            
            if device_id:
                if device_id in self.devices:
                    target_devices = [self.devices[device_id]]
            elif room:
                target_devices = [d for d in self.devices.values() if d.room.lower() == room.lower()]
            else:
                # Send to all appropriate devices based on nudge type
                target_devices = self._select_devices_for_nudge(nudge_type, context)
            
            if not target_devices:
                return ToolResult(
                    success=False,
                    error="No suitable devices found for nudge"
                )
            
            # Send nudges
            results = []
            for device in target_devices:
                if device.can_send_nudge():
                    result = await self._send_device_nudge(device, nudge_type, message, urgency)
                    results.append({
                        'device_id': device.device_id,
                        'device_name': device.name,
                        'room': device.room,
                        'success': result
                    })
                    
                    if result:
                        device.last_nudge_time = datetime.now()
            
            successful_nudges = len([r for r in results if r['success']])
            
            return ToolResult(
                success=successful_nudges > 0,
                data={
                    'nudges_sent': successful_nudges,
                    'total_devices': len(target_devices),
                    'results': results,
                    'nudge_type': nudge_type,
                    'message': message
                },
                message=f"Sent {nudge_type} nudge to {successful_nudges} device(s)",
                cognitive_load_impact=0.1,
                follow_up_suggested=False
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Nudge sending failed: {str(e)}"
            )
    
    async def _set_focus_mode(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Set ADHD focus mode across Nest devices."""
        try:
            focus_state = parameters.get('focus_state', FocusState.FOCUS)
            duration_minutes = parameters.get('duration_minutes', 25)  # Default Pomodoro
            room = parameters.get('room')
            
            self.current_focus_state = FocusState(focus_state)
            self.active_focus_mode = focus_state == FocusState.FOCUS
            
            # Determine affected devices
            if room:
                devices = [d for d in self.devices.values() if d.room.lower() == room.lower()]
            else:
                devices = list(self.devices.values())
            
            # Set ambient mode on all devices
            results = []
            for device in devices:
                if device.is_online:
                    result = await self._set_device_ambient(device, focus_state, duration_minutes)
                    results.append({
                        'device_id': device.device_id,
                        'device_name': device.name,
                        'room': device.room,
                        'success': result
                    })
            
            # Schedule focus end reminder if needed
            if focus_state == FocusState.FOCUS and duration_minutes:
                asyncio.create_task(
                    self._schedule_focus_end_reminder(duration_minutes)
                )
            
            successful_updates = len([r for r in results if r['success']])
            
            return ToolResult(
                success=successful_updates > 0,
                data={
                    'focus_state': focus_state,
                    'duration_minutes': duration_minutes,
                    'devices_updated': successful_updates,
                    'results': results,
                    'focus_end_scheduled': focus_state == FocusState.FOCUS and duration_minutes > 0
                },
                message=f"Set {focus_state} mode on {successful_updates} device(s)" + 
                        (f" for {duration_minutes} minutes" if duration_minutes else ""),
                cognitive_load_impact=0.15
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Focus mode setting failed: {str(e)}"
            )
    
    async def _send_celebration(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Send celebration for task completion."""
        try:
            task_name = parameters.get('task_name', 'task')
            celebration_level = parameters.get('level', 'normal')  # gentle, normal, big
            custom_message = parameters.get('message')
            
            # Generate celebration message
            if custom_message:
                message = custom_message
            else:
                import random
                base_message = random.choice(self.celebration_sounds)
                message = f"{base_message} You completed: {task_name}"
            
            # Send to appropriate devices (prefer Hub Max for visual celebration)
            hub_devices = [d for d in self.devices.values() 
                          if d.device_type == DeviceType.HUB_MAX and d.is_online]
            
            if not hub_devices:
                hub_devices = [d for d in self.devices.values() 
                              if d.is_online and d.has_capability('speaker')]
            
            if not hub_devices:
                return ToolResult(
                    success=False,
                    error="No available devices for celebration"
                )
            
            # Send celebration
            results = []
            for device in hub_devices[:2]:  # Limit to 2 devices max
                success = await self._send_celebration_to_device(
                    device, message, celebration_level
                )
                results.append({
                    'device_id': device.device_id,
                    'device_name': device.name,
                    'room': device.room,
                    'success': success
                })
            
            return ToolResult(
                success=True,
                data={
                    'task_name': task_name,
                    'message': message,
                    'celebration_level': celebration_level,
                    'devices_celebrated': len([r for r in results if r['success']]),
                    'results': results
                },
                message=f"🎉 Celebrated completion of '{task_name}' on {len([r for r in results if r['success']])} device(s)",
                cognitive_load_impact=0.05,
                follow_up_suggested=False
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Celebration failed: {str(e)}"
            )
    
    async def _emergency_calm(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Emergency calm mode for overwhelm situations."""
        try:
            calm_type = parameters.get('calm_type', 'breathing')  # breathing, grounding, distraction
            duration_minutes = parameters.get('duration_minutes', 5)
            
            # Find best device for calm session (prefer Hub Max)
            calm_device = None
            for device in self.devices.values():
                if device.device_type == DeviceType.HUB_MAX and device.is_online:
                    calm_device = device
                    break
            
            if not calm_device:
                for device in self.devices.values():
                    if device.is_online and device.has_capability('speaker'):
                        calm_device = device
                        break
            
            if not calm_device:
                return ToolResult(
                    success=False,
                    error="No available device for calm session"
                )
            
            # Start calm session
            success = await self._start_calm_session(calm_device, calm_type, duration_minutes)
            
            if success:
                # Set all other devices to quiet mode
                for device in self.devices.values():
                    if device != calm_device and device.is_online:
                        await self._set_device_quiet_mode(device, duration_minutes)
            
            return ToolResult(
                success=success,
                data={
                    'calm_type': calm_type,
                    'duration_minutes': duration_minutes,
                    'calm_device': {
                        'device_id': calm_device.device_id,
                        'name': calm_device.name,
                        'room': calm_device.room
                    }
                },
                message=f"Started {calm_type} calm session for {duration_minutes} minutes on {calm_device.name}",
                cognitive_load_impact=-0.3,  # Negative = reduces cognitive load
                follow_up_suggested=False
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Emergency calm failed: {str(e)}"
            )
    
    # Helper Methods
    
    async def discover_devices(self):
        """Discover available Nest devices."""
        # In a real implementation, this would use the Google Nest API
        # For now, we'll simulate device discovery
        
        # Simulate discovered devices
        mock_devices = [
            {
                'id': 'nest_hub_max_office',
                'name': 'Office Hub Max',
                'room': 'Office',
                'model': 'Nest Hub Max',
                'capabilities': ['display', 'speaker', 'camera'],
                'online': True
            },
            {
                'id': 'nest_mini_kitchen',
                'name': 'Kitchen Mini',
                'room': 'Kitchen', 
                'model': 'Nest Mini',
                'capabilities': ['speaker'],
                'online': True
            },
            {
                'id': 'nest_mini_bedroom',
                'name': 'Bedroom Mini',
                'room': 'Bedroom',
                'model': 'Nest Mini', 
                'capabilities': ['speaker'],
                'online': True
            }
        ]
        
        # Create device objects
        self.devices = {}
        for device_data in mock_devices:
            device = NestDevice(device_data)
            self.devices[device.device_id] = device
            
            # Set up room mapping (primary device per room)
            if device.room not in self.room_mappings:
                self.room_mappings[device.room] = device.device_id
    
    def _select_devices_for_nudge(self, nudge_type: NudgeType, context: Optional[ContextFrame]) -> List[NestDevice]:
        """Select appropriate devices for a nudge type."""
        available_devices = [d for d in self.devices.values() if d.can_send_nudge()]
        
        if nudge_type == NudgeType.SLEEP_TRANSITION:
            # Bedroom devices only
            return [d for d in available_devices if 'bedroom' in d.room.lower()]
        elif nudge_type == NudgeType.WAKE_UP_ROUTINE:
            # Bedroom devices only
            return [d for d in available_devices if 'bedroom' in d.room.lower()]
        elif nudge_type in [NudgeType.FOCUS_START, NudgeType.FOCUS_END]:
            # Office/work devices preferred
            work_devices = [d for d in available_devices if 'office' in d.room.lower() or 'study' in d.room.lower()]
            return work_devices if work_devices else available_devices[:1]
        elif nudge_type == NudgeType.BREAK_REMINDER:
            # Multiple rooms for movement
            return available_devices
        else:
            # Default: primary device from current room or office
            if context and hasattr(context, 'location') and context.location:
                room_devices = [d for d in available_devices if context.location.lower() in d.room.lower()]
                if room_devices:
                    return room_devices[:1]
            
            # Fallback to office or first available
            office_devices = [d for d in available_devices if 'office' in d.room.lower()]
            return office_devices[:1] if office_devices else available_devices[:1]
    
    async def _send_device_nudge(self, device: NestDevice, nudge_type: NudgeType, message: str, urgency: str) -> bool:
        """Send nudge to a specific device."""
        try:
            # Construct nudge content
            audio_cue = self.nudge_audio.get(nudge_type, "Gentle notification")
            full_message = f"{audio_cue}. {message}" if message else audio_cue
            
            # In a real implementation, this would use Google Assistant API
            logger.info("Sending nudge to device", 
                       device_id=device.device_id,
                       device_name=device.name,
                       room=device.room,
                       nudge_type=nudge_type,
                       message=full_message,
                       urgency=urgency)
            
            # Simulate successful nudge
            return True
            
        except Exception as e:
            logger.error("Failed to send device nudge", 
                        device_id=device.device_id,
                        error=str(e))
            return False
    
    async def _set_device_ambient(self, device: NestDevice, focus_state: FocusState, duration_minutes: int) -> bool:
        """Set ambient mode on a device based on focus state."""
        try:
            # Different ambient settings based on device type and focus state
            if device.device_type == DeviceType.HUB_MAX:
                # Visual ambient mode on Hub Max
                ambient_config = self._get_visual_ambient_config(focus_state)
            else:
                # Audio ambient mode on speakers
                ambient_config = self._get_audio_ambient_config(focus_state)
            
            logger.info("Setting ambient mode", 
                       device_id=device.device_id,
                       focus_state=focus_state,
                       duration=duration_minutes,
                       config=ambient_config)
            
            # Simulate successful ambient setting
            return True
            
        except Exception as e:
            logger.error("Failed to set device ambient", 
                        device_id=device.device_id,
                        error=str(e))
            return False
    
    def _get_visual_ambient_config(self, focus_state: FocusState) -> Dict[str, Any]:
        """Get visual ambient configuration for Hub Max."""
        configs = {
            FocusState.FOCUS: {
                'background_color': '#2E7D32',  # Calming green
                'brightness': 0.6,
                'display_timer': True,
                'show_notifications': False
            },
            FocusState.BREAK: {
                'background_color': '#FF9800',  # Energizing orange
                'brightness': 0.8,
                'display_timer': True,
                'show_notifications': True
            },
            FocusState.TRANSITION: {
                'background_color': '#1976D2',  # Neutral blue
                'brightness': 0.7,
                'display_timer': False,
                'show_notifications': True
            },
            FocusState.OVERWHELM: {
                'background_color': '#E53935',  # Alert red
                'brightness': 0.4,
                'display_timer': False,
                'show_notifications': False
            },
            FocusState.CELEBRATION: {
                'background_color': '#FFD700',  # Gold
                'brightness': 1.0,
                'display_timer': False,
                'show_notifications': True
            }
        }
        
        return configs.get(focus_state, configs[FocusState.TRANSITION])
    
    def _get_audio_ambient_config(self, focus_state: FocusState) -> Dict[str, Any]:
        """Get audio ambient configuration for speakers."""
        configs = {
            FocusState.FOCUS: {
                'ambient_sound': 'forest_sounds',
                'volume': 0.3,
                'duration': 'session'
            },
            FocusState.BREAK: {
                'ambient_sound': 'gentle_music',
                'volume': 0.5,
                'duration': 'break_length'
            },
            FocusState.TRANSITION: {
                'ambient_sound': None,
                'volume': 0.4,
                'duration': None
            },
            FocusState.OVERWHELM: {
                'ambient_sound': 'breathing_guide',
                'volume': 0.4,
                'duration': '5_minutes'
            },
            FocusState.CELEBRATION: {
                'ambient_sound': 'success_chime',
                'volume': 0.6,
                'duration': '30_seconds'
            }
        }
        
        return configs.get(focus_state, configs[FocusState.TRANSITION])
    
    async def _schedule_focus_end_reminder(self, duration_minutes: int):
        """Schedule focus session end reminder."""
        await asyncio.sleep(duration_minutes * 60)
        
        # Send focus end nudge
        await self._send_nudge({
            'nudge_type': NudgeType.FOCUS_END,
            'message': f"Focus session complete! Great work for {duration_minutes} minutes.",
            'urgency': 'gentle'
        }, None)
    
    async def _send_celebration_to_device(self, device: NestDevice, message: str, level: str) -> bool:
        """Send celebration to specific device."""
        try:
            if device.device_type == DeviceType.HUB_MAX:
                # Visual celebration on Hub Max
                celebration_config = {
                    'animation': 'celebration',
                    'message': message,
                    'duration': 5 if level == 'big' else 3,
                    'colors': ['#FFD700', '#FF6B35', '#F7931E']  # Gold, orange, amber
                }
            else:
                # Audio celebration on speakers
                celebration_config = {
                    'sound': 'celebration_chime',
                    'message': message,
                    'volume': 0.7 if level == 'big' else 0.5
                }
            
            logger.info("Sending celebration", 
                       device_id=device.device_id,
                       message=message,
                       level=level,
                       config=celebration_config)
            
            return True
            
        except Exception as e:
            logger.error("Celebration failed", device_id=device.device_id, error=str(e))
            return False
    
    async def _start_calm_session(self, device: NestDevice, calm_type: str, duration_minutes: int) -> bool:
        """Start calm session on device."""
        try:
            calm_sessions = {
                'breathing': {
                    'content': 'Guided breathing exercise',
                    'audio': 'calm_breathing_guide',
                    'visual': 'breathing_animation'
                },
                'grounding': {
                    'content': '5-4-3-2-1 grounding technique',
                    'audio': 'grounding_guide',
                    'visual': 'grounding_prompts'
                },
                'distraction': {
                    'content': 'Gentle nature sounds and visuals',
                    'audio': 'nature_sounds',
                    'visual': 'nature_scenes'
                }
            }
            
            session_config = calm_sessions.get(calm_type, calm_sessions['breathing'])
            
            logger.info("Starting calm session", 
                       device_id=device.device_id,
                       calm_type=calm_type,
                       duration=duration_minutes,
                       config=session_config)
            
            return True
            
        except Exception as e:
            logger.error("Calm session failed", device_id=device.device_id, error=str(e))
            return False
    
    async def _set_device_quiet_mode(self, device: NestDevice, duration_minutes: int) -> bool:
        """Set device to quiet mode."""
        try:
            logger.info("Setting quiet mode", 
                       device_id=device.device_id,
                       duration=duration_minutes)
            
            # In real implementation, would disable notifications and lower volume
            return True
            
        except Exception as e:
            logger.error("Failed to set quiet mode", device_id=device.device_id, error=str(e))
            return False
    
    async def _apply_ambient_to_device(self, device: NestDevice, ambient_mode: str, config: Dict[str, Any]) -> bool:
        """Apply ambient configuration to a device."""
        try:
            logger.info("Applying ambient mode",
                       device_id=device.device_id,
                       ambient_mode=ambient_mode,
                       config=config)
            
            # In real implementation, would apply ambient settings via Google Assistant API
            return True
            
        except Exception as e:
            logger.error("Failed to apply ambient mode", device_id=device.device_id, error=str(e))
            return False
    
    async def _schedule_break_reminder(self, focus_minutes: int, break_minutes: int, session_name: str):
        """Schedule break reminder after focus session."""
        await asyncio.sleep(focus_minutes * 60)
        
        # Send break nudge
        await self._send_nudge({
            'nudge_type': NudgeType.BREAK_REMINDER,
            'message': f"Great focus work! Time for a {break_minutes} minute break. Move your body! 🚶",
            'urgency': 'gentle'
        }, None)
        
        # Schedule focus end after break
        if break_minutes > 0:
            await asyncio.sleep(break_minutes * 60)
            await self._send_nudge({
                'nudge_type': NudgeType.FOCUS_START,
                'message': "Break time over. Ready for another focus session? You're doing great! 💪",
                'urgency': 'gentle'
            }, None)
    
    async def _send_room_announcement_to_device(self, device: NestDevice, message: str, announcement_type: str, config: Dict[str, Any]) -> bool:
        """Send announcement to specific device."""
        try:
            logger.info("Sending room announcement",
                       device_id=device.device_id,
                       message=message,
                       type=announcement_type,
                       config=config)
            
            # In real implementation, would use Google Assistant API for announcements
            return True
            
        except Exception as e:
            logger.error("Failed to send room announcement", device_id=device.device_id, error=str(e))
            return False
    
    async def _apply_sleep_config_to_device(self, device: NestDevice, sleep_phase: str, config: Dict[str, Any]) -> bool:
        """Apply sleep configuration to device."""
        try:
            logger.info("Applying sleep config",
                       device_id=device.device_id,
                       sleep_phase=sleep_phase,
                       config=config)
            
            # In real implementation, would configure device for sleep mode
            return True
            
        except Exception as e:
            logger.error("Failed to apply sleep config", device_id=device.device_id, error=str(e))
            return False
    
    async def _schedule_sleep_transition(self, wind_down_minutes: int):
        """Schedule transition to sleep mode after wind down."""
        await asyncio.sleep(wind_down_minutes * 60)
        
        # Automatically transition to sleep mode
        await self._set_sleep_mode({
            'sleep_phase': 'sleep',
            'duration_minutes': 0,
            'bedroom_only': True
        }, None)
    
    async def _start_morning_routine_on_device(self, device: NestDevice, routine: Dict[str, Any]) -> bool:
        """Start morning routine on device."""
        try:
            logger.info("Starting morning routine",
                       device_id=device.device_id,
                       routine_type=routine.get('description'))
            
            # Send first morning message
            first_message = routine['messages'][0]
            await self._send_device_nudge(device, NudgeType.WAKE_UP_ROUTINE, first_message, 'gentle')
            
            return True
            
        except Exception as e:
            logger.error("Failed to start morning routine", device_id=device.device_id, error=str(e))
            return False
    
    async def _execute_morning_routine_sequence(self, devices: List[NestDevice], routine: Dict[str, Any], duration_minutes: int):
        """Execute the full morning routine sequence."""
        try:
            lighting_sequence = routine['lighting_sequence']
            messages = routine['messages']
            
            # Execute each step in the lighting sequence
            for i, step in enumerate(lighting_sequence):
                if step['time'] > 0:
                    await asyncio.sleep(step['time'] * 60)  # Convert to seconds
                
                # Apply lighting changes to all devices
                for device in devices:
                    if device.device_type == DeviceType.HUB_MAX:
                        await self._set_device_lighting(device, step['brightness'], step['color'])
                
                # Send message if available
                if i < len(messages):
                    for device in devices:
                        await self._send_device_nudge(device, NudgeType.WAKE_UP_ROUTINE, messages[i], 'gentle')
                        break  # Only send message from one device
            
        except Exception as e:
            logger.error("Morning routine sequence failed", error=str(e))
    
    async def _set_device_lighting(self, device: NestDevice, brightness: float, color: str) -> bool:
        """Set lighting on device."""
        try:
            logger.info("Setting device lighting",
                       device_id=device.device_id,
                       brightness=brightness,
                       color=color)
            
            # In real implementation, would set lighting via Google Assistant API
            return True
            
        except Exception as e:
            logger.error("Failed to set device lighting", device_id=device.device_id, error=str(e))
            return False
    
    # Additional operations implementation
    async def _display_dashboard(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Display ADHD dashboard on Hub Max."""
        try:
            dashboard_type = parameters.get('dashboard_type', 'default')
            duration_minutes = parameters.get('duration_minutes', 0)  # 0 = permanent
            
            # Find Hub Max device
            hub_max = None
            for device in self.devices.values():
                if device.device_type == DeviceType.HUB_MAX and device.is_online:
                    hub_max = device
                    break
            
            if not hub_max:
                return ToolResult(
                    success=False,
                    error="No Hub Max device available for dashboard"
                )
            
            # Dashboard configurations
            dashboards = {
                'default': {
                    'title': 'ADHD Dashboard',
                    'widgets': ['focus_timer', 'task_list', 'energy_level', 'next_break'],
                    'background': '#1976D2'
                },
                'focus': {
                    'title': 'Focus Mode',
                    'widgets': ['focus_timer', 'current_task', 'distractions_blocked'],
                    'background': '#2E7D32'
                },
                'break': {
                    'title': 'Break Time',
                    'widgets': ['break_timer', 'movement_suggestions', 'hydration_reminder'],
                    'background': '#FF9800'
                },
                'overwhelm': {
                    'title': 'Calm Space',
                    'widgets': ['breathing_guide', 'grounding_exercise', 'support_contacts'],
                    'background': '#E53935'
                }
            }
            
            dashboard_config = dashboards.get(dashboard_type, dashboards['default'])
            
            logger.info("Displaying dashboard", 
                       device_id=hub_max.device_id,
                       dashboard_type=dashboard_type,
                       duration=duration_minutes,
                       config=dashboard_config)
            
            return ToolResult(
                success=True,
                data={
                    'dashboard_type': dashboard_type,
                    'device_id': hub_max.device_id,
                    'device_name': hub_max.name,
                    'duration_minutes': duration_minutes,
                    'config': dashboard_config
                },
                message=f"Displayed {dashboard_type} dashboard on {hub_max.name}",
                cognitive_load_impact=0.1
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Dashboard display failed: {str(e)}"
            )
    
    async def _set_ambient_mode(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Set ambient lighting/sound mode."""
        try:
            ambient_mode = parameters.get('ambient_mode', 'neutral')
            room = parameters.get('room')
            duration_minutes = parameters.get('duration_minutes', 0)
            
            # Ambient modes for ADHD support
            ambient_modes = {
                'focus': {
                    'description': 'Calming environment for deep work',
                    'lighting': {'color': '#2E7D32', 'brightness': 0.6},
                    'sound': 'forest_ambience',
                    'notifications': False
                },
                'energy': {
                    'description': 'Energizing environment for motivation',
                    'lighting': {'color': '#FF9800', 'brightness': 0.8},
                    'sound': 'uplifting_instrumental',
                    'notifications': True
                },
                'calm': {
                    'description': 'Relaxing environment for overwhelm',
                    'lighting': {'color': '#9C27B0', 'brightness': 0.4},
                    'sound': 'ocean_waves',
                    'notifications': False
                },
                'neutral': {
                    'description': 'Balanced environment',
                    'lighting': {'color': '#1976D2', 'brightness': 0.7},
                    'sound': None,
                    'notifications': True
                }
            }
            
            mode_config = ambient_modes.get(ambient_mode, ambient_modes['neutral'])
            
            # Determine target devices
            if room:
                devices = [d for d in self.devices.values() if d.room.lower() == room.lower() and d.is_online]
            else:
                devices = [d for d in self.devices.values() if d.is_online]
            
            # Apply ambient mode to devices
            results = []
            for device in devices:
                success = await self._apply_ambient_to_device(device, ambient_mode, mode_config)
                results.append({
                    'device_id': device.device_id,
                    'device_name': device.name,
                    'room': device.room,
                    'success': success
                })
            
            successful_updates = len([r for r in results if r['success']])
            
            return ToolResult(
                success=successful_updates > 0,
                data={
                    'ambient_mode': ambient_mode,
                    'duration_minutes': duration_minutes,
                    'devices_updated': successful_updates,
                    'results': results,
                    'mode_config': mode_config
                },
                message=f"Set {ambient_mode} ambient mode on {successful_updates} device(s)",
                cognitive_load_impact=0.05  # Low impact, ambient changes
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Ambient mode setting failed: {str(e)}"
            )
    
    async def _start_focus_session(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Start a focus session with timer."""
        try:
            duration_minutes = parameters.get('duration_minutes', 25)  # Default Pomodoro
            session_name = parameters.get('session_name', 'Focus Session')
            break_minutes = parameters.get('break_minutes', 5)
            room = parameters.get('room')
            
            # Set focus mode on devices
            focus_result = await self._set_focus_mode({
                'focus_state': FocusState.FOCUS,
                'duration_minutes': duration_minutes,
                'room': room
            }, context)
            
            if not focus_result.success:
                return focus_result
            
            # Schedule break reminder
            asyncio.create_task(
                self._schedule_break_reminder(duration_minutes, break_minutes, session_name)
            )
            
            # Send start nudge
            await self._send_nudge({
                'nudge_type': NudgeType.FOCUS_START,
                'message': f"Starting {session_name} for {duration_minutes} minutes. You've got this! 🎯",
                'room': room,
                'urgency': 'gentle'
            }, context)
            
            return ToolResult(
                success=True,
                data={
                    'session_name': session_name,
                    'duration_minutes': duration_minutes,
                    'break_minutes': break_minutes,
                    'room': room,
                    'devices_configured': len(focus_result.data.get('results', [])),
                    'break_scheduled': True,
                    'session_id': f"focus_{int(time.time())}"
                },
                message=f"Started '{session_name}' for {duration_minutes} minutes with {break_minutes} min break",
                cognitive_load_impact=0.2,
                follow_up_suggested=False
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Focus session start failed: {str(e)}"
            )
    
    async def _end_focus_session(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """End current focus session."""
        try:
            session_completed = parameters.get('completed', True)
            session_notes = parameters.get('notes', '')
            celebrate = parameters.get('celebrate', True)
            
            # Set devices to transition mode
            transition_result = await self._set_focus_mode({
                'focus_state': FocusState.TRANSITION,
                'duration_minutes': 0
            }, context)
            
            # Send completion message
            if session_completed and celebrate:
                await self._send_celebration({
                    'task_name': 'Focus Session',
                    'level': 'normal',
                    'message': 'Great focus work! Time for a well-deserved break. 🎉'
                }, context)
            else:
                await self._send_nudge({
                    'nudge_type': NudgeType.FOCUS_END,
                    'message': 'Focus session ended. Take a moment to transition.' if not session_completed else 'Focus session complete!',
                    'urgency': 'gentle'
                }, context)
            
            # Clear active focus mode
            self.active_focus_mode = False
            self.current_focus_state = FocusState.TRANSITION
            
            return ToolResult(
                success=True,
                data={
                    'session_completed': session_completed,
                    'session_notes': session_notes,
                    'celebrated': session_completed and celebrate,
                    'devices_updated': len(transition_result.data.get('results', [])),
                    'next_recommendation': 'Take a 5-10 minute break before your next focus session'
                },
                message=f"Focus session {'completed' if session_completed else 'ended'} - devices returned to neutral mode",
                cognitive_load_impact=0.1
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Focus session end failed: {str(e)}"
            )
    
    async def _room_announcement(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Make announcement to specific room."""
        try:
            room = parameters.get('room')
            message = parameters.get('message', '')
            announcement_type = parameters.get('type', 'general')  # general, urgent, celebration
            voice_only = parameters.get('voice_only', False)
            
            if not room or not message:
                return ToolResult(
                    success=False,
                    error="Room and message are required for announcements"
                )
            
            # Find devices in the room
            room_devices = [d for d in self.devices.values() 
                           if d.room.lower() == room.lower() and d.is_online]
            
            if not room_devices:
                return ToolResult(
                    success=False,
                    error=f"No available devices found in room: {room}"
                )
            
            # Configure announcement based on type
            announcement_configs = {
                'general': {
                    'volume': 0.6,
                    'tone': 'friendly',
                    'visual': not voice_only
                },
                'urgent': {
                    'volume': 0.8,
                    'tone': 'attention',
                    'visual': True
                },
                'celebration': {
                    'volume': 0.7,
                    'tone': 'cheerful',
                    'visual': True
                }
            }
            
            config = announcement_configs.get(announcement_type, announcement_configs['general'])
            
            # Send announcement to each device
            results = []
            for device in room_devices:
                success = await self._send_room_announcement_to_device(
                    device, message, announcement_type, config
                )
                results.append({
                    'device_id': device.device_id,
                    'device_name': device.name,
                    'device_type': device.device_type.value,
                    'success': success
                })
            
            successful_announcements = len([r for r in results if r['success']])
            
            return ToolResult(
                success=successful_announcements > 0,
                data={
                    'room': room,
                    'message': message,
                    'announcement_type': announcement_type,
                    'devices_announced': successful_announcements,
                    'total_devices': len(room_devices),
                    'results': results,
                    'config': config
                },
                message=f"Announced to {successful_announcements} device(s) in {room}: '{message[:50]}{'...' if len(message) > 50 else ''}",
                cognitive_load_impact=0.1
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Room announcement failed: {str(e)}"
            )
    
    async def _set_sleep_mode(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Set sleep/wind-down mode."""
        try:
            sleep_phase = parameters.get('sleep_phase', 'wind_down')  # wind_down, sleep, wake_prep
            duration_minutes = parameters.get('duration_minutes', 30)
            bedroom_only = parameters.get('bedroom_only', True)
            
            # Sleep configurations for ADHD support
            sleep_configs = {
                'wind_down': {
                    'ambient_mode': 'calm',
                    'lighting': {'color': '#9C27B0', 'brightness': 0.3},
                    'sound': 'rain_sounds',
                    'notifications': False,
                    'description': 'Preparing for sleep with calming environment'
                },
                'sleep': {
                    'ambient_mode': 'sleep',
                    'lighting': {'color': '#000000', 'brightness': 0.1},
                    'sound': 'white_noise',
                    'notifications': False,
                    'description': 'Sleep mode - minimal disruption'
                },
                'wake_prep': {
                    'ambient_mode': 'energy',
                    'lighting': {'color': '#FFC107', 'brightness': 0.7},
                    'sound': 'gentle_birds',
                    'notifications': True,
                    'description': 'Gentle wake-up preparation'
                }
            }
            
            config = sleep_configs.get(sleep_phase, sleep_configs['wind_down'])
            
            # Determine target devices
            if bedroom_only:
                devices = [d for d in self.devices.values() 
                          if 'bedroom' in d.room.lower() and d.is_online]
            else:
                devices = [d for d in self.devices.values() if d.is_online]
            
            if not devices:
                return ToolResult(
                    success=False,
                    error="No available devices for sleep mode"
                )
            
            # Apply sleep configuration
            results = []
            for device in devices:
                success = await self._apply_sleep_config_to_device(device, sleep_phase, config)
                results.append({
                    'device_id': device.device_id,
                    'device_name': device.name,
                    'room': device.room,
                    'success': success
                })
            
            # Schedule wake-up if this is wind_down
            wake_up_scheduled = False
            if sleep_phase == 'wind_down' and duration_minutes:
                asyncio.create_task(
                    self._schedule_sleep_transition(duration_minutes)
                )
                wake_up_scheduled = True
            
            successful_updates = len([r for r in results if r['success']])
            
            return ToolResult(
                success=successful_updates > 0,
                data={
                    'sleep_phase': sleep_phase,
                    'duration_minutes': duration_minutes,
                    'devices_updated': successful_updates,
                    'bedroom_only': bedroom_only,
                    'results': results,
                    'config': config,
                    'wake_up_scheduled': wake_up_scheduled
                },
                message=f"Set {sleep_phase} mode on {successful_updates} device(s) - {config['description']}",
                cognitive_load_impact=0.05,
                follow_up_suggested=False
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Sleep mode setting failed: {str(e)}"
            )
    
    async def _morning_routine(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Execute morning wake-up routine."""
        try:
            routine_type = parameters.get('routine_type', 'gradual')  # gradual, energetic, gentle
            duration_minutes = parameters.get('duration_minutes', 15)
            include_weather = parameters.get('include_weather', True)
            include_schedule = parameters.get('include_schedule', True)
            
            # Morning routine configurations
            routines = {
                'gradual': {
                    'description': 'Gentle wake-up with gradual lighting',
                    'lighting_sequence': [
                        {'time': 0, 'brightness': 0.2, 'color': '#FFC107'},
                        {'time': 5, 'brightness': 0.5, 'color': '#FF9800'},
                        {'time': 10, 'brightness': 0.8, 'color': '#FFEB3B'}
                    ],
                    'sounds': ['gentle_chimes', 'bird_sounds', 'soft_music'],
                    'messages': [
                        'Good morning! Starting your gentle wake-up.',
                        'Gradually increasing brightness...',
                        'Ready to start your day! You\'ve got this! ☀️'
                    ]
                },
                'energetic': {
                    'description': 'Energizing wake-up for motivation',
                    'lighting_sequence': [
                        {'time': 0, 'brightness': 0.6, 'color': '#FF5722'},
                        {'time': 3, 'brightness': 0.9, 'color': '#FF9800'}
                    ],
                    'sounds': ['upbeat_music', 'motivation_sounds'],
                    'messages': [
                        'Rise and shine! Time to conquer the day! 🚀',
                        'You\'re amazing and today is full of possibilities!'
                    ]
                },
                'gentle': {
                    'description': 'Extra gentle for ADHD overwhelm',
                    'lighting_sequence': [
                        {'time': 0, 'brightness': 0.1, 'color': '#E1BEE7'},
                        {'time': 8, 'brightness': 0.3, 'color': '#C8E6C9'},
                        {'time': 12, 'brightness': 0.6, 'color': '#DCEDC8'}
                    ],
                    'sounds': ['soft_nature', 'calm_instrumental'],
                    'messages': [
                        'Good morning. Take your time waking up.',
                        'No rush - let\'s ease into the day gently.',
                        'You\'re ready when you\'re ready. 🌱'
                    ]
                }
            }
            
            routine = routines.get(routine_type, routines['gradual'])
            
            # Find bedroom devices for routine
            bedroom_devices = [d for d in self.devices.values() 
                              if 'bedroom' in d.room.lower() and d.is_online]
            
            if not bedroom_devices:
                return ToolResult(
                    success=False,
                    error="No bedroom devices available for morning routine"
                )
            
            # Execute morning routine sequence
            routine_results = []
            
            # Start routine
            for device in bedroom_devices:
                success = await self._start_morning_routine_on_device(device, routine)
                routine_results.append({
                    'device_id': device.device_id,
                    'device_name': device.name,
                    'success': success
                })
            
            # Schedule routine steps
            asyncio.create_task(
                self._execute_morning_routine_sequence(bedroom_devices, routine, duration_minutes)
            )
            
            successful_starts = len([r for r in routine_results if r['success']])
            
            return ToolResult(
                success=successful_starts > 0,
                data={
                    'routine_type': routine_type,
                    'duration_minutes': duration_minutes,
                    'devices_started': successful_starts,
                    'routine_description': routine['description'],
                    'include_weather': include_weather,
                    'include_schedule': include_schedule,
                    'results': routine_results,
                    'total_steps': len(routine['lighting_sequence'])
                },
                message=f"Started {routine_type} morning routine on {successful_starts} device(s) - {routine['description']}",
                cognitive_load_impact=0.15
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Morning routine failed: {str(e)}"
            )