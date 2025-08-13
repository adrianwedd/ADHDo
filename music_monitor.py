#!/usr/bin/env python3
"""
Music Monitor - Ensures music keeps playing
Checks every minute and restarts if stopped
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:23443"
CHECK_INTERVAL = 60  # Check every minute
RESTART_AFTER_IDLE = 300  # Restart if idle for 5 minutes

class MusicMonitor:
    """Monitors and maintains music playback."""
    
    def __init__(self):
        self.last_track = None
        self.last_change = datetime.now()
        self.idle_count = 0
        
    async def get_status(self):
        """Get current music status."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BASE_URL}/music/status", timeout=5) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
        return None
    
    async def restart_music(self, mood="energy"):
        """Restart music playback."""
        try:
            logger.info(f"🔄 Restarting {mood} music...")
            async with aiohttp.ClientSession() as session:
                # Stop first
                await session.post(f"{BASE_URL}/music/stop")
                await asyncio.sleep(2)
                
                # Start again
                async with session.post(f"{BASE_URL}/music/{mood}", timeout=10) as resp:
                    data = await resp.json()
                    if data.get("success"):
                        logger.info(f"✅ Music restarted successfully")
                        return True
                    else:
                        logger.error(f"Failed to restart: {data.get('message')}")
        except Exception as e:
            logger.error(f"Restart error: {e}")
        return False
    
    async def check_and_fix(self):
        """Check if music is playing and fix if not."""
        status = await self.get_status()
        
        if not status:
            logger.warning("⚠️ Can't get music status")
            return
        
        is_playing = status.get("is_playing", False)
        current_track = status.get("current_track", {}).get("name", "Unknown")
        
        # Check if music should be playing (8am - 10pm)
        now = datetime.now()
        should_play = 8 <= now.hour < 22
        
        if should_play:
            if not is_playing:
                logger.warning("❌ Music stopped! Restarting...")
                await self.restart_music()
                self.last_track = None
                self.last_change = datetime.now()
                self.idle_count = 0
                
            elif current_track == self.last_track:
                # Same track for multiple checks
                self.idle_count += 1
                idle_minutes = self.idle_count * (CHECK_INTERVAL / 60)
                
                if self.idle_count >= (RESTART_AFTER_IDLE / CHECK_INTERVAL):
                    logger.warning(f"⚠️ Music stuck on '{current_track}' for {idle_minutes:.0f} minutes")
                    await self.restart_music()
                    self.idle_count = 0
                else:
                    logger.info(f"🎵 Still playing: {current_track} ({idle_minutes:.0f}m)")
            else:
                # Track changed, all good
                if self.last_track:
                    logger.info(f"✅ Track changed: {current_track}")
                else:
                    logger.info(f"🎵 Now playing: {current_track}")
                    
                self.last_track = current_track
                self.last_change = datetime.now()
                self.idle_count = 0
        else:
            if is_playing:
                logger.info("🌙 Outside music hours, stopping...")
                async with aiohttp.ClientSession() as session:
                    await session.post(f"{BASE_URL}/music/stop")
            else:
                # Log once per hour during quiet time
                if now.minute == 0:
                    logger.info(f"😴 Quiet hours ({now.hour}:00)")
    
    async def run_monitor(self):
        """Main monitoring loop."""
        logger.info("🎵 Music Monitor Started")
        logger.info(f"📍 Monitoring: {BASE_URL}")
        logger.info(f"⏱️ Check interval: {CHECK_INTERVAL}s")
        logger.info(f"🔄 Auto-restart if stuck for {RESTART_AFTER_IDLE/60:.0f} minutes")
        logger.info("="*50)
        
        while True:
            try:
                await self.check_and_fix()
                await asyncio.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("\n👋 Music monitor stopped")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(CHECK_INTERVAL)

async def main():
    """Run the music monitor."""
    # Check server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health", timeout=2) as resp:
                if resp.status != 200:
                    logger.error(f"❌ Server not responding at {BASE_URL}")
                    return 1
    except:
        logger.error(f"❌ Cannot connect to server at {BASE_URL}")
        logger.info("Start server first:")
        logger.info("PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23443 python -m mcp_server.minimal_main")
        return 1
    
    # Check current status
    monitor = MusicMonitor()
    status = await monitor.get_status()
    
    if status:
        if status.get("is_playing"):
            track = status.get("current_track", {}).get("name", "Unknown")
            logger.info(f"✅ Music is playing: {track}")
        else:
            logger.info("⚠️ Music is not playing")
            
            # Try to start it
            now = datetime.now()
            if 8 <= now.hour < 22:
                logger.info("Starting music...")
                await monitor.restart_music()
    
    # Run monitor
    await monitor.run_monitor()
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)