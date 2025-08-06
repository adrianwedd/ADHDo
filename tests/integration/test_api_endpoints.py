"""
Integration tests for API endpoints.

Tests complete API workflows, authentication, and ADHD-optimized responses.
"""
import pytest
from fastapi.testclient import TestClient
import httpx
import json
import time
from datetime import datetime

from mcp_server.main import app


class TestHealthEndpoints:
    """Test health monitoring API endpoints."""

    @pytest.mark.integration
    @pytest.mark.health
    def test_health_check_basic(self, test_client):
        """Test basic health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    @pytest.mark.integration
    @pytest.mark.health
    def test_health_check_detailed(self, test_client):
        """Test detailed health check with component status."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        components = data["components"]
        
        # Expected components
        expected_components = ["database", "llm", "redis", "system"]
        for component in expected_components:
            assert component in components
            assert "status" in components[component]
            assert "response_time_ms" in components[component]

    @pytest.mark.integration
    @pytest.mark.health
    @pytest.mark.performance
    def test_health_check_performance(self, test_client, performance_thresholds):
        """Test health check endpoint performance."""
        start_time = time.time()
        response = test_client.get("/health")
        duration_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert duration_ms < performance_thresholds['max_health_check_ms']

    @pytest.mark.integration
    @pytest.mark.health
    def test_readiness_check(self, test_client):
        """Test readiness check endpoint."""
        response = test_client.get("/ready")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "ready" in data
        assert isinstance(data["ready"], bool)

    @pytest.mark.integration
    @pytest.mark.health
    def test_liveness_check(self, test_client):
        """Test liveness check endpoint."""
        response = test_client.get("/live")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "alive" in data
        assert data["alive"] is True


class TestMetricsEndpoints:
    """Test metrics collection API endpoints."""

    @pytest.mark.integration
    @pytest.mark.metrics
    def test_metrics_endpoint_prometheus_format(self, test_client, metrics_assertions):
        """Test Prometheus metrics endpoint format."""
        response = test_client.get("/metrics")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        
        metrics_text = response.text
        metrics_assertions.assert_prometheus_format_valid(metrics_text)

    @pytest.mark.integration
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_metrics_adhd_specific_present(self, test_client, metrics_assertions):
        """Test ADHD-specific metrics are present."""
        response = test_client.get("/metrics")
        
        assert response.status_code == 200
        
        metrics_text = response.text
        metrics_assertions.assert_adhd_metrics_present(metrics_text)

    @pytest.mark.integration
    @pytest.mark.metrics
    @pytest.mark.performance
    def test_metrics_endpoint_performance(self, test_client, performance_thresholds):
        """Test metrics endpoint performance."""
        start_time = time.time()
        response = test_client.get("/metrics")
        duration_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert duration_ms < performance_thresholds['max_health_check_ms']


class TestChatEndpoints:
    """Test chat/conversation API endpoints."""

    @pytest.mark.integration
    @pytest.mark.llm
    async def test_chat_endpoint_basic(self, async_client):
        """Test basic chat endpoint functionality."""
        chat_request = {
            "message": "I'm feeling overwhelmed with my tasks",
            "user_id": "test_user_123",
            "context": {"current_tasks": 5, "energy_level": "low"}
        }
        
        response = await async_client.post("/api/chat", json=chat_request)
        
        assert response.status_code == 200
        
        data = response.json()
        assert "response" in data
        assert "cognitive_load" in data
        assert "processing_time_ms" in data
        assert "suggestions" in data

    @pytest.mark.integration
    @pytest.mark.llm
    @pytest.mark.adhd
    async def test_chat_endpoint_cognitive_load_header(self, async_client):
        """Test cognitive load header in chat response."""
        chat_request = {
            "message": "I have 20 tasks and 5 meetings today, feeling stressed",
            "user_id": "test_user_456"
        }
        
        response = await async_client.post("/api/chat", json=chat_request)
        
        assert response.status_code == 200
        assert "X-Cognitive-Load" in response.headers
        
        cognitive_load = float(response.headers["X-Cognitive-Load"])
        assert 0.0 <= cognitive_load <= 1.0
        assert cognitive_load >= 0.6  # Should be high for overwhelmed message

    @pytest.mark.integration
    @pytest.mark.llm
    @pytest.mark.adhd
    @pytest.mark.performance
    async def test_chat_endpoint_performance(self, async_client, performance_thresholds):
        """Test chat endpoint meets ADHD performance requirements."""
        chat_request = {
            "message": "Quick question: what should I work on next?",
            "user_id": "test_user_789"
        }
        
        start_time = time.time()
        response = await async_client.post("/api/chat", json=chat_request)
        duration_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert duration_ms < performance_thresholds['max_response_time_ms']

    @pytest.mark.integration
    @pytest.mark.llm
    @pytest.mark.adhd
    async def test_chat_endpoint_adhd_scenarios(self, async_client, adhd_helpers):
        """Test chat endpoint with ADHD-specific scenarios."""
        scenarios = adhd_helpers.generate_adhd_scenarios()
        
        for scenario in scenarios:
            chat_request = {
                "message": scenario['input'],
                "user_id": f"test_user_{scenario['name']}"
            }
            
            response = await async_client.post("/api/chat", json=chat_request)
            
            assert response.status_code == 200
            
            data = response.json()
            
            # Validate ADHD response requirements
            assert adhd_helpers.validate_adhd_response(data, scenario)

    @pytest.mark.integration
    @pytest.mark.llm
    async def test_chat_endpoint_validation_errors(self, async_client):
        """Test chat endpoint validation error handling."""
        # Missing required fields
        response = await async_client.post("/api/chat", json={})
        assert response.status_code == 422
        
        # Invalid user_id
        response = await async_client.post("/api/chat", json={
            "message": "test",
            "user_id": ""
        })
        assert response.status_code == 422
        
        # Empty message
        response = await async_client.post("/api/chat", json={
            "message": "",
            "user_id": "test_user"
        })
        assert response.status_code == 422


class TestTaskEndpoints:
    """Test task management API endpoints."""

    @pytest.mark.integration
    @pytest.mark.database
    async def test_create_task_endpoint(self, async_client):
        """Test task creation endpoint."""
        task_data = {
            "title": "Complete integration tests",
            "description": "Write comprehensive API integration tests",
            "priority": 4,
            "energy_required": "high",
            "estimated_focus_time": 120,
            "tags": ["testing", "development"],
            "user_id": "test_user_create"
        }
        
        response = await async_client.post("/api/tasks", json=task_data)
        
        assert response.status_code == 201
        
        data = response.json()
        assert data["title"] == task_data["title"]
        assert data["priority"] == task_data["priority"]
        assert data["dopamine_reward_tier"] == 4  # Should match priority
        assert "task_id" in data

    @pytest.mark.integration
    @pytest.mark.database
    async def test_get_tasks_endpoint(self, async_client):
        """Test task retrieval endpoint."""
        # First create a task
        task_data = {
            "title": "Test task for retrieval",
            "user_id": "test_user_get",
            "priority": 3
        }
        
        create_response = await async_client.post("/api/tasks", json=task_data)
        assert create_response.status_code == 201
        
        # Get tasks
        response = await async_client.get("/api/tasks?user_id=test_user_get")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) >= 1
        
        # Find our created task
        created_task = next((task for task in data["tasks"] if task["title"] == task_data["title"]), None)
        assert created_task is not None

    @pytest.mark.integration
    @pytest.mark.database
    @pytest.mark.adhd
    async def test_suggest_next_task_endpoint(self, async_client):
        """Test task suggestion endpoint."""
        user_id = "test_user_suggest"
        
        # Create multiple tasks with different characteristics
        tasks = [
            {"title": "Low energy task", "user_id": user_id, "energy_required": "low", "priority": 2},
            {"title": "High energy task", "user_id": user_id, "energy_required": "high", "priority": 5},
            {"title": "Medium task", "user_id": user_id, "energy_required": "medium", "priority": 3}
        ]
        
        for task in tasks:
            response = await async_client.post("/api/tasks", json=task)
            assert response.status_code == 201
        
        # Request task suggestion with low energy
        response = await async_client.get(f"/api/tasks/suggest?user_id={user_id}&current_energy=low")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "suggested_task" in data
        
        if data["suggested_task"]:  # May be None if no suitable tasks
            suggested_task = data["suggested_task"]
            # Should suggest low or medium energy task for low energy user
            assert suggested_task["energy_required"] in ["low", "medium"]

    @pytest.mark.integration
    @pytest.mark.database
    @pytest.mark.adhd
    async def test_complete_task_endpoint(self, async_client):
        """Test task completion endpoint."""
        # Create a task
        task_data = {
            "title": "Task to complete",
            "user_id": "test_user_complete",
            "priority": 4
        }
        
        create_response = await async_client.post("/api/tasks", json=task_data)
        assert create_response.status_code == 201
        
        task_id = create_response.json()["task_id"]
        
        # Complete the task
        response = await async_client.post(f"/api/tasks/{task_id}/complete")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "completed"
        assert data["completion_percentage"] == 1.0
        assert "reward" in data
        
        # Check dopamine reward
        reward = data["reward"]
        assert "points" in reward
        assert "celebration_level" in reward
        assert reward["points"] == 40  # 4 (priority) * 10


class TestUserEndpoints:
    """Test user management API endpoints."""

    @pytest.mark.integration
    @pytest.mark.database
    async def test_create_user_endpoint(self, async_client):
        """Test user creation endpoint."""
        user_data = {
            "name": "Test ADHD User",
            "email": "test.adhd@example.com",
            "timezone": "UTC",
            "preferred_nudge_methods": ["web", "telegram"],
            "energy_patterns": {
                "peak_hours": [9, 10, 11, 14, 15],
                "low_hours": [12, 13, 17, 18]
            }
        }
        
        response = await async_client.post("/api/users", json=user_data)
        
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == user_data["name"]
        assert data["email"] == user_data["email"]
        assert "user_id" in data
        assert data["preferred_nudge_methods"] == user_data["preferred_nudge_methods"]

    @pytest.mark.integration
    @pytest.mark.database
    async def test_get_user_endpoint(self, async_client):
        """Test user retrieval endpoint."""
        # Create a user first
        user_data = {
            "name": "User for Retrieval",
            "email": "retrieval@example.com"
        }
        
        create_response = await async_client.post("/api/users", json=user_data)
        assert create_response.status_code == 201
        
        user_id = create_response.json()["user_id"]
        
        # Get the user
        response = await async_client.get(f"/api/users/{user_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == user_data["name"]
        assert data["email"] == user_data["email"]
        assert data["user_id"] == user_id

    @pytest.mark.integration
    @pytest.mark.database
    async def test_update_user_endpoint(self, async_client):
        """Test user update endpoint."""
        # Create a user first
        user_data = {
            "name": "User for Update",
            "email": "update@example.com"
        }
        
        create_response = await async_client.post("/api/users", json=user_data)
        assert create_response.status_code == 201
        
        user_id = create_response.json()["user_id"]
        
        # Update the user
        update_data = {
            "name": "Updated ADHD User",
            "preferred_nudge_methods": ["telegram", "email"],
            "energy_patterns": {
                "peak_hours": [8, 9, 10, 15, 16],
                "low_hours": [11, 12, 13, 17, 18, 19]
            }
        }
        
        response = await async_client.put(f"/api/users/{user_id}", json=update_data)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["preferred_nudge_methods"] == update_data["preferred_nudge_methods"]

    @pytest.mark.integration
    @pytest.mark.database
    async def test_user_not_found(self, async_client):
        """Test user not found error handling."""
        response = await async_client.get("/api/users/nonexistent_user")
        
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data


class TestAuthenticationEndpoints:
    """Test authentication API endpoints."""

    @pytest.mark.integration
    @pytest.mark.auth
    async def test_create_api_key_endpoint(self, async_client):
        """Test API key creation endpoint."""
        # First create a user
        user_data = {
            "name": "User for API Key",
            "email": "apikey@example.com"
        }
        
        user_response = await async_client.post("/api/users", json=user_data)
        assert user_response.status_code == 201
        
        user_id = user_response.json()["user_id"]
        
        # Create API key
        api_key_data = {
            "name": "Integration Test Key",
            "permissions": ["chat", "tasks", "users"]
        }
        
        response = await async_client.post(f"/api/users/{user_id}/api-keys", json=api_key_data)
        
        assert response.status_code == 201
        
        data = response.json()
        assert "key_id" in data
        assert "api_key" in data
        assert data["key_id"].startswith("mk_")
        assert "." in data["api_key"]

    @pytest.mark.integration
    @pytest.mark.auth
    async def test_authenticate_with_api_key(self, async_client):
        """Test authentication using API key."""
        # Create user and API key
        user_data = {"name": "Auth Test User", "email": "auth@example.com"}
        user_response = await async_client.post("/api/users", json=user_data)
        user_id = user_response.json()["user_id"]
        
        api_key_data = {"name": "Auth Test Key", "permissions": ["tasks"]}
        key_response = await async_client.post(f"/api/users/{user_id}/api-keys", json=api_key_data)
        api_key = key_response.json()["api_key"]
        
        # Use API key to create task
        headers = {"Authorization": f"Bearer {api_key}"}
        task_data = {
            "title": "Authenticated Task",
            "user_id": user_id,
            "priority": 3
        }
        
        response = await async_client.post("/api/tasks", json=task_data, headers=headers)
        
        assert response.status_code == 201
        assert response.json()["title"] == "Authenticated Task"

    @pytest.mark.integration
    @pytest.mark.auth
    async def test_invalid_api_key(self, async_client):
        """Test invalid API key handling."""
        headers = {"Authorization": "Bearer invalid_api_key"}
        
        response = await async_client.get("/api/tasks?user_id=test", headers=headers)
        
        assert response.status_code == 401
        
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    @pytest.mark.auth
    async def test_create_session_endpoint(self, async_client):
        """Test session creation endpoint."""
        # Create user
        user_data = {"name": "Session Test User", "email": "session@example.com"}
        user_response = await async_client.post("/api/users", json=user_data)
        user_id = user_response.json()["user_id"]
        
        # Create session
        session_data = {
            "duration_hours": 24,
            "user_agent": "Test Client/1.0"
        }
        
        response = await async_client.post(f"/api/users/{user_id}/sessions", json=session_data)
        
        assert response.status_code == 201
        
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 20


class TestContextEndpoints:
    """Test context management API endpoints."""

    @pytest.mark.integration
    @pytest.mark.database
    @pytest.mark.adhd
    async def test_get_user_context_endpoint(self, async_client):
        """Test user context retrieval endpoint."""
        user_id = "test_user_context"
        
        # Create some context by creating tasks and traces
        task_data = {"title": "Context task", "user_id": user_id, "priority": 3}
        await async_client.post("/api/tasks", json=task_data)
        
        # Get user context
        response = await async_client.get(f"/api/users/{user_id}/context")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "recent_interactions" in data
        assert "active_task_count" in data
        assert "avg_response_time" in data
        assert "cognitive_load_trend" in data

    @pytest.mark.integration
    @pytest.mark.database
    async def test_record_trace_endpoint(self, async_client):
        """Test trace memory recording endpoint."""
        # Create user
        user_data = {"name": "Trace Test User", "email": "trace@example.com"}
        user_response = await async_client.post("/api/users", json=user_data)
        user_id = user_response.json()["user_id"]
        
        # Record trace
        trace_data = {
            "trace_type": "user_input",
            "content": {
                "message": "I need help organizing my tasks",
                "intent": "task_organization"
            },
            "processing_time_ms": 150.5,
            "cognitive_load": 0.6,
            "was_successful": True,
            "source": "web"
        }
        
        response = await async_client.post(f"/api/users/{user_id}/traces", json=trace_data)
        
        assert response.status_code == 201
        
        data = response.json()
        assert data["trace_type"] == trace_data["trace_type"]
        assert data["cognitive_load"] == trace_data["cognitive_load"]
        assert "trace_id" in data


class TestPerformanceAndReliability:
    """Test API performance and reliability requirements."""

    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.adhd
    async def test_api_response_time_compliance(self, async_client, performance_thresholds):
        """Test all API endpoints meet ADHD response time requirements."""
        # Test various endpoints
        endpoints = [
            ("GET", "/health", None),
            ("GET", "/metrics", None),
            ("GET", "/ready", None),
            ("POST", "/api/users", {"name": "Perf Test", "email": "perf@example.com"}),
        ]
        
        for method, endpoint, data in endpoints:
            start_time = time.time()
            
            if method == "GET":
                response = await async_client.get(endpoint)
            elif method == "POST":
                response = await async_client.post(endpoint, json=data)
            
            duration_ms = (time.time() - start_time) * 1000
            
            assert response.status_code in [200, 201]
            assert duration_ms < performance_thresholds['max_response_time_ms']

    @pytest.mark.integration
    @pytest.mark.performance
    async def test_concurrent_requests_performance(self, async_client, performance_thresholds):
        """Test API performance under concurrent load."""
        import asyncio
        
        async def make_health_request():
            start_time = time.time()
            response = await async_client.get("/health")
            duration_ms = (time.time() - start_time) * 1000
            return response.status_code, duration_ms
        
        # Make 10 concurrent health check requests
        tasks = [make_health_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed and meet performance requirements
        for status_code, duration_ms in results:
            assert status_code == 200
            assert duration_ms < performance_thresholds['max_response_time_ms']

    @pytest.mark.integration
    @pytest.mark.adhd
    async def test_cognitive_load_headers_consistency(self, async_client):
        """Test cognitive load headers are consistent across requests."""
        chat_requests = [
            {"message": "I'm ready to work!", "user_id": "test_ready"},
            {"message": "I'm overwhelmed and don't know where to start", "user_id": "test_overwhelmed"},
            {"message": "Quick question about task priority", "user_id": "test_quick"}
        ]
        
        cognitive_loads = []
        
        for chat_request in chat_requests:
            response = await async_client.post("/api/chat", json=chat_request)
            
            assert response.status_code == 200
            assert "X-Cognitive-Load" in response.headers
            
            cognitive_load = float(response.headers["X-Cognitive-Load"])
            cognitive_loads.append(cognitive_load)
            
            # All values should be valid
            assert 0.0 <= cognitive_load <= 1.0
        
        # Ready state should have lower cognitive load than overwhelmed
        assert cognitive_loads[0] < cognitive_loads[1]  # ready < overwhelmed

    @pytest.mark.integration
    @pytest.mark.database
    async def test_database_consistency_across_endpoints(self, async_client):
        """Test database consistency across different endpoints."""
        # Create user
        user_data = {"name": "Consistency Test", "email": "consistency@example.com"}
        user_response = await async_client.post("/api/users", json=user_data)
        user_id = user_response.json()["user_id"]
        
        # Create task
        task_data = {"title": "Consistency Task", "user_id": user_id, "priority": 4}
        task_response = await async_client.post("/api/tasks", json=task_data)
        task_id = task_response.json()["task_id"]
        
        # Get user - should include task count
        user_response = await async_client.get(f"/api/users/{user_id}")
        
        # Get tasks - should include our created task
        tasks_response = await async_client.get(f"/api/tasks?user_id={user_id}")
        
        # Verify consistency
        user_data = user_response.json()
        tasks_data = tasks_response.json()
        
        # Task should exist in tasks list
        created_task = next((task for task in tasks_data["tasks"] if task["task_id"] == task_id), None)
        assert created_task is not None
        assert created_task["title"] == "Consistency Task"

    @pytest.mark.integration
    async def test_error_handling_consistency(self, async_client):
        """Test consistent error handling across endpoints."""
        # Test 404 errors
        not_found_endpoints = [
            "/api/users/nonexistent_user",
            "/api/tasks/nonexistent_task",
        ]
        
        for endpoint in not_found_endpoints:
            response = await async_client.get(endpoint)
            assert response.status_code == 404
            
            data = response.json()
            assert "detail" in data
        
        # Test 422 validation errors
        validation_error_requests = [
            ("/api/users", {}),  # Missing required fields
            ("/api/tasks", {"title": ""}),  # Empty title
        ]
        
        for endpoint, invalid_data in validation_error_requests:
            response = await async_client.post(endpoint, json=invalid_data)
            assert response.status_code == 422
            
            data = response.json()
            assert "detail" in data