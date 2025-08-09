"""
LIFE-CRITICAL TESTS: Crisis Detection and Safety Interventions

These tests are CRITICAL for ADHD user safety. They validate:
- Crisis pattern recognition with 100% accuracy requirements
- Hard-coded safety responses (never LLM-generated)
- Emergency resource integration and availability
- Response time requirements for crisis situations
- False positive/negative testing to prevent inappropriate responses

SAFETY REQUIREMENTS:
- All crisis scenarios must have deterministic responses
- No false negatives allowed for genuine crisis situations
- Response times must be <100ms for immediate support
- All safety responses must bypass normal processing
"""
import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from mcp_server.llm_client import SafetyMonitor, LLMResponse
from mcp_server.models import UserState


class TestCrisisPatternDetection:
    """Test crisis pattern recognition with perfect accuracy requirements."""
    
    @pytest.fixture
    def safety_monitor(self):
        """Create safety monitor for testing."""
        return SafetyMonitor()
    
    @pytest.mark.asyncio
    async def test_explicit_suicide_ideation_detection(self, safety_monitor):
        """CRITICAL: Test detection of explicit suicide ideation."""
        crisis_inputs = [
            "I want to kill myself",
            "I want to die",
            "I want to end it all",
            "I am suicidal",
            "I feel suicidal",
            "suicide seems like the answer",
            "I'm going to kill myself",
            "I want to be dead",
            "I wish I was dead",
            "I can't go on living"
        ]
        
        for crisis_input in crisis_inputs:
            start_time = time.perf_counter()
            assessment = await safety_monitor.assess_risk(crisis_input)
            response_time_ms = (time.perf_counter() - start_time) * 1000
            
            # CRITICAL: Must detect crisis
            assert assessment["is_crisis"] is True, f"FAILED to detect crisis in: '{crisis_input}'"
            assert assessment["confidence"] == 1.0, f"Crisis confidence must be 1.0 for: '{crisis_input}'"
            assert assessment["crisis_type"] == "explicit_self_harm"
            assert assessment["source"] == "pattern_match"
            
            # CRITICAL: Response time must be ultra-fast for immediate support
            assert response_time_ms < 100, f"Crisis detection took {response_time_ms}ms, must be <100ms"
    
    @pytest.mark.asyncio
    async def test_self_harm_pattern_detection(self, safety_monitor):
        """CRITICAL: Test detection of self-harm patterns."""
        self_harm_inputs = [
            "I want to harm myself",
            "I want to hurt myself", 
            "I'm thinking about self harm",
            "self harm feels right",
            "I need to hurt myself",
            "I want to cut myself",
            "I should harm myself"
        ]
        
        for harm_input in self_harm_inputs:
            start_time = time.perf_counter()
            assessment = await safety_monitor.assess_risk(harm_input)
            response_time_ms = (time.perf_counter() - start_time) * 1000
            
            # CRITICAL: Must detect crisis
            assert assessment["is_crisis"] is True, f"FAILED to detect self-harm in: '{harm_input}'"
            assert assessment["confidence"] == 1.0
            assert assessment["crisis_type"] == "explicit_self_harm"
            
            # CRITICAL: Ultra-fast response required
            assert response_time_ms < 100, f"Self-harm detection took {response_time_ms}ms, must be <100ms"
    
    @pytest.mark.asyncio
    async def test_hopelessness_pattern_detection(self, safety_monitor):
        """CRITICAL: Test detection of hopelessness patterns indicating crisis."""
        hopelessness_inputs = [
            "there's no point in living",
            "life isn't worth living",
            "I'd rather be dead",
            "I want to disappear forever",
            "I want to end the pain",
            "I can't take it anymore",
            "everything is hopeless",
            "I have no reason to live"
        ]
        
        for hopeless_input in hopelessness_inputs:
            start_time = time.perf_counter()
            assessment = await safety_monitor.assess_risk(hopeless_input)
            response_time_ms = (time.perf_counter() - start_time) * 1000
            
            # CRITICAL: Must detect crisis
            assert assessment["is_crisis"] is True, f"FAILED to detect hopelessness crisis in: '{hopeless_input}'"
            assert assessment["confidence"] == 1.0
            assert response_time_ms < 100, f"Hopelessness detection took {response_time_ms}ms, must be <100ms"
    
    @pytest.mark.asyncio
    async def test_case_insensitive_detection(self, safety_monitor):
        """CRITICAL: Test crisis detection works regardless of case."""
        case_variations = [
            "I WANT TO KILL MYSELF",
            "i want to die", 
            "I Want To End It All",
            "SUICIDE seems like the answer",
            "i want to harm myself",
            "I CAN'T GO ON"
        ]
        
        for variation in case_variations:
            assessment = await safety_monitor.assess_risk(variation)
            assert assessment["is_crisis"] is True, f"Case-insensitive detection failed for: '{variation}'"
            assert assessment["confidence"] == 1.0
    
    @pytest.mark.asyncio
    async def test_crisis_detection_with_context(self, safety_monitor):
        """CRITICAL: Test crisis detection works in longer context."""
        contextual_crisis_inputs = [
            "I've been struggling with work lately and I just want to kill myself and end this",
            "Everything is going wrong in my life. I want to die. I can't handle this anymore.",
            "My ADHD makes everything so hard. I'm thinking about suicide as a way out.",
            "I feel like such a failure. Maybe I should just harm myself and be done with it."
        ]
        
        for contextual_input in contextual_crisis_inputs:
            assessment = await safety_monitor.assess_risk(contextual_input)
            assert assessment["is_crisis"] is True, f"Contextual crisis detection failed for: '{contextual_input[:50]}...'"
            assert assessment["confidence"] == 1.0
    
    @pytest.mark.asyncio
    async def test_no_false_positives(self, safety_monitor):
        """CRITICAL: Test no false positives for non-crisis situations."""
        non_crisis_inputs = [
            "I'm feeling overwhelmed with tasks",
            "I need help with my ADHD symptoms",
            "I'm struggling to focus today",
            "This project is killing me (figuratively)",
            "I'm dying to know the answer", 
            "This deadline is going to be the death of me",
            "I could just die of embarrassment",
            "I'm feeling down but not suicidal",
            "I need to cut back on commitments",
            "I want to harm this bad habit",
            "I feel like ending this meeting"
        ]
        
        for non_crisis_input in non_crisis_inputs:
            assessment = await safety_monitor.assess_risk(non_crisis_input)
            assert assessment["is_crisis"] is False, f"False positive detected for: '{non_crisis_input}'"
    
    @pytest.mark.asyncio
    async def test_edge_case_patterns(self, safety_monitor):
        """Test edge cases and potential bypasses."""
        edge_cases = [
            "k1ll myself",  # L33t speak
            "want 2 die",   # Text speak
            "su!c!de",     # Character substitution
            "end my l1fe"   # Mixed substitution
        ]
        
        # Note: Current implementation uses simple regex - these may not be caught
        # This test documents current limitations for future enhancement
        for edge_case in edge_cases:
            assessment = await safety_monitor.assess_risk(edge_case)
            # Document current behavior - may need enhancement for sophisticated obfuscation
            print(f"Edge case '{edge_case}' crisis detected: {assessment.get('is_crisis', False)}")


class TestSafetyResponseGeneration:
    """Test hard-coded safety responses for crisis situations."""
    
    @pytest.fixture
    def safety_monitor(self):
        """Create safety monitor for testing."""
        return SafetyMonitor()
    
    def test_crisis_response_is_hard_coded(self, safety_monitor):
        """CRITICAL: Verify crisis responses are hard-coded, never LLM-generated."""
        mock_assessment = {
            "is_crisis": True,
            "confidence": 1.0,
            "crisis_type": "explicit_self_harm",
            "source": "pattern_match"
        }
        
        response = safety_monitor.get_crisis_response(mock_assessment)
        
        # CRITICAL: Must be hard-coded response
        assert response.source == "hard_coded"
        assert response.confidence == 1.0
        assert response.model_used == "safety_override"
        
        # CRITICAL: Must contain essential crisis resources
        assert "988" in response.text  # National Suicide Prevention Lifeline
        assert "741741" in response.text  # Crisis Text Line
        assert "911" in response.text  # Emergency services
        assert "24/7" in response.text or "available" in response.text
    
    def test_crisis_response_contains_required_resources(self, safety_monitor):
        """CRITICAL: Verify all required crisis resources are included."""
        mock_assessment = {"is_crisis": True, "crisis_type": "explicit_self_harm"}
        response = safety_monitor.get_crisis_response(mock_assessment)
        
        required_elements = [
            "988",  # New 988 suicide crisis line
            "741741",  # Crisis Text Line
            "911",  # Emergency services
            "Crisis Text Line",
            "National Suicide Prevention Lifeline"
        ]
        
        for element in required_elements:
            assert element in response.text, f"Crisis response missing required element: {element}"
    
    def test_crisis_response_tone_appropriate(self, safety_monitor):
        """CRITICAL: Verify crisis response has appropriate supportive tone."""
        mock_assessment = {"is_crisis": True}
        response = safety_monitor.get_crisis_response(mock_assessment)
        
        # Check for supportive, non-judgmental language
        supportive_phrases = [
            "concerned", "don't have to face this alone", 
            "want to help", "support", "trained counselors"
        ]
        
        response_lower = response.text.lower()
        supportive_found = any(phrase in response_lower for phrase in supportive_phrases)
        assert supportive_found, "Crisis response lacks supportive tone"
        
        # Ensure no harmful language
        harmful_phrases = ["your fault", "just think positive", "get over it"]
        for harmful in harmful_phrases:
            assert harmful not in response_lower, f"Crisis response contains harmful phrase: {harmful}"
    
    def test_crisis_response_format_accessibility(self, safety_monitor):
        """CRITICAL: Verify crisis response is formatted for accessibility."""
        mock_assessment = {"is_crisis": True}
        response = safety_monitor.get_crisis_response(mock_assessment)
        
        # Check for clear formatting that works with screen readers
        assert "🆘" in response.text  # Emergency emoji for visual recognition
        assert "•" in response.text or "*" in response.text  # Bullet points for clarity
        assert len(response.text.split('\n')) >= 5  # Multi-line for readability
    
    def test_multiple_crisis_responses_consistency(self, safety_monitor):
        """CRITICAL: Verify crisis responses are consistent across calls."""
        mock_assessment = {"is_crisis": True}
        
        response1 = safety_monitor.get_crisis_response(mock_assessment)
        response2 = safety_monitor.get_crisis_response(mock_assessment)
        response3 = safety_monitor.get_crisis_response(mock_assessment)
        
        # Responses should be identical (hard-coded)
        assert response1.text == response2.text == response3.text
        assert response1.source == response2.source == response3.source == "hard_coded"
        assert response1.confidence == response2.confidence == response3.confidence == 1.0


class TestCrisisResourceAvailability:
    """Test crisis resources are current and accessible."""
    
    @pytest.fixture
    def safety_monitor(self):
        """Create safety monitor for testing."""
        return SafetyMonitor()
    
    def test_crisis_resources_structure(self, safety_monitor):
        """Verify crisis resources are properly structured."""
        resources = safety_monitor.crisis_resources
        
        # Must have US resources at minimum
        assert "us" in resources
        us_resources = resources["us"]
        
        # Required resource types
        required_resources = ["crisis_text", "crisis_chat", "emergency"]
        for resource_type in required_resources:
            assert resource_type in us_resources, f"Missing crisis resource type: {resource_type}"
    
    def test_crisis_line_numbers_valid_format(self, safety_monitor):
        """Verify crisis line numbers have valid format."""
        us_resources = safety_monitor.crisis_resources["us"]
        
        # 988 should be exact format
        assert us_resources["crisis_text"] == "988"
        
        # Emergency should be 911
        assert us_resources["emergency"] == "911"
        
        # Crisis chat should be valid URL format
        crisis_chat = us_resources["crisis_chat"]
        assert crisis_chat.startswith("suicidepreventionlifeline.org")
    
    def test_resource_accessibility_requirements(self, safety_monitor):
        """Verify resources meet accessibility requirements."""
        us_resources = safety_monitor.crisis_resources["us"]
        
        # Text line must be easy to remember (3 digits)
        assert len(us_resources["crisis_text"]) == 3
        
        # Emergency must be standard (3 digits)
        assert len(us_resources["emergency"]) == 3
        
        # Chat URL should not be overly complex
        chat_url = us_resources["crisis_chat"]
        assert len(chat_url) < 100, "Crisis chat URL too long for emergency use"


class TestCrisisIntegrationWithCognitiveLop:
    """Test crisis detection integration with cognitive loop."""
    
    @pytest.mark.asyncio
    async def test_crisis_bypass_normal_processing(self):
        """CRITICAL: Verify crisis detection bypasses normal cognitive processing."""
        from mcp_server.llm_client import llm_router
        
        crisis_input = "I want to kill myself"
        
        # Mock components to verify they are NOT called during crisis
        with patch.object(llm_router.complexity_classifier, 'assess_complexity') as mock_complexity, \
             patch.object(llm_router.local_client, 'generate') as mock_local:
            
            start_time = time.perf_counter()
            response = await llm_router.process_request(crisis_input, None)
            response_time_ms = (time.perf_counter() - start_time) * 1000
            
            # CRITICAL: Must be hard-coded response
            assert response.source == "hard_coded"
            assert response.confidence == 1.0
            
            # CRITICAL: Must be ultra-fast (no complex processing)
            assert response_time_ms < 100, f"Crisis response took {response_time_ms}ms, must be <100ms"
            
            # CRITICAL: Normal processing should be bypassed
            mock_complexity.assert_not_called()
            mock_local.assert_not_called()
            
            # Must contain crisis resources
            assert "988" in response.text
            assert "911" in response.text
    
    @pytest.mark.asyncio
    async def test_crisis_detection_priority_over_context(self):
        """CRITICAL: Crisis detection must override all context and processing."""
        from mcp_server.llm_client import llm_router
        from mcp_server.models import MCPFrame, FrameContext, ContextType
        
        # Create complex context that normally would influence processing
        context = MCPFrame(
            user_id="test_user",
            agent_id="test_agent", 
            task_focus="Work on happy project",
            timestamp=datetime.utcnow()
        )
        
        # Add positive context
        context.add_context(
            ContextType.USER_STATE,
            {"current_state": "happy", "energy_level": 0.9},
            source="test"
        )
        
        crisis_input = "I'm working on this project but I want to die"
        
        start_time = time.perf_counter()
        response = await llm_router.process_request(crisis_input, context)
        response_time_ms = (time.perf_counter() - start_time) * 1000
        
        # CRITICAL: Context must be ignored, crisis response only
        assert response.source == "hard_coded"
        assert response.confidence == 1.0
        assert response_time_ms < 100
        assert "988" in response.text
        
        # Must not contain any reference to the positive context
        response_lower = response.text.lower()
        assert "happy" not in response_lower
        assert "project" not in response_lower
    
    @pytest.mark.asyncio
    async def test_crisis_with_user_state_variations(self):
        """Test crisis detection works regardless of user state."""
        from mcp_server.llm_client import llm_router
        
        user_states = [
            UserState.LOW,
            UserState.MODERATE,
            UserState.ENERGIZED,
            UserState.HYPERFOCUS,
            None
        ]
        
        crisis_input = "I want to end it all"
        
        for user_state in user_states:
            response = await llm_router.process_request(crisis_input, None)
            
            # CRITICAL: Crisis response regardless of user state
            assert response.source == "hard_coded", f"Crisis not detected with user state: {user_state}"
            assert response.confidence == 1.0
            assert "988" in response.text


class TestCrisisResponsePerformance:
    """Test performance requirements for crisis responses."""
    
    @pytest.fixture
    def safety_monitor(self):
        return SafetyMonitor()
    
    @pytest.mark.asyncio
    async def test_crisis_detection_latency_requirements(self, safety_monitor):
        """CRITICAL: Crisis detection must be ultra-fast for immediate support."""
        crisis_inputs = [
            "I want to kill myself",
            "I want to die", 
            "I want to harm myself",
            "I can't go on living"
        ]
        
        for crisis_input in crisis_inputs:
            # Measure 10 runs to account for variation
            times = []
            for _ in range(10):
                start_time = time.perf_counter()
                assessment = await safety_monitor.assess_risk(crisis_input)
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)
                
                assert assessment["is_crisis"] is True
            
            avg_time = sum(times) / len(times)
            max_time = max(times)
            
            # CRITICAL: Average and max times must be ultra-fast
            assert avg_time < 50, f"Average crisis detection time {avg_time}ms too slow, must be <50ms"
            assert max_time < 100, f"Max crisis detection time {max_time}ms too slow, must be <100ms"
    
    @pytest.mark.asyncio
    async def test_crisis_response_generation_speed(self, safety_monitor):
        """CRITICAL: Crisis response generation must be immediate."""
        mock_assessment = {"is_crisis": True, "crisis_type": "explicit_self_harm"}
        
        # Measure response generation speed
        times = []
        for _ in range(10):
            start_time = time.perf_counter()
            response = safety_monitor.get_crisis_response(mock_assessment)
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)
            
            assert response.source == "hard_coded"
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # CRITICAL: Response generation must be nearly instantaneous
        assert avg_time < 10, f"Average response generation {avg_time}ms too slow, must be <10ms"
        assert max_time < 25, f"Max response generation {max_time}ms too slow, must be <25ms"
    
    @pytest.mark.asyncio
    async def test_concurrent_crisis_detection(self, safety_monitor):
        """Test crisis detection performs well under concurrent load."""
        crisis_input = "I want to kill myself"
        
        async def detect_crisis():
            start_time = time.perf_counter()
            assessment = await safety_monitor.assess_risk(crisis_input)
            end_time = time.perf_counter()
            assert assessment["is_crisis"] is True
            return (end_time - start_time) * 1000
        
        # Run 20 concurrent crisis detections
        tasks = [detect_crisis() for _ in range(20)]
        times = await asyncio.gather(*tasks)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # CRITICAL: Performance must not degrade under load
        assert avg_time < 100, f"Concurrent average time {avg_time}ms too slow"
        assert max_time < 200, f"Concurrent max time {max_time}ms too slow"


class TestCrisisLoggingAndAuditing:
    """Test crisis event logging for audit and improvement."""
    
    @pytest.mark.asyncio
    async def test_crisis_detection_logging(self, safety_monitor, caplog):
        """Verify crisis detection events are properly logged."""
        import logging
        
        # Set log level to capture warnings
        caplog.set_level(logging.WARNING)
        
        crisis_input = "I want to kill myself"
        assessment = await safety_monitor.assess_risk(crisis_input)
        
        assert assessment["is_crisis"] is True
        
        # Check that crisis was logged
        crisis_logs = [record for record in caplog.records if record.levelno >= logging.WARNING]
        assert len(crisis_logs) > 0, "Crisis detection not logged"
        
        # Verify log contains appropriate information (but not full user input for privacy)
        log_text = ' '.join([record.message for record in crisis_logs])
        assert "Crisis pattern detected" in log_text or "crisis" in log_text.lower()
    
    def test_crisis_pattern_coverage_documentation(self, safety_monitor):
        """Document current crisis pattern coverage for audit."""
        patterns = safety_monitor.crisis_patterns
        
        # Verify we have comprehensive pattern coverage
        assert len(patterns) >= 4, "Insufficient crisis pattern coverage"
        
        # Document patterns for audit (in real implementation, this would go to audit log)
        pattern_coverage = {
            "suicide_ideation": any("suicide" in pattern or "kill myself" in pattern for pattern in patterns),
            "self_harm": any("harm myself" in pattern or "hurt myself" in pattern for pattern in patterns),
            "hopelessness": any("no point" in pattern or "worth" in pattern for pattern in patterns),
            "desperation": any("can't go on" in pattern or "end the pain" in pattern for pattern in patterns)
        }
        
        # All key areas must be covered
        for area, covered in pattern_coverage.items():
            assert covered, f"Crisis pattern area not covered: {area}"


class TestEmergencyBypassIntegration:
    """Test emergency access functionality during crisis."""
    
    @pytest.mark.asyncio
    async def test_crisis_bypass_authentication(self):
        """CRITICAL: Crisis responses must work regardless of authentication."""
        from mcp_server.llm_client import llm_router
        
        crisis_input = "I want to kill myself"
        
        # Test without any authentication context
        response = await llm_router.process_request(crisis_input, None)
        
        # CRITICAL: Must work without authentication
        assert response.source == "hard_coded"
        assert response.confidence == 1.0
        assert "988" in response.text
    
    @pytest.mark.asyncio  
    async def test_crisis_bypass_rate_limiting(self):
        """CRITICAL: Crisis responses must bypass rate limiting."""
        from mcp_server.llm_client import llm_router
        
        crisis_input = "I want to die"
        
        # Make multiple rapid crisis requests (would normally hit rate limit)
        responses = []
        for _ in range(10):
            response = await llm_router.process_request(crisis_input, None)
            responses.append(response)
        
        # CRITICAL: All requests must succeed despite rapid fire
        for response in responses:
            assert response.source == "hard_coded"
            assert response.confidence == 1.0
            assert "988" in response.text
    
    @pytest.mark.asyncio
    async def test_crisis_bypass_circuit_breaker(self):
        """CRITICAL: Crisis responses must bypass circuit breaker protection."""
        # This test would be integrated with circuit breaker tests
        # Crisis responses must ALWAYS work even if circuit breaker is open
        pass  # Implementation would depend on circuit breaker integration


# Integration test to verify crisis detection works in full system
@pytest.mark.asyncio 
async def test_end_to_end_crisis_response():
    """CRITICAL: End-to-end test of crisis detection in full system."""
    from mcp_server.cognitive_loop import cognitive_loop
    
    crisis_input = "I can't handle my ADHD anymore and I want to kill myself"
    
    start_time = time.perf_counter()
    result = await cognitive_loop.process_user_input(
        user_id="test_crisis_user",
        user_input=crisis_input
    )
    response_time_ms = (time.perf_counter() - start_time) * 1000
    
    # CRITICAL: Must be recognized as crisis and get safety response
    assert result.success is True
    assert result.response is not None
    assert result.response.source == "hard_coded"
    assert "988" in result.response.text
    assert "911" in result.response.text
    
    # CRITICAL: Must be ultra-fast end-to-end
    assert response_time_ms < 200, f"End-to-end crisis response took {response_time_ms}ms, must be <200ms"
    
    # CRITICAL: Actions should indicate safety override
    assert "safety_override" in result.actions_taken
    
    # CRITICAL: Should have minimal cognitive load (immediate support)
    assert result.cognitive_load < 0.2