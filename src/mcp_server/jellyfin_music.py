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
from dataclasses import field
import random
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
    # Queue management
    queue: List[JellyfinTrack] = field(default_factory=list)
    queue_index: int = 0
    repeat_mode: str = "all"  # off, one, all
    shuffle: bool = False
    playback_monitor_task: Optional[asyncio.Task] = None

class JellyfinMusicController:
    """Controls music playback from Jellyfin to Chromecast Audio."""
    
    def __init__(self, jellyfin_url: str, api_key: str, chromecast_name: str = None, user_id: str = None):
        self.jellyfin_url = jellyfin_url.rstrip('/')
        self.api_key = api_key
        self.chromecast_name = chromecast_name
        self.user_id = user_id  # Add user_id for playlist management
        
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
            
            # Load existing playlists and create ADHD ones if needed
            await self._load_and_create_adhd_playlists()
            
            # Load actual tracks into mood playlists
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
    
    async def _get_default_user_id(self):
        """Get default user ID from Jellyfin for playlist operations."""
        try:
            async with self.session.get(f"{self.jellyfin_url}/Users") as response:
                if response.status == 200:
                    users = await response.json()
                    if users:
                        # Use first user (usually admin or primary user)
                        self.user_id = users[0]['Id']
                        logger.info(f"Using user: {users[0].get('Name', 'Unknown')} ({self.user_id})")
                    else:
                        logger.warning("No users found in Jellyfin")
                else:
                    logger.error(f"Failed to get users: {response.status}")
        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
    
    async def _load_adhd_playlists(self):
        """Load ADHD-optimized music collections."""
        try:
            # Load real music from Jellyfin
            logger.info("🎵 Loading music from Jellyfin library")
            
            # Set default user_id if not provided (get from system info)
            if not self.user_id:
                await self._get_default_user_id()
            
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
                        # Use network-accessible URL for Chromecast
                        jellyfin_network_url = self.jellyfin_url.replace('localhost', '192.168.1.100')
                        track = JellyfinTrack(
                            id=item['Id'],
                            name=item.get('Name', 'Unknown'),
                            artist=item.get('AlbumArtist', item.get('Artists', ['Unknown'])[0] if item.get('Artists') else 'Unknown'),
                            duration_seconds=item.get('RunTimeTicks', 0) // 10000000 if item.get('RunTimeTicks') else 180,
                            stream_url=f"{jellyfin_network_url}/Items/{item['Id']}/Download?api_key={self.api_key}"
                        )
                        
                        # Categorize by genre or use smart categorization
                        genres = [g.lower() for g in item.get('Genres', [])]
                        
                        # Smart mood mapping based on genres
                        track_added = False
                        
                        if any(g in genres for g in ['classical', 'piano', 'instrumental', 'ambient', 'lo-fi']):
                            self.playlists[MusicMood.FOCUS].append(track)
                            self.playlists[MusicMood.STUDY].append(track)
                            track_added = True
                        if any(g in genres for g in ['electronic', 'dance', 'rock', 'pop', 'techno', 'house']):
                            self.playlists[MusicMood.ENERGY].append(track)
                            track_added = True
                        if any(g in genres for g in ['meditation', 'relaxation', 'new age', 'spa', 'chill']):
                            self.playlists[MusicMood.CALM].append(track)
                            track_added = True
                        if any(g in genres for g in ['ambient', 'atmospheric', 'drone', 'dub techno']):
                            self.playlists[MusicMood.AMBIENT].append(track)
                            track_added = True
                        if any(g in genres for g in ['nature', 'soundscape', 'field recording']):
                            self.playlists[MusicMood.NATURE].append(track)
                            track_added = True
                        
                        # If no genre matches, add to focus as default
                        if not track_added:
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
            
            # Use fresh discovery approach like nudge system (which works)
            loop = asyncio.get_event_loop()
            chromecasts, browser = await loop.run_in_executor(
                None,
                lambda: pychromecast.get_chromecasts(timeout=15)
            )
            
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
                    # Wait for connection using executor (like nudge system)
                    await loop.run_in_executor(None, target_device.wait)
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
        """Play a mood-based playlist with queue management."""
        if mood not in self.playlists or not self.playlists[mood]:
            logger.warning(f"⚠️ No tracks available for mood: {mood.value}")
            return False
        
        try:
            # Build queue
            tracks = self.playlists[mood].copy()
            if shuffle:
                random.shuffle(tracks)
            
            # Set up queue
            self.state.queue = tracks
            self.state.queue_index = 0
            self.state.shuffle = shuffle
            
            logger.info(f"📚 Queue loaded with {len(tracks)} {mood.value} tracks")
            
            # Play first track
            track = tracks[0]
            success = await self._play_track_internal(track, volume)
            
            if success:
                logger.info(f"✅ Started {mood.value} playlist with {len(tracks)} tracks")
                # Start monitoring for next track
                if self.state.playback_monitor_task:
                    self.state.playback_monitor_task.cancel()
                self.state.playback_monitor_task = asyncio.create_task(
                    self._monitor_and_play_next(track.duration_seconds)
                )
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Playback failed: {e}")
            return False
    
    async def _play_track_internal(self, track: JellyfinTrack, volume: float = None) -> bool:
        """Internal method to play a single track."""
        try:
            logger.info(f"🎵 Playing: {track.name} by {track.artist}")
            
            # Cast to Chromecast if connected
            if self.state.chromecast_connected and self.media_controller:
                # Use the URL as-is (already has the tunnel URL)
                stream_url = track.stream_url
                logger.info(f"🔗 Stream URL: {stream_url}")
                
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
                
                logger.info(f"🎧 Now playing on {self.chromecast.name}")
            else:
                logger.warning("⚠️ Chromecast not connected, playing locally (simulated)")
            
            # Update state
            self.state.is_playing = True
            self.state.current_track = track
            if volume is not None:
                self.state.volume = volume
            self.state.last_activity = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Track playback failed: {e}")
            return False
    
    async def _monitor_and_play_next(self, duration_seconds: int):
        """Monitor playback and automatically play next track."""
        try:
            # Don't rely on duration - just monitor Chromecast status
            # Wait at least 30 seconds before checking (prevent premature advance)
            await asyncio.sleep(30)
            
            # Check if still playing every 10 seconds
            if self.media_controller:
                while True:
                    await asyncio.sleep(10)
                    if self.media_controller.status.player_state != "PLAYING":
                        logger.info(f"⏹️ Playback stopped, advancing to next track")
                        break
            
            logger.info(f"✅ Track finished: {self.state.current_track.name if self.state.current_track else 'Unknown'}")
            
            # Play next track in queue
            if self.state.queue and len(self.state.queue) > 0:
                # Move to next track
                self.state.queue_index += 1
                
                # Handle repeat modes
                if self.state.queue_index >= len(self.state.queue):
                    if self.state.repeat_mode == "all":
                        self.state.queue_index = 0
                        logger.info("🔁 Restarting playlist from beginning")
                    elif self.state.repeat_mode == "off":
                        logger.info("⏹️ Playlist finished")
                        self.state.is_playing = False
                        self.state.current_track = None
                        return
                elif self.state.repeat_mode == "one":
                    self.state.queue_index -= 1  # Stay on same track
                    logger.info("🔂 Repeating current track")
                
                # Play next track
                if self.state.queue_index < len(self.state.queue):
                    next_track = self.state.queue[self.state.queue_index]
                    logger.info(f"⏭️ Playing next: {next_track.name} by {next_track.artist}")
                    
                    success = await self._play_track_internal(next_track)
                    if success:
                        # Continue monitoring
                        self.state.playback_monitor_task = asyncio.create_task(
                            self._monitor_and_play_next(next_track.duration_seconds)
                        )
            else:
                logger.info("📭 Queue is empty")
                self.state.is_playing = False
                self.state.current_track = None
                
        except asyncio.CancelledError:
            logger.info("Playback monitoring cancelled")
        except Exception as e:
            logger.error(f"Playback monitoring error: {e}")
            self.state.is_playing = False
    
    async def skip_track(self) -> bool:
        """Skip to next track in queue."""
        try:
            if not self.state.queue or self.state.queue_index >= len(self.state.queue) - 1:
                logger.info("No more tracks in queue")
                return False
            
            # Cancel current monitor
            if self.state.playback_monitor_task:
                self.state.playback_monitor_task.cancel()
            
            # Stop current playback
            if self.media_controller:
                self.media_controller.stop()
            
            # Move to next track
            self.state.queue_index += 1
            next_track = self.state.queue[self.state.queue_index]
            
            logger.info(f"⏭️ Skipping to: {next_track.name}")
            success = await self._play_track_internal(next_track)
            
            if success:
                # Start monitoring new track
                self.state.playback_monitor_task = asyncio.create_task(
                    self._monitor_and_play_next(next_track.duration_seconds)
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Skip failed: {e}")
            return False
    
    async def stop_music(self):
        """Stop music playback."""
        try:
            logger.info("⏹️ Stopping music")
            
            # Cancel monitor task
            if self.state.playback_monitor_task:
                self.state.playback_monitor_task.cancel()
                self.state.playback_monitor_task = None
            
            # Stop Chromecast playback if connected
            if self.state.chromecast_connected and self.media_controller:
                self.media_controller.stop()
                logger.info(f"🔇 Stopped playback on {self.chromecast.name}")
            
            self.state.is_playing = False
            self.state.current_track = None
            self.state.queue = []
            self.state.queue_index = 0
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
        last_music_start = 0
        
        while True:
            try:
                # Check if auto music changes are locked
                auto_change_locked = False
                try:
                    # Import here to avoid circular imports
                    from mcp_server.minimal_main import redis_client
                    if redis_client:
                        lock_status = await redis_client.get("music:auto_change_locked")
                        auto_change_locked = lock_status == "true"
                except:
                    auto_change_locked = False
                
                # Also check instance variable if set
                if hasattr(self, 'auto_change_enabled'):
                    auto_change_locked = not self.auto_change_enabled
                
                if auto_change_locked:
                    logger.debug("🔒 Music auto-change is locked, skipping scheduler")
                    await asyncio.sleep(30)
                    continue
                
                now = datetime.now()
                current_time = now.time()
                current_timestamp = now.timestamp()
                
                # Only play between 9 AM and midnight
                if time(9, 0) <= current_time or current_time <= time(0, 0):
                    # Check if we should start ambient music
                    # Add cooldown: don't restart if music was started in last 5 minutes
                    time_since_last_start = current_timestamp - last_music_start
                    
                    if (not self.state.is_playing and 
                        not self._is_system_audio_active() and 
                        time_since_last_start > 300):  # 5 minute cooldown
                        
                        logger.info("🎵 Starting ambient focus music (silence detected)")
                        await self.play_mood_playlist(MusicMood.FOCUS, volume=0.75)
                        last_music_start = current_timestamp
                    elif time_since_last_start <= 300 and not self.state.is_playing:
                        logger.debug(f"🔄 Music restart cooldown: {300 - time_since_last_start:.0f}s remaining")
                
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
            "queue": {
                "total": len(self.state.queue),
                "current_index": self.state.queue_index,
                "next_track": self.state.queue[self.state.queue_index + 1].name if self.state.queue_index + 1 < len(self.state.queue) else None,
                "repeat_mode": self.state.repeat_mode,
                "shuffle": self.state.shuffle
            },
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
    
    # Playlist Management Methods
    async def _load_and_create_adhd_playlists(self):
        """Load existing playlists and create ADHD-specific ones if needed."""
        try:
            # Get existing playlists
            playlists = await self._get_jellyfin_playlists()
            existing_names = [p['Name'] for p in playlists]
            
            # ADHD playlist templates
            adhd_playlists = {
                "ADHD Deep Focus": {
                    "description": "Long ambient tracks for sustained attention",
                    "moods": [MusicMood.FOCUS, MusicMood.AMBIENT],
                    "max_tracks": 50
                },
                "ADHD Energy Boost": {
                    "description": "Upbeat music for task transitions",
                    "moods": [MusicMood.ENERGY],
                    "max_tracks": 30
                },
                "ADHD Anxiety Relief": {
                    "description": "Calming tracks for overwhelm moments", 
                    "moods": [MusicMood.CALM, MusicMood.NATURE],
                    "max_tracks": 40
                },
                "ADHD Pomodoro Focus": {
                    "description": "25-minute focus work sessions",
                    "moods": [MusicMood.FOCUS, MusicMood.STUDY],
                    "target_duration": 25 * 60  # 25 minutes
                }
            }
            
            # Create missing ADHD playlists
            for name, config in adhd_playlists.items():
                if name not in existing_names:
                    logger.info(f"🎵 Creating ADHD playlist: {name}")
                    await self._create_adhd_playlist(name, config)
            
            logger.info("✅ ADHD playlists loaded/created")
            
        except Exception as e:
            logger.error(f"❌ Failed to load ADHD playlists: {e}")
    
    async def _get_jellyfin_playlists(self):
        """Get all playlists from Jellyfin."""
        try:
            url = f"{self.jellyfin_url}/Users/{self.user_id}/Items"
            params = {
                'IncludeItemTypes': 'Playlist',
                'Recursive': 'true',
                'Fields': 'DateCreated,MediaStreams'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('Items', [])
                else:
                    logger.error(f"Failed to get playlists: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting playlists: {e}")
            return []
    
    async def _create_adhd_playlist(self, name: str, config: dict):
        """Create an ADHD-specific playlist with curated tracks."""
        try:
            # Create empty playlist
            playlist_id = await self._create_empty_playlist(name, config.get('description', ''))
            if not playlist_id:
                return False
            
            # Get tracks for the playlist based on moods
            tracks = []
            for mood in config.get('moods', []):
                mood_tracks = self.playlists.get(mood, [])
                tracks.extend(mood_tracks[:config.get('max_tracks', 30)])
            
            # Add tracks to playlist
            if tracks:
                await self._add_tracks_to_playlist(playlist_id, tracks[:config.get('max_tracks', 50)])
                logger.info(f"✅ Created '{name}' with {len(tracks)} tracks")
                return True
            else:
                logger.warning(f"⚠️ No tracks found for playlist '{name}'")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to create playlist '{name}': {e}")
            return False
    
    async def _create_empty_playlist(self, name: str, description: str = "") -> Optional[str]:
        """Create an empty playlist and return its ID."""
        try:
            url = f"{self.jellyfin_url}/Playlists"
            data = {
                'Name': name,
                'MediaType': 'Audio',
                'UserId': self.user_id
            }
            
            if description:
                data['Overview'] = description
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('Id')
                else:
                    logger.error(f"Failed to create playlist: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            return None
    
    async def _add_tracks_to_playlist(self, playlist_id: str, tracks: List[JellyfinTrack]):
        """Add tracks to an existing playlist."""
        try:
            # Convert tracks to item IDs
            item_ids = []
            for track in tracks:
                # Extract ID from stream URL if needed
                if '/Items/' in track.stream_url:
                    item_id = track.stream_url.split('/Items/')[1].split('/')[0]
                    item_ids.append(item_id)
            
            if not item_ids:
                return False
            
            url = f"{self.jellyfin_url}/Playlists/{playlist_id}/Items"
            params = {'Ids': ','.join(item_ids)}
            
            async with self.session.post(url, params=params) as response:
                if response.status == 204:  # Jellyfin returns 204 for successful playlist additions
                    logger.info(f"✅ Added {len(item_ids)} tracks to playlist")
                    return True
                else:
                    logger.error(f"Failed to add tracks to playlist: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error adding tracks to playlist: {e}")
            return False
    
    async def play_playlist(self, playlist_name: str, shuffle: bool = True):
        """Play a specific playlist by name."""
        try:
            playlists = await self._get_jellyfin_playlists()
            target_playlist = None
            
            for playlist in playlists:
                if playlist['Name'].lower() == playlist_name.lower():
                    target_playlist = playlist
                    break
            
            if not target_playlist:
                logger.error(f"Playlist '{playlist_name}' not found")
                return False
            
            # Get playlist items
            tracks = await self._get_playlist_tracks(target_playlist['Id'])
            if not tracks:
                logger.error(f"Playlist '{playlist_name}' is empty")
                return False
            
            # Update state and play
            self.state.queue = tracks
            self.state.queue_index = 0
            self.state.is_playing = True
            
            if shuffle:
                import random
                random.shuffle(self.state.queue)
            
            first_track = self.state.queue[0]
            success = await self._play_track_internal(first_track)
            
            if success:
                logger.info(f"🎵 Playing playlist '{playlist_name}' with {len(tracks)} tracks")
                self.state.playback_monitor_task = asyncio.create_task(
                    self._monitor_and_play_next(first_track.duration_seconds)
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to play playlist '{playlist_name}': {e}")
            return False
    
    async def play_playlist_by_name(self, name: str) -> bool:
        """Play a playlist by exact name match."""
        try:
            # Search for playlists
            url = f"{self.jellyfin_url}/Items"
            params = {
                'UserId': self.user_id,
                'IncludeItemTypes': 'Playlist',
                'Recursive': 'true',
                'SearchTerm': name
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('Items', [])
                    
                    # Look for exact match
                    for item in items:
                        if item.get('Name', '').lower() == name.lower():
                            return await self.play_playlist(item['Name'])
                    
                    # No exact match found
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to search playlists: {e}")
            return False
    
    async def play_playlist_by_partial_name(self, name: str) -> bool:
        """Play a playlist by partial name match."""
        try:
            # Search for playlists
            url = f"{self.jellyfin_url}/Items"
            params = {
                'UserId': self.user_id,
                'IncludeItemTypes': 'Playlist',
                'Recursive': 'true',
                'SearchTerm': name
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('Items', [])
                    
                    # Look for partial match
                    for item in items:
                        if name.lower() in item.get('Name', '').lower():
                            logger.info(f"Found playlist: {item['Name']}")
                            return await self.play_playlist(item['Name'])
                    
                    # No match found
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to search playlists: {e}")
            return False
    
    async def play_by_artist(self, artist_name: str) -> bool:
        """Play all tracks by an artist."""
        try:
            url = f"{self.jellyfin_url}/Items"
            params = {
                'UserId': self.user_id,
                'IncludeItemTypes': 'Audio',
                'Recursive': 'true',
                'Artists': artist_name,
                'SortBy': 'Album,IndexNumber',
                'Limit': '200'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('Items', [])
                    
                    if items:
                        # Build queue from artist tracks
                        tracks = []
                        for item in items:
                            jellyfin_network_url = self.jellyfin_url.replace('localhost', '192.168.1.100')
                            track = JellyfinTrack(
                                id=item['Id'],
                                name=item.get('Name', 'Unknown'),
                                artist=artist_name,
                                duration_seconds=item.get('RunTimeTicks', 0) // 10000000 if item.get('RunTimeTicks') else 180,
                                stream_url=f"{jellyfin_network_url}/Items/{item['Id']}/Download?api_key={self.api_key}"
                            )
                            tracks.append(track)
                        
                        self.state.queue = tracks
                        self.state.queue_index = 0
                        logger.info(f"📚 Queue loaded with {len(tracks)} tracks by {artist_name}")
                        
                        # Play first track
                        return await self.play_track(tracks[0])
                    
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to play artist {artist_name}: {e}")
            return False
    
    async def play_by_album(self, album_name: str) -> bool:
        """Play a specific album."""
        try:
            # First find the album
            url = f"{self.jellyfin_url}/Items"
            params = {
                'UserId': self.user_id,
                'IncludeItemTypes': 'MusicAlbum',
                'Recursive': 'true',
                'SearchTerm': album_name,
                'Limit': '10'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    albums = data.get('Items', [])
                    
                    if albums:
                        # Get tracks from first matching album
                        album = albums[0]
                        album_id = album['Id']
                        
                        # Get album tracks
                        params = {
                            'UserId': self.user_id,
                            'ParentId': album_id,
                            'IncludeItemTypes': 'Audio',
                            'SortBy': 'IndexNumber'
                        }
                        
                        async with self.session.get(url, params=params) as track_response:
                            if track_response.status == 200:
                                track_data = await track_response.json()
                                items = track_data.get('Items', [])
                                
                                if items:
                                    tracks = []
                                    for item in items:
                                        jellyfin_network_url = self.jellyfin_url.replace('localhost', '192.168.1.100')
                                        track = JellyfinTrack(
                                            id=item['Id'],
                                            name=item.get('Name', 'Unknown'),
                                            artist=item.get('AlbumArtist', 'Unknown'),
                                            duration_seconds=item.get('RunTimeTicks', 0) // 10000000 if item.get('RunTimeTicks') else 180,
                                            stream_url=f"{jellyfin_network_url}/Items/{item['Id']}/Download?api_key={self.api_key}"
                                        )
                                        tracks.append(track)
                                    
                                    self.state.queue = tracks
                                    self.state.queue_index = 0
                                    logger.info(f"📚 Queue loaded with album '{album['Name']}' ({len(tracks)} tracks)")
                                    
                                    # Play first track
                                    return await self._play_track(tracks[0])
                    
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to play album {album_name}: {e}")
            return False
    
    async def _get_playlist_tracks(self, playlist_id: str) -> List[JellyfinTrack]:
        """Get tracks from a specific playlist."""
        try:
            url = f"{self.jellyfin_url}/Playlists/{playlist_id}/Items"
            params = {
                'Fields': 'MediaStreams,Path,RunTimeTicks',
                'MediaTypes': 'Audio'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    tracks = []
                    
                    for item in data.get('Items', []):
                        # Use network-accessible URL for Chromecast
                        jellyfin_network_url = self.jellyfin_url.replace('localhost', '192.168.1.100')
                        track = JellyfinTrack(
                            id=item['Id'],
                            name=item.get('Name', 'Unknown'),
                            artist=item.get('AlbumArtist', item.get('Artists', ['Unknown'])[0] if item.get('Artists') else 'Unknown'),
                            duration_seconds=item.get('RunTimeTicks', 0) // 10000000 if item.get('RunTimeTicks') else 180,
                            stream_url=f"{jellyfin_network_url}/Items/{item['Id']}/Download?api_key={self.api_key}"
                        )
                        tracks.append(track)
                    
                    return tracks
                else:
                    logger.error(f"Failed to get playlist tracks: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting playlist tracks: {e}")
            return []
    
    async def list_playlists(self):
        """List all available playlists."""
        try:
            playlists = await self._get_jellyfin_playlists()
            result = []
            
            for playlist in playlists:
                # Get track count
                tracks = await self._get_playlist_tracks(playlist['Id'])
                result.append({
                    'id': playlist['Id'],
                    'name': playlist['Name'],
                    'description': playlist.get('Overview', ''),
                    'track_count': len(tracks),
                    'created': playlist.get('DateCreated', ''),
                    'is_adhd': playlist['Name'].startswith('ADHD')
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing playlists: {e}")
            return []
    
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

async def initialize_music_controller(jellyfin_url: str, jellyfin_token: str, chromecast_name: str = None, user_id: str = None) -> bool:
    """Initialize the global music controller."""
    global jellyfin_music
    
    try:
        jellyfin_music = JellyfinMusicController(
            jellyfin_url=jellyfin_url,
            api_key=jellyfin_token,
            chromecast_name=chromecast_name,
            user_id=user_id
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