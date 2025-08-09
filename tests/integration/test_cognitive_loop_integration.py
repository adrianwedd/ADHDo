"""
INTEGRATION TESTS: Cognitive Loop End-to-End Processing

These tests validate the complete cognitive loop processing flow:
- Context assembly with ADHD-optimized information density
- Safety assessment integration throughout processing
- LLM routing decisions based on complexity and user state  
- Action execution and environmental changes
- Memory update and pattern learning
- Performance under realistic ADHD usage patterns

CRITICAL REQUIREMENTS:
- Sub-3 second response times for maintaining ADHD focus
- Context building accuracy for executive function support
- Safety assessments at every critical decision point
- Graceful degradation under load or component failure
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List

from mcp_server.cognitive_loop import cognitive_loop, CognitiveLoopResult
from mcp_server.models import MCPFrame, FrameContext, ContextType, NudgeTier, TraceMemory
from mcp_server.llm_client import LLMResponse, TaskComplexity


class TestCognitiveLoopEndToEnd:
    """Test complete cognitive loop processing flows."""
    
    @pytest.mark.asyncio
    async def test_basic_user_input_flow(self):
        """Test basic user input processing through cognitive loop."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory') as mock_trace_memory:
            
            # Mock frame builder
            mock_context_frame = Mock()
            mock_context_frame.frame = Mock()
            mock_context_frame.frame.task_focus = "test task"
            mock_context_frame.frame.context = []
            mock_context_frame.cognitive_load = 0.5
            mock_context_frame.accessibility_score = 0.8
            mock_context_frame.recommended_action = None
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_context_frame)
            
            # Mock LLM response
            mock_llm_response = LLMResponse(
                text="I understand you need help with your task. Let's break it down into smaller steps.",
                source="local",
                confidence=0.8,
                latency_ms=150.0,
                model_used="local_llm"
            )
            mock_llm_router.process_request = AsyncMock(return_value=mock_llm_response)
            
            # Mock trace memory
            mock_trace_memory.store_trace = AsyncMock()
            
            # Execute cognitive loop
            start_time = time.perf_counter()
            result = await cognitive_loop.process_user_input(
                user_id="test_user_123",
                user_input="I'm struggling with my work task",
                task_focus="Complete project report"
            )
            processing_time = (time.perf_counter() - start_time) * 1000
            
            # Verify successful processing
            assert result.success is True
            assert result.response is not None
            assert result.response.text == mock_llm_response.text
            assert result.response.source == "local"
            assert result.context_frame is not None
            assert result.cognitive_load == 0.5
            assert result.processing_time_ms > 0
            
            # Verify ADHD-appropriate response time
            assert processing_time < 3000, f"Processing took {processing_time}ms, exceeds 3s ADHD limit"
            
            # Verify components were called correctly
            mock_frame_builder.build_frame.assert_called_once()
            mock_llm_router.process_request.assert_called_once()
            mock_trace_memory.store_trace.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_crisis_detection_in_cognitive_loop(self):
        """Test crisis detection bypasses normal processing."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory') as mock_trace_memory:
            
            # Mock crisis response from LLM router
            crisis_response = LLMResponse(
                text="I'm concerned about what you're going through. You don't have to face this alone.\n\n🆘 **Immediate Support:**\n• Crisis Text Line: Text HOME to 741741\n• National Suicide Prevention Lifeline: 988\n• Emergency: 911",
                source="hard_coded",
                confidence=1.0,
                model_used="safety_override"
            )
            mock_llm_router.process_request = AsyncMock(return_value=crisis_response)
            mock_trace_memory.store_trace = AsyncMock()
            
            # Crisis input should trigger safety override
            start_time = time.perf_counter()
            result = await cognitive_loop.process_user_input(
                user_id="crisis_test_user",
                user_input="I can't handle my ADHD anymore and I want to kill myself"
            )
            processing_time = (time.perf_counter() - start_time) * 1000
            
            # Verify crisis response
            assert result.success is True
            assert result.response.source == "hard_coded"
            assert result.response.confidence == 1.0
            assert "988" in result.response.text
            assert "911" in result.response.text
            assert "safety_override" in result.actions_taken
            
            # Crisis response must be ultra-fast
            assert processing_time < 200, f"Crisis response took {processing_time}ms, must be <200ms"
            
            # Safety event should be recorded
            mock_trace_memory.store_trace.assert_called()
            trace_call_args = mock_trace_memory.store_trace.call_args[0][0]
            assert trace_call_args.event_type == "safety_override"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration in processing flow."""
        user_id = "circuit_test_user"
        
        # Pre-trip the circuit breaker
        circuit_state = await cognitive_loop._check_circuit_breaker(user_id)
        circuit_state.is_open = True
        circuit_state.failure_count = 3
        circuit_state.next_test_time = datetime.utcnow() + timedelta(hours=2)
        
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router:
            
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I need help with something"
            )
            
            # Should get anchor mode response
            assert result.success is True
            assert result.response.source == "anchor_mode"
            assert "anchor_mode" in result.actions_taken
            assert result.cognitive_load < 0.2
            
            # Normal processing should be bypassed
            mock_frame_builder.build_frame.assert_not_called()
            mock_llm_router.process_request.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_enhanced_frame_builder_integration(self):
        """Test integration with enhanced frame builder (calendar)."""
        with patch.object(cognitive_loop, 'enhanced_frame_builder') as mock_enhanced_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory') as mock_trace_memory:
            
            # Mock enhanced frame with calendar context
            mock_enhanced_frame = Mock()
            mock_enhanced_frame.frame = Mock()
            mock_enhanced_frame.frame.context = []
            mock_enhanced_frame.frame.task_focus = "Meeting preparation"
            mock_enhanced_frame.cognitive_load = 0.4
            mock_enhanced_frame.accessibility_score = 0.9
            mock_enhanced_frame.recommended_action = "clarify_focus"
            mock_enhanced_builder.build_frame = AsyncMock(return_value=mock_enhanced_frame)
            
            mock_llm_response = LLMResponse(
                text="I see you have a meeting coming up. Let's prepare step by step.",
                source="local",
                confidence=0.9
            )
            mock_llm_router.process_request = AsyncMock(return_value=mock_llm_response)
            mock_trace_memory.store_trace = AsyncMock()
            
            result = await cognitive_loop.process_user_input(
                user_id="calendar_user",
                user_input="Help me prepare for my meeting",
                task_focus="Team standup meeting"
            )
            
            # Verify enhanced frame builder was used
            mock_enhanced_builder.build_frame.assert_called_once_with(
                user_id="calendar_user",
                agent_id="main_cognitive_loop",
                task_focus="Team standup meeting", 
                include_patterns=True,
                include_calendar=True
            )
            
            # Verify processing was successful
            assert result.success is True
            assert result.context_frame is not None
            assert result.cognitive_load == 0.4
            assert "focus_clarification" in result.actions_taken
    
    @pytest.mark.asyncio
    async def test_proactive_nudge_flow(self):
        """Test proactive nudge processing flow."""
        with patch.object(cognitive_loop, 'enhanced_frame_builder') as mock_enhanced_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router:
            
            # Mock frame for proactive nudging
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.frame.context = [
                Mock(type=Mock(value="user_state"), data={"current_state": "low"})
            ]
            mock_frame.cognitive_load = 0.3
            mock_enhanced_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            # Mock gentle nudge response
            nudge_response = LLMResponse(
                text="Gentle check-in about weekly report when you're ready ✨",
                source="local",
                confidence=0.7
            )
            mock_llm_router.process_request = AsyncMock(return_value=nudge_response)
            
            result = await cognitive_loop.initiate_proactive_nudge(
                user_id="nudge_test_user",
                task_id="weekly_report",
                context={"trigger": "calendar_reminder"}
            )
            
            assert result.success is True
            assert result.response.text.startswith("Gentle check-in")
            assert "weekly report" in result.response.text.lower()
            
            # Verify frame was built for proactive context
            mock_enhanced_builder.build_frame.assert_called_once()
            call_args = mock_enhanced_builder.build_frame.call_args
            assert "Task reminder: weekly_report" in call_args[1]["task_focus"]
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test cognitive loop handles errors gracefully."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('traces.memory.trace_memory') as mock_trace_memory:
            
            # Mock frame builder to raise exception
            mock_frame_builder.build_frame = AsyncMock(side_effect=Exception("Frame building failed"))
            mock_trace_memory.store_trace = AsyncMock()
            
            result = await cognitive_loop.process_user_input(
                user_id="error_test_user",
                user_input="Help me with my task"
            )
            
            # Should fail gracefully
            assert result.success is False
            assert result.error is not None
            assert "Frame building failed" in result.error
            assert result.processing_time_ms > 0
            
            # Circuit breaker should track the failure
            circuit_state = await cognitive_loop._check_circuit_breaker("error_test_user")
            assert circuit_state.failure_count == 1
    
    @pytest.mark.asyncio
    async def test_parallel_execution_optimization(self):
        """Test parallel execution of actions, memory, and circuit breaker updates."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory') as mock_trace_memory:
            
            # Mock components with delays to test parallelization
            mock_context_frame = Mock()
            mock_context_frame.frame = Mock()
            mock_context_frame.frame.context = []
            mock_context_frame.cognitive_load = 0.6
            mock_context_frame.accessibility_score = 0.7
            mock_context_frame.recommended_action = "simplify_context"
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_context_frame)
            
            mock_llm_response = LLMResponse(
                text="Let me help you break this down.",
                source="local",
                confidence=0.8
            )
            mock_llm_router.process_request = AsyncMock(return_value=mock_llm_response)
            
            # Add artificial delays to verify parallel execution
            async def delayed_store_trace(trace):
                await asyncio.sleep(0.1)  # 100ms delay
            
            mock_trace_memory.store_trace = AsyncMock(side_effect=delayed_store_trace)
            
            start_time = time.perf_counter()
            result = await cognitive_loop.process_user_input(
                user_id="parallel_test_user",
                user_input="I have multiple complex tasks"
            )
            total_time = (time.perf_counter() - start_time) * 1000
            
            assert result.success is True
            assert "context_simplification" in result.actions_taken
            
            # Should complete faster than sequential execution would
            # (If sequential: frame+llm+trace+actions+circuit = delays would add up)
            assert total_time < 500, f"Parallel execution took {total_time}ms, may not be properly parallelized"


class TestContextAssemblyAndFrameBuilding:
    """Test context assembly with ADHD-specific optimizations."""
    
    @pytest.mark.asyncio
    async def test_context_cognitive_load_calculation(self):
        """Test cognitive load calculation during context assembly."""
        with patch('frames.builder.frame_builder') as mock_frame_builder:
            
            # Mock high cognitive load context
            high_load_frame = Mock()
            high_load_frame.frame = Mock()
            high_load_frame.cognitive_load = 0.9
            high_load_frame.accessibility_score = 0.3
            high_load_frame.recommended_action = "simplify_context"
            mock_frame_builder.build_frame = AsyncMock(return_value=high_load_frame)
            
            with patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
                 patch('traces.memory.trace_memory'):
                
                mock_response = LLMResponse(text="Simplified response", source="local")
                mock_llm_router.process_request = AsyncMock(return_value=mock_response)
                
                result = await cognitive_loop.process_user_input(
                    user_id="load_test_user",
                    user_input="I have so many things to do and I'm feeling overwhelmed"
                )
                
                assert result.success is True
                assert result.cognitive_load == 0.9
                assert "context_simplification" in result.actions_taken
    
    @pytest.mark.asyncio
    async def test_accessibility_score_integration(self):
        """Test accessibility score influences processing."""
        with patch('frames.builder.frame_builder') as mock_frame_builder:
            
            # Mock low accessibility context
            low_access_frame = Mock()
            low_access_frame.frame = Mock()
            low_access_frame.cognitive_load = 0.5
            low_access_frame.accessibility_score = 0.4
            low_access_frame.recommended_action = None
            mock_frame_builder.build_frame = AsyncMock(return_value=low_access_frame)
            
            with patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
                 patch('traces.memory.trace_memory'):
                
                mock_response = LLMResponse(text="Accessible response", source="local")
                mock_llm_router.process_request = AsyncMock(return_value=mock_response)
                
                result = await cognitive_loop.process_user_input(
                    user_id="access_test_user",
                    user_input="Help me understand this complex topic"
                )
                
                assert result.success is True
                assert "accessibility_adjustment" in result.actions_taken
    
    @pytest.mark.asyncio
    async def test_task_focus_context_integration(self):
        """Test task focus is properly integrated into context."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.frame.task_focus = "Email response to client"
            mock_frame.cognitive_load = 0.4
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = LLMResponse(text="Let's work on that email", source="local")
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            result = await cognitive_loop.process_user_input(
                user_id="focus_test_user",
                user_input="I need to respond to Sarah's message",
                task_focus="Email response to client"
            )
            
            assert result.success is True
            assert result.context_frame.task_focus == "Email response to client"
            
            # Verify frame builder was called with correct task focus
            mock_frame_builder.build_frame.assert_called_once()
            call_args = mock_frame_builder.build_frame.call_args[1]
            assert call_args["task_focus"] == "Email response to client"


class TestLLMRoutingAndProcessing:
    """Test LLM routing decisions and processing integration."""
    
    @pytest.mark.asyncio
    async def test_llm_routing_based_on_context(self):
        """Test LLM router receives proper context for routing decisions."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            # Mock context frame
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.frame.context = [
                Mock(type=Mock(value="user_state"), data={"current_state": "energized"})
            ]
            mock_frame.cognitive_load = 0.3
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = LLMResponse(text="Great energy! Let's tackle this.", source="local")
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            result = await cognitive_loop.process_user_input(
                user_id="routing_test_user",
                user_input="I'm ready to work on my project",
                nudge_tier=NudgeTier.ENCOURAGING
            )
            
            assert result.success is True
            
            # Verify LLM router was called with correct parameters
            mock_llm_router.process_request.assert_called_once()
            call_args = mock_llm_router.process_request.call_args
            assert call_args[1]["user_input"] == "I'm ready to work on my project"
            assert call_args[1]["context"] == mock_frame.frame
            assert call_args[1]["nudge_tier"] == NudgeTier.ENCOURAGING
    
    @pytest.mark.asyncio
    async def test_response_quality_validation(self):
        """Test response quality meets ADHD-specific requirements."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            # Mock high-quality ADHD response
            adhd_response = LLMResponse(
                text="Let's break this into 3 small steps: 1) Open the document 2) Write one paragraph 3) Save your progress. You've got this! 💪",
                source="local",
                confidence=0.9,
                latency_ms=1200.0
            )
            mock_llm_router.process_request = AsyncMock(return_value=adhd_response)
            
            result = await cognitive_loop.process_user_input(
                user_id="quality_test_user",
                user_input="I need to write a report but I'm procrastinating"
            )
            
            assert result.success is True
            response_text = result.response.text
            
            # ADHD-friendly response characteristics
            assert len(response_text) < 500, "Response too long for ADHD attention span"
            assert any(char.isdigit() for char in response_text), "Should include numbered steps"
            assert "💪" in response_text or any(emoji in response_text for emoji in ["✨", "🌟", "👍"]), "Should include encouraging emoji"


class TestActionExecutionAndIntegration:
    """Test action execution and environmental integrations."""
    
    @pytest.mark.asyncio
    async def test_action_execution_based_on_frame_recommendations(self):
        """Test actions are executed based on frame analysis."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            # Mock frame with specific recommendations
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.8  # High load
            mock_frame.accessibility_score = 0.4  # Low accessibility
            mock_frame.recommended_action = "clarify_focus"
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = LLMResponse(text="Let's focus on one thing", source="local")
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            result = await cognitive_loop.process_user_input(
                user_id="action_test_user",
                user_input="I have multiple urgent tasks"
            )
            
            assert result.success is True
            
            # Should execute multiple actions based on frame analysis
            expected_actions = [
                "cognitive_load_warning",  # Due to high cognitive load
                "accessibility_adjustment",  # Due to low accessibility
                "focus_clarification"  # Due to recommended action
            ]
            
            for expected_action in expected_actions:
                assert expected_action in result.actions_taken, f"Missing expected action: {expected_action}"
    
    @pytest.mark.asyncio
    async def test_environmental_change_triggers(self):
        """Test environmental changes are triggered appropriately."""
        # This would test integration with Home Assistant, notifications, etc.
        # For now, we test the action tracking mechanism
        
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.3
            mock_frame.accessibility_score = 0.9
            mock_frame.recommended_action = "simplify_context"
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = LLMResponse(text="Simplified guidance", source="local")
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            result = await cognitive_loop.process_user_input(
                user_id="env_test_user",
                user_input="This is too complex for me right now"
            )
            
            assert result.success is True
            assert "context_simplification" in result.actions_taken
            
            # In a full implementation, this would trigger:
            # - Interface simplification
            # - Notification adjustments
            # - Calendar modifications
            # - Smart home adjustments


class TestMemoryAndPatternLearning:
    """Test memory updates and pattern learning integration."""
    
    @pytest.mark.asyncio
    async def test_trace_memory_recording(self):
        """Test trace memory records interactions properly."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory') as mock_trace_memory:
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.frame.task_focus = "Study session"
            mock_frame.cognitive_load = 0.6
            mock_frame.accessibility_score = 0.8
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = LLMResponse(
                text="Let's create a study plan",
                source="local",
                confidence=0.8,
                latency_ms=800.0
            )
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            mock_trace_memory.store_trace = AsyncMock()
            
            result = await cognitive_loop.process_user_input(
                user_id="memory_test_user",
                user_input="I need to study for my exam"
            )
            
            assert result.success is True
            
            # Verify trace memory was called
            mock_trace_memory.store_trace.assert_called_once()
            trace_record = mock_trace_memory.store_trace.call_args[0][0]
            
            # Verify trace record contents
            assert trace_record.user_id == "memory_test_user"
            assert trace_record.event_type == "cognitive_interaction"
            assert trace_record.confidence == 0.8
            assert trace_record.source == "cognitive_loop"
            
            # Verify event data
            event_data = trace_record.event_data
            assert event_data["user_input"] == "I need to study for my exam"
            assert event_data["llm_response"] == "Let's create a study plan"
            assert event_data["llm_source"] == "local"
            assert event_data["cognitive_load"] == 0.6
            assert event_data["accessibility_score"] == 0.8
            assert event_data["task_focus"] == "Study session"
    
    @pytest.mark.asyncio
    async def test_safety_event_recording(self):
        """Test safety events are recorded separately."""
        with patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory') as mock_trace_memory:
            
            # Mock safety response
            safety_response = LLMResponse(
                text="I'm concerned about what you're going through...",
                source="hard_coded",
                confidence=1.0,
                model_used="safety_override"
            )
            mock_llm_router.process_request = AsyncMock(return_value=safety_response)
            mock_trace_memory.store_trace = AsyncMock()
            
            result = await cognitive_loop.process_user_input(
                user_id="safety_memory_user",
                user_input="I want to hurt myself"
            )
            
            assert result.success is True
            assert result.response.source == "hard_coded"
            
            # Should have two trace calls: safety event + regular interaction
            assert mock_trace_memory.store_trace.call_count >= 1
            
            # Check for safety event recording
            safety_trace_calls = [
                call for call in mock_trace_memory.store_trace.call_args_list
                if call[0][0].event_type == "safety_override"
            ]
            assert len(safety_trace_calls) >= 1, "Safety event not recorded"
            
            safety_trace = safety_trace_calls[0][0][0]
            assert safety_trace.event_data["response_source"] == "hard_coded"
            assert safety_trace.confidence == 1.0
            assert safety_trace.source == "safety_monitor"


class TestPerformanceUnderLoad:
    """Test cognitive loop performance under various load conditions."""
    
    @pytest.mark.asyncio
    async def test_concurrent_user_processing(self):
        """Test cognitive loop handles concurrent users effectively."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = LLMResponse(text="Concurrent response", source="local")
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            async def process_user(user_id: str):
                start_time = time.perf_counter()
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input=f"Help request from {user_id}"
                )
                processing_time = (time.perf_counter() - start_time) * 1000
                return result, processing_time
            
            # Process 10 concurrent users
            tasks = [process_user(f"user_{i}") for i in range(10)]
            results_and_times = await asyncio.gather(*tasks)
            
            # All should succeed
            for result, processing_time in results_and_times:
                assert result.success is True
                assert processing_time < 3000, f"Concurrent processing took {processing_time}ms"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage remains reasonable under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.4
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = LLMResponse(text="Memory test response", source="local")
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            # Process many requests
            for i in range(100):
                result = await cognitive_loop.process_user_input(
                    user_id=f"memory_user_{i % 10}",  # Reuse user IDs to test circuit breaker memory
                    user_input=f"Request {i}"
                )
                assert result.success is True
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 50MB for 100 requests)
            assert memory_increase < 50, f"Memory increased by {memory_increase}MB, potential memory leak"
    
    @pytest.mark.asyncio
    async def test_error_recovery_under_load(self):
        """Test system recovers gracefully from errors under load."""
        error_count = 0
        success_count = 0
        
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            # Mock intermittent failures
            async def failing_frame_builder(*args, **kwargs):
                nonlocal error_count
                if error_count < 20 and (error_count % 3 == 0):  # Fail every 3rd request for first 20
                    error_count += 1
                    raise Exception("Simulated frame builder error")
                
                mock_frame = Mock()
                mock_frame.frame = Mock()
                mock_frame.cognitive_load = 0.5
                return mock_frame
            
            mock_frame_builder.build_frame = AsyncMock(side_effect=failing_frame_builder)
            mock_response = LLMResponse(text="Recovery test", source="local")
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            # Process requests with intermittent failures
            for i in range(50):
                result = await cognitive_loop.process_user_input(
                    user_id=f"recovery_user_{i % 5}",
                    user_input=f"Request {i}"
                )
                
                if result.success:
                    success_count += 1
                
                # Even with failures, processing should continue
                assert result.processing_time_ms > 0
            
            # Should have some successes and some failures
            assert success_count > 30, f"Too many failures: only {success_count}/50 succeeded"
            assert success_count < 50, "Should have had some failures for this test"


class TestCognitiveLoopStatistics:
    """Test statistics and monitoring integration."""
    
    def test_processing_statistics_tracking(self):
        """Test processing statistics are tracked correctly."""
        initial_stats = cognitive_loop.get_stats()
        
        # Verify expected statistics fields
        expected_fields = [
            "total_requests",
            "safety_overrides", 
            "circuit_breaker_trips",
            "successful_responses",
            "active_circuit_breakers",
            "success_rate"
        ]
        
        for field in expected_fields:
            assert field in initial_stats, f"Missing statistics field: {field}"
        
        # Success rate should be between 0 and 1
        assert 0.0 <= initial_stats["success_rate"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_statistics_updates_during_processing(self):
        """Test statistics are updated during processing."""
        initial_stats = cognitive_loop.get_stats()
        initial_total = initial_stats["total_requests"]
        initial_successful = initial_stats["successful_responses"]
        
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = LLMResponse(text="Stats test", source="local")
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            # Process a successful request
            result = await cognitive_loop.process_user_input(
                user_id="stats_test_user",
                user_input="Test request for statistics"
            )
            
            assert result.success is True
            
            # Check updated statistics
            updated_stats = cognitive_loop.get_stats()
            assert updated_stats["total_requests"] == initial_total + 1
            assert updated_stats["successful_responses"] == initial_successful + 1


class TestIntegrationHealthChecks:
    """Test health and monitoring integration points."""
    
    @pytest.mark.asyncio
    async def test_cognitive_loop_health_indicators(self):
        """Test cognitive loop provides health indicators."""
        # Test with clean state
        stats = cognitive_loop.get_stats()
        
        # Health indicators
        success_rate = stats["success_rate"]
        active_circuits = stats["active_circuit_breakers"]
        total_requests = stats["total_requests"]
        
        # Basic health checks
        if total_requests > 0:
            assert success_rate > 0.0, "Success rate should be positive with requests"
        
        # Active circuit breakers indicate user struggles
        if active_circuits > 0:
            print(f"Health indicator: {active_circuits} users have circuit breakers open")
        
        # High circuit breaker percentage indicates system issues
        if total_requests > 10 and active_circuits > (total_requests * 0.3):
            print("WARNING: High percentage of users with open circuit breakers")
    
    @pytest.mark.asyncio
    async def test_component_integration_health(self):
        """Test integration health between components."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory') as mock_trace_memory:
            
            # Test each component responds
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = LLMResponse(text="Health check", source="local")
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            mock_trace_memory.store_trace = AsyncMock()
            
            result = await cognitive_loop.process_user_input(
                user_id="health_check_user",
                user_input="System health check"
            )
            
            assert result.success is True
            
            # Verify all components were called (indicating healthy integration)
            mock_frame_builder.build_frame.assert_called_once()
            mock_llm_router.process_request.assert_called_once()
            mock_trace_memory.store_trace.assert_called_once()
            
            # Response time should be healthy
            assert result.processing_time_ms < 3000, "Processing time indicates unhealthy system"