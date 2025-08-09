"""
Unit tests for Intelligent Adaptation Engine.

Tests the adaptive interface management, cognitive load optimization,
and real-time adaptation capabilities.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from adhd.adaptation_engine import (
    AdaptationEngine, CognitiveLoadAdapter, InterfaceAdapter, ResponseAdapter,
    AdaptationType, AdaptationPriority, AdaptationDecision, AdaptationResult,
    InterfaceComplexityLevel
)
from mcp_server.models import MCPFrame, FrameContext, ContextType


class TestCognitiveLoadAdapter:
    """Test suite for Cognitive Load Adapter."""
    
    @pytest.fixture
    def cognitive_adapter(self):
        """Create cognitive load adapter for testing."""
        return CognitiveLoadAdapter("test_user")
    
    @pytest.fixture
    def sample_frame(self):
        """Create sample MCP frame for testing."""
        frame = MCPFrame(
            user_id="test_user",
            agent_id="test_agent",
            task_focus="test task",
            timestamp=datetime.utcnow()
        )
        
        # Add some context items
        for i in range(5):
            frame.add_context(
                ContextType.TASK,
                {"task": f"context_{i}", "data": f"some data {i}"},
                source="test"
            )
        
        return frame
    
    @pytest.mark.asyncio
    async def test_assess_current_load_normal(self, cognitive_adapter, sample_frame):
        """Test cognitive load assessment with normal conditions."""
        interaction_data = {
            'energy_level': 0.7,
            'task_complexity': 0.5,
            'time_pressure': 0.3
        }
        
        load = await cognitive_adapter.assess_current_load(sample_frame, interaction_data)
        
        assert 0.0 <= load <= 1.0
        assert len(cognitive_adapter.load_history) == 1
        assert cognitive_adapter.current_load == load
    
    @pytest.mark.asyncio
    async def test_assess_current_load_high(self, cognitive_adapter, sample_frame):
        """Test cognitive load assessment with high load conditions."""
        # Add more context items to increase load
        for i in range(10):
            sample_frame.add_context(
                ContextType.ENVIRONMENT,
                {"env": f"context_{i}", "complex_data": "x" * 100},
                source="test"
            )
        
        interaction_data = {
            'energy_level': 0.2,  # Low energy
            'task_complexity': 0.8,  # High complexity
            'time_pressure': 0.7   # High pressure
        }
        
        load = await cognitive_adapter.assess_current_load(sample_frame, interaction_data)
        
        assert load > 0.6  # Should be high load
        assert cognitive_adapter.current_load == load
    
    @pytest.mark.asyncio
    async def test_recommend_load_adaptations_high_load(self, cognitive_adapter):
        """Test adaptation recommendations for high cognitive load."""
        cognitive_adapter.overwhelm_threshold = 0.7
        
        adaptations = await cognitive_adapter.recommend_load_adaptations(0.9)
        
        assert len(adaptations) > 0
        
        # Check for cognitive load reduction adaptation
        load_adaptations = [a for a in adaptations 
                          if a.adaptation_type == AdaptationType.COGNITIVE_LOAD_REDUCTION]
        assert len(load_adaptations) > 0
        
        adaptation = load_adaptations[0]
        assert adaptation.priority == AdaptationPriority.HIGH
        assert adaptation.confidence > 0.8
        assert 'max_context_items' in adaptation.parameters
        assert adaptation.parameters['max_context_items'] <= 5
    
    @pytest.mark.asyncio
    async def test_recommend_load_adaptations_low_load(self, cognitive_adapter):
        """Test adaptation recommendations for low cognitive load."""
        cognitive_adapter.minimum_engagement = 0.2
        
        adaptations = await cognitive_adapter.recommend_load_adaptations(0.1)
        
        # Should recommend complexity scaling for engagement
        complexity_adaptations = [a for a in adaptations 
                                if a.adaptation_type == AdaptationType.COMPLEXITY_SCALING]
        
        if complexity_adaptations:  # May not always recommend if load is too low
            adaptation = complexity_adaptations[0]
            assert adaptation.priority == AdaptationPriority.MEDIUM
            assert 'increase_detail_level' in adaptation.parameters


class TestInterfaceAdapter:
    """Test suite for Interface Adapter."""
    
    @pytest.fixture
    def interface_adapter(self):
        """Create interface adapter for testing."""
        return InterfaceAdapter("test_user")
    
    @pytest.mark.asyncio
    async def test_adapt_interface_minimal(self, interface_adapter):
        """Test adapting interface to minimal complexity."""
        context = {'adaptation_reason': 'high_cognitive_load'}
        
        adaptations = await interface_adapter.adapt_interface_complexity(
            InterfaceComplexityLevel.MINIMAL, context
        )
        
        assert 'max_visible_items' in adaptations
        assert adaptations['max_visible_items'] == 3
        assert adaptations['hide_secondary_actions'] is True
        assert adaptations['single_column_layout'] is True
        assert interface_adapter.current_complexity == InterfaceComplexityLevel.MINIMAL
    
    @pytest.mark.asyncio
    async def test_adapt_interface_expert(self, interface_adapter):
        """Test adapting interface to expert complexity."""
        context = {'adaptation_reason': 'user_request'}
        
        adaptations = await interface_adapter.adapt_interface_complexity(
            InterfaceComplexityLevel.EXPERT, context
        )
        
        assert 'max_visible_items' in adaptations
        assert adaptations['max_visible_items'] == -1  # No limit
        assert adaptations['show_all_features'] is True
        assert adaptations['expert_shortcuts'] is True
        assert interface_adapter.current_complexity == InterfaceComplexityLevel.EXPERT
    
    @pytest.mark.asyncio
    async def test_interface_rollback(self, interface_adapter):
        """Test rolling back interface adaptations."""
        # First adaptation
        await interface_adapter.adapt_interface_complexity(
            InterfaceComplexityLevel.SIMPLE, {}
        )
        assert interface_adapter.current_complexity == InterfaceComplexityLevel.SIMPLE
        
        # Second adaptation
        await interface_adapter.adapt_interface_complexity(
            InterfaceComplexityLevel.MINIMAL, {}
        )
        assert interface_adapter.current_complexity == InterfaceComplexityLevel.MINIMAL
        
        # Rollback
        success = await interface_adapter.rollback_last_adaptation()
        assert success
        assert interface_adapter.current_complexity == InterfaceComplexityLevel.SIMPLE
        
        # Another rollback
        success = await interface_adapter.rollback_last_adaptation()
        assert success
        assert interface_adapter.current_complexity == InterfaceComplexityLevel.MODERATE
        
        # No more rollbacks available
        success = await interface_adapter.rollback_last_adaptation()
        assert not success


class TestResponseAdapter:
    """Test suite for Response Adapter."""
    
    @pytest.fixture
    def response_adapter(self):
        """Create response adapter for testing."""
        return ResponseAdapter("test_user")
    
    @pytest.mark.asyncio
    async def test_adapt_response_simplification(self, response_adapter):
        """Test response simplification."""
        original_response = ("This is a very long and complex response that "
                           "goes into great detail about various topics and "
                           "uses sophisticated vocabulary and complex sentence "
                           "structures that might overwhelm users with ADHD.")
        
        adaptation = AdaptationDecision(
            adaptation_type=AdaptationType.COGNITIVE_LOAD_REDUCTION,
            priority=AdaptationPriority.HIGH,
            confidence=0.8,
            reasoning="High cognitive load detected",
            parameters={'response_length_limit': 100, 'simplify_language': True},
            expected_outcome="Reduced cognitive load",
            rollback_criteria=[],
            timestamp=datetime.utcnow(),
            user_id="test_user"
        )
        
        user_state = {'stress_level': 0.3, 'energy_level': 0.5}
        
        adapted_response = await response_adapter.adapt_response_style(
            original_response, user_state, [adaptation]
        )
        
        assert len(adapted_response) <= 103  # 100 + "..."
        assert adapted_response.endswith("...")
        assert len(response_adapter.response_history) == 1
    
    @pytest.mark.asyncio
    async def test_adapt_response_style_direct(self, response_adapter):
        """Test adapting response to direct style."""
        original_response = "Maybe you might want to perhaps consider trying this approach."
        
        adaptation = AdaptationDecision(
            adaptation_type=AdaptationType.RESPONSE_STYLE_MODIFICATION,
            priority=AdaptationPriority.MEDIUM,
            confidence=0.7,
            reasoning="User prefers direct communication",
            parameters={'target_style': 'direct'},
            expected_outcome="Clearer communication",
            rollback_criteria=[],
            timestamp=datetime.utcnow(),
            user_id="test_user"
        )
        
        user_state = {'stress_level': 0.4, 'energy_level': 0.6}
        
        adapted_response = await response_adapter.adapt_response_style(
            original_response, user_state, [adaptation]
        )
        
        assert "maybe" not in adapted_response.lower()
        assert "perhaps" not in adapted_response.lower()
        assert "should" in adapted_response or "try" in adapted_response
    
    @pytest.mark.asyncio
    async def test_adapt_response_encouraging_style(self, response_adapter):
        """Test adapting response to encouraging style."""
        original_response = "Here is the information you requested."
        
        adaptation = AdaptationDecision(
            adaptation_type=AdaptationType.RESPONSE_STYLE_MODIFICATION,
            priority=AdaptationPriority.MEDIUM,
            confidence=0.7,
            reasoning="User needs encouragement",
            parameters={'target_style': 'encouraging'},
            expected_outcome="Increased motivation",
            rollback_criteria=[],
            timestamp=datetime.utcnow(),
            user_id="test_user"
        )
        
        user_state = {'stress_level': 0.2, 'energy_level': 0.7}
        
        adapted_response = await response_adapter.adapt_response_style(
            original_response, user_state, [adaptation]
        )
        
        assert ("great" in adapted_response.lower() or 
                "excellent" in adapted_response.lower() or
                "you've got this" in adapted_response.lower())
    
    @pytest.mark.asyncio
    async def test_adapt_response_high_stress(self, response_adapter):
        """Test response adaptation for high stress user state."""
        original_response = "You must complete this task immediately!"
        
        user_state = {'stress_level': 0.9, 'energy_level': 0.3}
        
        adapted_response = await response_adapter.adapt_response_style(
            original_response, user_state, []
        )
        
        # Should add calming tone
        assert ("take a deep breath" in adapted_response.lower() or
                "no pressure" in adapted_response.lower() or
                "one step at a time" in adapted_response.lower())
    
    @pytest.mark.asyncio
    async def test_adapt_response_low_energy(self, response_adapter):
        """Test response adaptation for low energy user state."""
        original_response = "Here's what you need to do."
        
        user_state = {'stress_level': 0.4, 'energy_level': 0.1}
        
        adapted_response = await response_adapter.adapt_response_style(
            original_response, user_state, []
        )
        
        # Should add gentle encouragement
        assert ("small steps count" in adapted_response.lower() or
                "progress is still progress" in adapted_response.lower() or
                "you're doing better than you think" in adapted_response.lower())


class TestAdaptationEngine:
    """Test suite for main Adaptation Engine."""
    
    @pytest.fixture
    def adaptation_engine(self):
        """Create adaptation engine for testing."""
        return AdaptationEngine()
    
    @pytest.fixture
    def sample_frame(self):
        """Create sample MCP frame."""
        frame = MCPFrame(
            user_id="test_user",
            agent_id="test_agent",
            task_focus="test task",
            timestamp=datetime.utcnow()
        )
        
        frame.add_context(
            ContextType.USER_STATE,
            {"current_state": "focused", "energy_level": 0.6},
            source="test"
        )
        
        return frame
    
    @pytest.mark.asyncio
    async def test_process_adaptation_request(self, adaptation_engine, sample_frame):
        """Test processing adaptation request."""
        # Mock profile manager
        with patch('adhd.adaptation_engine.profile_manager') as mock_profile_manager:
            mock_profile = Mock()
            mock_profile.hyperfocus_tendency = 0.7
            mock_profile_manager.get_or_create_profile.return_value = asyncio.coroutine(lambda: mock_profile)()
            
            current_state = {
                'user_id': 'test_user',
                'cognitive_load': 0.8,
                'energy_level': 0.5,
                'stress_level': 0.6
            }
            
            detected_patterns = []  # No patterns for this test
            
            adaptations = await adaptation_engine.process_adaptation_request(
                "test_user", current_state, detected_patterns, sample_frame
            )
            
            # Should get cognitive load adaptations due to high load
            assert len(adaptations) > 0
            high_priority_adaptations = [a for a in adaptations 
                                       if a.priority == AdaptationPriority.HIGH]
            assert len(high_priority_adaptations) > 0
    
    @pytest.mark.asyncio
    async def test_apply_adaptations(self, adaptation_engine):
        """Test applying adaptations to response and interface."""
        adaptation = AdaptationDecision(
            adaptation_type=AdaptationType.COGNITIVE_LOAD_REDUCTION,
            priority=AdaptationPriority.HIGH,
            confidence=0.8,
            reasoning="High cognitive load detected",
            parameters={'response_length_limit': 100},
            expected_outcome="Reduced cognitive load",
            rollback_criteria=[],
            timestamp=datetime.utcnow(),
            user_id="test_user"
        )
        
        original_response = "This is a very long response " * 20
        sample_frame = Mock()
        sample_frame.context = []
        
        with patch.object(adaptation_engine, '_extract_user_state_from_frame', return_value={}):
            modified_response, interface_changes = await adaptation_engine.apply_adaptations(
                [adaptation], original_response, sample_frame
            )
            
            # Response should be modified (truncated)
            assert len(modified_response) < len(original_response)
            
            # Should track the adaptation
            assert "test_user" in adaptation_engine.adaptation_history
            assert len(adaptation_engine.adaptation_history["test_user"]) == 1
    
    @pytest.mark.asyncio
    async def test_track_adaptation_effectiveness(self, adaptation_engine):
        """Test tracking adaptation effectiveness."""
        # First apply an adaptation to create history
        adaptation = AdaptationDecision(
            adaptation_type=AdaptationType.COGNITIVE_LOAD_REDUCTION,
            priority=AdaptationPriority.HIGH,
            confidence=0.8,
            reasoning="Test adaptation",
            parameters={},
            expected_outcome="Test outcome",
            rollback_criteria=[],
            timestamp=datetime.utcnow(),
            user_id="test_user"
        )
        
        await adaptation_engine.apply_adaptations([adaptation], "test", Mock())
        
        # Get the adaptation ID
        adaptation_result = adaptation_engine.adaptation_history["test_user"][0]
        adaptation_id = adaptation_result.adaptation_id
        
        # Track effectiveness
        user_feedback = {
            'task_completed': True,
            'reduced_stress': True,
            'improved_focus': False,
            'confused': False
        }
        
        outcome_metrics = {
            'completion_time': 25,
            'expected_completion_time': 30
        }
        
        await adaptation_engine.track_adaptation_effectiveness(
            "test_user", adaptation_id, user_feedback, outcome_metrics
        )
        
        # Check that effectiveness was recorded
        result = adaptation_engine.adaptation_history["test_user"][0]
        assert result.effectiveness_score is not None
        assert result.effectiveness_score > 0.5  # Should be positive due to task completion
    
    def test_get_adaptation_summary(self, adaptation_engine):
        """Test getting adaptation summary for user."""
        # Create some adaptation history
        adaptation_engine.adaptation_history["test_user"] = [
            Mock(
                timestamp=datetime.utcnow(),
                effectiveness_score=0.8,
                adaptation_id="test_1"
            ),
            Mock(
                timestamp=datetime.utcnow() - timedelta(hours=2),
                effectiveness_score=0.6,
                adaptation_id="test_2"
            )
        ]
        
        adaptation_engine.effectiveness_tracking["test_user"] = {
            "cognitive_load_reduction": 0.7,
            "interface_simplification": 0.8
        }
        
        summary = adaptation_engine.get_adaptation_summary("test_user")
        
        assert summary['total_adaptations'] == 2
        assert summary['recent_adaptations'] == 2
        assert summary['average_effectiveness'] == 0.7
        assert 'cognitive_load_reduction' in summary['adaptation_types']
        assert summary['most_effective_adaptation'] == "interface_simplification"
    
    def test_get_adaptation_summary_no_data(self, adaptation_engine):
        """Test getting adaptation summary for user with no data."""
        summary = adaptation_engine.get_adaptation_summary("new_user")
        
        assert summary['no_adaptations'] is True


class TestAdaptationDecision:
    """Test AdaptationDecision model."""
    
    def test_adaptation_decision_creation(self):
        """Test creating adaptation decision."""
        decision = AdaptationDecision(
            adaptation_type=AdaptationType.COGNITIVE_LOAD_REDUCTION,
            priority=AdaptationPriority.HIGH,
            confidence=0.85,
            reasoning="User showing signs of cognitive overload",
            parameters={'max_context_items': 5, 'simplify_language': True},
            expected_outcome="Reduced cognitive burden and clearer responses",
            rollback_criteria=['user_confusion', 'task_incompletion'],
            timestamp=datetime.utcnow(),
            user_id="test_user"
        )
        
        assert decision.adaptation_type == AdaptationType.COGNITIVE_LOAD_REDUCTION
        assert decision.priority == AdaptationPriority.HIGH
        assert decision.confidence == 0.85
        assert len(decision.parameters) == 2
        assert len(decision.rollback_criteria) == 2
        assert decision.user_id == "test_user"


class TestAdaptationResult:
    """Test AdaptationResult model."""
    
    def test_adaptation_result_creation(self):
        """Test creating adaptation result."""
        result = AdaptationResult(
            success=True,
            adaptation_id="adaptation_123",
            applied_changes={'response_modified': True, 'interface_simplified': True},
            user_feedback={'satisfied': True, 'task_completed': True},
            effectiveness_score=0.8,
            side_effects=['increased_engagement'],
            timestamp=datetime.utcnow()
        )
        
        assert result.success is True
        assert result.adaptation_id == "adaptation_123"
        assert result.applied_changes['response_modified'] is True
        assert result.effectiveness_score == 0.8
        assert len(result.side_effects) == 1