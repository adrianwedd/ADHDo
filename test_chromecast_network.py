import pychromecast
import time

print("🔍 Testing Chromecast network access...")
chromecasts, browser = pychromecast.get_chromecasts(timeout=10)

for cc in chromecasts:
    if "Nest Hub Max" in cc.name:
        print(f"📱 Testing {cc.name}")
        cc.wait()
        cc.set_volume(1.0)
        
        # Test multiple URL types to see what works
        test_urls = [
            ("Google TTS", "https://translate.google.com/translate_tts?ie=UTF-8&q=Hello&tl=en&client=tw-ob"),
            ("Simple MP3", "https://www.soundjay.com/misc/sounds/beep-07a.mp3"),
            ("Our server", "http://10.30.17.41:23443/test_tts.mp3")
        ]
        
        mc = cc.media_controller
        for name, url in test_urls:
            print(f"\n🧪 Testing {name}: {url[:50]}...")
            mc.play_media(url, 'audio/mp3')
            time.sleep(3)
            
            status = mc.status
            print(f"   State: {status.player_state}")
            print(f"   Position: {status.current_time}")
            
            if status.player_state == "PLAYING":
                print(f"   ✅ {name} WORKS\!")
                break
            else:
                print(f"   ❌ {name} failed")
        
        break

browser.stop_discovery()
