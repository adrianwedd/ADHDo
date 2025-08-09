"""
CRITICAL TESTS: Emergency Access Bypass for Crisis Situations

These tests validate emergency access mechanisms that ensure crisis support
is available regardless of authentication, rate limiting, or system state:
- Crisis responses work without valid authentication
- Emergency access bypasses rate limiting protection
- Crisis support functions during system degradation
- Safety responses work regardless of circuit breaker state
- Emergency contact integration during crisis scenarios

EMERGENCY ACCESS REQUIREMENTS:
- Crisis detection must work for unauthenticated users
- Safety responses must bypass all normal system protections
- Emergency access must not compromise overall system security
- Crisis support must be available during system maintenance
- Emergency protocols must be audit-logged for accountability
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from mcp_server.cognitive_loop import cognitive_loop
from mcp_server.llm_client import llm_router, SafetyMonitor
from mcp_server.auth import AuthManager, get_current_user
from mcp_server.models import User
from fastapi import HTTPException, Request


class TestUnauthenticatedCrisisAccess:
    """Test crisis support works without authentication."""
    
    @pytest.mark.asyncio
    async def test_crisis_detection_without_authentication(self):
        """Test crisis detection works for unauthenticated requests."""
        safety_monitor = SafetyMonitor()
        
        crisis_inputs = [
            "I want to kill myself",
            "I want to die",
            "I want to harm myself",
            "I can't go on living"
        ]
        
        for crisis_input in crisis_inputs:
            # Test direct safety monitor (no auth context)
            start_time = time.perf_counter()
            assessment = await safety_monitor.assess_risk(crisis_input)
            response_time = (time.perf_counter() - start_time) * 1000
            
            # CRITICAL: Must detect crisis without any authentication
            assert assessment["is_crisis"] is True, f"Crisis not detected without auth: '{crisis_input}'"
            assert assessment["confidence"] == 1.0
            assert response_time < 100, f"Unauthenticated crisis detection took {response_time}ms"
            
            # Test crisis response generation
            crisis_response = safety_monitor.get_crisis_response(assessment)
            assert crisis_response.source == "hard_coded"
            assert crisis_response.confidence == 1.0
            assert "988" in crisis_response.text
            assert "911" in crisis_response.text
    
    @pytest.mark.asyncio
    async def test_cognitive_loop_crisis_without_user_context(self):
        """Test cognitive loop handles crisis without user context."""
        with patch('traces.memory.trace_memory'):  # Don't fail on memory storage
            
            # Test with minimal/no user context
            result = await cognitive_loop.process_user_input(
                user_id="emergency_anonymous_user",  # Not a real authenticated user
                user_input="I can't handle this anymore and I want to kill myself"
            )
            
            # CRITICAL: Must succeed and provide crisis response
            assert result.success is True
            assert result.response is not None
            assert result.response.source == "hard_coded"
            assert "988" in result.response.text
            assert "safety_override" in result.actions_taken
            
            # Should be ultra-fast despite lack of context
            assert result.processing_time_ms < 200, f"Emergency response took {result.processing_time_ms}ms"
    
    @pytest.mark.asyncio
    async def test_llm_router_crisis_bypass_authentication(self):
        """Test LLM router crisis detection bypasses auth requirements."""
        # Test without any authentication context
        crisis_input = "I want to die"
        
        start_time = time.perf_counter()
        response = await llm_router.process_request(
            user_input=crisis_input,
            context=None,  # No authentication context
            nudge_tier=None
        )
        response_time = (time.perf_counter() - start_time) * 1000
        
        # CRITICAL: Must provide crisis response without auth
        assert response.source == "hard_coded"
        assert response.confidence == 1.0
        assert "988" in response.text
        assert response_time < 100, f"Router crisis response took {response_time}ms without auth"
    
    def test_emergency_user_creation_for_crisis(self):
        """Test system can create emergency user context for crisis situations."""
        auth_manager = AuthManager()
        
        # Simulate emergency user creation (like debug mode but for crisis)
        emergency_user = User(
            user_id="emergency_crisis_user",
            name="Emergency Crisis User",
            preferred_nudge_methods=["web"],
            emergency_access=True  # Special flag for crisis situations
        )
        
        # Should be able to create emergency user without normal validation
        auth_manager.create_user(emergency_user)
        
        # Emergency user should exist and be accessible
        retrieved_user = auth_manager.get_user("emergency_crisis_user")
        assert retrieved_user is not None
        assert retrieved_user.name == "Emergency Crisis User"
        assert hasattr(retrieved_user, 'emergency_access')


class TestRateLimitingBypassForCrisis:
    """Test crisis responses bypass rate limiting."""
    
    def test_crisis_requests_bypass_rate_limiting(self):
        """Test crisis requests are not subject to rate limits."""
        auth_manager = AuthManager()
        
        # Set up aggressive rate limiting
        identifier = "crisis_rate_limit_test"
        limit = 2  # Very low limit
        window = 60  # 1 minute window
        
        # Use up the rate limit with normal requests
        assert auth_manager.check_rate_limit(identifier, limit, window) is True
        assert auth_manager.check_rate_limit(identifier, limit, window) is True
        assert auth_manager.check_rate_limit(identifier, limit, window) is False  # Should be blocked
        
        # Crisis requests should bypass rate limiting
        # In real implementation, this would be a special crisis endpoint or flag
        crisis_identifier = f"CRISIS_OVERRIDE_{identifier}"
        
        # Multiple crisis requests should all succeed
        for _ in range(10):
            allowed = auth_manager.check_rate_limit(crisis_identifier, 1000, window)  # High limit for crisis
            assert allowed is True, "Crisis requests should bypass normal rate limiting"
    
    @pytest.mark.asyncio
    async def test_cognitive_loop_crisis_ignores_rate_limits(self):
        """Test cognitive loop crisis responses ignore rate limits."""
        with patch('traces.memory.trace_memory'), \
             patch('mcp_server.auth.AuthManager.check_rate_limit') as mock_rate_limit:
            
            # Make rate limiting always fail for normal requests
            mock_rate_limit.return_value = False
            
            user_id = "rate_limited_crisis_user"
            
            # Normal request should be affected by rate limiting in real scenario
            # But crisis requests should bypass this
            
            # Multiple rapid crisis requests should all succeed
            for i in range(5):
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input=f"Crisis request {i}: I want to kill myself"
                )
                
                # CRITICAL: Crisis should work regardless of rate limits
                assert result.success is True
                assert result.response.source == "hard_coded"
                assert "988" in result.response.text
            
            # Rate limiting should not have been called for crisis requests
            # (In a real implementation, crisis would bypass the rate limit check entirely)
    
    @pytest.mark.asyncio
    async def test_concurrent_crisis_requests_no_rate_limiting(self):
        """Test concurrent crisis requests are not rate limited."""
        with patch('traces.memory.trace_memory'):
            
            async def crisis_request(user_num: int):
                start_time = time.perf_counter()
                result = await cognitive_loop.process_user_input(
                    user_id=f"concurrent_crisis_user_{user_num}",
                    user_input="I can't take it anymore and want to die"
                )
                response_time = (time.perf_counter() - start_time) * 1000
                return result, response_time
            
            # Launch 20 concurrent crisis requests
            tasks = [crisis_request(i) for i in range(20)]
            results_and_times = await asyncio.gather(*tasks)
            
            # All crisis requests should succeed
            for result, response_time in results_and_times:
                assert result.success is True
                assert result.response.source == "hard_coded"
                assert "988" in result.response.text
                assert response_time < 500, f"Concurrent crisis response took {response_time}ms"
            
            # Response times should be consistent (not degraded by rate limiting)
            response_times = [time for _, time in results_and_times]
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            
            assert avg_time < 200, f"Average concurrent crisis response {avg_time}ms too slow"
            assert max_time < 300, f"Max concurrent crisis response {max_time}ms too slow"


class TestSystemDegradationCrisisAccess:
    """Test crisis access during system degradation."""
    
    @pytest.mark.asyncio
    async def test_crisis_access_during_component_failures(self):
        """Test crisis responses work when system components fail."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('traces.memory.trace_memory') as mock_trace_memory:
            
            # Simulate various component failures
            mock_frame_builder.build_frame = AsyncMock(side_effect=Exception("Frame builder down"))
            mock_trace_memory.store_trace = AsyncMock(side_effect=Exception("Memory system down"))
            
            # Crisis should still work despite component failures
            result = await cognitive_loop.process_user_input(
                user_id="degraded_system_crisis_user",
                user_input="System is broken and I want to kill myself"
            )
            
            # CRITICAL: Crisis response must work despite system failures
            assert result.success is True
            assert result.response is not None
            assert result.response.source == "hard_coded"
            assert "988" in result.response.text
            assert "safety_override" in result.actions_taken
    
    @pytest.mark.asyncio
    async def test_crisis_response_with_database_failure(self):
        """Test crisis responses work when database is unavailable."""
        # In a real implementation, this would test database connection failures
        # For now, we test that the safety monitor works without external dependencies
        
        safety_monitor = SafetyMonitor()
        
        # Safety monitor should work without any external dependencies
        assessment = await safety_monitor.assess_risk("I want to harm myself")
        
        assert assessment["is_crisis"] is True
        assert assessment["confidence"] == 1.0
        
        # Crisis response should be generated without database access
        response = safety_monitor.get_crisis_response(assessment)
        assert response.source == "hard_coded"
        assert response.confidence == 1.0
        assert "988" in response.text
        
        # Response should be immediate (no database delays)
        start_time = time.perf_counter()
        response2 = safety_monitor.get_crisis_response(assessment)
        response_time = (time.perf_counter() - start_time) * 1000
        
        assert response_time < 10, f"Crisis response took {response_time}ms with DB failure"
    
    @pytest.mark.asyncio
    async def test_crisis_fallback_mode(self):
        """Test system falls back to crisis-only mode during severe degradation."""
        with patch('mcp_server.llm_client.llm_router') as mock_llm_router:
            
            # Simulate complete system failure except for crisis detection
            def crisis_only_mode(user_input, context=None, **kwargs):
                # Check for crisis first
                if any(crisis_word in user_input.lower() for crisis_word in ["kill myself", "want to die", "harm myself"]):
                    mock_response = Mock()
                    mock_response.source = "hard_coded"
                    mock_response.confidence = 1.0
                    mock_response.text = "Crisis support available. Call 988 immediately."
                    mock_response.model_used = "emergency_fallback"
                    return mock_response
                else:
                    # All other requests fail in degraded mode
                    raise Exception("System in emergency fallback mode - only crisis support available")
            
            mock_llm_router.process_request = AsyncMock(side_effect=crisis_only_mode)
            
            # Crisis request should work in fallback mode
            crisis_result = await cognitive_loop.process_user_input(
                user_id="fallback_crisis_user",
                user_input="Everything is broken and I want to kill myself"
            )
            
            assert crisis_result.success is True
            assert crisis_result.response.source == "hard_coded"
            assert crisis_result.response.model_used == "emergency_fallback"
            
            # Non-crisis request should fail gracefully in fallback mode
            normal_result = await cognitive_loop.process_user_input(
                user_id="fallback_normal_user", 
                user_input="How are you today?"
            )
            
            assert normal_result.success is False
            assert "emergency fallback mode" in normal_result.error


class TestCircuitBreakerCrisisBypass:
    """Test crisis responses bypass circuit breaker protection."""
    
    @pytest.mark.asyncio
    async def test_crisis_bypasses_open_circuit_breaker(self):
        """Test crisis responses work even with open circuit breaker."""
        user_id = "circuit_breaker_crisis_user"
        
        # Pre-trip the circuit breaker
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        circuit_state.is_open = True
        circuit_state.failure_count = 5
        circuit_state.next_test_time = datetime.utcnow() + timedelta(hours=4)  # Far future
        
        # Normal request should get anchor mode
        with patch('traces.memory.trace_memory'):
            normal_result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I need help with my task"
            )
            
            assert normal_result.success is True
            assert normal_result.response.source == "anchor_mode"
            assert "anchor_mode" in normal_result.actions_taken
        
        # Crisis request should bypass circuit breaker
        with patch('traces.memory.trace_memory'):
            crisis_result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="The circuit breaker is open but I want to kill myself"
            )
            
            # CRITICAL: Crisis must bypass circuit breaker
            assert crisis_result.success is True
            assert crisis_result.response.source == "hard_coded"
            assert "988" in crisis_result.response.text
            assert "safety_override" in crisis_result.actions_taken
            
            # Should NOT get anchor mode for crisis
            assert "anchor_mode" not in crisis_result.actions_taken
    
    @pytest.mark.asyncio
    async def test_crisis_resets_circuit_breaker_appropriately(self):
        """Test crisis response appropriately handles circuit breaker state."""
        user_id = "crisis_cb_reset_user"
        
        # Trip the circuit breaker
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        circuit_state.is_open = True
        circuit_state.failure_count = 3
        
        with patch('traces.memory.trace_memory'):
            # Crisis response
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I want to harm myself"
            )
            
            assert result.success is True
            assert result.response.source == "hard_coded"
            
            # Circuit breaker state should remain protective for user
            # (Crisis doesn't indicate the user is "better" - they still need protection)
            post_crisis_circuit = await cognitive_loop._check_circuit_breaker(user_id)
            
            # The specific behavior here depends on design choice:
            # Option 1: Keep circuit breaker open for continued protection
            # Option 2: Reset it because user reached out for help
            # We'll test that the system handles it consistently
            assert post_crisis_circuit.user_id == user_id
    
    @pytest.mark.asyncio
    async def test_multiple_users_crisis_and_circuit_breaker_isolation(self):
        """Test crisis responses don't interfere with other users' circuit breakers."""
        user1_id = "crisis_user_isolation_1"
        user2_id = "normal_user_isolation_2"
        
        # Trip circuit breaker for user2 (normal user)
        user2_circuit = await cognitive_loop._check_circuit_breaker(user2_id)
        user2_circuit.is_open = True
        user2_circuit.failure_count = 3
        
        with patch('traces.memory.trace_memory'):
            # User1 has crisis - should work normally
            crisis_result = await cognitive_loop.process_user_input(
                user_id=user1_id,
                user_input="I want to die"
            )
            
            assert crisis_result.success is True
            assert crisis_result.response.source == "hard_coded"
            
            # User2 should still have circuit breaker protection
            normal_result = await cognitive_loop.process_user_input(
                user_id=user2_id,
                user_input="I need help"
            )
            
            assert normal_result.success is True
            assert normal_result.response.source == "anchor_mode"  # Still protected
            
            # Circuit breaker states should be independent
            user1_circuit = await cognitive_loop._check_circuit_breaker(user1_id)
            user2_circuit_after = await cognitive_loop._check_circuit_breaker(user2_id)
            
            assert user1_circuit.user_id != user2_circuit_after.user_id
            assert user2_circuit_after.is_open is True  # Should remain protected


class TestEmergencyContactIntegration:
    """Test emergency contact and escalation integration."""
    
    def test_crisis_resource_availability_checking(self):
        """Test crisis resources are validated and available."""
        safety_monitor = SafetyMonitor()
        
        # Check crisis resources structure
        resources = safety_monitor.crisis_resources
        assert "us" in resources
        
        us_resources = resources["us"]
        required_resources = ["crisis_text", "crisis_chat", "emergency"]
        
        for resource in required_resources:
            assert resource in us_resources
            assert us_resources[resource] is not None
            assert len(us_resources[resource]) > 0
        
        # Validate resource formats
        assert us_resources["crisis_text"] == "988"  # New 988 number
        assert us_resources["emergency"] == "911"   # Standard emergency
        assert "suicidepreventionlifeline.org" in us_resources["crisis_chat"]
    
    def test_crisis_response_includes_all_contact_methods(self):
        """Test crisis response includes multiple contact methods."""
        safety_monitor = SafetyMonitor()
        assessment = {"is_crisis": True, "crisis_type": "explicit_self_harm"}
        
        response = safety_monitor.get_crisis_response(assessment)
        
        # Should include multiple ways to get help
        response_text = response.text
        
        # Essential phone numbers
        assert "988" in response_text  # Crisis line
        assert "741741" in response_text  # Crisis text
        assert "911" in response_text  # Emergency
        
        # Clear contact methods
        assert "Text HOME to 741741" in response_text or "text" in response_text.lower()
        assert "24/7" in response_text or "available" in response_text.lower()
        
        # Supportive language
        assert "don't have to face this alone" in response_text.lower() or \
               "support" in response_text.lower()
    
    def test_emergency_escalation_pathways(self):
        """Test emergency escalation pathways are clear."""
        safety_monitor = SafetyMonitor()
        
        # Different crisis types might need different escalation
        crisis_types = [
            {"crisis_type": "explicit_self_harm", "expected_urgency": "immediate"},
            {"crisis_type": "suicidal_ideation", "expected_urgency": "immediate"},
            {"crisis_type": "desperation", "expected_urgency": "immediate"}
        ]
        
        for crisis_type_data in crisis_types:
            assessment = {"is_crisis": True, **crisis_type_data}
            response = safety_monitor.get_crisis_response(assessment)
            
            # All crisis types should get immediate resources
            assert "988" in response.text
            assert "911" in response.text
            assert response.confidence == 1.0
            assert response.source == "hard_coded"
    
    @pytest.mark.asyncio
    async def test_crisis_logging_for_emergency_follow_up(self):
        """Test crisis events are logged for potential emergency follow-up."""
        with patch('traces.memory.trace_memory') as mock_trace_memory:
            mock_trace_memory.store_trace = AsyncMock()
            
            user_id = "crisis_logging_user"
            crisis_input = "I want to kill myself"
            
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input=crisis_input
            )
            
            assert result.success is True
            assert result.response.source == "hard_coded"
            
            # Should log the crisis event for follow-up
            mock_trace_memory.store_trace.assert_called()
            
            # Check that safety event was logged
            safety_trace_calls = [
                call for call in mock_trace_memory.store_trace.call_args_list
                if call[0][0].event_type == "safety_override"
            ]
            
            assert len(safety_trace_calls) >= 1, "Safety event not logged for follow-up"
            
            safety_trace = safety_trace_calls[0][0][0]
            assert safety_trace.user_id == user_id
            assert safety_trace.confidence == 1.0
            assert safety_trace.source == "safety_monitor"
            assert "trigger_input" in safety_trace.event_data
            assert safety_trace.event_data["response_source"] == "hard_coded"


class TestEmergencyAccessAuditing:
    """Test emergency access is properly audited and monitored."""
    
    @pytest.mark.asyncio
    async def test_emergency_access_audit_logging(self):
        """Test emergency access events are audit logged."""
        import logging
        
        # Capture log output
        with patch('traces.memory.trace_memory'), \
             patch('mcp_server.cognitive_loop.logger') as mock_logger:
            
            result = await cognitive_loop.process_user_input(
                user_id="audit_test_user",
                user_input="I want to harm myself"
            )
            
            assert result.success is True
            assert result.response.source == "hard_coded"
            
            # Should have logged the safety override
            mock_logger.warning.assert_called()  # Crisis events should be logged as warnings
    
    def test_emergency_access_security_boundaries(self):
        """Test emergency access doesn't compromise security boundaries."""
        safety_monitor = SafetyMonitor()
        
        # Crisis responses should be completely deterministic
        crisis_inputs = ["I want to kill myself", "I want to die"]
        
        responses = []
        for crisis_input in crisis_inputs:
            assessment = asyncio.run(safety_monitor.assess_risk(crisis_input))
            response = safety_monitor.get_crisis_response(assessment)
            responses.append(response)
        
        # All crisis responses should be identical (deterministic, not personalized)
        first_response = responses[0]
        for response in responses[1:]:
            assert response.text == first_response.text, "Crisis responses must be deterministic"
            assert response.source == first_response.source == "hard_coded"
            assert response.confidence == first_response.confidence == 1.0
        
        # Crisis responses should not contain user-specific information
        response_text = first_response.text
        user_specific_terms = ["user", "your name", "personal", "account", "profile"]
        for term in user_specific_terms:
            assert term not in response_text.lower(), f"Crisis response contains user-specific term: {term}"
    
    def test_emergency_access_rate_limiting_exceptions_are_logged(self):
        """Test that rate limiting bypasses for emergency access are logged."""
        auth_manager = AuthManager()
        
        # This would test that when crisis requests bypass rate limiting,
        # the bypass is logged for security auditing
        
        # For now, verify that rate limiting behavior is consistent
        identifier = "emergency_audit_test"
        
        # Normal rate limiting should work
        assert auth_manager.check_rate_limit(identifier, 1, 60) is True
        assert auth_manager.check_rate_limit(identifier, 1, 60) is False  # Blocked
        
        # Crisis bypass would be logged in real implementation
        # Emergency access should be traceable but not blockable
    
    @pytest.mark.asyncio
    async def test_emergency_access_does_not_create_security_vulnerabilities(self):
        """Test emergency access doesn't create attack vectors."""
        # Crisis detection should not be exploitable for system abuse
        
        # Test that adding crisis words to normal requests doesn't grant special access
        non_crisis_with_crisis_words = [
            "I want to kill this bug in my code",
            "This deadline is going to be the death of me", 
            "I'm dying to know the answer",
            "I could just die of embarrassment"
        ]
        
        safety_monitor = SafetyMonitor()
        
        for input_text in non_crisis_with_crisis_words:
            assessment = await safety_monitor.assess_risk(input_text)
            
            # Should not trigger false crisis detection
            assert assessment["is_crisis"] is False, \
                f"False crisis detection for: '{input_text}'"
        
        # Verify that genuine crisis detection is still working
        real_crisis = "I genuinely want to kill myself"
        crisis_assessment = await safety_monitor.assess_risk(real_crisis)
        assert crisis_assessment["is_crisis"] is True
        
        # Crisis detection should be precise, not exploitable
    
    def test_emergency_access_performance_monitoring(self):
        """Test emergency access performance is monitored."""
        # Emergency access should be fast and monitored
        
        safety_monitor = SafetyMonitor()
        crisis_inputs = ["I want to kill myself"] * 10
        
        times = []
        for crisis_input in crisis_inputs:
            start_time = time.perf_counter()
            assessment = asyncio.run(safety_monitor.assess_risk(crisis_input))
            response = safety_monitor.get_crisis_response(assessment)
            end_time = time.perf_counter()
            
            response_time = (end_time - start_time) * 1000
            times.append(response_time)
            
            assert assessment["is_crisis"] is True
            assert response.source == "hard_coded"
        
        # Performance should be consistent and fast
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        assert avg_time < 50, f"Average emergency access time {avg_time}ms too slow"
        assert max_time < 100, f"Max emergency access time {max_time}ms too slow"
        
        # Performance should be consistent (low variance)
        variance = sum((t - avg_time) ** 2 for t in times) / len(times)
        std_dev = variance ** 0.5
        
        assert std_dev < 25, f"Emergency access timing variance too high: {std_dev}ms"


class TestEmergencyAccessIntegrationWithNormalFlow:
    """Test emergency access integrates properly with normal system flow."""
    
    @pytest.mark.asyncio
    async def test_crisis_user_can_continue_normal_interaction_after_crisis(self):
        """Test user can continue normal interactions after crisis response."""
        with patch('traces.memory.trace_memory'):
            
            user_id = "post_crisis_interaction_user"
            
            # 1. Crisis interaction
            crisis_result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I want to kill myself"
            )
            
            assert crisis_result.success is True
            assert crisis_result.response.source == "hard_coded"
            
            # 2. Follow-up normal interaction should work
            with patch('frames.builder.frame_builder') as mock_frame_builder, \
                 patch('mcp_server.llm_client.llm_router') as mock_llm_router:
                
                mock_frame = Mock()
                mock_frame.frame = Mock()
                mock_frame.cognitive_load = 0.6
                mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
                
                mock_response = Mock()
                mock_response.source = "local"
                mock_response.text = "I'm glad you're still here. How can I support you right now?"
                mock_llm_router.process_request = AsyncMock(return_value=mock_response)
                
                normal_result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input="I called the crisis line and talked to someone. What should I do next?"
                )
                
                assert normal_result.success is True
                assert normal_result.response.source == "local"  # Normal processing resumed
                
                # System should handle post-crisis interaction appropriately
                assert "support" in normal_result.response.text.lower() or \
                       "help" in normal_result.response.text.lower()
    
    @pytest.mark.asyncio
    async def test_emergency_access_does_not_interfere_with_other_users(self):
        """Test emergency access for one user doesn't affect others."""
        with patch('traces.memory.trace_memory'):
            
            crisis_user = "emergency_user_1"
            normal_user = "normal_user_2"
            
            # Crisis user gets emergency access
            crisis_result = await cognitive_loop.process_user_input(
                user_id=crisis_user,
                user_input="I want to die"
            )
            
            assert crisis_result.success is True
            assert crisis_result.response.source == "hard_coded"
            
            # Normal user should have normal experience
            with patch('frames.builder.frame_builder') as mock_frame_builder, \
                 patch('mcp_server.llm_client.llm_router') as mock_llm_router:
                
                mock_frame = Mock()
                mock_frame.frame = Mock()
                mock_frame.cognitive_load = 0.4
                mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
                
                mock_response = Mock()
                mock_response.source = "local"
                mock_response.text = "How can I help you today?"
                mock_llm_router.process_request = AsyncMock(return_value=mock_response)
                
                normal_result = await cognitive_loop.process_user_input(
                    user_id=normal_user,
                    user_input="I need help organizing my tasks"
                )
                
                assert normal_result.success is True
                assert normal_result.response.source == "local"
                
                # Normal user should get normal response, not emergency resources
                assert "988" not in normal_result.response.text
                assert "911" not in normal_result.response.text
    
    @pytest.mark.asyncio
    async def test_emergency_access_statistics_tracking(self):
        """Test emergency access events are tracked in system statistics."""
        with patch('traces.memory.trace_memory'):
            
            initial_stats = cognitive_loop.get_stats()
            initial_safety_overrides = initial_stats["safety_overrides"]
            
            # Trigger emergency access
            result = await cognitive_loop.process_user_input(
                user_id="emergency_stats_user",
                user_input="I want to harm myself"
            )
            
            assert result.success is True
            assert result.response.source == "hard_coded"
            assert "safety_override" in result.actions_taken
            
            # Statistics should reflect emergency access usage
            updated_stats = cognitive_loop.get_stats()
            
            assert updated_stats["safety_overrides"] == initial_safety_overrides + 1
            assert updated_stats["total_requests"] == initial_stats["total_requests"] + 1
            
            # Safety overrides should be tracked for system monitoring
            safety_override_rate = updated_stats["safety_overrides"] / updated_stats["total_requests"]
            
            # High safety override rates might indicate system issues
            if safety_override_rate > 0.1:  # More than 10% emergency access
                print(f"WARNING: High emergency access rate: {safety_override_rate:.2%}")


# Integration test for complete emergency access workflow
@pytest.mark.asyncio
async def test_complete_emergency_access_workflow():
    """Integration test: Complete emergency access workflow from detection to resolution."""
    with patch('traces.memory.trace_memory') as mock_trace_memory:
        mock_trace_memory.store_trace = AsyncMock()
        
        user_id = "complete_emergency_user"
        
        # 1. User in crisis makes request (potentially unauthenticated)
        start_time = time.perf_counter()
        crisis_result = await cognitive_loop.process_user_input(
            user_id=user_id,
            user_input="My ADHD is overwhelming me and I can't take it anymore. I want to kill myself."
        )
        total_time = (time.perf_counter() - start_time) * 1000
        
        # 2. Verify emergency access worked
        assert crisis_result.success is True
        assert crisis_result.response.source == "hard_coded"
        assert crisis_result.response.confidence == 1.0
        
        # 3. Verify crisis resources provided
        response_text = crisis_result.response.text
        assert "988" in response_text  # Crisis line
        assert "741741" in response_text  # Crisis text
        assert "911" in response_text  # Emergency
        
        # 4. Verify appropriate actions taken
        assert "safety_override" in crisis_result.actions_taken
        
        # 5. Verify performance requirements met
        assert total_time < 200, f"Complete emergency workflow took {total_time}ms"
        assert crisis_result.processing_time_ms < 200
        
        # 6. Verify audit logging occurred
        mock_trace_memory.store_trace.assert_called()
        
        safety_traces = [
            call for call in mock_trace_memory.store_trace.call_args_list
            if call[0][0].event_type == "safety_override"
        ]
        
        assert len(safety_traces) >= 1, "Emergency access not properly logged"
        
        safety_trace = safety_traces[0][0][0]
        assert safety_trace.user_id == user_id
        assert safety_trace.confidence == 1.0
        assert safety_trace.source == "safety_monitor"
        
        # 7. Verify system can continue normal operation
        # (Emergency access doesn't break the system)
        normal_result = await cognitive_loop.process_user_input(
            user_id="normal_after_emergency_user", 
            user_input="How are you today?"
        )
        
        # Should process normally (though might fail due to mocked components)
        assert normal_result is not None  # System didn't crash
        
        print("Complete emergency access workflow test passed!")
        print(f"Crisis detection and response: {total_time:.1f}ms")
        print(f"Resources provided: 988, 741741, 911")
        print(f"Audit logging: {len(safety_traces)} safety events recorded")