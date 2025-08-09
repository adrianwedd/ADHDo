"""
Advanced ADHD Pattern Recognition Engine.

This module implements sophisticated behavioral pattern analysis specifically designed
for ADHD users, including hyperfocus detection, executive dysfunction prediction,
time blindness compensation, and emotional dysregulation intervention.

Core Features:
- Real-time behavioral pattern analysis and learning
- Hyperfocus episode detection and management
- Executive dysfunction early warning system
- Time blindness compensation with predictive modeling
- Emotional dysregulation pattern recognition and intervention
- ADHD subtype classification (Inattentive, Hyperactive, Combined)

The system uses machine learning techniques adapted for neurodivergent patterns
while maintaining privacy-first processing and user autonomy.
"""
import asyncio
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict, deque

import structlog
import numpy as np
from pydantic import BaseModel
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from mcp_server.models import TraceMemory as TraceMemoryModel
from traces.memory import trace_memory

logger = structlog.get_logger()


class ADHDSubtype(Enum):
    """ADHD subtypes for personalized support."""
    PREDOMINANTLY_INATTENTIVE = "inattentive"
    PREDOMINANTLY_HYPERACTIVE_IMPULSIVE = "hyperactive"
    COMBINED_PRESENTATION = "combined"
    UNSPECIFIED = "unspecified"


class PatternType(Enum):
    """Types of ADHD behavioral patterns."""
    HYPERFOCUS = "hyperfocus"
    EXECUTIVE_DYSFUNCTION = "executive_dysfunction"
    TIME_BLINDNESS = "time_blindness"
    EMOTIONAL_DYSREGULATION = "emotional_dysregulation"
    PROCRASTINATION = "procrastination"
    TASK_SWITCHING = "task_switching"
    ENERGY_PATTERN = "energy_pattern"
    OVERWHELM = "overwhelm"


class PatternSeverity(Enum):
    """Severity levels for pattern intervention."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PatternDetection:
    """Result of pattern analysis."""
    pattern_type: PatternType
    severity: PatternSeverity
    confidence: float
    evidence: Dict[str, Any]
    intervention_recommended: bool
    intervention_urgency: int  # 1-10 scale
    timestamp: datetime


class BehavioralMetrics(BaseModel):
    """Behavioral metrics for pattern analysis."""
    session_duration: float  # minutes
    task_switching_frequency: float  # switches per hour
    response_delay: float  # minutes to respond to nudges
    completion_rate: float  # 0.0-1.0
    hyperfocus_indicators: List[str]
    stress_markers: List[str]
    energy_level: float  # 0.0-1.0
    time_estimation_accuracy: float  # ratio of estimated vs actual
    interruption_frequency: float  # interruptions per hour
    emotional_volatility: float  # 0.0-1.0


class ADHDPatternEngine:
    """
    Advanced pattern recognition engine for ADHD behavioral analysis.
    
    This engine analyzes user behavior patterns to provide personalized
    interventions and support strategies tailored to individual ADHD
    presentation and needs.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.pattern_history: deque = deque(maxlen=1000)  # Rolling pattern history
        self.baseline_metrics: Dict[str, float] = {}
        self.personalization_data: Dict[str, Any] = {}
        self.intervention_effectiveness: Dict[str, float] = defaultdict(float)
        self.adhd_subtype: ADHDSubtype = ADHDSubtype.UNSPECIFIED
        self.pattern_thresholds: Dict[PatternType, Dict[str, float]] = self._initialize_thresholds()
        
        # Machine learning components
        self.scaler = StandardScaler()
        self.clustering_model = None
        self.pattern_vectors: List[List[float]] = []
        
        # Real-time pattern tracking
        self.current_session_start: Optional[datetime] = None
        self.current_focus_depth: float = 0.0
        self.recent_interactions: deque = deque(maxlen=50)
        
        logger.info("Initialized ADHD Pattern Engine", user_id=user_id)
    
    async def analyze_realtime_behavior(self, 
                                       interaction_data: Dict[str, Any]) -> List[PatternDetection]:
        """
        Analyze real-time behavior for immediate pattern detection.
        
        Args:
            interaction_data: Current interaction details including timing,
                            content, user state, and context
        
        Returns:
            List of detected patterns requiring immediate attention
        """
        patterns_detected = []
        
        try:
            # Update recent interaction history
            self.recent_interactions.append({
                **interaction_data,
                'timestamp': datetime.utcnow()
            })
            
            # Extract behavioral metrics
            metrics = await self._extract_behavioral_metrics()
            
            # Detect hyperfocus patterns
            hyperfocus_pattern = await self._detect_hyperfocus(metrics, interaction_data)
            if hyperfocus_pattern:
                patterns_detected.append(hyperfocus_pattern)
            
            # Detect executive dysfunction
            executive_pattern = await self._detect_executive_dysfunction(metrics)
            if executive_pattern:
                patterns_detected.append(executive_pattern)
            
            # Detect time blindness
            time_pattern = await self._detect_time_blindness(metrics, interaction_data)
            if time_pattern:
                patterns_detected.append(time_pattern)
            
            # Detect emotional dysregulation
            emotional_pattern = await self._detect_emotional_dysregulation(metrics)
            if emotional_pattern:
                patterns_detected.append(emotional_pattern)
            
            # Detect overwhelm patterns
            overwhelm_pattern = await self._detect_overwhelm(metrics, interaction_data)
            if overwhelm_pattern:
                patterns_detected.append(overwhelm_pattern)
            
            # Update pattern history for learning
            for pattern in patterns_detected:
                self.pattern_history.append(pattern)
                await self._log_pattern_detection(pattern)
            
            # Update baseline metrics adaptively
            await self._update_baseline_metrics(metrics)
            
            logger.info("Real-time pattern analysis completed", 
                       user_id=self.user_id,
                       patterns_found=len(patterns_detected))
            
            return patterns_detected
            
        except Exception as e:
            logger.error("Real-time behavior analysis failed", 
                        user_id=self.user_id, error=str(e))
            return []
    
    async def _detect_hyperfocus(self, 
                                metrics: BehavioralMetrics, 
                                interaction_data: Dict[str, Any]) -> Optional[PatternDetection]:
        """
        Detect hyperfocus episodes using multiple behavioral indicators.
        
        Hyperfocus indicators:
        - Extended session duration without breaks
        - Decreased response to external stimuli (nudges, messages)
        - High task engagement with single focus
        - Loss of time awareness
        - Delayed responses to non-task communications
        """
        try:
            # Check for extended session duration
            session_duration = metrics.session_duration
            if session_duration > 180:  # 3+ hours
                hyperfocus_score = min(session_duration / 240, 1.0)  # Normalize to 4 hours
            else:
                hyperfocus_score = 0.0
            
            # Check response delay patterns
            if metrics.response_delay > 30:  # 30+ minute delays
                hyperfocus_score += 0.3
            
            # Check task switching frequency (hyperfocus = low switching)
            if metrics.task_switching_frequency < 0.5:  # Less than 0.5 switches per hour
                hyperfocus_score += 0.3
            
            # Check for time estimation inaccuracy
            if metrics.time_estimation_accuracy < 0.3:  # Severely underestimating time
                hyperfocus_score += 0.2
            
            # Analyze interaction patterns
            recent_interactions = list(self.recent_interactions)
            if len(recent_interactions) >= 3:
                time_gaps = []
                for i in range(1, len(recent_interactions)):
                    gap = (recent_interactions[i]['timestamp'] - 
                          recent_interactions[i-1]['timestamp']).total_seconds() / 60
                    time_gaps.append(gap)
                
                # Large gaps between interactions suggest deep focus
                if time_gaps and max(time_gaps) > 60:  # 1+ hour gaps
                    hyperfocus_score += 0.2
            
            # Determine severity
            if hyperfocus_score >= 0.8:
                severity = PatternSeverity.HIGH
                intervention_urgency = 8
            elif hyperfocus_score >= 0.6:
                severity = PatternSeverity.MODERATE
                intervention_urgency = 6
            elif hyperfocus_score >= 0.4:
                severity = PatternSeverity.LOW
                intervention_urgency = 4
            else:
                return None
            
            return PatternDetection(
                pattern_type=PatternType.HYPERFOCUS,
                severity=severity,
                confidence=min(hyperfocus_score, 1.0),
                evidence={
                    'session_duration': session_duration,
                    'response_delay': metrics.response_delay,
                    'task_switching_frequency': metrics.task_switching_frequency,
                    'time_estimation_accuracy': metrics.time_estimation_accuracy,
                    'max_interaction_gap': max(time_gaps) if time_gaps else 0
                },
                intervention_recommended=hyperfocus_score >= 0.6,
                intervention_urgency=intervention_urgency,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.warning("Hyperfocus detection failed", error=str(e))
            return None
    
    async def _detect_executive_dysfunction(self, 
                                          metrics: BehavioralMetrics) -> Optional[PatternDetection]:
        """
        Detect executive dysfunction patterns including task initiation difficulty,
        working memory issues, and cognitive flexibility problems.
        """
        try:
            dysfunction_score = 0.0
            evidence = {}
            
            # Task completion issues
            if metrics.completion_rate < 0.3:
                dysfunction_score += 0.4
                evidence['low_completion_rate'] = metrics.completion_rate
            
            # High task switching without completion
            if metrics.task_switching_frequency > 3.0 and metrics.completion_rate < 0.5:
                dysfunction_score += 0.3
                evidence['excessive_switching'] = metrics.task_switching_frequency
            
            # Response delays suggesting processing difficulties
            if metrics.response_delay > 15:  # 15+ minute delays consistently
                dysfunction_score += 0.2
                evidence['processing_delays'] = metrics.response_delay
            
            # High interruption frequency affecting working memory
            if metrics.interruption_frequency > 2.0:  # 2+ interruptions per hour
                dysfunction_score += 0.2
                evidence['high_interruptions'] = metrics.interruption_frequency
            
            # Low energy affecting executive function
            if metrics.energy_level < 0.3:
                dysfunction_score += 0.1
                evidence['low_energy'] = metrics.energy_level
            
            if dysfunction_score < 0.3:
                return None
            
            # Determine severity
            if dysfunction_score >= 0.8:
                severity = PatternSeverity.CRITICAL
                intervention_urgency = 9
            elif dysfunction_score >= 0.6:
                severity = PatternSeverity.HIGH
                intervention_urgency = 7
            elif dysfunction_score >= 0.4:
                severity = PatternSeverity.MODERATE
                intervention_urgency = 5
            else:
                severity = PatternSeverity.LOW
                intervention_urgency = 3
            
            return PatternDetection(
                pattern_type=PatternType.EXECUTIVE_DYSFUNCTION,
                severity=severity,
                confidence=min(dysfunction_score, 1.0),
                evidence=evidence,
                intervention_recommended=dysfunction_score >= 0.4,
                intervention_urgency=intervention_urgency,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.warning("Executive dysfunction detection failed", error=str(e))
            return None
    
    async def _detect_time_blindness(self, 
                                   metrics: BehavioralMetrics, 
                                   interaction_data: Dict[str, Any]) -> Optional[PatternDetection]:
        """
        Detect time blindness patterns including poor time estimation,
        lost track of time, and temporal processing difficulties.
        """
        try:
            time_blindness_score = 0.0
            evidence = {}
            
            # Poor time estimation accuracy
            if metrics.time_estimation_accuracy < 0.4:
                time_blindness_score += 0.4
                evidence['time_estimation_accuracy'] = metrics.time_estimation_accuracy
            
            # Session durations vastly different from estimates
            expected_duration = interaction_data.get('expected_duration', 0)
            actual_duration = metrics.session_duration
            
            if expected_duration > 0:
                duration_ratio = actual_duration / expected_duration
                if duration_ratio > 2.0 or duration_ratio < 0.5:  # Off by 2x either way
                    time_blindness_score += 0.3
                    evidence['duration_estimation_error'] = abs(1.0 - duration_ratio)
            
            # Missed scheduled events or reminders
            scheduled_events = interaction_data.get('missed_events', 0)
            if scheduled_events > 0:
                time_blindness_score += min(scheduled_events * 0.2, 0.3)
                evidence['missed_events'] = scheduled_events
            
            # Late responses to time-sensitive items
            urgency_responses = interaction_data.get('urgent_response_delays', [])
            if urgency_responses:
                avg_delay = sum(urgency_responses) / len(urgency_responses)
                if avg_delay > 30:  # 30+ minutes for urgent items
                    time_blindness_score += 0.2
                    evidence['urgent_response_delay'] = avg_delay
            
            if time_blindness_score < 0.3:
                return None
            
            # Determine severity
            if time_blindness_score >= 0.8:
                severity = PatternSeverity.HIGH
                intervention_urgency = 7
            elif time_blindness_score >= 0.5:
                severity = PatternSeverity.MODERATE
                intervention_urgency = 5
            else:
                severity = PatternSeverity.LOW
                intervention_urgency = 3
            
            return PatternDetection(
                pattern_type=PatternType.TIME_BLINDNESS,
                severity=severity,
                confidence=min(time_blindness_score, 1.0),
                evidence=evidence,
                intervention_recommended=time_blindness_score >= 0.4,
                intervention_urgency=intervention_urgency,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.warning("Time blindness detection failed", error=str(e))
            return None
    
    async def _detect_emotional_dysregulation(self, 
                                             metrics: BehavioralMetrics) -> Optional[PatternDetection]:
        """
        Detect emotional dysregulation patterns including mood swings,
        frustration spikes, and emotional overwhelm.
        """
        try:
            dysregulation_score = 0.0
            evidence = {}
            
            # High emotional volatility
            if metrics.emotional_volatility > 0.7:
                dysregulation_score += 0.4
                evidence['emotional_volatility'] = metrics.emotional_volatility
            
            # Stress markers present
            if metrics.stress_markers:
                stress_intensity = len(metrics.stress_markers) / 5.0  # Normalize to 5 markers
                dysregulation_score += min(stress_intensity * 0.3, 0.3)
                evidence['stress_markers'] = metrics.stress_markers
            
            # Energy crashes following high periods
            if hasattr(self, '_previous_energy') and self._previous_energy:
                energy_drop = self._previous_energy - metrics.energy_level
                if energy_drop > 0.5:  # Significant energy crash
                    dysregulation_score += 0.2
                    evidence['energy_crash'] = energy_drop
            
            # Frustration patterns from interaction history
            recent_frustration = 0
            for interaction in list(self.recent_interactions)[-10:]:
                if any(marker in interaction.get('content', '').lower() 
                      for marker in ['frustrated', 'angry', 'overwhelmed', 'stressed']):
                    recent_frustration += 1
            
            if recent_frustration >= 3:
                dysregulation_score += 0.3
                evidence['frustration_indicators'] = recent_frustration
            
            if dysregulation_score < 0.3:
                return None
            
            # Determine severity
            if dysregulation_score >= 0.9:
                severity = PatternSeverity.CRITICAL
                intervention_urgency = 10
            elif dysregulation_score >= 0.7:
                severity = PatternSeverity.HIGH
                intervention_urgency = 8
            elif dysregulation_score >= 0.5:
                severity = PatternSeverity.MODERATE
                intervention_urgency = 6
            else:
                severity = PatternSeverity.LOW
                intervention_urgency = 4
            
            return PatternDetection(
                pattern_type=PatternType.EMOTIONAL_DYSREGULATION,
                severity=severity,
                confidence=min(dysregulation_score, 1.0),
                evidence=evidence,
                intervention_recommended=dysregulation_score >= 0.5,
                intervention_urgency=intervention_urgency,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.warning("Emotional dysregulation detection failed", error=str(e))
            return None
    
    async def _detect_overwhelm(self, 
                               metrics: BehavioralMetrics, 
                               interaction_data: Dict[str, Any]) -> Optional[PatternDetection]:
        """
        Detect cognitive and emotional overwhelm patterns that require
        immediate intervention to prevent shutdown.
        """
        try:
            overwhelm_score = 0.0
            evidence = {}
            
            # High interruption frequency
            if metrics.interruption_frequency > 3.0:
                overwhelm_score += 0.3
                evidence['high_interruptions'] = metrics.interruption_frequency
            
            # Multiple high-urgency items
            urgent_items = interaction_data.get('urgent_items_count', 0)
            if urgent_items >= 3:
                overwhelm_score += 0.3
                evidence['urgent_items'] = urgent_items
            
            # Cognitive load exceeding capacity
            cognitive_load = interaction_data.get('cognitive_load', 0.5)
            if cognitive_load > 0.8:
                overwhelm_score += 0.4
                evidence['high_cognitive_load'] = cognitive_load
            
            # Decreased task completion with increased switching
            if (metrics.completion_rate < 0.2 and 
                metrics.task_switching_frequency > 4.0):
                overwhelm_score += 0.3
                evidence['completion_switching_pattern'] = {
                    'completion_rate': metrics.completion_rate,
                    'switching_frequency': metrics.task_switching_frequency
                }
            
            # Physical/emotional stress indicators
            if len(metrics.stress_markers) >= 3:
                overwhelm_score += 0.2
                evidence['multiple_stress_markers'] = metrics.stress_markers
            
            if overwhelm_score < 0.4:
                return None
            
            # Overwhelm is always high priority
            if overwhelm_score >= 0.8:
                severity = PatternSeverity.CRITICAL
                intervention_urgency = 10
            elif overwhelm_score >= 0.6:
                severity = PatternSeverity.HIGH
                intervention_urgency = 9
            else:
                severity = PatternSeverity.MODERATE
                intervention_urgency = 7
            
            return PatternDetection(
                pattern_type=PatternType.OVERWHELM,
                severity=severity,
                confidence=min(overwhelm_score, 1.0),
                evidence=evidence,
                intervention_recommended=True,  # Always recommend intervention
                intervention_urgency=intervention_urgency,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.warning("Overwhelm detection failed", error=str(e))
            return None
    
    async def classify_adhd_subtype(self) -> ADHDSubtype:
        """
        Classify user's ADHD subtype based on behavioral patterns.
        
        This uses longitudinal pattern analysis to determine the
        predominant presentation type for personalized interventions.
        """
        try:
            # Get historical pattern data
            inattentive_patterns = 0
            hyperactive_patterns = 0
            combined_indicators = 0
            
            for pattern in self.pattern_history:
                if pattern.pattern_type in [PatternType.HYPERFOCUS, PatternType.TIME_BLINDNESS]:
                    inattentive_patterns += 1
                elif pattern.pattern_type in [PatternType.TASK_SWITCHING, PatternType.EMOTIONAL_DYSREGULATION]:
                    hyperactive_patterns += 1
                
                # Combined indicators
                if pattern.pattern_type in [PatternType.EXECUTIVE_DYSFUNCTION, PatternType.OVERWHELM]:
                    combined_indicators += 1
            
            total_patterns = len(self.pattern_history)
            if total_patterns < 10:
                return ADHDSubtype.UNSPECIFIED
            
            inattentive_ratio = inattentive_patterns / total_patterns
            hyperactive_ratio = hyperactive_patterns / total_patterns
            combined_ratio = combined_indicators / total_patterns
            
            # Classification logic
            if combined_ratio > 0.4 or (inattentive_ratio > 0.3 and hyperactive_ratio > 0.3):
                subtype = ADHDSubtype.COMBINED_PRESENTATION
            elif inattentive_ratio > hyperactive_ratio and inattentive_ratio > 0.3:
                subtype = ADHDSubtype.PREDOMINANTLY_INATTENTIVE
            elif hyperactive_ratio > 0.3:
                subtype = ADHDSubtype.PREDOMINANTLY_HYPERACTIVE_IMPULSIVE
            else:
                subtype = ADHDSubtype.UNSPECIFIED
            
            self.adhd_subtype = subtype
            logger.info("ADHD subtype classified", 
                       user_id=self.user_id, 
                       subtype=subtype.value,
                       confidence_data={
                           'inattentive_ratio': inattentive_ratio,
                           'hyperactive_ratio': hyperactive_ratio,
                           'combined_ratio': combined_ratio,
                           'total_patterns': total_patterns
                       })
            
            return subtype
            
        except Exception as e:
            logger.error("ADHD subtype classification failed", 
                        user_id=self.user_id, error=str(e))
            return ADHDSubtype.UNSPECIFIED
    
    async def _extract_behavioral_metrics(self) -> BehavioralMetrics:
        """Extract behavioral metrics from recent interaction history."""
        try:
            if not self.recent_interactions:
                return BehavioralMetrics(
                    session_duration=0.0,
                    task_switching_frequency=0.0,
                    response_delay=0.0,
                    completion_rate=0.0,
                    hyperfocus_indicators=[],
                    stress_markers=[],
                    energy_level=0.5,
                    time_estimation_accuracy=0.5,
                    interruption_frequency=0.0,
                    emotional_volatility=0.0
                )
            
            interactions = list(self.recent_interactions)
            
            # Session duration calculation
            if len(interactions) >= 2:
                session_start = interactions[0]['timestamp']
                session_end = interactions[-1]['timestamp']
                session_duration = (session_end - session_start).total_seconds() / 60.0
            else:
                session_duration = 5.0  # Default 5 minutes
            
            # Task switching frequency
            task_switches = 0
            current_task = None
            for interaction in interactions:
                task_focus = interaction.get('task_focus')
                if task_focus and task_focus != current_task:
                    task_switches += 1
                    current_task = task_focus
            
            task_switching_frequency = task_switches / max(session_duration / 60.0, 0.1)
            
            # Response delay (average)
            response_delays = []
            for i, interaction in enumerate(interactions):
                if i > 0:
                    delay = (interaction['timestamp'] - 
                           interactions[i-1]['timestamp']).total_seconds() / 60.0
                    response_delays.append(delay)
            
            avg_response_delay = statistics.mean(response_delays) if response_delays else 0.0
            
            # Completion indicators
            completed_tasks = sum(1 for interaction in interactions 
                                if interaction.get('task_completed', False))
            completion_rate = completed_tasks / max(len(interactions), 1)
            
            # Extract other metrics from interaction content
            hyperfocus_indicators = []
            stress_markers = []
            energy_indicators = []
            
            for interaction in interactions:
                content = interaction.get('content', '').lower()
                
                # Hyperfocus indicators
                if any(indicator in content for indicator in 
                      ['lost track of time', 'been working for hours', 'forgot to eat']):
                    hyperfocus_indicators.append('time_loss')
                if 'interrupted' in content or 'distracted' in content:
                    hyperfocus_indicators.append('resistance_to_interruption')
                
                # Stress markers
                if any(marker in content for marker in 
                      ['stressed', 'overwhelmed', 'anxious', 'frustrated']):
                    stress_markers.append('verbal_stress_indication')
                
                # Energy indicators
                if any(indicator in content for indicator in 
                      ['tired', 'exhausted', 'drained']):
                    energy_indicators.append('low_energy')
                elif any(indicator in content for indicator in 
                        ['energized', 'motivated', 'ready']):
                    energy_indicators.append('high_energy')
            
            # Calculate energy level
            low_energy_count = sum(1 for ind in energy_indicators if ind == 'low_energy')
            high_energy_count = sum(1 for ind in energy_indicators if ind == 'high_energy')
            total_energy_indicators = low_energy_count + high_energy_count
            
            if total_energy_indicators > 0:
                energy_level = high_energy_count / total_energy_indicators
            else:
                energy_level = 0.5  # Neutral
            
            # Emotional volatility (based on sentiment changes)
            emotional_scores = []
            for interaction in interactions[-10:]:  # Last 10 interactions
                content = interaction.get('content', '').lower()
                score = 0.5  # Neutral baseline
                
                # Simple sentiment scoring
                if any(pos in content for pos in ['good', 'great', 'excellent', 'happy']):
                    score += 0.3
                if any(neg in content for neg in ['bad', 'terrible', 'awful', 'sad']):
                    score -= 0.3
                
                emotional_scores.append(max(0.0, min(1.0, score)))
            
            emotional_volatility = statistics.stdev(emotional_scores) if len(emotional_scores) > 1 else 0.0
            
            return BehavioralMetrics(
                session_duration=session_duration,
                task_switching_frequency=task_switching_frequency,
                response_delay=avg_response_delay,
                completion_rate=completion_rate,
                hyperfocus_indicators=list(set(hyperfocus_indicators)),
                stress_markers=list(set(stress_markers)),
                energy_level=energy_level,
                time_estimation_accuracy=0.5,  # TODO: Implement time estimation tracking
                interruption_frequency=len([i for i in interactions 
                                          if 'interrupted' in i.get('content', '').lower()]) / 
                                        max(session_duration / 60.0, 0.1),
                emotional_volatility=emotional_volatility
            )
            
        except Exception as e:
            logger.error("Behavioral metrics extraction failed", error=str(e))
            # Return safe defaults
            return BehavioralMetrics(
                session_duration=0.0,
                task_switching_frequency=0.0,
                response_delay=0.0,
                completion_rate=0.0,
                hyperfocus_indicators=[],
                stress_markers=[],
                energy_level=0.5,
                time_estimation_accuracy=0.5,
                interruption_frequency=0.0,
                emotional_volatility=0.0
            )
    
    async def _update_baseline_metrics(self, metrics: BehavioralMetrics) -> None:
        """Update baseline metrics for personalized thresholds."""
        try:
            # Update baseline with exponential moving average
            alpha = 0.1  # Learning rate
            
            current_baselines = {
                'session_duration': metrics.session_duration,
                'task_switching_frequency': metrics.task_switching_frequency,
                'response_delay': metrics.response_delay,
                'completion_rate': metrics.completion_rate,
                'energy_level': metrics.energy_level,
                'emotional_volatility': metrics.emotional_volatility
            }
            
            for metric, value in current_baselines.items():
                if metric in self.baseline_metrics:
                    self.baseline_metrics[metric] = (
                        (1 - alpha) * self.baseline_metrics[metric] + 
                        alpha * value
                    )
                else:
                    self.baseline_metrics[metric] = value
            
            # Store previous energy for crash detection
            self._previous_energy = metrics.energy_level
            
        except Exception as e:
            logger.warning("Baseline metrics update failed", error=str(e))
    
    async def _log_pattern_detection(self, pattern: PatternDetection) -> None:
        """Log pattern detection to trace memory for learning."""
        try:
            trace_record = TraceMemoryModel(
                user_id=self.user_id,
                event_type="pattern_detection",
                event_data={
                    "pattern_type": pattern.pattern_type.value,
                    "severity": pattern.severity.value,
                    "confidence": pattern.confidence,
                    "evidence": pattern.evidence,
                    "intervention_recommended": pattern.intervention_recommended,
                    "intervention_urgency": pattern.intervention_urgency,
                    "adhd_subtype": self.adhd_subtype.value
                },
                confidence=pattern.confidence,
                source="pattern_engine"
            )
            
            await trace_memory.store_trace(trace_record)
            
        except Exception as e:
            logger.error("Pattern detection logging failed", error=str(e))
    
    def _initialize_thresholds(self) -> Dict[PatternType, Dict[str, float]]:
        """Initialize pattern detection thresholds."""
        return {
            PatternType.HYPERFOCUS: {
                'session_duration_threshold': 180.0,  # 3 hours
                'response_delay_threshold': 30.0,  # 30 minutes
                'task_switching_threshold': 0.5  # switches per hour
            },
            PatternType.EXECUTIVE_DYSFUNCTION: {
                'completion_rate_threshold': 0.3,
                'switching_frequency_threshold': 3.0,
                'response_delay_threshold': 15.0
            },
            PatternType.TIME_BLINDNESS: {
                'estimation_accuracy_threshold': 0.4,
                'duration_ratio_threshold': 2.0
            },
            PatternType.EMOTIONAL_DYSREGULATION: {
                'volatility_threshold': 0.7,
                'energy_crash_threshold': 0.5
            },
            PatternType.OVERWHELM: {
                'interruption_threshold': 3.0,
                'cognitive_load_threshold': 0.8,
                'urgent_items_threshold': 3
            }
        }
    
    def get_pattern_summary(self) -> Dict[str, Any]:
        """Get summary of detected patterns for user insights."""
        try:
            pattern_counts = defaultdict(int)
            recent_patterns = []
            
            # Analyze pattern history
            for pattern in list(self.pattern_history)[-50:]:  # Last 50 patterns
                pattern_counts[pattern.pattern_type.value] += 1
                if pattern.timestamp > datetime.utcnow() - timedelta(hours=24):
                    recent_patterns.append({
                        'type': pattern.pattern_type.value,
                        'severity': pattern.severity.value,
                        'confidence': pattern.confidence,
                        'timestamp': pattern.timestamp.isoformat()
                    })
            
            return {
                'adhd_subtype': self.adhd_subtype.value,
                'pattern_counts': dict(pattern_counts),
                'recent_patterns': recent_patterns,
                'baseline_metrics': self.baseline_metrics,
                'total_patterns_detected': len(self.pattern_history),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Pattern summary generation failed", error=str(e))
            return {'error': str(e)}


# Factory function for pattern engines
_pattern_engines: Dict[str, ADHDPatternEngine] = {}

def get_pattern_engine(user_id: str) -> ADHDPatternEngine:
    """Get or create pattern engine for user."""
    if user_id not in _pattern_engines:
        _pattern_engines[user_id] = ADHDPatternEngine(user_id)
    return _pattern_engines[user_id]