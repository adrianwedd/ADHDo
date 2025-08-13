#!/usr/bin/env python3
"""
Simple Chromecast music player that actually works
Bypasses Jellyfin and streams directly to Chromecasts
"""
import pychromecast
import time
from typing import Dict, Optional

# SomaFM streams (reliable, no auth needed)
STREAMS = {
    "focus": {
        "name": "Drone Zone - Ambient focus music",
        "url": "http://ice1.somafm.com/dronezone-128-mp3"
    },
    "energy": {
        "name": "Beat Blender - Upbeat electronic",
        "url": "http://ice1.somafm.com/beatblender-128-mp3"
    },
    "calm": {
        "name": "Deep Space One - Calm ambient",
        "url": "http://ice1.somafm.com/deepspaceone-128-mp3"
    },
    "ambient": {
        "name": "Space Station - Ambient electronica",
        "url": "http://ice1.somafm.com/spacestation-128-mp3"
    },
    "nature": {
        "name": "Groove Salad - Chill beats",
        "url": "http://ice1.somafm.com/groovesalad-128-mp3"
    },
    "study": {
        "name": "Secret Agent - Mysterious jazz",
        "url": "http://ice1.somafm.com/secretagent-128-mp3"
    }
}

class ChromecastMusic:
    def __init__(self):
        self.cast = None
        self.current_mood = None
        
    def connect(self, device_name: str = "Nest Mini") -> bool:
        """Connect to a Chromecast device."""
        try:
            chromecasts, browser = pychromecast.get_chromecasts()
            self.cast = next((cc for cc in chromecasts if device_name in cc.name), None)
            
            if self.cast:
                self.cast.wait()
                return True
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def play(self, mood: str = "focus", device: Optional[str] = None) -> Dict:
        """Play music on Chromecast."""
        try:
            # Get stream
            stream = STREAMS.get(mood, STREAMS["focus"])
            
            # Connect to device
            device_name = device or "Nest Mini"
            if not self.cast or (device and device != self.cast.name):
                if not self.connect(device_name):
                    return {"success": False, "message": f"Could not find {device_name}"}
            
            # Play stream
            mc = self.cast.media_controller
            mc.play_media(stream["url"], "audio/mp3")
            mc.block_until_active(timeout=5)
            
            self.current_mood = mood
            
            return {
                "success": True,
                "message": f"Playing {stream['name']} on {self.cast.name}",
                "device": self.cast.name,
                "mood": mood
            }
            
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def stop(self) -> Dict:
        """Stop playback."""
        try:
            if self.cast:
                self.cast.media_controller.stop()
                return {"success": True, "message": "Stopped playback"}
            return {"success": False, "message": "Not connected"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def status(self) -> Dict:
        """Get playback status."""
        try:
            if self.cast:
                mc = self.cast.media_controller
                return {
                    "is_playing": mc.status.player_state == "PLAYING",
                    "device": self.cast.name,
                    "mood": self.current_mood,
                    "volume": mc.status.volume_level
                }
            return {"is_playing": False, "device": None}
        except:
            return {"is_playing": False, "device": None}

# Test if run directly
if __name__ == "__main__":
    player = ChromecastMusic()
    
    # List available devices
    chromecasts, _ = pychromecast.get_chromecasts()
    print("Available devices:")
    for cc in chromecasts:
        print(f"  - {cc.name}")
    
    # Play energy music
    print("\nPlaying energy music...")
    result = player.play("energy")
    print(result)