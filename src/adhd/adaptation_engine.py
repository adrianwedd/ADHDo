"""
Intelligent Adaptation System for ADHD Support.

This module implements real-time adaptation of the user interface, cognitive load,
nudge timing, and intervention strategies based on individual ADHD patterns and
current user state. The system respects neurodiversity principles by empowering
rather than restricting user capabilities.

Core Features:
- Dynamic interface complexity adjustment
- Real-time cognitive load optimization
- Personalized nudge timing and intensity
- Adaptive crisis intervention protocols
- Context-aware accessibility modifications
- Privacy-preserving adaptation algorithms

The adaptation engine continuously learns from user interactions while
maintaining complete user control and transparency about system decisions.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from collections import deque, defaultdict

import structlog
from pydantic import BaseModel

from mcp_server.models import TraceMemory as TraceMemoryModel, MCPFrame
from traces.memory import trace_memory
from adhd.pattern_engine import PatternDetection, PatternType, PatternSeverity, get_pattern_engine
from adhd.user_profile import profile_manager, CognitiveLoadPreference, InteractionStyle

logger = structlog.get_logger()


class AdaptationType(Enum):
    """Types of adaptations the system can make."""
    INTERFACE_SIMPLIFICATION = "interface_simplification"
    COGNITIVE_LOAD_REDUCTION = "cognitive_load_reduction"
    NUDGE_TIMING_ADJUSTMENT = "nudge_timing_adjustment"
    RESPONSE_STYLE_MODIFICATION = "response_style_modification"
    CRISIS_PROTOCOL_ACTIVATION = "crisis_protocol_activation"
    ACCESSIBILITY_ENHANCEMENT = "accessibility_enhancement"
    COMPLEXITY_SCALING = "complexity_scaling"
    CONTEXT_FILTERING = "context_filtering"


class AdaptationPriority(Enum):
    """Priority levels for adaptations."""
    CRITICAL = "critical"    # Immediate adaptation required (safety/crisis)
    HIGH = "high"           # Important for user wellbeing
    MEDIUM = "medium"       # Improves user experience
    LOW = "low"             # Minor optimization


@dataclass
class AdaptationDecision:
    """Represents an adaptation decision made by the system."""
    adaptation_type: AdaptationType
    priority: AdaptationPriority
    confidence: float
    reasoning: str
    parameters: Dict[str, Any]
    expected_outcome: str
    rollback_criteria: List[str]
    timestamp: datetime
    user_id: str


@dataclass
class AdaptationResult:
    """Result of applying an adaptation."""
    success: bool
    adaptation_id: str
    applied_changes: Dict[str, Any]
    user_feedback: Optional[Dict[str, Any]]
    effectiveness_score: Optional[float]
    side_effects: List[str]
    timestamp: datetime


class InterfaceComplexityLevel(Enum):
    """Interface complexity levels."""
    MINIMAL = "minimal"      # Absolute minimum information
    SIMPLE = "simple"        # Basic, essential information only
    MODERATE = "moderate"    # Balanced information density
    DETAILED = "detailed"    # Comprehensive information
    EXPERT = "expert"        # Full complexity for power users


class CognitiveLoadAdapter:
    """
    Adapter for real-time cognitive load optimization.
    
    Monitors user cognitive state and automatically adjusts information
    density, response complexity, and context richness to prevent overwhelm
    while maintaining effectiveness.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.current_load = 0.5
        self.load_history = deque(maxlen=50)
        self.adaptation_history = []
        
        # Load thresholds (will be personalized)
        self.overwhelm_threshold = 0.8
        self.optimal_range = (0.4, 0.7)
        self.minimum_engagement = 0.2
        
        # Adaptation parameters
        self.adaptation_sensitivity = 0.1
        self.rollback_threshold = 0.9
        
    async def assess_current_load(self, frame: MCPFrame, interaction_data: Dict[str, Any]) -> float:
        """Assess current cognitive load based on context and user state."""
        try:
            base_load = 0.0
            
            # Context complexity
            context_items = len(frame.context)
            base_load += min(context_items / 10.0, 0.4)  # Max 0.4 from context
            
            # Information density in context
            total_data_points = sum(len(str(ctx.data)) for ctx in frame.context)
            base_load += min(total_data_points / 1000.0, 0.3)  # Max 0.3 from density
            
            # User state factors
            current_energy = interaction_data.get('energy_level', 0.5)
            base_load += (1.0 - current_energy) * 0.2  # Fatigue increases load
            
            # Task complexity
            task_complexity = interaction_data.get('task_complexity', 0.5)
            base_load += task_complexity * 0.3
            
            # Time pressure
            time_pressure = interaction_data.get('time_pressure', 0.0)
            base_load += time_pressure * 0.2
            
            # Normalize to 0-1 range
            cognitive_load = min(base_load, 1.0)
            
            # Update history
            self.current_load = cognitive_load
            self.load_history.append({
                'load': cognitive_load,
                'timestamp': datetime.utcnow(),
                'context_items': context_items
            })
            
            return cognitive_load
            
        except Exception as e:
            logger.warning("Cognitive load assessment failed", error=str(e))
            return 0.5  # Safe default
    
    async def recommend_load_adaptations(self, current_load: float) -> List[AdaptationDecision]:
        """Recommend adaptations based on cognitive load assessment."""
        adaptations = []
        
        try:
            if current_load > self.overwhelm_threshold:
                # High load - reduce complexity
                adaptations.append(AdaptationDecision(
                    adaptation_type=AdaptationType.COGNITIVE_LOAD_REDUCTION,
                    priority=AdaptationPriority.HIGH,
                    confidence=0.9,
                    reasoning=f"Cognitive load {current_load:.2f} exceeds threshold {self.overwhelm_threshold}",
                    parameters={
                        'max_context_items': 5,
                        'response_length_limit': 100,
                        'simplify_language': True,
                        'remove_non_essential': True
                    },
                    expected_outcome="Reduced cognitive overwhelm and improved comprehension",
                    rollback_criteria=["user_confusion", "task_incompletion", "explicitly_requests_detail"],
                    timestamp=datetime.utcnow(),
                    user_id=self.user_id
                ))
                
                adaptations.append(AdaptationDecision(
                    adaptation_type=AdaptationType.INTERFACE_SIMPLIFICATION,
                    priority=AdaptationPriority.HIGH,
                    confidence=0.8,
                    reasoning="Interface simplification needed due to high cognitive load",
                    parameters={
                        'complexity_level': InterfaceComplexityLevel.SIMPLE.value,
                        'hide_advanced_options': True,
                        'reduce_visual_clutter': True
                    },
                    expected_outcome="Clearer focus on essential elements",
                    rollback_criteria=["user_seeks_advanced_features", "task_requires_complexity"],
                    timestamp=datetime.utcnow(),
                    user_id=self.user_id
                ))
            
            elif current_load < self.minimum_engagement:
                # Too low load - might need more engagement
                adaptations.append(AdaptationDecision(
                    adaptation_type=AdaptationType.COMPLEXITY_SCALING,
                    priority=AdaptationPriority.MEDIUM,
                    confidence=0.6,
                    reasoning=f"Cognitive load {current_load:.2f} below engagement threshold",
                    parameters={
                        'increase_detail_level': True,
                        'add_contextual_information': True,
                        'enable_advanced_features': True
                    },
                    expected_outcome="Increased engagement and cognitive stimulation",
                    rollback_criteria=["signs_of_overwhelm", "user_requests_simplification"],
                    timestamp=datetime.utcnow(),
                    user_id=self.user_id
                ))
            
            return adaptations
            
        except Exception as e:
            logger.error("Load adaptation recommendation failed", error=str(e))
            return []


class InterfaceAdapter:
    """
    Adapter for dynamic interface complexity management.
    
    Automatically adjusts interface elements, information density,
    and interaction patterns based on user cognitive state and preferences.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.current_complexity = InterfaceComplexityLevel.MODERATE
        self.adaptation_stack = []  # For rollbacks
        
    async def adapt_interface_complexity(self, 
                                       target_level: InterfaceComplexityLevel,
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt interface to target complexity level."""
        try:
            adaptations = {}
            
            if target_level == InterfaceComplexityLevel.MINIMAL:
                adaptations = {
                    'max_visible_items': 3,
                    'hide_secondary_actions': True,
                    'use_icons_only': True,
                    'single_column_layout': True,
                    'hide_advanced_settings': True,
                    'simplified_navigation': True
                }
            
            elif target_level == InterfaceComplexityLevel.SIMPLE:
                adaptations = {
                    'max_visible_items': 5,
                    'hide_secondary_actions': True,
                    'use_clear_labels': True,
                    'group_related_items': True,
                    'hide_advanced_settings': True,
                    'show_essential_only': True
                }
            
            elif target_level == InterfaceComplexityLevel.MODERATE:
                adaptations = {
                    'max_visible_items': 8,
                    'show_common_actions': True,
                    'balanced_information': True,
                    'progressive_disclosure': True,
                    'contextual_help': True
                }
            
            elif target_level == InterfaceComplexityLevel.DETAILED:
                adaptations = {
                    'max_visible_items': 12,
                    'show_all_actions': True,
                    'detailed_information': True,
                    'advanced_controls': True,
                    'comprehensive_options': True
                }
            
            elif target_level == InterfaceComplexityLevel.EXPERT:
                adaptations = {
                    'max_visible_items': -1,  # No limit
                    'show_all_features': True,
                    'expert_shortcuts': True,
                    'advanced_customization': True,
                    'power_user_mode': True
                }
            
            # Store current state for potential rollback
            self.adaptation_stack.append({
                'previous_level': self.current_complexity,
                'timestamp': datetime.utcnow(),
                'context': context
            })
            
            self.current_complexity = target_level
            
            logger.info("Interface adapted", 
                       user_id=self.user_id,
                       target_level=target_level.value,
                       adaptations=adaptations)
            
            return adaptations
            
        except Exception as e:
            logger.error("Interface adaptation failed", error=str(e))
            return {}
    
    async def rollback_last_adaptation(self) -> bool:
        """Rollback the most recent interface adaptation."""
        try:
            if not self.adaptation_stack:
                return False
            
            last_adaptation = self.adaptation_stack.pop()
            self.current_complexity = last_adaptation['previous_level']
            
            logger.info("Interface adaptation rolled back", 
                       user_id=self.user_id,
                       restored_level=self.current_complexity.value)
            
            return True
            
        except Exception as e:
            logger.error("Interface rollback failed", error=str(e))
            return False


class ResponseAdapter:
    """
    Adapter for response style and content optimization.
    
    Modifies response length, complexity, tone, and structure based
    on user state and preferences while maintaining effectiveness.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.response_history = deque(maxlen=20)
        
    async def adapt_response_style(self, 
                                 original_response: str,
                                 user_state: Dict[str, Any],
                                 adaptations: List[AdaptationDecision]) -> str:
        """Adapt response based on user state and adaptation decisions."""
        try:
            adapted_response = original_response
            
            for adaptation in adaptations:
                if adaptation.adaptation_type == AdaptationType.COGNITIVE_LOAD_REDUCTION:
                    adapted_response = await self._simplify_response(
                        adapted_response, 
                        adaptation.parameters
                    )
                
                elif adaptation.adaptation_type == AdaptationType.RESPONSE_STYLE_MODIFICATION:
                    adapted_response = await self._modify_style(
                        adapted_response,
                        adaptation.parameters
                    )
            
            # Apply general user state adaptations
            if user_state.get('stress_level', 0) > 0.7:
                adapted_response = await self._apply_calming_tone(adapted_response)
            
            if user_state.get('energy_level', 0.5) < 0.3:
                adapted_response = await self._apply_gentle_encouragement(adapted_response)
            
            # Track adaptation
            self.response_history.append({
                'original_length': len(original_response),
                'adapted_length': len(adapted_response),
                'adaptations_applied': len(adaptations),
                'timestamp': datetime.utcnow()
            })
            
            return adapted_response
            
        except Exception as e:
            logger.error("Response adaptation failed", error=str(e))
            return original_response  # Return original on failure
    
    async def _simplify_response(self, response: str, parameters: Dict[str, Any]) -> str:
        """Simplify response based on parameters."""
        try:
            # Length reduction
            max_length = parameters.get('response_length_limit', 150)
            if len(response) > max_length:
                # Simple truncation with ellipsis (could be more sophisticated)
                sentences = response.split('. ')
                simplified = ""
                for sentence in sentences:
                    if len(simplified + sentence) < max_length - 3:
                        simplified += sentence + ". "
                    else:
                        break
                response = simplified.strip() + "..."
            
            # Language simplification
            if parameters.get('simplify_language', False):
                # Replace complex words/phrases with simpler alternatives
                simplifications = {
                    'utilize': 'use',
                    'subsequently': 'then',
                    'accordingly': 'so',
                    'consequently': 'so',
                    'nevertheless': 'but',
                    'furthermore': 'also',
                    'additionally': 'also'
                }
                
                for complex_word, simple_word in simplifications.items():
                    response = response.replace(complex_word, simple_word)
            
            return response
            
        except Exception as e:
            logger.warning("Response simplification failed", error=str(e))
            return response
    
    async def _modify_style(self, response: str, parameters: Dict[str, Any]) -> str:
        """Modify response style based on parameters."""
        try:
            style = parameters.get('target_style', 'encouraging')
            
            if style == 'direct':
                # Remove hedging language and be more direct
                response = response.replace('maybe', '').replace('perhaps', '')
                response = response.replace('you might want to', 'you should')
                response = response.replace('you could try', 'try')
            
            elif style == 'encouraging':
                # Add more positive, encouraging language
                if not any(word in response.lower() for word in ['great', 'excellent', 'good', 'nice']):
                    response = "Great question! " + response
                
                # Add encouraging endings
                if not response.endswith(('!', '.')):
                    response += ". You've got this!"
            
            elif style == 'collaborative':
                # Use more collaborative language
                response = response.replace('you should', 'we could')
                response = response.replace('I recommend', "let's try")
            
            return response
            
        except Exception as e:
            logger.warning("Style modification failed", error=str(e))
            return response
    
    async def _apply_calming_tone(self, response: str) -> str:
        """Apply calming tone for stressed users."""
        calming_phrases = [
            "Take a deep breath.",
            "It's okay to take this one step at a time.",
            "No pressure - we'll figure this out together."
        ]
        
        # Add calming opener if response seems intense
        if any(word in response.lower() for word in ['must', 'urgent', 'immediately', 'quickly']):
            return f"{calming_phrases[0]} {response}"
        
        return response
    
    async def _apply_gentle_encouragement(self, response: str) -> str:
        """Apply gentle encouragement for low-energy users."""
        encouraging_phrases = [
            "Small steps count too.",
            "Even a little progress is still progress.",
            "You're doing better than you think."
        ]
        
        # Add gentle encouragement
        return f"{response} {encouraging_phrases[0]}"


class AdaptationEngine:
    """
    Main adaptation engine that orchestrates all adaptive behaviors.
    
    Coordinates between different adapters to provide comprehensive,
    real-time adaptation that enhances user experience while respecting
    neurodivergent needs and preferences.
    """
    
    def __init__(self):
        self.user_adapters: Dict[str, Dict[str, Any]] = {}
        self.adaptation_history: Dict[str, List[AdaptationResult]] = defaultdict(list)
        self.effectiveness_tracking: Dict[str, Dict[str, float]] = defaultdict(dict)
        
    async def process_adaptation_request(self, 
                                       user_id: str,
                                       current_state: Dict[str, Any],
                                       detected_patterns: List[PatternDetection],
                                       frame: MCPFrame) -> List[AdaptationDecision]:
        """Process adaptation request and return recommended adaptations."""
        try:
            # Initialize user adapters if needed
            if user_id not in self.user_adapters:
                await self._initialize_user_adapters(user_id)
            
            adapters = self.user_adapters[user_id]
            adaptations = []
            
            # Get user profile for personalized adaptations
            profile = await profile_manager.get_or_create_profile(user_id)
            
            # Assess cognitive load
            cognitive_adapter = adapters['cognitive_load']
            current_load = await cognitive_adapter.assess_current_load(frame, current_state)
            load_adaptations = await cognitive_adapter.recommend_load_adaptations(current_load)
            adaptations.extend(load_adaptations)
            
            # Process pattern-based adaptations
            pattern_adaptations = await self._process_pattern_adaptations(
                detected_patterns, profile, current_state
            )
            adaptations.extend(pattern_adaptations)
            
            # Add crisis adaptations if needed
            crisis_adaptations = await self._assess_crisis_adaptations(
                detected_patterns, current_state
            )
            adaptations.extend(crisis_adaptations)
            
            # Sort by priority and confidence
            adaptations.sort(
                key=lambda x: (x.priority.value, -x.confidence), 
                reverse=True
            )
            
            logger.info("Adaptation recommendations generated", 
                       user_id=user_id,
                       total_adaptations=len(adaptations),
                       high_priority=len([a for a in adaptations if a.priority == AdaptationPriority.HIGH]))
            
            return adaptations
            
        except Exception as e:
            logger.error("Adaptation request processing failed", user_id=user_id, error=str(e))
            return []
    
    async def apply_adaptations(self, 
                              adaptations: List[AdaptationDecision],
                              original_response: str,
                              frame: MCPFrame) -> Tuple[str, Dict[str, Any]]:
        """Apply adaptations and return modified response and interface changes."""
        try:
            if not adaptations:
                return original_response, {}
            
            user_id = adaptations[0].user_id
            adapters = self.user_adapters.get(user_id, {})
            
            modified_response = original_response
            interface_changes = {}
            
            # Apply response adaptations
            if 'response' in adapters:
                response_adapter = adapters['response']
                user_state = self._extract_user_state_from_frame(frame)
                modified_response = await response_adapter.adapt_response_style(
                    original_response, user_state, adaptations
                )
            
            # Apply interface adaptations
            interface_adaptations = [a for a in adaptations 
                                   if a.adaptation_type in [AdaptationType.INTERFACE_SIMPLIFICATION,
                                                          AdaptationType.COMPLEXITY_SCALING]]
            
            if interface_adaptations and 'interface' in adapters:
                interface_adapter = adapters['interface']
                
                for adaptation in interface_adaptations:
                    if adaptation.adaptation_type == AdaptationType.INTERFACE_SIMPLIFICATION:
                        complexity_level = InterfaceComplexityLevel(
                            adaptation.parameters.get('complexity_level', 'simple')
                        )
                        changes = await interface_adapter.adapt_interface_complexity(
                            complexity_level, {'adaptation_reason': adaptation.reasoning}
                        )
                        interface_changes.update(changes)
            
            # Track adaptation results
            for adaptation in adaptations:
                result = AdaptationResult(
                    success=True,
                    adaptation_id=f"{adaptation.adaptation_type.value}_{datetime.utcnow().timestamp()}",
                    applied_changes={
                        'response_modified': modified_response != original_response,
                        'interface_modified': bool(interface_changes)
                    },
                    user_feedback=None,  # Will be updated with user feedback
                    effectiveness_score=None,  # Will be calculated later
                    side_effects=[],
                    timestamp=datetime.utcnow()
                )
                
                self.adaptation_history[user_id].append(result)
            
            logger.info("Adaptations applied", 
                       user_id=user_id,
                       response_changed=modified_response != original_response,
                       interface_changes=len(interface_changes))
            
            return modified_response, interface_changes
            
        except Exception as e:
            logger.error("Adaptation application failed", error=str(e))
            return original_response, {}
    
    async def track_adaptation_effectiveness(self, 
                                           user_id: str,
                                           adaptation_id: str,
                                           user_feedback: Dict[str, Any],
                                           outcome_metrics: Dict[str, Any]) -> None:
        """Track the effectiveness of applied adaptations."""
        try:
            # Find the adaptation result
            for result in self.adaptation_history[user_id]:
                if result.adaptation_id == adaptation_id:
                    result.user_feedback = user_feedback
                    
                    # Calculate effectiveness score
                    effectiveness = 0.5  # Base score
                    
                    # Positive indicators
                    if user_feedback.get('task_completed', False):
                        effectiveness += 0.3
                    if user_feedback.get('reduced_stress', False):
                        effectiveness += 0.2
                    if user_feedback.get('improved_focus', False):
                        effectiveness += 0.2
                    
                    # Negative indicators
                    if user_feedback.get('confused', False):
                        effectiveness -= 0.3
                    if user_feedback.get('frustrated', False):
                        effectiveness -= 0.2
                    
                    # Outcome metrics
                    if outcome_metrics.get('completion_time'):
                        expected_time = outcome_metrics.get('expected_completion_time', 30)
                        actual_time = outcome_metrics['completion_time']
                        if actual_time <= expected_time:
                            effectiveness += 0.1
                        elif actual_time > expected_time * 1.5:
                            effectiveness -= 0.1
                    
                    result.effectiveness_score = max(0.0, min(1.0, effectiveness))
                    
                    # Update global effectiveness tracking
                    adaptation_type = adaptation_id.split('_')[0]
                    self.effectiveness_tracking[user_id][adaptation_type] = (
                        self.effectiveness_tracking[user_id].get(adaptation_type, 0.5) * 0.8 +
                        result.effectiveness_score * 0.2
                    )
                    
                    logger.info("Adaptation effectiveness tracked", 
                               user_id=user_id,
                               adaptation_id=adaptation_id,
                               effectiveness=result.effectiveness_score)
                    break
            
        except Exception as e:
            logger.error("Adaptation effectiveness tracking failed", error=str(e))
    
    async def _initialize_user_adapters(self, user_id: str) -> None:
        """Initialize adapters for a user."""
        self.user_adapters[user_id] = {
            'cognitive_load': CognitiveLoadAdapter(user_id),
            'interface': InterfaceAdapter(user_id),
            'response': ResponseAdapter(user_id)
        }
        
        logger.info("User adapters initialized", user_id=user_id)
    
    async def _process_pattern_adaptations(self, 
                                         patterns: List[PatternDetection],
                                         profile: Any,
                                         current_state: Dict[str, Any]) -> List[AdaptationDecision]:
        """Process detected patterns and generate adaptations."""
        adaptations = []
        
        try:
            for pattern in patterns:
                if pattern.pattern_type == PatternType.HYPERFOCUS:
                    # Suggest break reminders and time awareness
                    if pattern.severity in [PatternSeverity.HIGH, PatternSeverity.CRITICAL]:
                        adaptations.append(AdaptationDecision(
                            adaptation_type=AdaptationType.NUDGE_TIMING_ADJUSTMENT,
                            priority=AdaptationPriority.HIGH,
                            confidence=pattern.confidence,
                            reasoning="Hyperfocus detected - need break reminders",
                            parameters={
                                'break_reminder_frequency': 30,  # minutes
                                'time_awareness_nudges': True,
                                'gentle_interruption_style': True
                            },
                            expected_outcome="Healthier work patterns and time awareness",
                            rollback_criteria=["user_explicitly_rejects", "productivity_drops"],
                            timestamp=datetime.utcnow(),
                            user_id=profile.user_id
                        ))
                
                elif pattern.pattern_type == PatternType.EXECUTIVE_DYSFUNCTION:
                    # Simplify interface and provide more structure
                    adaptations.append(AdaptationDecision(
                        adaptation_type=AdaptationType.INTERFACE_SIMPLIFICATION,
                        priority=AdaptationPriority.HIGH,
                        confidence=pattern.confidence,
                        reasoning="Executive dysfunction - need simplified interface",
                        parameters={
                            'complexity_level': InterfaceComplexityLevel.SIMPLE.value,
                            'provide_structure': True,
                            'clear_next_steps': True
                        },
                        expected_outcome="Reduced decision fatigue and clearer action paths",
                        rollback_criteria=["user_needs_advanced_features", "task_complexity_increases"],
                        timestamp=datetime.utcnow(),
                        user_id=profile.user_id
                    ))
                
                elif pattern.pattern_type == PatternType.OVERWHELM:
                    # Critical adaptation - reduce everything
                    adaptations.append(AdaptationDecision(
                        adaptation_type=AdaptationType.COGNITIVE_LOAD_REDUCTION,
                        priority=AdaptationPriority.CRITICAL,
                        confidence=pattern.confidence,
                        reasoning="Overwhelm detected - emergency cognitive load reduction",
                        parameters={
                            'max_context_items': 3,
                            'response_length_limit': 50,
                            'simplify_language': True,
                            'emergency_mode': True
                        },
                        expected_outcome="Immediate cognitive load relief",
                        rollback_criteria=["overwhelm_subsides", "user_explicitly_requests"],
                        timestamp=datetime.utcnow(),
                        user_id=profile.user_id
                    ))
            
            return adaptations
            
        except Exception as e:
            logger.error("Pattern adaptation processing failed", error=str(e))
            return adaptations
    
    async def _assess_crisis_adaptations(self, 
                                       patterns: List[PatternDetection],
                                       current_state: Dict[str, Any]) -> List[AdaptationDecision]:
        """Assess need for crisis intervention adaptations."""
        adaptations = []
        
        try:
            # Check for crisis indicators
            crisis_patterns = [p for p in patterns if p.severity == PatternSeverity.CRITICAL]
            stress_level = current_state.get('stress_level', 0.0)
            
            if crisis_patterns or stress_level > 0.9:
                adaptations.append(AdaptationDecision(
                    adaptation_type=AdaptationType.CRISIS_PROTOCOL_ACTIVATION,
                    priority=AdaptationPriority.CRITICAL,
                    confidence=0.95,
                    reasoning="Crisis indicators detected - activating support protocol",
                    parameters={
                        'crisis_resources': True,
                        'simplified_interactions': True,
                        'emergency_contacts': True,
                        'calming_tone': True
                    },
                    expected_outcome="User safety and immediate support",
                    rollback_criteria=["crisis_resolved", "professional_help_engaged"],
                    timestamp=datetime.utcnow(),
                    user_id=current_state.get('user_id', 'unknown')
                ))
            
            return adaptations
            
        except Exception as e:
            logger.error("Crisis adaptation assessment failed", error=str(e))
            return []
    
    def _extract_user_state_from_frame(self, frame: MCPFrame) -> Dict[str, Any]:
        """Extract user state information from MCP frame."""
        user_state = {'user_id': frame.user_id}
        
        for context in frame.context:
            if context.type.value == 'user_state':
                user_state.update(context.data)
        
        return user_state
    
    def get_adaptation_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of adaptations for user insights."""
        try:
            if user_id not in self.adaptation_history:
                return {'no_adaptations': True}
            
            results = self.adaptation_history[user_id]
            effectiveness_scores = [r.effectiveness_score for r in results 
                                  if r.effectiveness_score is not None]
            
            return {
                'total_adaptations': len(results),
                'recent_adaptations': len([r for r in results 
                                         if r.timestamp > datetime.utcnow() - timedelta(hours=24)]),
                'average_effectiveness': sum(effectiveness_scores) / len(effectiveness_scores) if effectiveness_scores else None,
                'adaptation_types': list(self.effectiveness_tracking[user_id].keys()),
                'most_effective_adaptation': max(self.effectiveness_tracking[user_id].items(), 
                                               key=lambda x: x[1])[0] if self.effectiveness_tracking[user_id] else None
            }
            
        except Exception as e:
            logger.error("Adaptation summary generation failed", error=str(e))
            return {'error': str(e)}


# Global adaptation engine
adaptation_engine = AdaptationEngine()