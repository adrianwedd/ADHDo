#!/usr/bin/env python3
"""Debug Chromecast discovery for music system."""

import pychromecast
import asyncio
import os
import sys

sys.path.append('src')

from mcp_server.jellyfin_music import JellyfinMusicController, MusicMood

async def debug_chromecast_discovery():
    """Debug the exact same discovery process that music system uses."""
    print("🔍 Debugging Chromecast discovery for music system...")
    
    try:
        # Same discovery method as music system
        print("🔍 Discovering Chromecast devices...")
        chromecasts, browser = pychromecast.get_chromecasts(timeout=10)
        
        print(f"📱 Found {len(chromecasts)} devices:")
        for cc in chromecasts:
            print(f"  • Name: '{cc.name}' | Model: {cc.model_name}")
            
        # Get the configured name from env
        chromecast_name = os.getenv('CHROMECAST_NAME', 'Nest Hub Max')
        print(f"🎯 Looking for configured device: '{chromecast_name}'")
        
        # Test exact matching logic from music system
        target_device = None
        for cc in chromecasts:
            if chromecast_name and cc.name == chromecast_name:
                target_device = cc
                print(f"✅ Found exact match: {cc.name}")
                break
            elif not chromecast_name:
                # Fallback to first available
                target_device = chromecasts[0] if chromecasts else None
                print(f"🔄 Using first available: {target_device.name if target_device else 'None'}")
                break
                
        if not target_device and chromecasts:
            target_device = chromecasts[0]
            print(f"⚠️ No exact match, using first available: {target_device.name}")
        
        if target_device:
            print(f"🎯 Testing connection to {target_device.name}...")
            target_device.wait()
            print(f"✅ Successfully connected to {target_device.name}")
            print(f"📱 Device info: {target_device.device}")
        else:
            print("❌ No target device found")
            
        browser.stop_discovery()
        
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        import traceback
        traceback.print_exc()

async def test_music_controller():
    """Test the actual music controller initialization."""
    print("\n🎵 Testing MusicController initialization...")
    
    jellyfin_url = os.getenv('JELLYFIN_URL', 'http://localhost:8096')
    jellyfin_token = os.getenv('JELLYFIN_TOKEN')
    chromecast_name = os.getenv('CHROMECAST_NAME', 'Nest Hub Max')
    
    if not jellyfin_token:
        print("❌ JELLYFIN_TOKEN not set")
        return
        
    print(f"🔧 Config: URL={jellyfin_url}, Token={jellyfin_token[:10]}..., Cast={chromecast_name}")
    
    try:
        controller = JellyfinMusicController(jellyfin_url, jellyfin_token, chromecast_name)
        await controller.initialize()
        
        print(f"📊 Status: {controller.get_status()}")
        
    except Exception as e:
        print(f"❌ Controller init failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Load .env
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(debug_chromecast_discovery())
    asyncio.run(test_music_controller())