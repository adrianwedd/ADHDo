"""
ADHD-specific performance tests.

Tests system performance against ADHD-optimized targets and requirements.
"""
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import statistics
from typing import List, Dict, Any

from mcp_server.main import app


class TestADHDResponseTimes:
    """Test ADHD-specific response time requirements."""

    @pytest.mark.performance
    @pytest.mark.adhd
    async def test_chat_response_time_adhd_target(self, async_client, performance_thresholds):
        """Test chat endpoint meets ADHD response time target (<3s)."""
        adhd_messages = [
            "I'm feeling overwhelmed and need help prioritizing tasks",
            "What should I work on first?",
            "I'm stuck on this project and losing focus",
            "Help me break down this complex task",
            "I need a quick win to build momentum"
        ]
        
        response_times = []
        
        for message in adhd_messages:
            chat_request = {
                "message": message,
                "user_id": "perf_test_user",
                "context": {"urgent": True, "adhd_optimized": True}
            }
            
            start_time = time.time()
            response = await async_client.post("/api/chat", json=chat_request)
            response_time_ms = (time.time() - start_time) * 1000
            
            assert response.status_code == 200
            response_times.append(response_time_ms)
            
            # Each individual response must meet ADHD target
            assert response_time_ms < performance_thresholds['max_response_time_ms']
        
        # Statistical analysis
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        
        # ADHD performance requirements
        assert avg_time < performance_thresholds['max_response_time_ms'] * 0.7  # 70% of max
        assert max_time < performance_thresholds['max_response_time_ms']
        assert p95_time < performance_thresholds['max_response_time_ms'] * 0.9  # 90% of max

    @pytest.mark.performance
    @pytest.mark.adhd
    async def test_cognitive_load_calculation_speed(self, async_client, performance_thresholds):
        """Test cognitive load calculation meets ADHD processing targets."""
        high_cognitive_load_scenarios = [
            "I have 15 urgent tasks, 3 meetings today, 5 overdue items, and I'm behind on 2 projects",
            "Everything is falling apart and I don't know where to start with anything",
            "I'm completely overwhelmed with work, personal stuff, and family commitments",
            "There are too many decisions to make and I'm paralyzed by all the options"
        ]
        
        processing_times = []
        
        for scenario in high_cognitive_load_scenarios:
            request_data = {
                "message": scenario,
                "user_id": "cognitive_load_test",
                "context": {"stress_level": "high", "task_count": 15}
            }
            
            start_time = time.time()
            response = await async_client.post("/api/chat", json=request_data)
            processing_time_ms = (time.time() - start_time) * 1000
            
            assert response.status_code == 200
            assert "X-Cognitive-Load" in response.headers
            
            cognitive_load = float(response.headers["X-Cognitive-Load"])
            assert cognitive_load >= 0.7  # Should detect high cognitive load
            
            processing_times.append(processing_time_ms)
        
        # Cognitive load processing should be very fast
        avg_processing = statistics.mean(processing_times)
        max_processing = max(processing_times)
        
        assert avg_processing < performance_thresholds['max_cognitive_processing_ms']
        assert max_processing < performance_thresholds['max_cognitive_processing_ms'] * 1.5

    @pytest.mark.performance
    @pytest.mark.adhd
    async def test_pattern_matching_speed(self, async_client, performance_thresholds, adhd_helpers):
        """Test ADHD pattern matching speed requirements."""
        scenarios = adhd_helpers.generate_adhd_scenarios()
        pattern_match_times = []
        
        for scenario in scenarios:
            request_data = {
                "message": scenario['input'],
                "user_id": "pattern_test_user",
                "context": {"pattern_detection": True}
            }
            
            start_time = time.time()
            response = await async_client.post("/api/chat", json=request_data)
            match_time_ms = (time.time() - start_time) * 1000
            
            assert response.status_code == 200
            pattern_match_times.append(match_time_ms)
            
            # Validate pattern was detected correctly
            response_data = response.json()
            assert adhd_helpers.validate_adhd_response(response_data, scenario)
        
        # Pattern matching should be ultra-fast for ADHD responsiveness
        avg_match_time = statistics.mean(pattern_match_times)
        max_match_time = max(pattern_match_times)
        
        assert avg_match_time < performance_thresholds['max_pattern_match_ms']
        assert max_match_time < performance_thresholds['max_pattern_match_ms'] * 2

    @pytest.mark.performance
    @pytest.mark.adhd
    async def test_task_suggestion_speed(self, async_client, performance_thresholds):
        """Test task suggestion speed for ADHD users."""
        # Create test user and tasks first
        user_data = {"name": "Task Speed Test User", "email": "taskspeed@test.com"}
        user_response = await async_client.post("/api/users", json=user_data)
        user_id = user_response.json()["user_id"]
        
        # Create various tasks for suggestion testing
        task_types = [
            {"priority": 1, "energy_required": "low", "estimated_focus_time": 15},
            {"priority": 3, "energy_required": "medium", "estimated_focus_time": 30},
            {"priority": 5, "energy_required": "high", "estimated_focus_time": 90},
            {"priority": 2, "energy_required": "low", "estimated_focus_time": 20},
            {"priority": 4, "energy_required": "high", "estimated_focus_time": 60}
        ]
        
        for i, task_params in enumerate(task_types):
            task_data = {
                "title": f"Performance Test Task {i}",
                "user_id": user_id,
                **task_params
            }
            await async_client.post("/api/tasks", json=task_data)
        
        # Test suggestion speed for different energy levels
        energy_levels = ["low", "medium", "high"]
        suggestion_times = []
        
        for energy in energy_levels:
            start_time = time.time()
            response = await async_client.get(f"/api/tasks/suggest?user_id={user_id}&current_energy={energy}")
            suggestion_time_ms = (time.time() - start_time) * 1000
            
            assert response.status_code == 200
            suggestion_times.append(suggestion_time_ms)
            
            # Should get appropriate suggestion
            data = response.json()
            if data["suggested_task"]:
                suggested_task = data["suggested_task"]
                if energy == "low":
                    assert suggested_task["energy_required"] in ["low", "medium"]
                elif energy == "high":
                    assert suggested_task["energy_required"] in ["medium", "high"]
        
        # Task suggestions must be very fast for ADHD decision making
        avg_suggestion_time = statistics.mean(suggestion_times)
        max_suggestion_time = max(suggestion_times)
        
        assert avg_suggestion_time < 800  # <800ms for quick decisions
        assert max_suggestion_time < 1200  # <1.2s maximum


class TestADHDConcurrentPerformance:
    """Test ADHD performance under concurrent load."""

    @pytest.mark.performance
    @pytest.mark.adhd
    @pytest.mark.slow
    async def test_concurrent_adhd_users_performance(self, async_client, performance_thresholds):
        """Test performance with multiple ADHD users simultaneously."""
        
        async def simulate_adhd_user_session(user_index: int):
            """Simulate a typical ADHD user session."""
            # Create user
            user_data = {
                "name": f"Concurrent ADHD User {user_index}",
                "email": f"concurrent{user_index}@adhd.test"
            }
            user_response = await async_client.post("/api/users", json=user_data)
            if user_response.status_code != 201:
                return {"user_index": user_index, "success": False}
            
            user_id = user_response.json()["user_id"]
            
            # Typical ADHD user workflow
            session_times = []
            
            # 1. Overwhelmed check-in
            start = time.time()
            chat_response = await async_client.post("/api/chat", json={
                "message": "I'm feeling overwhelmed with my tasks today",
                "user_id": user_id,
                "context": {"stress_level": "high", "needs_support": True}
            })
            session_times.append((time.time() - start) * 1000)
            
            # 2. Create urgent task
            start = time.time()
            task_response = await async_client.post("/api/tasks", json={
                "title": f"Urgent task for user {user_index}",
                "user_id": user_id,
                "priority": 5,
                "energy_required": "high"
            })
            session_times.append((time.time() - start) * 1000)
            
            # 3. Get task suggestions
            start = time.time()
            suggestion_response = await async_client.get(
                f"/api/tasks/suggest?user_id={user_id}&current_energy=medium"
            )
            session_times.append((time.time() - start) * 1000)
            
            # 4. Health check
            start = time.time()
            health_response = await async_client.get("/health")
            session_times.append((time.time() - start) * 1000)
            
            # Analyze session performance
            all_successful = all(
                resp.status_code in [200, 201] 
                for resp in [chat_response, task_response, suggestion_response, health_response]
            )
            
            return {
                "user_index": user_index,
                "success": all_successful,
                "session_times": session_times,
                "total_time": sum(session_times),
                "max_time": max(session_times) if session_times else 0
            }
        
        # Run 8 concurrent ADHD user sessions
        concurrent_users = 8
        tasks = [simulate_adhd_user_session(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        successful_results = [r for r in results if not isinstance(r, Exception) and r["success"]]
        
        # Performance analysis
        assert len(successful_results) >= concurrent_users * 0.8  # 80% success rate minimum
        
        all_session_times = []
        for result in successful_results:
            all_session_times.extend(result["session_times"])
        
        if all_session_times:
            avg_response_time = statistics.mean(all_session_times)
            p95_response_time = statistics.quantiles(all_session_times, n=20)[18]
            
            # Under concurrent load, still meet ADHD requirements
            assert avg_response_time < performance_thresholds['max_response_time_ms'] * 1.5
            assert p95_response_time < performance_thresholds['max_response_time_ms'] * 2


class TestADHDMemoryAndResourceUsage:
    """Test memory usage and resource consumption for ADHD optimization."""

    @pytest.mark.performance
    @pytest.mark.adhd
    async def test_memory_usage_adhd_sessions(self, async_client, performance_thresholds):
        """Test memory usage during typical ADHD user sessions."""
        import psutil
        import os
        
        # Get baseline memory usage
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate extended ADHD user session
        user_data = {"name": "Memory Test User", "email": "memory@test.com"}
        user_response = await async_client.post("/api/users", json=user_data)
        user_id = user_response.json()["user_id"]
        
        # Create many interactions to test memory usage
        for i in range(20):
            # Chat interactions
            await async_client.post("/api/chat", json={
                "message": f"Session message {i} - working on task prioritization",
                "user_id": user_id,
                "context": {"session_number": i, "cognitive_load": 0.5 + (i * 0.02)}
            })
            
            # Task operations
            task_response = await async_client.post("/api/tasks", json={
                "title": f"Memory test task {i}",
                "user_id": user_id,
                "priority": (i % 5) + 1
            })
            
            if task_response.status_code == 201:
                task_id = task_response.json()["task_id"]
                
                # Complete some tasks
                if i % 3 == 0:
                    await async_client.post(f"/api/tasks/{task_id}/complete")
            
            # Health checks
            await async_client.get("/health")
        
        # Check memory usage after session
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - baseline_memory
        
        # Memory usage should remain reasonable for ADHD system
        assert memory_increase < performance_thresholds.get('max_memory_usage_mb', 256)


class TestADHDStressTest:
    """Stress testing for ADHD-critical scenarios."""

    @pytest.mark.performance
    @pytest.mark.adhd
    @pytest.mark.slow
    async def test_overwhelm_scenario_stress_test(self, async_client, performance_thresholds):
        """Test system performance during user overwhelm scenarios."""
        
        # Create overwhelmed user scenario
        user_data = {"name": "Overwhelmed Stress User", "email": "stress@overwhelm.test"}
        user_response = await async_client.post("/api/users", json=user_data)
        user_id = user_response.json()["user_id"]
        
        # Create overwhelming task load
        overwhelming_tasks = []
        for i in range(20):  # 20 urgent tasks
            task_data = {
                "title": f"Urgent stress task {i}",
                "user_id": user_id,
                "priority": 5,  # All high priority
                "energy_required": "high"
            }
            response = await async_client.post("/api/tasks", json=task_data)
            if response.status_code == 201:
                overwhelming_tasks.append(response.json()["task_id"])
        
        # Simulate overwhelm crisis - rapid requests
        crisis_requests = []
        start_time = time.time()
        
        # Multiple overwhelm messages in quick succession
        for i in range(5):
            crisis_message = {
                "message": f"I'm completely overwhelmed! Crisis message {i}. "
                          "I have too many urgent tasks and don't know where to start!",
                "user_id": user_id,
                "context": {
                    "stress_level": "critical",
                    "overwhelm_count": i + 1,
                    "crisis_mode": True
                }
            }
            
            start = time.time()
            response = await async_client.post("/api/chat", json=crisis_message)
            response_time = (time.time() - start) * 1000
            
            crisis_requests.append({
                "response_time_ms": response_time,
                "status_code": response.status_code,
                "cognitive_load": float(response.headers.get("X-Cognitive-Load", 0))
            })
            
            # Verify crisis is detected
            assert response.status_code == 200
            assert response.headers.get("X-Cognitive-Load")
            cognitive_load = float(response.headers["X-Cognitive-Load"])
            assert cognitive_load >= 0.8, "System should detect high cognitive load in crisis"
        
        total_crisis_time = (time.time() - start_time) * 1000
        
        # Crisis response performance analysis
        avg_crisis_response = statistics.mean([req["response_time_ms"] for req in crisis_requests])
        max_crisis_response = max([req["response_time_ms"] for req in crisis_requests])
        
        # Crisis responses must be even faster than normal for ADHD support
        assert avg_crisis_response < 2000, "Crisis responses must be <2s for ADHD support"
        assert max_crisis_response < 3000, "No crisis response should exceed 3s"
        assert total_crisis_time < 8000, "Total crisis handling must be <8s"
        
        # All crisis requests should succeed
        success_rate = len([req for req in crisis_requests if req["status_code"] == 200]) / len(crisis_requests)
        assert success_rate == 1.0, "All crisis requests must succeed"


class TestADHDLoadBalancing:
    """Test load balancing and resource allocation for ADHD users."""

    @pytest.mark.performance
    @pytest.mark.adhd
    async def test_priority_based_request_handling(self, async_client):
        """Test that ADHD crisis requests get priority handling."""
        
        # Mix of normal and crisis requests
        request_types = [
            # Normal requests
            *[("normal", {"message": "Regular check-in", "user_id": f"normal_{i}"}) for i in range(5)],
            
            # Crisis requests (should get priority)
            ("crisis", {
                "message": "URGENT: I'm having a panic attack and completely overwhelmed!",
                "user_id": "crisis_user",
                "context": {"crisis": True, "urgency": "critical"}
            }),
            ("crisis", {
                "message": "Emergency help needed - everything is falling apart",
                "user_id": "crisis_user2", 
                "context": {"crisis": True, "urgency": "high"}
            })
        ]
        
        # Execute all requests concurrently
        tasks = []
        start_times = {}
        
        for i, (req_type, data) in enumerate(request_types):
            start_times[i] = time.time()
            task = async_client.post("/api/chat", json=data)
            tasks.append((i, req_type, task))
        
        # Wait for all responses
        results = []
        for i, req_type, task in tasks:
            response = await task
            response_time = (time.time() - start_times[i]) * 1000
            results.append({
                "index": i,
                "type": req_type,
                "response_time_ms": response_time,
                "status_code": response.status_code,
                "cognitive_load": float(response.headers.get("X-Cognitive-Load", 0))
            })
        
        # Analyze priority handling
        crisis_times = [r["response_time_ms"] for r in results if r["type"] == "crisis"]
        normal_times = [r["response_time_ms"] for r in results if r["type"] == "normal"]
        
        # Crisis requests should be faster on average (priority handling)
        if crisis_times and normal_times:
            avg_crisis_time = statistics.mean(crisis_times)
            avg_normal_time = statistics.mean(normal_times)
            
            # Crisis requests should get priority (be faster or similar)
            assert avg_crisis_time <= avg_normal_time * 1.2  # Allow 20% variance
        
        # All crisis requests must meet strict timing
        for crisis_time in crisis_times:
            assert crisis_time < 2500, "Crisis requests must be handled in <2.5s"