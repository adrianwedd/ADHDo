"""
Enhanced User Profiling System for ADHD Personalization.

This module implements comprehensive user profiling that adapts to individual
ADHD patterns, preferences, and needs while respecting user autonomy and
neurodiversity-affirming principles.

Core Features:
- Dynamic user profile adaptation based on behavior patterns
- Intelligent nudge timing based on individual energy patterns
- Personalized cognitive load thresholds and adjustments
- Adaptive interface complexity based on user capability
- Custom ADHD subtype recognition and support
- Privacy-first approach with user control

The system continuously learns and adapts while ensuring users maintain
complete control over their data and preferences.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict

import structlog
from pydantic import BaseModel, Field

from mcp_server.models import TraceMemory as TraceMemoryModel
from mcp_server.db_models import User
from traces.memory import trace_memory
from adhd.pattern_engine import ADHDSubtype, PatternType, get_pattern_engine

logger = structlog.get_logger()


class EnergyPattern(Enum):
    """Energy pattern classifications for ADHD users."""
    MORNING_PEAK = "morning_peak"
    AFTERNOON_PEAK = "afternoon_peak"
    EVENING_PEAK = "evening_peak"
    CONSISTENT = "consistent"
    UNPREDICTABLE = "unpredictable"


class CognitiveLoadPreference(Enum):
    """User preference for cognitive load management."""
    MINIMAL = "minimal"          # Prefer very simple, minimal information
    MODERATE = "moderate"        # Balanced information density
    HIGH = "high"               # Can handle complex information
    ADAPTIVE = "adaptive"       # Let system decide based on current state


class InteractionStyle(Enum):
    """User's preferred interaction style."""
    DIRECT = "direct"           # Brief, to-the-point responses
    ENCOURAGING = "encouraging" # Positive, motivational tone
    COLLABORATIVE = "collaborative"  # Working together approach
    ANALYTICAL = "analytical"   # Detailed explanations and reasoning


@dataclass
class EnergySchedule:
    """User's energy pattern schedule."""
    peak_hours: List[int]       # Hours of highest energy (0-23)
    low_hours: List[int]        # Hours of lowest energy
    variable_hours: List[int]   # Hours that vary day to day
    pattern_confidence: float   # How consistent this pattern is (0.0-1.0)
    last_updated: datetime


@dataclass
class CognitiveThresholds:
    """Personalized cognitive load thresholds."""
    overwhelm_threshold: float      # Point where user gets overwhelmed (0.0-1.0)
    optimal_load: float            # Sweet spot for productivity (0.0-1.0)
    minimum_engagement: float      # Minimum needed to maintain focus (0.0-1.0)
    context_item_limit: int        # Max context items before overload
    response_length_preference: int # Preferred response length (characters)
    complexity_tolerance: float    # Tolerance for complex tasks (0.0-1.0)


@dataclass
class NudgePreferences:
    """User preferences for nudging behavior."""
    preferred_methods: List[str]    # ['web', 'telegram', 'email', 'calendar']
    timing_preferences: Dict[str, str]  # Time slots for different nudge types
    frequency_limits: Dict[str, int]    # Max nudges per time period
    urgency_escalation: bool          # Whether to escalate urgent items
    quiet_hours: List[Tuple[int, int]] # Hours to avoid nudging
    effectiveness_scores: Dict[str, float]  # How effective each method is


class ADHDUserProfile(BaseModel):
    """
    Comprehensive ADHD user profile with adaptive learning capabilities.
    
    This profile learns from user behavior and adapts interventions
    to individual needs while maintaining user control and privacy.
    """
    user_id: str
    
    # Core ADHD characteristics
    adhd_subtype: ADHDSubtype = ADHDSubtype.UNSPECIFIED
    subtype_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Energy and temporal patterns
    energy_pattern: EnergyPattern = EnergyPattern.UNPREDICTABLE
    energy_schedule: Optional[EnergySchedule] = None
    circadian_preference: str = "neutral"  # "morning", "evening", "neutral"
    
    # Cognitive characteristics
    cognitive_thresholds: Optional[CognitiveThresholds] = None
    cognitive_load_preference: CognitiveLoadPreference = CognitiveLoadPreference.ADAPTIVE
    working_memory_capacity: float = Field(ge=0.0, le=1.0, default=0.5)
    attention_span_average: float = Field(ge=0.0, default=25.0)  # minutes
    
    # Interaction preferences
    interaction_style: InteractionStyle = InteractionStyle.ENCOURAGING
    nudge_preferences: Optional[NudgePreferences] = None
    interface_complexity: str = "adaptive"  # "simple", "moderate", "complex", "adaptive"
    
    # Behavioral patterns
    hyperfocus_tendency: float = Field(ge=0.0, le=1.0, default=0.3)
    task_switching_pattern: str = "moderate"  # "low", "moderate", "high"
    procrastination_triggers: List[str] = Field(default_factory=list)
    motivation_factors: List[str] = Field(default_factory=list)
    
    # Personalization data
    successful_strategies: Dict[str, float] = Field(default_factory=dict)
    avoided_strategies: List[str] = Field(default_factory=list)
    custom_preferences: Dict[str, Any] = Field(default_factory=dict)
    
    # Adaptation tracking
    learning_rate: float = Field(ge=0.0, le=1.0, default=0.1)
    adaptation_enabled: bool = True
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    profile_version: int = 1
    
    # Privacy and control
    data_sharing_consent: bool = False
    learning_enabled: bool = True
    pattern_detection_enabled: bool = True
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserProfileManager:
    """
    Manager for ADHD user profiles with adaptive learning capabilities.
    
    Handles profile creation, updates, adaptation, and privacy controls
    while integrating with pattern recognition and intervention systems.
    """
    
    def __init__(self):
        self._profiles: Dict[str, ADHDUserProfile] = {}
        self._adaptation_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Learning parameters
        self.min_interactions_for_adaptation = 10
        self.confidence_threshold = 0.6
        self.adaptation_frequency_hours = 24
        
        logger.info("UserProfileManager initialized")
    
    async def get_or_create_profile(self, user_id: str) -> ADHDUserProfile:
        """Get existing profile or create new one with intelligent defaults."""
        try:
            if user_id in self._profiles:
                return self._profiles[user_id]
            
            # Try to load from trace memory first
            profile = await self._load_profile_from_traces(user_id)
            
            if not profile:
                # Create new profile with intelligent defaults
                profile = await self._create_initial_profile(user_id)
            
            self._profiles[user_id] = profile
            logger.info("Profile loaded/created", user_id=user_id)
            
            return profile
            
        except Exception as e:
            logger.error("Profile creation failed", user_id=user_id, error=str(e))
            # Return minimal safe profile
            return ADHDUserProfile(user_id=user_id)
    
    async def update_profile_from_interaction(self, 
                                            user_id: str, 
                                            interaction_data: Dict[str, Any]) -> None:
        """Update profile based on user interaction patterns."""
        try:
            profile = await self.get_or_create_profile(user_id)
            
            if not profile.adaptation_enabled:
                return
            
            # Extract insights from interaction
            insights = await self._extract_interaction_insights(interaction_data)
            
            # Update energy patterns
            await self._update_energy_patterns(profile, insights)
            
            # Update cognitive thresholds
            await self._update_cognitive_thresholds(profile, insights)
            
            # Update interaction preferences
            await self._update_interaction_preferences(profile, insights)
            
            # Update nudge effectiveness
            await self._update_nudge_effectiveness(profile, insights)
            
            # Update ADHD subtype confidence
            await self._update_subtype_classification(profile, user_id)
            
            # Save updated profile
            await self._save_profile(profile)
            
            profile.last_updated = datetime.utcnow()
            profile.profile_version += 1
            
            logger.info("Profile updated from interaction", 
                       user_id=user_id, 
                       version=profile.profile_version)
            
        except Exception as e:
            logger.error("Profile update failed", user_id=user_id, error=str(e))
    
    async def adapt_to_pattern_detection(self, 
                                       user_id: str, 
                                       detected_patterns: List[Any]) -> None:
        """Adapt profile based on detected ADHD patterns."""
        try:
            profile = await self.get_or_create_profile(user_id)
            
            if not profile.pattern_detection_enabled:
                return
            
            adaptations_made = []
            
            for pattern in detected_patterns:
                # Adapt cognitive thresholds based on patterns
                if pattern.pattern_type == PatternType.OVERWHELM:
                    if profile.cognitive_thresholds:
                        profile.cognitive_thresholds.overwhelm_threshold *= 0.9  # Lower threshold
                        adaptations_made.append("lowered_overwhelm_threshold")
                
                # Adapt hyperfocus tendency
                if pattern.pattern_type == PatternType.HYPERFOCUS:
                    profile.hyperfocus_tendency = min(1.0, profile.hyperfocus_tendency + 0.1)
                    adaptations_made.append("increased_hyperfocus_tendency")
                
                # Adapt interaction style based on emotional patterns
                if pattern.pattern_type == PatternType.EMOTIONAL_DYSREGULATION:
                    if profile.interaction_style != InteractionStyle.ENCOURAGING:
                        profile.interaction_style = InteractionStyle.ENCOURAGING
                        adaptations_made.append("switched_to_encouraging_style")
            
            if adaptations_made:
                await self._save_profile(profile)
                await self._log_adaptations(user_id, adaptations_made)
                
                logger.info("Profile adapted to patterns", 
                           user_id=user_id, 
                           adaptations=adaptations_made)
            
        except Exception as e:
            logger.error("Pattern-based adaptation failed", user_id=user_id, error=str(e))
    
    async def get_personalized_settings(self, user_id: str) -> Dict[str, Any]:
        """Get personalized settings for system components."""
        try:
            profile = await self.get_or_create_profile(user_id)
            
            # Build personalized settings
            settings = {
                'cognitive_load': {
                    'max_context_items': profile.cognitive_thresholds.context_item_limit if profile.cognitive_thresholds else 8,
                    'response_length': profile.cognitive_thresholds.response_length_preference if profile.cognitive_thresholds else 150,
                    'complexity_limit': profile.cognitive_thresholds.complexity_tolerance if profile.cognitive_thresholds else 0.7
                },
                'nudging': {
                    'preferred_methods': profile.nudge_preferences.preferred_methods if profile.nudge_preferences else ['web'],
                    'timing': profile.nudge_preferences.timing_preferences if profile.nudge_preferences else {'general': '09:00'},
                    'frequency_limits': profile.nudge_preferences.frequency_limits if profile.nudge_preferences else {'daily': 5}
                },
                'interface': {
                    'complexity': profile.interface_complexity,
                    'interaction_style': profile.interaction_style.value
                },
                'patterns': {
                    'adhd_subtype': profile.adhd_subtype.value,
                    'hyperfocus_tendency': profile.hyperfocus_tendency,
                    'energy_pattern': profile.energy_pattern.value
                }
            }
            
            return settings
            
        except Exception as e:
            logger.error("Personalized settings retrieval failed", user_id=user_id, error=str(e))
            return self._get_default_settings()
    
    async def update_user_preferences(self, 
                                    user_id: str, 
                                    preferences: Dict[str, Any]) -> bool:
        """Update user preferences with validation."""
        try:
            profile = await self.get_or_create_profile(user_id)
            
            # Validate and update preferences
            updated = False
            
            if 'cognitive_load_preference' in preferences:
                new_pref = CognitiveLoadPreference(preferences['cognitive_load_preference'])
                profile.cognitive_load_preference = new_pref
                updated = True
            
            if 'interaction_style' in preferences:
                new_style = InteractionStyle(preferences['interaction_style'])
                profile.interaction_style = new_style
                updated = True
            
            if 'interface_complexity' in preferences:
                if preferences['interface_complexity'] in ['simple', 'moderate', 'complex', 'adaptive']:
                    profile.interface_complexity = preferences['interface_complexity']
                    updated = True
            
            if 'nudge_methods' in preferences:
                if not profile.nudge_preferences:
                    profile.nudge_preferences = NudgePreferences(
                        preferred_methods=preferences['nudge_methods'],
                        timing_preferences={},
                        frequency_limits={},
                        urgency_escalation=True,
                        quiet_hours=[],
                        effectiveness_scores={}
                    )
                else:
                    profile.nudge_preferences.preferred_methods = preferences['nudge_methods']
                updated = True
            
            if 'privacy_settings' in preferences:
                privacy = preferences['privacy_settings']
                if 'learning_enabled' in privacy:
                    profile.learning_enabled = privacy['learning_enabled']
                if 'pattern_detection_enabled' in privacy:
                    profile.pattern_detection_enabled = privacy['pattern_detection_enabled']
                if 'data_sharing_consent' in privacy:
                    profile.data_sharing_consent = privacy['data_sharing_consent']
                updated = True
            
            # Update custom preferences
            if 'custom' in preferences:
                profile.custom_preferences.update(preferences['custom'])
                updated = True
            
            if updated:
                await self._save_profile(profile)
                logger.info("User preferences updated", user_id=user_id)
            
            return updated
            
        except Exception as e:
            logger.error("User preferences update failed", user_id=user_id, error=str(e))
            return False
    
    async def _create_initial_profile(self, user_id: str) -> ADHDUserProfile:
        """Create initial profile with intelligent defaults based on any available data."""
        try:
            # Get pattern engine for initial assessment
            pattern_engine = get_pattern_engine(user_id)
            
            # Get any existing traces to inform initial profile
            traces = await trace_memory.get_user_traces(user_id, limit=50)
            
            # Initialize with defaults
            profile = ADHDUserProfile(user_id=user_id)
            
            # Set intelligent defaults based on trace analysis
            if traces:
                # Analyze traces for initial insights
                interaction_times = [trace.timestamp.hour for trace in traces]
                if interaction_times:
                    # Determine likely peak hours
                    from collections import Counter
                    hour_counts = Counter(interaction_times)
                    peak_hours = [hour for hour, count in hour_counts.most_common(3)]
                    
                    profile.energy_schedule = EnergySchedule(
                        peak_hours=peak_hours,
                        low_hours=[],
                        variable_hours=[],
                        pattern_confidence=0.3,  # Low initial confidence
                        last_updated=datetime.utcnow()
                    )
                
                # Set task switching pattern based on trace variety
                unique_tasks = len(set(trace.task_id for trace in traces if trace.task_id))
                if unique_tasks > len(traces) * 0.7:
                    profile.task_switching_pattern = "high"
                elif unique_tasks > len(traces) * 0.3:
                    profile.task_switching_pattern = "moderate"
                else:
                    profile.task_switching_pattern = "low"
            
            # Set conservative cognitive thresholds initially
            profile.cognitive_thresholds = CognitiveThresholds(
                overwhelm_threshold=0.7,
                optimal_load=0.5,
                minimum_engagement=0.3,
                context_item_limit=8,
                response_length_preference=150,
                complexity_tolerance=0.6
            )
            
            # Set default nudge preferences
            profile.nudge_preferences = NudgePreferences(
                preferred_methods=['web'],
                timing_preferences={'general': '09:00'},
                frequency_limits={'hourly': 2, 'daily': 8},
                urgency_escalation=True,
                quiet_hours=[(22, 7)],  # 10 PM to 7 AM
                effectiveness_scores={}
            )
            
            await self._save_profile(profile)
            
            logger.info("Initial profile created", user_id=user_id)
            return profile
            
        except Exception as e:
            logger.error("Initial profile creation failed", user_id=user_id, error=str(e))
            return ADHDUserProfile(user_id=user_id)
    
    async def _extract_interaction_insights(self, 
                                          interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights from interaction data for profile adaptation."""
        insights = {
            'timestamp': datetime.utcnow(),
            'energy_indicators': [],
            'cognitive_load_indicators': [],
            'preference_indicators': [],
            'effectiveness_data': {}
        }
        
        try:
            # Energy level indicators
            content = interaction_data.get('content', '').lower()
            if any(word in content for word in ['tired', 'exhausted', 'drained']):
                insights['energy_indicators'].append('low_energy')
            elif any(word in content for word in ['energized', 'motivated', 'ready']):
                insights['energy_indicators'].append('high_energy')
            
            # Cognitive load indicators
            cognitive_load = interaction_data.get('cognitive_load', 0.5)
            response_time = interaction_data.get('response_time_ms', 0)
            
            if cognitive_load > 0.8:
                insights['cognitive_load_indicators'].append('high_load')
            elif cognitive_load < 0.3:
                insights['cognitive_load_indicators'].append('low_load')
            
            if response_time > 5000:  # 5+ seconds
                insights['cognitive_load_indicators'].append('slow_processing')
            
            # Preference indicators
            if 'simple' in content or 'brief' in content:
                insights['preference_indicators'].append('prefers_simple')
            elif 'detail' in content or 'explain' in content:
                insights['preference_indicators'].append('wants_detail')
            
            # Nudge effectiveness
            if interaction_data.get('responding_to_nudge'):
                nudge_method = interaction_data.get('nudge_method', 'unknown')
                nudge_delay = interaction_data.get('nudge_response_delay_minutes', 0)
                
                # Effectiveness based on response time
                effectiveness = max(0.1, 1.0 - (nudge_delay / 60.0))  # Decay over 1 hour
                insights['effectiveness_data'][nudge_method] = effectiveness
            
            return insights
            
        except Exception as e:
            logger.warning("Interaction insights extraction failed", error=str(e))
            return insights
    
    async def _update_energy_patterns(self, 
                                    profile: ADHDUserProfile, 
                                    insights: Dict[str, Any]) -> None:
        """Update energy pattern recognition."""
        try:
            current_hour = insights['timestamp'].hour
            
            if not profile.energy_schedule:
                profile.energy_schedule = EnergySchedule(
                    peak_hours=[],
                    low_hours=[],
                    variable_hours=[],
                    pattern_confidence=0.0,
                    last_updated=datetime.utcnow()
                )
            
            # Update based on energy indicators
            for indicator in insights['energy_indicators']:
                if indicator == 'high_energy':
                    if current_hour not in profile.energy_schedule.peak_hours:
                        profile.energy_schedule.peak_hours.append(current_hour)
                elif indicator == 'low_energy':
                    if current_hour not in profile.energy_schedule.low_hours:
                        profile.energy_schedule.low_hours.append(current_hour)
            
            # Increase confidence gradually
            profile.energy_schedule.pattern_confidence = min(1.0, 
                profile.energy_schedule.pattern_confidence + 0.05)
            profile.energy_schedule.last_updated = datetime.utcnow()
            
        except Exception as e:
            logger.warning("Energy pattern update failed", error=str(e))
    
    async def _update_cognitive_thresholds(self, 
                                         profile: ADHDUserProfile, 
                                         insights: Dict[str, Any]) -> None:
        """Update cognitive load thresholds based on user responses."""
        try:
            if not profile.cognitive_thresholds:
                return
            
            learning_rate = profile.learning_rate
            
            # Adjust thresholds based on indicators
            for indicator in insights['cognitive_load_indicators']:
                if indicator == 'high_load':
                    # User experienced high load - lower threshold
                    profile.cognitive_thresholds.overwhelm_threshold *= (1 - learning_rate)
                elif indicator == 'slow_processing':
                    # Slow processing - reduce complexity tolerance
                    profile.cognitive_thresholds.complexity_tolerance *= (1 - learning_rate * 0.5)
            
            # Adjust based on preference indicators
            for indicator in insights['preference_indicators']:
                if indicator == 'prefers_simple':
                    profile.cognitive_thresholds.response_length_preference = int(
                        profile.cognitive_thresholds.response_length_preference * 0.9
                    )
                elif indicator == 'wants_detail':
                    profile.cognitive_thresholds.response_length_preference = int(
                        profile.cognitive_thresholds.response_length_preference * 1.1
                    )
            
        except Exception as e:
            logger.warning("Cognitive thresholds update failed", error=str(e))
    
    async def _update_interaction_preferences(self, 
                                            profile: ADHDUserProfile, 
                                            insights: Dict[str, Any]) -> None:
        """Update interaction style preferences."""
        try:
            # This is a simplified example - in practice, this would use more sophisticated analysis
            for indicator in insights['preference_indicators']:
                if indicator == 'prefers_simple':
                    if profile.interface_complexity == 'complex':
                        profile.interface_complexity = 'moderate'
                elif indicator == 'wants_detail':
                    if profile.interface_complexity == 'simple':
                        profile.interface_complexity = 'moderate'
            
        except Exception as e:
            logger.warning("Interaction preferences update failed", error=str(e))
    
    async def _update_nudge_effectiveness(self, 
                                        profile: ADHDUserProfile, 
                                        insights: Dict[str, Any]) -> None:
        """Update nudge effectiveness scores."""
        try:
            if not profile.nudge_preferences:
                return
            
            for method, effectiveness in insights['effectiveness_data'].items():
                current_score = profile.nudge_preferences.effectiveness_scores.get(method, 0.5)
                # Update with exponential moving average
                new_score = 0.7 * current_score + 0.3 * effectiveness
                profile.nudge_preferences.effectiveness_scores[method] = new_score
            
        except Exception as e:
            logger.warning("Nudge effectiveness update failed", error=str(e))
    
    async def _update_subtype_classification(self, 
                                           profile: ADHDUserProfile, 
                                           user_id: str) -> None:
        """Update ADHD subtype classification based on pattern recognition."""
        try:
            pattern_engine = get_pattern_engine(user_id)
            new_subtype = await pattern_engine.classify_adhd_subtype()
            
            if new_subtype != profile.adhd_subtype:
                profile.adhd_subtype = new_subtype
                # Increase confidence if consistent classification
                profile.subtype_confidence = min(1.0, profile.subtype_confidence + 0.1)
            else:
                # Reinforce existing classification
                profile.subtype_confidence = min(1.0, profile.subtype_confidence + 0.05)
            
        except Exception as e:
            logger.warning("Subtype classification update failed", error=str(e))
    
    async def _save_profile(self, profile: ADHDUserProfile) -> None:
        """Save profile to persistent storage."""
        try:
            # Store in trace memory for persistence
            trace_record = TraceMemoryModel(
                user_id=profile.user_id,
                event_type="profile_update",
                event_data=profile.dict(),
                confidence=1.0,
                source="profile_manager"
            )
            
            await trace_memory.store_trace(trace_record)
            
        except Exception as e:
            logger.error("Profile save failed", user_id=profile.user_id, error=str(e))
    
    async def _load_profile_from_traces(self, user_id: str) -> Optional[ADHDUserProfile]:
        """Load profile from trace memory."""
        try:
            # Get most recent profile update
            traces = await trace_memory.get_user_traces(
                user_id, 
                event_types=["profile_update"], 
                limit=1
            )
            
            if traces:
                profile_data = traces[0].event_data
                return ADHDUserProfile(**profile_data)
            
            return None
            
        except Exception as e:
            logger.warning("Profile load from traces failed", user_id=user_id, error=str(e))
            return None
    
    async def _log_adaptations(self, user_id: str, adaptations: List[str]) -> None:
        """Log profile adaptations for transparency."""
        try:
            trace_record = TraceMemoryModel(
                user_id=user_id,
                event_type="profile_adaptation",
                event_data={
                    "adaptations": adaptations,
                    "timestamp": datetime.utcnow().isoformat(),
                    "adaptation_count": len(adaptations)
                },
                confidence=1.0,
                source="profile_manager"
            )
            
            await trace_memory.store_trace(trace_record)
            
        except Exception as e:
            logger.error("Adaptation logging failed", user_id=user_id, error=str(e))
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get safe default settings."""
        return {
            'cognitive_load': {
                'max_context_items': 8,
                'response_length': 150,
                'complexity_limit': 0.7
            },
            'nudging': {
                'preferred_methods': ['web'],
                'timing': {'general': '09:00'},
                'frequency_limits': {'daily': 5}
            },
            'interface': {
                'complexity': 'adaptive',
                'interaction_style': 'encouraging'
            },
            'patterns': {
                'adhd_subtype': 'unspecified',
                'hyperfocus_tendency': 0.3,
                'energy_pattern': 'unpredictable'
            }
        }


# Global profile manager
profile_manager = UserProfileManager()