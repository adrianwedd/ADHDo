import pychromecast
import time

print("🔍 Detailed Chromecast debug...")
chromecasts, browser = pychromecast.get_chromecasts(timeout=10)

for cc in chromecasts:
    if "Nest Hub Max" in cc.name:
        print(f"📱 {cc.name} ({cc.model_name})")
        cc.wait()
        
        # Check what's connected
        print(f"   Status: {cc.status.status_text}")
        print(f"   App: {cc.status.display_name}")
        print(f"   App ID: {cc.status.app_id}")
        print(f"   Session ID: {cc.status.session_id}")
        print(f"   Volume: {cc.status.volume_level}")
        print(f"   Muted: {cc.status.volume_muted}")
        
        # Try to quit current app and restart
        print("🔄 Quitting current app...")
        cc.quit_app()
        time.sleep(2)
        
        # Check status after quit
        print(f"   After quit - Status: {cc.status.status_text}")
        print(f"   After quit - App: {cc.status.display_name}")
        
        # Now try to play
        print("🎵 Trying to play after quit...")
        mc = cc.media_controller
        mc.play_media("https://www.soundjay.com/misc/sounds/beep-07a.mp3", 'audio/mp3')
        mc.block_until_active(timeout=5)
        
        time.sleep(3)
        status = mc.status
        print(f"🎵 Final state: {status.player_state}")
        print(f"🎵 Content: {status.content_id}")
        break

browser.stop_discovery()
