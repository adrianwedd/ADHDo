"""
User Onboarding System for MCP ADHD Server.

Guides new users through ADHD-optimized setup and preference configuration.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

import structlog
from pydantic import BaseModel

from mcp_server.models import User, NudgeTier
from mcp_server.auth import auth_manager

logger = structlog.get_logger()


class OnboardingStep(str, Enum):
    """Onboarding step identifiers."""
    WELCOME = "welcome"
    ADHD_PROFILE = "adhd_profile"
    NUDGE_PREFERENCES = "nudge_preferences"
    INTEGRATION_SETUP = "integration_setup"
    FIRST_TASK = "first_task"
    COMPLETED = "completed"


class OnboardingData(BaseModel):
    """User onboarding progress data."""
    user_id: str
    current_step: OnboardingStep
    started_at: datetime
    completed_at: Optional[datetime] = None
    step_data: Dict[str, Any] = {}
    is_completed: bool = False


class ADHDProfileData(BaseModel):
    """ADHD-specific profile information."""
    # Core ADHD characteristics
    primary_challenges: List[str] = []  # e.g., ["focus", "organization", "time_management"]
    strengths: List[str] = []  # e.g., ["creativity", "hyperfocus", "problem_solving"]
    
    # Energy patterns
    best_focus_times: List[str] = []  # e.g., ["morning", "afternoon", "evening"]
    energy_levels: Dict[str, str] = {}  # hour -> level mapping
    
    # Hyperfocus patterns
    hyperfocus_triggers: List[str] = []
    hyperfocus_duration: str = "2-4 hours"  # typical duration
    post_hyperfocus_needs: List[str] = []  # what helps after hyperfocus crashes
    
    # Overwhelm patterns
    overwhelm_triggers: List[str] = []
    early_warning_signs: List[str] = []
    coping_strategies: List[str] = []
    
    # Motivation and rewards
    motivation_style: str = "mixed"  # "internal", "external", "mixed"
    preferred_rewards: List[str] = []
    celebration_preferences: List[str] = []


class NudgePreferences(BaseModel):
    """User preferences for nudging system."""
    preferred_methods: List[str] = ["web"]  # "web", "telegram", "email"
    frequency: str = "normal"  # "minimal", "normal", "frequent"
    timing_preferences: Dict[str, str] = {
        "morning_checkin": "09:00",
        "afternoon_nudge": "14:00", 
        "evening_review": "18:00"
    }
    nudge_style: NudgeTier = NudgeTier.GENTLE
    
    # Context-aware preferences
    work_hours_start: str = "09:00"
    work_hours_end: str = "17:00"
    break_reminders: bool = True
    focus_session_alerts: bool = True
    celebration_messages: bool = True


class OnboardingManager:
    """Manages the user onboarding process."""
    
    def __init__(self):
        self._onboarding_sessions: Dict[str, OnboardingData] = {}
        self._step_handlers = {
            OnboardingStep.WELCOME: self._handle_welcome_step,
            OnboardingStep.ADHD_PROFILE: self._handle_adhd_profile_step,
            OnboardingStep.NUDGE_PREFERENCES: self._handle_nudge_preferences_step,
            OnboardingStep.INTEGRATION_SETUP: self._handle_integration_setup_step,
            OnboardingStep.FIRST_TASK: self._handle_first_task_step,
        }
    
    async def start_onboarding(self, user_id: str) -> OnboardingData:
        """Start onboarding process for a new user."""
        if user_id in self._onboarding_sessions:
            # Resume existing session
            return self._onboarding_sessions[user_id]
        
        onboarding = OnboardingData(
            user_id=user_id,
            current_step=OnboardingStep.WELCOME,
            started_at=datetime.utcnow()
        )
        
        self._onboarding_sessions[user_id] = onboarding
        
        logger.info("Started onboarding session", user_id=user_id)
        return onboarding
    
    async def get_onboarding_status(self, user_id: str) -> Optional[OnboardingData]:
        """Get current onboarding status for user."""
        return self._onboarding_sessions.get(user_id)
    
    async def process_step(self, user_id: str, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process user input for current onboarding step."""
        onboarding = self._onboarding_sessions.get(user_id)
        if not onboarding:
            raise ValueError("No onboarding session found for user")
        
        if onboarding.is_completed:
            return {"status": "completed", "message": "Onboarding already completed!"}
        
        # Get handler for current step
        handler = self._step_handlers.get(onboarding.current_step)
        if not handler:
            raise ValueError(f"No handler for step: {onboarding.current_step}")
        
        # Process the step
        result = await handler(onboarding, step_input)
        
        # Update onboarding data
        self._onboarding_sessions[user_id] = onboarding
        
        logger.info("Processed onboarding step", 
                   user_id=user_id, 
                   step=onboarding.current_step,
                   next_step=onboarding.current_step)
        
        return result
    
    async def _handle_welcome_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle welcome step - introduce the system."""
        # Store any initial preferences
        if step_input.get("ready"):
            onboarding.current_step = OnboardingStep.ADHD_PROFILE
            
            return {
                "status": "next_step",
                "step": "adhd_profile",
                "title": "Let's Learn About Your ADHD 🧠",
                "message": (
                    "Understanding your unique ADHD patterns helps me provide better support.\n\n"
                    "This is completely optional and you can skip any questions. "
                    "Everything you share is private and helps customize your experience."
                ),
                "questions": [
                    {
                        "id": "primary_challenges",
                        "type": "multi_select",
                        "question": "What are your biggest ADHD challenges? (Select all that apply)",
                        "options": [
                            "Staying focused on tasks",
                            "Getting started (procrastination)",
                            "Time management",
                            "Organization", 
                            "Remembering tasks/appointments",
                            "Managing overwhelm",
                            "Emotional regulation",
                            "Task switching"
                        ]
                    },
                    {
                        "id": "strengths",
                        "type": "multi_select", 
                        "question": "What are some of your ADHD superpowers? (Select all that apply)",
                        "options": [
                            "Creativity and out-of-box thinking",
                            "Hyperfocus abilities",
                            "Problem-solving skills",
                            "High energy and enthusiasm",
                            "Ability to think quickly",
                            "Entrepreneurial mindset",
                            "Empathy and emotional intelligence",
                            "Seeing the big picture"
                        ]
                    }
                ]
            }
        
        return {
            "status": "current_step",
            "step": "welcome",
            "title": "Welcome to MCP ADHD Server! 🎉",
            "message": (
                "I'm your AI-powered executive function support system, specifically designed "
                "for ADHD minds like yours.\n\n"
                "I'll help you:\n"
                "• Break down overwhelming tasks\n"
                "• Stay focused with gentle nudges\n"
                "• Celebrate your wins (big and small!)\n"
                "• Work *with* your ADHD, not against it\n\n"
                "Ready to get started?"
            ),
            "action": {
                "type": "button",
                "text": "Let's do this! 🚀",
                "value": {"ready": True}
            }
        }
    
    async def _handle_adhd_profile_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ADHD profile setup."""
        # Store ADHD profile data
        profile_data = {
            "primary_challenges": step_input.get("primary_challenges", []),
            "strengths": step_input.get("strengths", []),
            "best_focus_times": step_input.get("best_focus_times", []),
            "hyperfocus_triggers": step_input.get("hyperfocus_triggers", []),
            "overwhelm_triggers": step_input.get("overwhelm_triggers", []),
            "coping_strategies": step_input.get("coping_strategies", [])
        }
        
        onboarding.step_data["adhd_profile"] = profile_data
        onboarding.current_step = OnboardingStep.NUDGE_PREFERENCES
        
        return {
            "status": "next_step",
            "step": "nudge_preferences",
            "title": "Nudge & Reminder Preferences 📳",
            "message": (
                f"Thanks for sharing! Based on your preferences, I can see you value "
                f"{', '.join(profile_data['strengths'][:2]) if profile_data['strengths'] else 'your unique ADHD strengths'}.\n\n"
                "Now let's set up how you'd like me to help keep you on track:"
            ),
            "questions": [
                {
                    "id": "nudge_methods",
                    "type": "multi_select",
                    "question": "How would you like to receive reminders and nudges?",
                    "options": [
                        "Web notifications (in browser)",
                        "Telegram messages",
                        "Email reminders",
                        "Desktop notifications"
                    ]
                },
                {
                    "id": "nudge_frequency",
                    "type": "single_select",
                    "question": "How often would you like gentle check-ins?",
                    "options": [
                        "Minimal (only when asked)",
                        "Normal (2-3 times per day)",
                        "Frequent (hourly during work hours)",
                        "Adaptive (based on my activity)"
                    ]
                },
                {
                    "id": "nudge_style",
                    "type": "single_select", 
                    "question": "What nudging style works best for you?",
                    "options": [
                        "Gentle and encouraging 🌱",
                        "Playfully sarcastic 🙄", 
                        "Direct and assertive ⚡",
                        "Mix it up based on context"
                    ]
                }
            ]
        }
    
    async def _handle_nudge_preferences_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle nudge preferences configuration."""
        # Store nudge preferences
        nudge_prefs = {
            "methods": step_input.get("nudge_methods", ["web"]),
            "frequency": step_input.get("nudge_frequency", "normal"),
            "style": step_input.get("nudge_style", "gentle"),
            "work_hours_start": step_input.get("work_hours_start", "09:00"),
            "work_hours_end": step_input.get("work_hours_end", "17:00")
        }
        
        onboarding.step_data["nudge_preferences"] = nudge_prefs
        onboarding.current_step = OnboardingStep.INTEGRATION_SETUP
        
        return {
            "status": "next_step",
            "step": "integration_setup",
            "title": "Connect Your Tools 🔗",
            "message": (
                "Great choices! I'll send you gentle nudges that match your style.\n\n"
                "Want to connect any external tools? (All optional - you can set these up later)"
            ),
            "options": [
                {
                    "id": "telegram",
                    "title": "Telegram Bot",
                    "description": "Get nudges and chat with me via Telegram",
                    "setup_url": "/integrations/telegram",
                    "status": "available"
                },
                {
                    "id": "calendar",
                    "title": "Calendar Integration", 
                    "description": "Sync with Google Calendar for context-aware support",
                    "setup_url": "/integrations/calendar",
                    "status": "coming_soon"
                },
                {
                    "id": "home_assistant",
                    "title": "Home Assistant",
                    "description": "Environmental context for better focus support",
                    "setup_url": "/integrations/home_assistant", 
                    "status": "coming_soon"
                }
            ],
            "action": {
                "type": "button",
                "text": "Continue (set up later)",
                "value": {"skip_integrations": True}
            }
        }
    
    async def _handle_integration_setup_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle integration setup (optional)."""
        # Store integration preferences
        integrations = step_input.get("integrations", [])
        onboarding.step_data["integrations"] = integrations
        onboarding.current_step = OnboardingStep.FIRST_TASK
        
        return {
            "status": "next_step", 
            "step": "first_task",
            "title": "Your First Task 🎯",
            "message": (
                "Perfect! You're almost ready to go.\n\n"
                "Let's start with something simple. What would you like to work on right now? "
                "It can be anything - big or small!"
            ),
            "input": {
                "type": "text",
                "placeholder": "e.g., Respond to Sarah's email, Organize desk, Plan weekend...",
                "label": "What's one thing you'd like to tackle?"
            },
            "suggestions": [
                "Clear my email inbox",
                "Organize my workspace", 
                "Plan tomorrow's priorities",
                "Finish that project I've been putting off",
                "Take a quick break and reset"
            ]
        }
    
    async def _handle_first_task_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle first task setup and complete onboarding."""
        first_task = step_input.get("task", "")
        
        if first_task:
            onboarding.step_data["first_task"] = first_task
            
            # Apply all collected preferences to user account
            await self._apply_onboarding_preferences(onboarding)
            
            # Mark onboarding as completed
            onboarding.current_step = OnboardingStep.COMPLETED
            onboarding.is_completed = True
            onboarding.completed_at = datetime.utcnow()
            
            # Generate personalized welcome message
            user = auth_manager.get_user(onboarding.user_id)
            name = user.name if user else "there"
            
            challenges = onboarding.step_data.get("adhd_profile", {}).get("primary_challenges", [])
            challenge_text = f"I know {challenges[0].lower()} can be tough" if challenges else "I'm here to help"
            
            return {
                "status": "completed",
                "title": f"Welcome aboard, {name}! 🎉",
                "message": (
                    f"You're all set up! {challenge_text}, but together we'll make progress.\n\n"
                    f"Let's start with your first task: **{first_task}**\n\n"
                    "I'm here whenever you need support. Just tell me what's on your mind!"
                ),
                "next_action": {
                    "type": "start_chat",
                    "initial_message": f"I'm ready to work on: {first_task}",
                    "task_focus": first_task
                },
                "quick_tips": [
                    "💬 Chat naturally - I understand context",
                    "🎯 Set your current focus anytime", 
                    "⏸️ Tell me when you need breaks",
                    "🎉 I'll celebrate your wins!"
                ]
            }
        
        return {
            "status": "current_step",
            "error": "Please enter a task to get started"
        }
    
    async def _apply_onboarding_preferences(self, onboarding: OnboardingData) -> None:
        """Apply collected preferences to user account."""
        user = auth_manager.get_user(onboarding.user_id)
        if not user:
            logger.error("User not found during onboarding completion", user_id=onboarding.user_id)
            return
        
        # Apply ADHD profile
        adhd_profile = onboarding.step_data.get("adhd_profile", {})
        if adhd_profile:
            user.energy_patterns = {
                "primary_challenges": adhd_profile.get("primary_challenges", []),
                "strengths": adhd_profile.get("strengths", []),
                "best_focus_times": adhd_profile.get("best_focus_times", []),
                "peak_hours": [9, 10, 11, 14, 15, 16]  # Default, can be customized later
            }
            
            user.hyperfocus_indicators = adhd_profile.get("hyperfocus_triggers", ["long_sessions"])
            
        # Apply nudge preferences  
        nudge_prefs = onboarding.step_data.get("nudge_preferences", {})
        if nudge_prefs:
            # Map UI selections to system values
            method_mapping = {
                "Web notifications (in browser)": "web",
                "Telegram messages": "telegram",
                "Email reminders": "email"
            }
            
            user.preferred_nudge_methods = [
                method_mapping.get(method, method.lower()) 
                for method in nudge_prefs.get("methods", ["web"])
            ]
            
            style_mapping = {
                "Gentle and encouraging 🌱": NudgeTier.GENTLE,
                "Playfully sarcastic 🙄": NudgeTier.SARCASTIC,
                "Direct and assertive ⚡": NudgeTier.SERGEANT
            }
            
            user.nudge_timing_preferences = {
                "morning": nudge_prefs.get("work_hours_start", "09:00"),
                "afternoon": "14:00",
                "evening": nudge_prefs.get("work_hours_end", "17:00")
            }
        
        logger.info("Applied onboarding preferences", 
                   user_id=onboarding.user_id,
                   preferences_applied=list(onboarding.step_data.keys()))
    
    async def skip_onboarding(self, user_id: str) -> Dict[str, Any]:
        """Skip onboarding and use default settings."""
        onboarding = OnboardingData(
            user_id=user_id,
            current_step=OnboardingStep.COMPLETED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            is_completed=True,
            step_data={"skipped": True}
        )
        
        self._onboarding_sessions[user_id] = onboarding
        
        user = auth_manager.get_user(user_id)
        name = user.name if user else "there"
        
        logger.info("User skipped onboarding", user_id=user_id)
        
        return {
            "status": "completed",
            "title": f"Welcome, {name}! 🎉",
            "message": (
                "No problem! You can customize your preferences anytime in settings.\n\n"
                "I'm ready to help you tackle whatever you're working on!"
            ),
            "next_action": {
                "type": "start_chat",
                "initial_message": "I'm ready to get started!",
                "task_focus": None
            }
        }


# Global onboarding manager instance
onboarding_manager = OnboardingManager()