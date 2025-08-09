"""
Unit tests for ADHD Pattern Recognition Engine.

Tests the core pattern recognition functionality including hyperfocus detection,
executive dysfunction identification, time blindness patterns, and emotional
dysregulation recognition.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from adhd.pattern_engine import (
    ADHDPatternEngine, PatternType, PatternSeverity, PatternDetection,
    ADHDSubtype, BehavioralMetrics
)


class TestADHDPatternEngine:
    """Test suite for ADHD Pattern Recognition Engine."""
    
    @pytest.fixture
    def pattern_engine(self):
        """Create pattern engine for testing."""
        return ADHDPatternEngine("test_user")
    
    @pytest.fixture
    def sample_interaction_data(self):
        """Sample interaction data for testing."""
        return {
            'content': 'I have been working on this task for 3 hours straight',
            'cognitive_load': 0.7,
            'task_focus': 'coding project',
            'session_duration_minutes': 180,
            'energy_level': 0.8,
            'timestamp': datetime.utcnow(),
            'response_delay_minutes': 45,
            'task_switches_per_hour': 0.3,
            'completion_rate': 0.9,
            'time_estimation_accuracy': 0.2,
            'interruption_frequency': 0.1
        }
    
    @pytest.mark.asyncio
    async def test_hyperfocus_detection_high_severity(self, pattern_engine, sample_interaction_data):
        """Test detection of high-severity hyperfocus pattern."""
        # Modify data to trigger hyperfocus
        sample_interaction_data.update({
            'session_duration_minutes': 240,  # 4 hours
            'response_delay_minutes': 60,     # 1 hour delay
            'task_switches_per_hour': 0.2,    # Very low switching
            'time_estimation_accuracy': 0.1   # Poor time estimation
        })
        
        patterns = await pattern_engine.analyze_realtime_behavior(sample_interaction_data)
        
        hyperfocus_patterns = [p for p in patterns if p.pattern_type == PatternType.HYPERFOCUS]
        assert len(hyperfocus_patterns) > 0
        
        pattern = hyperfocus_patterns[0]
        assert pattern.severity == PatternSeverity.HIGH
        assert pattern.confidence > 0.6
        assert pattern.intervention_recommended
        assert pattern.intervention_urgency >= 6
        assert 'session_duration' in pattern.evidence
    
    @pytest.mark.asyncio
    async def test_executive_dysfunction_detection(self, pattern_engine, sample_interaction_data):
        """Test detection of executive dysfunction patterns."""
        sample_interaction_data.update({
            'completion_rate': 0.2,           # Very low completion
            'task_switches_per_hour': 4.0,    # High switching
            'response_delay_minutes': 20,     # Processing delays
            'interruption_frequency': 3.0,    # High interruptions
            'energy_level': 0.2               # Low energy
        })
        
        patterns = await pattern_engine.analyze_realtime_behavior(sample_interaction_data)
        
        dysfunction_patterns = [p for p in patterns if p.pattern_type == PatternType.EXECUTIVE_DYSFUNCTION]
        assert len(dysfunction_patterns) > 0
        
        pattern = dysfunction_patterns[0]
        assert pattern.severity in [PatternSeverity.MODERATE, PatternSeverity.HIGH, PatternSeverity.CRITICAL]
        assert pattern.intervention_recommended
        assert 'low_completion_rate' in pattern.evidence
    
    @pytest.mark.asyncio
    async def test_time_blindness_detection(self, pattern_engine, sample_interaction_data):
        """Test detection of time blindness patterns."""
        sample_interaction_data.update({
            'time_estimation_accuracy': 0.3,  # Poor time estimation
            'expected_duration': 30,          # Expected 30 minutes
            'actual_duration': 90,            # Took 90 minutes
            'missed_events': 2,               # Missed scheduled events
            'urgent_response_delays': [45, 60, 30]  # Delays for urgent items
        })
        
        patterns = await pattern_engine.analyze_realtime_behavior(sample_interaction_data)
        
        time_patterns = [p for p in patterns if p.pattern_type == PatternType.TIME_BLINDNESS]
        assert len(time_patterns) > 0
        
        pattern = time_patterns[0]
        assert pattern.confidence > 0.3
        assert 'time_estimation_accuracy' in pattern.evidence
    
    @pytest.mark.asyncio
    async def test_emotional_dysregulation_detection(self, pattern_engine, sample_interaction_data):
        """Test detection of emotional dysregulation patterns."""
        sample_interaction_data.update({
            'emotional_volatility': 0.8,      # High volatility
            'stress_indicators': ['frustrated', 'overwhelmed', 'angry'],
            'energy_level': 0.2,              # Energy crash
            'content': 'I am so frustrated with this task, it is overwhelming'
        })
        
        # Set previous energy for crash detection
        pattern_engine._previous_energy = 0.8
        
        patterns = await pattern_engine.analyze_realtime_behavior(sample_interaction_data)
        
        emotional_patterns = [p for p in patterns if p.pattern_type == PatternType.EMOTIONAL_DYSREGULATION]
        assert len(emotional_patterns) > 0
        
        pattern = emotional_patterns[0]
        assert pattern.severity in [PatternSeverity.MODERATE, PatternSeverity.HIGH, PatternSeverity.CRITICAL]
        assert pattern.intervention_recommended
        assert 'emotional_volatility' in pattern.evidence
    
    @pytest.mark.asyncio
    async def test_overwhelm_detection(self, pattern_engine, sample_interaction_data):
        """Test detection of overwhelm patterns."""
        sample_interaction_data.update({
            'interruption_frequency': 4.0,    # High interruptions
            'urgent_items_count': 5,          # Many urgent items
            'cognitive_load': 0.9,            # Very high cognitive load
            'completion_rate': 0.1,           # Very low completion
            'task_switches_per_hour': 5.0,    # Excessive switching
            'stress_indicators': ['overwhelmed', 'stressed', 'anxious']
        })
        
        patterns = await pattern_engine.analyze_realtime_behavior(sample_interaction_data)
        
        overwhelm_patterns = [p for p in patterns if p.pattern_type == PatternType.OVERWHELM]
        assert len(overwhelm_patterns) > 0
        
        pattern = overwhelm_patterns[0]
        assert pattern.severity in [PatternSeverity.HIGH, PatternSeverity.CRITICAL]
        assert pattern.intervention_recommended
        assert pattern.intervention_urgency >= 7
    
    @pytest.mark.asyncio
    async def test_adhd_subtype_classification_inattentive(self, pattern_engine):
        """Test ADHD subtype classification for predominantly inattentive type."""
        # Simulate pattern history for inattentive type
        for _ in range(15):
            pattern_engine.pattern_history.append(PatternDetection(
                pattern_type=PatternType.HYPERFOCUS,
                severity=PatternSeverity.MODERATE,
                confidence=0.7,
                evidence={},
                intervention_recommended=True,
                intervention_urgency=5,
                timestamp=datetime.utcnow()
            ))
            
        for _ in range(10):
            pattern_engine.pattern_history.append(PatternDetection(
                pattern_type=PatternType.TIME_BLINDNESS,
                severity=PatternSeverity.MODERATE,
                confidence=0.6,
                evidence={},
                intervention_recommended=True,
                intervention_urgency=4,
                timestamp=datetime.utcnow()
            ))
        
        subtype = await pattern_engine.classify_adhd_subtype()
        assert subtype == ADHDSubtype.PREDOMINANTLY_INATTENTIVE
    
    @pytest.mark.asyncio
    async def test_adhd_subtype_classification_combined(self, pattern_engine):
        """Test ADHD subtype classification for combined presentation."""
        # Simulate mixed pattern history
        inattentive_patterns = [PatternType.HYPERFOCUS, PatternType.TIME_BLINDNESS]
        hyperactive_patterns = [PatternType.TASK_SWITCHING, PatternType.EMOTIONAL_DYSREGULATION]
        combined_patterns = [PatternType.EXECUTIVE_DYSFUNCTION, PatternType.OVERWHELM]
        
        for pattern_type in inattentive_patterns * 5:
            pattern_engine.pattern_history.append(PatternDetection(
                pattern_type=pattern_type,
                severity=PatternSeverity.MODERATE,
                confidence=0.7,
                evidence={},
                intervention_recommended=True,
                intervention_urgency=5,
                timestamp=datetime.utcnow()
            ))
        
        for pattern_type in hyperactive_patterns * 5:
            pattern_engine.pattern_history.append(PatternDetection(
                pattern_type=pattern_type,
                severity=PatternSeverity.MODERATE,
                confidence=0.7,
                evidence={},
                intervention_recommended=True,
                intervention_urgency=5,
                timestamp=datetime.utcnow()
            ))
            
        for pattern_type in combined_patterns * 8:
            pattern_engine.pattern_history.append(PatternDetection(
                pattern_type=pattern_type,
                severity=PatternSeverity.HIGH,
                confidence=0.8,
                evidence={},
                intervention_recommended=True,
                intervention_urgency=6,
                timestamp=datetime.utcnow()
            ))
        
        subtype = await pattern_engine.classify_adhd_subtype()
        assert subtype == ADHDSubtype.COMBINED_PRESENTATION
    
    @pytest.mark.asyncio
    async def test_behavioral_metrics_extraction(self, pattern_engine):
        """Test extraction of behavioral metrics from interaction history."""
        # Populate interaction history
        for i in range(10):
            pattern_engine.recent_interactions.append({
                'timestamp': datetime.utcnow() - timedelta(minutes=i*10),
                'content': f'test message {i}',
                'task_focus': 'test_task',
                'task_completed': i % 3 == 0,  # Every 3rd task completed
                'energy_level': 0.5 + (i % 3) * 0.2
            })
        
        metrics = await pattern_engine._extract_behavioral_metrics()
        
        assert isinstance(metrics, BehavioralMetrics)
        assert 0 <= metrics.completion_rate <= 1
        assert 0 <= metrics.energy_level <= 1
        assert 0 <= metrics.emotional_volatility <= 1
        assert metrics.session_duration >= 0
        assert metrics.task_switching_frequency >= 0
    
    @pytest.mark.asyncio
    async def test_pattern_logging(self, pattern_engine):
        """Test that patterns are properly logged to trace memory."""
        with patch('adhd.pattern_engine.trace_memory.store_trace') as mock_store:
            mock_store.return_value = asyncio.coroutine(lambda: None)()
            
            pattern = PatternDetection(
                pattern_type=PatternType.HYPERFOCUS,
                severity=PatternSeverity.HIGH,
                confidence=0.8,
                evidence={'test': 'data'},
                intervention_recommended=True,
                intervention_urgency=8,
                timestamp=datetime.utcnow()
            )
            
            await pattern_engine._log_pattern_detection(pattern)
            
            mock_store.assert_called_once()
            args = mock_store.call_args[0]
            trace_record = args[0]
            
            assert trace_record.event_type == "pattern_detection"
            assert trace_record.event_data['pattern_type'] == PatternType.HYPERFOCUS.value
            assert trace_record.event_data['confidence'] == 0.8
    
    def test_pattern_summary_generation(self, pattern_engine):
        """Test generation of pattern summary."""
        # Add some patterns to history
        pattern_engine.pattern_history.extend([
            PatternDetection(
                pattern_type=PatternType.HYPERFOCUS,
                severity=PatternSeverity.HIGH,
                confidence=0.8,
                evidence={},
                intervention_recommended=True,
                intervention_urgency=7,
                timestamp=datetime.utcnow()
            ),
            PatternDetection(
                pattern_type=PatternType.EXECUTIVE_DYSFUNCTION,
                severity=PatternSeverity.MODERATE,
                confidence=0.6,
                evidence={},
                intervention_recommended=True,
                intervention_urgency=5,
                timestamp=datetime.utcnow() - timedelta(hours=2)
            )
        ])
        
        summary = pattern_engine.get_pattern_summary()
        
        assert 'adhd_subtype' in summary
        assert 'pattern_counts' in summary
        assert 'recent_patterns' in summary
        assert 'total_patterns_detected' in summary
        assert summary['total_patterns_detected'] == 2
        assert PatternType.HYPERFOCUS.value in summary['pattern_counts']


class TestBehavioralMetrics:
    """Test behavioral metrics calculation."""
    
    def test_behavioral_metrics_validation(self):
        """Test behavioral metrics validation."""
        metrics = BehavioralMetrics(
            session_duration=45.0,
            task_switching_frequency=2.5,
            response_delay=15.0,
            completion_rate=0.7,
            hyperfocus_indicators=['time_loss'],
            stress_markers=['verbal_stress_indication'],
            energy_level=0.6,
            time_estimation_accuracy=0.4,
            interruption_frequency=1.2,
            emotional_volatility=0.3
        )
        
        assert metrics.session_duration == 45.0
        assert metrics.completion_rate == 0.7
        assert len(metrics.hyperfocus_indicators) == 1
        assert metrics.energy_level == 0.6
    
    def test_behavioral_metrics_boundary_values(self):
        """Test behavioral metrics with boundary values."""
        # Test minimum values
        metrics_min = BehavioralMetrics(
            session_duration=0.0,
            task_switching_frequency=0.0,
            response_delay=0.0,
            completion_rate=0.0,
            hyperfocus_indicators=[],
            stress_markers=[],
            energy_level=0.0,
            time_estimation_accuracy=0.0,
            interruption_frequency=0.0,
            emotional_volatility=0.0
        )
        
        assert metrics_min.completion_rate == 0.0
        assert metrics_min.energy_level == 0.0
        
        # Test maximum values  
        metrics_max = BehavioralMetrics(
            session_duration=1000.0,
            task_switching_frequency=10.0,
            response_delay=120.0,
            completion_rate=1.0,
            hyperfocus_indicators=['time_loss', 'resistance_to_interruption'],
            stress_markers=['verbal_stress_indication', 'behavioral_stress'],
            energy_level=1.0,
            time_estimation_accuracy=1.0,
            interruption_frequency=5.0,
            emotional_volatility=1.0
        )
        
        assert metrics_max.completion_rate == 1.0
        assert metrics_max.energy_level == 1.0