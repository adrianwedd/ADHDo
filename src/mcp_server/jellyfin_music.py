"""
Jellyfin Music Controller for ADHD Support
Fixed version with proper API endpoints and demo tracks
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Dict, List, Optional
import aiohttp
import pychromecast

logger = logging.getLogger(__name__)

class MusicMood(Enum):
    """ADHD-optimized music moods."""
    FOCUS = "focus"
    ENERGY = "energy"
    CALM = "calm"
    AMBIENT = "ambient"
    NATURE = "nature"
    STUDY = "study"

@dataclass
class JellyfinTrack:
    """Represents a track from Jellyfin."""
    id: str
    name: str
    artist: str
    duration_seconds: int
    stream_url: str

@dataclass
class PlaybackState:
    """Current playback state."""
    is_playing: bool = False
    current_track: Optional[JellyfinTrack] = None
    volume: float = 0.75
    chromecast_connected: bool = False
    last_activity: Optional[datetime] = None

class JellyfinMusicController:
    """Controls music playback from Jellyfin to Chromecast Audio."""
    
    def __init__(self, jellyfin_url: str, api_key: str, chromecast_name: str = None):
        self.jellyfin_url = jellyfin_url.rstrip('/')
        self.api_key = api_key
        self.chromecast_name = chromecast_name
        
        # Session for API calls
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Chromecast components
        self.chromecast: Optional[pychromecast.Chromecast] = None
        self.media_controller = None
        
        # Music organization
        self.playlists: Dict[MusicMood, List[JellyfinTrack]] = {
            mood: [] for mood in MusicMood
        }
        
        # Playback state
        self.state = PlaybackState()
        
        # Background scheduler
        self.scheduler_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> bool:
        """Initialize the music controller."""
        try:
            logger.info("🎵 Initializing Jellyfin music controller")
            
            # Create session with auth headers
            self.session = aiohttp.ClientSession(
                headers={'X-Emby-Token': self.api_key}
            )
            
            # Test Jellyfin connection
            if not await self._test_jellyfin_connection():
                return False
            
            # Load playlists
            await self._load_adhd_playlists()
            
            # Initialize Chromecast (don't fail if not available)
            await self._initialize_chromecast()
            
            # Start background scheduler
            self.scheduler_task = asyncio.create_task(self._music_scheduler())
            
            logger.info("🎧 Jellyfin music controller ready")
            return True
            
        except Exception as e:
            logger.error(f"❌ Music initialization failed: {e}")
            return False
    
    async def _test_jellyfin_connection(self) -> bool:
        """Test Jellyfin server connectivity."""
        try:
            async with self.session.get(f"{self.jellyfin_url}/System/Info/Public") as response:
                if response.status == 200:
                    info = await response.json()
                    logger.info(f"Connected to Jellyfin: {info.get('ServerName', 'Unknown')}")
                    logger.info("✅ Jellyfin connection successful")
                    return True
                logger.error(f"Jellyfin connection failed: {response.status}")
                return False
        except Exception as e:
            logger.error(f"❌ Jellyfin unreachable: {e}")
            return False
    
    async def _load_adhd_playlists(self):
        """Load ADHD-optimized music collections."""
        try:
            # Load real music from Jellyfin
            logger.info("🎵 Loading music from Jellyfin library")
            
            # Get all audio items from Jellyfin
            async with self.session.get(
                f"{self.jellyfin_url}/Items",
                params={
                    "IncludeItemTypes": "Audio",
                    "Recursive": "true",
                    "Fields": "Path,MediaSources,Genres,Artists,AlbumArtist",
                    "Limit": 5000  # Load more tracks from your 600GB library
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('Items', [])
                    logger.info(f"Found {len(items)} audio tracks in Jellyfin")
                    
                    # Organize tracks by genre/mood
                    for item in items:
                        track = JellyfinTrack(
                            id=item['Id'],
                            name=item.get('Name', 'Unknown'),
                            artist=item.get('AlbumArtist', item.get('Artists', ['Unknown'])[0] if item.get('Artists') else 'Unknown'),
                            duration_seconds=item.get('RunTimeTicks', 0) // 10000000 if item.get('RunTimeTicks') else 180,
                            stream_url=f"{self.jellyfin_url.replace('localhost', '192.168.1.100')}/Audio/{item['Id']}/stream?api_key={self.api_key}"
                        )
                        
                        # Categorize by genre or use smart categorization
                        genres = [g.lower() for g in item.get('Genres', [])]
                        
                        # Smart mood mapping based on genres
                        if any(g in genres for g in ['classical', 'piano', 'instrumental', 'ambient']):
                            self.playlists[MusicMood.FOCUS].append(track)
                            self.playlists[MusicMood.STUDY].append(track)
                        if any(g in genres for g in ['electronic', 'dance', 'rock', 'pop']):
                            self.playlists[MusicMood.ENERGY].append(track)
                        if any(g in genres for g in ['meditation', 'relaxation', 'new age', 'spa']):
                            self.playlists[MusicMood.CALM].append(track)
                        if any(g in genres for g in ['ambient', 'atmospheric', 'drone']):
                            self.playlists[MusicMood.AMBIENT].append(track)
                        if any(g in genres for g in ['nature', 'soundscape', 'field recording']):
                            self.playlists[MusicMood.NATURE].append(track)
                        
                        # If no genre matches, add to focus as default
                        if not any(self.playlists[mood] for mood in MusicMood):
                            self.playlists[MusicMood.FOCUS].append(track)
                else:
                    logger.warning(f"Failed to load Jellyfin library: {response.status}")
            
            # Log loaded playlists
            for mood, tracks in self.playlists.items():
                if tracks:
                    logger.info(f"📚 Loaded {len(tracks)} {mood.value} demo tracks")
        
        except Exception as e:
            logger.error(f"❌ Failed to load playlists: {e}")
    
    async def _initialize_chromecast_async(self):
        """Initialize Chromecast in background without blocking."""
        await asyncio.sleep(2)  # Give system time to stabilize
        await self._initialize_chromecast()
        if self.state.chromecast_connected:
            logger.info("🎵 Chromecast ready for playback!")
    
    async def _initialize_chromecast(self):
        """Initialize Chromecast Audio connection."""
        try:
            logger.info("🔍 Discovering Chromecast devices...")
            
            # Use blocking discovery with longer timeout for better results
            import time
            chromecasts, browser = pychromecast.get_chromecasts(timeout=10)
            
            if chromecasts:
                logger.info(f"Found {len(chromecasts)} Chromecast device(s):")
                for cc in chromecasts:
                    logger.info(f"  - {cc.name} ({cc.model_name})")
                
                # Find the specific device
                target_device = None
                if self.chromecast_name:
                    for cc in chromecasts:
                        if cc.name == self.chromecast_name:
                            target_device = cc
                            logger.info(f"Found target device: {cc.name}")
                            break
                
                if not target_device and chromecasts:
                    target_device = chromecasts[0]
                    logger.info(f"Using first available: {target_device.name}")
                
                if target_device:
                    self.chromecast = target_device
                    self.chromecast.wait()
                    self.media_controller = self.chromecast.media_controller
                    self.state.chromecast_connected = True
                    logger.info(f"✅ Connected to Chromecast: {self.chromecast.name}")
                else:
                    logger.warning(f"⚠️ Chromecast '{self.chromecast_name}' not found")
                    self.state.chromecast_connected = False
            else:
                logger.warning("⚠️ No Chromecast devices found on network")
                self.state.chromecast_connected = False
            
            # Stop the browser to free resources
            browser.stop_discovery()
            
        except Exception as e:
            logger.error(f"❌ Chromecast initialization failed: {e}")
            self.state.chromecast_connected = False
    
    async def play_mood_playlist(self, mood: MusicMood, volume: float = None, shuffle: bool = True):
        """Play a mood-based playlist."""
        if mood not in self.playlists or not self.playlists[mood]:
            logger.warning(f"⚠️ No tracks available for mood: {mood.value}")
            return False
        
        try:
            tracks = self.playlists[mood].copy()
            if shuffle:
                import random
                random.shuffle(tracks)
            
            # Play the actual track
            track = tracks[0]
            logger.info(f"🎵 Playing: {track.name} by {track.artist} ({mood.value} mood)")
            
            # Cast to Chromecast if connected
            if self.state.chromecast_connected and self.media_controller:
                # Replace localhost with actual IP for Chromecast access
                stream_url = track.stream_url.replace('localhost', '192.168.1.100')
                
                self.media_controller.play_media(
                    stream_url,
                    'audio/mpeg'
                )
                self.media_controller.block_until_active()
                
                # Set volume
                if volume is not None:
                    self.chromecast.set_volume(volume)
                else:
                    self.chromecast.set_volume(self.state.volume)
                
                logger.info(f"🎧 Now playing on {self.chromecast.device.friendly_name}")
            else:
                logger.warning("⚠️ Chromecast not connected, playing locally (simulated)")
            
            # Update state
            self.state.is_playing = True
            self.state.current_track = track
            if volume is not None:
                self.state.volume = volume
            self.state.last_activity = datetime.now()
            
            logger.info(f"✅ Started {mood.value} playlist")
            return True
            
        except Exception as e:
            logger.error(f"❌ Playback failed: {e}")
            return False
    
    async def stop_music(self):
        """Stop music playback."""
        try:
            logger.info("⏹️ Stopping music")
            
            # Stop Chromecast playback if connected
            if self.state.chromecast_connected and self.media_controller:
                self.media_controller.stop()
                logger.info(f"🔇 Stopped playback on {self.chromecast.device.friendly_name}")
            
            self.state.is_playing = False
            self.state.current_track = None
            return True
        except Exception as e:
            logger.error(f"❌ Stop failed: {e}")
            return False
    
    async def set_volume(self, volume: float):
        """Set playback volume (0.0 - 1.0)."""
        try:
            volume = max(0.0, min(1.0, volume))
            self.state.volume = volume
            
            # Set Chromecast volume if connected
            if self.state.chromecast_connected and self.chromecast:
                self.chromecast.set_volume(volume)
                logger.info(f"🔊 Volume set to {int(volume * 100)}% on {self.chromecast.name}")
            else:
                logger.info(f"🔊 Volume set to {int(volume * 100)}% (local)")
            
            return True
        except Exception as e:
            logger.error(f"❌ Volume change failed: {e}")
            return False
    
    async def _music_scheduler(self):
        """Background task to manage automatic music based on time and activity."""
        logger.info("⏰ Starting ADHD music scheduler")
        
        while True:
            try:
                now = datetime.now()
                current_time = now.time()
                
                # Only play between 9 AM and 9 PM
                if time(9, 0) <= current_time <= time(21, 0):
                    # Check if we should start ambient music
                    if not self.state.is_playing and not self._is_system_audio_active():
                        logger.info("🎵 Starting ambient focus music (silence detected)")
                        await self.play_mood_playlist(MusicMood.FOCUS, volume=0.75)
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Music scheduler error: {e}")
                await asyncio.sleep(60)
    
    def _is_system_audio_active(self) -> bool:
        """Check if other system audio is playing."""
        # Simplified - assume no other audio
        return False
    
    def get_status(self) -> Dict:
        """Get current playback status."""
        return {
            "is_playing": self.state.is_playing,
            "current_track": {
                "name": self.state.current_track.name,
                "artist": self.state.current_track.artist,
                "mood": self._get_track_mood(self.state.current_track)
            } if self.state.current_track else None,
            "volume": self.state.volume,
            "chromecast_connected": self.state.chromecast_connected,
            "available_moods": [mood.value for mood in MusicMood if self.playlists[mood]]
        }
    
    def _get_track_mood(self, track: JellyfinTrack) -> str:
        """Get the mood of a track."""
        for mood, tracks in self.playlists.items():
            if any(t.id == track.id for t in tracks):
                return mood.value
        return "unknown"
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.scheduler_task:
                self.scheduler_task.cancel()
                await asyncio.gather(self.scheduler_task, return_exceptions=True)
            
            if self.session:
                await self.session.close()
            
            logger.info("🎵 Jellyfin music controller shut down")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# Global instance
jellyfin_music: Optional[JellyfinMusicController] = None

async def initialize_music_controller(jellyfin_url: str, jellyfin_token: str, chromecast_name: str = None) -> bool:
    """Initialize the global music controller."""
    global jellyfin_music
    
    try:
        jellyfin_music = JellyfinMusicController(
            jellyfin_url=jellyfin_url,
            api_key=jellyfin_token,
            chromecast_name=chromecast_name
        )
        
        success = await jellyfin_music.initialize()
        if not success:
            jellyfin_music = None
            return False
        
        logger.info("🎧 Music system initialized for ADHD focus support")
        return True
        
    except Exception as e:
        logger.error(f"❌ Music system initialization failed: {e}")
        jellyfin_music = None
        return False