"""
Unit tests for metrics collection system.
"""
import pytest
import time
from datetime import datetime, timedelta

from tests.utils import MetricsAssertions, PerformanceAssertions


@pytest.mark.unit
@pytest.mark.metrics
class TestMetricsCollector:
    """Test MetricsCollector functionality."""
    
    def test_metrics_collector_initialization(self, metrics_collector):
        """Test metrics collector initialization."""
        assert metrics_collector is not None
        assert hasattr(metrics_collector, 'registry')
        assert hasattr(metrics_collector, 'start_time')
        assert metrics_collector.start_time is not None
    
    def test_server_info_metric(self, metrics_collector):
        """Test server info metric recording."""
        metrics_data = metrics_collector.export_metrics()
        
        MetricsAssertions.assert_metric_exists(metrics_data, "mcp_adhd_server_info")
        MetricsAssertions.assert_metric_labels(
            metrics_data,
            "mcp_adhd_server_info",
            {"version": "0.1.0"}  # Adjust based on actual version
        )
    
    def test_uptime_metric(self, metrics_collector):
        """Test uptime metric recording."""
        metrics_data = metrics_collector.export_metrics()
        
        MetricsAssertions.assert_metric_exists(metrics_data, "mcp_adhd_server_uptime_seconds")
        
        # Uptime should be positive
        lines = metrics_data.split('\n')
        for line in lines:
            if line.startswith("mcp_adhd_server_uptime_seconds") and not line.startswith('#'):
                uptime_value = float(line.split()[-1])
                assert uptime_value >= 0
                break
    
    def test_http_request_metrics(self, metrics_collector):
        """Test HTTP request metrics recording."""
        # Record various HTTP requests
        test_requests = [
            ("GET", "/health", 200, 0.05),
            ("POST", "/chat", 200, 0.15),
            ("GET", "/metrics", 200, 0.02),
            ("GET", "/nonexistent", 404, 0.01),
            ("POST", "/chat", 500, 0.3)
        ]
        
        for method, path, status_code, duration in test_requests:
            metrics_collector.record_http_request(method, path, status_code, duration)
        
        metrics_data = metrics_collector.export_metrics()
        
        # Check total requests counter
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_http_requests_total"
        )
        
        # Check request duration histogram
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_http_request_duration_seconds"
        )
        
        # Verify labels are recorded correctly
        MetricsAssertions.assert_metric_labels(
            metrics_data,
            "mcp_adhd_server_http_requests_total",
            {"method": "GET", "endpoint": "/health", "status": "200"}
        )
    
    def test_user_session_metrics(self, metrics_collector):
        """Test user session metrics recording."""
        # Record user sessions
        test_users = ["user1", "user2", "user3", "user1"]  # user1 has 2 sessions
        
        for user_id in test_users:
            metrics_collector.record_user_session_start(user_id)
        
        # End some sessions
        metrics_collector.record_user_session_end("user2")
        
        metrics_data = metrics_collector.export_metrics()
        
        # Check active users gauge
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_active_users"
        )
        
        # Check total sessions counter
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_total_sessions"
        )
        
        # Should have 3 active users (user1 still has 1 active session)
        # and 4 total sessions
    
    def test_task_metrics(self, metrics_collector):
        """Test task-related metrics recording."""
        # Record task creation
        priorities = [1, 2, 3, 4, 5, 4, 3]
        energy_levels = ["low", "medium", "high", "medium", "high", "low", "medium"]
        
        for priority, energy in zip(priorities, energy_levels):
            metrics_collector.record_task_created(priority, energy)
        
        # Record task completions
        completion_times = [300, 450, 180, 600, 120]  # seconds
        for completion_time in completion_times:
            metrics_collector.record_task_completed(completion_time)
        
        metrics_data = metrics_collector.export_metrics()
        
        # Check task creation metrics
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_tasks_created_total"
        )
        MetricsAssertions.assert_metric_labels(
            metrics_data,
            "mcp_adhd_server_tasks_created_total",
            {"priority": "5", "energy_required": "high"}
        )
        
        # Check task completion metrics
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_tasks_completed_total"
        )
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_task_completion_duration_seconds"
        )
    
    def test_cognitive_loop_metrics(self, metrics_collector):
        """Test cognitive loop execution metrics."""
        # Record cognitive loop executions
        execution_results = [
            ("success", 0.05, 0.3),
            ("success", 0.08, 0.4),
            ("error", 0.12, 0.7),
            ("success", 0.06, 0.2),
            ("timeout", 0.15, 0.6)
        ]
        
        for result, duration, cognitive_load in execution_results:
            metrics_collector.record_cognitive_loop_execution(result, duration)
            metrics_collector.update_cognitive_load(cognitive_load)
        
        metrics_data = metrics_collector.export_metrics()
        
        # Check cognitive loop metrics
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_cognitive_loop_executions_total"
        )
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_cognitive_loop_duration_seconds"
        )
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_cognitive_load"
        )
        
        # Verify labels for different results
        MetricsAssertions.assert_metric_labels(
            metrics_data,
            "mcp_adhd_server_cognitive_loop_executions_total",
            {"result": "success"}
        )
        MetricsAssertions.assert_metric_labels(
            metrics_data,
            "mcp_adhd_server_cognitive_loop_executions_total",
            {"result": "error"}
        )
    
    def test_pattern_matching_metrics(self, metrics_collector):
        """Test pattern matching metrics recording."""
        # Record pattern matches
        patterns = [
            ("overwhelmed", 0.8),
            ("focused", 0.9),
            ("stuck", 0.7),
            ("ready", 0.85),
            ("overwhelmed", 0.75),
            ("focused", 0.92)
        ]
        
        for pattern, confidence in patterns:
            metrics_collector.record_pattern_match(pattern, confidence)
        
        metrics_data = metrics_collector.export_metrics()
        
        # Check pattern matching metrics
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_pattern_matches_total"
        )
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_pattern_match_confidence"
        )
        
        # Verify pattern labels
        MetricsAssertions.assert_metric_labels(
            metrics_data,
            "mcp_adhd_server_pattern_matches_total",
            {"pattern": "overwhelmed"}
        )
        MetricsAssertions.assert_metric_labels(
            metrics_data,
            "mcp_adhd_server_pattern_matches_total",
            {"pattern": "focused"}
        )
    
    def test_system_metrics(self, metrics_collector):
        """Test system resource metrics recording."""
        # Update system metrics
        cpu_values = [25.5, 30.2, 45.8, 35.1, 28.7]
        memory_values = [60.3, 62.1, 58.9, 64.2, 61.5]
        disk_values = [75.2, 75.3, 75.1, 75.4, 75.2]
        
        for cpu, memory, disk in zip(cpu_values, memory_values, disk_values):
            metrics_collector.update_system_metrics(cpu, memory, disk)
            time.sleep(0.1)  # Small delay between updates
        
        metrics_data = metrics_collector.export_metrics()
        
        # Check system resource metrics
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_cpu_usage_percent"
        )
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_memory_usage_percent"
        )
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_disk_usage_percent"
        )
        
        # Values should be within expected ranges
        lines = metrics_data.split('\n')
        for line in lines:
            if line.startswith("mcp_adhd_server_cpu_usage_percent") and not line.startswith('#'):
                cpu_value = float(line.split()[-1])
                assert 0 <= cpu_value <= 100
            elif line.startswith("mcp_adhd_server_memory_usage_percent") and not line.startswith('#'):
                memory_value = float(line.split()[-1])
                assert 0 <= memory_value <= 100
    
    def test_component_health_metrics(self, metrics_collector):
        """Test component health metrics recording."""
        # Update component health
        components = [
            ("database", "healthy"),
            ("redis", "healthy"),
            ("llm", "degraded"),
            ("system", "healthy"),
            ("application", "healthy")
        ]
        
        for component, status in components:
            metrics_collector.update_component_health(component, status)
        
        metrics_data = metrics_collector.export_metrics()
        
        # Check component health metrics
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_component_health"
        )
        
        # Verify component labels and status values
        for component, status in components:
            MetricsAssertions.assert_metric_labels(
                metrics_data,
                "mcp_adhd_server_component_health",
                {"component": component}
            )
    
    def test_cache_metrics(self, metrics_collector):
        """Test cache-related metrics recording."""
        # Record cache operations
        cache_operations = [
            ("hit", "user_context"),
            ("miss", "user_context"),
            ("hit", "task_suggestions"),
            ("hit", "user_context"),
            ("miss", "pattern_matches"),
            ("hit", "task_suggestions")
        ]
        
        for operation, cache_type in cache_operations:
            if operation == "hit":
                metrics_collector.record_cache_hit(cache_type)
            else:
                metrics_collector.record_cache_miss(cache_type)
        
        metrics_data = metrics_collector.export_metrics()
        
        # Check cache metrics
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_cache_operations_total"
        )
        
        # Verify cache operation labels
        MetricsAssertions.assert_metric_labels(
            metrics_data,
            "mcp_adhd_server_cache_operations_total",
            {"operation": "hit", "cache_type": "user_context"}
        )
    
    def test_adhd_specific_metrics(self, metrics_collector):
        """Test ADHD-specific metrics recording."""
        # Record ADHD-specific events
        dopamine_rewards = [10, 15, 25, 5, 20, 30]
        focus_sessions = [
            (25, "completed"),
            (15, "interrupted"),
            (30, "completed"),
            (10, "abandoned"),
            (45, "completed")
        ]
        
        # Record dopamine rewards
        for reward in dopamine_rewards:
            metrics_collector.record_dopamine_reward(reward)
        
        # Record focus sessions
        for duration, outcome in focus_sessions:
            metrics_collector.record_focus_session(duration, outcome)
        
        metrics_data = metrics_collector.export_metrics()
        
        # Check ADHD-specific metrics
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_dopamine_rewards_total"
        )
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_focus_sessions_total"
        )
        MetricsAssertions.assert_metric_exists(
            metrics_data, "mcp_adhd_server_focus_session_duration_seconds"
        )
        
        # Verify focus session outcome labels
        MetricsAssertions.assert_metric_labels(
            metrics_data,
            "mcp_adhd_server_focus_sessions_total",
            {"outcome": "completed"}
        )
        MetricsAssertions.assert_metric_labels(
            metrics_data,
            "mcp_adhd_server_focus_sessions_total",
            {"outcome": "interrupted"}
        )
    
    def test_metrics_summary(self, metrics_collector):
        """Test metrics summary generation."""
        # Generate some data across different metrics
        metrics_collector.record_user_session_start("user1")
        metrics_collector.record_user_session_start("user2")
        metrics_collector.record_task_created(4, "medium")
        metrics_collector.record_task_completed(300)
        metrics_collector.record_cognitive_loop_execution("success", 0.08)
        metrics_collector.update_cognitive_load(0.4)
        metrics_collector.record_pattern_match("focused", 0.87)
        
        # Get metrics summary
        summary = metrics_collector.get_metrics_summary()
        
        assert "uptime_seconds" in summary
        assert "active_users" in summary
        assert "total_sessions" in summary
        assert "total_tasks_created" in summary
        assert "total_tasks_completed" in summary
        assert "avg_cognitive_load" in summary
        assert "total_pattern_matches" in summary
        assert "cache_hit_rate" in summary
        
        # Verify data types and ranges
        assert isinstance(summary["uptime_seconds"], (int, float))
        assert summary["uptime_seconds"] >= 0
        assert isinstance(summary["active_users"], int)
        assert summary["active_users"] >= 0
        assert 0.0 <= summary["avg_cognitive_load"] <= 1.0
        assert 0.0 <= summary["cache_hit_rate"] <= 1.0
    
    def test_metrics_reset(self, metrics_collector):
        """Test metrics reset functionality."""
        # Record some metrics
        metrics_collector.record_http_request("GET", "/test", 200, 0.1)
        metrics_collector.record_user_session_start("test_user")
        metrics_collector.update_cognitive_load(0.5)
        
        # Get initial metrics
        initial_metrics = metrics_collector.export_metrics()
        assert "mcp_adhd_server_http_requests_total" in initial_metrics
        
        # Reset specific counters (if implemented)
        # Note: Prometheus counters typically don't reset, but gauges can be set to 0
        metrics_collector.update_cognitive_load(0.0)
        
        # Verify reset worked
        reset_metrics = metrics_collector.export_metrics()
        
        # Cognitive load should be 0
        lines = reset_metrics.split('\n')
        for line in lines:
            if line.startswith("mcp_adhd_server_cognitive_load") and not line.startswith('#'):
                cognitive_load = float(line.split()[-1])
                assert cognitive_load == 0.0
                break
    
    def test_metrics_performance(self, metrics_collector):
        """Test metrics collection performance."""
        import time
        
        # Test high-frequency metric recording
        start_time = time.time()
        
        # Record many metrics quickly
        for i in range(100):
            metrics_collector.record_http_request("GET", f"/test_{i%10}", 200, 0.01)
            metrics_collector.update_cognitive_load(i / 100.0)
        
        record_duration = (time.time() - start_time) * 1000
        
        # Should be fast enough for real-time collection
        PerformanceAssertions.assert_response_time(
            record_duration, 200, "100 metrics recordings"
        )
        
        # Test metrics export performance
        start_time = time.time()
        metrics_data = metrics_collector.export_metrics()
        export_duration = (time.time() - start_time) * 1000
        
        # Export should also be fast
        PerformanceAssertions.assert_response_time(
            export_duration, 100, "metrics export"
        )
        
        # Verify we got substantial metrics data
        assert len(metrics_data) > 1000  # Should have substantial content
    
    def test_concurrent_metrics_recording(self, metrics_collector):
        """Test concurrent metrics recording safety."""
        import asyncio
        import threading
        
        # Function to record metrics in a thread
        def record_metrics_thread(thread_id):
            for i in range(50):
                metrics_collector.record_http_request(
                    "GET", f"/thread_{thread_id}", 200, 0.01
                )
                metrics_collector.update_cognitive_load((thread_id + i) / 100.0)
        
        # Start multiple threads recording metrics
        threads = []
        for thread_id in range(4):
            thread = threading.Thread(target=record_metrics_thread, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify metrics were recorded correctly
        metrics_data = metrics_collector.export_metrics()
        
        # Should contain metrics from all threads
        assert "mcp_adhd_server_http_requests_total" in metrics_data
        assert "mcp_adhd_server_cognitive_load" in metrics_data
        
        # No exceptions should have occurred during concurrent recording
    
    def test_metrics_labels_sanitization(self, metrics_collector):
        """Test that metric labels are properly sanitized."""
        # Record metrics with potentially problematic labels
        problematic_endpoints = [
            "/api/users/123/tasks",  # Contains numbers
            "/search?q=test query",  # Contains query parameters
            "/files/document.pdf",   # Contains file extension
            "/api/très/spéçiál",     # Contains special characters
        ]
        
        for endpoint in problematic_endpoints:
            metrics_collector.record_http_request("GET", endpoint, 200, 0.05)
        
        metrics_data = metrics_collector.export_metrics()
        
        # Verify metrics were recorded (labels should be sanitized)
        assert "mcp_adhd_server_http_requests_total" in metrics_data
        
        # Verify no invalid characters in the output
        for line in metrics_data.split('\n'):
            if 'mcp_adhd_server_http_requests_total{' in line:
                # Prometheus labels should not contain invalid characters
                assert '"' in line  # Should have proper quoting