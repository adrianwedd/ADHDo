"""
Simple ADHD Assistant - Pattern-based responses with system control.

This provides instant, helpful responses without relying on slow LLMs.
"""

import re
import random
from typing import Dict, List, Optional, Tuple
import asyncio
import logging

logger = logging.getLogger(__name__)


class ADHDAssistant:
    """Pattern-based ADHD assistant with system integration."""
    
    def __init__(self):
        """Initialize the ADHD assistant with response patterns."""
        self.patterns = self._build_patterns()
        self.context = {}
        
    def _build_patterns(self) -> List[Tuple[re.Pattern, str, Optional[str]]]:
        """Build pattern matching rules for common ADHD queries."""
        return [
            # Focus help
            (re.compile(r'\b(help|need|want).*(focus|concentrate|attention)', re.I),
             "focus_help",
             None),
            (re.compile(r'\b(cant|cannot|can\'t).*(focus|concentrate)', re.I),
             "focus_help",
             None),
            (re.compile(r'\b(distracted|distracting|distraction)', re.I),
             "distraction_help",
             None),
            
            # Task management
            (re.compile(r'\b(overwhelm|overwhelmed|too much|too many)', re.I),
             "overwhelm_help",
             None),
            (re.compile(r'\b(start|begin|get started)', re.I),
             "start_help",
             None),
            (re.compile(r'\b(prioriti|what.*first|where.*start)', re.I),
             "priority_help",
             None),
            
            # Energy/mood
            (re.compile(r'\b(tired|exhausted|no energy|low energy)', re.I),
             "energy_help",
             None),
            (re.compile(r'\b(anxious|anxiety|worried|stress)', re.I),
             "anxiety_help",
             None),
            (re.compile(r'\b(sad|depressed|down|blue)', re.I),
             "mood_help",
             None),
            
            # Music control
            (re.compile(r'\b(play|start).*(music|focus|energy)', re.I),
             "music_command",
             "play"),
            (re.compile(r'\b(stop|pause|quiet).*(music|sound)', re.I),
             "music_command",
             "stop"),
            
            # Nudge control
            (re.compile(r'\b(remind|nudge|alert).*me', re.I),
             "nudge_command",
             "create"),
            (re.compile(r'\b(bedtime|sleep|bed)', re.I),
             "bedtime_help",
             None),
            
            # General support
            (re.compile(r'\b(hello|hi|hey)', re.I),
             "greeting",
             None),
            (re.compile(r'\b(thank|thanks)', re.I),
             "thanks",
             None),
            (re.compile(r'\b(help|what can you)', re.I),
             "help",
             None),
        ]
    
    async def process_message(self, message: str, user_id: str = "default") -> Dict:
        """Process user message and return response with actions."""
        message_lower = message.lower()
        response = None
        actions = []
        
        # Check patterns
        for pattern, response_type, action_data in self.patterns:
            if pattern.search(message):
                response = self._get_response(response_type, action_data)
                actions = await self._execute_actions(response_type, action_data)
                break
        
        # Default response if no pattern matches
        if not response:
            response = self._get_default_response()
        
        return {
            "response": response,
            "actions": actions,
            "success": True
        }
    
    def _get_response(self, response_type: str, action_data: Optional[str] = None) -> str:
        """Get appropriate response for the given type."""
        responses = {
            "focus_help": [
                "Let me help you focus. I'm starting some focus music and will minimize distractions. Try the Pomodoro technique: 25 minutes of focused work, then a 5-minute break.",
                "Focus mode activated! Playing concentration music. Remember: one task at a time. What's the ONE thing you want to accomplish in the next 25 minutes?",
                "I've got you! Starting focus music now. Pro tip: write down any distracting thoughts on paper to deal with later."
            ],
            "distraction_help": [
                "Distractions are tough with ADHD! I'm playing focus music to help. Try this: put your phone in another room and use a website blocker for 25 minutes.",
                "Let's minimize distractions together. Starting focus music. Quick tip: close all tabs except what you need right now.",
                "Distraction shield activated! Playing concentration music. Remember: it's okay to get distracted - just gently bring yourself back."
            ],
            "overwhelm_help": [
                "I hear you - feeling overwhelmed is so common with ADHD. Let's break this down: What's ONE small thing you can do right now? Just one.",
                "Take a deep breath. You don't have to do everything at once. Pick the easiest task first - build momentum with a quick win.",
                "Overwhelm is real. Here's the ADHD trick: forget the big picture for now. What's the tiniest next step? Do just that."
            ],
            "start_help": [
                "Starting is the hardest part! Here's the trick: commit to just 2 minutes. That's it. Often you'll keep going once you start.",
                "Let's make starting easier: 1) Pick the smallest part of the task, 2) Set a 5-minute timer, 3) Just begin - imperfectly is fine!",
                "The ADHD startup sequence: Stand up, stretch, take 3 deep breaths, then do literally ANYTHING related to your task for 60 seconds. Momentum will follow."
            ],
            "priority_help": [
                "ADHD priority hack: Ask yourself - 'If I could only do ONE thing today, what would make the biggest difference?' Start there.",
                "Let's prioritize: 1) What has a deadline? Do that first. 2) What will cause problems if ignored? Do that second. 3) Everything else can wait.",
                "Forget perfect prioritization. Pick what feels most urgent or interesting right now. Done is better than perfectly planned."
            ],
            "energy_help": [
                "Low energy is tough. Let me play some energizing music. Also try: stand up, do 10 jumping jacks, or take a 5-minute walk.",
                "Energy boost incoming! Starting upbeat music. Quick tip: dehydration mimics ADHD symptoms - when did you last drink water?",
                "Let's boost that energy! Playing energizing music. Remember: ADHD brains need more breaks. Take a real break every hour."
            ],
            "anxiety_help": [
                "Anxiety and ADHD often go together. Playing calming music. Try box breathing: 4 counts in, 4 hold, 4 out, 4 hold.",
                "I understand. Let's calm that anxiety. Starting soothing music. Remember: most things we worry about never happen.",
                "Anxiety is lying to you about the urgency. Playing calm music. Ground yourself: name 5 things you see, 4 you hear, 3 you feel."
            ],
            "mood_help": [
                "I hear you. ADHD can affect mood. Playing uplifting music. Remember: movement helps - even a 2-minute walk can shift your mood.",
                "Mood struggles are real with ADHD. Starting mood-boost music. Be kind to yourself - you're doing better than you think.",
                "Let's gently lift that mood. Playing positive music. Small wins count: make your bed, drink water, step outside for a moment."
            ],
            "bedtime_help": [
                "Sleep is crucial for ADHD brains! I'll set a bedtime reminder. Start winding down 30 minutes before bed - no screens!",
                "Good sleep = better ADHD management tomorrow. Setting bedtime nudge. Try: dim lights, calming music, and put devices away.",
                "ADHD sleep tip: your brain needs a runway to land. I'll remind you to start your bedtime routine. No revenge bedtime procrastination!"
            ],
            "greeting": [
                "Hey! I'm here to help with ADHD challenges. What's on your mind?",
                "Hello! Ready to tackle ADHD together. What do you need support with?",
                "Hi there! Your ADHD support system is here. How can I help you focus, organize, or feel better?"
            ],
            "thanks": [
                "You're welcome! Remember, asking for help is a strength, not a weakness.",
                "Happy to help! You've got this, one step at a time.",
                "Anytime! ADHD is challenging, but you're doing great by using support tools."
            ],
            "help": [
                "I can help with: 🎯 Focus and concentration, 📝 Task overwhelm, 🎵 Music for focus/energy, ⏰ Reminders and nudges, 😰 Anxiety and mood support. What do you need?",
                "I'm your ADHD assistant! I can: play focus music, send reminders, help with overwhelm, provide starting strategies, and offer emotional support. What's challenging you?",
                "Here to help with ADHD! Try: 'I can't focus', 'I'm overwhelmed', 'Play focus music', 'I need energy', or 'Remind me to take a break'."
            ],
            "music_command": [
                "Music control activated! Adjusting your audio environment for better focus.",
                "Handling your music request now.",
                "Audio environment updated!"
            ],
            "nudge_command": [
                "Setting up your reminder. You'll get gentle nudges to keep you on track.",
                "Nudge system activated! I'll help keep you accountable.",
                "Reminder created! I'll make sure you don't forget."
            ]
        }
        
        # Default responses if type not found
        default_responses = [
            "I understand ADHD makes things challenging. What specific support do you need right now?",
            "You're not alone in this. How can I help make things easier?",
            "ADHD is tough, but you're tougher. What's the main challenge right now?"
        ]
        
        response_list = responses.get(response_type, default_responses)
        return random.choice(response_list)
    
    def _get_default_response(self) -> str:
        """Get a default response when no pattern matches."""
        defaults = [
            "I'm here to help with ADHD challenges. Try asking about focus, overwhelm, or energy. Or I can play music to help you concentrate!",
            "Not sure I understood that, but I'm here to help! I can assist with focus, task management, music, and reminders.",
            "Let me know how I can support you! I can help with concentration, motivation, task overwhelm, or just play some focus music."
        ]
        return random.choice(defaults)
    
    async def _execute_actions(self, response_type: str, action_data: Optional[str] = None) -> List[str]:
        """Execute system actions based on response type."""
        actions = []
        
        try:
            if response_type in ["focus_help", "distraction_help"]:
                # Start focus music
                actions.append("music:focus")
                
            elif response_type == "energy_help":
                # Start energy music
                actions.append("music:energy")
                
            elif response_type in ["anxiety_help", "mood_help"]:
                # Start calming music
                actions.append("music:calm")
                
            elif response_type == "bedtime_help":
                # Set bedtime reminder
                actions.append("schedule:bedtime")
                
            elif response_type == "music_command":
                if action_data == "play":
                    actions.append("music:focus")
                elif action_data == "stop":
                    actions.append("music:stop")
                    
            elif response_type == "nudge_command":
                actions.append("nudge:create")
                
        except Exception as e:
            logger.error(f"Failed to execute action: {e}")
        
        return actions


# Global instance
adhd_assistant = ADHDAssistant()