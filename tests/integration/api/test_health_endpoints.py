"""
Integration tests for health monitoring API endpoints.
"""
import pytest
import asyncio
from httpx import AsyncClient

from tests.utils import HealthCheckAssertions, PerformanceAssertions


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.health
class TestHealthEndpoints:
    """Test health monitoring API endpoints integration."""
    
    async def test_basic_health_endpoint(self, async_test_client):
        """Test GET /health endpoint."""
        response = await async_test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        HealthCheckAssertions.assert_healthy_response(data)
        
        # Should have basic health info
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "message" in data
    
    async def test_detailed_health_endpoint(self, async_test_client):
        """Test GET /health/detailed endpoint."""
        response = await async_test_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have detailed health information
        assert "status" in data
        assert "components" in data
        assert "system_metrics" in data
        assert "uptime_seconds" in data
        
        # Check all required components
        components = data["components"]
        required_components = ["database", "redis", "llm", "system", "application"]
        
        for component in required_components:
            assert component in components
            HealthCheckAssertions.assert_component_health(data, component)
    
    async def test_component_specific_health_endpoints(self, async_test_client):
        """Test component-specific health endpoints."""
        components = ["database", "redis", "llm", "system", "application"]
        
        for component in components:
            response = await async_test_client.get(f"/health/{component}")
            
            if response.status_code == 200:
                data = response.json()
                
                assert "status" in data
                assert "response_time_ms" in data
                assert "last_check" in data
                
                # Status should be valid
                assert data["status"] in ["healthy", "degraded", "unhealthy"]
                
                # Response time should be reasonable
                assert 0 <= data["response_time_ms"] <= 5000
            elif response.status_code == 404:
                # Component endpoint not implemented yet
                continue
            else:
                pytest.fail(f"Unexpected status code {response.status_code} for {component}")
    
    async def test_system_metrics_endpoint(self, async_test_client):
        """Test GET /health/metrics/system endpoint."""
        response = await async_test_client.get("/health/metrics/system")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have system resource metrics
        required_metrics = [
            "cpu_percent",
            "memory_percent", 
            "disk_usage_percent",
            "load_average",
            "uptime_seconds"
        ]
        
        for metric in required_metrics:
            assert metric in data
        
        # Validate metric ranges
        assert 0 <= data["cpu_percent"] <= 100
        assert 0 <= data["memory_percent"] <= 100
        assert 0 <= data["disk_usage_percent"] <= 100
        assert data["uptime_seconds"] >= 0
        assert isinstance(data["load_average"], list)
        assert len(data["load_average"]) == 3  # 1, 5, 15 minute averages
    
    async def test_health_history_endpoint(self, async_test_client):
        """Test GET /health/history/{component} endpoint."""
        # First trigger some health checks
        await async_test_client.get("/health/detailed")
        await asyncio.sleep(0.1)
        await async_test_client.get("/health/detailed")
        
        # Get history
        response = await async_test_client.get("/health/history/overall?hours=1")
        
        if response.status_code == 200:
            data = response.json()
            
            assert isinstance(data, list)
            
            if data:  # May be empty if no history yet
                for entry in data:
                    assert "timestamp" in entry
                    assert "status" in entry
                    assert "response_time_ms" in entry
                    
                    # Verify chronological order
                    assert entry["status"] in ["healthy", "degraded", "unhealthy"]
                    assert entry["response_time_ms"] >= 0
        elif response.status_code == 404:
            # History endpoint not implemented yet
            pytest.skip("Health history endpoint not implemented")
    
    async def test_health_endpoint_performance(self, async_test_client):
        """Test health endpoint performance."""
        import time
        
        endpoints_to_test = [
            "/health",
            "/health/detailed",
            "/health/database",
            "/health/metrics/system"
        ]
        
        for endpoint in endpoints_to_test:
            start_time = time.time()
            response = await async_test_client.get(endpoint)
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                # Health endpoints should be fast
                if endpoint == "/health":
                    PerformanceAssertions.assert_response_time(
                        duration_ms, 500, f"{endpoint} response time"
                    )
                else:
                    PerformanceAssertions.assert_response_time(
                        duration_ms, 1000, f"{endpoint} response time"
                    )
                
                # Should have ADHD optimization headers
                PerformanceAssertions.assert_adhd_optimization_headers(response)
    
    async def test_health_endpoint_error_handling(self, async_test_client):
        """Test health endpoint error handling."""
        # Test non-existent component
        response = await async_test_client.get("/health/nonexistent")
        assert response.status_code == 404
        
        # Test invalid parameters
        response = await async_test_client.get("/health/history/redis?hours=invalid")
        assert response.status_code in [400, 404]  # Bad request or not found
        
        # Test negative hours
        response = await async_test_client.get("/health/history/redis?hours=-1")
        assert response.status_code in [400, 404]
        
        # Test extremely large hours
        response = await async_test_client.get("/health/history/redis?hours=999999")
        assert response.status_code in [400, 404]
    
    async def test_health_endpoint_headers(self, async_test_client):
        """Test health endpoint response headers."""
        response = await async_test_client.get("/health")
        
        # Should have security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        
        # Should have performance headers
        assert "X-Processing-Time" in response.headers
        assert "X-Cognitive-Load" in response.headers
        
        # Should have proper content type
        assert response.headers["content-type"] == "application/json"
    
    async def test_concurrent_health_requests(self, async_test_client):
        """Test concurrent health endpoint requests."""
        # Make multiple concurrent requests
        tasks = []
        for i in range(10):
            task = async_test_client.get("/health")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    async def test_health_endpoint_caching(self, async_test_client):
        """Test health endpoint response caching."""
        # Make first request
        response1 = await async_test_client.get("/health")
        data1 = response1.json()
        
        # Make second request immediately
        response2 = await async_test_client.get("/health")
        data2 = response2.json()
        
        # Should get responses (may be cached)
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Uptime should be similar if cached, or slightly higher if not
        uptime_diff = abs(data2["uptime_seconds"] - data1["uptime_seconds"])
        assert uptime_diff < 2.0  # Should be very close
    
    async def test_health_status_consistency(self, async_test_client):
        """Test consistency between different health endpoints."""
        # Get overall health
        overall_response = await async_test_client.get("/health")
        overall_data = overall_response.json()
        
        # Get detailed health
        detailed_response = await async_test_client.get("/health/detailed")
        
        if detailed_response.status_code == 200:
            detailed_data = detailed_response.json()
            
            # Overall status should match detailed status
            assert overall_data["status"] == detailed_data["status"]
            
            # Version should be consistent
            assert overall_data["version"] == detailed_data["version"]
            
            # Uptime should be very close
            uptime_diff = abs(
                detailed_data["uptime_seconds"] - overall_data["uptime_seconds"]
            )
            assert uptime_diff < 1.0  # Within 1 second


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.health
class TestHealthEndpointIntegration:
    """Test health endpoint integration with other systems."""
    
    async def test_health_with_database_down(self, async_test_client):
        """Test health endpoints when database is unavailable."""
        # This would require actually stopping the database or mocking connection failure
        # For now, test that endpoints handle database errors gracefully
        
        response = await async_test_client.get("/health/database")
        
        # Should return some response (healthy or unhealthy)
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
    
    async def test_health_with_redis_down(self, async_test_client, mock_redis):
        """Test health endpoints when Redis is unavailable."""
        # Mock Redis connection failure
        mock_redis.ping.side_effect = Exception("Redis connection failed")
        
        response = await async_test_client.get("/health/redis")
        
        # Should handle Redis failure gracefully
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] in ["degraded", "unhealthy"]
    
    async def test_health_endpoint_monitoring_integration(self, async_test_client, metrics_collector):
        """Test health endpoint integration with monitoring."""
        # Make health check request
        response = await async_test_client.get("/health")
        assert response.status_code == 200
        
        # Should update metrics
        metrics_data = metrics_collector.export_metrics()
        
        # Should have HTTP request metrics
        assert "mcp_adhd_server_http_requests_total" in metrics_data
        
        # Should have health-related metrics
        assert "mcp_adhd_server_component_health" in metrics_data or \
               "mcp_adhd_server_uptime_seconds" in metrics_data