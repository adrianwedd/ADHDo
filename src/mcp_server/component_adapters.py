"""
Component Adapters - Make components work with the integration hub
"""
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class NestAdapter:
    """Adapter for Nest nudge system to work with integration hub."""
    
    def __init__(self, nest_system):
        self.nest = nest_system
    
    async def send_nudge(self, message: str, urgency: str = "medium", **kwargs):
        """Send a nudge with urgency mapping."""
        from mcp_server.nest_nudges import NudgeType
        
        urgency_map = {
            "low": NudgeType.GENTLE,
            "medium": NudgeType.MOTIVATIONAL,
            "high": NudgeType.URGENT
        }
        
        nudge_type = urgency_map.get(urgency, NudgeType.GENTLE)
        
        return await self.nest.send_nudge(
            message=message,
            nudge_type=nudge_type,
            **kwargs
        )

class MusicAdapter:
    """Adapter for music system to work with integration hub."""
    
    def __init__(self, music_controller):
        self.music = music_controller
    
    async def play_focus_music(self, intensity: str = "medium", **kwargs):
        """Play focus music based on intensity."""
        from mcp_server.jellyfin_music import MusicMood
        
        intensity_map = {
            "low": MusicMood.CALM,
            "medium": MusicMood.FOCUS,
            "high": MusicMood.ENERGY
        }
        
        mood = intensity_map.get(intensity, MusicMood.FOCUS)
        
        try:
            return await self.music.play_mood_playlist(mood)
        except Exception as e:
            logger.error(f"Failed to play focus music: {e}")
            return False
    
    async def play_energizing_music(self, **kwargs):
        """Play energizing music to encourage movement."""
        from mcp_server.jellyfin_music import MusicMood
        
        try:
            return await self.music.play_mood_playlist(MusicMood.ENERGY)
        except Exception as e:
            logger.error(f"Failed to play energizing music: {e}")
            return False
    
    async def stop_music(self, **kwargs):
        """Stop current music playback."""
        try:
            return await self.music.stop_playback()
        except Exception as e:
            logger.error(f"Failed to stop music: {e}")
            return False

class CalendarAdapter:
    """Adapter for calendar/OAuth to work with integration hub."""
    
    def __init__(self, oauth_manager):
        self.oauth = oauth_manager
    
    async def create_focus_event(self, duration_minutes: int = 25, **kwargs):
        """Create a focus event in the calendar."""
        try:
            if hasattr(self.oauth, 'create_focus_event'):
                return await self.oauth.create_focus_event(duration_minutes)
            else:
                logger.warning("create_focus_event not implemented in OAuth manager")
                return None
        except Exception as e:
            logger.error(f"Failed to create focus event: {e}")
            return None
    
    async def get_calendar_events(self, **kwargs):
        """Get calendar events."""
        try:
            return await self.oauth.get_calendar_events(**kwargs)
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []

class FitnessAdapter:
    """Adapter for fitness data to work with integration hub."""
    
    def __init__(self, oauth_manager):
        self.oauth = oauth_manager
    
    async def get_today_stats(self, **kwargs):
        """Get today's fitness stats."""
        try:
            return await self.oauth.get_today_stats()
        except Exception as e:
            logger.error(f"Failed to get fitness stats: {e}")
            return {"error": str(e)}