"""
Cache Performance Tests for MCP ADHD Server.

Tests multi-layer caching performance with ADHD optimization targets.
Validates cache hit rates, access times, warming effectiveness, and invalidation performance.

Performance Targets:
- Memory cache: <1ms access time
- Redis hot cache: <10ms access time  
- Redis warm cache: <100ms access time
- Cache hit rates: >90% for frequently accessed data
- Cache warming: Complete within user attention span
- Invalidation: <50ms for critical updates
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch

from mcp_server.caching_system import cache_manager, CacheLayer, CachePriority
from mcp_server.cache_strategies import cache_warming_engine, cache_invalidation_engine, WarmingStrategy, InvalidationStrategy


class TestCachePerformance:
    """Test suite for cache performance targets."""
    
    @pytest.fixture(autouse=True)
    async def setup_cache_systems(self):
        """Set up caching systems for testing."""
        try:
            # Initialize cache systems
            await cache_manager.initialize()
            await cache_warming_engine.initialize()
            await cache_invalidation_engine.initialize()
            
            yield
            
        finally:
            # Clean up
            await cache_manager.shutdown()
            await cache_warming_engine.shutdown()
            await cache_invalidation_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_memory_cache_access_time(self):
        """Test memory cache meets <1ms access time target."""
        user_id = "test_user_memory"
        test_data = {"profile": "test", "preferences": {"theme": "dark"}}
        
        # Set data in memory cache
        await cache_manager.set(
            f"memory_test:{user_id}",
            test_data,
            layer=CacheLayer.MEMORY,
            priority=CachePriority.CRISIS
        )
        
        # Test access time multiple times for accuracy
        access_times = []
        
        for _ in range(10):
            start_time = time.perf_counter()
            
            result = await cache_manager.get(
                f"memory_test:{user_id}",
                user_id=user_id,
                priority=CachePriority.CRISIS
            )
            
            access_time_ms = (time.perf_counter() - start_time) * 1000
            access_times.append(access_time_ms)
            
            assert result == test_data, "Cache data mismatch"
        
        avg_access_time = sum(access_times) / len(access_times)
        max_access_time = max(access_times)
        
        assert avg_access_time < 1.0, f"Memory cache avg access: {avg_access_time:.3f}ms, exceeds 1ms target"
        assert max_access_time < 2.0, f"Memory cache max access: {max_access_time:.3f}ms, too slow"
    
    @pytest.mark.asyncio
    async def test_redis_hot_cache_access_time(self):
        """Test Redis hot cache meets <10ms access time target."""
        user_id = "test_user_hot"
        test_data = {"context": "hot_data", "timestamp": datetime.utcnow().isoformat()}
        
        # Set data in hot cache
        await cache_manager.set(
            f"hot_test:{user_id}",
            test_data,
            layer=CacheLayer.REDIS_HOT,
            priority=CachePriority.HIGH
        )
        
        # Test access time multiple times
        access_times = []
        
        for _ in range(20):
            start_time = time.perf_counter()
            
            result = await cache_manager.get(
                f"hot_test:{user_id}",
                user_id=user_id,
                priority=CachePriority.HIGH
            )
            
            access_time_ms = (time.perf_counter() - start_time) * 1000
            access_times.append(access_time_ms)
            
            assert result == test_data, "Cache data mismatch"
        
        avg_access_time = sum(access_times) / len(access_times)
        max_access_time = max(access_times)
        p95_access_time = sorted(access_times)[int(len(access_times) * 0.95)]
        
        assert avg_access_time < 10.0, f"Hot cache avg access: {avg_access_time:.2f}ms, exceeds 10ms target"
        assert p95_access_time < 15.0, f"Hot cache 95th percentile: {p95_access_time:.2f}ms, too slow"
    
    @pytest.mark.asyncio
    async def test_redis_warm_cache_access_time(self):
        """Test Redis warm cache meets <100ms access time target."""
        user_id = "test_user_warm"
        test_data = {"analytics": "warm_data", "computed_results": [1, 2, 3, 4, 5]}
        
        # Set data in warm cache
        await cache_manager.set(
            f"warm_test:{user_id}",
            test_data,
            layer=CacheLayer.REDIS_WARM,
            priority=CachePriority.NORMAL
        )
        
        # Test access time
        access_times = []
        
        for _ in range(15):
            start_time = time.perf_counter()
            
            result = await cache_manager.get(
                f"warm_test:{user_id}",
                user_id=user_id,
                priority=CachePriority.NORMAL
            )
            
            access_time_ms = (time.perf_counter() - start_time) * 1000
            access_times.append(access_time_ms)
            
            assert result == test_data, "Cache data mismatch"
        
        avg_access_time = sum(access_times) / len(access_times)
        max_access_time = max(access_times)
        
        assert avg_access_time < 100.0, f"Warm cache avg access: {avg_access_time:.2f}ms, exceeds 100ms target"
        assert max_access_time < 150.0, f"Warm cache max access: {max_access_time:.2f}ms, too slow"
    
    @pytest.mark.asyncio
    async def test_cache_hit_rates(self):
        """Test cache achieves >90% hit rates for frequently accessed data."""
        user_id = "test_user_hitrate"
        
        # Pre-populate cache with test data
        test_keys = []
        for i in range(100):
            key = f"hitrate_test:{user_id}:{i}"
            data = {"id": i, "data": f"test_data_{i}"}
            
            await cache_manager.set(
                key,
                data,
                priority=CachePriority.NORMAL
            )
            test_keys.append(key)
        
        # Simulate access patterns (80% hits on first 20 keys, 20% on remaining)
        cache_hits = 0
        total_requests = 0
        
        # Frequently accessed keys (should have high hit rate)
        for _ in range(500):
            key_index = total_requests % 20  # First 20 keys
            key = test_keys[key_index]
            
            result = await cache_manager.get(key, user_id=user_id, priority=CachePriority.NORMAL)
            
            if result is not None:
                cache_hits += 1
            
            total_requests += 1
        
        # Less frequently accessed keys
        for i in range(20, 100):
            key = test_keys[i]
            result = await cache_manager.get(key, user_id=user_id, priority=CachePriority.NORMAL)
            
            if result is not None:
                cache_hits += 1
            
            total_requests += 1
        
        hit_rate = cache_hits / total_requests
        
        assert hit_rate > 0.90, f"Cache hit rate: {hit_rate:.3f}, below 90% target"
        assert total_requests == 580, "Incorrect number of requests"
    
    @pytest.mark.asyncio
    async def test_cache_warming_performance(self):
        """Test cache warming completes within ADHD attention span targets."""
        user_id = "test_user_warming"
        
        # Test critical data warming (should be very fast)
        start_time = time.perf_counter()
        
        warming_result = await cache_warming_engine.warm_user_critical_data(user_id)
        
        critical_warming_time = (time.perf_counter() - start_time) * 1000
        
        assert critical_warming_time < 2000, f"Critical warming: {critical_warming_time:.2f}ms, exceeds 2s target"
        assert 'patterns_warmed' in warming_result
        assert 'warming_tasks' in warming_result
        
        # Test pattern-based warming
        patterns = [
            f"user_context:{user_id}:*",
            f"user_preferences:{user_id}",
            f"task_history:{user_id}:*"
        ]
        
        pattern_start = time.perf_counter()
        
        task_id = await cache_warming_engine.schedule_warming_task(
            key_patterns=patterns,
            strategy=WarmingStrategy.PREDICTIVE,
            priority=CachePriority.HIGH,
            user_id=user_id,
            attention_critical=True
        )
        
        pattern_warming_time = (time.perf_counter() - pattern_start) * 1000
        
        assert pattern_warming_time < 100, f"Pattern warming scheduling: {pattern_warming_time:.2f}ms, too slow"
        assert task_id is not None, "Warming task not scheduled"
        
        # Test peak usage warming
        peak_start = time.perf_counter()
        
        peak_result = await cache_warming_engine.warm_peak_usage_data()
        
        peak_warming_time = (time.perf_counter() - peak_start) * 1000
        
        assert peak_warming_time < 5000, f"Peak warming: {peak_warming_time:.2f}ms, too slow"
        assert 'patterns_warmed' in peak_result
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_performance(self):
        """Test cache invalidation meets <50ms target for critical updates."""
        user_id = "test_user_invalidation"
        
        # Set up test data with dependencies
        parent_key = f"parent:{user_id}"
        child_keys = [f"child:{user_id}:{i}" for i in range(10)]
        
        parent_data = {"id": "parent", "children": child_keys}
        await cache_manager.set(parent_key, parent_data, priority=CachePriority.HIGH)
        
        for i, child_key in enumerate(child_keys):
            child_data = {"id": f"child_{i}", "parent": parent_key}
            await cache_manager.set(child_key, child_data, priority=CachePriority.NORMAL)
            
            # Register dependency
            cache_invalidation_engine.register_dependency(child_key, parent_key)
        
        # Test immediate invalidation performance
        start_time = time.perf_counter()
        
        invalidated_count = await cache_invalidation_engine.invalidate_with_dependencies(
            parent_key,
            strategy=InvalidationStrategy.IMMEDIATE
        )
        
        invalidation_time = (time.perf_counter() - start_time) * 1000
        
        assert invalidation_time < 50, f"Invalidation: {invalidation_time:.2f}ms, exceeds 50ms target"
        assert invalidated_count > 0, "No keys invalidated"
        
        # Verify invalidation worked
        parent_result = await cache_manager.get(parent_key, user_id=user_id)
        assert parent_result is None, "Parent key not invalidated"
        
        # Test pattern invalidation performance
        # Set up pattern test data
        pattern_keys = [f"pattern_test:{user_id}:{i}" for i in range(50)]
        
        for key in pattern_keys:
            await cache_manager.set(key, {"test": "data"}, priority=CachePriority.NORMAL)
        
        pattern_start = time.perf_counter()
        
        pattern_count = await cache_manager.invalidate_pattern(f"pattern_test:{user_id}:*")
        
        pattern_invalidation_time = (time.perf_counter() - pattern_start) * 1000
        
        assert pattern_invalidation_time < 100, f"Pattern invalidation: {pattern_invalidation_time:.2f}ms, too slow"
        assert pattern_count >= 0, "Pattern invalidation failed"
    
    @pytest.mark.asyncio
    async def test_cache_layer_promotion_performance(self):
        """Test cache layer promotion based on access patterns."""
        user_id = "test_user_promotion"
        test_key = f"promotion_test:{user_id}"
        test_data = {"frequently_accessed": True, "data": "test"}
        
        # Set data in warm cache initially
        await cache_manager.set(
            test_key,
            test_data,
            layer=CacheLayer.REDIS_WARM,
            priority=CachePriority.NORMAL
        )
        
        # Access frequently to trigger promotion
        access_times = []
        
        for i in range(20):
            start_time = time.perf_counter()
            
            result = await cache_manager.get(
                test_key,
                user_id=user_id,
                priority=CachePriority.HIGH  # Higher priority should trigger promotion
            )
            
            access_time = (time.perf_counter() - start_time) * 1000
            access_times.append(access_time)
            
            assert result == test_data, f"Data mismatch on access {i}"
            
            # Simulate frequent access pattern
            await asyncio.sleep(0.01)  # Brief pause between accesses
        
        # Later accesses should be faster due to promotion
        early_avg = sum(access_times[:5]) / 5
        late_avg = sum(access_times[-5:]) / 5
        
        # Performance should improve or stay consistent (not degrade)
        performance_ratio = late_avg / early_avg
        assert performance_ratio <= 1.5, f"Performance degraded: {performance_ratio:.2f}x slower"
        
        # All access times should be reasonable
        max_access_time = max(access_times)
        assert max_access_time < 50, f"Max access time: {max_access_time:.2f}ms, too slow"
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self):
        """Test cache performance under concurrent operations."""
        user_id = "test_user_concurrent"
        
        async def concurrent_set_operations():
            """Concurrent set operations."""
            tasks = []
            for i in range(100):
                key = f"concurrent_set:{user_id}:{i}"
                data = {"id": i, "timestamp": datetime.utcnow().isoformat()}
                
                task = cache_manager.set(
                    key,
                    data,
                    priority=CachePriority.NORMAL
                )
                tasks.append(task)
            
            return await asyncio.gather(*tasks)
        
        async def concurrent_get_operations():
            """Concurrent get operations."""
            tasks = []
            for i in range(100):
                key = f"concurrent_get:{user_id}:{i % 20}"  # Some cache hits, some misses
                
                task = cache_manager.get(
                    key,
                    user_id=user_id,
                    priority=CachePriority.NORMAL
                )
                tasks.append(task)
            
            return await asyncio.gather(*tasks)
        
        async def concurrent_invalidation_operations():
            """Concurrent invalidation operations."""
            tasks = []
            for i in range(20):
                key = f"concurrent_invalidate:{user_id}:{i}"
                
                # Set then invalidate
                await cache_manager.set(key, {"data": i}, priority=CachePriority.NORMAL)
                
                task = cache_manager.delete(key)
                tasks.append(task)
            
            return await asyncio.gather(*tasks)
        
        # Run all operations concurrently
        start_time = time.perf_counter()
        
        set_results, get_results, invalidate_results = await asyncio.gather(
            concurrent_set_operations(),
            concurrent_get_operations(),
            concurrent_invalidation_operations()
        )
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        # Verify results
        assert len(set_results) == 100, "Not all set operations completed"
        assert len(get_results) == 100, "Not all get operations completed"
        assert len(invalidate_results) == 20, "Not all invalidation operations completed"
        
        # Performance should remain acceptable under concurrency
        assert total_time < 3000, f"Concurrent operations: {total_time:.2f}ms, too slow"
        
        # Check individual operation success
        successful_sets = sum(1 for result in set_results if result)
        assert successful_sets >= 90, f"Only {successful_sets}/100 set operations succeeded"
        
        successful_invalidations = sum(1 for result in invalidate_results if result)
        assert successful_invalidations >= 18, f"Only {successful_invalidations}/20 invalidations succeeded"
    
    @pytest.mark.asyncio
    async def test_cache_compression_performance(self):
        """Test cache compression impact on performance."""
        user_id = "test_user_compression"
        
        # Test with large data that benefits from compression
        large_data = {
            "repeated_data": ["test_string"] * 1000,
            "user_id": user_id,
            "metadata": {"compressed": True}
        }
        
        # Test compressed storage performance
        start_time = time.perf_counter()
        
        await cache_manager.set(
            f"compression_test:{user_id}",
            large_data,
            priority=CachePriority.NORMAL
        )
        
        set_time = (time.perf_counter() - start_time) * 1000
        
        # Test compressed retrieval performance
        start_time = time.perf_counter()
        
        result = await cache_manager.get(
            f"compression_test:{user_id}",
            user_id=user_id,
            priority=CachePriority.NORMAL
        )
        
        get_time = (time.perf_counter() - start_time) * 1000
        
        assert result == large_data, "Compression corrupted data"
        
        # Compression should not significantly impact performance
        assert set_time < 200, f"Compressed set: {set_time:.2f}ms, too slow"
        assert get_time < 100, f"Compressed get: {get_time:.2f}ms, too slow"
        
        # Test with small data (should not be compressed)
        small_data = {"small": "data", "user": user_id}
        
        small_start = time.perf_counter()
        
        await cache_manager.set(f"small_test:{user_id}", small_data, priority=CachePriority.NORMAL)
        small_result = await cache_manager.get(f"small_test:{user_id}", user_id=user_id, priority=CachePriority.NORMAL)
        
        small_total_time = (time.perf_counter() - small_start) * 1000
        
        assert small_result == small_data, "Small data corrupted"
        assert small_total_time < 50, f"Small data operations: {small_total_time:.2f}ms, too slow"
    
    @pytest.mark.asyncio
    async def test_cache_statistics_performance(self):
        """Test cache statistics collection doesn't impact performance."""
        user_id = "test_user_stats"
        
        # Perform cache operations
        for i in range(50):
            key = f"stats_test:{user_id}:{i}"
            data = {"id": i, "test": "statistics"}
            
            await cache_manager.set(key, data, priority=CachePriority.NORMAL)
            await cache_manager.get(key, user_id=user_id, priority=CachePriority.NORMAL)
        
        # Test statistics collection performance
        stats_times = []
        
        for _ in range(10):
            start_time = time.perf_counter()
            
            stats = await cache_manager.get_cache_stats()
            
            stats_time = (time.perf_counter() - start_time) * 1000
            stats_times.append(stats_time)
            
            assert isinstance(stats, dict), "Stats should be dictionary"
            assert 'overall' in stats, "Missing overall statistics"
        
        avg_stats_time = sum(stats_times) / len(stats_times)
        max_stats_time = max(stats_times)
        
        # Statistics collection should be fast and not impact user experience
        assert avg_stats_time < 20, f"Stats collection avg: {avg_stats_time:.2f}ms, impacts responsiveness"
        assert max_stats_time < 50, f"Stats collection max: {max_stats_time:.2f}ms, too slow"
        
        # Verify statistics accuracy
        final_stats = await cache_manager.get_cache_stats()
        overall_stats = final_stats.get('overall', {})
        
        assert overall_stats.get('total_requests', 0) >= 50, "Request count tracking failed"
        assert overall_stats.get('total_hits', 0) >= 0, "Hit count should be non-negative"
    
    @pytest.mark.asyncio
    async def test_adhd_cache_optimization_targets(self):
        """Test ADHD-specific cache optimization targets."""
        user_id = "test_user_adhd_cache"
        
        # Test crisis data caching (highest priority)
        crisis_data = {"crisis_mode": True, "emergency_contacts": ["911", "988"]}
        
        crisis_start = time.perf_counter()
        
        await cache_manager.set(
            f"crisis_data:{user_id}",
            crisis_data,
            priority=CachePriority.CRISIS,
            layer=CacheLayer.MEMORY
        )
        
        result = await cache_manager.get(
            f"crisis_data:{user_id}",
            user_id=user_id,
            priority=CachePriority.CRISIS
        )
        
        crisis_time = (time.perf_counter() - crisis_start) * 1000
        
        assert result == crisis_data, "Crisis data not cached correctly"
        assert crisis_time < 5, f"Crisis data access: {crisis_time:.2f}ms, too slow for emergency"
        
        # Test attention-critical data caching
        attention_data = {"focus_timer": 25, "current_task": "Important work"}
        
        attention_start = time.perf_counter()
        
        await cache_manager.set(
            f"attention_data:{user_id}",
            attention_data,
            priority=CachePriority.HIGH
        )
        
        attention_result = await cache_manager.get(
            f"attention_data:{user_id}",
            user_id=user_id,
            priority=CachePriority.HIGH
        )
        
        attention_time = (time.perf_counter() - attention_start) * 1000
        
        assert attention_result == attention_data, "Attention data not cached correctly"
        assert attention_time < 20, f"Attention data access: {attention_time:.2f}ms, impacts focus"
        
        # Test cognitive load consideration in caching
        complex_data = {"cognitive_load": 0.9, "recommendations": ["take_break", "simplify_task"]}
        
        await cache_manager.set(
            f"cognitive_state:{user_id}",
            complex_data,
            priority=CachePriority.HIGH
        )
        
        # High cognitive load data should be quickly accessible
        cognitive_start = time.perf_counter()
        
        cognitive_result = await cache_manager.get(
            f"cognitive_state:{user_id}",
            user_id=user_id,
            priority=CachePriority.HIGH
        )
        
        cognitive_time = (time.perf_counter() - cognitive_start) * 1000
        
        assert cognitive_result == complex_data, "Cognitive state not cached correctly"
        assert cognitive_time < 15, f"Cognitive state access: {cognitive_time:.2f}ms, adds to cognitive load"
        
        # Test pattern analysis caching effectiveness
        await cache_warming_engine.analyze_access_patterns(f"attention_data:{user_id}", user_id=user_id)
        await cache_warming_engine.analyze_access_patterns(f"cognitive_state:{user_id}", user_id=user_id)
        
        warming_stats = cache_warming_engine.get_warming_stats()
        
        assert warming_stats['global_patterns'] >= 0, "Pattern analysis not working"
        assert warming_stats['engine_running'], "Warming engine should be running"


@pytest.mark.asyncio
async def test_cache_system_integration():
    """
    Integration test for complete cache system performance.
    
    Tests the interaction between all cache components to ensure
    the system meets ADHD performance targets as a whole.
    """
    user_id = "test_user_integration"
    
    # Initialize all cache systems
    await cache_manager.initialize()
    await cache_warming_engine.initialize()
    await cache_invalidation_engine.initialize()
    
    try:
        integration_start = time.perf_counter()
        
        # Step 1: Warm critical user data
        warming_result = await cache_warming_engine.warm_user_critical_data(user_id)
        
        # Step 2: Perform various cache operations
        operations_start = time.perf_counter()
        
        # Set data across different layers
        await cache_manager.set(f"user_profile:{user_id}", {"name": "Test User"}, priority=CachePriority.HIGH)
        await cache_manager.set(f"user_settings:{user_id}", {"theme": "dark"}, priority=CachePriority.NORMAL)
        await cache_manager.set(f"user_analytics:{user_id}", {"score": 85}, priority=CachePriority.LOW)
        
        # Perform rapid access pattern
        access_results = []
        for _ in range(20):
            result1 = await cache_manager.get(f"user_profile:{user_id}", user_id=user_id, priority=CachePriority.HIGH)
            result2 = await cache_manager.get(f"user_settings:{user_id}", user_id=user_id, priority=CachePriority.NORMAL)
            
            access_results.extend([result1, result2])
        
        operations_time = (time.perf_counter() - operations_start) * 1000
        
        # Step 3: Invalidate and refresh data
        invalidation_start = time.perf_counter()
        
        await cache_invalidation_engine.invalidate_with_dependencies(f"user_profile:{user_id}")
        
        invalidation_time = (time.perf_counter() - invalidation_start) * 1000
        
        # Step 4: Get comprehensive statistics
        stats_start = time.perf_counter()
        
        cache_stats = await cache_manager.get_cache_stats()
        warming_stats = cache_warming_engine.get_warming_stats()
        invalidation_stats = cache_invalidation_engine.get_invalidation_stats()
        
        stats_time = (time.perf_counter() - stats_start) * 1000
        
        # Step 5: Verify overall performance
        total_integration_time = (time.perf_counter() - integration_start) * 1000
        
        # Performance assertions
        assert operations_time < 500, f"Cache operations: {operations_time:.2f}ms, too slow"
        assert invalidation_time < 50, f"Invalidation: {invalidation_time:.2f}ms, too slow"
        assert stats_time < 100, f"Stats collection: {stats_time:.2f}ms, impacts responsiveness"
        assert total_integration_time < 5000, f"Total integration: {total_integration_time:.2f}ms, too slow"
        
        # Functional assertions
        assert all(result is not None for result in access_results[:40]), "Cache misses during rapid access"
        assert len(access_results) == 40, "Incorrect number of access results"
        
        # Statistics should reflect operations
        overall_stats = cache_stats.get('overall', {})
        assert overall_stats.get('total_requests', 0) >= 40, "Request tracking failed"
        
        # ADHD optimization assertions
        crisis_access_times = []
        for layer_stats in cache_stats.values():
            if isinstance(layer_stats, dict) and 'crisis_access_time_ms' in layer_stats:
                if layer_stats['crisis_access_time_ms'] > 0:
                    crisis_access_times.append(layer_stats['crisis_access_time_ms'])
        
        if crisis_access_times:
            avg_crisis_time = sum(crisis_access_times) / len(crisis_access_times)
            assert avg_crisis_time < 50, f"Crisis access time: {avg_crisis_time:.2f}ms, too slow"
        
        print(f"Cache integration test completed successfully:")
        print(f"  - Total time: {total_integration_time:.2f}ms")
        print(f"  - Operations time: {operations_time:.2f}ms") 
        print(f"  - Invalidation time: {invalidation_time:.2f}ms")
        print(f"  - Stats time: {stats_time:.2f}ms")
        print(f"  - Cache operations: {overall_stats.get('total_requests', 0)}")
        print(f"  - Cache hits: {overall_stats.get('total_hits', 0)}")
        print(f"  - Hit rate: {overall_stats.get('overall_hit_rate', 0.0):.3f}")
        
    finally:
        # Shutdown systems
        await cache_manager.shutdown()
        await cache_warming_engine.shutdown()
        await cache_invalidation_engine.shutdown()


if __name__ == "__main__":
    # Run cache performance tests
    asyncio.run(test_cache_system_integration())