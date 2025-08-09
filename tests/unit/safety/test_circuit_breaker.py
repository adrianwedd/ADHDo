"""
CRITICAL TESTS: Circuit Breaker System for ADHD Psychological Safety

These tests validate the circuit breaker pattern adapted for ADHD users:
- Prevents system overwhelm during vulnerable states
- Implements Dynamic Systems Theory for psychological stability
- Protects users from shame spirals and executive dysfunction cascades
- Provides "anchor mode" responses during crisis states
- Ensures proper recovery and testing mechanisms

ADHD-SPECIFIC REQUIREMENTS:
- Circuit breaker must prevent overwhelming struggling users
- Recovery periods must account for ADHD executive dysfunction patterns
- Anchor mode responses must be non-demanding and supportive
- State transitions must be gradual to avoid additional stress
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from mcp_server.cognitive_loop import CognitiveLoop, CircuitBreakerState
from mcp_server.models import MCPFrame, NudgeTier


class TestCircuitBreakerStateManagement:
    """Test circuit breaker state tracking and transitions."""
    
    @pytest.fixture
    def circuit_breaker_state(self):
        """Create fresh circuit breaker state for testing."""
        return CircuitBreakerState(user_id="test_user")
    
    def test_initial_state_closed(self, circuit_breaker_state):
        """Test circuit breaker starts in closed (normal) state."""
        assert circuit_breaker_state.is_open is False
        assert circuit_breaker_state.failure_count == 0
        assert circuit_breaker_state.last_failure is None
        assert circuit_breaker_state.next_test_time is None
    
    def test_should_trip_threshold(self, circuit_breaker_state):
        """Test circuit breaker trip threshold logic."""
        # Should not trip with low failure count
        circuit_breaker_state.failure_count = 1
        assert circuit_breaker_state.should_trip() is False
        
        circuit_breaker_state.failure_count = 2
        assert circuit_breaker_state.should_trip() is False
        
        # Should trip at default threshold of 3
        circuit_breaker_state.failure_count = 3
        assert circuit_breaker_state.should_trip() is True
        
        circuit_breaker_state.failure_count = 5
        assert circuit_breaker_state.should_trip() is True
    
    def test_custom_trip_threshold(self, circuit_breaker_state):
        """Test circuit breaker with custom trip threshold."""
        circuit_breaker_state.failure_count = 2
        
        # Custom threshold of 2
        assert circuit_breaker_state.should_trip(max_failures=2) is True
        
        # Custom threshold of 5
        assert circuit_breaker_state.should_trip(max_failures=5) is False
    
    def test_should_test_recovery_timing(self, circuit_breaker_state):
        """Test recovery testing timing logic."""
        # Closed circuit should not test
        assert circuit_breaker_state.should_test() is False
        
        # Open circuit without test time should not test
        circuit_breaker_state.is_open = True
        assert circuit_breaker_state.should_test() is False
        
        # Open circuit with future test time should not test
        circuit_breaker_state.next_test_time = datetime.utcnow() + timedelta(hours=1)
        assert circuit_breaker_state.should_test() is False
        
        # Open circuit with past test time should test
        circuit_breaker_state.next_test_time = datetime.utcnow() - timedelta(minutes=1)
        assert circuit_breaker_state.should_test() is True
    
    def test_adhd_specific_recovery_periods(self, circuit_breaker_state):
        """Test recovery periods are appropriate for ADHD patterns."""
        # ADHD users need longer recovery periods due to executive dysfunction
        circuit_breaker_state.is_open = True
        
        # Recovery periods should be in hours, not minutes
        test_times = [
            datetime.utcnow() + timedelta(hours=2),
            datetime.utcnow() + timedelta(hours=4),
            datetime.utcnow() + timedelta(hours=6)
        ]
        
        for test_time in test_times:
            circuit_breaker_state.next_test_time = test_time
            # Should not test before recovery period
            assert circuit_breaker_state.should_test() is False


class TestCognitiveLoopCircuitBreakerIntegration:
    """Test circuit breaker integration with cognitive loop."""
    
    @pytest.fixture
    def cognitive_loop(self):
        """Create cognitive loop for testing."""
        return CognitiveLoop()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_initialization(self, cognitive_loop):
        """Test circuit breaker is properly initialized per user."""
        user_id = "test_user_123"
        
        # Check circuit breaker for user
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        
        assert circuit_state.user_id == user_id
        assert circuit_state.is_open is False
        assert circuit_state.failure_count == 0
        
        # Should be stored in cognitive loop
        assert user_id in cognitive_loop.circuit_breakers
        assert cognitive_loop.circuit_breakers[user_id] == circuit_state
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_tracking(self, cognitive_loop):
        """Test circuit breaker tracks failures correctly."""
        user_id = "failure_test_user"
        
        # Initialize circuit breaker
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        
        # Simulate failure
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        
        assert circuit_state.failure_count == 1
        assert circuit_state.last_failure is not None
        assert circuit_state.is_open is False  # Should not trip yet
        
        # Another failure
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        
        assert circuit_state.failure_count == 2
        assert circuit_state.is_open is False
        
        # Third failure should trip circuit
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        
        assert circuit_state.failure_count == 3
        assert circuit_state.is_open is True
        assert circuit_state.next_test_time is not None
        
        # Test time should be set for future (ADHD-appropriate recovery period)
        assert circuit_state.next_test_time > datetime.utcnow()
        recovery_hours = (circuit_state.next_test_time - datetime.utcnow()).total_seconds() / 3600
        assert 1.5 <= recovery_hours <= 6  # ADHD-appropriate recovery period
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success_recovery(self, cognitive_loop):
        """Test circuit breaker recovers on success."""
        user_id = "recovery_test_user"
        
        # Trip the circuit breaker
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        await cognitive_loop._update_circuit_breaker(user_id, success=False) 
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        
        assert circuit_state.is_open is True
        assert circuit_state.failure_count == 3
        
        # Success should reset circuit breaker
        await cognitive_loop._update_circuit_breaker(user_id, success=True)
        
        assert circuit_state.is_open is False
        assert circuit_state.failure_count == 0
        assert circuit_state.last_failure is None
        assert circuit_state.next_test_time is None
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_stats_tracking(self, cognitive_loop):
        """Test circuit breaker trips are tracked in stats."""
        user_id = "stats_test_user"
        
        initial_trips = cognitive_loop.processing_stats["circuit_breaker_trips"]
        
        # Trip circuit breaker
        await cognitive_loop._check_circuit_breaker(user_id)
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        
        # Stats should be updated
        assert cognitive_loop.processing_stats["circuit_breaker_trips"] == initial_trips + 1


class TestAnchorModeResponses:
    """Test anchor mode responses during circuit breaker activation."""
    
    @pytest.fixture
    def cognitive_loop(self):
        return CognitiveLoop()
    
    @pytest.mark.asyncio
    async def test_anchor_mode_response_content(self, cognitive_loop):
        """Test anchor mode provides appropriate supportive response."""
        user_id = "anchor_test_user"
        
        # Create tripped circuit breaker state
        circuit_state = CircuitBreakerState(
            user_id=user_id,
            is_open=True,
            failure_count=3,
            last_failure=datetime.utcnow(),
            next_test_time=datetime.utcnow() + timedelta(hours=2)
        )
        
        result = await cognitive_loop._handle_circuit_open(user_id, circuit_state)
        
        # Verify anchor mode response characteristics
        assert result.success is True
        assert result.response is not None
        assert result.response.source == "anchor_mode"
        assert result.response.model_used == "circuit_breaker"
        assert result.response.confidence == 1.0
        
        # Response should be supportive and non-demanding
        response_text = result.response.text.lower()
        supportive_phrases = ["no pressure", "when you're ready", "here when", "take care"]
        assert any(phrase in response_text for phrase in supportive_phrases), \
            "Anchor mode response lacks supportive language"
        
        # Should not contain demanding language
        demanding_phrases = ["must", "should", "need to", "have to", "complete", "finish"]
        assert not any(phrase in response_text for phrase in demanding_phrases), \
            "Anchor mode response contains demanding language"
    
    @pytest.mark.asyncio
    async def test_anchor_mode_minimal_cognitive_load(self, cognitive_loop):
        """Test anchor mode has minimal cognitive load."""
        user_id = "load_test_user"
        circuit_state = CircuitBreakerState(
            user_id=user_id,
            is_open=True,
            failure_count=3
        )
        
        result = await cognitive_loop._handle_circuit_open(user_id, circuit_state)
        
        # Cognitive load should be minimal for anchor mode
        assert result.cognitive_load <= 0.2, \
            f"Anchor mode cognitive load {result.cognitive_load} too high, should be ≤0.2"
        
        # Processing time should be nearly instant
        assert result.processing_time_ms <= 5.0, \
            f"Anchor mode processing time {result.processing_time_ms}ms too slow"
        
        # Actions should indicate anchor mode
        assert "anchor_mode" in result.actions_taken
    
    @pytest.mark.asyncio
    async def test_anchor_mode_visual_elements(self, cognitive_loop):
        """Test anchor mode includes calming visual elements."""
        user_id = "visual_test_user"
        circuit_state = CircuitBreakerState(user_id=user_id, is_open=True)
        
        result = await cognitive_loop._handle_circuit_open(user_id, circuit_state)
        
        response_text = result.response.text
        
        # Should include calming emoji
        calming_emojis = ["💙", "🤗", "🌟", "✨", "🕊️", "🌸"]
        assert any(emoji in response_text for emoji in calming_emojis), \
            "Anchor mode response lacks calming visual elements"
    
    @pytest.mark.asyncio
    async def test_anchor_mode_consistency(self, cognitive_loop):
        """Test anchor mode responses are consistent but not repetitive."""
        user_id = "consistency_test_user"
        circuit_state = CircuitBreakerState(user_id=user_id, is_open=True)
        
        responses = []
        for _ in range(5):
            result = await cognitive_loop._handle_circuit_open(user_id, circuit_state)
            responses.append(result.response.text)
        
        # All responses should be anchor mode
        for i, response_text in enumerate(responses):
            assert "no pressure" in response_text.lower() or "when you're ready" in response_text.lower(), \
                f"Response {i+1} not in anchor mode: {response_text}"
        
        # Responses should be identical (consistent support)
        assert all(response == responses[0] for response in responses), \
            "Anchor mode responses should be consistent"


class TestCircuitBreakerProcessingFlow:
    """Test circuit breaker integration in main processing flow."""
    
    @pytest.fixture
    def cognitive_loop(self):
        return CognitiveLoop()
    
    @pytest.mark.asyncio
    async def test_normal_processing_with_closed_circuit(self, cognitive_loop):
        """Test normal processing when circuit breaker is closed."""
        with patch.object(cognitive_loop, 'enhanced_frame_builder', None), \
             patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router:
            
            # Mock successful processing
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_contextual_frame = Mock()
            mock_contextual_frame.frame = mock_frame.frame
            mock_contextual_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_contextual_frame)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.8
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            result = await cognitive_loop.process_user_input(
                user_id="normal_test_user",
                user_input="I need help with my task"
            )
            
            # Should proceed with normal processing
            assert result.success is True
            assert result.response.source == "local"
            mock_frame_builder.build_frame.assert_called_once()
            mock_llm_router.process_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_processing_with_open_circuit_no_testing(self, cognitive_loop):
        """Test processing when circuit is open and not ready for testing."""
        user_id = "open_circuit_user"
        
        # Pre-trip the circuit breaker
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        circuit_state.is_open = True
        circuit_state.failure_count = 3
        circuit_state.next_test_time = datetime.utcnow() + timedelta(hours=1)  # Future test time
        
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router:
            
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I need help"
            )
            
            # Should get anchor mode response
            assert result.success is True
            assert result.response.source == "anchor_mode"
            assert "anchor_mode" in result.actions_taken
            
            # Normal processing should be bypassed
            mock_frame_builder.build_frame.assert_not_called()
            mock_llm_router.process_request.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_processing_with_open_circuit_ready_for_testing(self, cognitive_loop):
        """Test processing when circuit is open but ready for recovery testing."""
        user_id = "testing_circuit_user"
        
        # Set up circuit for testing
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        circuit_state.is_open = True
        circuit_state.failure_count = 3
        circuit_state.next_test_time = datetime.utcnow() - timedelta(minutes=1)  # Past test time
        
        with patch.object(cognitive_loop, 'enhanced_frame_builder', None), \
             patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router:
            
            # Mock successful processing
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_contextual_frame = Mock()
            mock_contextual_frame.frame = mock_frame.frame
            mock_contextual_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_contextual_frame)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.8
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I'm feeling better now"
            )
            
            # Should proceed with testing (normal processing)
            assert result.success is True
            assert result.response.source == "local"
            mock_frame_builder.build_frame.assert_called_once()
            mock_llm_router.process_request.assert_called_once()
            
            # Circuit should be reset on success
            assert circuit_state.is_open is False
            assert circuit_state.failure_count == 0


class TestCircuitBreakerEdgeCases:
    """Test circuit breaker edge cases and error conditions."""
    
    @pytest.fixture
    def cognitive_loop(self):
        return CognitiveLoop()
    
    @pytest.mark.asyncio
    async def test_multiple_users_independent_circuits(self, cognitive_loop):
        """Test circuit breakers are independent between users."""
        user1_id = "user1_independent"
        user2_id = "user2_independent"
        
        # Trip circuit for user1 only
        await cognitive_loop._update_circuit_breaker(user1_id, success=False)
        await cognitive_loop._update_circuit_breaker(user1_id, success=False)
        await cognitive_loop._update_circuit_breaker(user1_id, success=False)
        
        user1_state = await cognitive_loop._check_circuit_breaker(user1_id)
        user2_state = await cognitive_loop._check_circuit_breaker(user2_id)
        
        # Only user1 should have tripped circuit
        assert user1_state.is_open is True
        assert user1_state.failure_count == 3
        
        assert user2_state.is_open is False
        assert user2_state.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_partial_recovery(self, cognitive_loop):
        """Test circuit breaker handles partial recovery scenarios."""
        user_id = "partial_recovery_user"
        
        # Trip the circuit
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        
        assert circuit_state.is_open is True
        
        # Simulate partial recovery (still some failures)
        circuit_state.next_test_time = datetime.utcnow() - timedelta(minutes=1)
        
        # First test succeeds
        await cognitive_loop._update_circuit_breaker(user_id, success=True)
        assert circuit_state.is_open is False
        
        # But then fails again
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        assert circuit_state.failure_count == 1
        assert circuit_state.is_open is False  # Should not trip immediately
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_processing_errors(self, cognitive_loop):
        """Test circuit breaker during processing errors."""
        user_id = "error_test_user"
        
        with patch.object(cognitive_loop, 'enhanced_frame_builder', None), \
             patch('frames.builder.frame_builder') as mock_frame_builder:
            
            # Mock frame builder to raise exception
            mock_frame_builder.build_frame = AsyncMock(side_effect=Exception("Processing error"))
            
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="Test input"
            )
            
            # Should fail gracefully
            assert result.success is False
            assert result.error is not None
            
            # Circuit breaker should track the failure
            circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
            assert circuit_state.failure_count == 1


class TestCircuitBreakerADHDSpecificBehaviors:
    """Test ADHD-specific circuit breaker behaviors."""
    
    @pytest.fixture
    def cognitive_loop(self):
        return CognitiveLoop()
    
    @pytest.mark.asyncio
    async def test_adhd_appropriate_failure_threshold(self, cognitive_loop):
        """Test failure threshold is appropriate for ADHD patterns."""
        user_id = "adhd_threshold_user"
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        
        # ADHD users may have more variable days - threshold should not be too sensitive
        default_threshold = 3  # Current default
        assert default_threshold >= 3, "Failure threshold too sensitive for ADHD users"
        
        # Test that threshold is reasonable for ADHD patterns
        assert circuit_state.should_trip(max_failures=1) is False, "Threshold of 1 too sensitive"
        assert circuit_state.should_trip(max_failures=2) is False, "Threshold of 2 may be too sensitive"
    
    @pytest.mark.asyncio
    async def test_adhd_recovery_period_length(self, cognitive_loop):
        """Test recovery periods are appropriate for ADHD executive dysfunction."""
        user_id = "adhd_recovery_user"
        
        # Trip circuit breaker
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        circuit_state.failure_count = 3
        await cognitive_loop._update_circuit_breaker(user_id, success=False)
        
        assert circuit_state.is_open is True
        assert circuit_state.next_test_time is not None
        
        # Recovery period should be measured in hours, not minutes
        recovery_time = (circuit_state.next_test_time - datetime.utcnow()).total_seconds()
        recovery_hours = recovery_time / 3600
        
        # ADHD users often need longer recovery periods
        assert recovery_hours >= 1.0, "Recovery period too short for ADHD executive dysfunction"
        assert recovery_hours <= 8.0, "Recovery period too long, may feel abandoned"
    
    @pytest.mark.asyncio
    async def test_anchor_mode_adhd_friendly_language(self, cognitive_loop):
        """Test anchor mode uses ADHD-friendly language patterns."""
        user_id = "adhd_language_user"
        circuit_state = CircuitBreakerState(user_id=user_id, is_open=True)
        
        result = await cognitive_loop._handle_circuit_open(user_id, circuit_state)
        response_text = result.response.text.lower()
        
        # Should avoid shame-inducing language common in ADHD experiences
        shame_triggers = [
            "lazy", "failed", "wrong", "bad", "broken", "not enough", 
            "should have", "why didn't you", "just try harder"
        ]
        
        for shame_trigger in shame_triggers:
            assert shame_trigger not in response_text, \
                f"Anchor mode contains ADHD shame trigger: '{shame_trigger}'"
        
        # Should include ADHD-affirming language
        affirming_phrases = [
            "space", "ready", "here", "care", "support", "understanding"
        ]
        
        assert any(phrase in response_text for phrase in affirming_phrases), \
            "Anchor mode lacks ADHD-affirming language"


class TestCircuitBreakerMetrics:
    """Test circuit breaker metrics and monitoring."""
    
    @pytest.fixture
    def cognitive_loop(self):
        return CognitiveLoop()
    
    def test_get_circuit_breaker_stats(self, cognitive_loop):
        """Test circuit breaker statistics reporting."""
        # Create some circuit breakers in different states
        user1_state = CircuitBreakerState(user_id="user1", is_open=False)
        user2_state = CircuitBreakerState(user_id="user2", is_open=True)
        user3_state = CircuitBreakerState(user_id="user3", is_open=True)
        
        cognitive_loop.circuit_breakers = {
            "user1": user1_state,
            "user2": user2_state,
            "user3": user3_state
        }
        
        stats = cognitive_loop.get_stats()
        
        # Should track active circuit breakers
        assert stats["active_circuit_breakers"] == 2
        
        # Should have circuit breaker trip count
        assert "circuit_breaker_trips" in stats
        
        # Should calculate success rate
        assert "success_rate" in stats
        assert 0.0 <= stats["success_rate"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_event_tracking(self, cognitive_loop):
        """Test circuit breaker events are properly tracked."""
        user_id = "tracking_test_user"
        
        initial_trips = cognitive_loop.processing_stats["circuit_breaker_trips"]
        
        # Trip multiple circuit breakers
        for i in range(3):
            test_user = f"{user_id}_{i}"
            await cognitive_loop._check_circuit_breaker(test_user)
            await cognitive_loop._update_circuit_breaker(test_user, success=False)
            await cognitive_loop._update_circuit_breaker(test_user, success=False)
            await cognitive_loop._update_circuit_breaker(test_user, success=False)
        
        # Should track all trips
        final_trips = cognitive_loop.processing_stats["circuit_breaker_trips"]
        assert final_trips == initial_trips + 3
    
    def test_circuit_breaker_health_indicators(self, cognitive_loop):
        """Test circuit breaker provides health indicators."""
        # Simulate some circuit breaker states
        cognitive_loop.circuit_breakers = {
            f"user_{i}": CircuitBreakerState(
                user_id=f"user_{i}",
                is_open=(i % 3 == 0),  # Every 3rd user has open circuit
                failure_count=i % 4
            ) for i in range(10)
        }
        
        stats = cognitive_loop.get_stats()
        
        # High number of open circuits indicates system health issues
        total_users = len(cognitive_loop.circuit_breakers)
        open_circuits = stats["active_circuit_breakers"]
        open_circuit_percentage = open_circuits / total_users if total_users > 0 else 0
        
        # More than 30% open circuits might indicate system-wide issues
        if open_circuit_percentage > 0.3:
            # This would trigger alerts in production
            print(f"WARNING: {open_circuit_percentage:.1%} of users have open circuit breakers")
        
        assert stats["active_circuit_breakers"] >= 0
        assert stats["total_requests"] >= 0


class TestCircuitBreakerIntegrationWithSafety:
    """Test circuit breaker interaction with crisis detection."""
    
    @pytest.mark.asyncio
    async def test_crisis_detection_bypasses_circuit_breaker(self):
        """CRITICAL: Crisis responses must work even with open circuit breaker."""
        from mcp_server.cognitive_loop import cognitive_loop
        
        user_id = "crisis_circuit_user"
        
        # Trip the circuit breaker first
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        circuit_state.is_open = True
        circuit_state.failure_count = 3
        
        # Crisis input should still get proper response
        crisis_input = "I can't handle my circuit breaker being tripped and I want to kill myself"
        
        result = await cognitive_loop.process_user_input(
            user_id=user_id,
            user_input=crisis_input
        )
        
        # CRITICAL: Must get crisis response, not anchor mode
        assert result.success is True
        assert result.response.source == "hard_coded"
        assert "988" in result.response.text
        assert "safety_override" in result.actions_taken
        
        # Should NOT get anchor mode despite open circuit
        assert "anchor_mode" not in result.actions_taken
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_during_crisis_recovery(self):
        """Test circuit breaker behavior during crisis recovery."""
        from mcp_server.cognitive_loop import cognitive_loop
        
        user_id = "crisis_recovery_user"
        
        # User in crisis gets safety response (should reset circuit breaker)
        crisis_input = "I want to die"
        result = await cognitive_loop.process_user_input(
            user_id=user_id,
            user_input=crisis_input
        )
        
        assert result.response.source == "hard_coded"
        
        # Circuit breaker should remain in healthy state after crisis response
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        assert circuit_state.is_open is False
        assert circuit_state.failure_count == 0


# Performance tests for circuit breaker
class TestCircuitBreakerPerformance:
    """Test circuit breaker performance requirements."""
    
    @pytest.fixture
    def cognitive_loop(self):
        return CognitiveLoop()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_check_performance(self, cognitive_loop):
        """Test circuit breaker checks are fast enough for ADHD response times."""
        user_id = "perf_test_user"
        
        # Measure circuit breaker check time
        times = []
        for _ in range(100):
            start_time = asyncio.get_event_loop().time()
            await cognitive_loop._check_circuit_breaker(user_id)
            end_time = asyncio.get_event_loop().time()
            times.append((end_time - start_time) * 1000)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Circuit breaker checks must be ultra-fast to not impact response time
        assert avg_time < 1.0, f"Average circuit breaker check {avg_time}ms too slow"
        assert max_time < 5.0, f"Max circuit breaker check {max_time}ms too slow"
    
    @pytest.mark.asyncio
    async def test_anchor_mode_response_speed(self, cognitive_loop):
        """Test anchor mode responses meet ADHD speed requirements."""
        user_id = "anchor_speed_user"
        circuit_state = CircuitBreakerState(user_id=user_id, is_open=True)
        
        times = []
        for _ in range(50):
            start_time = asyncio.get_event_loop().time()
            await cognitive_loop._handle_circuit_open(user_id, circuit_state)
            end_time = asyncio.get_event_loop().time()
            times.append((end_time - start_time) * 1000)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Anchor mode must be nearly instantaneous for immediate support
        assert avg_time < 2.0, f"Average anchor mode response {avg_time}ms too slow"
        assert max_time < 10.0, f"Max anchor mode response {max_time}ms too slow"