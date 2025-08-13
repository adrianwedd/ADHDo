#!/usr/bin/env python3
"""
Simple music auto-play loop for ADHD support
Checks every minute if music should be playing between 8am-10pm
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, time
import os
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = os.environ.get("BASE_URL", "http://localhost:23444")
CHECK_INTERVAL = 60  # Check every 60 seconds
START_HOUR = 8   # 8 AM
END_HOUR = 22    # 10 PM
DEFAULT_MOOD = "focus"  # Default music mood

async def check_music_status():
    """Check if music is currently playing."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/music/status") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("is_playing", False), data.get("available", False)
                return False, False
    except Exception as e:
        logger.error(f"Failed to check music status: {e}")
        return False, False

async def start_music(mood="focus"):
    """Start playing music."""
    try:
        async with aiohttp.ClientSession() as session:
            # Try the simple endpoint first
            async with session.post(f"{BASE_URL}/music/{mood}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        logger.info(f"✅ Started {mood} music")
                        return True
                    else:
                        logger.warning(f"Music start failed: {data.get('message', 'Unknown error')}")
                elif resp.status == 503:
                    logger.warning("Music system not available")
                return False
    except Exception as e:
        logger.error(f"Failed to start music: {e}")
        return False

async def stop_music():
    """Stop playing music."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE_URL}/music/stop") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        logger.info("⏹️ Stopped music")
                        return True
                return False
    except Exception as e:
        logger.error(f"Failed to stop music: {e}")
        return False

def should_play_music():
    """Check if current time is within music hours."""
    now = datetime.now()
    current_time = now.time()
    start_time = time(START_HOUR, 0)
    end_time = time(END_HOUR, 0)
    
    return start_time <= current_time <= end_time

async def music_autoplay_loop():
    """Main loop that manages music playback."""
    logger.info("🎵 Starting ADHD Music Auto-Play Loop")
    logger.info(f"📍 Server: {BASE_URL}")
    logger.info(f"⏰ Schedule: {START_HOUR}:00 - {END_HOUR}:00")
    logger.info(f"🔄 Check interval: {CHECK_INTERVAL} seconds")
    
    consecutive_failures = 0
    max_failures = 5
    
    while True:
        try:
            # Check if we're in music hours
            in_music_hours = should_play_music()
            current_time = datetime.now().strftime("%H:%M")
            
            # Get current music status
            is_playing, music_available = await check_music_status()
            
            if not music_available:
                logger.warning(f"[{current_time}] Music system not available, waiting...")
                await asyncio.sleep(CHECK_INTERVAL * 5)  # Wait longer if system not ready
                continue
            
            if in_music_hours:
                if not is_playing:
                    logger.info(f"[{current_time}] Music hours active, starting music...")
                    success = await start_music(DEFAULT_MOOD)
                    if success:
                        consecutive_failures = 0
                        logger.info(f"🎧 Music started successfully")
                    else:
                        consecutive_failures += 1
                        logger.warning(f"Failed to start music (attempt {consecutive_failures}/{max_failures})")
                else:
                    # Music is playing, all good
                    consecutive_failures = 0
                    if datetime.now().minute % 10 == 0:  # Log every 10 minutes
                        logger.info(f"[{current_time}] Music playing ✓")
            else:
                # Outside music hours
                if is_playing:
                    logger.info(f"[{current_time}] Outside music hours, stopping music...")
                    await stop_music()
                else:
                    if datetime.now().minute == 0:  # Log once per hour when idle
                        logger.info(f"[{current_time}] Outside music hours, music off")
            
            # Back off if too many failures
            if consecutive_failures >= max_failures:
                logger.error(f"Too many failures, backing off for 5 minutes")
                await asyncio.sleep(300)  # 5 minutes
                consecutive_failures = 0
            else:
                await asyncio.sleep(CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("🛑 Stopping music auto-play loop")
            break
        except Exception as e:
            logger.error(f"Unexpected error in music loop: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

async def test_connection():
    """Test connection to the server."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✅ Server connection OK: {data.get('status', 'unknown')}")
                    return True
                else:
                    logger.error(f"❌ Server returned status {resp.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Cannot connect to server at {BASE_URL}: {e}")
        return False

async def main():
    """Main entry point."""
    print("="*60)
    print("🎵 ADHD MUSIC AUTO-PLAY SYSTEM")
    print("="*60)
    
    # Test server connection first
    if not await test_connection():
        logger.error("Cannot connect to server. Is it running?")
        logger.info(f"Start server with: PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23444 python -m mcp_server.minimal_main")
        return 1
    
    # Check music system status
    is_playing, music_available = await check_music_status()
    if music_available:
        logger.info(f"✅ Music system available")
        if is_playing:
            logger.info(f"🎧 Music currently playing")
    else:
        logger.warning("⚠️ Music system not configured - will keep trying")
    
    # Run the auto-play loop
    try:
        await music_autoplay_loop()
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")
        
        # Stop music if playing
        is_playing, _ = await check_music_status()
        if is_playing:
            logger.info("Stopping music before exit...")
            await stop_music()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)