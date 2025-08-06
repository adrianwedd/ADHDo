"""
Test utilities and helper functions for MCP ADHD Server tests.
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient


class TestDataFactory:
    """Factory for creating test data objects."""
    
    @staticmethod
    def create_user_data(**overrides) -> Dict[str, Any]:
        """Create user test data."""
        data = {
            "name": "Test User",
            "email": "test@example.com",
            "telegram_chat_id": "123456789",
            "preferences": {
                "nudge_style": "gentle",
                "focus_duration": 25,
                "break_duration": 5,
            }
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_task_data(user_id: str, **overrides) -> Dict[str, Any]:
        """Create task test data."""
        data = {
            "user_id": user_id,
            "title": "Test ADHD Task",
            "description": "This is a test task for ADHD management",
            "priority": 4,
            "energy_required": "medium",
            "estimated_focus_time": 30,
            "tags": ["work", "important"],
            "context": {
                "project": "test_project",
                "category": "development"
            }
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_trace_data(user_id: str, task_id: Optional[str] = None, **overrides) -> Dict[str, Any]:
        """Create trace memory test data."""
        data = {
            "user_id": user_id,
            "trace_type": "user_input",
            "content": {
                "message": "I'm ready to work!",
                "intent": "start_task",
                "context": "morning_routine"
            },
            "task_id": task_id,
            "processing_time_ms": 123.45,
            "cognitive_load": 0.3,
            "was_successful": True,
            "source": "test",
            "metadata": {
                "test_marker": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        data.update(overrides)
        return data


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self):
        self.responses = []
        self.current_response_index = 0
    
    def add_response(self, response: str, processing_time: float = 0.1):
        """Add a mock response."""
        self.responses.append({
            "content": response,
            "processing_time": processing_time
        })
    
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate mock response."""
        if not self.responses:
            self.add_response("Default test response")
        
        response = self.responses[self.current_response_index % len(self.responses)]
        self.current_response_index += 1
        
        # Simulate processing time
        await asyncio.sleep(response["processing_time"])
        
        return {
            "content": response["content"],
            "tokens_used": len(response["content"].split()) * 2,
            "processing_time": response["processing_time"],
            "model": "test-model"
        }


class MetricsAssertions:
    """Helper class for metrics-related assertions."""
    
    @staticmethod
    def assert_metric_exists(metrics_text: str, metric_name: str):
        """Assert that a Prometheus metric exists in the output."""
        assert metric_name in metrics_text, f"Metric '{metric_name}' not found in metrics output"
    
    @staticmethod
    def assert_metric_value(metrics_text: str, metric_name: str, expected_value: float, tolerance: float = 0.01):
        """Assert that a metric has an expected value."""
        lines = metrics_text.split('\n')
        for line in lines:
            if line.startswith(metric_name) and not line.startswith('#'):
                try:
                    value = float(line.split()[-1])
                    assert abs(value - expected_value) <= tolerance, \
                        f"Metric '{metric_name}' value {value} not within {tolerance} of expected {expected_value}"
                    return
                except (ValueError, IndexError):
                    continue
        
        raise AssertionError(f"Metric '{metric_name}' value not found in metrics output")
    
    @staticmethod
    def assert_metric_labels(metrics_text: str, metric_name: str, expected_labels: Dict[str, str]):
        """Assert that a metric has expected labels."""
        lines = metrics_text.split('\n')
        for line in lines:
            if line.startswith(metric_name) and not line.startswith('#'):
                for label_key, label_value in expected_labels.items():
                    expected_label = f'{label_key}="{label_value}"'
                    assert expected_label in line, \
                        f"Label {expected_label} not found in metric line: {line}"
                return
        
        raise AssertionError(f"Metric '{metric_name}' not found in metrics output")


class HealthCheckAssertions:
    """Helper class for health check assertions."""
    
    @staticmethod
    def assert_healthy_response(response_data: Dict[str, Any]):
        """Assert that a health check response indicates healthy status."""
        assert response_data.get("status") == "healthy", \
            f"Expected healthy status, got: {response_data.get('status')}"
        assert "timestamp" in response_data
        assert "uptime_seconds" in response_data
    
    @staticmethod
    def assert_component_health(response_data: Dict[str, Any], component: str, expected_status: str = "healthy"):
        """Assert that a specific component has expected health status."""
        components = response_data.get("components", {})
        assert component in components, f"Component '{component}' not found in health response"
        
        component_data = components[component]
        assert component_data.get("status") == expected_status, \
            f"Component '{component}' status is {component_data.get('status')}, expected {expected_status}"
        assert "response_time_ms" in component_data
        assert "last_check" in component_data


class PerformanceAssertions:
    """Helper class for performance-related assertions."""
    
    @staticmethod
    def assert_response_time(duration_ms: float, max_duration_ms: float, operation: str = "operation"):
        """Assert that an operation completed within the expected time."""
        assert duration_ms <= max_duration_ms, \
            f"{operation} took {duration_ms:.1f}ms, expected <= {max_duration_ms}ms"
    
    @staticmethod
    def assert_adhd_optimization_headers(response):
        """Assert that ADHD optimization headers are present."""
        assert "X-Cognitive-Load" in response.headers, "Missing X-Cognitive-Load header"
        assert "X-Processing-Time" in response.headers, "Missing X-Processing-Time header"
        
        cognitive_load = float(response.headers["X-Cognitive-Load"])
        assert 0.0 <= cognitive_load <= 1.0, f"Cognitive load {cognitive_load} outside valid range [0.0, 1.0]"
    
    @staticmethod
    def assert_cognitive_load_appropriate(cognitive_load: float, user_input: str, max_load: float = 0.7):
        """Assert that cognitive load is appropriate for the user input."""
        assert 0.0 <= cognitive_load <= 1.0, f"Cognitive load {cognitive_load} outside valid range [0.0, 1.0]"
        
        # Check if cognitive load seems reasonable for the input
        if any(keyword in user_input.lower() for keyword in ["overwhelmed", "stuck", "can't", "impossible"]):
            assert cognitive_load >= 0.5, f"Expected high cognitive load for input: {user_input}"
        elif any(keyword in user_input.lower() for keyword in ["ready", "focused", "good"]):
            assert cognitive_load <= 0.4, f"Expected low cognitive load for input: {user_input}"


class DatabaseAssertions:
    """Helper class for database-related assertions."""
    
    @staticmethod
    async def assert_user_exists(db_service, user_id: str):
        """Assert that a user exists in the database."""
        user = await db_service.users.get_by_id(user_id)
        assert user is not None, f"User with ID {user_id} not found"
        return user
    
    @staticmethod
    async def assert_task_exists(db_service, task_id: str):
        """Assert that a task exists in the database."""
        task = await db_service.tasks.get_by_id(task_id)
        assert task is not None, f"Task with ID {task_id} not found"
        return task
    
    @staticmethod
    async def assert_trace_recorded(db_service, user_id: str, trace_type: str):
        """Assert that a trace was recorded for a user."""
        traces = await db_service.get_user_traces(user_id, limit=10)
        matching_traces = [t for t in traces if t.trace_type == trace_type]
        assert matching_traces, f"No traces of type '{trace_type}' found for user {user_id}"
        return matching_traces[0]


class ADHDTestHelpers:
    """Helper functions for ADHD-specific testing."""
    
    @staticmethod
    def get_high_cognitive_load_inputs() -> List[str]:
        """Get list of inputs that should trigger high cognitive load."""
        return [
            "I have 10 tasks and don't know where to start",
            "Everything feels overwhelming right now",
            "I can't focus on anything",
            "I'm stuck and don't know what to do",
            "Too many things to think about",
        ]
    
    @staticmethod
    def get_low_cognitive_load_inputs() -> List[str]:
        """Get list of inputs that should trigger low cognitive load."""
        return [
            "I'm ready to work on my next task",
            "Feeling focused and energized",
            "Let's get this done",
            "I know exactly what I need to do",
            "Feeling good about tackling this",
        ]
    
    @staticmethod
    def get_focus_request_inputs() -> List[str]:
        """Get list of inputs that represent focus requests."""
        return [
            "Help me focus on this task",
            "I need to concentrate better",
            "How can I stay focused?",
            "I keep getting distracted",
            "Help me get in the zone",
        ]
    
    @staticmethod
    def validate_nudge_appropriateness(user_input: str, nudge_response: str, nudge_tier: str):
        """Validate that a nudge response is appropriate for the input and tier."""
        user_input_lower = user_input.lower()
        nudge_lower = nudge_response.lower()
        
        if nudge_tier == "gentle":
            # Gentle nudges should be supportive and non-directive
            assert not any(word in nudge_lower for word in ["must", "should", "need to", "have to"]), \
                f"Gentle nudge contains directive language: {nudge_response}"
            assert any(word in nudge_lower for word in ["you can", "consider", "might", "perhaps"]), \
                f"Gentle nudge lacks supportive language: {nudge_response}"
        
        elif nudge_tier == "structured":
            # Structured nudges should provide clear guidance
            assert any(word in nudge_lower for word in ["step", "first", "next", "try"]), \
                f"Structured nudge lacks clear guidance: {nudge_response}"


async def simulate_user_workflow(client: AsyncClient, user_data: Dict[str, Any], workflow_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Simulate a complete user workflow for testing."""
    results = []
    
    for step in workflow_steps:
        start_time = time.time()
        
        method = step.get("method", "GET")
        endpoint = step["endpoint"]
        data = step.get("data")
        headers = step.get("headers", {})
        
        if method == "GET":
            response = await client.get(endpoint, headers=headers)
        elif method == "POST":
            response = await client.post(endpoint, json=data, headers=headers)
        elif method == "PUT":
            response = await client.put(endpoint, json=data, headers=headers)
        elif method == "DELETE":
            response = await client.delete(endpoint, headers=headers)
        
        duration_ms = (time.time() - start_time) * 1000
        
        result = {
            "step": step.get("name", f"{method} {endpoint}"),
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "response_data": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
            "headers": dict(response.headers)
        }
        
        results.append(result)
    
    return results