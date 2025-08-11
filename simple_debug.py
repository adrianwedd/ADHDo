import pychromecast
import time

print("🔍 Simple Chromecast check...")
chromecasts, browser = pychromecast.get_chromecasts(timeout=10)

for cc in chromecasts:
    print(f"\n📱 {cc.name} ({cc.model_name})")
    try:
        cc.wait(timeout=5)
        print(f"   Volume: {cc.status.volume_level * 100:.0f}%")
        print(f"   App: {cc.status.display_name}")
        
        media = cc.media_controller.status
        if media and media.content_id:
            print(f"   🎵 Playing: {media.title}")
            print(f"   🎵 State: {media.player_state}")
        else:
            print(f"   💤 Idle")
    except Exception as e:
        print(f"   ❌ Error: {e}")

browser.stop_discovery()
