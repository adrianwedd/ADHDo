"""
Integration tests for Enhanced Cognitive Loop.

Tests the full integration of all ADHD features through the enhanced
cognitive loop, ensuring proper coordination between components and
end-to-end functionality.
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from adhd.enhanced_cognitive_loop import enhanced_cognitive_loop, EnhancedCognitiveLoopResult
from mcp_server.models import NudgeTier, LLMResponse


class TestEnhancedCognitiveLoop:
    """Integration tests for enhanced cognitive loop."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch.multiple(
            'adhd.enhanced_cognitive_loop',
            frame_builder=AsyncMock(),
            profile_manager=AsyncMock(),
            trace_memory=AsyncMock(),
            llm_router=AsyncMock()
        ) as mocks:
            
            # Setup mock returns
            mocks['frame_builder'].build_frame.return_value = Mock(
                frame=Mock(
                    user_id="test_user",
                    context=[],
                    task_focus="test task"
                ),
                cognitive_load=0.5,
                accessibility_score=0.8
            )
            
            mock_profile = Mock()
            mock_profile.dict.return_value = {'user_id': 'test_user'}
            mocks['profile_manager'].get_or_create_profile.return_value = mock_profile
            mocks['profile_manager'].get_personalized_settings.return_value = {
                'cognitive_load': {'max_context_items': 8},
                'interface': {'complexity': 'adaptive'}
            }
            mocks['profile_manager'].update_profile_from_interaction.return_value = None
            mocks['profile_manager'].adapt_to_pattern_detection.return_value = None
            
            mocks['llm_router'].process_request.return_value = LLMResponse(
                text="Test response",
                source="llm",
                confidence=0.8,
                model_used="test_model",
                latency_ms=100
            )
            
            mocks['trace_memory'].store_trace.return_value = None
            
            yield mocks
    
    @pytest.mark.asyncio
    async def test_process_user_input_basic_flow(self, mock_dependencies):
        """Test basic user input processing through enhanced loop."""
        with patch('adhd.enhanced_cognitive_loop.get_pattern_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.analyze_realtime_behavior.return_value = []
            mock_get_engine.return_value = mock_engine
            
            with patch('adhd.enhanced_cognitive_loop.ml_pipeline') as mock_ml:
                mock_ml.process_interaction.return_value = {'ml_insights': {}}
                
                result = await enhanced_cognitive_loop.process_user_input(
                    user_id="test_user",
                    user_input="I need help with my task",
                    task_focus="Complete project",
                    nudge_tier=NudgeTier.GENTLE
                )
                
                assert isinstance(result, EnhancedCognitiveLoopResult)
                assert result.success is True
                assert result.response is not None
                assert result.response.text == "Test response"
                assert isinstance(result.detected_patterns, list)
                assert isinstance(result.adaptations_applied, list)
                assert isinstance(result.executive_function_support, dict)
    
    @pytest.mark.asyncio
    async def test_process_user_input_with_patterns(self, mock_dependencies):
        """Test processing with detected ADHD patterns."""
        with patch('adhd.enhanced_cognitive_loop.get_pattern_engine') as mock_get_engine:
            mock_engine = Mock()
            
            # Mock detected patterns
            mock_pattern = Mock()
            mock_pattern.pattern_type.value = 'hyperfocus'
            mock_pattern.severity.value = 'high'
            mock_pattern.confidence = 0.8
            mock_pattern.evidence = {'session_duration': 180}
            mock_pattern.intervention_recommended = True
            mock_pattern.intervention_urgency = 8
            mock_pattern.timestamp.isoformat.return_value = datetime.utcnow().isoformat()
            
            mock_engine.analyze_realtime_behavior.return_value = [mock_pattern]
            mock_get_engine.return_value = mock_engine
            
            with patch('adhd.enhanced_cognitive_loop.ml_pipeline') as mock_ml:
                mock_ml.process_interaction.return_value = {'ml_insights': {}}
                
                with patch('adhd.enhanced_cognitive_loop.adaptation_engine') as mock_adapt:
                    mock_adapt.process_adaptation_request.return_value = []
                    mock_adapt.apply_adaptations.return_value = ("adapted response", {})
                    
                    result = await enhanced_cognitive_loop.process_user_input(
                        user_id="test_user",
                        user_input="I've been working on this for 3 hours straight",
                        task_focus="Coding project"
                    )
                    
                    assert result.success is True
                    assert len(result.detected_patterns) == 1
                    assert result.detected_patterns[0]['type'] == 'hyperfocus'
                    assert result.detected_patterns[0]['confidence'] == 0.8
    
    @pytest.mark.asyncio
    async def test_process_user_input_with_adaptations(self, mock_dependencies):
        """Test processing with interface adaptations."""
        with patch('adhd.enhanced_cognitive_loop.get_pattern_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.analyze_realtime_behavior.return_value = []
            mock_get_engine.return_value = mock_engine
            
            with patch('adhd.enhanced_cognitive_loop.ml_pipeline') as mock_ml:
                mock_ml.process_interaction.return_value = {'ml_insights': {}}
                
                with patch('adhd.enhanced_cognitive_loop.adaptation_engine') as mock_adapt:
                    # Mock adaptation decisions
                    mock_decision = Mock()
                    mock_decision.adaptation_type.value = 'cognitive_load_reduction'
                    mock_decision.priority.value = 'high'
                    mock_decision.reasoning = 'High cognitive load detected'
                    mock_decision.parameters = {'max_context_items': 5}
                    
                    mock_adapt.process_adaptation_request.return_value = [mock_decision]
                    mock_adapt.apply_adaptations.return_value = (
                        "Simplified response",
                        {'max_visible_items': 5}
                    )
                    
                    result = await enhanced_cognitive_loop.process_user_input(
                        user_id="test_user",
                        user_input="I'm feeling overwhelmed with all this information",
                        task_focus="Research task"
                    )
                    
                    assert result.success is True
                    assert len(result.adaptations_applied) == 1
                    assert result.adaptations_applied[0]['type'] == 'cognitive_load_reduction'
                    assert result.adaptations_applied[0]['priority'] == 'high'
    
    @pytest.mark.asyncio
    async def test_process_user_input_with_executive_support(self, mock_dependencies):
        """Test processing with executive function support."""
        with patch('adhd.enhanced_cognitive_loop.get_pattern_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.analyze_realtime_behavior.return_value = []
            mock_get_engine.return_value = mock_engine
            
            with patch('adhd.enhanced_cognitive_loop.ml_pipeline') as mock_ml:
                mock_ml.process_interaction.return_value = {'ml_insights': {}}
                
                with patch('adhd.enhanced_cognitive_loop.adaptation_engine') as mock_adapt:
                    mock_adapt.process_adaptation_request.return_value = []
                    mock_adapt.apply_adaptations.return_value = ("response", {})
                    
                    with patch('adhd.enhanced_cognitive_loop.task_breakdown_engine') as mock_breakdown:
                        mock_task_breakdown = Mock()
                        mock_task_breakdown.subtasks = [
                            {'title': 'Step 1', 'time_estimate': 10},
                            {'title': 'Step 2', 'time_estimate': 15}
                        ]
                        mock_task_breakdown.estimated_total_time = 25
                        mock_task_breakdown.complexity_level.value = 'medium'
                        mock_task_breakdown.success_strategies = ['Use timer', 'Take breaks']
                        
                        mock_breakdown.breakdown_task.return_value = mock_task_breakdown
                        
                        result = await enhanced_cognitive_loop.process_user_input(
                            user_id="test_user",
                            user_input="I need to write a report but don't know where to start",
                            task_focus="Write quarterly report"
                        )
                        
                        assert result.success is True
                        assert 'task_breakdown' in result.executive_function_support
                        breakdown = result.executive_function_support['task_breakdown']
                        assert len(breakdown['subtasks']) == 2
                        assert breakdown['estimated_time'] == 25
    
    @pytest.mark.asyncio
    async def test_crisis_detection_and_response(self, mock_dependencies):
        """Test crisis detection and safety response."""
        with patch('adhd.enhanced_cognitive_loop.get_pattern_engine') as mock_get_engine:
            mock_engine = Mock()
            
            # Mock critical pattern
            mock_pattern = Mock()
            mock_pattern.severity.value = 'critical'
            mock_pattern.intervention_urgency = 10
            mock_pattern.pattern_type.value = 'emotional_dysregulation'
            mock_pattern.confidence = 0.9
            mock_pattern.evidence = {'crisis_indicators': True}
            mock_pattern.intervention_recommended = True
            mock_pattern.timestamp.isoformat.return_value = datetime.utcnow().isoformat()
            
            mock_engine.analyze_realtime_behavior.return_value = [mock_pattern]
            mock_get_engine.return_value = mock_engine
            
            # Mock crisis-triggering LLM response
            mock_dependencies['llm_router'].process_request.return_value = LLMResponse(
                text="I understand you're going through a difficult time. Please reach out for support.",
                source="hard_coded",
                confidence=1.0,
                model_used="safety_override",
                latency_ms=50
            )
            
            with patch('adhd.enhanced_cognitive_loop.ml_pipeline') as mock_ml:
                mock_ml.process_interaction.return_value = {'ml_insights': {}}
                
                result = await enhanced_cognitive_loop.process_user_input(
                    user_id="test_user",
                    user_input="I can't handle this anymore, everything is falling apart",
                    task_focus=None
                )
                
                assert result.success is True
                assert result.response.source == "hard_coded"
                assert result.crisis_assessment['is_crisis'] is True
                assert result.crisis_assessment['highest_urgency'] == 10
                assert 'crisis_intervention' in [r['type'] for r in result.intervention_recommendations]
    
    @pytest.mark.asyncio
    async def test_ml_insights_integration(self, mock_dependencies):
        """Test integration with ML pipeline."""
        with patch('adhd.enhanced_cognitive_loop.get_pattern_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.analyze_realtime_behavior.return_value = []
            mock_get_engine.return_value = mock_engine
            
            with patch('adhd.enhanced_cognitive_loop.ml_pipeline') as mock_ml:
                mock_ml.process_interaction.return_value = {
                    'ml_insights': {
                        'detected_pattern': {
                            'type': 'hyperfocus',
                            'confidence': 0.7
                        },
                        'crisis_assessment': {
                            'is_crisis': False,
                            'confidence': 0.2
                        }
                    },
                    'feature_vector': {
                        'features': {'cognitive_load': 0.6, 'energy_level': 0.8}
                    },
                    'processing_success': True
                }
                
                with patch('adhd.enhanced_cognitive_loop.adaptation_engine') as mock_adapt:
                    mock_adapt.process_adaptation_request.return_value = []
                    mock_adapt.apply_adaptations.return_value = ("response", {})
                    
                    result = await enhanced_cognitive_loop.process_user_input(
                        user_id="test_user",
                        user_input="Working on my project",
                        task_focus="Development work"
                    )
                    
                    assert result.success is True
                    assert 'predictions' in result.ml_insights
                    assert result.ml_insights['processing_success'] is True
                    predictions = result.ml_insights['predictions']
                    assert 'detected_pattern' in predictions
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self, mock_dependencies):
        """Test error handling and graceful fallback."""
        # Make pattern engine fail
        with patch('adhd.enhanced_cognitive_loop.get_pattern_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.analyze_realtime_behavior.side_effect = Exception("Pattern analysis failed")
            mock_get_engine.return_value = mock_engine
            
            with patch('adhd.enhanced_cognitive_loop.ml_pipeline') as mock_ml:
                mock_ml.process_interaction.side_effect = Exception("ML processing failed")
                
                # Should still process through basic cognitive loop
                result = await enhanced_cognitive_loop.process_user_input(
                    user_id="test_user",
                    user_input="Test message",
                    task_focus="Test task"
                )
                
                # Should either succeed with fallback or fail gracefully
                if result.success:
                    # Fallback succeeded
                    assert result.response is not None
                    assert result.detected_patterns == []  # Empty due to failure
                else:
                    # Failed gracefully with error
                    assert result.error is not None
                    assert "failed" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self, mock_dependencies):
        """Test that performance metrics are properly tracked."""
        with patch('adhd.enhanced_cognitive_loop.get_pattern_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.analyze_realtime_behavior.return_value = []
            mock_get_engine.return_value = mock_engine
            
            with patch('adhd.enhanced_cognitive_loop.ml_pipeline') as mock_ml:
                mock_ml.process_interaction.return_value = {'ml_insights': {}}
                
                initial_stats = enhanced_cognitive_loop.get_enhanced_stats()
                initial_requests = initial_stats['total_requests']
                
                result = await enhanced_cognitive_loop.process_user_input(
                    user_id="test_user",
                    user_input="Test message"
                )
                
                updated_stats = enhanced_cognitive_loop.get_enhanced_stats()
                
                assert updated_stats['total_requests'] == initial_requests + 1
                if result.success:
                    assert updated_stats['successful_responses'] > initial_stats.get('successful_responses', 0)
                
                # Check performance metrics
                assert result.processing_time_ms > 0
                assert 'success_rate' in updated_stats
                assert 'patterns_per_request' in updated_stats
    
    def test_enhanced_stats_calculation(self):
        """Test enhanced statistics calculation."""
        # Set some mock statistics
        enhanced_cognitive_loop.processing_stats.update({
            'total_requests': 100,
            'successful_responses': 95,
            'patterns_detected': 150,
            'adaptations_applied': 80,
            'executive_interventions': 25,
            'ml_predictions': 90
        })
        
        stats = enhanced_cognitive_loop.get_enhanced_stats()
        
        assert stats['total_requests'] == 100
        assert stats['successful_responses'] == 95
        assert stats['success_rate'] == 0.95
        assert stats['patterns_per_request'] == 1.5
        assert stats['adaptations_per_request'] == 0.8
        assert 'enhancement_features_active' in stats


class TestEnhancedCognitiveLoopResult:
    """Test enhanced cognitive loop result model."""
    
    def test_result_creation_minimal(self):
        """Test creating result with minimal data."""
        result = EnhancedCognitiveLoopResult(
            success=True,
            processing_time_ms=150.5
        )
        
        assert result.success is True
        assert result.processing_time_ms == 150.5
        assert result.detected_patterns == []
        assert result.adaptations_applied == []
        assert result.executive_function_support == {}
    
    def test_result_creation_comprehensive(self):
        """Test creating result with full data."""
        result = EnhancedCognitiveLoopResult(
            success=True,
            response=Mock(text="Test response"),
            actions_taken=['pattern_detection', 'adaptation_applied'],
            cognitive_load=0.6,
            processing_time_ms=200.0,
            detected_patterns=[
                {'type': 'hyperfocus', 'confidence': 0.8}
            ],
            adaptations_applied=[
                {'type': 'cognitive_load_reduction', 'priority': 'high'}
            ],
            executive_function_support={
                'task_breakdown': {'subtasks': 3}
            },
            ml_insights={'predictions': {}},
            crisis_assessment={'is_crisis': False},
            intervention_recommendations=[
                {'type': 'pattern_intervention', 'urgency': 5}
            ]
        )
        
        assert result.success is True
        assert result.cognitive_load == 0.6
        assert len(result.detected_patterns) == 1
        assert len(result.adaptations_applied) == 1
        assert 'task_breakdown' in result.executive_function_support
        assert len(result.intervention_recommendations) == 1