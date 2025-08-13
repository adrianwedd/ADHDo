#!/usr/bin/env python3
"""
Simple music player that actually works
Uses Chromecast to play web radio streams - no Jellyfin needed
"""

import asyncio
import logging
from typing import Optional, Dict
import pychromecast
from pychromecast.controllers.media import MediaController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Free streaming radio URLs that work
MUSIC_STREAMS = {
    "focus": {
        "name": "Brain.fm Focus",
        "url": "http://stream.brain.fm/focus.mp3",  # May need subscription
        "fallback": "http://ice1.somafm.com/dronezone-128-mp3"  # SomaFM Drone Zone
    },
    "energy": {
        "name": "Energetic Electronic", 
        "url": "http://ice1.somafm.com/beatblender-128-mp3"  # SomaFM Beat Blender
    },
    "calm": {
        "name": "Calm Ambient",
        "url": "http://ice1.somafm.com/deepspaceone-128-mp3"  # SomaFM Deep Space One
    },
    "lofi": {
        "name": "Lofi Hip Hop",
        "url": "http://ice1.somafm.com/fluid-128-mp3"  # SomaFM Fluid
    },
    "classical": {
        "name": "Classical Focus",
        "url": "http://stream.classical.org/classical128"  # Classical MPR
    }
}

class SimpleMusicPlayer:
    """Simple Chromecast music player for ADHD support."""
    
    def __init__(self):
        self.chromecast: Optional[pychromecast.Chromecast] = None
        self.media_controller: Optional[MediaController] = None
        self.is_playing = False
        self.current_stream = None
        
    def find_chromecast(self, name: Optional[str] = None) -> bool:
        """Find and connect to Chromecast."""
        try:
            logger.info("🔍 Searching for Chromecasts...")
            chromecasts, browser = pychromecast.get_chromecasts()
            
            if not chromecasts:
                logger.error("No Chromecasts found")
                return False
                
            # List available devices
            logger.info(f"Found {len(chromecasts)} Chromecast(s):")
            for cc in chromecasts:
                logger.info(f"  • {cc.name} ({cc.cast_type})")
            
            # Try to find specific device or use first one
            if name:
                for cc in chromecasts:
                    if name.lower() in cc.name.lower():
                        self.chromecast = cc
                        break
            
            if not self.chromecast:
                self.chromecast = chromecasts[0]
                
            logger.info(f"✅ Using: {self.chromecast.name}")
            
            # Connect and setup
            self.chromecast.wait()
            self.media_controller = self.chromecast.media_controller
            
            pychromecast.discovery.stop_discovery(browser)
            return True
            
        except Exception as e:
            logger.error(f"Chromecast error: {e}")
            return False
    
    def play_stream(self, mood: str = "focus", volume: float = 0.5) -> bool:
        """Play a music stream."""
        try:
            if not self.chromecast:
                logger.error("No Chromecast connected")
                return False
                
            stream = MUSIC_STREAMS.get(mood, MUSIC_STREAMS["focus"])
            
            logger.info(f"🎵 Playing {stream['name']}...")
            
            # Set volume
            self.chromecast.set_volume(volume)
            
            # Play the stream
            self.media_controller.play_media(
                stream.get("fallback", stream["url"]),  # Use fallback if main URL fails
                "audio/mp3",
                title=stream["name"],
                thumb=None,
                stream_type="LIVE"
            )
            
            # Wait for it to start
            self.media_controller.block_until_active(timeout=10)
            
            self.is_playing = True
            self.current_stream = mood
            
            logger.info(f"✅ Playing {stream['name']} on {self.chromecast.name}")
            return True
            
        except Exception as e:
            logger.error(f"Playback error: {e}")
            # Try fallback URL
            if "fallback" in MUSIC_STREAMS.get(mood, {}):
                try:
                    self.media_controller.play_media(
                        MUSIC_STREAMS[mood]["fallback"],
                        "audio/mp3"
                    )
                    self.is_playing = True
                    return True
                except:
                    pass
            return False
    
    def stop(self) -> bool:
        """Stop playback."""
        try:
            if self.chromecast and self.media_controller:
                self.media_controller.stop()
                self.is_playing = False
                self.current_stream = None
                logger.info("⏹️ Stopped playback")
                return True
        except Exception as e:
            logger.error(f"Stop error: {e}")
        return False
    
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            "is_playing": self.is_playing,
            "current_stream": self.current_stream,
            "chromecast_connected": self.chromecast is not None,
            "chromecast_name": self.chromecast.name if self.chromecast else None,
            "available_moods": list(MUSIC_STREAMS.keys())
        }

# Global player instance
player = SimpleMusicPlayer()

async def play_music(mood: str = "focus") -> Dict:
    """Play music with specified mood."""
    # Connect to Chromecast if not connected
    if not player.chromecast:
        if not player.find_chromecast():
            return {"success": False, "message": "No Chromecast found"}
    
    # Play the stream
    if player.play_stream(mood):
        return {"success": True, "message": f"Playing {mood} music"}
    else:
        return {"success": False, "message": "Failed to play music"}

async def stop_music() -> Dict:
    """Stop music playback."""
    if player.stop():
        return {"success": True, "message": "Music stopped"}
    else:
        return {"success": False, "message": "Failed to stop music"}

async def music_status() -> Dict:
    """Get music status."""
    return player.get_status()

# Test script
if __name__ == "__main__":
    async def test():
        print("🎵 Simple Music Player Test")
        print("="*40)
        
        # Find Chromecasts
        if player.find_chromecast():
            print("\n1. Playing focus music...")
            result = await play_music("focus")
            print(f"   Result: {result}")
            
            if result["success"]:
                await asyncio.sleep(10)
                
                print("\n2. Getting status...")
                status = await music_status()
                print(f"   Status: {status}")
                
                print("\n3. Stopping music...")
                result = await stop_music()
                print(f"   Result: {result}")
        else:
            print("❌ No Chromecast found")
            print("\nAvailable streams (for testing):")
            for mood, stream in MUSIC_STREAMS.items():
                print(f"  • {mood}: {stream['name']}")
                print(f"    URL: {stream.get('fallback', stream['url'])}")
    
    asyncio.run(test())