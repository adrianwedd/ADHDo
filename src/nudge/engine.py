"""
Nudge Engine - Multi-modal nudging system for ADHD executive function support.

Supports escalating nudges through multiple channels:
- Telegram messages
- Home Assistant TTS/speakers
- Google Nest displays and speakers
- Environmental changes (lights, music, etc.)
- Visual displays and notifications
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
import structlog
from telegram import Bot
from telegram.error import TelegramError

from mcp_server.config import settings
from mcp_server.models import NudgeTier, NudgeAttempt, User, Task

logger = structlog.get_logger()


class NudgeMethod:
    """Base class for nudge delivery methods."""
    
    async def send_nudge(
        self, 
        user: User, 
        message: str, 
        tier: NudgeTier,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a nudge. Returns True if successful."""
        raise NotImplementedError


class TelegramNudger(NudgeMethod):
    """Telegram bot nudging."""
    
    def __init__(self):
        if settings.telegram_bot_token:
            self.bot = Bot(token=settings.telegram_bot_token)
        else:
            self.bot = None
            logger.warning("Telegram bot token not configured")
    
    async def send_nudge(
        self, 
        user: User, 
        message: str, 
        tier: NudgeTier,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send Telegram message nudge."""
        if not self.bot or not user.telegram_chat_id:
            return False
        
        try:
            # Add tier-appropriate formatting
            if tier == NudgeTier.GENTLE:
                formatted_message = f"🌱 {message}"
            elif tier == NudgeTier.SARCASTIC:
                formatted_message = f"🙄 {message}"
            else:  # SERGEANT
                formatted_message = f"⚡ {message.upper()}"
            
            await self.bot.send_message(
                chat_id=user.telegram_chat_id,
                text=formatted_message,
                parse_mode="HTML"
            )
            
            logger.info(
                "Sent Telegram nudge",
                user_id=user.user_id,
                tier=tier.name,
                chat_id=user.telegram_chat_id
            )
            return True
            
        except TelegramError as e:
            logger.error(
                "Failed to send Telegram nudge",
                user_id=user.user_id,
                error=str(e)
            )
            return False


class HomeAssistantNudger(NudgeMethod):
    """Home Assistant integration for environmental nudging."""
    
    def __init__(self):
        self.base_url = settings.home_assistant_url
        self.token = settings.home_assistant_token
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.token}"}
        ) if self.token else None
    
    async def send_nudge(
        self, 
        user: User, 
        message: str, 
        tier: NudgeTier,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send Home Assistant nudge via TTS and environmental changes."""
        if not self.client:
            return False
        
        success = True
        
        # Text-to-speech announcement
        tts_success = await self._send_tts(user, message, tier)
        success = success and tts_success
        
        # Environmental changes based on tier
        env_success = await self._trigger_environment(user, tier, metadata)
        success = success and env_success
        
        return success
    
    async def _send_tts(self, user: User, message: str, tier: NudgeTier) -> bool:
        """Send TTS announcement through Home Assistant speakers."""
        try:
            # Customize voice and delivery based on tier
            tts_data = {
                "entity_id": "media_player.all_speakers",  # or user-specific
                "message": message,
            }
            
            # Tier-specific voice modifications
            if tier == NudgeTier.GENTLE:
                tts_data.update({
                    "options": {
                        "voice": "en-US-Wavenet-C",  # Gentle female voice
                        "speed": 0.9
                    }
                })
            elif tier == NudgeTier.SARCASTIC:
                tts_data.update({
                    "options": {
                        "voice": "en-US-Wavenet-B",  # More assertive
                        "speed": 1.0
                    }
                })
            else:  # SERGEANT
                tts_data.update({
                    "options": {
                        "voice": "en-US-Wavenet-A",  # Authoritative
                        "speed": 1.1,
                        "pitch": "+2st"
                    }
                })
            
            response = await self.client.post(
                f"{self.base_url}/api/services/tts/google_translate_say",
                json=tts_data
            )
            
            if response.status_code == 200:
                logger.info(
                    "Sent Home Assistant TTS nudge",
                    user_id=user.user_id,
                    tier=tier.name
                )
                return True
            else:
                logger.error(
                    "Home Assistant TTS failed",
                    status_code=response.status_code,
                    response=response.text
                )
                return False
                
        except Exception as e:
            logger.error("Home Assistant TTS error", error=str(e))
            return False
    
    async def _trigger_environment(
        self, 
        user: User, 
        tier: NudgeTier,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Trigger environmental changes based on nudge tier."""
        try:
            actions = []
            
            if tier == NudgeTier.GENTLE:
                # Gentle environmental cues
                actions = [
                    # Slightly brighten lights
                    {
                        "service": "light.turn_on",
                        "entity_id": "light.office_lights",
                        "data": {"brightness_pct": 75, "transition": 3}
                    },
                    # Play focus music quietly
                    {
                        "service": "media_player.play_media",
                        "entity_id": "media_player.office_speaker",
                        "data": {
                            "media_content_id": "https://open.spotify.com/playlist/focus",
                            "media_content_type": "music"
                        }
                    }
                ]
            
            elif tier == NudgeTier.SARCASTIC:
                # More noticeable environmental changes
                actions = [
                    # Flash lights briefly
                    {
                        "service": "light.turn_on",
                        "entity_id": "light.office_lights", 
                        "data": {"flash": "short", "color_name": "orange"}
                    },
                    # Change display to show nudge
                    {
                        "service": "notify.living_room_display",
                        "data": {
                            "title": "Task Reminder",
                            "message": "Still working on that thing? 🤔"
                        }
                    }
                ]
            
            else:  # SERGEANT
                # Dramatic environmental intervention
                actions = [
                    # Bright red lights
                    {
                        "service": "light.turn_on",
                        "entity_id": "light.office_lights",
                        "data": {"brightness_pct": 100, "color_name": "red"}
                    },
                    # Stop all entertainment
                    {
                        "service": "media_player.media_stop",
                        "entity_id": "media_player.entertainment_areas"
                    },
                    # Display urgent message
                    {
                        "service": "notify.all_displays",
                        "data": {
                            "title": "FOCUS TIME",
                            "message": "Stop procrastinating. Do the thing. NOW.",
                            "data": {"priority": "high", "sticky": True}
                        }
                    }
                ]
            
            # Execute all actions
            success = True
            for action in actions:
                try:
                    service_path = action["service"].replace(".", "/")
                    response = await self.client.post(
                        f"{self.base_url}/api/services/{service_path}",
                        json={
                            "entity_id": action.get("entity_id"),
                            **action.get("data", {})
                        }
                    )
                    
                    if response.status_code != 200:
                        logger.warning(
                            "Home Assistant action failed",
                            service=action["service"],
                            status_code=response.status_code
                        )
                        success = False
                        
                except Exception as e:
                    logger.error(
                        "Home Assistant action error",
                        service=action["service"],
                        error=str(e)
                    )
                    success = False
            
            return success
            
        except Exception as e:
            logger.error("Home Assistant environment trigger error", error=str(e))
            return False


class GoogleNestNudger(NudgeMethod):
    """Google Nest/Cast device nudging."""
    
    def __init__(self):
        # This would typically use Google Cast SDK or similar
        # For now, we'll route through Home Assistant if available
        self.ha_nudger = HomeAssistantNudger()
    
    async def send_nudge(
        self, 
        user: User, 
        message: str, 
        tier: NudgeTier,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send nudge to Google Nest devices."""
        try:
            # Route through Home Assistant for now
            # TODO: Implement direct Cast SDK integration
            
            # Enhance message for Nest displays
            if tier == NudgeTier.GENTLE:
                display_message = f"💡 Gentle reminder: {message}"
            elif tier == NudgeTier.SARCASTIC:
                display_message = f"🤨 Hey you: {message}"
            else:  # SERGEANT
                display_message = f"🚨 ATTENTION: {message}"
            
            # Send to Nest Hub displays
            nest_actions = [
                {
                    "service": "notify.google_nest_hub",
                    "data": {
                        "title": "Task Nudge",
                        "message": display_message,
                        "data": {
                            "duration": 30 if tier == NudgeTier.SERGEANT else 15,
                            "fontsize": "large" if tier == NudgeTier.SERGEANT else "medium"
                        }
                    }
                }
            ]
            
            # For sergeant level, also interrupt any playing media
            if tier == NudgeTier.SERGEANT:
                nest_actions.append({
                    "service": "media_player.media_pause",
                    "entity_id": "media_player.nest_speakers"
                })
            
            # Execute via Home Assistant
            success = True
            for action in nest_actions:
                try:
                    service_path = action["service"].replace(".", "/")
                    response = await self.ha_nudger.client.post(
                        f"{self.ha_nudger.base_url}/api/services/{service_path}",
                        json={
                            "entity_id": action.get("entity_id"),
                            **action.get("data", {})
                        }
                    ) if self.ha_nudger.client else None
                    
                    if response and response.status_code == 200:
                        logger.info(
                            "Sent Google Nest nudge",
                            user_id=user.user_id,
                            tier=tier.name
                        )
                    else:
                        success = False
                        
                except Exception as e:
                    logger.error("Google Nest action error", error=str(e))
                    success = False
            
            return success
            
        except Exception as e:
            logger.error("Google Nest nudge error", error=str(e))
            return False


class NudgeEngine:
    """
    Central nudging coordinator that manages escalation and multi-modal delivery.
    
    This is the "accountability partner" that makes MCP ADHD Server effective.
    """
    
    def __init__(self):
        self.methods = {
            "telegram": TelegramNudger(),
            "home_assistant": HomeAssistantNudger(),
            "google_nest": GoogleNestNudger(),
        }
        
        # Track active nudge sequences per user
        self.active_nudges: Dict[str, Dict[str, Any]] = {}
    
    async def initiate_nudge_sequence(
        self, 
        user: User, 
        task: Task,
        initial_message: Optional[str] = None
    ) -> None:
        """
        Start a nudge sequence for a task.
        
        This creates a scheduled escalation pattern that will
        progressively increase pressure until the user responds.
        """
        sequence_id = f"{user.user_id}:{task.task_id}"
        
        # Build contextual message if not provided
        if not initial_message:
            initial_message = self._generate_contextual_message(user, task, NudgeTier.GENTLE)
        
        # Initialize nudge sequence
        self.active_nudges[sequence_id] = {
            "user": user,
            "task": task,
            "current_tier": NudgeTier.GENTLE,
            "attempt_count": 0,
            "started_at": datetime.utcnow(),
            "last_nudge": None,
            "next_nudge": datetime.utcnow() + timedelta(seconds=settings.nudge_tier_0_delay)
        }
        
        # Send initial nudge
        await self._send_nudge(user, task, NudgeTier.GENTLE, initial_message)
        
        # Schedule next escalation
        asyncio.create_task(self._schedule_escalation(sequence_id))
        
        logger.info(
            "Initiated nudge sequence",
            user_id=user.user_id,
            task_id=task.task_id,
            sequence_id=sequence_id
        )
    
    async def _schedule_escalation(self, sequence_id: str) -> None:
        """Schedule and execute nudge escalation."""
        while sequence_id in self.active_nudges:
            sequence = self.active_nudges[sequence_id]
            
            # Wait until next nudge time
            now = datetime.utcnow()
            if sequence["next_nudge"] > now:
                wait_seconds = (sequence["next_nudge"] - now).total_seconds()
                await asyncio.sleep(wait_seconds)
            
            # Check if sequence was cancelled
            if sequence_id not in self.active_nudges:
                break
            
            # Escalate tier if needed
            current_tier = sequence["current_tier"]
            attempt_count = sequence["attempt_count"]
            
            if attempt_count >= settings.nudge_max_attempts:
                # Max attempts reached, record abandonment
                await self._record_abandonment(sequence)
                del self.active_nudges[sequence_id]
                break
            
            # Determine next tier and delay
            if current_tier == NudgeTier.GENTLE and attempt_count >= 1:
                next_tier = NudgeTier.SARCASTIC
                delay = settings.nudge_tier_1_delay
            elif current_tier == NudgeTier.SARCASTIC and attempt_count >= 2:
                next_tier = NudgeTier.SERGEANT
                delay = settings.nudge_tier_2_delay
            else:
                next_tier = current_tier
                delay = settings.nudge_tier_0_delay if current_tier == NudgeTier.GENTLE else \
                       settings.nudge_tier_1_delay if current_tier == NudgeTier.SARCASTIC else \
                       settings.nudge_tier_2_delay
            
            # Send escalated nudge
            user = sequence["user"]
            task = sequence["task"]
            message = self._generate_contextual_message(user, task, next_tier)
            
            success = await self._send_nudge(user, task, next_tier, message)
            
            # Update sequence state
            sequence.update({
                "current_tier": next_tier,
                "attempt_count": attempt_count + 1,
                "last_nudge": now,
                "next_nudge": now + timedelta(seconds=delay)
            })
            
            if not success:
                logger.warning(
                    "Nudge delivery failed",
                    sequence_id=sequence_id,
                    tier=next_tier.name
                )
    
    async def _send_nudge(
        self, 
        user: User, 
        task: Task, 
        tier: NudgeTier,
        message: str
    ) -> bool:
        """Send nudge via all configured methods for the user."""
        success_count = 0
        total_methods = 0
        
        # Record nudge attempt
        nudge_attempt = NudgeAttempt(
            user_id=user.user_id,
            task_id=task.task_id,
            tier=tier,
            method="multi",
            message=message
        )
        
        # Try each configured method
        for method_name in user.preferred_nudge_methods:
            if method_name in self.methods:
                total_methods += 1
                method = self.methods[method_name]
                
                try:
                    success = await method.send_nudge(user, message, tier)
                    if success:
                        success_count += 1
                        
                except Exception as e:
                    logger.error(
                        "Nudge method failed",
                        method=method_name,
                        user_id=user.user_id,
                        error=str(e)
                    )
        
        # Update nudge attempt record
        nudge_attempt.delivered = success_count > 0
        
        # TODO: Store nudge attempt in database/trace memory
        
        return success_count > 0
    
    def _generate_contextual_message(
        self, 
        user: User, 
        task: Task, 
        tier: NudgeTier
    ) -> str:
        """Generate contextual nudge message based on user and task."""
        task_title = task.title or "that thing"
        
        messages = {
            NudgeTier.GENTLE: [
                f"Hey {user.name}, ready to tackle '{task_title}'?",
                f"Gentle reminder about '{task_title}' 🌱",
                f"Want to make some progress on '{task_title}'?",
                f"'{task_title}' is waiting for you when you're ready",
            ],
            NudgeTier.SARCASTIC: [
                f"Still avoiding '{task_title}', huh? 🙄",
                f"'{task_title}' called. It misses you.",
                f"I see we're playing hide-and-seek with '{task_title}'",
                f"Your future self wants to have words about '{task_title}'",
            ],
            NudgeTier.SERGEANT: [
                f"GET UP AND DO '{task_title.upper()}' RIGHT NOW!",
                f"STOP EVERYTHING. '{task_title.upper()}' NEEDS TO HAPPEN.",
                f"THIS IS NOT A DRILL. '{task_title.upper()}' TIME.",
                f"YOUR EXECUTIVE FUNCTION IS LYING TO YOU. DO '{task_title.upper()}'!",
            ]
        }
        
        import random
        return random.choice(messages[tier])
    
    async def cancel_nudge_sequence(self, user_id: str, task_id: str) -> bool:
        """Cancel active nudge sequence (task completed or abandoned)."""
        sequence_id = f"{user_id}:{task_id}"
        
        if sequence_id in self.active_nudges:
            del self.active_nudges[sequence_id]
            logger.info("Cancelled nudge sequence", sequence_id=sequence_id)
            return True
        
        return False
    
    async def _record_abandonment(self, sequence: Dict[str, Any]) -> None:
        """Record when a nudge sequence fails to get response."""
        # TODO: Store abandonment in trace memory for pattern analysis
        logger.warning(
            "Task abandoned after max nudge attempts",
            user_id=sequence["user"].user_id,
            task_id=sequence["task"].task_id,
            attempts=sequence["attempt_count"]
        )


# Global nudge engine instance
nudge_engine = NudgeEngine()