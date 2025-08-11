#!/usr/bin/env python3
"""Direct Chromecast debug - check what's actually playing"""

import pychromecast
import time

def debug_chromecast():
    print("🔍 Direct Chromecast status check...")
    
    try:
        # Discover devices
        chromecasts, browser = pychromecast.get_chromecasts(timeout=10)
        print(f"📱 Found {len(chromecasts)} Chromecast devices")
        
        for cc in chromecasts:
            print(f"\n📱 Device: {cc.name} ({cc.model_name})")
            print(f"   Host: {cc.host}:{cc.port}")
            print(f"   UUID: {cc.uuid}")
            
            # Connect and check status
            cc.wait()
            
            # Get receiver status
            receiver = cc.status
            print(f"   Volume: {receiver.volume_level * 100:.0f}% (muted: {receiver.volume_muted})")
            print(f"   Status: {receiver.status_text}")
            print(f"   App: {receiver.display_name}")
            
            # Get media status
            mc = cc.media_controller
            media = mc.status
            
            if media and media.content_id:
                print(f"   🎵 Playing: {media.title or 'Unknown'}")
                print(f"   🎵 Artist: {media.artist or 'Unknown'}")  
                print(f"   🎵 URL: {media.content_id[:100]}...")
                print(f"   🎵 State: {media.player_state}")
                print(f"   🎵 Duration: {media.duration}s")
                print(f"   🎵 Position: {media.current_time}s")
            else:
                print(f"   💤 No media playing")
            
        browser.stop_discovery()
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")

if __name__ == "__main__":
    debug_chromecast()