"""
Voice Assistant Interface for ADHD Support
Enables two-way voice interaction through Google Assistant/Nest devices
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

# Check for required libraries
try:
    import speech_recognition as sr
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    sr = None
    logger.warning("Speech recognition not available. Install with: pip install SpeechRecognition pyaudio")

class ListeningMode(Enum):
    """Listening modes for different contexts."""
    ALWAYS_ON = "always_on"      # Continuous listening
    WAKE_WORD = "wake_word"       # Listen for "Hey Claude"
    PUSH_TO_TALK = "push_to_talk" # Manual activation
    SCHEDULED = "scheduled"        # Listen at specific times

@dataclass
class VoiceSession:
    """Active voice interaction session."""
    is_active: bool = False
    last_command: Optional[str] = None
    context: Dict[str, Any] = None
    timeout_seconds: int = 30
    
class ADHDVoiceAssistant:
    """Voice assistant optimized for ADHD support."""
    
    def __init__(self, wake_word: str = "hey claude"):
        self.wake_word = wake_word.lower()
        self.recognizer = sr.Recognizer() if (AUDIO_AVAILABLE and sr) else None
        self.microphone = sr.Microphone() if (AUDIO_AVAILABLE and sr) else None
        self.listening_mode = ListeningMode.WAKE_WORD
        self.session = VoiceSession()
        self.voice_calendar = None
        self.nest_system = None
        self.cognitive_loop = None
        self.listener_task = None
        
        # Voice prompts optimized for ADHD
        self.prompts = {
            'listening': "I'm listening",
            'thinking': "Let me think about that",
            'error': "Sorry, I didn't catch that",
            'timeout': "I'm here when you need me",
            'confirm': "Got it",
        }
        
    async def initialize(self, voice_calendar=None, nest_system=None, cognitive_loop=None):
        """Initialize the voice assistant."""
        try:
            logger.info("🎙️ Initializing ADHD voice assistant")
            
            # Connect to other systems
            self.voice_calendar = voice_calendar
            self.nest_system = nest_system
            self.cognitive_loop = cognitive_loop
            
            # Calibrate microphone for ambient noise
            if self.recognizer and self.microphone:
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    logger.info("🎤 Microphone calibrated for ambient noise")
            
            # Start listening based on mode
            if self.listening_mode == ListeningMode.ALWAYS_ON:
                self.listener_task = asyncio.create_task(self._continuous_listen())
            elif self.listening_mode == ListeningMode.WAKE_WORD:
                self.listener_task = asyncio.create_task(self._wake_word_listen())
            
            logger.info("✅ Voice assistant ready")
            return True
            
        except Exception as e:
            logger.error(f"Voice assistant initialization failed: {e}")
            return False
    
    async def _continuous_listen(self):
        """Continuous listening mode for always-on assistance."""
        logger.info("👂 Continuous listening activated")
        
        while True:
            try:
                # Listen for voice input
                text = await self._listen_for_speech()
                
                if text:
                    # Process the command
                    await self.process_voice_input(text)
                
                # Brief pause between listens
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Continuous listen error: {e}")
                await asyncio.sleep(2)
    
    async def _wake_word_listen(self):
        """Listen for wake word before activating."""
        logger.info(f"👂 Listening for wake word: '{self.wake_word}'")
        
        while True:
            try:
                # Listen for any speech
                text = await self._listen_for_speech(timeout=1, phrase_limit=3)
                
                if text and self.wake_word in text.lower():
                    # Wake word detected - activate session
                    logger.info("✅ Wake word detected!")
                    await self.start_session()
                
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Wake word listen error: {e}")
                await asyncio.sleep(2)
    
    async def _listen_for_speech(self, timeout: int = 3, phrase_limit: int = None) -> Optional[str]:
        """Listen for speech input."""
        if not self.recognizer or not self.microphone:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            
            # Use executor for blocking audio operations
            def listen_sync():
                with self.microphone as source:
                    if phrase_limit:
                        audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
                    else:
                        audio = self.recognizer.listen(source, timeout=timeout)
                    
                    # Try Google Speech Recognition
                    try:
                        text = self.recognizer.recognize_google(audio)
                        return text
                    except sr.UnknownValueError:
                        return None
                    except sr.RequestError as e:
                        logger.error(f"Speech recognition error: {e}")
                        return None
            
            text = await loop.run_in_executor(None, listen_sync)
            
            if text:
                logger.info(f"🎤 Heard: '{text}'")
            
            return text
            
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            logger.error(f"Listen error: {e}")
            return None
    
    async def start_session(self):
        """Start an interactive voice session."""
        self.session.is_active = True
        
        # Send listening prompt
        await self.speak(self.prompts['listening'])
        
        # Listen for command
        command = await self._listen_for_speech(timeout=5)
        
        if command:
            await self.process_voice_input(command)
        else:
            await self.speak(self.prompts['timeout'])
        
        self.session.is_active = False
    
    async def process_voice_input(self, text: str):
        """Process voice input and generate response."""
        try:
            logger.info(f"Processing: '{text}'")
            
            # Send thinking feedback
            await self.speak(self.prompts['thinking'], quick=True)
            
            # Check for calendar commands
            if any(word in text.lower() for word in ['calendar', 'event', 'meeting', 'schedule']):
                if self.voice_calendar:
                    response = await self.voice_calendar.process_voice_command(text)
                else:
                    response = "Calendar system is not available"
            
            # Check for music commands
            elif any(word in text.lower() for word in ['music', 'play', 'stop', 'volume']):
                response = await self._handle_music_command(text)
            
            # Check for reminder commands
            elif any(word in text.lower() for word in ['remind', 'timer', 'alarm']):
                response = await self._handle_reminder_command(text)
            
            # Check for ADHD support commands
            elif any(word in text.lower() for word in ['focus', 'help', 'stuck', 'overwhelmed']):
                response = await self._handle_adhd_support(text)
            
            # General chat - use cognitive loop
            else:
                if self.cognitive_loop:
                    response = await self._process_with_cognitive_loop(text)
                else:
                    response = "I heard you say: " + text
            
            # Speak the response
            await self.speak(response)
            
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            await self.speak(self.prompts['error'])
    
    async def _handle_music_command(self, text: str) -> str:
        """Handle music-related voice commands."""
        from mcp_server.jellyfin_music import jellyfin_music, MusicMood
        
        if not jellyfin_music:
            return "Music system is not available"
        
        text_lower = text.lower()
        
        if 'stop' in text_lower:
            await jellyfin_music.stop_music()
            return "Music stopped"
        
        elif 'focus' in text_lower:
            await jellyfin_music.play_mood_playlist(MusicMood.FOCUS)
            return "Playing focus music"
        
        elif 'calm' in text_lower or 'relax' in text_lower:
            await jellyfin_music.play_mood_playlist(MusicMood.CALM)
            return "Playing calming music"
        
        elif 'energy' in text_lower or 'energize' in text_lower:
            await jellyfin_music.play_mood_playlist(MusicMood.ENERGY)
            return "Playing energizing music"
        
        elif 'next' in text_lower or 'skip' in text_lower:
            await jellyfin_music.skip_track()
            return "Skipping to next track"
        
        elif 'volume up' in text_lower:
            current_volume = jellyfin_music.state.volume
            await jellyfin_music.set_volume(min(1.0, current_volume + 0.1))
            return "Volume increased"
        
        elif 'volume down' in text_lower:
            current_volume = jellyfin_music.state.volume
            await jellyfin_music.set_volume(max(0.1, current_volume - 0.1))
            return "Volume decreased"
        
        else:
            return "Playing music for you"
    
    async def _handle_reminder_command(self, text: str) -> str:
        """Handle reminder-related voice commands."""
        from mcp_server.adhd_reminders import adhd_reminders
        
        if not adhd_reminders:
            return "Reminder system is not available"
        
        # Parse reminder from natural language
        if 'in' in text:
            # "Remind me to take a break in 25 minutes"
            parts = text.split('in')
            what = parts[0].replace('remind me to', '').strip()
            when = parts[1].strip()
            
            # Parse time
            minutes = 25  # default
            if 'hour' in when:
                minutes = 60
            elif 'minute' in when:
                try:
                    minutes = int(''.join(filter(str.isdigit, when)))
                except:
                    minutes = 25
            
            # Add custom reminder
            await adhd_reminders.add_custom_reminder(
                message=f"Reminder: {what}",
                interval_minutes=minutes,
                priority="normal"
            )
            
            return f"I'll remind you to {what} in {minutes} minutes"
        
        else:
            return "When should I remind you?"
    
    async def _handle_adhd_support(self, text: str) -> str:
        """Handle ADHD support requests."""
        text_lower = text.lower()
        
        if 'stuck' in text_lower or 'overwhelmed' in text_lower:
            # Activate grounding exercise
            return ("Take a deep breath with me. Let's break this down into small steps. "
                   "First, what's the very next tiny action you can take?")
        
        elif 'focus' in text_lower:
            # Start focus session
            from mcp_server.jellyfin_music import jellyfin_music
            if jellyfin_music:
                await jellyfin_music.play_mood_playlist("focus")
            return "Starting a 25-minute focus session. I'll remind you when it's time for a break."
        
        elif 'help' in text_lower:
            return ("I'm here to help! You can ask me to: start focus time, "
                   "check your calendar, play music, set reminders, or just talk if you're feeling stuck.")
        
        else:
            return "I'm here to support you. What do you need?"
    
    async def _process_with_cognitive_loop(self, text: str) -> str:
        """Process general conversation through cognitive loop."""
        if self.cognitive_loop:
            # This would integrate with the actual cognitive loop
            return f"Let me think about '{text}' for you..."
        else:
            return "I understand you said: " + text
    
    async def speak(self, text: str, quick: bool = False):
        """Speak text through Nest devices."""
        if self.nest_system:
            from mcp_server.nest_nudges import NudgeType
            nudge_type = NudgeType.GENTLE
            await self.nest_system.send_nudge(text, nudge_type=nudge_type)
        else:
            logger.info(f"🔊 Speaking: '{text}'")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.listener_task:
            self.listener_task.cancel()
            await asyncio.gather(self.listener_task, return_exceptions=True)

# Global instance
voice_assistant: Optional[ADHDVoiceAssistant] = None

async def initialize_voice_assistant(wake_word: str = "hey claude") -> bool:
    """Initialize the global voice assistant."""
    global voice_assistant
    
    try:
        voice_assistant = ADHDVoiceAssistant(wake_word)
        
        # Get connected systems
        from mcp_server.voice_calendar_integration import voice_calendar
        from mcp_server.nest_nudges import nest_nudge_system
        
        success = await voice_assistant.initialize(
            voice_calendar=voice_calendar,
            nest_system=nest_nudge_system
        )
        
        if not success:
            voice_assistant = None
            return False
        
        logger.info("🎙️ Voice assistant ready for ADHD support")
        return True
        
    except Exception as e:
        logger.error(f"Voice assistant initialization failed: {e}")
        voice_assistant = None
        return False