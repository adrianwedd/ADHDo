#!/usr/bin/env python3
"""
Stateful Cognitive Loop for ADHD Support
A practical implementation that maintains awareness across interactions.

This cognitive loop:
1. Maintains persistent state about the user's context
2. Tracks patterns over time (medication taken, energy levels, tasks)
3. Provides context-aware responses based on history
4. Learns from each interaction to improve future support

Key features:
- Redis-backed state persistence
- Time-aware context (morning routine, bedtime, work hours)
- Pattern recognition (what helps this specific user?)
- Integration with all system components
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import redis.asyncio as redis
from dataclasses import dataclass, asdict, field
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


class UserState(str, Enum):
    """Current user state/energy level."""
    ENERGIZED = "energized"
    FOCUSED = "focused"
    STRUGGLING = "struggling"
    OVERWHELMED = "overwhelmed"
    HYPERFOCUS = "hyperfocus"
    TIRED = "tired"
    ANXIOUS = "anxious"
    CALM = "calm"


class ActivityType(str, Enum):
    """Types of activities we track."""
    MEDICATION_TAKEN = "medication_taken"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    BREAK_TAKEN = "break_taken"
    MUSIC_STARTED = "music_started"
    MUSIC_STOPPED = "music_stopped"
    NUDGE_SENT = "nudge_sent"
    NUDGE_ACKNOWLEDGED = "nudge_acknowledged"
    CALENDAR_EVENT = "calendar_event"
    USER_CHECK_IN = "user_check_in"
    PANIC_MODE = "panic_mode"
    BEDTIME_ROUTINE = "bedtime_routine"


@dataclass
class UserContext:
    """Complete context about a user at a point in time."""
    user_id: str
    current_state: UserState = UserState.CALM
    last_medication: Optional[datetime] = None
    current_task: Optional[str] = None
    task_started_at: Optional[datetime] = None
    music_playing: bool = False
    music_mood: Optional[str] = None
    last_break: Optional[datetime] = None
    today_completed_tasks: List[str] = field(default_factory=list)
    pending_tasks: List[Dict[str, Any]] = field(default_factory=list)
    upcoming_events: List[Dict[str, Any]] = field(default_factory=list)
    interaction_count: int = 0
    patterns: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for Redis storage."""
        return {
            'user_id': self.user_id,
            'current_state': self.current_state.value,
            'last_medication': self.last_medication.isoformat() if self.last_medication else None,
            'current_task': self.current_task,
            'task_started_at': self.task_started_at.isoformat() if self.task_started_at else None,
            'music_playing': self.music_playing,
            'music_mood': self.music_mood,
            'last_break': self.last_break.isoformat() if self.last_break else None,
            'today_completed_tasks': self.today_completed_tasks,
            'pending_tasks': self.pending_tasks,
            'upcoming_events': self.upcoming_events,
            'interaction_count': self.interaction_count,
            'patterns': self.patterns,
            'last_updated': self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserContext':
        """Create from dictionary retrieved from Redis."""
        return cls(
            user_id=data['user_id'],
            current_state=UserState(data.get('current_state', 'calm')),
            last_medication=datetime.fromisoformat(data['last_medication']) if data.get('last_medication') else None,
            current_task=data.get('current_task'),
            task_started_at=datetime.fromisoformat(data['task_started_at']) if data.get('task_started_at') else None,
            music_playing=data.get('music_playing', False),
            music_mood=data.get('music_mood'),
            last_break=datetime.fromisoformat(data['last_break']) if data.get('last_break') else None,
            today_completed_tasks=data.get('today_completed_tasks', []),
            pending_tasks=data.get('pending_tasks', []),
            upcoming_events=data.get('upcoming_events', []),
            interaction_count=data.get('interaction_count', 0),
            patterns=data.get('patterns', {}),
            last_updated=datetime.fromisoformat(data['last_updated']) if data.get('last_updated') else datetime.now()
        )


class StatefulCognitiveLoop:
    """
    A cognitive loop that maintains state and learns from interactions.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.base_url = "http://localhost:23443"  # Server URL
        
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Redis connected for state management")
        except Exception as e:
            logger.warning(f"⚠️ Redis not available, using memory-only state: {e}")
            self.redis_client = None
            
    async def get_user_context(self, user_id: str) -> UserContext:
        """Retrieve or create user context."""
        if self.redis_client:
            try:
                data = await self.redis_client.get(f"user_context:{user_id}")
                if data:
                    context_dict = json.loads(data)
                    return UserContext.from_dict(context_dict)
            except Exception as e:
                logger.error(f"Error loading context: {e}")
        
        # Return new context if not found
        return UserContext(user_id=user_id)
    
    async def save_user_context(self, context: UserContext):
        """Save user context to Redis."""
        if self.redis_client:
            try:
                context.last_updated = datetime.now()
                data = json.dumps(context.to_dict())
                await self.redis_client.setex(
                    f"user_context:{context.user_id}",
                    86400,  # 24 hour expiry
                    data
                )
            except Exception as e:
                logger.error(f"Error saving context: {e}")
    
    async def log_activity(self, user_id: str, activity: ActivityType, data: Dict[str, Any]):
        """Log an activity for pattern recognition."""
        if self.redis_client:
            try:
                activity_record = {
                    'timestamp': datetime.now().isoformat(),
                    'type': activity.value,
                    'data': data
                }
                
                # Add to activity stream (keep last 100)
                await self.redis_client.lpush(
                    f"activities:{user_id}",
                    json.dumps(activity_record)
                )
                await self.redis_client.ltrim(f"activities:{user_id}", 0, 99)
                
                # Update daily stats
                date_key = datetime.now().strftime("%Y-%m-%d")
                await self.redis_client.hincrby(
                    f"daily_stats:{user_id}:{date_key}",
                    activity.value,
                    1
                )
            except Exception as e:
                logger.error(f"Error logging activity: {e}")
    
    async def get_time_context(self) -> Dict[str, Any]:
        """Get current time-based context."""
        now = datetime.now()
        hour = now.hour
        
        # Determine time period
        if hour < 6:
            period = "night"
            focus_suggestion = "sleep"
        elif hour < 9:
            period = "early_morning"
            focus_suggestion = "morning_routine"
        elif hour < 12:
            period = "morning"
            focus_suggestion = "deep_work"
        elif hour < 14:
            period = "midday"
            focus_suggestion = "lunch_break"
        elif hour < 17:
            period = "afternoon"
            focus_suggestion = "focused_work"
        elif hour < 19:
            period = "early_evening"
            focus_suggestion = "wrap_up"
        elif hour < 22:
            period = "evening"
            focus_suggestion = "relaxation"
        else:
            period = "late_night"
            focus_suggestion = "bedtime_routine"
        
        # Check if it's a workday
        is_workday = now.weekday() < 5  # Monday = 0, Sunday = 6
        
        return {
            'current_time': now.isoformat(),
            'hour': hour,
            'period': period,
            'focus_suggestion': focus_suggestion,
            'is_workday': is_workday,
            'day_of_week': now.strftime('%A')
        }
    
    async def analyze_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyze user patterns for insights."""
        patterns = {
            'medication_consistency': 0,
            'task_completion_rate': 0,
            'best_focus_time': None,
            'average_task_duration': 0,
            'break_frequency': 0,
            'music_preference': None
        }
        
        if not self.redis_client:
            return patterns
            
        try:
            # Get last 7 days of stats
            for i in range(7):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                stats = await self.redis_client.hgetall(f"daily_stats:{user_id}:{date}")
                
                if stats:
                    # Analyze medication consistency
                    if b'medication_taken' in stats:
                        patterns['medication_consistency'] += 1
                    
                    # Calculate task completion rate
                    started = int(stats.get(b'task_started', 0))
                    completed = int(stats.get(b'task_completed', 0))
                    if started > 0:
                        patterns['task_completion_rate'] += (completed / started)
            
            # Average out the patterns
            patterns['medication_consistency'] = (patterns['medication_consistency'] / 7) * 100
            patterns['task_completion_rate'] = (patterns['task_completion_rate'] / 7) * 100 if patterns['task_completion_rate'] > 0 else 0
            
        except Exception as e:
            logger.error(f"Error analyzing patterns: {e}")
        
        return patterns
    
    async def determine_intervention(self, context: UserContext, time_context: Dict) -> Optional[Dict[str, Any]]:
        """Determine if an intervention is needed based on context."""
        now = datetime.now()
        interventions = []
        
        # Check medication reminder (if morning and not taken)
        if time_context['period'] in ['early_morning', 'morning'] and not context.last_medication:
            interventions.append({
                'type': 'medication_reminder',
                'message': '💊 Morning medication reminder',
                'urgency': 'high',
                'action': 'nudge'
            })
        
        # Check if stuck on task too long
        if context.current_task and context.task_started_at:
            task_duration = (now - context.task_started_at).total_seconds() / 60
            if task_duration > 90:  # More than 90 minutes
                interventions.append({
                    'type': 'break_reminder',
                    'message': f'🧘 You\'ve been on "{context.current_task}" for {int(task_duration)} minutes. Time for a break?',
                    'urgency': 'normal',
                    'action': 'nudge'
                })
        
        # Check if no break in last 2 hours
        if context.last_break:
            time_since_break = (now - context.last_break).total_seconds() / 60
            if time_since_break > 120:
                interventions.append({
                    'type': 'break_reminder',
                    'message': '☕ It\'s been over 2 hours. Stand up, stretch, hydrate!',
                    'urgency': 'normal',
                    'action': 'nudge'
                })
        
        # Check upcoming events
        for event in context.upcoming_events:
            event_time = datetime.fromisoformat(event['time'])
            minutes_until = (event_time - now).total_seconds() / 60
            
            if 0 < minutes_until <= 15:
                interventions.append({
                    'type': 'event_reminder',
                    'message': f'📅 {event["title"]} in {int(minutes_until)} minutes',
                    'urgency': 'urgent' if minutes_until <= 5 else 'high',
                    'action': 'nudge'
                })
        
        # Bedtime reminder
        if time_context['period'] == 'late_night' and context.current_state != UserState.TIRED:
            interventions.append({
                'type': 'bedtime_reminder',
                'message': '🛏️ Time to start winding down for bed',
                'urgency': 'normal',
                'action': 'nudge'
            })
        
        # Return highest priority intervention
        if interventions:
            # Sort by urgency
            urgency_order = {'urgent': 0, 'high': 1, 'normal': 2, 'low': 3}
            interventions.sort(key=lambda x: urgency_order.get(x['urgency'], 3))
            return interventions[0]
        
        return None
    
    async def process_user_input(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        Process user input with full context awareness.
        """
        # Get user context
        context = await self.get_user_context(user_id)
        context.interaction_count += 1
        
        # Get time context
        time_context = await self.get_time_context()
        
        # Analyze patterns
        patterns = await self.analyze_patterns(user_id)
        context.patterns = patterns
        
        # Parse user intent
        intent = self.parse_intent(message, context)
        
        # Generate response based on context and intent
        response = await self.generate_contextual_response(
            message, intent, context, time_context
        )
        
        # Update context based on interaction
        await self.update_context_from_interaction(context, intent, message)
        
        # Save updated context
        await self.save_user_context(context)
        
        # Log the interaction
        await self.log_activity(user_id, ActivityType.USER_CHECK_IN, {
            'message': message,
            'intent': intent,
            'state': context.current_state.value
        })
        
        return response
    
    def parse_intent(self, message: str, context: UserContext) -> str:
        """Parse user intent from message."""
        message_lower = message.lower()
        
        # Task-related intents
        if any(word in message_lower for word in ['start', 'begin', 'working on', 'doing']):
            return 'start_task'
        elif any(word in message_lower for word in ['done', 'finished', 'completed', 'complete']):
            return 'complete_task'
        elif any(word in message_lower for word in ['stuck', 'help', "can't", 'struggling']):
            return 'need_help'
        
        # State-related intents
        elif any(word in message_lower for word in ['tired', 'exhausted', 'sleepy']):
            return 'feeling_tired'
        elif any(word in message_lower for word in ['anxious', 'worried', 'stressed', 'overwhelmed']):
            return 'feeling_anxious'
        elif any(word in message_lower for word in ['focused', 'good', 'great', 'energized']):
            return 'feeling_good'
        
        # Medication/routine intents
        elif any(word in message_lower for word in ['medication', 'meds', 'pill']):
            return 'medication_query'
        elif any(word in message_lower for word in ['break', 'rest', 'pause']):
            return 'take_break'
        
        # Music intents
        elif any(word in message_lower for word in ['music', 'play', 'sound']):
            return 'music_request'
        
        # Calendar/schedule intents
        elif any(word in message_lower for word in ['calendar', 'schedule', 'events', 'meeting', "what's next"]):
            return 'calendar_query'
        
        # Default
        return 'general_chat'
    
    async def generate_contextual_response(
        self, 
        message: str, 
        intent: str, 
        context: UserContext, 
        time_context: Dict
    ) -> Dict[str, Any]:
        """Generate a response based on full context."""
        
        response = {
            'message': '',
            'actions': [],
            'context_used': {
                'user_state': context.current_state.value,
                'time_period': time_context['period'],
                'intent': intent,
                'patterns': context.patterns
            }
        }
        
        # Handle different intents with context awareness
        if intent == 'start_task':
            task = self.extract_task_from_message(message)
            response['message'] = f"Great! Starting '{task}'. I'll help you stay focused."
            
            # Add music if not playing
            if not context.music_playing and time_context['period'] in ['morning', 'afternoon']:
                response['actions'].append({
                    'type': 'start_music',
                    'mood': 'focus'
                })
                response['message'] += " Starting focus music to help."
            
            response['actions'].append({
                'type': 'update_task',
                'task': task,
                'status': 'started'
            })
            
        elif intent == 'complete_task':
            if context.current_task:
                response['message'] = f"🎉 Awesome! You completed '{context.current_task}'!"
                
                # Calculate task duration
                if context.task_started_at:
                    duration = (datetime.now() - context.task_started_at).total_seconds() / 60
                    response['message'] += f" That took {int(duration)} minutes."
                
                # Suggest break if needed
                if context.last_break and (datetime.now() - context.last_break).total_seconds() / 60 > 90:
                    response['message'] += " Time for a well-deserved break!"
                    response['actions'].append({'type': 'suggest_break'})
            else:
                response['message'] = "Great job completing that! What's next?"
            
        elif intent == 'need_help':
            response['message'] = self.generate_help_response(context, time_context)
            response['actions'].append({'type': 'offer_support'})
            
        elif intent == 'feeling_anxious':
            response['message'] = "I hear you're feeling overwhelmed. Let's take this one step at a time."
            response['actions'].append({
                'type': 'start_music',
                'mood': 'calm'
            })
            response['actions'].append({
                'type': 'suggest_breathing'
            })
            
        elif intent == 'medication_query':
            if context.last_medication:
                time_since = (datetime.now() - context.last_medication).total_seconds() / 3600
                response['message'] = f"You took your medication {int(time_since)} hours ago."
            else:
                response['message'] = "I don't have a record of medication today. Have you taken it?"
                
        elif intent == 'calendar_query':
            if context.upcoming_events:
                next_event = context.upcoming_events[0]
                response['message'] = f"Next up: {next_event['title']} at {next_event['time']}"
            else:
                response['message'] = "Your calendar is clear for now!"
                
        else:
            # General supportive response based on context
            response['message'] = self.generate_general_response(context, time_context)
        
        return response
    
    def extract_task_from_message(self, message: str) -> str:
        """Extract task description from message."""
        # Simple extraction - in production would use NLP
        indicators = ['working on', 'starting', 'doing', 'begin', 'start']
        for indicator in indicators:
            if indicator in message.lower():
                parts = message.lower().split(indicator)
                if len(parts) > 1:
                    return parts[1].strip().strip('.!?')
        return message  # Return whole message as task if can't extract
    
    def generate_help_response(self, context: UserContext, time_context: Dict) -> str:
        """Generate helpful response for someone who's stuck."""
        if context.current_task:
            suggestions = [
                f"Let's break down '{context.current_task}' into smaller steps.",
                f"What's the very next tiny action for '{context.current_task}'?",
                f"Sometimes starting is the hardest part. Can you do just 2 minutes of '{context.current_task}'?"
            ]
        else:
            suggestions = [
                "What's the smallest possible step you could take right now?",
                "Let's pick one tiny thing to do. What feels manageable?",
                "Remember: progress over perfection. What's one small win we can get?"
            ]
        
        import random
        return random.choice(suggestions)
    
    def generate_general_response(self, context: UserContext, time_context: Dict) -> str:
        """Generate a general contextual response."""
        responses = []
        
        # Time-based responses
        if time_context['period'] == 'early_morning':
            responses.append("Good morning! Ready to tackle the day?")
        elif time_context['period'] == 'late_night':
            responses.append("It's getting late. Don't forget to wind down.")
        
        # State-based responses
        if context.current_state == UserState.FOCUSED:
            responses.append("You're in the zone! Keep it up!")
        elif context.current_state == UserState.OVERWHELMED:
            responses.append("Remember to breathe. One thing at a time.")
        
        # Pattern-based responses
        if context.patterns.get('task_completion_rate', 0) > 70:
            responses.append("You've been crushing it lately! Great job!")
        
        import random
        return random.choice(responses) if responses else "I'm here to help. What do you need?"
    
    async def update_context_from_interaction(self, context: UserContext, intent: str, message: str):
        """Update context based on the interaction."""
        # Update state based on intent
        if intent == 'feeling_tired':
            context.current_state = UserState.TIRED
        elif intent == 'feeling_anxious':
            context.current_state = UserState.ANXIOUS
        elif intent == 'feeling_good':
            context.current_state = UserState.ENERGIZED
        elif intent == 'start_task':
            context.current_state = UserState.FOCUSED
            context.current_task = self.extract_task_from_message(message)
            context.task_started_at = datetime.now()
        elif intent == 'complete_task':
            if context.current_task:
                context.today_completed_tasks.append(context.current_task)
                context.current_task = None
                context.task_started_at = None
        elif intent == 'take_break':
            context.last_break = datetime.now()
    
    async def run_periodic_check(self):
        """Run periodic checks for all users."""
        # This would run every few minutes to check if interventions are needed
        # For now, focusing on single user
        user_id = "default_user"
        
        while True:
            try:
                # Get context
                context = await self.get_user_context(user_id)
                time_context = await self.get_time_context()
                
                # Check if intervention needed
                intervention = await self.determine_intervention(context, time_context)
                
                if intervention:
                    logger.info(f"🔔 Intervention needed: {intervention['message']}")
                    # Here you would trigger the actual intervention
                    # e.g., send nudge, start music, etc.
                
                # Save context
                await self.save_user_context(context)
                
            except Exception as e:
                logger.error(f"Error in periodic check: {e}")
            
            # Wait 5 minutes before next check
            await asyncio.sleep(300)


# Example usage
async def main():
    """Example of using the stateful cognitive loop."""
    loop = StatefulCognitiveLoop()
    await loop.initialize()
    
    # Simulate user interactions
    user_id = "test_user"
    
    # Morning check-in
    response = await loop.process_user_input(
        user_id, 
        "Good morning, I'm starting work on the quarterly report"
    )
    print(f"Response: {response['message']}")
    print(f"Actions: {response['actions']}")
    
    # Later...
    response = await loop.process_user_input(
        user_id,
        "I'm feeling stuck and overwhelmed"
    )
    print(f"Response: {response['message']}")
    
    # Complete task
    response = await loop.process_user_input(
        user_id,
        "Finished the report!"
    )
    print(f"Response: {response['message']}")
    
    # Check patterns
    patterns = await loop.analyze_patterns(user_id)
    print(f"User patterns: {patterns}")


if __name__ == "__main__":
    asyncio.run(main())