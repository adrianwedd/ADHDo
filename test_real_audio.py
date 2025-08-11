import pychromecast
import time

print("🔍 Testing with real audio URL...")
chromecasts, browser = pychromecast.get_chromecasts(timeout=10)

# Find Nest Hub Max
nest_hub = None
for cc in chromecasts:
    if "Nest Hub Max" in cc.name:
        nest_hub = cc
        break

if nest_hub:
    print(f"📱 Testing on {nest_hub.name}")
    nest_hub.wait()
    
    # Test with a known working audio URL
    test_url = "https://www.soundjay.com/misc/sounds/beep-07a.mp3"
    
    mc = nest_hub.media_controller
    print(f"🎵 Playing test audio: {test_url}")
    mc.play_media(test_url, 'audio/mp3')
    
    # Wait and check status
    time.sleep(5)
    mc.block_until_active(timeout=10)
    
    status = mc.status
    print(f"🎵 Player state: {status.player_state}")
    print(f"🎵 Content: {status.content_id}")
    
    if status.player_state == "PLAYING":
        print("✅ AUDIO IS WORKING\! The issue is with Jellyfin URLs")
    else:
        print("❌ Chromecast audio playback is broken")
        
else:
    print("❌ Nest Hub Max not found")

browser.stop_discovery()
