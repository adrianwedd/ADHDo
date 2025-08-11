#!/usr/bin/env python3
"""External music streaming service for ADHD system."""

import asyncio
import logging
import random
from typing import List, Dict, Optional, Any
import pychromecast
from pychromecast.controllers.media import MediaController

logger = logging.getLogger(__name__)

class ExternalMusicService:
    """External music streaming service using Internet Archive and other free sources."""
    
    def __init__(self, chromecast_name: str = "Nest Hub Max"):
        self.chromecast_name = chromecast_name
        self.cast_device: Optional[pychromecast.Chromecast] = None
        self.media_controller: Optional[MediaController] = None
        self.browser = None
        
        # Free external music sources
        self.music_libraries = {
            'focus': [
                {
                    'title': 'Ambient Focus Music',
                    'url': 'https://archive.org/download/AmbientFocus2022/ambient_focus_30min.mp3',
                    'duration': 1800  # 30 minutes
                },
                {
                    'title': 'White Noise for Focus',
                    'url': 'https://archive.org/download/WhiteNoiseFocus/whitenoise_60min.mp3',
                    'duration': 3600  # 60 minutes
                },
                {
                    'title': 'Nature Sounds - Forest',
                    'url': 'https://archive.org/download/NatureSoundsForest/forest_ambient_45min.mp3',
                    'duration': 2700  # 45 minutes
                }
            ],
            'relaxing': [
                {
                    'title': 'Soft Piano for Sleep',
                    'url': 'https://archive.org/download/SoftPianoSleep/piano_sleep_60min.mp3',
                    'duration': 3600
                },
                {
                    'title': 'Ocean Waves',
                    'url': 'https://archive.org/download/OceanWavesSleep/ocean_waves_30min.mp3',
                    'duration': 1800
                },
                {
                    'title': 'Meditation Bells',
                    'url': 'https://archive.org/download/MeditationBells/meditation_bells_20min.mp3',
                    'duration': 1200  # 20 minutes
                }
            ],
            'energizing': [
                {
                    'title': 'Upbeat Instrumental',
                    'url': 'https://archive.org/download/UpbeatInstrumental/upbeat_energy_25min.mp3',
                    'duration': 1500  # 25 minutes
                },
                {
                    'title': 'Morning Energy Mix',
                    'url': 'https://archive.org/download/MorningEnergyMix/morning_energy_30min.mp3',
                    'duration': 1800
                }
            ],
            'adhd': [
                {
                    'title': 'Binaural Beats - Focus (40Hz)',
                    'url': 'https://archive.org/download/BinauralBeats40Hz/binaural_focus_40hz_30min.mp3',
                    'duration': 1800
                },
                {
                    'title': 'Brown Noise - ADHD Support',
                    'url': 'https://archive.org/download/BrownNoiseADHD/brown_noise_adhd_60min.mp3',
                    'duration': 3600
                },
                {
                    'title': 'Study Music - ADHD Optimized',
                    'url': 'https://archive.org/download/ADHDStudyMusic/adhd_study_music_45min.mp3',
                    'duration': 2700
                }
            ]
        }
        
        # Fallback URLs that are known to work
        self.fallback_tracks = [
            {
                'title': 'Test Track',
                'url': 'https://archive.org/download/testmp3testfile/mpthreetest.mp3',
                'duration': 30
            },
            {
                'title': 'Ambient Test',
                'url': 'https://archive.org/download/AmbientTest/ambient_short.mp3',
                'duration': 60
            }
        ]

    async def initialize(self) -> bool:
        """Initialize connection to Chromecast device."""
        try:
            logger.info("🎵 Initializing external music service...")
            
            # Fresh discovery each time to avoid threading issues
            chromecasts, browser = pychromecast.get_chromecasts(timeout=10)
            self.browser = browser
            
            logger.info(f"🔍 Found {len(chromecasts)} devices: {[cc.name for cc in chromecasts]}")
            
            # Find target device - use more flexible matching
            for cast in chromecasts:
                logger.info(f"🔍 Checking device: '{cast.name}' vs target: '{self.chromecast_name}'")
                if (self.chromecast_name.lower() in cast.name.lower() or 
                    "nest hub max" in cast.name.lower() or
                    cast.name.lower() in self.chromecast_name.lower()):
                    self.cast_device = cast
                    logger.info(f"✅ Matched device: {cast.name}")
                    break
            
            if not self.cast_device:
                logger.error(f"❌ Chromecast '{self.chromecast_name}' not found in available devices: {[cc.name for cc in chromecasts]}")
                if self.browser:
                    self.browser.stop_discovery()
                return False
            
            # Wait for device connection
            self.cast_device.wait()
            self.media_controller = self.cast_device.media_controller
            
            logger.info(f"✅ Connected to {self.cast_device.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize external music: {e}")
            if self.browser:
                self.browser.stop_discovery()
            return False

    async def play_music(self, mood: str = "focus", volume: float = 0.6) -> Dict[str, Any]:
        """Play music based on mood/category."""
        if not self.cast_device or not self.media_controller:
            if not await self.initialize():
                return {"success": False, "error": "Device not available"}
        
        try:
            # Get tracks for mood
            tracks = self.music_libraries.get(mood, self.music_libraries['focus'])
            
            # Add fallback tracks if needed
            if len(tracks) == 0:
                tracks = self.fallback_tracks
            
            # Select random track
            track = random.choice(tracks)
            
            logger.info(f"🎵 Playing: {track['title']} ({mood} mood)")
            
            # Set volume
            self.cast_device.set_volume(volume)
            
            # Play track
            self.media_controller.play_media(
                track['url'],
                'audio/mp3',
                title=track['title'],
                thumb=None
            )
            
            # Wait a moment for playback to start
            await asyncio.sleep(2)
            
            # Check status
            status = self.media_controller.status
            success = status.player_state in ["PLAYING", "BUFFERING"]
            
            logger.info(f"📊 Playback status: {status.player_state}")
            
            return {
                "success": success,
                "track": track,
                "mood": mood,
                "volume": volume,
                "status": status.player_state,
                "device": self.cast_device.name
            }
            
        except Exception as e:
            logger.error(f"Failed to play music: {e}")
            return {"success": False, "error": str(e)}

    async def stop_music(self) -> bool:
        """Stop current music playback."""
        try:
            if self.media_controller:
                self.media_controller.stop()
                logger.info("🛑 Music stopped")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to stop music: {e}")
            return False

    async def pause_music(self) -> bool:
        """Pause current music playback."""
        try:
            if self.media_controller:
                self.media_controller.pause()
                logger.info("⏸️ Music paused")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to pause music: {e}")
            return False

    async def resume_music(self) -> bool:
        """Resume paused music playback."""
        try:
            if self.media_controller:
                self.media_controller.play()
                logger.info("▶️ Music resumed")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to resume music: {e}")
            return False

    async def set_volume(self, volume: float) -> bool:
        """Set music volume (0.0 to 1.0)."""
        try:
            if self.cast_device:
                self.cast_device.set_volume(volume)
                logger.info(f"🔊 Volume set to {volume:.1f}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return False

    async def get_status(self) -> Dict[str, Any]:
        """Get current playback status."""
        try:
            if not self.media_controller:
                return {"connected": False}
            
            status = self.media_controller.status
            return {
                "connected": True,
                "playing": status.player_state == "PLAYING",
                "paused": status.player_state == "PAUSED",
                "stopped": status.player_state == "IDLE",
                "volume": self.cast_device.status.volume_level if self.cast_device else 0,
                "title": status.title or "Unknown",
                "player_state": status.player_state
            }
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"connected": False, "error": str(e)}

    def get_available_moods(self) -> List[str]:
        """Get list of available music moods/categories."""
        return list(self.music_libraries.keys())

    def get_tracks_for_mood(self, mood: str) -> List[Dict[str, Any]]:
        """Get available tracks for a specific mood."""
        return self.music_libraries.get(mood, [])

    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.media_controller:
                self.media_controller.stop()
        except:
            pass
        
        try:
            if self.cast_device:
                self.cast_device.disconnect()
        except:
            pass
        
        try:
            if self.browser:
                self.browser.stop_discovery()
        except:
            pass

# Global instance
external_music_service: Optional[ExternalMusicService] = None

async def initialize_external_music() -> bool:
    """Initialize the external music service."""
    global external_music_service
    
    try:
        external_music_service = ExternalMusicService()
        success = await external_music_service.initialize()
        
        if success:
            logger.info("🎵 External music service ready")
            return True
        else:
            external_music_service = None
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize external music: {e}")
        external_music_service = None
        return False

async def play_external_music(mood: str = "focus", volume: float = 0.6) -> Dict[str, Any]:
    """Play music using external service."""
    global external_music_service
    
    if not external_music_service:
        if not await initialize_external_music():
            return {"success": False, "error": "Service not available"}
    
    return await external_music_service.play_music(mood, volume)

if __name__ == "__main__":
    # Test the service
    async def test_external_music():
        service = ExternalMusicService()
        if await service.initialize():
            result = await service.play_music("focus", 0.7)
            print(f"Play result: {result}")
            
            await asyncio.sleep(5)
            
            status = await service.get_status()
            print(f"Status: {status}")
            
            await service.cleanup()
        else:
            print("Failed to initialize service")
    
    asyncio.run(test_external_music())