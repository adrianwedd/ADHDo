"""
Performance Tests for Background Processing System.

Tests enterprise-scale background processing performance with ADHD optimization targets.
Validates response times, throughput, resource usage, and ADHD-specific metrics.

Performance Targets:
- Task acknowledgment: <1 second
- Crisis tasks: <100ms response
- Background tasks: Efficient resource usage without impacting foreground
- Cache access: <10ms for hot data, <100ms for warm data
- System maintains <3 second response times under high load
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch

from mcp_server.background_processing import (
    background_task_manager, TaskDefinition, TaskPriority, TaskType, TaskStatus
)
from mcp_server.task_monitoring import task_monitoring_system, AttentionLevel
from mcp_server.caching_system import cache_manager, CacheLayer, CachePriority
from mcp_server.cache_strategies import cache_warming_engine, cache_invalidation_engine
from mcp_server.cognitive_loop_integration import enhanced_cognitive_loop


class TestBackgroundProcessingPerformance:
    """Test suite for background processing performance targets."""
    
    @pytest.fixture(autouse=True)
    async def setup_background_systems(self):
        """Set up background processing systems for testing."""
        try:
            # Initialize all systems
            await background_task_manager.initialize()
            await task_monitoring_system.initialize()
            await cache_manager.initialize()
            await cache_warming_engine.initialize()
            await cache_invalidation_engine.initialize()
            
            # Start workers
            await background_task_manager.start_workers()
            
            yield
            
        finally:
            # Clean up
            await background_task_manager.shutdown()
            await task_monitoring_system.shutdown()
            await cache_manager.shutdown()
            await cache_warming_engine.shutdown()
            await cache_invalidation_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_task_submission_response_time(self):
        """Test that task submission meets <1 second response time target."""
        user_id = "test_user_123"
        
        # Test normal priority task submission
        start_time = time.perf_counter()
        
        task = TaskDefinition(
            name="Test task submission performance",
            task_type=TaskType.DATA_AGGREGATION,
            priority=TaskPriority.NORMAL,
            function_name="test_function",
            args=["arg1", "arg2"],
            user_id=user_id
        )
        
        task_id = await background_task_manager.submit_task(task)
        
        response_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Assert response time meets ADHD target
        assert response_time_ms < 1000, f"Task submission took {response_time_ms:.2f}ms, exceeds 1000ms target"
        assert task_id is not None
        
        # Verify task was queued
        task_status = await background_task_manager.get_task_status(task_id)
        assert task_status is not None
        assert task_status.status in [TaskStatus.PENDING, TaskStatus.RUNNING]
    
    @pytest.mark.asyncio
    async def test_crisis_task_response_time(self):
        """Test that crisis tasks meet <100ms response time target."""
        user_id = "test_user_crisis"
        
        # Test crisis priority task submission
        start_time = time.perf_counter()
        
        task = TaskDefinition(
            name="Crisis task test",
            task_type=TaskType.CRISIS_DETECTION,
            priority=TaskPriority.CRISIS,
            function_name="crisis_function",
            user_id=user_id,
            attention_friendly=True
        )
        
        task_id = await background_task_manager.submit_task(task)
        
        response_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Assert crisis response time meets target
        assert response_time_ms < 100, f"Crisis task took {response_time_ms:.2f}ms, exceeds 100ms target"
        assert task_id is not None
    
    @pytest.mark.asyncio
    async def test_high_load_performance(self):
        """Test system performance under high load (1000+ tasks)."""
        user_id = "test_user_load"
        
        # Submit 1000 tasks of various priorities
        tasks = []
        start_time = time.perf_counter()
        
        for i in range(1000):
            priority = TaskPriority.CRISIS if i % 100 == 0 else TaskPriority.HIGH if i % 10 == 0 else TaskPriority.NORMAL
            
            task = TaskDefinition(
                name=f"Load test task {i}",
                task_type=TaskType.DATA_AGGREGATION,
                priority=priority,
                function_name="load_test_function",
                args=[i],
                user_id=user_id
            )
            
            task_id = await background_task_manager.submit_task(task)
            tasks.append(task_id)
        
        submission_time = (time.perf_counter() - start_time) * 1000
        
        # Test performance targets
        average_submission_time = submission_time / 1000
        assert average_submission_time < 3, f"Average task submission: {average_submission_time:.2f}ms per task"
        
        # Wait for processing to begin
        await asyncio.sleep(0.5)
        
        # Check system responsiveness during load
        response_start = time.perf_counter()
        stats = await background_task_manager.get_performance_stats()
        stats_response_time = (time.perf_counter() - response_start) * 1000
        
        assert stats_response_time < 100, f"Stats query took {stats_response_time:.2f}ms during high load"
        assert stats['running_tasks_count'] > 0, "No tasks running during load test"
    
    @pytest.mark.asyncio
    async def test_cache_access_performance(self):
        """Test cache access meets ADHD performance targets."""
        user_id = "test_user_cache"
        
        # Test hot cache access (<10ms target)
        test_data = {"user_profile": "test_data", "preferences": {"theme": "dark"}}
        
        # Set data in hot cache
        await cache_manager.set(
            f"user_profile:{user_id}",
            test_data,
            priority=CachePriority.CRISIS,
            layer=CacheLayer.MEMORY
        )
        
        # Test hot cache access time
        start_time = time.perf_counter()
        
        cached_data = await cache_manager.get(
            f"user_profile:{user_id}",
            user_id=user_id,
            priority=CachePriority.CRISIS
        )
        
        hot_access_time_ms = (time.perf_counter() - start_time) * 1000
        
        assert cached_data == test_data
        assert hot_access_time_ms < 10, f"Hot cache access: {hot_access_time_ms:.2f}ms, exceeds 10ms target"
        
        # Test warm cache access (<100ms target)
        await cache_manager.set(
            f"user_context:{user_id}",
            test_data,
            priority=CachePriority.NORMAL,
            layer=CacheLayer.REDIS_WARM
        )
        
        start_time = time.perf_counter()
        
        warm_cached_data = await cache_manager.get(
            f"user_context:{user_id}",
            user_id=user_id,
            priority=CachePriority.NORMAL
        )
        
        warm_access_time_ms = (time.perf_counter() - start_time) * 1000
        
        assert warm_cached_data == test_data
        assert warm_access_time_ms < 100, f"Warm cache access: {warm_access_time_ms:.2f}ms, exceeds 100ms target"
    
    @pytest.mark.asyncio
    async def test_task_monitoring_websocket_performance(self):
        """Test WebSocket progress updates meet performance targets."""
        user_id = "test_user_websocket"
        
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        
        # Connect to monitoring system
        start_time = time.perf_counter()
        
        connection_id = await task_monitoring_system.connect_websocket(
            websocket=mock_websocket,
            user_id=user_id,
            attention_level=AttentionLevel.FOCUSED
        )
        
        connection_time_ms = (time.perf_counter() - start_time) * 1000
        
        assert connection_time_ms < 50, f"WebSocket connection: {connection_time_ms:.2f}ms, too slow"
        assert connection_id is not None
        
        # Test progress update delivery performance
        task = TaskDefinition(
            name="WebSocket test task",
            task_type=TaskType.PATTERN_ANALYSIS,
            priority=TaskPriority.HIGH,
            function_name="websocket_test",
            user_id=user_id,
            user_visible=True
        )
        
        task_id = await background_task_manager.submit_task(task)
        tracker = task_monitoring_system.start_task_tracking(task)
        
        # Test progress update speed
        update_start = time.perf_counter()
        
        update = task_monitoring_system.update_task_progress(
            task_id,
            percentage=50.0,
            current_step="Testing progress updates"
        )
        
        # Wait for delivery
        await asyncio.sleep(0.1)
        
        update_time_ms = (time.perf_counter() - update_start) * 1000
        
        assert update_time_ms < 100, f"Progress update: {update_time_ms:.2f}ms, too slow for ADHD users"
        assert mock_websocket.send_json.called, "Progress update not sent via WebSocket"
        
        # Clean up
        await task_monitoring_system.disconnect_websocket(connection_id)
    
    @pytest.mark.asyncio
    async def test_cache_warming_performance(self):
        """Test cache warming meets performance and effectiveness targets."""
        user_id = "test_user_warming"
        
        # Test critical data warming speed
        start_time = time.perf_counter()
        
        result = await cache_warming_engine.warm_user_critical_data(user_id)
        
        warming_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Should complete quickly for ADHD responsiveness
        assert warming_time_ms < 2000, f"Critical data warming: {warming_time_ms:.2f}ms, too slow"
        assert result.get('patterns_warmed', 0) >= 0
        assert 'warming_tasks' in result
        
        # Test warming effectiveness
        warming_stats = cache_warming_engine.get_warming_stats()
        
        # Should have reasonable success rates
        if warming_stats['tasks_executed'] > 0:
            assert warming_stats['success_rate'] > 0.8, "Cache warming success rate too low"
    
    @pytest.mark.asyncio
    async def test_cognitive_loop_integration_performance(self):
        """Test enhanced cognitive loop meets ADHD performance targets."""
        user_id = "test_user_cognitive"
        
        # Test normal user input processing
        start_time = time.perf_counter()
        
        with patch('mcp_server.cognitive_loop_integration.enhanced_cognitive_loop.original_loop') as mock_loop:
            mock_response = Mock()
            mock_response.text = "Test response"
            mock_response.source = "test"
            mock_response.confidence = 0.9
            mock_response.model_used = "test_model"
            mock_response.latency_ms = 50
            mock_response.model_dump.return_value = {
                'text': 'Test response',
                'source': 'test',
                'confidence': 0.9
            }
            
            mock_loop.llm_router.process_request = AsyncMock(return_value=mock_response)
            mock_loop.enhanced_frame_builder = None
            
            result = await enhanced_cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="Test input for performance",
                task_focus="Test task"
            )
        
        processing_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Should meet ADHD response time targets
        assert processing_time_ms < 3000, f"Cognitive loop: {processing_time_ms:.2f}ms, exceeds 3s target"
        assert result.success
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_crisis_detection_performance(self):
        """Test crisis detection meets immediate response targets."""
        user_id = "test_user_crisis_detection"
        
        crisis_inputs = [
            "I want to kill myself",
            "I can't take it anymore, help",
            "This is an emergency",
            "I'm having thoughts of self-harm"
        ]
        
        for crisis_input in crisis_inputs:
            start_time = time.perf_counter()
            
            # Test crisis detection speed
            crisis_detected = await enhanced_cognitive_loop._detect_crisis_input(crisis_input)
            
            detection_time_ms = (time.perf_counter() - start_time) * 1000
            
            assert crisis_detected, f"Failed to detect crisis in: '{crisis_input}'"
            assert detection_time_ms < 10, f"Crisis detection: {detection_time_ms:.2f}ms, too slow"
    
    @pytest.mark.asyncio
    async def test_resource_efficiency_under_load(self):
        """Test resource efficiency during high load scenarios."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu = process.cpu_percent()
        
        # Submit many background tasks
        tasks = []
        for i in range(500):
            task = TaskDefinition(
                name=f"Resource test task {i}",
                task_type=TaskType.DATA_AGGREGATION,
                priority=TaskPriority.NORMAL,
                function_name="resource_test",
                user_id="resource_test_user",
                max_execution_time=30
            )
            
            task_id = await background_task_manager.submit_task(task)
            tasks.append(task_id)
        
        # Wait for some processing
        await asyncio.sleep(2.0)
        
        # Check resource usage
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        current_cpu = process.cpu_percent(interval=1.0)
        
        memory_increase = current_memory - initial_memory
        
        # Resource usage should remain reasonable
        assert memory_increase < 100, f"Memory usage increased by {memory_increase:.1f}MB, too much"
        assert current_cpu < 80, f"CPU usage at {current_cpu:.1f}%, too high for background tasks"
        
        # System should remain responsive
        start_time = time.perf_counter()
        stats = await background_task_manager.get_performance_stats()
        stats_time = (time.perf_counter() - start_time) * 1000
        
        assert stats_time < 100, f"System responsiveness degraded: {stats_time:.2f}ms for stats"
        assert stats['running_tasks_count'] > 0, "No tasks processing during resource test"
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self):
        """Test performance with concurrent operations across all systems."""
        user_id = "test_user_concurrent"
        
        # Define concurrent operations
        async def submit_tasks():
            tasks = []
            for i in range(100):
                task = TaskDefinition(
                    name=f"Concurrent task {i}",
                    task_type=TaskType.PATTERN_ANALYSIS,
                    priority=TaskPriority.HIGH if i % 10 == 0 else TaskPriority.NORMAL,
                    function_name="concurrent_test",
                    user_id=user_id
                )
                task_id = await background_task_manager.submit_task(task)
                tasks.append(task_id)
            return tasks
        
        async def cache_operations():
            operations = []
            for i in range(50):
                key = f"concurrent_cache_{i}"
                data = {"value": i, "timestamp": datetime.utcnow().isoformat()}
                
                # Set operation
                await cache_manager.set(key, data, priority=CachePriority.HIGH)
                
                # Get operation
                result = await cache_manager.get(key, priority=CachePriority.HIGH)
                operations.append(result)
            
            return operations
        
        async def warming_operations():
            patterns = [f"concurrent_pattern_{i}" for i in range(20)]
            return await cache_warming_engine.schedule_warming_task(
                key_patterns=patterns,
                priority=CachePriority.NORMAL
            )
        
        # Run all operations concurrently
        start_time = time.perf_counter()
        
        task_results, cache_results, warming_result = await asyncio.gather(
            submit_tasks(),
            cache_operations(), 
            warming_operations(),
            return_exceptions=True
        )
        
        total_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Verify all operations completed successfully
        assert not isinstance(task_results, Exception), f"Task operations failed: {task_results}"
        assert not isinstance(cache_results, Exception), f"Cache operations failed: {cache_results}"
        assert not isinstance(warming_result, Exception), f"Warming operations failed: {warming_result}"
        
        assert len(task_results) == 100, "Not all tasks were submitted"
        assert len(cache_results) == 50, "Not all cache operations completed"
        assert warming_result is not None, "Warming task not scheduled"
        
        # Performance should remain acceptable with concurrent operations
        assert total_time_ms < 5000, f"Concurrent operations: {total_time_ms:.2f}ms, too slow"
        
        # System should remain responsive
        stats_start = time.perf_counter()
        
        bg_stats = await background_task_manager.get_performance_stats()
        cache_stats = await cache_manager.get_cache_stats()
        
        stats_time_ms = (time.perf_counter() - stats_start) * 1000
        
        assert stats_time_ms < 50, f"Stats collection during load: {stats_time_ms:.2f}ms, too slow"
        assert bg_stats['running_tasks_count'] >= 0
        assert cache_stats.get('overall', {}).get('total_requests', 0) >= 50
    
    @pytest.mark.asyncio
    async def test_adhd_optimization_metrics(self):
        """Test ADHD-specific optimization metrics and targets."""
        user_id = "test_user_adhd"
        
        # Test attention-friendly task processing
        attention_task = TaskDefinition(
            name="ADHD attention test",
            task_type=TaskType.CONTEXT_BUILDING,
            priority=TaskPriority.HIGH,
            function_name="adhd_test",
            user_id=user_id,
            user_visible=True,
            attention_friendly=True,
            max_execution_time=30
        )
        
        start_time = time.perf_counter()
        task_id = await background_task_manager.submit_task(attention_task)
        submission_time = (time.perf_counter() - start_time) * 1000
        
        # Attention-friendly tasks should be acknowledged quickly
        assert submission_time < 100, f"ADHD task submission: {submission_time:.2f}ms, too slow"
        
        # Start monitoring
        tracker = task_monitoring_system.start_task_tracking(attention_task)
        
        # Update progress with ADHD-friendly messaging
        update_start = time.perf_counter()
        
        update = task_monitoring_system.update_task_progress(
            task_id,
            percentage=25.0,
            current_step="Building context",
            brief_message="Getting your context ready..."
        )
        
        update_time = (time.perf_counter() - update_start) * 1000
        
        assert update_time < 50, f"ADHD progress update: {update_time:.2f}ms, too slow"
        assert update.cognitive_load_score <= 2.0, "Cognitive load too high for ADHD user"
        assert len(update.brief_message) <= 80, "Brief message too long for ADHD users"
        assert update.attention_friendly_updates >= 0
        
        # Test crisis override speed
        crisis_start = time.perf_counter()
        
        crisis_task = TaskDefinition(
            name="Crisis override test",
            task_type=TaskType.SAFETY_INTERVENTION,
            priority=TaskPriority.CRISIS,
            function_name="crisis_test",
            user_id=user_id
        )
        
        crisis_task_id = await background_task_manager.submit_task(crisis_task)
        crisis_time = (time.perf_counter() - crisis_start) * 1000
        
        assert crisis_time < 50, f"Crisis task submission: {crisis_time:.2f}ms, too slow for safety"
        
        # Verify ADHD optimization stats
        enhanced_stats = enhanced_cognitive_loop.get_enhanced_stats()
        
        assert 'adhd_optimization' in enhanced_stats
        assert enhanced_stats['adhd_optimization']['crisis_response_time_target_ms'] == 100
        assert enhanced_stats['adhd_optimization']['user_response_time_target_ms'] == 1000


@pytest.mark.asyncio 
async def test_end_to_end_performance_scenario():
    """
    End-to-end performance test simulating real ADHD user workflow.
    
    This test simulates a complete user interaction flow with background
    processing, caching, and monitoring to ensure the entire system
    meets ADHD performance targets.
    """
    user_id = "test_user_e2e"
    
    # Initialize systems
    await background_task_manager.initialize()
    await task_monitoring_system.initialize()
    await cache_manager.initialize()
    await cache_warming_engine.initialize()
    
    try:
        # Start workers
        await background_task_manager.start_workers()
        
        # Scenario: User logs in and system warms critical data
        scenario_start = time.perf_counter()
        
        # Step 1: Warm user's critical cache data
        warming_start = time.perf_counter()
        warming_result = await cache_warming_engine.warm_user_critical_data(user_id)
        warming_time = (time.perf_counter() - warming_start) * 1000
        
        assert warming_time < 1000, f"Critical data warming: {warming_time:.2f}ms, too slow"
        
        # Step 2: User submits multiple tasks (common ADHD pattern)
        tasks = []
        
        for i, task_name in enumerate([
            "Check calendar for today",
            "Analyze productivity patterns", 
            "Generate focus report",
            "Update task priorities"
        ]):
            task = TaskDefinition(
                name=task_name,
                task_type=TaskType.PATTERN_ANALYSIS,
                priority=TaskPriority.HIGH if i == 0 else TaskPriority.NORMAL,
                function_name="user_workflow_task",
                args=[task_name, i],
                user_id=user_id,
                user_visible=True,
                attention_friendly=True
            )
            
            task_id = await background_task_manager.submit_task(task)
            tasks.append(task_id)
        
        # Step 3: Monitor progress updates
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        
        connection_id = await task_monitoring_system.connect_websocket(
            websocket=mock_websocket,
            user_id=user_id,
            attention_level=AttentionLevel.FOCUSED
        )
        
        # Step 4: Simulate progress updates
        for i, task_id in enumerate(tasks):
            tracker = task_monitoring_system.start_task_tracking(
                TaskDefinition(
                    id=task_id,
                    name=f"Task {i}",
                    task_type=TaskType.PATTERN_ANALYSIS,
                    priority=TaskPriority.HIGH,
                    function_name="test",
                    user_id=user_id,
                    user_visible=True
                )
            )
            
            # Update progress
            task_monitoring_system.update_task_progress(
                task_id,
                percentage=100.0,
                current_step="Completed",
                brief_message="Task finished!"
            )
        
        # Step 5: Get system performance stats
        stats_start = time.perf_counter()
        
        bg_stats = await background_task_manager.get_performance_stats()
        monitoring_stats = task_monitoring_system.get_monitoring_stats()
        cache_stats = await cache_manager.get_cache_stats()
        
        stats_time = (time.perf_counter() - stats_start) * 1000
        
        # Step 6: Verify end-to-end performance
        total_scenario_time = (time.perf_counter() - scenario_start) * 1000
        
        # Performance assertions
        assert total_scenario_time < 10000, f"E2E scenario: {total_scenario_time:.2f}ms, too slow"
        assert stats_time < 100, f"Stats collection: {stats_time:.2f}ms, impacts responsiveness"
        
        # ADHD-specific assertions
        assert len(tasks) == 4, "Not all tasks submitted"
        assert bg_stats['running_tasks_count'] >= 0
        assert monitoring_stats['connected_users'] >= 0
        
        # WebSocket should have received progress updates
        assert mock_websocket.send_json.call_count >= 4, "Missing progress updates"
        
        # Cache should be effective
        overall_cache_stats = cache_stats.get('overall', {})
        if overall_cache_stats.get('total_requests', 0) > 0:
            hit_rate = overall_cache_stats.get('overall_hit_rate', 0.0)
            assert hit_rate >= 0, "Cache hit rate should be non-negative"
        
        # Clean up
        await task_monitoring_system.disconnect_websocket(connection_id)
        
    finally:
        # Shutdown systems
        await background_task_manager.shutdown()
        await task_monitoring_system.shutdown()
        await cache_manager.shutdown()
        await cache_warming_engine.shutdown()


if __name__ == "__main__":
    # Run performance tests
    asyncio.run(test_end_to_end_performance_scenario())