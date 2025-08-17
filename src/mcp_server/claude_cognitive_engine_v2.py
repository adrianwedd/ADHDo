#!/usr/bin/env python3
"""
Claude Cognitive Engine V2 - Tool-Aware Version
Claude IS the cognitive loop with full awareness of available tools
"""

import json
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Import all our data sources
from .google_integration import get_google_integration
from .claude_browser_working import get_claude_browser
from .sqlite_fallback import get_persistent_storage  # Uses PostgreSQL if available, otherwise SQLite
# from .claude_remote_browser import SmartSessionManager  # This doesn't work - expects existing Chrome

@dataclass
class CompleteSystemState:
    """Complete system state for Claude to reason about."""
    # User Context
    current_message: str
    last_interaction_minutes: int
    recent_messages: List[Dict[str, str]]
    emotional_indicators: str
    
    # Physical State - ENHANCED WITH FULL FIT DATA
    steps_today: int
    steps_last_hour: int
    calories_burned: int
    distance_km: float
    active_minutes: int
    last_movement_minutes: int
    sitting_duration_minutes: int
    last_hydration_minutes: int
    
    # Sleep Data
    sleep_hours: float
    sleep_quality: int  # 1-10
    poor_sleep: bool
    
    # Temporal State
    current_time: str
    day_part: str
    weekday_weekend: str
    typical_energy_now: str
    
    # Task State
    current_focus: Optional[str]
    task_duration_minutes: int
    urgent_tasks: List[str]
    overdue_tasks: List[str]
    upcoming_30min: List[str]
    
    # Environment
    ambient_noise: str
    distractions: List[str]
    available_devices: List[str]
    music_playing: bool
    music_mood: Optional[str]
    
    # Medication
    last_medication: str
    next_medication: str
    medication_effective: bool
    
    # Patterns & History
    recent_patterns: List[str]
    typical_crash_times: List[str]
    hyperfocus_triggers: List[str]
    success_rate_today: float
    
    # Recent System Activity
    last_nudge_ago: str
    last_break_ago: str
    recent_actions: List[Dict[str, Any]]
    ignored_suggestions_count: int
    
    # Decision Context
    previous_decision: Dict[str, Any]
    previous_outcome: str
    user_feedback: Optional[str]


class ToolRegistry:
    """Registry of available tools that Claude can execute."""
    
    @staticmethod
    def get_available_tools() -> Dict[str, Any]:
        """Return all available tools with their schemas."""
        return {
            "music_control": {
                "description": "Control music playback on available devices",
                "actions": {
                    "play_music": {
                        "params": {
                            "mood": "focus|calm|energizing|ambient|deep_work",
                            "device": "optional - specific device name",
                            "duration_minutes": "optional - how long to play"
                        },
                        "example": {"type": "play_music", "params": {"mood": "focus", "device": "Nest Hub Max"}}
                    },
                    "stop_music": {
                        "params": {},
                        "example": {"type": "stop_music", "params": {}}
                    },
                    "adjust_volume": {
                        "params": {"level": "0-100"},
                        "example": {"type": "adjust_volume", "params": {"level": 50}}
                    }
                }
            },
            "timer_system": {
                "description": "Set timers and reminders",
                "actions": {
                    "set_timer": {
                        "params": {
                            "minutes": "duration in minutes",
                            "purpose": "work|break|medication|hydration|movement",
                            "alert_message": "what to say when timer expires"
                        },
                        "example": {"type": "set_timer", "params": {"minutes": 25, "purpose": "work", "alert_message": "Time for a 5 minute break!"}}
                    },
                    "cancel_timer": {
                        "params": {"timer_id": "optional - specific timer to cancel"},
                        "example": {"type": "cancel_timer", "params": {}}
                    }
                }
            },
            "nudge_system": {
                "description": "Send nudges via Nest devices or notifications",
                "actions": {
                    "send_nudge": {
                        "params": {
                            "message": "what to say",
                            "urgency": "gentle|normal|firm|critical",
                            "device": "optional - specific device or 'all'"
                        },
                        "example": {"type": "send_nudge", "params": {"message": "Time to stand up and stretch!", "urgency": "gentle"}}
                    },
                    "schedule_nudge": {
                        "params": {
                            "delay_minutes": "when to send",
                            "message": "what to say",
                            "urgency": "gentle|normal|firm"
                        },
                        "example": {"type": "schedule_nudge", "params": {"delay_minutes": 15, "message": "Check in on your task progress", "urgency": "normal"}}
                    }
                }
            },
            "environment_control": {
                "description": "Adjust environmental factors",
                "actions": {
                    "adjust_lights": {
                        "params": {
                            "brightness": "0-100",
                            "color_temp": "warm|neutral|cool"
                        },
                        "example": {"type": "adjust_lights", "params": {"brightness": 70, "color_temp": "warm"}}
                    },
                    "reduce_stimulation": {
                        "params": {},
                        "example": {"type": "reduce_stimulation", "params": {}}
                    }
                }
            },
            "task_management": {
                "description": "Manage tasks and focus",
                "actions": {
                    "set_focus": {
                        "params": {
                            "task_name": "what to focus on",
                            "duration_minutes": "optional - expected duration"
                        },
                        "example": {"type": "set_focus", "params": {"task_name": "Email responses", "duration_minutes": 30}}
                    },
                    "add_task": {
                        "params": {
                            "title": "task description",
                            "priority": "low|medium|high|urgent",
                            "due_time": "optional - when due"
                        },
                        "example": {"type": "add_task", "params": {"title": "Review meeting notes", "priority": "medium"}}
                    },
                    "complete_task": {
                        "params": {"task_name": "which task was completed"},
                        "example": {"type": "complete_task", "params": {"task_name": "Email responses"}}
                    }
                }
            },
            "medication_tracking": {
                "description": "Track medication and effectiveness",
                "actions": {
                    "log_medication": {
                        "params": {"taken": "true|false", "time": "optional - when taken"},
                        "example": {"type": "log_medication", "params": {"taken": "true"}}
                    },
                    "set_medication_reminder": {
                        "params": {"time": "when to remind"},
                        "example": {"type": "set_medication_reminder", "params": {"time": "8:00 PM"}}
                    }
                }
            },
            "pattern_tracking": {
                "description": "Track and log behavioral patterns",
                "actions": {
                    "log_pattern": {
                        "params": {
                            "pattern_type": "procrastination|hyperfocus|time_blindness|task_switching|overwhelm",
                            "context": "what triggered it"
                        },
                        "example": {"type": "log_pattern", "params": {"pattern_type": "procrastination", "context": "Large undefined task"}}
                    }
                }
            }
        }
    
    @staticmethod
    def get_tool_prompt() -> str:
        """Generate the tool awareness section for Claude's prompt."""
        tools = ToolRegistry.get_available_tools()
        
        prompt = "\n\nAVAILABLE TOOLS YOU CAN USE:\n"
        prompt += "="*50 + "\n\n"
        
        for category, info in tools.items():
            prompt += f"📦 {category.upper()}: {info['description']}\n"
            for action_name, action_info in info['actions'].items():
                prompt += f"  • {action_name}:\n"
                prompt += f"    Parameters: {json.dumps(action_info['params'], indent=6)}\n"
                prompt += f"    Example: {json.dumps(action_info['example'], indent=6)}\n"
            prompt += "\n"
        
        prompt += """
TOOL USAGE RULES:
1. You can execute multiple tools in one response
2. Tools execute in the order listed in immediate_actions
3. Use high priority for time-sensitive actions
4. Chain tools for complex interventions (e.g., timer + nudge + music)
5. Consider device availability before targeting specific devices
6. Default to 'all' devices for important nudges

EXAMPLE MULTI-TOOL RESPONSE:
{
  "immediate_actions": [
    {"type": "stop_music", "params": {}},
    {"type": "send_nudge", "params": {"message": "Time for a break!", "urgency": "normal"}},
    {"type": "set_timer", "params": {"minutes": 5, "purpose": "break", "alert_message": "Break over, ready to continue?"}},
    {"type": "play_music", "params": {"mood": "calm", "duration_minutes": 5}}
  ]
}
"""
        
        return prompt


class StateGatherer:
    """Gathers complete system state from all sources."""
    
    def __init__(self):
        self.google = get_google_integration()
        self.redis_client = None
        self._init_redis()
        
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
    
    async def gather_complete_state(self, message: str, user_id: str) -> CompleteSystemState:
        """Gather ALL state from ALL sources."""
        
        # Get Google data
        google_context = {}
        if self.google:
            try:
                google_context = self.google.get_adhd_context()
            except Exception as e:
                logger.error(f"Failed to get Google context: {e}")
        
        # Get user interaction history
        recent_messages = await self._get_recent_messages(user_id)
        last_interaction = await self._get_last_interaction_time(user_id)
        
        # Physical state from Google Fit - USE ALL DATA WE'RE COLLECTING!
        fitness = google_context.get("fitness", {})
        steps = fitness.get("steps_today", 0)
        last_movement = fitness.get("last_activity_minutes", 60)
        
        # Additional Fit data we're already collecting but not using
        calories_burned = 0
        distance_km = 0
        active_minutes = 0
        steps_last_hour = fitness.get("steps_last_hour", 0)
        
        # Get the actual fitness data if available
        sleep_hours = 7.0  # Default assumption
        sleep_quality = 5
        poor_sleep = False
        
        if self.google and self.google.fitness_service:
            try:
                fit_data = self.google.get_fitness_data()
                if fit_data:
                    calories_burned = fit_data.calories_burned
                    distance_km = fit_data.distance_meters / 1000
                    active_minutes = fit_data.active_minutes
                    
                    # Get sleep data if available
                    if fit_data.sleep_data:
                        sleep_hours = fit_data.sleep_data.duration_hours
                        sleep_quality = fit_data.sleep_data.quality_score
                        poor_sleep = fit_data.sleep_data.is_poor_sleep
                        logger.info(f"Sleep data: {sleep_hours}h, quality {sleep_quality}/10")
            except Exception as e:
                logger.warning(f"Could not get full fitness data: {e}")
        
        # Get sitting duration from Redis
        sitting_duration = await self._get_sitting_duration(user_id)
        last_hydration = await self._get_last_hydration(user_id)
        
        # Temporal state
        now = datetime.now()
        current_time = now.strftime("%I:%M %p")
        day_part = self._get_day_part(now.hour)
        weekday_weekend = "weekday" if now.weekday() < 5 else "weekend"
        typical_energy = self._get_typical_energy(now.hour)
        
        # Task state from Google
        tasks = google_context.get("tasks", {})
        urgent_tasks = [t["title"] for t in tasks.get("urgent_tasks", [])][:5]
        
        # Get calendar for upcoming
        calendar = google_context.get("calendar", {})
        upcoming = []
        if calendar.get("next_event"):
            event = calendar["next_event"]
            if event["minutes_until"] <= 30:
                upcoming.append(f"{event['title']} in {event['minutes_until']}min")
        
        # Current focus from Redis
        current_focus = await self._get_current_focus(user_id)
        task_duration = await self._get_task_duration(user_id, current_focus)
        
        # Environment state
        devices = await self._get_available_devices()
        music_status = await self._get_music_status()
        ambient_noise = await self._get_ambient_noise()
        distractions = await self._get_distractions()
        
        # Medication tracking
        med_info = await self._get_medication_info(user_id)
        
        # Pattern history
        patterns = await self._get_recent_patterns(user_id)
        crash_times = await self._get_crash_times(user_id)
        hyperfocus_triggers = await self._get_hyperfocus_triggers(user_id)
        success_rate = await self._calculate_success_rate(user_id)
        
        # Recent activity
        last_nudge = await self._get_last_nudge_time(user_id)
        last_break = await self._get_last_break_time(user_id)
        recent_actions = await self._get_recent_actions(user_id)
        ignored_count = await self._get_ignored_suggestions_count(user_id)
        
        # Previous decision context
        previous_decision = await self._get_previous_decision(user_id)
        previous_outcome = await self._get_previous_outcome(user_id)
        user_feedback = await self._get_user_feedback(user_id)
        
        # Detect emotional indicators
        emotional_indicators = self._detect_emotional_indicators(message)
        
        return CompleteSystemState(
            # User Context
            current_message=message,
            last_interaction_minutes=last_interaction,
            recent_messages=recent_messages,
            emotional_indicators=emotional_indicators,
            
            # Physical State - ENHANCED WITH FULL FIT DATA
            steps_today=steps,
            steps_last_hour=steps_last_hour,
            calories_burned=calories_burned,
            distance_km=distance_km,
            active_minutes=active_minutes,
            last_movement_minutes=last_movement,
            sitting_duration_minutes=sitting_duration,
            last_hydration_minutes=last_hydration,
            
            # Sleep Data
            sleep_hours=sleep_hours,
            sleep_quality=sleep_quality,
            poor_sleep=poor_sleep,
            
            # Temporal State
            current_time=current_time,
            day_part=day_part,
            weekday_weekend=weekday_weekend,
            typical_energy_now=typical_energy,
            
            # Task State
            current_focus=current_focus,
            task_duration_minutes=task_duration,
            urgent_tasks=urgent_tasks,
            overdue_tasks=[],  # TODO: Calculate from tasks
            upcoming_30min=upcoming,
            
            # Environment
            ambient_noise=ambient_noise,
            distractions=distractions,
            available_devices=devices,
            music_playing=music_status["playing"],
            music_mood=music_status.get("mood"),
            
            # Medication
            last_medication=med_info["last_taken"],
            next_medication=med_info["next_due"],
            medication_effective=med_info["effective"],
            
            # Patterns & History
            recent_patterns=patterns,
            typical_crash_times=crash_times,
            hyperfocus_triggers=hyperfocus_triggers,
            success_rate_today=success_rate,
            
            # Recent System Activity
            last_nudge_ago=last_nudge,
            last_break_ago=last_break,
            recent_actions=recent_actions,
            ignored_suggestions_count=ignored_count,
            
            # Decision Context
            previous_decision=previous_decision,
            previous_outcome=previous_outcome,
            user_feedback=user_feedback
        )
    
    # Include all helper methods from original (omitted for brevity - same as before)
    def _get_day_part(self, hour: int) -> str:
        if hour < 6:
            return "early_morning"
        elif hour < 12:
            return "morning"
        elif hour < 14:
            return "midday"
        elif hour < 17:
            return "afternoon"
        elif hour < 20:
            return "evening"
        else:
            return "night"
    
    def _get_typical_energy(self, hour: int) -> str:
        if 10 <= hour <= 11 or 16 <= hour <= 17:
            return "peak"
        elif 7 <= hour <= 9 or 18 <= hour <= 20:
            return "moderate"
        elif 13 <= hour <= 15:
            return "post_lunch_dip"
        else:
            return "low"
    
    def _detect_emotional_indicators(self, message: str) -> str:
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["overwhelmed", "too much", "can't handle"]):
            return "overwhelmed"
        elif any(word in message_lower for word in ["stressed", "anxious", "worried"]):
            return "anxious"
        elif any(word in message_lower for word in ["frustrated", "stuck", "annoyed"]):
            return "frustrated"
        elif any(word in message_lower for word in ["excited", "pumped", "ready"]):
            return "motivated"
        elif any(word in message_lower for word in ["tired", "exhausted", "drained"]):
            return "fatigued"
        else:
            return "neutral"
    
    # Add all other helper methods (same as original)
    async def _get_recent_messages(self, user_id: str) -> List[Dict[str, str]]:
        if not self.redis_client:
            return []
        try:
            messages = await self.redis_client.lrange(f"messages:{user_id}", 0, 4)
            return [json.loads(m) for m in messages] if messages else []
        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []
    
    async def _get_last_interaction_time(self, user_id: str) -> int:
        if not self.redis_client:
            return 0
        try:
            last_time = await self.redis_client.get(f"last_interaction:{user_id}")
            if last_time:
                last_dt = datetime.fromisoformat(last_time)
                return int((datetime.now() - last_dt).total_seconds() / 60)
            return 999
        except:
            return 0
    
    async def _get_sitting_duration(self, user_id: str) -> int:
        return 30  # Default
    
    async def _get_last_hydration(self, user_id: str) -> int:
        return 60  # Default
    
    async def _get_current_focus(self, user_id: str) -> Optional[str]:
        if not self.redis_client:
            return None
        try:
            focus = await self.redis_client.get(f"current_focus:{user_id}")
            return focus
        except:
            return None
    
    async def _get_task_duration(self, user_id: str, task: Optional[str]) -> int:
        if not task or not self.redis_client:
            return 0
        try:
            start_time = await self.redis_client.get(f"task_start:{user_id}:{task}")
            if start_time:
                start_dt = datetime.fromisoformat(start_time)
                return int((datetime.now() - start_dt).total_seconds() / 60)
            return 0
        except:
            return 0
    
    async def _get_available_devices(self) -> List[str]:
        return ["Nest Hub Max", "Nest Mini", "Living Room speaker"]
    
    async def _get_music_status(self) -> Dict[str, Any]:
        return {"playing": False, "mood": None}
    
    async def _get_ambient_noise(self) -> str:
        return "quiet"
    
    async def _get_distractions(self) -> List[str]:
        return []
    
    async def _get_medication_info(self, user_id: str) -> Dict[str, Any]:
        now = datetime.now()
        return {
            "last_taken": "8:00 AM" if now.hour > 8 else "yesterday",
            "next_due": "8:00 PM" if now.hour < 20 else "8:00 AM",
            "effective": 8 <= now.hour <= 16
        }
    
    async def _get_recent_patterns(self, user_id: str) -> List[str]:
        if not self.redis_client:
            return []
        try:
            patterns = await self.redis_client.lrange(f"patterns:{user_id}", 0, 4)
            return patterns if patterns else []
        except:
            return []
    
    async def _get_crash_times(self, user_id: str) -> List[str]:
        return ["3:00 PM", "8:00 PM"]
    
    async def _get_hyperfocus_triggers(self, user_id: str) -> List[str]:
        return ["coding", "research", "gaming"]
    
    async def _calculate_success_rate(self, user_id: str) -> float:
        return 0.65
    
    async def _get_last_nudge_time(self, user_id: str) -> str:
        return "15 minutes ago"
    
    async def _get_last_break_time(self, user_id: str) -> str:
        return "45 minutes ago"
    
    async def _get_recent_actions(self, user_id: str) -> List[Dict[str, Any]]:
        if not self.redis_client:
            return []
        try:
            actions = await self.redis_client.lrange(f"actions:{user_id}", 0, 4)
            return [json.loads(a) for a in actions] if actions else []
        except:
            return []
    
    async def _get_ignored_suggestions_count(self, user_id: str) -> int:
        return 0
    
    async def _get_previous_decision(self, user_id: str) -> Dict[str, Any]:
        if not self.redis_client:
            return {}
        try:
            decision = await self.redis_client.get(f"last_decision:{user_id}")
            return json.loads(decision) if decision else {}
        except:
            return {}
    
    async def _get_previous_outcome(self, user_id: str) -> str:
        return "unknown"
    
    async def _get_user_feedback(self, user_id: str) -> Optional[str]:
        return None


class ClaudeCognitiveEngineV2:
    """The main cognitive engine powered by Claude with tool awareness."""
    
    # Enhanced system prompt with tool awareness
    SYSTEM_PROMPT = """You are an ADHD cognitive support system making real-time decisions based on user state.
You have access to various tools to help manage the user's environment, tasks, and well-being.

CRITICAL: Respond with ONLY a JSON object, no other text. The JSON must match this EXACT structure:

{
  "reasoning": "Brief explanation of your decision process",
  "confidence": 0.0-1.0,
  "response_to_user": "Natural message if user needs communication, or null",
  "immediate_actions": [
    {
      "type": "action_type_from_available_tools",
      "params": {},
      "priority": "high|medium|low"
    }
  ],
  "scheduled_actions": [
    {
      "delay_minutes": 15,
      "action": {"type": "...", "params": {}}
    }
  ],
  "state_updates": {
    "stress_level": "low|medium|high|critical",
    "focus_state": "deep|shallow|scattered|recovering",
    "energy_trend": "rising|stable|falling|crashed",
    "intervention_needed": "true|false",
    "current_focus": "task name or null"
  },
  "patterns_detected": ["procrastination", "hyperfocus", "time_blindness"],
  "prediction": {
    "next_need": "break|food|movement|medication|sleep",
    "timeframe_minutes": 30,
    "confidence": 0.8
  }
}

CRITICAL RULES:
1. Response must be ONLY valid JSON - no explanations outside
2. All fields required - use null/[]/{} for empty
3. response_to_user ONLY when user needs direct communication
4. Consider medication effectiveness window
5. Prioritize movement if sitting > 60 minutes
6. Detect and interrupt hyperfocus after 90 minutes
7. Be encouraging but realistic about ADHD challenges
8. Use available tools proactively to support the user
9. Chain multiple tools for comprehensive interventions
10. Consider device availability when targeting specific devices"""
    
    def __init__(self):
        self.state_gatherer = StateGatherer()
        self.claude = None
        self.redis_client = None
        self.tool_registry = ToolRegistry()
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis for storing decisions."""
        try:
            self.redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
    
    def _build_user_prompt(self, state: CompleteSystemState) -> str:
        """Build the user prompt with complete state and tool awareness."""
        
        # Get tool information
        tool_prompt = self.tool_registry.get_tool_prompt()
        
        # Build state information
        state_prompt = f"""Current State:

USER CONTEXT:
- Current message: "{state.current_message}"
- Last interaction: {state.last_interaction_minutes} minutes ago
- Recent messages: {json.dumps(state.recent_messages)}
- Emotional indicators: {state.emotional_indicators}

PHYSICAL STATE:
- Steps today: {state.steps_today} (last hour: {state.steps_last_hour})
- Calories burned: {state.calories_burned} cal
- Distance walked: {state.distance_km:.1f} km
- Active minutes: {state.active_minutes} min
- Last movement: {state.last_movement_minutes} minutes ago
- Sitting duration: {state.sitting_duration_minutes} minutes
- Hydration reminder: {state.last_hydration_minutes} minutes ago
- Energy expenditure rate: {state.calories_burned / max(state.active_minutes, 1):.1f} cal/min
- Movement quality: {"good" if state.active_minutes > 10 else "needs improvement"}

SLEEP DATA:
- Last night: {state.sleep_hours} hours
- Sleep quality: {state.sleep_quality}/10
- Impact: {"POOR SLEEP - medication less effective, higher crash risk" if state.poor_sleep else "Adequate sleep for ADHD management"}

TEMPORAL STATE:
- Current time: {state.current_time}
- Day part: {state.day_part}
- Day type: {state.weekday_weekend}
- Typical energy: {state.typical_energy_now}

TASK STATE:
- Current focus: "{state.current_focus or 'none'}"
- Task duration: {state.task_duration_minutes} minutes
- Urgent items: {json.dumps(state.urgent_tasks)}
- Overdue items: {json.dumps(state.overdue_tasks)}
- Upcoming (30min): {json.dumps(state.upcoming_30min)}

ENVIRONMENT:
- Ambient noise: {state.ambient_noise}
- Distractions present: {json.dumps(state.distractions)}
- Available devices: {json.dumps(state.available_devices)}
- Music playing: {state.music_playing}
- Music mood: {state.music_mood or 'none'}

MEDICATION:
- Last taken: {state.last_medication}
- Next due: {state.next_medication}
- In therapeutic window: {state.medication_effective}

PATTERNS:
- Recent patterns: {json.dumps(state.recent_patterns)}
- Energy crashes typically at: {json.dumps(state.typical_crash_times)}
- Hyperfocus triggers: {json.dumps(state.hyperfocus_triggers)}
- Success rate today: {state.success_rate_today:.0%}

RECENT ACTIONS:
- Last nudge: {state.last_nudge_ago}
- Last break: {state.last_break_ago}
- Actions taken: {json.dumps(state.recent_actions)}
- Ignored suggestions: {state.ignored_suggestions_count}

DECISION CONTEXT:
Previous decision: {json.dumps(state.previous_decision)}
Outcome: {state.previous_outcome}
User feedback: {state.user_feedback or 'none'}"""
        
        # Combine state and tools with clear instruction
        full_prompt = state_prompt + "\n" + tool_prompt + "\n\nNow analyze this state and respond with a JSON decision following the structure shown above."
        
        return full_prompt
    
    async def process(self, message: str, user_id: str) -> Dict[str, Any]:
        """Main processing - gather state, get decision, execute."""
        try:
            # 1. Gather complete state
            state = await self.state_gatherer.gather_complete_state(message, user_id)
            
            # 2. Get Claude's decision (browser-only)
            decision = await self._get_claude_decision(state)
            
            # 3. Execute the decision
            execution_results = await self._execute_decision(decision, user_id)
            
            # 4. Store for learning
            await self._store_decision(user_id, decision, state)
            
            # 5. Return structured response
            return {
                "response": decision.get("response_to_user", "Processing..."),
                "thinking": {
                    "reasoning": decision.get("reasoning"),
                    "confidence": decision.get("confidence"),
                    "patterns": decision.get("patterns_detected")
                },
                "actions_taken": execution_results,
                "state_updates": decision.get("state_updates"),
                "prediction": decision.get("prediction"),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Cognitive engine error: {e}")
            # Add detailed traceback for debugging
            import traceback
            full_traceback = traceback.format_exc()
            logger.error(f"Full traceback: {full_traceback}")
            
            return {
                "response": "I need a moment to recalibrate. What's your biggest challenge right now?",
                "thinking": {
                    "error": str(e),
                    "traceback": full_traceback,
                    "debug_info": "Added detailed logging to find 'true' error source"
                },
                "actions_taken": [],
                "success": False
            }
    
    async def _get_claude_decision(self, state: CompleteSystemState) -> Dict[str, Any]:
        """Get decision from Claude using browser-only authentication."""
        prompt = self._build_user_prompt(state)
        
        # Initialize Claude with working browser client
        if not self.claude:
            try:
                # Use the working browser client that actually launches its own browser
                self.claude = await get_claude_browser()
                logger.info("✅ Using working browser client for Claude")
            except Exception as e:
                logger.error(f"Failed to initialize Claude browser client: {e}")
                # Return fallback response instead of crashing
                return {
                    'response': "Claude integration temporarily unavailable. Please refresh session with manual_session_refresh.py",
                    'thinking': {'reasoning': 'Browser client initialization failed', 'error': str(e)},
                    'actions_taken': [],
                    'state_updates': {},
                    'prediction': {},
                    'success': False
                }
        
        # Get response with strict JSON
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}"
        
        try:
            # Use smart session manager if available, otherwise fallback
            if hasattr(self.claude, 'send_message_with_retry'):
                response = await self.claude.send_message_with_retry(full_prompt)
            else:
                response = await self.claude.send_message(full_prompt)
            
            # Extract JSON from response
            import re
            
            # Try to find JSON in the response
            # First, try to parse the entire response as JSON
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
            
            # Try to extract JSON object from the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse extracted JSON: {json_match.group()[:100]}")
            
            # If response looks like it's echoing the prompt, return a default decision
            if "Make a decision" in response or "analyze this state" in response:
                logger.warning("Claude echoed the prompt, using default decision")
                return self._create_default_decision(state)
            
            # Fallback parsing
            return self._parse_text_response(response)
                
        except Exception as e:
            logger.error(f"Claude decision failed: {e}")
            # No fallback patterns - we want real Claude thinking
            raise
    
    def _create_default_decision(self, state: CompleteSystemState) -> Dict[str, Any]:
        """Create a sensible default decision based on state."""
        # Analyze state to create appropriate actions
        actions = []
        
        # Check if user needs a break
        if state.sitting_duration_minutes > 45:
            actions.append({
                "type": "send_nudge",
                "params": {"message": "Time for a movement break!", "urgency": "gentle"},
                "priority": "medium"
            })
        
        # Check hydration
        if state.last_hydration_minutes > 60:
            actions.append({
                "type": "send_nudge", 
                "params": {"message": "Stay hydrated! 💧", "urgency": "gentle"},
                "priority": "low"
            })
        
        return {
            "reasoning": "Default decision based on state analysis",
            "confidence": 0.3,
            "response_to_user": "I'll help you stay focused and healthy.",
            "immediate_actions": actions,
            "scheduled_actions": [],
            "state_updates": {
                "stress_level": "medium",
                "focus_state": "shallow",
                "energy_trend": "stable",
                "intervention_needed": len(actions) > 0
            },
            "patterns_detected": [],
            "prediction": {
                "next_need": "break" if state.sitting_duration_minutes > 30 else "focus",
                "timeframe_minutes": 15,
                "confidence": 0.3
            }
        }
    
    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """Parse non-JSON response into decision structure."""
        return {
            "reasoning": "Parsed from text response",
            "confidence": 0.5,
            "response_to_user": response[:500],
            "immediate_actions": [],
            "scheduled_actions": [],
            "state_updates": {
                "stress_level": "medium",
                "focus_state": "shallow",
                "energy_trend": "stable",
                "intervention_needed": False
            },
            "patterns_detected": [],
            "prediction": {
                "next_need": "unknown",
                "timeframe_minutes": 60,
                "confidence": 0.3
            }
        }
    
    async def _execute_decision(self, decision: Dict[str, Any], user_id: str) -> List[Dict]:
        """Execute the actions from decision with confidence gating."""
        results = []
        
        # Check confidence level for gating
        confidence = decision.get("confidence", 0.5)
        
        # Confidence gating - prevents low-confidence actions
        if confidence < 0.3:
            # Too uncertain - ask user for clarification
            return [{
                "type": "user_confirmation_needed",
                "confidence": confidence,
                "proposed_actions": decision.get("immediate_actions", []),
                "status": "gated_low_confidence"
            }]
        
        # Import actual tool executors
        try:
            from .music_controller import MusicController
            from .nest_nudges import NestNudgeSystem
            from .timer_system import TimerSystem
            from .task_manager import TaskManager
            
            # Initialize executors
            music = MusicController()
            nudges = NestNudgeSystem()
            timers = TimerSystem()
            tasks = TaskManager()
            
            executors = {
                "music": music,
                "nudges": nudges,
                "timers": timers,
                "tasks": tasks
            }
            
        except ImportError:
            # Fallback to mock executors
            executors = {
                "music": None,
                "nudges": None, 
                "timers": None,
                "tasks": None
            }
        
        # Medium confidence - notify user of actions being taken
        if confidence < 0.7:
            await self._notify_user_of_actions(decision, user_id)
        
        # Execute immediate actions
        for action in decision.get("immediate_actions", []):
            result = await self._execute_action(action, user_id, executors)
            results.append(result)
        
        # Schedule future actions
        for scheduled in decision.get("scheduled_actions", []):
            await self._schedule_action(scheduled, user_id)
        
        # Update state
        if decision.get("state_updates"):
            await self._update_state(user_id, decision["state_updates"])
        
        # Add confidence metadata to results
        results.append({
            "type": "execution_metadata",
            "confidence": confidence,
            "confidence_level": self._get_confidence_label(confidence),
            "status": "executed"
        })
        
        return results
    
    def _get_confidence_label(self, confidence: float) -> str:
        """Get human-readable confidence level."""
        if confidence >= 0.8:
            return "very_high"
        elif confidence >= 0.7:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        elif confidence >= 0.3:
            return "low"
        else:
            return "very_low"
    
    async def _notify_user_of_actions(self, decision: Dict, user_id: str):
        """Notify user when medium confidence actions are being taken."""
        actions = decision.get("immediate_actions", [])
        if actions:
            action_summary = ", ".join([a.get("type", "unknown") for a in actions])
            logger.info(f"Medium confidence ({decision.get('confidence', 0):.1%}) - executing: {action_summary}")
            
            # Could send actual notification here
            if self.redis_client:
                notification = {
                    "type": "action_notification",
                    "confidence": decision.get("confidence"),
                    "actions": action_summary,
                    "timestamp": datetime.now().isoformat()
                }
                await self.redis_client.lpush(
                    f"notifications:{user_id}",
                    json.dumps(notification)
                )
    
    async def _execute_action(self, action: Dict, user_id: str, executors: Dict) -> Dict:
        """Execute a single action using real tool executors."""
        action_type = action.get("type")
        params = action.get("params", {})
        
        logger.info(f"Executing action: {action_type} with params: {params}")
        
        # Map to actual system actions
        if action_type == "play_music":
            try:
                result = await executors["music"].play_mood(params.get("mood", "focus"))
                return {"type": "music", "status": "playing", "params": params}
            except Exception as e:
                logger.error(f"Music action failed: {e}")
                return {"type": "music", "status": "failed", "error": str(e)}
        
        elif action_type == "send_nudge":
            try:
                # Map urgency strings to NudgeType enum values
                from mcp_server.nest_nudges import NudgeType
                urgency_map = {
                    "gentle": NudgeType.GENTLE,
                    "normal": NudgeType.GENTLE,  # Default to gentle
                    "firm": NudgeType.URGENT,
                    "critical": NudgeType.URGENT,
                    "urgent": NudgeType.URGENT
                }
                urgency = params.get("urgency", "normal")
                nudge_type = urgency_map.get(urgency, NudgeType.GENTLE)
                
                await executors["nudges"].send_nudge(
                    params.get("message"),
                    nudge_type=nudge_type,
                    device_name=params.get("device")
                )
                return {"type": "nudge", "status": "sent", "message": params.get("message")}
            except Exception as e:
                logger.error(f"Nudge action failed: {e}")
                return {"type": "nudge", "status": "failed", "error": str(e)}
        
        elif action_type == "set_timer":
            try:
                timer_id = await executors["timers"].set_timer(
                    params.get("minutes"),
                    purpose=params.get("purpose"),
                    message=params.get("alert_message")
                )
                return {"type": "timer", "status": "set", "timer_id": timer_id, "minutes": params.get("minutes")}
            except Exception as e:
                logger.error(f"Timer action failed: {e}")
                return {"type": "timer", "status": "failed", "error": str(e)}
        
        elif action_type == "set_focus":
            try:
                await executors["tasks"].set_focus(user_id, params.get("task_name"))
                return {"type": "focus", "status": "updated", "task": params.get("task_name")}
            except Exception as e:
                logger.error(f"Focus action failed: {e}")
                return {"type": "focus", "status": "failed", "error": str(e)}
        
        return {"type": action_type, "status": "unknown"}
    
    async def _schedule_action(self, scheduled: Dict, user_id: str):
        """Schedule a future action."""
        if self.redis_client:
            key = f"scheduled:{user_id}:{datetime.now().timestamp()}"
            await self.redis_client.set(key, json.dumps(scheduled), ex=scheduled["delay_minutes"] * 60)
    
    async def _update_state(self, user_id: str, updates: Dict):
        """Update system state based on decision."""
        if self.redis_client:
            # Update current focus
            if "current_focus" in updates:
                await self.redis_client.set(f"current_focus:{user_id}", updates["current_focus"])
                await self.redis_client.set(f"task_start:{user_id}:{updates['current_focus']}", 
                                           datetime.now().isoformat())
            
            # Store state assessment
            await self.redis_client.set(f"state_assessment:{user_id}", json.dumps(updates))
    
    async def _store_decision(self, user_id: str, decision: Dict, state: CompleteSystemState):
        """Store decision for learning - NOW WITH PERMANENT DATABASE STORAGE!"""
        
        # Store in database for permanent record (PostgreSQL or SQLite)
        try:
            db = await get_persistent_storage()
            
            # Store the complete state snapshot
            snapshot_id = await db.store_state_snapshot(user_id, state)
            
            # Store Claude's decision linked to the snapshot
            if snapshot_id:
                await db.store_claude_decision(user_id, snapshot_id, decision)
            
            # Update daily fitness trends
            fitness_data = {
                'steps_today': state.steps_today,
                'calories_burned': state.calories_burned,
                'distance_km': state.distance_km,
                'active_minutes': state.active_minutes
            }
            await db.update_daily_fitness(user_id, fitness_data)
            
            # Log any ADHD patterns detected
            for pattern in decision.get("patterns_detected", []):
                await db.log_adhd_pattern(
                    user_id=user_id,
                    pattern_type=pattern,
                    context=state.current_message,
                    physical_state=asdict(state),
                    intervention=decision.get("response_to_user")
                )
            
            logger.info(f"✅ Stored decision in PostgreSQL for {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store in database: {e}")
        
        # Also store in Redis for fast access (temporary cache)
        if self.redis_client:
            # Store decision
            await self.redis_client.set(f"last_decision:{user_id}", json.dumps(decision))
            
            # Store patterns
            for pattern in decision.get("patterns_detected", []):
                await self.redis_client.lpush(f"patterns:{user_id}", pattern)
                await self.redis_client.ltrim(f"patterns:{user_id}", 0, 19)  # Keep last 20
            
            # Store message
            message_entry = {
                "message": state.current_message,
                "timestamp": datetime.now().isoformat(),
                "emotional_state": state.emotional_indicators
            }
            await self.redis_client.lpush(f"messages:{user_id}", json.dumps(message_entry))
            await self.redis_client.ltrim(f"messages:{user_id}", 0, 9)  # Keep last 10
            
            # Update interaction time
            await self.redis_client.set(f"last_interaction:{user_id}", datetime.now().isoformat())


# Global instance
_engine_v2 = None

def get_cognitive_engine_v2() -> ClaudeCognitiveEngineV2:
    """Get or create the cognitive engine v2 singleton."""
    global _engine_v2
    if _engine_v2 is None:
        _engine_v2 = ClaudeCognitiveEngineV2()
    return _engine_v2