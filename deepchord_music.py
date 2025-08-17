#!/usr/bin/env python3
"""
Deepchord and Ambient Techno Music Streams
Perfect for deep focus and ADHD flow states
"""
import pychromecast
import webbrowser
import time

# Curated deepchord/ambient techno streams
DEEPCHORD_STREAMS = {
    "dronezone": {
        "name": "SomaFM Drone Zone - Ambient/Space Music", 
        "url": "http://ice1.somafm.com/dronezone-128-mp3",
        "description": "Perfect deepchord vibes - minimal, hypnotic, spacious"
    },
    "deepspace": {
        "name": "SomaFM Deep Space One - Dark Ambient",
        "url": "http://ice1.somafm.com/deepspaceone-128-mp3", 
        "description": "Darker, more atmospheric - great for late night coding"
    },
    "spacestation": {
        "name": "SomaFM Space Station Soma - Ambient Electronica",
        "url": "http://ice1.somafm.com/spacestation-128-mp3",
        "description": "Beatless ambient with subtle rhythms"
    },
    "ambient_sleeping": {
        "name": "Radio.org Ambient Sleeping Pill",
        "url": "http://radio.stereoscenic.com/asp-h",
        "description": "Deep ambient for ultimate focus"
    },
    "echoes": {
        "name": "Echoes Online - Ambient & Space Music", 
        "url": "http://50.117.32.122:80/stream",
        "description": "High-quality ambient and space music"
    },
    "hearts_of_space": {
        "name": "Hearts of Space - Contemplative Music",
        "url": "https://hos-streamserver.org:8000/live",  
        "description": "Legendary ambient/space music show"
    },
    "musicforprogramming": {
        "name": "Music For Programming",
        "url": "http://datashat.net:8000/programming.m3u",
        "description": "Curated for deep coding sessions"
    }
}

class DeepchorMusicPlayer:
    """Ambient/deepchord music player for deep focus."""
    
    def __init__(self):
        self.current_stream = None
        
    def discover_devices(self):
        """Show available Chromecast devices."""
        chromecasts, _ = pychromecast.get_chromecasts()
        print("🔊 Available devices:")
        for cc in chromecasts:
            print(f"  • {cc.name}")
        return chromecasts
        
    def play_deepchord(self, stream_key="dronezone", device_name="Shack Speakers"):
        """Play deepchord/ambient stream on specified device."""
        
        if stream_key not in DEEPCHORD_STREAMS:
            print(f"❌ Stream '{stream_key}' not found")
            print("Available streams:", list(DEEPCHORD_STREAMS.keys()))
            return False
            
        stream = DEEPCHORD_STREAMS[stream_key]
        
        try:
            # Find Chromecast
            chromecasts, _ = pychromecast.get_chromecasts()
            device = next((cc for cc in chromecasts if device_name in cc.name), None)
            
            if not device:
                print(f"❌ Device '{device_name}' not found")
                print("Available devices:")
                for cc in chromecasts:
                    print(f"  • {cc.name}")
                return False
            
            print(f"🎵 Playing: {stream['name']}")
            print(f"📝 Description: {stream['description']}")
            print(f"🔊 Device: {device.name}")
            
            # Connect and play
            device.wait()
            mc = device.media_controller
            mc.play_media(stream["url"], "audio/mp3")
            mc.block_until_active(timeout=10)
            
            time.sleep(2)
            if mc.status.player_state == "PLAYING":
                print("✅ Stream started successfully!")
                self.current_stream = stream_key
                return True
            else:
                print(f"⚠️ Stream status: {mc.status.player_state}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def show_streams(self):
        """Display all available deepchord streams."""
        print("🎵 Available Deepchord/Ambient Streams:")
        print("=" * 50)
        
        for key, stream in DEEPCHORD_STREAMS.items():
            print(f"🎧 {key}")
            print(f"   {stream['name']}")
            print(f"   💭 {stream['description']}")
            print()
    
    def browser_fallback(self, stream_key="dronezone"):
        """Open stream in browser if Chromecast fails."""
        if stream_key not in DEEPCHORD_STREAMS:
            stream_key = "dronezone"
            
        stream = DEEPCHORD_STREAMS[stream_key]
        
        # For SomaFM streams, use their web player
        if "somafm.com" in stream["url"]:
            station = stream["url"].split("/")[-1].split("-")[0]
            web_url = f"https://somafm.com/player/#/now-playing/{station}"
        else:
            web_url = stream["url"]
        
        print(f"🌐 Opening {stream['name']} in browser...")
        webbrowser.open(web_url)
        return True

def main():
    """Interactive deepchord player."""
    player = DeepchorMusicPlayer()
    
    print("🎵 DEEPCHORD MUSIC PLAYER")
    print("Perfect ambient techno for deep ADHD focus")
    print("=" * 50)
    
    # Show available streams
    player.show_streams()
    
    # Discover devices
    devices = player.discover_devices()
    
    if not devices:
        print("No Chromecast devices found - using browser fallback")
        player.browser_fallback("dronezone")
        return
    
    # Auto-play best deepchord stream
    print("🚀 Starting with SomaFM Drone Zone (classic deepchord vibes)...")
    
    success = player.play_deepchord("dronezone", "Shack Speakers")
    
    if not success:
        print("Chromecast failed - trying browser...")
        player.browser_fallback("dronezone")

if __name__ == "__main__":
    main()