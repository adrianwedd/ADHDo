import pychromecast
import time

print("🔍 Testing LOCAL audio URL...")
chromecasts, browser = pychromecast.get_chromecasts(timeout=10)

for cc in chromecasts:
    if "Nest Hub Max" in cc.name:
        print(f"📱 Testing on {cc.name}")
        cc.wait()
        cc.set_volume(1.0)
        
        # Test with our local server - this should work if it worked before
        local_url = "http://10.30.17.41:23443/test_tts.mp3"
        print(f"🎵 Playing LOCAL audio: {local_url}")
        
        mc = cc.media_controller
        mc.play_media(local_url, 'audio/mp3')
        
        print("⏰ Waiting 10 seconds for LOCAL audio...")
        time.sleep(10)
        
        status = mc.status
        print(f"🎵 Local test state: {status.player_state}")
        print(f"🎵 Local content: {status.content_id}")
        
        if status.player_state == "PLAYING":
            print("✅ LOCAL AUDIO WORKS\! External URLs are the problem")
        else:
            print("❌ Even local audio fails - deeper issue")
        break

browser.stop_discovery()
