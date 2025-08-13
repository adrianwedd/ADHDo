#!/usr/bin/env python3
"""
Simplest possible music solution - opens streams in browser
No Chromecast or Jellyfin needed!
"""

import webbrowser
import subprocess
import os
from typing import Dict

# Web-based music players that work in browser
WEB_MUSIC = {
    "focus": {
        "name": "Focus Music - SomaFM Drone Zone",
        "url": "https://somafm.com/player/#/now-playing/dronezone"
    },
    "energy": {
        "name": "Energy Music - SomaFM Beat Blender",
        "url": "https://somafm.com/player/#/now-playing/beatblender"
    },
    "calm": {
        "name": "Calm Music - SomaFM Deep Space One",
        "url": "https://somafm.com/player/#/now-playing/deepspaceone"
    },
    "lofi": {
        "name": "Lofi Stream",
        "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk"  # Lofi Girl stream
    }
}

class BrowserMusicPlayer:
    """Dead simple browser-based music player."""
    
    def __init__(self):
        self.is_playing = False
        self.current_mood = None
        
    def play(self, mood: str = "focus") -> Dict:
        """Open music in browser."""
        try:
            stream = WEB_MUSIC.get(mood, WEB_MUSIC["focus"])
            
            # Try to open in browser
            if webbrowser.open(stream["url"]):
                self.is_playing = True
                self.current_mood = mood
                return {
                    "success": True,
                    "message": f"Opened {stream['name']} in browser",
                    "url": stream["url"]
                }
            else:
                return {
                    "success": False,
                    "message": "Couldn't open browser"
                }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    def stop(self) -> Dict:
        """Can't really stop browser, but reset state."""
        self.is_playing = False
        self.current_mood = None
        return {
            "success": True,
            "message": "Close the browser tab to stop music"
        }
    
    def status(self) -> Dict:
        """Get status."""
        return {
            "is_playing": self.is_playing,
            "current_mood": self.current_mood,
            "available": True,
            "method": "browser",
            "available_moods": list(WEB_MUSIC.keys())
        }

# Global player
player = BrowserMusicPlayer()

async def play_music(mood: str = "focus") -> Dict:
    """Play music in browser."""
    return player.play(mood)

async def stop_music() -> Dict:
    """Stop music (tell user to close tab)."""
    return player.stop()

async def music_status() -> Dict:
    """Get music status."""
    return player.status()

if __name__ == "__main__":
    print("🎵 Browser Music Player")
    print("This opens music streams in your web browser")
    print("\nAvailable streams:")
    for mood, info in WEB_MUSIC.items():
        print(f"  • {mood}: {info['name']}")
        print(f"    {info['url']}")
    
    # Test
    import asyncio
    async def test():
        result = await play_music("focus")
        print(f"\nResult: {result}")
    
    asyncio.run(test())