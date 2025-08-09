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
    """Enhanced onboarding step identifiers for comprehensive ADHD support setup."""
    WELCOME = "welcome"
    PRIVACY_AGREEMENT = "privacy_agreement" 
    ADHD_ASSESSMENT = "adhd_assessment"
    ENERGY_PATTERNS = "energy_patterns"
    CRISIS_SUPPORT = "crisis_support"
    NUDGE_PREFERENCES = "nudge_preferences"
    GOOGLE_CALENDAR = "google_calendar"
    TELEGRAM_SETUP = "telegram_setup"
    API_INTRODUCTION = "api_introduction"
    FIRST_SUCCESS = "first_success"
    CELEBRATION = "celebration"
    COMPLETED = "completed"


class OnboardingData(BaseModel):
    """User onboarding progress data."""
    user_id: str
    current_step: OnboardingStep
    started_at: datetime
    completed_at: Optional[datetime] = None
    step_data: Dict[str, Any] = {}
    is_completed: bool = False


class ADHDAssessmentData(BaseModel):
    """Comprehensive ADHD assessment data for personalization."""
    # Executive function challenges (rated 1-5)
    executive_challenges: Dict[str, int] = {
        "working_memory": 3,
        "cognitive_flexibility": 3, 
        "inhibitory_control": 3,
        "planning_organization": 3,
        "task_initiation": 3,
        "sustained_attention": 3,
        "time_management": 3,
        "emotional_regulation": 3
    }
    
    # ADHD strengths and superpowers
    strengths: List[str] = []  # ["creativity", "hyperfocus", "innovation", "empathy"]
    hyperfocus_areas: List[str] = []  # subjects/activities that trigger hyperfocus
    
    # Daily patterns
    energy_patterns: Dict[str, int] = {}  # hour -> energy level (1-5)
    focus_patterns: Dict[str, int] = {}   # hour -> focus capacity (1-5) 
    best_work_times: List[str] = []       # ["morning", "afternoon", "evening"]
    
    # Sensory processing preferences
    sensory_preferences: Dict[str, str] = {
        "noise_level": "moderate",     # "quiet", "moderate", "background_music"
        "lighting": "bright",         # "dim", "moderate", "bright"
        "workspace": "organized",     # "minimal", "organized", "stimulating"
        "interruptions": "minimal"    # "none", "minimal", "frequent_ok"
    }
    
    # Coping strategies and accommodations
    current_coping_strategies: List[str] = []
    past_successful_accommodations: List[str] = []
    
    # Goals and motivation
    primary_goals: List[str] = []         # ["productivity", "focus", "organization"]
    motivation_style: str = "mixed"       # "intrinsic", "extrinsic", "mixed"
    reward_preferences: List[str] = []    # ["achievement", "recognition", "breaks"]


class EnergyPatternsData(BaseModel):
    """Detailed energy and focus pattern configuration."""
    # Daily energy mapping (0-24 hours)
    hourly_energy: Dict[int, int] = {}    # hour -> energy level (1-5)
    hourly_focus: Dict[int, int] = {}     # hour -> focus capacity (1-5)
    
    # Weekly patterns
    weekly_patterns: Dict[str, Dict[str, int]] = {}
    
    # Hyperfocus patterns
    hyperfocus_triggers: List[str] = []
    hyperfocus_duration_avg: str = "2-4 hours"
    hyperfocus_warning_signs: List[str] = []
    post_hyperfocus_recovery: List[str] = []
    
    # Overwhelm and burnout prevention
    overwhelm_early_signs: List[str] = []
    burnout_prevention_strategies: List[str] = []
    
    # Break and recovery preferences
    preferred_break_activities: List[str] = []
    break_frequency: str = "every_hour"   # "30min", "every_hour", "as_needed"
    recovery_time_needed: str = "15min"   # time needed to recover focus


class CrisisSupportData(BaseModel):
    """Crisis support and safety configuration."""
    # Emergency contacts
    emergency_contacts: List[Dict[str, str]] = []
    
    # Professional support
    has_therapist: bool = False
    therapist_contact: Optional[str] = None
    has_psychiatrist: bool = False
    psychiatrist_contact: Optional[str] = None
    
    # Crisis resources
    preferred_crisis_hotlines: List[Dict[str, str]] = []
    local_crisis_resources: List[Dict[str, str]] = []
    
    # Warning signs and triggers
    personal_warning_signs: List[str] = []
    crisis_triggers: List[str] = []
    
    # Safety planning
    safety_plan_exists: bool = False
    safety_plan_location: Optional[str] = None
    
    # Medication information (if comfortable sharing)
    takes_medication: Optional[bool] = None
    medication_reminders_needed: bool = False
    
    # Consent for crisis intervention
    consent_crisis_detection: bool = True
    consent_emergency_contacts: bool = False


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


class OnboardingProgress(BaseModel):
    """Detailed progress tracking for onboarding steps."""
    step: OnboardingStep
    started_at: datetime
    completed_at: Optional[datetime] = None
    data_collected: Dict[str, Any] = {}
    is_completed: bool = False
    is_skipped: bool = False
    retry_count: int = 0
    

class OnboardingAnalytics(BaseModel):
    """Analytics data for onboarding optimization."""
    total_time_minutes: Optional[float] = None
    steps_completed: int = 0
    steps_skipped: int = 0
    abandon_points: List[OnboardingStep] = []
    feature_adoption: Dict[str, bool] = {}
    satisfaction_rating: Optional[int] = None  # 1-5
    feedback_text: Optional[str] = None


class EnhancedOnboardingManager:
    """Enhanced onboarding manager with comprehensive ADHD support setup."""
    
    def __init__(self):
        self._onboarding_sessions: Dict[str, OnboardingData] = {}
        self._progress_tracking: Dict[str, Dict[OnboardingStep, OnboardingProgress]] = {}
        self._analytics: Dict[str, OnboardingAnalytics] = {}
        
        # Enhanced step handlers
        self._step_handlers = {
            OnboardingStep.WELCOME: self._handle_welcome_step,
            OnboardingStep.PRIVACY_AGREEMENT: self._handle_privacy_agreement_step,
            OnboardingStep.ADHD_ASSESSMENT: self._handle_adhd_assessment_step,
            OnboardingStep.ENERGY_PATTERNS: self._handle_energy_patterns_step,
            OnboardingStep.CRISIS_SUPPORT: self._handle_crisis_support_step,
            OnboardingStep.NUDGE_PREFERENCES: self._handle_nudge_preferences_step,
            OnboardingStep.GOOGLE_CALENDAR: self._handle_google_calendar_step,
            OnboardingStep.TELEGRAM_SETUP: self._handle_telegram_setup_step,
            OnboardingStep.API_INTRODUCTION: self._handle_api_introduction_step,
            OnboardingStep.FIRST_SUCCESS: self._handle_first_success_step,
            OnboardingStep.CELEBRATION: self._handle_celebration_step,
        }
    
    async def start_onboarding(self, user_id: str, skip_to_step: Optional[OnboardingStep] = None) -> OnboardingData:
        """Start enhanced onboarding process for a new user."""
        if user_id in self._onboarding_sessions:
            # Resume existing session
            existing = self._onboarding_sessions[user_id]
            if not existing.is_completed:
                logger.info("Resumed existing onboarding session", 
                           user_id=user_id, current_step=existing.current_step)
                return existing
        
        start_step = skip_to_step or OnboardingStep.WELCOME
        
        onboarding = OnboardingData(
            user_id=user_id,
            current_step=start_step,
            started_at=datetime.utcnow()
        )
        
        self._onboarding_sessions[user_id] = onboarding
        self._progress_tracking[user_id] = {}
        self._analytics[user_id] = OnboardingAnalytics()
        
        # Initialize progress tracking
        await self._track_step_start(user_id, start_step)
        
        logger.info("Started enhanced onboarding session", 
                   user_id=user_id, start_step=start_step)
        return onboarding
    
    async def _track_step_start(self, user_id: str, step: OnboardingStep) -> None:
        """Track the start of an onboarding step."""
        if user_id not in self._progress_tracking:
            self._progress_tracking[user_id] = {}
        
        self._progress_tracking[user_id][step] = OnboardingProgress(
            step=step,
            started_at=datetime.utcnow()
        )
    
    async def _track_step_completion(self, user_id: str, step: OnboardingStep, 
                                   data: Dict[str, Any], skipped: bool = False) -> None:
        """Track the completion of an onboarding step."""
        if user_id in self._progress_tracking and step in self._progress_tracking[user_id]:
            progress = self._progress_tracking[user_id][step]
            progress.completed_at = datetime.utcnow()
            progress.is_completed = True
            progress.is_skipped = skipped
            progress.data_collected = data
            
            # Update analytics
            analytics = self._analytics.get(user_id, OnboardingAnalytics())
            if skipped:
                analytics.steps_skipped += 1
            else:
                analytics.steps_completed += 1
            self._analytics[user_id] = analytics
    
    async def get_onboarding_progress(self, user_id: str) -> Dict[str, Any]:
        """Get detailed progress information for a user's onboarding."""
        onboarding = self._onboarding_sessions.get(user_id)
        if not onboarding:
            return {"status": "not_started"}
        
        progress_data = self._progress_tracking.get(user_id, {})
        analytics = self._analytics.get(user_id, OnboardingAnalytics())
        
        completed_steps = [step.value for step, progress in progress_data.items() 
                          if progress.is_completed]
        
        total_steps = len(OnboardingStep)
        progress_percentage = (len(completed_steps) / total_steps) * 100
        
        return {
            "status": "completed" if onboarding.is_completed else "in_progress",
            "current_step": onboarding.current_step.value,
            "progress_percentage": progress_percentage,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "can_resume": not onboarding.is_completed,
            "started_at": onboarding.started_at.isoformat(),
            "estimated_remaining_minutes": max(0, (total_steps - len(completed_steps)) * 2),
            "analytics": {
                "steps_completed": analytics.steps_completed,
                "steps_skipped": analytics.steps_skipped,
                "total_time_minutes": analytics.total_time_minutes
            }
        }
    
    async def get_onboarding_status(self, user_id: str) -> Optional[OnboardingData]:
        """Get current onboarding status for user."""
        return self._onboarding_sessions.get(user_id)
    
    async def process_step(self, user_id: str, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process user input for current onboarding step with enhanced tracking."""
        onboarding = self._onboarding_sessions.get(user_id)
        if not onboarding:
            raise ValueError("No onboarding session found for user")
        
        if onboarding.is_completed:
            return {"status": "completed", "message": "Onboarding already completed! 🎉"}
        
        current_step = onboarding.current_step
        
        # Get handler for current step
        handler = self._step_handlers.get(current_step)
        if not handler:
            raise ValueError(f"No handler for step: {current_step}")
        
        # Check for skip request
        is_skipped = step_input.get("skip", False)
        
        try:
            # Process the step
            result = await handler(onboarding, step_input)
            
            # Track step completion
            await self._track_step_completion(user_id, current_step, step_input, is_skipped)
            
            # If step advances, track new step start
            if result.get("status") == "next_step" and "next_step" in result:
                next_step_enum = OnboardingStep(result["next_step"])
                await self._track_step_start(user_id, next_step_enum)
            
            # Update onboarding data
            self._onboarding_sessions[user_id] = onboarding
            
            # Add progress information to response
            progress_info = await self.get_onboarding_progress(user_id)
            result["progress"] = {
                "current_step": result.get("next_step", current_step.value),
                "percentage": progress_info["progress_percentage"],
                "completed_steps": progress_info["completed_steps"],
                "estimated_remaining_minutes": progress_info["estimated_remaining_minutes"]
            }
            
            logger.info("Processed enhanced onboarding step", 
                       user_id=user_id, 
                       step=current_step.value,
                       next_step=result.get("next_step"),
                       skipped=is_skipped)
            
            return result
            
        except Exception as e:
            # Track retry
            if user_id in self._progress_tracking and current_step in self._progress_tracking[user_id]:
                self._progress_tracking[user_id][current_step].retry_count += 1
            
            logger.error("Error processing onboarding step", 
                        user_id=user_id, step=current_step.value, error=str(e))
            raise
    
    async def skip_to_step(self, user_id: str, target_step: OnboardingStep) -> Dict[str, Any]:
        """Skip to a specific onboarding step."""
        onboarding = self._onboarding_sessions.get(user_id)
        if not onboarding:
            raise ValueError("No onboarding session found for user")
        
        # Mark current step as skipped
        if onboarding.current_step != target_step:
            await self._track_step_completion(
                user_id, onboarding.current_step, {}, skipped=True
            )
        
        # Update current step
        onboarding.current_step = target_step
        await self._track_step_start(user_id, target_step)
        
        logger.info("Skipped to onboarding step", 
                   user_id=user_id, target_step=target_step.value)
        
        # Get step content
        return await self._get_step_content(onboarding, target_step)
    
    async def _get_step_content(self, onboarding: OnboardingData, step: OnboardingStep) -> Dict[str, Any]:
        """Get content for a specific step without processing input."""
        handler = self._step_handlers.get(step)
        if handler:
            return await handler(onboarding, {})
        return {"status": "error", "message": f"No handler for step: {step}"}
    
    async def _handle_welcome_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced welcome step with clear value proposition and progress indicator."""
        if step_input.get("ready") or step_input.get("action") == "start":
            onboarding.current_step = OnboardingStep.PRIVACY_AGREEMENT
            
            return {
                "status": "next_step",
                "next_step": "privacy_agreement",
                "step_number": 2,
                "total_steps": 11,
                "title": "Privacy & Data Protection 🔒",
                "message": (
                    "Your privacy is our top priority. Let's quickly review how we protect your data "
                    "and what information helps us provide better ADHD support."
                ),
                "estimated_time": "10-12 minutes total",
                "can_skip": True,
                "skip_message": "You can skip steps anytime - we'll use sensible defaults"
            }
        
        return {
            "status": "current_step",
            "step": "welcome",
            "step_number": 1,
            "total_steps": 11,
            "title": "Welcome to Your ADHD Support System! 🧠✨",
            "message": (
                "I'm designed specifically for ADHD minds - understanding hyperfocus, "
                "executive function challenges, and the unique strengths you bring.\n\n"
                "**What makes this different:**\n"
                "• **Sub-3 second responses** - because waiting kills momentum\n"
                "• **Crisis-aware support** - safety first, always\n"
                "• **Privacy by design** - your data stays protected\n"
                "• **Celebrates your wins** - every success matters\n\n"
                "This setup takes 10-12 minutes and delivers immediate value. Ready?"
            ),
            "features_preview": [
                "🎯 Smart task breakdown that works with ADHD",
                "📅 Calendar integration for context-aware support", 
                "💬 Telegram nudges when you need gentle redirects",
                "🛡️ Built-in crisis detection and support resources",
                "📊 Energy pattern learning for optimal scheduling"
            ],
            "action": {
                "type": "button",
                "text": "Start Setup (10-12 min) 🚀",
                "value": {"ready": True}
            },
            "secondary_action": {
                "type": "link",
                "text": "Quick demo first?",
                "action": "show_demo"
            },
            "estimated_time": "10-12 minutes",
            "can_skip": False  # Welcome step should be experienced
        }
    
    async def _handle_privacy_agreement_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle privacy agreement and data collection consent."""
        if step_input.get("agree") or step_input.get("action") == "agree":
            privacy_data = {
                "privacy_agreed": True,
                "data_collection_consent": step_input.get("data_collection_consent", True),
                "analytics_consent": step_input.get("analytics_consent", True),
                "crisis_detection_consent": step_input.get("crisis_detection_consent", True)
            }
            
            onboarding.step_data["privacy"] = privacy_data
            onboarding.current_step = OnboardingStep.ADHD_ASSESSMENT
            
            return {
                "status": "next_step",
                "next_step": "adhd_assessment",
                "step_number": 3,
                "total_steps": 11,
                "title": "Your ADHD Profile 🧠",
                "message": (
                    "Great! Now let's learn about your unique ADHD patterns. This helps me provide "
                    "personalized support that works with your brain, not against it.\n\n"
                    "**This is completely optional** - skip any questions you're not comfortable with."
                ),
                "estimated_time": "2-3 minutes"
            }
        
        return {
            "status": "current_step",
            "step": "privacy_agreement",
            "step_number": 2,
            "total_steps": 11,
            "title": "Privacy & Data Protection 🔒",
            "message": (
                "Your data privacy is non-negotiable. Here's exactly what we collect and why:"
            ),
            "privacy_details": [
                {
                    "category": "Essential Data",
                    "what": "Account info, preferences, chat history",
                    "why": "Core functionality and personalization",
                    "required": True
                },
                {
                    "category": "ADHD Patterns",
                    "what": "Focus times, energy levels, coping strategies",
                    "why": "Personalized nudges and support",
                    "required": False
                },
                {
                    "category": "Crisis Detection",
                    "what": "Messages analyzed for safety keywords",
                    "why": "Immediate crisis support resources",
                    "required": False
                },
                {
                    "category": "Usage Analytics",
                    "what": "Feature usage, response times (anonymized)",
                    "why": "System improvements",
                    "required": False
                }
            ],
            "privacy_rights": [
                "✓ Export your data anytime",
                "✓ Delete your account and all data",
                "✓ Opt out of any data collection",
                "✓ Local processing for sensitive data",
                "✓ No data sold to third parties, ever"
            ],
            "consent_options": [
                {
                    "id": "data_collection_consent",
                    "label": "Basic data collection for personalization",
                    "description": "Allows customized ADHD support",
                    "default": True
                },
                {
                    "id": "analytics_consent", 
                    "label": "Anonymous usage analytics",
                    "description": "Helps improve the system for everyone",
                    "default": True
                },
                {
                    "id": "crisis_detection_consent",
                    "label": "Crisis detection and safety monitoring",
                    "description": "Provides immediate help resources when needed",
                    "default": True
                }
            ],
            "action": {
                "type": "button",
                "text": "I understand and agree 👍",
                "value": {"agree": True}
            },
            "secondary_action": {
                "type": "link",
                "text": "Read full privacy policy",
                "url": "/privacy-policy"
            },
            "can_skip": False  # Privacy agreement is required
        }
    
    async def _handle_adhd_assessment_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle comprehensive ADHD assessment."""
        if step_input.get("skip"):
            onboarding.current_step = OnboardingStep.ENERGY_PATTERNS
            return await self._handle_energy_patterns_step(onboarding, {})
        
        if step_input.get("executive_challenges") or step_input.get("action") == "submit":
            assessment_data = ADHDAssessmentData(
                executive_challenges=step_input.get("executive_challenges", {}),
                strengths=step_input.get("strengths", []),
                hyperfocus_areas=step_input.get("hyperfocus_areas", []),
                sensory_preferences=step_input.get("sensory_preferences", {}),
                current_coping_strategies=step_input.get("coping_strategies", []),
                primary_goals=step_input.get("primary_goals", []),
                motivation_style=step_input.get("motivation_style", "mixed"),
                reward_preferences=step_input.get("reward_preferences", [])
            )
            
            onboarding.step_data["adhd_assessment"] = assessment_data.dict()
            onboarding.current_step = OnboardingStep.ENERGY_PATTERNS
            
            # Generate personalized insights
            insights = self._generate_adhd_insights(assessment_data)
            
            return {
                "status": "next_step",
                "next_step": "energy_patterns", 
                "step_number": 4,
                "total_steps": 11,
                "title": "Energy & Focus Patterns ⚡",
                "message": (
                    f"Excellent insights! I can see you excel in {', '.join(assessment_data.strengths[:2])} "
                    f"and would benefit from support with executive functions.\n\n"
                    f"Next, let's map your energy patterns so I can suggest optimal work times."
                ),
                "personal_insights": insights,
                "estimated_time": "2 minutes"
            }
        
        return {
            "status": "current_step",
            "step": "adhd_assessment",
            "step_number": 3,
            "total_steps": 11,
            "title": "Your ADHD Profile 🧠",
            "message": (
                "Let's understand your unique ADHD patterns. Rate these executive function areas "
                "from 1 (no challenges) to 5 (significant challenges). This helps me provide "
                "targeted support.\n\n"
                "**Remember:** There are no wrong answers - ADHD affects everyone differently!"
            ),
            "assessment_sections": [
                {
                    "title": "Executive Function Challenges",
                    "type": "rating_scale",
                    "scale": {"min": 1, "max": 5, "labels": {"1": "No challenge", "3": "Sometimes", "5": "Daily struggle"}},
                    "items": [
                        {"id": "working_memory", "label": "Holding information in mind while working"},
                        {"id": "cognitive_flexibility", "label": "Switching between tasks or adapting to changes"},
                        {"id": "inhibitory_control", "label": "Resisting distractions and impulses"},
                        {"id": "planning_organization", "label": "Planning ahead and organizing tasks"},
                        {"id": "task_initiation", "label": "Getting started on tasks"},
                        {"id": "sustained_attention", "label": "Maintaining focus on tasks"},
                        {"id": "time_management", "label": "Estimating and managing time"},
                        {"id": "emotional_regulation", "label": "Managing emotions and frustration"}
                    ]
                },
                {
                    "title": "ADHD Strengths & Superpowers",
                    "type": "multi_select",
                    "options": [
                        "Creative and innovative thinking",
                        "Hyperfocus abilities",
                        "High energy and enthusiasm",
                        "Quick problem-solving",
                        "Entrepreneurial mindset",
                        "Empathy and emotional intelligence",
                        "Big picture thinking",
                        "Resilience and adaptability",
                        "Spontaneity and flexibility",
                        "Intense curiosity and passion"
                    ]
                },
                {
                    "title": "Hyperfocus Areas",
                    "type": "multi_select",
                    "description": "What topics or activities can capture your complete attention?",
                    "options": [
                        "Technology/Programming",
                        "Creative arts", 
                        "Research/Learning",
                        "Games/Puzzles",
                        "Social causes",
                        "Sports/Fitness",
                        "Music",
                        "Reading",
                        "Organizing/Cleaning",
                        "Work projects"
                    ]
                }
            ],
            "action": {
                "type": "button",
                "text": "Continue with Assessment 📊",
                "value": {"action": "submit"}
            },
            "can_skip": True,
            "skip_message": "Skip to use general ADHD support patterns",
            "estimated_time": "2-3 minutes"
        }
    
    def _generate_adhd_insights(self, assessment: ADHDAssessmentData) -> List[str]:
        """Generate personalized insights from ADHD assessment."""
        insights = []
        
        # Executive function insights
        high_challenge_areas = [k for k, v in assessment.executive_challenges.items() if v >= 4]
        if high_challenge_areas:
            insights.append(f"Your primary support areas: {', '.join(high_challenge_areas).replace('_', ' ')}")
        
        # Strength-based insights
        if assessment.strengths:
            insights.append(f"Your ADHD superpowers: {', '.join(assessment.strengths[:3])}")
        
        # Hyperfocus insights
        if assessment.hyperfocus_areas:
            insights.append(f"Hyperfocus triggers: {', '.join(assessment.hyperfocus_areas[:2])} - we'll leverage these!")
        
        return insights
    
    async def _handle_energy_patterns_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle energy and focus pattern mapping."""
        if step_input.get("skip"):
            onboarding.current_step = OnboardingStep.CRISIS_SUPPORT
            return await self._handle_crisis_support_step(onboarding, {})
        
        if step_input.get("energy_mapping") or step_input.get("action") == "submit":
            patterns_data = EnergyPatternsData(
                hourly_energy=step_input.get("hourly_energy", {}),
                hourly_focus=step_input.get("hourly_focus", {}),
                hyperfocus_triggers=step_input.get("hyperfocus_triggers", []),
                hyperfocus_duration_avg=step_input.get("hyperfocus_duration", "2-4 hours"),
                overwhelm_early_signs=step_input.get("overwhelm_signs", []),
                preferred_break_activities=step_input.get("break_activities", []),
                break_frequency=step_input.get("break_frequency", "every_hour")
            )
            
            onboarding.step_data["energy_patterns"] = patterns_data.dict()
            onboarding.current_step = OnboardingStep.CRISIS_SUPPORT
            
            return {
                "status": "next_step",
                "next_step": "crisis_support",
                "step_number": 5,
                "total_steps": 11,
                "title": "Crisis Support & Safety 🛡️",
                "message": (
                    "Perfect! I'll use your energy patterns to suggest optimal work times and "
                    "detect when you might need breaks.\n\n"
                    "Now for something important: setting up your safety net. This ensures you "
                    "always have support when you need it most."
                ),
                "estimated_time": "1-2 minutes"
            }
        
        return {
            "status": "current_step",
            "step": "energy_patterns",
            "step_number": 4, 
            "total_steps": 11,
            "title": "Energy & Focus Patterns ⚡",
            "message": (
                "ADHD brains have unique energy rhythms. Let's map yours so I can suggest "
                "optimal times for different types of work and detect when you need breaks.\n\n"
                "**Tip:** Think about your typical day - when do you feel most alert vs. when do you crash?"
            ),
            "pattern_mapping": {
                "energy_scale": {
                    "title": "Energy Levels Throughout the Day",
                    "description": "Rate your typical energy from 1 (exhausted) to 5 (energized)",
                    "hours": list(range(6, 24)),  # 6 AM to 11 PM
                    "type": "hourly_slider"
                },
                "focus_scale": {
                    "title": "Focus Capacity Throughout the Day", 
                    "description": "Rate your ability to focus from 1 (scattered) to 5 (laser focused)",
                    "hours": list(range(6, 24)),
                    "type": "hourly_slider"
                }
            },
            "quick_patterns": {
                "title": "Or choose a common ADHD pattern:",
                "options": [
                    {
                        "id": "morning_lark",
                        "title": "Morning Lark 🌅",
                        "description": "High energy 6-10 AM, crash after lunch"
                    },
                    {
                        "id": "night_owl", 
                        "title": "Night Owl 🦉",
                        "description": "Low mornings, peak energy 2-6 PM and 8-11 PM"
                    },
                    {
                        "id": "roller_coaster",
                        "title": "Roller Coaster 🎢",
                        "description": "Multiple peaks and valleys throughout day"
                    },
                    {
                        "id": "variable",
                        "title": "Highly Variable 🔄",
                        "description": "Changes daily based on sleep, stress, etc."
                    }
                ]
            },
            "additional_questions": [
                {
                    "id": "hyperfocus_triggers",
                    "type": "multi_select",
                    "question": "What typically triggers your hyperfocus?",
                    "options": [
                        "Interesting new projects",
                        "Deadline pressure",
                        "Problem-solving challenges",
                        "Creative tasks",
                        "Research and learning",
                        "Organizing and cleaning",
                        "Social interactions",
                        "Physical activity"
                    ]
                },
                {
                    "id": "break_activities",
                    "type": "multi_select", 
                    "question": "What helps you recharge during breaks?",
                    "options": [
                        "Short walk or movement",
                        "Deep breathing/meditation",
                        "Snack or hydration",
                        "Quick chat with someone",
                        "Listening to music",
                        "Stretching or yoga",
                        "Quick game or puzzle",
                        "Step outside for fresh air"
                    ]
                }
            ],
            "action": {
                "type": "button",
                "text": "Save Energy Patterns ⚡",
                "value": {"action": "submit"}
            },
            "can_skip": True,
            "skip_message": "Skip to use adaptive pattern detection",
            "estimated_time": "2-3 minutes"
        }
    
    async def _handle_crisis_support_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle crisis support and safety net configuration."""
        if step_input.get("skip"):
            onboarding.current_step = OnboardingStep.NUDGE_PREFERENCES
            return await self._handle_nudge_preferences_step(onboarding, {})
        
        if step_input.get("crisis_config") or step_input.get("action") == "submit":
            crisis_data = CrisisSupportData(
                emergency_contacts=step_input.get("emergency_contacts", []),
                has_therapist=step_input.get("has_therapist", False),
                therapist_contact=step_input.get("therapist_contact"),
                preferred_crisis_hotlines=step_input.get("crisis_hotlines", []),
                personal_warning_signs=step_input.get("warning_signs", []),
                consent_crisis_detection=step_input.get("consent_crisis_detection", True),
                consent_emergency_contacts=step_input.get("consent_emergency_contacts", False)
            )
            
            onboarding.step_data["crisis_support"] = crisis_data.dict()
            onboarding.current_step = OnboardingStep.NUDGE_PREFERENCES
            
            return {
                "status": "next_step",
                "next_step": "nudge_preferences",
                "step_number": 6,
                "total_steps": 11,
                "title": "Nudge & Communication Preferences 📳",
                "message": (
                    "Your safety net is configured! I'll always prioritize your wellbeing.\n\n"
                    "Now let's set up how you'd like me to communicate with you - gentle nudges, "
                    "reminders, and check-ins that work with your ADHD patterns."
                ),
                "estimated_time": "2 minutes"
            }
        
        return {
            "status": "current_step",
            "step": "crisis_support",
            "step_number": 5,
            "total_steps": 11,
            "title": "Crisis Support & Safety 🛡️",
            "message": (
                "Your safety and wellbeing are my top priority. Let's set up your support network "
                "so you always have help when you need it.\n\n"
                "**I have built-in crisis detection** that provides immediate resources for mental health emergencies. "
                "This step helps me provide even better support."
            ),
            "crisis_features": [
                "🔍 **Automatic Crisis Detection** - I recognize distress patterns in messages",
                "📞 **Immediate Resources** - Crisis hotlines and local support numbers", 
                "🛡️ **Safety Planning** - Personalized coping strategies and contacts",
                "⚡ **Instant Response** - Never wait when you need help most"
            ],
            "configuration_sections": [
                {
                    "title": "Professional Support",
                    "type": "optional_contacts",
                    "fields": [
                        {
                            "id": "has_therapist",
                            "type": "checkbox",
                            "label": "I have a therapist or counselor"
                        },
                        {
                            "id": "therapist_contact",
                            "type": "text",
                            "label": "Therapist contact (optional)",
                            "depends_on": "has_therapist"
                        }
                    ]
                },
                {
                    "title": "Emergency Contacts",
                    "type": "contact_list",
                    "description": "People who can help in a crisis (optional but recommended)",
                    "max_contacts": 3
                },
                {
                    "title": "Personal Warning Signs", 
                    "type": "multi_select",
                    "description": "Help me recognize when you might need extra support",
                    "options": [
                        "Feeling overwhelmed or out of control",
                        "Extreme fatigue or burnout",
                        "Social isolation or withdrawal",
                        "Difficulty with basic self-care",
                        "Increased emotional intensity",
                        "Sleep disruption patterns",
                        "Appetite or eating changes",
                        "Substance use changes"
                    ]
                },
                {
                    "title": "Consent Options",
                    "type": "consent_checkboxes",
                    "options": [
                        {
                            "id": "consent_crisis_detection",
                            "label": "Enable crisis detection in my messages",
                            "description": "I'll analyze your messages for distress patterns and offer immediate support",
                            "default": True,
                            "required": False
                        },
                        {
                            "id": "consent_emergency_contacts",
                            "label": "Contact my emergency contacts in severe crisis",
                            "description": "Only in extreme situations with clear risk indicators",
                            "default": False,
                            "required": False
                        }
                    ]
                }
            ],
            "default_resources": [
                {
                    "name": "National Suicide Prevention Lifeline",
                    "number": "988", 
                    "available": "24/7"
                },
                {
                    "name": "Crisis Text Line",
                    "number": "Text HOME to 741741",
                    "available": "24/7"
                },
                {
                    "name": "SAMHSA National Helpline",
                    "number": "1-800-662-4357",
                    "available": "24/7"
                }
            ],
            "action": {
                "type": "button",
                "text": "Configure Safety Net 🛡️",
                "value": {"action": "submit"}
            },
            "can_skip": True,
            "skip_message": "Skip - use default crisis detection only",
            "estimated_time": "2-3 minutes",
            "privacy_note": "All crisis information is encrypted and only used for your safety."
        }
    
    async def _handle_nudge_preferences_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle comprehensive nudge and communication preferences."""
        if step_input.get("skip"):
            onboarding.current_step = OnboardingStep.GOOGLE_CALENDAR
            return await self._handle_google_calendar_step(onboarding, {})
        
        if step_input.get("nudge_config") or step_input.get("action") == "submit":
            nudge_prefs = NudgePreferences(
                preferred_methods=step_input.get("nudge_methods", ["web"]),
                frequency=step_input.get("nudge_frequency", "normal"),
                nudge_style=NudgeTier(int(step_input.get("nudge_style", 0))),
                timing_preferences=step_input.get("timing_preferences", {}),
                work_hours_start=step_input.get("work_hours_start", "09:00"),
                work_hours_end=step_input.get("work_hours_end", "17:00"),
                break_reminders=step_input.get("break_reminders", True),
                focus_session_alerts=step_input.get("focus_session_alerts", True),
                celebration_messages=step_input.get("celebration_messages", True)
            )
            
            onboarding.step_data["nudge_preferences"] = nudge_prefs.dict()
            onboarding.current_step = OnboardingStep.GOOGLE_CALENDAR
            
            return {
                "status": "next_step",
                "next_step": "google_calendar",
                "step_number": 7,
                "total_steps": 11, 
                "title": "Google Calendar Integration 📅",
                "message": (
                    "Perfect! I'll nudge you in ways that feel supportive, not overwhelming.\n\n"
                    "Want to connect your Google Calendar? This gives me context about your schedule "
                    "so I can provide better timing suggestions and avoid interrupting important meetings."
                ),
                "estimated_time": "1-2 minutes"
            }
        
        return {
            "status": "current_step", 
            "step": "nudge_preferences",
            "step_number": 6,
            "total_steps": 11,
            "title": "Nudge & Communication Preferences 📳",
            "message": (
                "How would you like me to communicate with you? I'll adapt my style to work "
                "with your ADHD patterns and preferences.\n\n"
                "**The goal:** Helpful nudges that feel supportive, never overwhelming."
            ),
            "preference_sections": [
                {
                    "title": "Communication Methods",
                    "type": "multi_select",
                    "id": "nudge_methods",
                    "description": "How should I reach you with reminders and check-ins?",
                    "options": [
                        {
                            "id": "web",
                            "label": "Web notifications (in browser)",
                            "description": "Non-intrusive browser notifications"
                        },
                        {
                            "id": "telegram", 
                            "label": "Telegram messages",
                            "description": "Chat with me on your phone (setup next)"
                        },
                        {
                            "id": "email",
                            "label": "Email reminders",
                            "description": "Daily summaries and important nudges"
                        }
                    ]
                },
                {
                    "title": "Nudge Style",
                    "type": "single_select",
                    "id": "nudge_style",
                    "description": "What communication style motivates you?",
                    "options": [
                        {
                            "id": "0",
                            "label": "Gentle & Encouraging 🌱",
                            "description": "Supportive, understanding, celebrates small wins"
                        },
                        {
                            "id": "1",
                            "label": "Playfully Sarcastic 🙄",
                            "description": "Light humor, gentle call-outs, keeps it real"
                        },
                        {
                            "id": "2", 
                            "label": "Direct & Assertive ⚡",
                            "description": "Clear expectations, firm accountability"
                        }
                    ]
                },
                {
                    "title": "Timing Preferences",
                    "type": "time_selector",
                    "fields": [
                        {
                            "id": "work_hours_start",
                            "label": "Work day starts",
                            "default": "09:00"
                        },
                        {
                            "id": "work_hours_end", 
                            "label": "Work day ends",
                            "default": "17:00"
                        }
                    ]
                },
                {
                    "title": "Nudge Types",
                    "type": "checkbox_group",
                    "options": [
                        {
                            "id": "break_reminders",
                            "label": "Break reminders",
                            "description": "Gentle nudges to take breaks and recharge",
                            "default": True
                        },
                        {
                            "id": "focus_session_alerts",
                            "label": "Focus session check-ins",
                            "description": "Check how focus sessions are going",
                            "default": True
                        },
                        {
                            "id": "celebration_messages",
                            "label": "Celebration messages",
                            "description": "Celebrate completed tasks and achievements",
                            "default": True
                        }
                    ]
                }
            ],
            "action": {
                "type": "button",
                "text": "Save Communication Preferences 📳",
                "value": {"action": "submit"}
            },
            "can_skip": True,
            "skip_message": "Skip to use gentle, web-based nudges",
            "estimated_time": "2 minutes"
        }
    
    async def _handle_google_calendar_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Google Calendar integration setup."""
        if step_input.get("skip"):
            onboarding.current_step = OnboardingStep.TELEGRAM_SETUP
            return await self._handle_telegram_setup_step(onboarding, {})
        
        if step_input.get("action") == "connect":
            # Generate OAuth URL for Google Calendar
            oauth_url = f"/api/calendar/auth?user_id={onboarding.user_id}&return_to=onboarding"
            
            return {
                "status": "external_auth",
                "oauth_url": oauth_url,
                "step": "google_calendar", 
                "title": "Connecting to Google Calendar...",
                "message": (
                    "I'll redirect you to Google to authorize calendar access. After authorization, "
                    "you'll return here to continue setup."
                ),
                "privacy_note": "I only read calendar events to understand your schedule - never modify anything."
            }
        
        if step_input.get("calendar_connected"):
            onboarding.step_data["google_calendar"] = {"connected": True, "connected_at": datetime.utcnow().isoformat()}
            onboarding.current_step = OnboardingStep.TELEGRAM_SETUP
            
            return {
                "status": "next_step",
                "next_step": "telegram_setup",
                "step_number": 8,
                "total_steps": 11,
                "title": "Telegram Bot Setup 💬",
                "message": (
                    "Excellent! Your calendar is connected. I'll now provide context-aware support "
                    "based on your schedule.\n\n"
                    "Want to set up Telegram for mobile nudges? This lets you chat with me "
                    "on your phone and receive gentle reminders throughout the day."
                ),
                "calendar_benefits": [
                    "📅 I'll avoid interrupting during meetings",
                    "⏰ Smart break suggestions between events", 
                    "🎯 Context-aware task recommendations",
                    "📊 Schedule optimization insights"
                ],
                "estimated_time": "1-2 minutes"
            }
        
        return {
            "status": "current_step",
            "step": "google_calendar",
            "step_number": 7,
            "total_steps": 11,
            "title": "Google Calendar Integration 📅",
            "message": (
                "Connecting your calendar helps me provide context-aware ADHD support. I'll know "
                "when you're in meetings, when you have free time, and can suggest optimal "
                "scheduling for your energy patterns.\n\n"
                "**Privacy First:** I only read your calendar events - I never create, modify, or delete anything."
            ),
            "calendar_benefits": [
                "📅 **Smart Scheduling** - Suggest optimal times for different types of work",
                "⏰ **Meeting Awareness** - Never interrupt during important calls",
                "🎯 **Context-Aware Nudges** - Different support based on what's coming up", 
                "📊 **Schedule Insights** - Identify patterns that help or hurt your productivity",
                "🔄 **Break Optimization** - Perfect break timing between meetings"
            ],
            "privacy_details": [
                "✓ Read-only access to calendar events",
                "✓ No event creation or modification",
                "✓ Data processed locally when possible",
                "✓ No calendar data shared with third parties",
                "✓ Disconnect anytime from settings"
            ],
            "action": {
                "type": "oauth_button",
                "text": "Connect Google Calendar 📅",
                "value": {"action": "connect"}
            },
            "can_skip": True,
            "skip_message": "Skip - add calendar integration later",
            "estimated_time": "1 minute"
        }
    
    async def _handle_telegram_setup_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Telegram bot setup and verification."""
        if step_input.get("skip"):
            onboarding.current_step = OnboardingStep.API_INTRODUCTION
            return await self._handle_api_introduction_step(onboarding, {})
        
        if step_input.get("telegram_connected"):
            onboarding.step_data["telegram"] = {
                "connected": True,
                "chat_id": step_input.get("chat_id"),
                "connected_at": datetime.utcnow().isoformat()
            }
            onboarding.current_step = OnboardingStep.API_INTRODUCTION
            
            return {
                "status": "next_step", 
                "next_step": "api_introduction",
                "step_number": 9,
                "total_steps": 11,
                "title": "API Access (Optional) 🔧",
                "message": (
                    "Great! Telegram is connected. You can now chat with me on your phone!\n\n"
                    "For developers and power users: Want API access to integrate with your "
                    "own tools and workflows?"
                ),
                "telegram_success": True,
                "estimated_time": "1 minute"
            }
        
        return {
            "status": "current_step",
            "step": "telegram_setup",
            "step_number": 8,
            "total_steps": 11, 
            "title": "Telegram Bot Setup 💬",
            "message": (
                "Get ADHD support directly on your phone! The Telegram bot lets you chat with me "
                "anywhere and receive gentle nudges throughout the day.\n\n"
                "**Perfect for ADHD** because it works with your existing phone habits."
            ),
            "telegram_benefits": [
                "📱 **Mobile Chat** - Full conversations on your phone",
                "🔔 **Smart Nudges** - Gentle reminders based on your patterns", 
                "⚡ **Instant Access** - Quick check-ins and support anywhere",
                "🤖 **Same AI** - Same personalized support, different interface",
                "🔒 **Private & Secure** - End-to-end encrypted conversations"
            ],
            "setup_instructions": [
                {
                    "step": 1,
                    "text": "Open Telegram and search for",
                    "highlight": "@ADHDoAssistantBot"
                },
                {
                    "step": 2, 
                    "text": "Send the command",
                    "highlight": "/start"
                },
                {
                    "step": 3,
                    "text": "Follow the authentication link to connect your account"
                },
                {
                    "step": 4,
                    "text": "Return here and click 'Verify Connection'"
                }
            ],
            "bot_username": "@ADHDoAssistantBot",
            "action": {
                "type": "verification_button",
                "text": "Verify Telegram Connection ✅",
                "value": {"action": "verify"}
            },
            "secondary_action": {
                "type": "link",
                "text": "Open Telegram Bot",
                "url": "https://t.me/ADHDoAssistantBot"
            },
            "can_skip": True,
            "skip_message": "Skip - set up Telegram later",
            "estimated_time": "1-2 minutes"
        }
    
    async def _handle_api_introduction_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API introduction for power users."""
        if step_input.get("skip"):
            onboarding.current_step = OnboardingStep.FIRST_SUCCESS
            return await self._handle_first_success_step(onboarding, {})
        
        if step_input.get("generate_api_key"):
            # Generate API key for the user
            from mcp_server.auth import auth_manager
            key_id, api_key = auth_manager.generate_api_key(onboarding.user_id, "Onboarding Setup Key")
            
            onboarding.step_data["api_access"] = {
                "api_key_generated": True,
                "key_id": key_id,
                "generated_at": datetime.utcnow().isoformat()
            }
            onboarding.current_step = OnboardingStep.FIRST_SUCCESS
            
            return {
                "status": "next_step",
                "next_step": "first_success",
                "step_number": 10,
                "total_steps": 11,
                "title": "Your First Success! 🎯",
                "message": (
                    "Your API key is ready! Keep it secure - you'll need it for API calls.\n\n"
                    "Now let's create your first success story. What's one thing you'd like "
                    "to accomplish right now?"
                ),
                "api_key": api_key,
                "api_key_warning": "Save this key securely - it won't be shown again!",
                "estimated_time": "1 minute"
            }
        
        return {
            "status": "current_step",
            "step": "api_introduction",
            "step_number": 9, 
            "total_steps": 11,
            "title": "API Access (Optional) 🔧",
            "message": (
                "For developers and power users: Want programmatic access to your ADHD support system? "
                "The API lets you integrate with your existing tools and workflows.\n\n"
                "**Great for:** Custom notifications, workflow integrations, data analysis"
            ),
            "api_capabilities": [
                "💬 **Chat API** - Send messages and get AI responses",
                "📊 **Analytics API** - Access your productivity patterns",
                "🎯 **Task Management** - Create and update tasks programmatically",
                "🔔 **Nudge Control** - Trigger custom nudges and reminders",
                "📅 **Calendar Integration** - Sync with external calendar systems"
            ],
            "example_use_cases": [
                "Integrate with task management apps",
                "Custom notification systems",
                "Productivity dashboard creation", 
                "Workflow automation",
                "Research and data analysis"
            ],
            "documentation_link": "/docs/api",
            "action": {
                "type": "button",
                "text": "Generate API Key 🔑",
                "value": {"generate_api_key": True}
            },
            "can_skip": True,
            "skip_message": "Skip - I just want to use the web interface",
            "estimated_time": "1 minute"
        }
    
    async def _handle_first_success_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle first success task setup."""
        first_task = step_input.get("task", "")
        
        if first_task:
            onboarding.step_data["first_task"] = first_task
            onboarding.current_step = OnboardingStep.CELEBRATION
            
            # Generate personalized insights based on setup
            insights = await self._generate_setup_insights(onboarding)
            
            return {
                "status": "next_step",
                "next_step": "celebration",
                "step_number": 11,
                "total_steps": 11,
                "title": "Setup Complete! 🎉",
                "message": (
                    f"Perfect! Let's tackle: **{first_task}**\n\n"
                    "Your ADHD support system is fully configured and ready to help you succeed!"
                ),
                "personal_insights": insights,
                "estimated_time": "Ready to go!"
            }
        
        return {
            "status": "current_step",
            "step": "first_success",
            "step_number": 10,
            "total_steps": 11,
            "title": "Your First Success! 🎯",
            "message": (
                "You're almost there! Let's start with immediate value. What's one thing "
                "you'd like to accomplish right now?\n\n"
                "**It can be anything** - big or small, work or personal. The goal is your first "
                "success story with your new ADHD support system!"
            ),
            "task_suggestions": [
                {
                    "category": "Quick Wins (5-15 min)",
                    "tasks": [
                        "Reply to an important email",
                        "Organize my desk/workspace", 
                        "Make that phone call I've been avoiding",
                        "Write tomorrow's top 3 priorities",
                        "Take a mindful 5-minute break"
                    ]
                },
                {
                    "category": "Bigger Goals (30-60 min)",
                    "tasks": [
                        "Start that project I've been putting off",
                        "Plan out my week",
                        "Research something I'm curious about",
                        "Tackle my email inbox", 
                        "Work on a creative project"
                    ]
                },
                {
                    "category": "Self-Care & Wellness",
                    "tasks": [
                        "Go for a refreshing walk",
                        "Practice some deep breathing",
                        "Prepare a healthy snack",
                        "Do some gentle stretching",
                        "Connect with a friend or family member"
                    ]
                }
            ],
            "input": {
                "type": "text",
                "placeholder": "e.g., Respond to Sarah's email, Plan my weekend, Clean my office...",
                "label": "What's one thing you'd like to tackle?"
            },
            "action": {
                "type": "button",
                "text": "Let's Do This! 🚀",
                "value": {"action": "submit"}
            },
            "cannot_skip": True,  # This step creates the first success experience
            "estimated_time": "1 minute to choose"
        }
    
    async def _handle_celebration_step(self, onboarding: OnboardingData, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle onboarding completion and celebration."""
        # Apply all collected preferences to user account
        await self._apply_onboarding_preferences(onboarding)
        
        # Mark onboarding as completed
        onboarding.current_step = OnboardingStep.COMPLETED
        onboarding.is_completed = True
        onboarding.completed_at = datetime.utcnow()
        
        # Calculate total onboarding time
        total_time = (onboarding.completed_at - onboarding.started_at).total_seconds() / 60
        self._analytics[onboarding.user_id].total_time_minutes = total_time
        
        # Generate personalized welcome message
        user = auth_manager.get_user(onboarding.user_id)
        name = user.name if user else "there"
        
        first_task = onboarding.step_data.get("first_task", "your goals")
        setup_summary = await self._generate_setup_summary(onboarding)
        
        logger.info("Enhanced onboarding completed", 
                   user_id=onboarding.user_id, 
                   total_time_minutes=total_time,
                   features_configured=len(onboarding.step_data))
        
        return {
            "status": "completed",
            "title": f"Welcome to Your ADHD Support System, {name}! 🎉",
            "message": (
                f"🎯 **You're all set!** Your personalized ADHD support system is ready.\n\n"
                f"**Your first focus:** {first_task}\n\n"
                "I'm here to help you succeed. Let's make today amazing!"
            ),
            "setup_summary": setup_summary,
            "onboarding_stats": {
                "total_time_minutes": round(total_time, 1),
                "features_configured": len(onboarding.step_data),
                "completed_at": onboarding.completed_at.isoformat()
            },
            "next_actions": [
                {
                    "type": "start_chat",
                    "text": "Start Your First Task 🚀",
                    "initial_message": f"I'm ready to work on: {first_task}",
                    "task_focus": first_task
                },
                {
                    "type": "view_dashboard",
                    "text": "Explore Your Dashboard 📊",
                    "url": "/dashboard"
                }
            ],
            "quick_tips": [
                "💬 **Chat naturally** - I understand context and remember our conversations",
                "🎯 **Update your focus** anytime by saying what you're working on",
                "⏸️ **Take breaks** - Tell me when you need to recharge",
                "🎉 **Celebrate wins** - I'll help you recognize every success!",
                "⚙️ **Adjust settings** anytime in your profile"
            ],
            "celebration": {
                "message": "You've just completed something many people with ADHD struggle with - following through on a multi-step process! That's already a win! 🏆",
                "achievement_unlocked": "Setup Master - Completed comprehensive ADHD support configuration"
            }
        }
    
    async def _generate_setup_insights(self, onboarding: OnboardingData) -> List[str]:
        """Generate personalized insights from onboarding setup."""
        insights = []
        
        # ADHD assessment insights
        if "adhd_assessment" in onboarding.step_data:
            assessment = onboarding.step_data["adhd_assessment"]
            if assessment.get("strengths"):
                insights.append(f"Your ADHD superpowers: {', '.join(assessment['strengths'][:2])}")
        
        # Energy pattern insights
        if "energy_patterns" in onboarding.step_data:
            insights.append("I'll use your energy patterns to suggest optimal work times")
        
        # Integration insights
        integrations = []
        if onboarding.step_data.get("google_calendar", {}).get("connected"):
            integrations.append("Calendar")
        if onboarding.step_data.get("telegram", {}).get("connected"):
            integrations.append("Telegram")
        if integrations:
            insights.append(f"Connected: {', '.join(integrations)} - context-aware support enabled!")
        
        # Safety net insight
        if "crisis_support" in onboarding.step_data:
            insights.append("Your safety net is configured - I'll always prioritize your wellbeing")
        
        return insights
    
    async def _generate_setup_summary(self, onboarding: OnboardingData) -> Dict[str, Any]:
        """Generate a summary of configured features."""
        summary = {
            "features_enabled": [],
            "personalization_level": "basic",
            "integrations": [],
            "support_areas": []
        }
        
        # Check configured features
        if "adhd_assessment" in onboarding.step_data:
            summary["features_enabled"].append("ADHD Profile")
            summary["personalization_level"] = "comprehensive"
        
        if "energy_patterns" in onboarding.step_data:
            summary["features_enabled"].append("Energy Pattern Optimization")
        
        if "crisis_support" in onboarding.step_data:
            summary["features_enabled"].append("Crisis Detection & Safety Net")
        
        if "nudge_preferences" in onboarding.step_data:
            summary["features_enabled"].append("Personalized Nudges")
        
        # Check integrations
        if onboarding.step_data.get("google_calendar", {}).get("connected"):
            summary["integrations"].append("Google Calendar")
        
        if onboarding.step_data.get("telegram", {}).get("connected"):
            summary["integrations"].append("Telegram Bot")
        
        if onboarding.step_data.get("api_access", {}).get("api_key_generated"):
            summary["integrations"].append("API Access")
        
        # Support areas
        if "adhd_assessment" in onboarding.step_data:
            assessment = onboarding.step_data["adhd_assessment"]
            high_challenges = [k for k, v in assessment.get("executive_challenges", {}).items() if v >= 4]
            summary["support_areas"] = [area.replace('_', ' ').title() for area in high_challenges]
        
        return summary
    
    async def _apply_onboarding_preferences(self, onboarding: OnboardingData) -> None:
        """Apply comprehensive onboarding preferences to user account."""
        user = auth_manager.get_user(onboarding.user_id)
        if not user:
            logger.error("User not found during onboarding completion", user_id=onboarding.user_id)
            return
        
        # Apply ADHD assessment data
        if "adhd_assessment" in onboarding.step_data:
            assessment_data = onboarding.step_data["adhd_assessment"]
            user.energy_patterns = {
                "executive_challenges": assessment_data.get("executive_challenges", {}),
                "strengths": assessment_data.get("strengths", []),
                "hyperfocus_areas": assessment_data.get("hyperfocus_areas", []),
                "sensory_preferences": assessment_data.get("sensory_preferences", {}),
                "primary_goals": assessment_data.get("primary_goals", [])
            }
        
        # Apply energy patterns
        if "energy_patterns" in onboarding.step_data:
            patterns = onboarding.step_data["energy_patterns"]
            if not hasattr(user, 'energy_patterns'):
                user.energy_patterns = {}
            user.energy_patterns.update({
                "hourly_energy": patterns.get("hourly_energy", {}),
                "hourly_focus": patterns.get("hourly_focus", {}),
                "hyperfocus_triggers": patterns.get("hyperfocus_triggers", []),
                "break_preferences": patterns.get("preferred_break_activities", []),
                "break_frequency": patterns.get("break_frequency", "every_hour")
            })
        
        # Apply crisis support configuration
        if "crisis_support" in onboarding.step_data:
            crisis_data = onboarding.step_data["crisis_support"]
            user.crisis_support = {
                "emergency_contacts": crisis_data.get("emergency_contacts", []),
                "has_therapist": crisis_data.get("has_therapist", False),
                "therapist_contact": crisis_data.get("therapist_contact"),
                "warning_signs": crisis_data.get("personal_warning_signs", []),
                "consent_crisis_detection": crisis_data.get("consent_crisis_detection", True),
                "consent_emergency_contacts": crisis_data.get("consent_emergency_contacts", False)
            }
        
        # Apply nudge preferences
        if "nudge_preferences" in onboarding.step_data:
            nudge_prefs = onboarding.step_data["nudge_preferences"]
            user.preferred_nudge_methods = nudge_prefs.get("preferred_methods", ["web"])
            user.nudge_timing_preferences = {
                "work_hours_start": nudge_prefs.get("work_hours_start", "09:00"),
                "work_hours_end": nudge_prefs.get("work_hours_end", "17:00"),
                "break_reminders": nudge_prefs.get("break_reminders", True),
                "focus_session_alerts": nudge_prefs.get("focus_session_alerts", True),
                "celebration_messages": nudge_prefs.get("celebration_messages", True)
            }
            
            # Set nudge style from enum
            if isinstance(nudge_prefs.get("nudge_style"), int):
                user.nudge_style = NudgeTier(nudge_prefs["nudge_style"])
        
        # Apply integration preferences
        integrations_configured = []
        
        if onboarding.step_data.get("google_calendar", {}).get("connected"):
            integrations_configured.append("google_calendar")
        
        if onboarding.step_data.get("telegram", {}).get("connected"):
            integrations_configured.append("telegram")
            user.telegram_chat_id = onboarding.step_data["telegram"].get("chat_id")
        
        if integrations_configured:
            user.integrations_enabled = integrations_configured
        
        logger.info("Applied comprehensive onboarding preferences", 
                   user_id=onboarding.user_id,
                   preferences_applied=list(onboarding.step_data.keys()),
                   integrations_configured=integrations_configured)
    
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


# Global enhanced onboarding manager instance
onboarding_manager = EnhancedOnboardingManager()