#!/usr/bin/env python3
"""Debug audio issues - check TTS generation and URL serving"""

import asyncio
import tempfile
import os
from gtts import gTTS
import requests

async def test_tts_generation():
    """Test if TTS files are being generated properly"""
    print("🔍 Testing TTS generation...")
    
    try:
        # Generate test TTS
        message = "This is a test of TTS generation. Can you hear this message?"
        tts = gTTS(text=message, lang='en', slow=False)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tts.save(tmp_file.name)
            file_size = os.path.getsize(tmp_file.name)
            print(f"✅ TTS file generated: {tmp_file.name} ({file_size} bytes)")
            
            # Test if file is playable/has content
            with open(tmp_file.name, 'rb') as f:
                first_bytes = f.read(10)
                print(f"📊 First 10 bytes: {first_bytes}")
                if first_bytes.startswith(b'ID3') or b'MPEG' in first_bytes[:20]:
                    print("✅ File appears to be valid MP3")
                else:
                    print("❌ File may not be valid MP3")
            
            # Clean up
            os.remove(tmp_file.name)
            return True
            
    except Exception as e:
        print(f"❌ TTS generation failed: {e}")
        return False

def test_audio_serving():
    """Test if audio files are being served properly"""
    print("🔍 Testing audio serving endpoint...")
    
    try:
        # Test the nudge-audio endpoint
        response = requests.get("http://localhost:23443/nudge-audio/nonexistent.mp3")
        print(f"📊 Nudge audio endpoint status: {response.status_code}")
        
        if response.status_code == 404:
            print("✅ Endpoint exists but file not found (expected)")
        elif response.status_code == 405:
            print("❌ Method not allowed - endpoint may be misconfigured")
        else:
            print(f"⚠️ Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Audio serving test failed: {e}")

def test_jellyfin_api():
    """Test Jellyfin API connectivity"""
    print("🔍 Testing Jellyfin API...")
    
    try:
        # Test basic Jellyfin connectivity
        response = requests.get("http://localhost:8096/System/Info", timeout=5)
        if response.status_code == 200:
            info = response.json()
            print(f"✅ Jellyfin connected: {info.get('ServerName', 'Unknown')}")
            
            # Test audio items
            api_key = "abf44b9de48c46dab56d4ace26b24f9a"
            user_id = "ab7b4e8e1a4a46aaa1f39e9e6af0b64a"
            
            audio_response = requests.get(
                f"http://localhost:8096/Users/{user_id}/Items",
                params={
                    "api_key": api_key,
                    "IncludeItemTypes": "Audio",
                    "Limit": 5,
                    "Fields": "Path"
                }
            )
            
            if audio_response.status_code == 200:
                items = audio_response.json().get('Items', [])
                print(f"✅ Found {len(items)} audio items in Jellyfin")
                
                if items:
                    item = items[0]
                    item_id = item['Id']
                    
                    # Test stream URL
                    stream_url = f"http://localhost:8096/Audio/{item_id}/stream.mp3?UserId={user_id}&DeviceId=ADHDo_Test&api_key={api_key}"
                    stream_response = requests.head(stream_url, timeout=5)
                    print(f"📊 Stream URL test: {stream_response.status_code}")
                    
                    if stream_response.status_code == 200:
                        print("✅ Audio streaming working")
                    else:
                        print(f"❌ Audio streaming failed: {stream_response.status_code}")
            else:
                print(f"❌ Failed to get audio items: {audio_response.status_code}")
        else:
            print(f"❌ Jellyfin connection failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Jellyfin test failed: {e}")

async def main():
    print("🔧 Audio Debug Test Suite")
    print("=" * 50)
    
    # Test TTS generation
    await test_tts_generation()
    print()
    
    # Test audio serving
    test_audio_serving()
    print()
    
    # Test Jellyfin
    test_jellyfin_api()
    print()
    
    print("🎯 Debug complete!")

if __name__ == "__main__":
    asyncio.run(main())