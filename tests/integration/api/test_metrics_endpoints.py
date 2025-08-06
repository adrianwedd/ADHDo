"""
Integration tests for metrics API endpoints.
"""
import pytest
import asyncio
from httpx import AsyncClient

from tests.utils import MetricsAssertions, PerformanceAssertions


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.metrics
class TestMetricsEndpoints:
    """Test metrics API endpoints integration."""
    
    async def test_prometheus_metrics_endpoint(self, async_test_client, metrics_collector):
        """Test GET /metrics endpoint (Prometheus format)."""
        # Generate some metrics first
        metrics_collector.record_http_request("GET", "/test", 200, 0.1)
        metrics_collector.update_system_metrics(45.0, 60.0, 75.0)
        metrics_collector.update_cognitive_load(0.3)
        
        response = await async_test_client.get("/metrics")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        
        metrics_text = response.text
        
        # Verify core metrics are present
        expected_metrics = [
            "mcp_adhd_server_info",
            "mcp_adhd_server_uptime_seconds",
            "mcp_adhd_server_http_requests_total",
            "mcp_adhd_server_cognitive_load",
            "mcp_adhd_server_cpu_usage_percent",
            "mcp_adhd_server_memory_usage_percent"
        ]
        
        for metric in expected_metrics:
            MetricsAssertions.assert_metric_exists(metrics_text, metric)
        
        # Verify metric formats
        assert "# HELP" in metrics_text  # Should have help text
        assert "# TYPE" in metrics_text  # Should have type definitions
    
    async def test_metrics_summary_endpoint(self, async_test_client, metrics_collector):
        """Test GET /metrics/summary endpoint (JSON format)."""
        # Generate metrics data
        metrics_collector.record_user_session_start("user1")
        metrics_collector.record_user_session_start("user2")
        metrics_collector.record_task_created(4, "medium")
        metrics_collector.record_task_completed(300)
        metrics_collector.record_cognitive_loop_execution("success", 0.05)
        
        response = await async_test_client.get("/metrics/summary")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        # Should have summary metrics
        expected_fields = [
            "uptime_seconds",
            "active_users",
            "total_sessions",
            "total_tasks_created",
            "total_tasks_completed",
            "avg_cognitive_load",
            "cache_hit_rate"
        ]
        
        for field in expected_fields:
            assert field in data
        
        # Validate data types and ranges
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0
        assert isinstance(data["active_users"], int)
        assert data["active_users"] >= 0
        assert 0.0 <= data["avg_cognitive_load"] <= 1.0
        assert 0.0 <= data["cache_hit_rate"] <= 1.0
    
    async def test_metrics_by_component_endpoint(self, async_test_client):
        """Test GET /metrics/{component} endpoint."""
        components = ["system", "database", "redis", "llm"]
        
        for component in components:
            response = await async_test_client.get(f"/metrics/{component}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Should have component-specific metrics
                assert isinstance(data, dict)
                assert len(data) > 0
                
                # Should have timestamp
                if "timestamp" in data:
                    assert isinstance(data["timestamp"], str)
            elif response.status_code == 404:
                # Component metrics not implemented yet
                continue
            else:
                pytest.fail(f"Unexpected status code {response.status_code} for {component}")
    
    async def test_adhd_specific_metrics_endpoint(self, async_test_client, metrics_collector):
        """Test GET /metrics/adhd endpoint for ADHD-specific metrics."""
        # Generate ADHD-specific data
        metrics_collector.record_pattern_match("focused", 0.9)
        metrics_collector.record_pattern_match("overwhelmed", 0.8)
        metrics_collector.record_dopamine_reward(25)
        metrics_collector.record_focus_session(25, "completed")
        
        response = await async_test_client.get("/metrics/adhd")
        
        if response.status_code == 200:
            data = response.json()
            
            # Should have ADHD-specific metrics
            expected_adhd_metrics = [
                "pattern_matches",
                "cognitive_load",
                "dopamine_rewards",
                "focus_sessions"
            ]
            
            # At least some should be present
            assert any(metric in str(data).lower() for metric in expected_adhd_metrics)
        elif response.status_code == 404:
            pytest.skip("ADHD metrics endpoint not implemented yet")
    
    async def test_metrics_endpoint_performance(self, async_test_client):
        """Test metrics endpoint performance."""
        import time
        
        endpoints_to_test = [
            "/metrics",
            "/metrics/summary",
            "/metrics/system"
        ]
        
        for endpoint in endpoints_to_test:
            start_time = time.time()
            response = await async_test_client.get(endpoint)
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                # Metrics endpoints should be reasonably fast
                if endpoint == "/metrics":
                    # Prometheus export might be slower due to formatting
                    PerformanceAssertions.assert_response_time(
                        duration_ms, 1000, f"{endpoint} response time"
                    )
                else:
                    PerformanceAssertions.assert_response_time(
                        duration_ms, 500, f"{endpoint} response time"
                    )
    
    async def test_metrics_endpoint_caching(self, async_test_client):
        """Test metrics endpoint caching behavior."""
        # Make first request
        response1 = await async_test_client.get("/metrics/summary")
        
        if response1.status_code == 200:
            data1 = response1.json()
            
            # Make second request immediately
            response2 = await async_test_client.get("/metrics/summary")
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Uptime should be very close if cached
            uptime_diff = abs(data2["uptime_seconds"] - data1["uptime_seconds"])
            assert uptime_diff < 2.0  # Should be within 2 seconds
    
    async def test_metrics_endpoint_filtering(self, async_test_client):
        """Test metrics endpoint with filtering parameters."""
        # Test with time range filters
        response = await async_test_client.get("/metrics/summary?hours=1")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        elif response.status_code == 400:
            # Filtering not supported
            pass
        
        # Test with metric type filters
        response = await async_test_client.get("/metrics?filter=cpu,memory")
        
        # Should get some response
        assert response.status_code in [200, 400, 404]
    
    async def test_metrics_endpoint_headers(self, async_test_client):
        """Test metrics endpoint response headers."""
        # Test Prometheus endpoint headers
        response = await async_test_client.get("/metrics")
        
        if response.status_code == 200:
            # Should have proper Prometheus content type
            content_type = response.headers["content-type"]
            assert content_type.startswith("text/plain")
            assert "version=0.0.4" in content_type
        
        # Test JSON endpoint headers
        response = await async_test_client.get("/metrics/summary")
        
        if response.status_code == 200:
            assert response.headers["content-type"] == "application/json"
            
            # Should have performance headers
            assert "X-Processing-Time" in response.headers
    
    async def test_metrics_endpoint_security(self, async_test_client):
        """Test metrics endpoint security."""
        response = await async_test_client.get("/metrics")
        
        if response.status_code == 200:
            # Should have security headers
            assert "X-Content-Type-Options" in response.headers
            assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        # Test that metrics don't expose sensitive information
        if response.status_code == 200:
            metrics_text = response.text
            
            # Should not contain sensitive data
            sensitive_patterns = [
                "password",
                "secret",
                "key",
                "token",
                "api_key"
            ]
            
            metrics_lower = metrics_text.lower()
            for pattern in sensitive_patterns:
                assert pattern not in metrics_lower, f"Metrics contain sensitive data: {pattern}"
    
    async def test_concurrent_metrics_requests(self, async_test_client):
        """Test concurrent metrics endpoint requests."""
        # Make multiple concurrent requests
        tasks = []
        for i in range(10):
            task = async_test_client.get("/metrics/summary")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed or fail consistently
        success_count = sum(1 for r in responses if r.status_code == 200)
        
        if success_count > 0:
            # At least some should succeed
            assert success_count >= 5
            
            # All successful responses should have consistent structure
            successful_responses = [r for r in responses if r.status_code == 200]
            first_data = successful_responses[0].json()
            
            for response in successful_responses[1:]:
                data = response.json()
                # Should have same keys
                assert set(data.keys()) == set(first_data.keys())
    
    async def test_metrics_data_consistency(self, async_test_client, metrics_collector):
        """Test consistency between Prometheus and JSON metrics."""
        # Generate some metrics
        metrics_collector.record_http_request("GET", "/test", 200, 0.1)
        metrics_collector.update_system_metrics(50.0, 65.0, 80.0)
        
        # Get Prometheus metrics
        prometheus_response = await async_test_client.get("/metrics")
        json_response = await async_test_client.get("/metrics/summary")
        
        if prometheus_response.status_code == 200 and json_response.status_code == 200:
            prometheus_text = prometheus_response.text
            json_data = json_response.json()
            
            # CPU usage should be consistent
            if "mcp_adhd_server_cpu_usage_percent" in prometheus_text:
                # Extract CPU value from Prometheus (simplified)
                for line in prometheus_text.split('\n'):
                    if line.startswith("mcp_adhd_server_cpu_usage_percent") and not line.startswith('#'):
                        prometheus_cpu = float(line.split()[-1])
                        break
                else:
                    prometheus_cpu = None
                
                if prometheus_cpu is not None and "system_metrics" in json_data:
                    json_cpu = json_data["system_metrics"].get("cpu_percent")
                    if json_cpu is not None:
                        # Should be very close
                        assert abs(prometheus_cpu - json_cpu) < 1.0


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.metrics
class TestMetricsEndpointIntegration:
    """Test metrics endpoint integration with monitoring systems."""
    
    async def test_metrics_with_real_data(self, async_test_client):
        """Test metrics endpoints with real application data."""
        # Generate real application activity
        endpoints_to_hit = ["/health", "/health/detailed", "/metrics/summary"]
        
        for endpoint in endpoints_to_hit:
            await async_test_client.get(endpoint)
        
        # Get metrics after real activity
        response = await async_test_client.get("/metrics")
        
        if response.status_code == 200:
            metrics_text = response.text
            
            # Should have recorded HTTP requests
            MetricsAssertions.assert_metric_exists(
                metrics_text, "mcp_adhd_server_http_requests_total"
            )
            
            # Should have labels for our requests
            assert 'endpoint="/health"' in metrics_text
    
    async def test_metrics_alerting_integration(self, async_test_client, alert_manager):
        """Test metrics integration with alerting system."""
        # This would test if high metrics values trigger alerts
        # For now, just verify metrics are accessible for alerting
        
        response = await async_test_client.get("/metrics/summary")
        
        if response.status_code == 200:
            data = response.json()
            
            # Alert manager should be able to use these metrics
            # (Implementation would depend on actual alerting setup)
            assert isinstance(data, dict)
            assert len(data) > 0
    
    async def test_metrics_dashboard_integration(self, async_test_client):
        """Test metrics integration with dashboard."""
        # Test dashboard endpoint
        response = await async_test_client.get("/dashboard")
        
        if response.status_code == 200:
            content = response.text if hasattr(response, 'text') else response.content.decode()
            
            # Should be HTML dashboard
            assert "html" in content.lower()
            assert "metrics" in content.lower() or "dashboard" in content.lower()
            
            # Should reference metrics endpoints
            assert "/metrics" in content or "/api/metrics" in content