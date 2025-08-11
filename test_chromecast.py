#!/usr/bin/env python3
"""Test Chromecast connection and play music."""
import pychromecast
import time

print("🔍 Discovering Chromecast devices...")
chromecasts, browser = pychromecast.get_chromecasts(timeout=10)

print(f"Found {len(chromecasts)} devices:")
for cc in chromecasts:
    print(f"  - {cc.name} ({cc.model_name})")

# Find Shack Speakers
target = None
for cc in chromecasts:
    if cc.name == "Shack Speakers":
        target = cc
        break

if target:
    print(f"\n✅ Connecting to {target.name}...")
    target.wait()
    mc = target.media_controller
    
    # Play test audio - use a known working MP3
    # First try the Jellyfin URL
    jellyfin_url = "http://192.168.1.100:8096/Audio/00011c7a60b7a4d6e404c1ba913676f7/stream?api_key=abf44b9de48c46dab56d4ace26b24f9a"
    # Fallback to test MP3
    test_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
    
    print(f"🎵 Playing test audio...")
    mc.play_media(test_url, "audio/mpeg")
    mc.block_until_active()
    time.sleep(2)  # Give it time to start
    
    # Set volume
    target.set_volume(0.5)
    print(f"🔊 Volume set to 50%")
    
    print("✅ Music should be playing on your Chromecast!")
    print("Status:", mc.status)
else:
    print("❌ Shack Speakers not found")

browser.stop_discovery()