#!/usr/bin/env python3
"""
Simple Chat Handler - Pragmatic ADHD support without overengineering
Direct path: User → Google Context → Claude → Response
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import our working components
try:
    from .claude_context_builder import ClaudeContextBuilder
    from .claude_browser_working import get_claude_browser
    from .google_integration import get_google_integration
    INTEGRATIONS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Import error: {e}")
    INTEGRATIONS_AVAILABLE = False

# Import music control - use Jellyfin, not internet radio!
try:
    from mcp_server.jellyfin_music import jellyfin_music
    MUSIC_AVAILABLE = True if jellyfin_music else False
except ImportError:
    MUSIC_AVAILABLE = False
    logger.warning("Music control not available")

@dataclass
class ChatResponse:
    """Simple chat response structure."""
    message: str
    success: bool
    context: Dict[str, Any]
    actions_taken: list

class SimpleChatHandler:
    """
    Pragmatic chat handler that actually works.
    No cognitive loops, no circuit breakers, just useful ADHD support.
    """
    
    def __init__(self):
        self.context_builder = ClaudeContextBuilder() if INTEGRATIONS_AVAILABLE else None
        self.google = get_google_integration() if INTEGRATIONS_AVAILABLE else None
        self.music_player = jellyfin_music if MUSIC_AVAILABLE else None
        self.last_context = {}
        
    async def handle_chat(self, message: str, user_id: str = "default") -> ChatResponse:
        """
        Main chat handler - simple and direct.
        """
        try:
            actions_taken = []
            
            # 1. Check for direct commands
            command_result = await self._handle_commands(message)
            if command_result:
                actions_taken.append(command_result)
            
            # 2. Build rich context from Google APIs
            context = {}
            if self.context_builder:
                context = self.context_builder.build_context(
                    user_id=user_id,
                    current_task="chatting"
                )
                self.last_context = context
                logger.info(f"Built context with Google data: {bool(context.get('google_insights'))}")
            
            # 3. Create prompt for Claude with context
            claude_prompt = self._build_claude_prompt(message, context)
            
            # 4. Get Claude's response OR use smart fallback
            claude_response = None
            try:
                # Try Claude first (often fails due to browser issues)
                claude_client = await get_claude_browser()
                if await claude_client.initialize():
                    claude_response = await claude_client.send_message(claude_prompt)
            except Exception as e:
                logger.debug(f"Claude unavailable: {e}")
            
            # If Claude fails, use smart fallback with real Google data
            if not claude_response:
                fallback = self._get_fallback_response(message, context)
                claude_response = fallback
            
            # 5. Check if response suggests any actions
            suggested_actions = self._extract_suggested_actions(claude_response)
            for action in suggested_actions:
                result = await self._execute_suggested_action(action)
                if result:
                    actions_taken.append(result)
            
            return ChatResponse(
                message=claude_response,
                success=True,
                context=context.get('google_insights', {}),
                actions_taken=actions_taken
            )
                
        except Exception as e:
            logger.error(f"Chat handler error: {e}")
            return ChatResponse(
                message=f"I had trouble processing that. Try asking about your calendar, tasks, or say 'play music'.",
                success=False,
                context={},
                actions_taken=[]
            )
    
    async def _handle_commands(self, message: str) -> Optional[str]:
        """Handle direct commands like 'play music' or 'what's next'."""
        message_lower = message.lower()
        
        # Music commands
        if any(word in message_lower for word in ['play music', 'play some', 'music please', 'start music']):
            if self.music_player:
                # Detect mood
                mood = "focus"  # default
                if 'energy' in message_lower or 'upbeat' in message_lower:
                    mood = "energy"
                elif 'calm' in message_lower or 'relax' in message_lower:
                    mood = "calm"
                elif 'ambient' in message_lower or 'deep' in message_lower:
                    mood = "ambient"
                
                # Convert mood string to MusicMood enum
                from mcp_server.jellyfin_music import MusicMood
                mood_map = {
                    'focus': MusicMood.FOCUS,
                    'energy': MusicMood.ENERGY,
                    'calm': MusicMood.CALM,
                    'ambient': MusicMood.AMBIENT
                }
                music_mood = mood_map.get(mood, MusicMood.FOCUS)
                
                # Play using Jellyfin async method
                loop = asyncio.get_event_loop()
                success = await self.music_player.play_mood_playlist(music_mood)
                if success:
                    return f"Started {mood} music from Jellyfin library on Shack Speakers"
                    
        elif any(word in message_lower for word in ['stop music', 'music off', 'silence please']):
            if self.music_player:
                # Stop using Jellyfin async method
                success = await self.music_player.stop_music()
                if success:
                    return "Music stopped"
        
        # Quick info commands
        elif 'what\'s next' in message_lower or 'next meeting' in message_lower:
            if self.google:
                events = self.google.get_upcoming_events(hours=4)
                if events:
                    next_event = events[0]
                    return f"Next: {next_event.summary} in {next_event.minutes_until} minutes"
        
        elif 'how many steps' in message_lower or 'step count' in message_lower:
            if self.google:
                fitness = self.google.get_fitness_data()
                if fitness:
                    return f"Steps today: {fitness.steps_today:,}"
        
        return None
    
    def _build_claude_prompt(self, message: str, context: Dict) -> str:
        """Build a rich prompt for Claude with all context."""
        prompt_parts = []
        
        # Add ADHD context header
        prompt_parts.append("You are helping someone with ADHD. Be concise, actionable, and supportive.")
        
        # Add Google insights if available
        insights = context.get('google_insights', {})
        
        # Next event
        if insights.get('next_event'):
            event = insights['next_event']
            prompt_parts.append(f"Their next event: {event['title']} in {event['minutes_until']} minutes")
        
        # Urgent tasks
        if insights.get('urgent_tasks'):
            tasks = insights['urgent_tasks']
            task_list = ", ".join([t['title'] for t in tasks[:3]])
            prompt_parts.append(f"Urgent tasks: {task_list}")
        
        # Fitness data
        if insights.get('fitness'):
            fitness = insights['fitness']
            prompt_parts.append(f"Activity today: {fitness.get('steps_today', 0)} steps, activity level: {fitness.get('activity_level', 'unknown')}")
            if fitness.get('needs_movement'):
                prompt_parts.append("They need a movement break (haven't moved in over an hour)")
        
        # Smart recommendations
        if insights.get('smart_recommendations'):
            for rec in insights['smart_recommendations'][:2]:
                prompt_parts.append(f"System recommendation: {rec}")
        
        # Add time context
        time_ctx = context.get('time_context', {})
        if time_ctx:
            prompt_parts.append(f"Current time: {time_ctx.get('current_time', 'unknown')}, {time_ctx.get('day_part', 'day')}")
        
        # Add the user's message
        prompt_parts.append(f"\nUser message: {message}")
        prompt_parts.append("\nProvide helpful, ADHD-friendly advice. Be specific and actionable.")
        
        return "\n".join(prompt_parts)
    
    def _extract_suggested_actions(self, response: str) -> list:
        """Extract actionable suggestions from Claude's response."""
        actions = []
        response_lower = response.lower()
        
        # Check for timer suggestions
        if 'timer' in response_lower or 'minutes' in response_lower:
            # Look for patterns like "15-minute timer" or "timer for 20 minutes"
            timer_match = re.search(r'(\d+)[-\s]minute', response_lower)
            if timer_match:
                minutes = int(timer_match.group(1))
                actions.append(('timer', minutes))
        
        # Check for music suggestions
        if any(word in response_lower for word in ['music', 'playlist', 'sounds', 'audio']):
            if 'focus' in response_lower or 'concentrate' in response_lower:
                actions.append(('music', 'focus'))
            elif 'energy' in response_lower or 'upbeat' in response_lower:
                actions.append(('music', 'energy'))
            elif 'calm' in response_lower or 'relax' in response_lower:
                actions.append(('music', 'calm'))
        
        # Check for movement suggestions
        if any(word in response_lower for word in ['walk', 'move', 'stretch', 'break']):
            actions.append(('movement', 'suggested'))
        
        return actions
    
    async def _execute_suggested_action(self, action: tuple) -> Optional[str]:
        """Execute an action suggested by Claude."""
        action_type, param = action
        
        if action_type == 'music' and self.music_player:
            # Convert param to MusicMood and play
            from mcp_server.jellyfin_music import MusicMood
            mood_map = {
                'focus': MusicMood.FOCUS,
                'energy': MusicMood.ENERGY,
                'calm': MusicMood.CALM,
                'ambient': MusicMood.AMBIENT
            }
            music_mood = mood_map.get(param, MusicMood.FOCUS)
            success = await self.music_player.play_mood_playlist(music_mood)
            if success:
                return f"Auto-started {param} music from Jellyfin library"
        
        elif action_type == 'timer':
            # For now, just log that a timer was suggested
            # Could integrate with system timers later
            return f"Timer suggestion noted: {param} minutes"
        
        elif action_type == 'movement':
            return "Movement reminder noted"
        
        return None
    
    def _get_fallback_response(self, message: str, context: Dict) -> str:
        """Fallback responses when Claude times out."""
        message_lower = message.lower()
        
        # Use context for smart fallbacks
        insights = context.get('google_insights', {})
        
        if 'time' in message_lower or 'schedule' in message_lower or 'next' in message_lower:
            if insights.get('next_event'):
                event = insights['next_event']
                return f"Your next event is {event['title']} in {event['minutes_until']} minutes."
            return "I don't see any upcoming events in your calendar."
        
        elif 'task' in message_lower or 'todo' in message_lower:
            if insights.get('urgent_tasks'):
                tasks = insights['urgent_tasks']
                return f"You have {len(tasks)} urgent tasks. The most important is: {tasks[0]['title']}"
            return "No urgent tasks right now - you're all caught up!"
        
        elif 'step' in message_lower or 'walk' in message_lower or 'move' in message_lower:
            if insights.get('fitness'):
                fitness = insights['fitness']
                return f"You've taken {fitness.get('steps_today', 0)} steps today. {'Time for a movement break!' if fitness.get('needs_movement') else 'Keep it up!'}"
            return "I couldn't get your fitness data, but a short walk is always a good idea!"
        
        elif 'focus' in message_lower or 'concentrate' in message_lower:
            return "Try the Pomodoro technique: 25 minutes of focused work, then a 5-minute break. Want me to play some focus music?"
        
        elif 'overwhelm' in message_lower or 'stress' in message_lower or 'anxious' in message_lower:
            return "Take a deep breath. Let's break things down into small steps. What's the ONE smallest thing you can do right now?"
        
        # Generic ADHD-friendly response
        return "I'm here to help with your ADHD challenges. You can ask about your schedule, tasks, or say 'play focus music'. What do you need?"

# Global handler instance
_chat_handler = None

def get_chat_handler() -> SimpleChatHandler:
    """Get or create the chat handler singleton."""
    global _chat_handler
    if _chat_handler is None:
        _chat_handler = SimpleChatHandler()
    return _chat_handler

# For testing
if __name__ == "__main__":
    async def test():
        handler = get_chat_handler()
        
        # Test various messages
        test_messages = [
            "What's next on my calendar?",
            "I'm feeling overwhelmed",
            "Play some focus music",
            "How many steps have I taken?",
            "I need help starting this task"
        ]
        
        for msg in test_messages:
            print(f"\nUser: {msg}")
            response = await handler.handle_chat(msg)
            print(f"Bot: {response.message[:200]}...")
            if response.actions_taken:
                print(f"Actions: {response.actions_taken}")
    
    asyncio.run(test())