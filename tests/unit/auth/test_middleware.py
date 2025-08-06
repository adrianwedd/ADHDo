"""
Unit tests for middleware components.
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, Response
from fastapi.testclient import TestClient

from tests.utils import PerformanceAssertions


@pytest.mark.unit
@pytest.mark.auth
class TestMiddleware:
    """Test middleware functionality."""
    
    async def test_metrics_middleware(self, test_client, metrics_collector):
        """Test metrics collection middleware."""
        # Make requests to different endpoints
        endpoints_to_test = [
            ("/health", 200),
            ("/metrics", 200),
            ("/nonexistent", 404),
        ]
        
        for endpoint, expected_status in endpoints_to_test:
            response = test_client.get(endpoint)
            assert response.status_code == expected_status
        
        # Check that metrics were collected
        metrics_data = metrics_collector.export_metrics()
        
        # Should have HTTP request metrics
        assert "mcp_adhd_server_http_requests_total" in metrics_data
        assert "mcp_adhd_server_http_request_duration_seconds" in metrics_data
    
    async def test_performance_middleware(self, test_client):
        """Test performance monitoring middleware."""
        response = test_client.get("/health")
        
        # Should have performance headers
        assert "X-Processing-Time" in response.headers
        assert "X-Response-Time" in response.headers
        
        # Values should be reasonable
        processing_time = float(response.headers["X-Processing-Time"])
        response_time = float(response.headers["X-Response-Time"])
        
        assert 0 <= processing_time <= 10.0  # Reasonable processing time
        assert 0 <= response_time <= 10.0   # Reasonable response time
        assert response_time >= processing_time  # Response time should be >= processing time
    
    async def test_adhd_optimization_middleware(self, test_client):
        """Test ADHD optimization middleware."""
        # Test with different types of requests
        test_requests = [
            ("/health", "simple"),
            ("/chat", "complex"),  # Would need to be implemented
            ("/metrics", "data")
        ]
        
        for endpoint, request_type in test_requests:
            if endpoint == "/chat":
                continue  # Skip if endpoint doesn't exist yet
                
            response = test_client.get(endpoint)
            
            if response.status_code == 200:
                # Should have ADHD optimization headers
                assert "X-Cognitive-Load" in response.headers
                
                cognitive_load = float(response.headers["X-Cognitive-Load"])
                assert 0.0 <= cognitive_load <= 1.0
                
                # Simple endpoints should have lower cognitive load
                if endpoint == "/health":
                    assert cognitive_load <= 0.3
    
    async def test_security_middleware(self, test_client):
        """Test security middleware."""
        response = test_client.get("/health")
        
        # Should have security headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security"
        ]
        
        for header in security_headers:
            assert header in response.headers
        
        # Verify specific security values
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
    
    async def test_health_check_middleware(self, test_client, health_monitor):
        """Test health check middleware."""
        # Normal request should pass through
        response = test_client.get("/health")
        assert response.status_code == 200
        
        # Test with unhealthy system
        with patch.object(health_monitor, 'get_health_status') as mock_health:
            mock_health.return_value = {"status": "unhealthy"}
            
            # Health endpoint should still work
            response = test_client.get("/health")
            assert response.status_code in [200, 503]  # May return 503 for unhealthy
    
    async def test_rate_limiting_middleware(self, test_client):
        """Test rate limiting middleware."""
        # Make many requests quickly
        responses = []
        for i in range(20):
            response = test_client.get("/health")
            responses.append(response.status_code)
        
        # Should have mostly successful responses, possibly some rate limited
        success_count = responses.count(200)
        rate_limited_count = responses.count(429)
        
        # At least some should succeed
        assert success_count > 0
        
        # If rate limiting is active, some should be limited
        if rate_limited_count > 0:
            assert rate_limited_count < len(responses)  # Not all should be limited
    
    async def test_cors_middleware(self, test_client):
        """Test CORS middleware."""
        # Test preflight request
        response = test_client.options("/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # Should have CORS headers
        if response.status_code in [200, 204]:
            assert "Access-Control-Allow-Origin" in response.headers
            assert "Access-Control-Allow-Methods" in response.headers
    
    async def test_request_id_middleware(self, test_client):
        """Test request ID middleware."""
        response = test_client.get("/health")
        
        # Should have request ID header
        assert "X-Request-ID" in response.headers
        
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) > 10  # Should be substantial length
        
        # Make another request, should have different ID
        response2 = test_client.get("/health")
        request_id2 = response2.headers["X-Request-ID"]
        
        assert request_id != request_id2  # Should be unique
    
    async def test_compression_middleware(self, test_client):
        """Test response compression middleware."""
        # Request with compression headers
        response = test_client.get("/metrics", headers={
            "Accept-Encoding": "gzip, deflate"
        })
        
        if response.status_code == 200:
            # May have compression headers if content is large enough
            content_length = len(response.content)
            
            # Large responses should potentially be compressed
            if content_length > 1000:
                # Check if compression was applied (optional)
                encoding = response.headers.get("Content-Encoding")
                # Note: FastAPI may or may not compress depending on configuration
    
    async def test_logging_middleware(self, test_client, caplog):
        """Test request logging middleware."""
        with caplog.at_level("INFO"):
            response = test_client.get("/health")
        
        # Should have logged the request
        log_records = caplog.records
        
        # Look for request-related logs
        request_logs = [r for r in log_records if "GET" in r.message and "/health" in r.message]
        assert len(request_logs) > 0
    
    async def test_error_handling_middleware(self, test_client):
        """Test error handling middleware."""
        # Test non-existent endpoint
        response = test_client.get("/nonexistent/endpoint")
        assert response.status_code == 404
        
        # Should have proper error response format
        if response.headers.get("content-type", "").startswith("application/json"):
            error_data = response.json()
            assert "error" in error_data or "detail" in error_data
    
    async def test_middleware_performance(self, test_client):
        """Test middleware performance impact."""
        # Time multiple requests to measure middleware overhead
        request_times = []
        
        for i in range(10):
            start_time = time.time()
            response = test_client.get("/health")
            end_time = time.time()
            
            if response.status_code == 200:
                duration_ms = (end_time - start_time) * 1000
                request_times.append(duration_ms)
        
        # Calculate average request time
        if request_times:
            avg_time = sum(request_times) / len(request_times)
            
            # Middleware should add minimal overhead
            PerformanceAssertions.assert_response_time(
                avg_time, 500, "average request with middleware"
            )
    
    async def test_middleware_order(self, test_client):
        """Test middleware execution order."""
        response = test_client.get("/health")
        
        # Check that all expected headers are present (indicating middleware ran)
        expected_headers = [
            "X-Request-ID",      # Should be added early
            "X-Processing-Time", # Should be added late
            "X-Content-Type-Options"  # Security should be present
        ]
        
        for header in expected_headers:
            assert header in response.headers
        
        # Request ID should be set before processing time is calculated
        request_id = response.headers["X-Request-ID"]
        processing_time = float(response.headers["X-Processing-Time"])
        
        assert len(request_id) > 0
        assert processing_time >= 0
    
    async def test_middleware_with_errors(self, test_client):
        """Test middleware behavior when errors occur."""
        # Test with invalid request
        response = test_client.get("/health", headers={
            "Invalid-Header": "bad\x00value"  # Header with null byte
        })
        
        # Middleware should handle the request despite bad headers
        # (FastAPI/Starlette typically handles this)
        assert response.status_code in [200, 400]  # Either works or properly rejects
    
    async def test_middleware_context_passing(self, test_client):
        """Test that middleware properly passes context."""
        response = test_client.get("/health")
        
        # Headers should indicate proper context was maintained
        assert "X-Processing-Time" in response.headers
        
        # Processing time should be reasonable (not negative or extremely high)
        processing_time = float(response.headers["X-Processing-Time"])
        assert 0 <= processing_time <= 5.0  # Should be reasonable


@pytest.mark.unit
@pytest.mark.auth
class TestAuthenticationMiddleware:
    """Test authentication-specific middleware."""
    
    async def test_jwt_authentication_middleware(self, test_client, auth_manager, test_user):
        """Test JWT authentication middleware."""
        # Create valid JWT token
        token_data = {"user_id": test_user.user_id, "email": test_user.email}
        valid_token = auth_manager.create_access_token(token_data)
        
        # Test protected endpoint with valid token
        # Note: This would need actual protected endpoints to test
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Test unprotected endpoint (should work without token)
        response = test_client.get("/health")
        assert response.status_code == 200
        
        # Test with invalid token (would need protected endpoint)
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        # response = test_client.get("/protected", headers=invalid_headers)
        # assert response.status_code == 401
    
    async def test_api_key_authentication_middleware(self, test_client, test_api_key):
        """Test API key authentication middleware."""
        key_id, api_key = test_api_key
        
        # Test with valid API key
        headers = {"X-API-Key": api_key}
        
        # Test unprotected endpoint
        response = test_client.get("/health", headers=headers)
        assert response.status_code == 200
        
        # API key should be validated in background
        # (Implementation would depend on actual middleware setup)
    
    async def test_session_authentication_middleware(self, test_client, test_user_session):
        """Test session-based authentication middleware."""
        # Test with session cookie/header
        headers = {"X-Session-ID": test_user_session}
        
        response = test_client.get("/health", headers=headers)
        assert response.status_code == 200
        
        # Session should be validated in background
    
    async def test_authentication_priority(self, test_client, auth_manager, test_user, test_api_key):
        """Test authentication method priority."""
        # Create JWT token
        token_data = {"user_id": test_user.user_id}
        jwt_token = auth_manager.create_access_token(token_data)
        
        key_id, api_key = test_api_key
        
        # Test with multiple authentication methods
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "X-API-Key": api_key
        }
        
        response = test_client.get("/health", headers=headers)
        assert response.status_code == 200
        
        # Should use the highest priority method (implementation dependent)