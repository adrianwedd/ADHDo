#!/usr/bin/env python3
"""Test direct nudge to Nest Hub Max."""
import pychromecast
from gtts import gTTS
import tempfile
import time
import os

print("🔍 Finding Nest Hub Max...")
chromecasts, browser = pychromecast.get_chromecasts(timeout=15)

nest_max = None
for cc in chromecasts:
    print(f"Found: {cc.name} ({cc.model_name})")
    if 'nest hub max' in cc.model_name.lower():
        nest_max = cc
        print(f"✅ Found Nest Hub Max: {cc.name}")
        break

if nest_max:
    print("🎯 Connecting to Nest Hub Max...")
    nest_max.wait()
    mc = nest_max.media_controller
    
    # Generate TTS for the nudge
    message = "Hello! This is a test nudge from your ADHD system. Testing the Google Nest integration."
    print(f"📢 Generating TTS: {message}")
    
    tts = gTTS(text=message, lang='en', slow=False)
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
        tts.save(tmp_file.name)
        print(f"💾 TTS saved to: {tmp_file.name}")
        
        # Create a local file URL that the Nest can access
        # For this test, we'll use a simple HTTP server approach
        audio_url = f"http://192.168.1.100:23443/nudge-audio/{os.path.basename(tmp_file.name)}"
        print(f"🌐 Audio URL: {audio_url}")
        
        # Set volume
        nest_max.set_volume(0.4)
        print("🔊 Volume set to 40%")
        
        # Play the nudge
        print("🎵 Playing nudge...")
        try:
            mc.play_media(audio_url, 'audio/mpeg')
            mc.block_until_active()
            
            print("✅ Nudge sent successfully!")
            print(f"Status: {mc.status}")
            
            # Wait for playback
            time.sleep(10)
            
        except Exception as e:
            print(f"❌ Playback failed: {e}")
            
            # Try fallback with a direct file approach
            print("🔄 Trying alternative approach...")
            # Let's just test if we can set volume and get status
            print(f"Device status: {nest_max.status}")
            
        finally:
            # Clean up
            try:
                os.remove(tmp_file.name)
            except:
                pass
    
else:
    print("❌ Nest Hub Max not found")
    print("Available devices:")
    for cc in chromecasts:
        print(f"  - {cc.name} ({cc.model_name})")

browser.stop_discovery()
print("🏁 Test complete")