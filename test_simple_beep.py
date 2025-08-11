import pychromecast
import time

print("🔍 Testing simple beep...")
chromecasts, browser = pychromecast.get_chromecasts(timeout=10)

nest_hub = None
for cc in chromecasts:
    if "Nest Hub Max" in cc.name:
        nest_hub = cc
        break

if nest_hub:
    print(f"📱 Testing on {nest_hub.name} - listen for beep\!")
    nest_hub.wait()
    nest_hub.set_volume(1.0)  # Max volume
    
    mc = nest_hub.media_controller
    
    # Try a simple online beep
    beep_url = "https://www.soundjay.com/misc/beep-07a.wav"
    print(f"🔊 MAX VOLUME BEEP TEST: {beep_url}")
    mc.play_media(beep_url, 'audio/wav')
    
    print("⏰ Waiting 10 seconds... LISTEN FOR BEEP\!")
    time.sleep(10)
    
    status = mc.status
    print(f"Status: {status.player_state}")

browser.stop_discovery()
print("🎯 Did you hear the beep? This will tell us if Chromecast audio works at all.")
