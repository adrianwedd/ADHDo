"""
PERFORMANCE TESTS: ADHD-Specific Load and Performance Validation

These tests validate performance requirements critical for ADHD users:
- Sub-3 second response times for maintaining focus and engagement
- Pattern matching speed for immediate recognition and response
- Database performance under realistic ADHD usage patterns
- Memory usage and resource management during high cognitive load
- Concurrent user handling with ADHD-specific interaction patterns
- Degradation testing and recovery performance

ADHD PERFORMANCE REQUIREMENTS:
- Response times must be <3s to maintain attention and prevent frustration
- Pattern matching must be <100ms for immediate recognition
- System must handle hyperfocus sessions (extended high-frequency usage)
- Memory usage must be optimized for long-running support sessions
- Crisis detection must be ultra-fast (<100ms) regardless of load
"""
import pytest
import asyncio
import time
import psutil
import os
import statistics
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List, Tuple
import json

from mcp_server.cognitive_loop import cognitive_loop
from mcp_server.llm_client import llm_router, SafetyMonitor
from mcp_server.auth import AuthManager
from mcp_server.models import NudgeTier


class TestADHDResponseTimeRequirements:
    """Test response times meet ADHD-specific requirements."""
    
    @pytest.mark.asyncio
    async def test_basic_response_time_adhd_friendly(self):
        """Test basic responses are within ADHD-friendly time limits."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            # Mock fast response components
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.8
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            # Test ADHD-typical inputs
            adhd_inputs = [
                "I'm feeling overwhelmed",
                "I can't focus right now", 
                "Help me start this task",
                "I'm procrastinating",
                "I need a quick win"
            ]
            
            for user_input in adhd_inputs:
                start_time = time.perf_counter()
                result = await cognitive_loop.process_user_input(
                    user_id="perf_test_user",
                    user_input=user_input
                )
                response_time = (time.perf_counter() - start_time) * 1000
                
                # CRITICAL: Must be under 3 seconds for ADHD attention span
                assert result.success is True
                assert response_time < 3000, f"Response time {response_time}ms exceeds 3s ADHD limit for input: '{user_input}'"
                
                # Ideal response time for ADHD is under 1.5 seconds
                if response_time > 1500:
                    print(f"WARNING: Response time {response_time}ms approaching ADHD attention limit")
    
    @pytest.mark.asyncio
    async def test_crisis_detection_ultra_fast_response(self):
        """Test crisis detection meets ultra-fast response requirements."""
        safety_monitor = SafetyMonitor()
        
        crisis_inputs = [
            "I want to kill myself",
            "I want to die",
            "I want to harm myself",
            "I can't go on living"
        ]
        
        for crisis_input in crisis_inputs:
            # Multiple runs for statistical accuracy
            times = []
            for _ in range(20):
                start_time = time.perf_counter()
                assessment = await safety_monitor.assess_risk(crisis_input)
                end_time = time.perf_counter()
                response_time = (end_time - start_time) * 1000
                times.append(response_time)
                
                assert assessment["is_crisis"] is True
            
            # Statistical analysis of response times
            avg_time = statistics.mean(times)
            max_time = max(times)
            p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
            
            # CRITICAL: Crisis detection must be ultra-fast
            assert avg_time < 50, f"Crisis detection average {avg_time}ms too slow"
            assert max_time < 100, f"Crisis detection max {max_time}ms too slow"  
            assert p95_time < 75, f"Crisis detection P95 {p95_time}ms too slow"
    
    @pytest.mark.asyncio
    async def test_pattern_matching_speed(self):
        """Test pattern matching speed for ADHD quick responses."""
        # Test the quick response pattern matching
        quick_response_inputs = [
            "ready",
            "let's go", 
            "stuck",
            "overwhelmed",
            "tired",
            "focused"
        ]
        
        for user_input in quick_response_inputs:
            # Test pattern matching speed directly
            times = []
            for _ in range(50):
                start_time = time.perf_counter()
                response = llm_router._get_quick_response(user_input)
                end_time = time.perf_counter()
                response_time = (end_time - start_time) * 1000
                times.append(response_time)
            
            avg_time = statistics.mean(times)
            max_time = max(times)
            
            # Pattern matching must be nearly instantaneous
            assert avg_time < 10, f"Pattern matching average {avg_time}ms too slow for '{user_input}'"
            assert max_time < 25, f"Pattern matching max {max_time}ms too slow for '{user_input}'"
            
            # Should have found a response for these patterns
            if response is not None:
                assert len(response) > 0, f"Empty quick response for '{user_input}'"
    
    @pytest.mark.asyncio
    async def test_response_time_under_load(self):
        """Test response times remain ADHD-friendly under concurrent load."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.8
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            async def process_request(user_id: str):
                start_time = time.perf_counter()
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input="I need help staying focused"
                )
                response_time = (time.perf_counter() - start_time) * 1000
                return result, response_time
            
            # Simulate 20 concurrent ADHD users
            tasks = [process_request(f"load_user_{i}") for i in range(20)]
            results_and_times = await asyncio.gather(*tasks)
            
            response_times = [time for result, time in results_and_times]
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            p95_time = statistics.quantiles(response_times, n=20)[18]
            
            # All requests should succeed
            for result, _ in results_and_times:
                assert result.success is True
            
            # Response times must remain ADHD-friendly under load
            assert avg_time < 3500, f"Average response time under load {avg_time}ms exceeds ADHD limit"
            assert max_time < 5000, f"Max response time under load {max_time}ms exceeds reasonable ADHD limit"
            assert p95_time < 4000, f"P95 response time under load {p95_time}ms too high"


class TestADHDUsagePatterns:
    """Test performance under ADHD-specific usage patterns."""
    
    @pytest.mark.asyncio
    async def test_hyperfocus_session_performance(self):
        """Test system performance during hyperfocus sessions (extended high usage)."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.4
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.8
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            # Simulate hyperfocus session: many rapid requests over time
            hyperfocus_user = "hyperfocus_test_user"
            request_count = 100
            
            response_times = []
            memory_usage = []
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            for i in range(request_count):
                start_time = time.perf_counter()
                result = await cognitive_loop.process_user_input(
                    user_id=hyperfocus_user,
                    user_input=f"Help me with step {i+1} of my project"
                )
                response_time = (time.perf_counter() - start_time) * 1000
                response_times.append(response_time)
                
                assert result.success is True
                
                # Track memory usage every 10 requests
                if i % 10 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_usage.append(current_memory)
                
                # Small delay to simulate realistic hyperfocus typing speed
                await asyncio.sleep(0.01)
            
            final_memory = process.memory_info().rss / 1024 / 1024
            
            # Performance should not degrade significantly during hyperfocus
            first_10_avg = statistics.mean(response_times[:10])
            last_10_avg = statistics.mean(response_times[-10:])
            performance_degradation = (last_10_avg - first_10_avg) / first_10_avg
            
            assert performance_degradation < 0.5, f"Performance degraded {performance_degradation:.1%} during hyperfocus"
            
            # Memory usage should be reasonable
            memory_increase = final_memory - initial_memory
            assert memory_increase < 100, f"Memory increased {memory_increase}MB during hyperfocus session"
            
            # Response times should remain ADHD-friendly throughout
            max_response_time = max(response_times)
            assert max_response_time < 3000, f"Max response time {max_response_time}ms exceeded ADHD limit"
    
    @pytest.mark.asyncio
    async def test_interrupted_session_recovery(self):
        """Test system recovers quickly from interrupted ADHD sessions."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.6
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.8
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            interrupt_user = "interrupt_test_user"
            
            # Simulate normal activity
            for i in range(5):
                result = await cognitive_loop.process_user_input(
                    user_id=interrupt_user,
                    user_input=f"Working on task {i}"
                )
                assert result.success is True
            
            # Simulate interruption break (common in ADHD)
            await asyncio.sleep(0.1)
            
            # Return to task - should be fast to re-engage
            start_time = time.perf_counter()
            result = await cognitive_loop.process_user_input(
                user_id=interrupt_user,
                user_input="I'm back, where was I?"
            )
            recovery_time = (time.perf_counter() - start_time) * 1000
            
            assert result.success is True
            # Recovery should be fast to help with ADHD re-engagement
            assert recovery_time < 2000, f"Recovery time {recovery_time}ms too slow for ADHD re-engagement"
    
    @pytest.mark.asyncio
    async def test_task_switching_performance(self):
        """Test performance during frequent task switching (ADHD pattern)."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.8
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            switching_user = "task_switch_user"
            
            # Simulate rapid task switching
            tasks = [
                "email", "project", "calendar", "meeting prep", "research",
                "writing", "organizing", "planning", "review", "cleanup"
            ]
            
            switch_times = []
            
            for i in range(50):  # 5 cycles through all tasks
                task = tasks[i % len(tasks)]
                
                start_time = time.perf_counter()
                result = await cognitive_loop.process_user_input(
                    user_id=switching_user,
                    user_input=f"Switching to {task}",
                    task_focus=task
                )
                switch_time = (time.perf_counter() - start_time) * 1000
                switch_times.append(switch_time)
                
                assert result.success is True
            
            # Task switching should remain fast
            avg_switch_time = statistics.mean(switch_times)
            max_switch_time = max(switch_times)
            
            assert avg_switch_time < 2000, f"Average task switch time {avg_switch_time}ms too slow"
            assert max_switch_time < 3000, f"Max task switch time {max_switch_time}ms exceeds ADHD limit"
    
    @pytest.mark.asyncio
    async def test_overwhelm_pattern_performance(self):
        """Test performance when processing overwhelm patterns (common ADHD trigger)."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            # Mock high cognitive load response
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.9  # High load
            mock_frame.accessibility_score = 0.3  # Low accessibility
            mock_frame.recommended_action = "simplify_context"
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.7
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            overwhelm_inputs = [
                "I have so many tasks I don't know where to start",
                "Everything is due today and I'm panicking",
                "I can't handle all these deadlines",
                "Too many things to remember, I'm losing track",
                "My to-do list is overwhelming me"
            ]
            
            for overwhelm_input in overwhelm_inputs:
                start_time = time.perf_counter()
                result = await cognitive_loop.process_user_input(
                    user_id="overwhelm_test_user",
                    user_input=overwhelm_input
                )
                response_time = (time.perf_counter() - start_time) * 1000
                
                assert result.success is True
                # High cognitive load processing should still be fast
                assert response_time < 3000, f"Overwhelm response time {response_time}ms too slow"
                
                # Should trigger cognitive load management actions
                assert "context_simplification" in result.actions_taken or \
                       "cognitive_load_warning" in result.actions_taken


class TestDatabasePerformanceUnderADHDPatterns:
    """Test database performance under ADHD-specific usage patterns."""
    
    @pytest.mark.asyncio
    async def test_rapid_context_switching_db_performance(self):
        """Test database handles rapid context switching efficiently."""
        # This would test database query performance during task switching
        # For now, we test the pattern without actual database
        
        auth_manager = AuthManager()
        
        # Simulate rapid user context changes
        user_count = 50
        operations_per_user = 20
        
        start_time = time.perf_counter()
        
        for user_id in range(user_count):
            test_user_id = f"db_test_user_{user_id}"
            
            for op in range(operations_per_user):
                # Simulate database operations during context switching
                session_id = auth_manager.create_session(test_user_id)
                session = auth_manager.validate_session(session_id)
                assert session is not None
                
                # Simulate rapid session validation (context switches)
                for _ in range(5):
                    validated = auth_manager.validate_session(session_id)
                    assert validated is not None
                
                # Cleanup
                auth_manager.revoke_session(session_id)
        
        total_time = (time.perf_counter() - start_time) * 1000
        total_operations = user_count * operations_per_user * 7  # 7 ops per cycle
        avg_op_time = total_time / total_operations
        
        # Database operations should be fast for ADHD responsiveness
        assert avg_op_time < 10, f"Average DB operation time {avg_op_time}ms too slow"
        assert total_time < 10000, f"Total DB test time {total_time}ms too long"
    
    @pytest.mark.asyncio
    async def test_memory_pattern_storage_performance(self):
        """Test memory/pattern storage performance during learning."""
        with patch('traces.memory.trace_memory') as mock_trace_memory:
            # Mock trace memory with timing
            async def timed_store_trace(trace):
                await asyncio.sleep(0.001)  # Simulate DB write time
                return True
            
            mock_trace_memory.store_trace = AsyncMock(side_effect=timed_store_trace)
            
            # Simulate pattern learning during ADHD session
            pattern_user = "pattern_test_user"
            pattern_count = 100
            
            store_times = []
            
            for i in range(pattern_count):
                start_time = time.perf_counter()
                
                # Simulate storing interaction pattern
                await mock_trace_memory.store_trace(Mock())
                
                store_time = (time.perf_counter() - start_time) * 1000
                store_times.append(store_time)
            
            avg_store_time = statistics.mean(store_times)
            max_store_time = max(store_times)
            
            # Pattern storage should not slow down user interactions
            assert avg_store_time < 50, f"Average pattern store time {avg_store_time}ms too slow"
            assert max_store_time < 100, f"Max pattern store time {max_store_time}ms too slow"
    
    def test_authentication_performance_under_load(self):
        """Test authentication performance under concurrent ADHD users."""
        auth_manager = AuthManager()
        
        # Register users for testing
        user_count = 100
        user_credentials = []
        
        for i in range(user_count):
            from mcp_server.auth import RegistrationRequest
            request = RegistrationRequest(
                name=f"Load Test User {i}",
                email=f"loadtest{i}@example.com", 
                password=f"LoadTestPass{i}23!"
            )
            response = auth_manager.register_user(request)
            assert response.success is True
            user_credentials.append((f"loadtest{i}@example.com", f"LoadTestPass{i}23!"))
        
        # Test concurrent authentication
        def authenticate_user(credentials):
            email, password = credentials
            from mcp_server.auth import LoginRequest
            start_time = time.perf_counter()
            login_request = LoginRequest(email=email, password=password)
            response = auth_manager.login_user(login_request)
            auth_time = (time.perf_counter() - start_time) * 1000
            
            assert response.success is True
            
            # Cleanup
            auth_manager.logout_user(response.session_id)
            return auth_time
        
        # Use thread pool to simulate concurrent authentication
        with ThreadPoolExecutor(max_workers=20) as executor:
            start_time = time.perf_counter()
            auth_times = list(executor.map(authenticate_user, user_credentials))
            total_time = (time.perf_counter() - start_time) * 1000
        
        avg_auth_time = statistics.mean(auth_times)
        max_auth_time = max(auth_times)
        
        # Authentication should remain fast under load
        assert avg_auth_time < 500, f"Average auth time {avg_auth_time}ms too slow under load"
        assert max_auth_time < 1000, f"Max auth time {max_auth_time}ms too slow"
        assert total_time < 20000, f"Total concurrent auth time {total_time}ms too long"


class TestMemoryUsageOptimization:
    """Test memory usage remains optimized for ADHD support sessions."""
    
    @pytest.mark.asyncio
    async def test_long_session_memory_stability(self):
        """Test memory usage remains stable during long ADHD support sessions."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            memory_samples = [initial_memory]
            session_user = "memory_session_user"
            
            # Simulate extended ADHD support session (2 hours worth of requests)
            for i in range(200):  # ~2 hours at 1 request/36 seconds average
                result = await cognitive_loop.process_user_input(
                    user_id=session_user,
                    user_input=f"Request {i}: help me stay focused"
                )
                assert result.success is True
                
                # Sample memory every 25 requests
                if i % 25 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_samples.append(current_memory)
            
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory
            
            # Memory growth should be minimal and linear
            assert memory_increase < 50, f"Memory increased {memory_increase}MB, potential leak"
            
            # Check for memory stability (no exponential growth)
            if len(memory_samples) >= 4:
                early_growth = memory_samples[2] - memory_samples[0]
                late_growth = memory_samples[-1] - memory_samples[-3]
                
                # Late growth should not be significantly more than early growth
                growth_ratio = late_growth / max(early_growth, 1)
                assert growth_ratio < 3.0, f"Memory growth accelerating: ratio {growth_ratio}"
    
    def test_circuit_breaker_memory_efficiency(self):
        """Test circuit breaker states don't consume excessive memory."""
        # Create many circuit breaker states
        user_count = 1000
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Create circuit breakers for many users
        for i in range(user_count):
            asyncio.run(cognitive_loop._check_circuit_breaker(f"cb_user_{i}"))
        
        mid_memory = process.memory_info().rss / 1024 / 1024
        
        # Trip half the circuit breakers
        for i in range(0, user_count, 2):
            user_id = f"cb_user_{i}"
            asyncio.run(cognitive_loop._update_circuit_breaker(user_id, success=False))
            asyncio.run(cognitive_loop._update_circuit_breaker(user_id, success=False))
            asyncio.run(cognitive_loop._update_circuit_breaker(user_id, success=False))
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # Memory usage should scale reasonably with circuit breaker count
        memory_per_cb = (mid_memory - initial_memory) / user_count * 1024  # KB per CB
        total_memory_increase = final_memory - initial_memory
        
        assert memory_per_cb < 1, f"Circuit breaker uses {memory_per_cb}KB each, too much"
        assert total_memory_increase < 20, f"Circuit breakers used {total_memory_increase}MB total"
    
    @pytest.mark.asyncio
    async def test_cache_memory_management(self):
        """Test response caching doesn't cause memory bloat."""
        # Test LLM router cache behavior
        cache_test_inputs = []
        for i in range(500):  # Generate many different inputs
            cache_test_inputs.append(f"Help me with task number {i} and make it unique {i*7}")
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        with patch('mcp_server.llm_client.OllamaClient.generate') as mock_generate:
            mock_response = Mock()
            mock_response.text = "Cached response"
            mock_response.source = "local"
            mock_response.confidence = 0.8
            mock_response.latency_ms = 100
            mock_response.model_used = "test"
            mock_generate.return_value = asyncio.coroutine(lambda: mock_response)()
            
            # Fill up cache
            for user_input in cache_test_inputs:
                response = await llm_router.local_client.generate(user_input)
                assert response.text == "Cached response"
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        # Cache should have reasonable memory footprint
        assert memory_increase < 30, f"Cache used {memory_increase}MB, too much for {len(cache_test_inputs)} items"
        
        # Test that cache has limits (doesn't grow indefinitely)
        cache_size = len(llm_router.local_client._cache)
        max_expected_cache_size = 200  # From the implementation
        assert cache_size <= max_expected_cache_size, f"Cache size {cache_size} exceeds limit"


class TestConcurrentUserHandling:
    """Test concurrent ADHD user handling and performance."""
    
    @pytest.mark.asyncio
    async def test_mixed_user_state_performance(self):
        """Test performance with users in different ADHD states."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            # Define different ADHD user states and their typical requests
            user_states = {
                "hyperfocus": ["deep dive into this topic", "more details please"],
                "scattered": ["what was I doing?", "help me refocus"],
                "overwhelmed": ["too many tasks", "I can't handle this"],
                "low_energy": ["need gentle nudge", "small step please"],
                "ready": ["let's do this", "I'm pumped"]
            }
            
            async def simulate_user_state(state: str, user_id: str):
                requests = user_states[state]
                times = []
                
                for i in range(10):  # 10 requests per user state
                    request = requests[i % len(requests)]
                    
                    start_time = time.perf_counter()
                    result = await cognitive_loop.process_user_input(
                        user_id=f"{state}_{user_id}",
                        user_input=f"{request} (iteration {i})"
                    )
                    response_time = (time.perf_counter() - start_time) * 1000
                    times.append(response_time)
                    
                    assert result.success is True
                
                return state, times
            
            # Run concurrent users in different states
            tasks = []
            for state in user_states.keys():
                for user_num in range(3):  # 3 users per state
                    tasks.append(simulate_user_state(state, str(user_num)))
            
            results = await asyncio.gather(*tasks)
            
            # Analyze performance by user state
            state_performance = {}
            for state, times in results:
                if state not in state_performance:
                    state_performance[state] = []
                state_performance[state].extend(times)
            
            # All states should have reasonable performance
            for state, times in state_performance.items():
                avg_time = statistics.mean(times)
                max_time = max(times)
                
                assert avg_time < 3000, f"State '{state}' average time {avg_time}ms exceeds ADHD limit"
                assert max_time < 5000, f"State '{state}' max time {max_time}ms too high"
                
                print(f"State '{state}': avg={avg_time:.1f}ms, max={max_time:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_crisis_user_priority_handling(self):
        """Test crisis users get priority even under system load."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            # Mock normal processing with delay
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.cognitive_load = 0.5
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            async def slow_normal_response(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate slow processing
                mock_resp = Mock()
                mock_resp.source = "local"
                return mock_resp
            
            # Mock fast crisis response
            async def fast_crisis_response(user_input, *args, **kwargs):
                if any(crisis_word in user_input.lower() for crisis_word in ["kill myself", "want to die"]):
                    mock_resp = Mock()
                    mock_resp.source = "hard_coded"
                    mock_resp.text = "Crisis response with resources"
                    mock_resp.confidence = 1.0
                    return mock_resp
                else:
                    return await slow_normal_response(*args, **kwargs)
            
            mock_llm_router.process_request = AsyncMock(side_effect=fast_crisis_response)
            
            async def normal_user_request(user_id: str):
                start_time = time.perf_counter()
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input="Help me with my regular task"
                )
                response_time = (time.perf_counter() - start_time) * 1000
                return "normal", result, response_time
            
            async def crisis_user_request(user_id: str):
                start_time = time.perf_counter()
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input="I can't handle this anymore and want to kill myself"
                )
                response_time = (time.perf_counter() - start_time) * 1000
                return "crisis", result, response_time
            
            # Create load with normal users + crisis user
            tasks = []
            
            # 15 normal users creating load
            for i in range(15):
                tasks.append(normal_user_request(f"normal_user_{i}"))
            
            # 2 crisis users
            for i in range(2):
                tasks.append(crisis_user_request(f"crisis_user_{i}"))
            
            results = await asyncio.gather(*tasks)
            
            # Separate results by type
            normal_times = [time for type_, result, time in results if type_ == "normal"]
            crisis_times = [time for type_, result, time in results if type_ == "crisis"]
            
            crisis_results = [result for type_, result, time in results if type_ == "crisis"]
            
            # Crisis responses should be much faster despite system load
            avg_normal_time = statistics.mean(normal_times)
            avg_crisis_time = statistics.mean(crisis_times)
            max_crisis_time = max(crisis_times)
            
            assert avg_crisis_time < 200, f"Crisis response time {avg_crisis_time}ms too slow under load"
            assert max_crisis_time < 500, f"Max crisis response time {max_crisis_time}ms too slow"
            
            # Crisis responses should be much faster than normal responses under load
            assert avg_crisis_time < avg_normal_time * 0.3, "Crisis responses not prioritized properly"
            
            # All crisis responses should be hard-coded
            for result in crisis_results:
                assert result.response.source == "hard_coded"


class TestPerformanceDegradationAndRecovery:
    """Test system behavior under stress and recovery."""
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_under_extreme_load(self):
        """Test system degrades gracefully under extreme load."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            # Mock components with occasional failures under load
            failure_count = 0
            
            async def occasionally_failing_frame_builder(*args, **kwargs):
                nonlocal failure_count
                failure_count += 1
                if failure_count % 10 == 0:  # 10% failure rate under extreme load
                    raise Exception("Simulated overload failure")
                
                mock_frame = Mock()
                mock_frame.frame = Mock()
                mock_frame.cognitive_load = 0.8  # High load during stress
                return mock_frame
            
            mock_frame_builder.build_frame = AsyncMock(side_effect=occasionally_failing_frame_builder)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            # Generate extreme load
            extreme_load_tasks = []
            for i in range(100):  # Extreme concurrent load
                task = cognitive_loop.process_user_input(
                    user_id=f"extreme_user_{i % 20}",  # 20 users hitting hard
                    user_input=f"Extreme load request {i}"
                )
                extreme_load_tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*extreme_load_tasks, return_exceptions=True)
            
            # Count successes and failures
            successes = sum(1 for result in results if not isinstance(result, Exception) and result.success)
            failures = len(results) - successes
            
            # Should handle most requests even under extreme load
            success_rate = successes / len(results)
            assert success_rate > 0.85, f"Success rate {success_rate:.2%} too low under extreme load"
            
            # Failed requests should fail gracefully (not crash the system)
            for result in results:
                if isinstance(result, Exception):
                    # Exception should be handled gracefully
                    assert "Simulated overload failure" in str(result)
                elif not result.success:
                    # Failed results should have error information
                    assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_recovery_after_component_failure(self):
        """Test system recovers after component failures."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            call_count = 0
            
            async def failing_then_recovering_component(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count <= 5:  # First 5 calls fail
                    raise Exception("Component temporarily down")
                
                # Then recover
                mock_frame = Mock()
                mock_frame.frame = Mock()
                mock_frame.cognitive_load = 0.5
                return mock_frame
            
            mock_frame_builder.build_frame = AsyncMock(side_effect=failing_then_recovering_component)
            
            mock_response = Mock()
            mock_response.source = "local"
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            recovery_user = "recovery_test_user"
            results = []
            
            # Test requests during failure and recovery
            for i in range(10):
                result = await cognitive_loop.process_user_input(
                    user_id=recovery_user,
                    user_input=f"Recovery test request {i}"
                )
                results.append(result)
                
                # Small delay between requests
                await asyncio.sleep(0.01)
            
            # First requests should fail, later ones should succeed
            early_failures = sum(1 for result in results[:5] if not result.success)
            late_successes = sum(1 for result in results[5:] if result.success)
            
            assert early_failures >= 4, "Should have failures during component downtime"
            assert late_successes >= 4, "Should recover after component restoration"
            
            # Circuit breaker should track the failures but not trip permanently
            circuit_state = await cognitive_loop._check_circuit_breaker(recovery_user)
            # May have some failure count but should recover
            assert circuit_state.failure_count < 5, "Circuit breaker should reset on recovery"
    
    def test_system_resource_limits(self):
        """Test system respects resource limits for ADHD user stability."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu_percent = process.cpu_percent()
        
        # Generate sustained load to test resource usage
        auth_manager = AuthManager()
        
        operations = 1000
        start_time = time.perf_counter()
        
        for i in range(operations):
            # Simulate typical ADHD user authentication patterns
            session_id = auth_manager.create_session(f"resource_user_{i % 50}")
            
            # Multiple rapid validations (task switching pattern)
            for _ in range(3):
                auth_manager.validate_session(session_id)
            
            # Check rate limits (impulse control testing)
            auth_manager.check_rate_limit(f"rate_user_{i % 10}", 100)
            
            # Clean up periodically
            if i % 100 == 0:
                auth_manager.cleanup_expired()
            
            auth_manager.revoke_session(session_id)
        
        end_time = time.perf_counter()
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # Resource usage should be reasonable
        memory_increase = final_memory - initial_memory
        processing_time = (end_time - start_time) * 1000
        ops_per_second = operations / ((end_time - start_time))
        
        assert memory_increase < 25, f"Memory increased {memory_increase}MB during load test"
        assert ops_per_second > 500, f"Processing rate {ops_per_second} ops/sec too slow"
        
        # System should maintain responsiveness for ADHD users
        avg_op_time = processing_time / operations
        assert avg_op_time < 1, f"Average operation time {avg_op_time}ms too slow for ADHD responsiveness"


# Utility functions for performance testing
def measure_response_time_stats(times: List[float]) -> Dict[str, float]:
    """Calculate comprehensive response time statistics."""
    if not times:
        return {}
    
    times_sorted = sorted(times)
    count = len(times)
    
    return {
        "min": min(times),
        "max": max(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "p95": times_sorted[int(0.95 * count)] if count > 20 else max(times),
        "p99": times_sorted[int(0.99 * count)] if count > 100 else max(times),
        "std_dev": statistics.stdev(times) if count > 1 else 0
    }


def assert_adhd_performance_requirements(stats: Dict[str, float], context: str = ""):
    """Assert response times meet ADHD-specific requirements."""
    context_msg = f" ({context})" if context else ""
    
    assert stats["mean"] < 3000, f"Average response time {stats['mean']:.1f}ms exceeds 3s ADHD limit{context_msg}"
    assert stats["p95"] < 4000, f"P95 response time {stats['p95']:.1f}ms too high for ADHD users{context_msg}"
    assert stats["max"] < 5000, f"Max response time {stats['max']:.1f}ms exceeds reasonable ADHD limit{context_msg}"
    
    # Ideal ADHD performance targets
    if stats["mean"] > 1500:
        print(f"WARNING: Average response time {stats['mean']:.1f}ms approaching ADHD attention limit{context_msg}")
    if stats["p95"] > 2500:
        print(f"WARNING: P95 response time {stats['p95']:.1f}ms may cause ADHD engagement issues{context_msg}")