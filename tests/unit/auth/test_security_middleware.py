"""
Tests for security middleware components.

This module tests the comprehensive security middleware including:
- Rate limiting
- Security headers
- CSRF protection
- Crisis support bypass
- Session management
"""
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.responses import Response as StarletteResponse

from mcp_server.security_middleware import (
    SecurityMiddleware, CSRFMiddleware, SessionCleanupMiddleware
)
from mcp_server.config import settings


class TestSecurityMiddleware:
    """Test main security middleware functionality."""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI application."""
        return Mock()
    
    @pytest.fixture
    async def security_middleware(self, mock_app):
        """Create security middleware instance."""
        return SecurityMiddleware(mock_app)
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.url = Mock()
        request.url.path = "/api/test"
        request.method = "POST"
        request.headers = {
            "user-agent": "test-agent",
            "accept-language": "en-US",
            "accept-encoding": "gzip"
        }
        return request
    
    @pytest.fixture
    def mock_response(self):
        """Create mock response."""
        response = Mock(spec=StarletteResponse)
        response.headers = {}
        return response
    
    async def test_security_headers_added(self, security_middleware, mock_request, mock_response):
        """Test that security headers are added to responses."""
        async def mock_call_next(request):
            return mock_response
        
        # Process request
        result = await security_middleware.dispatch(mock_request, mock_call_next)
        
        # Verify security headers were added
        headers = result.headers
        assert "Strict-Transport-Security" in headers
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Content-Security-Policy" in headers
        assert "X-Response-Time" in headers
        
        # Verify HTTPS security
        assert "max-age=31536000" in headers["Strict-Transport-Security"]
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
    
    async def test_rate_limiting_allows_normal_requests(self, security_middleware, mock_request):
        """Test that rate limiting allows normal request rates."""
        # Mock call_next to return a simple response
        async def mock_call_next(request):
            response = Mock(spec=StarletteResponse)
            response.headers = {}
            return response
        
        # Make requests within rate limit
        for i in range(10):  # Well under the default limit
            result = await security_middleware.dispatch(mock_request, mock_call_next)
            assert not isinstance(result, JSONResponse) or result.status_code != 429
    
    async def test_rate_limiting_blocks_excessive_requests(self, security_middleware, mock_request):
        """Test that rate limiting blocks excessive requests."""
        # Mock call_next
        async def mock_call_next(request):
            response = Mock(spec=StarletteResponse)
            response.headers = {}
            return response
        
        # Flood with requests to trigger rate limit
        # Note: This test might be slow due to the actual rate limiting implementation
        request_count = settings.rate_limit_requests_per_minute + 5
        
        responses = []
        for i in range(request_count):
            result = await security_middleware.dispatch(mock_request, mock_call_next)
            responses.append(result)
        
        # Check that some requests were rate limited
        rate_limited_count = sum(1 for r in responses 
                               if isinstance(r, JSONResponse) and r.status_code == 429)
        assert rate_limited_count > 0
    
    async def test_crisis_bypass_detection(self, security_middleware):
        """Test crisis support bypass detection."""
        # Create request with crisis keywords
        crisis_request = Mock(spec=Request)
        crisis_request.client = Mock()
        crisis_request.client.host = "127.0.0.1"
        crisis_request.url = Mock()
        crisis_request.url.path = "/chat"
        crisis_request.method = "POST"
        crisis_request.headers = {"user-agent": "test-agent"}
        
        # Mock request body with crisis content
        crisis_body = b'{"message": "I am having thoughts of suicide and need help"}'
        crisis_request.body = AsyncMock(return_value=crisis_body)
        
        # Test crisis bypass detection
        is_crisis = await security_middleware._check_crisis_bypass(crisis_request)
        assert is_crisis is True
    
    async def test_crisis_bypass_normal_content(self, security_middleware):
        """Test that normal content doesn't trigger crisis bypass."""
        # Create normal request
        normal_request = Mock(spec=Request)
        normal_request.client = Mock()
        normal_request.client.host = "127.0.0.1"
        normal_request.url = Mock()
        normal_request.url.path = "/chat"
        normal_request.method = "POST"
        normal_request.headers = {"user-agent": "test-agent"}
        
        # Mock request body with normal content
        normal_body = b'{"message": "Hello, how can I organize my tasks better?"}'
        normal_request.body = AsyncMock(return_value=normal_body)
        
        # Test crisis bypass detection
        is_crisis = await security_middleware._check_crisis_bypass(normal_request)
        assert is_crisis is False
    
    async def test_adhd_performance_indicator(self, security_middleware, mock_request):
        """Test ADHD performance indicator header."""
        # Mock fast response
        async def fast_call_next(request):
            # Simulate fast processing
            response = Mock(spec=StarletteResponse)
            response.headers = {}
            return response
        
        result = await security_middleware.dispatch(mock_request, fast_call_next)
        
        # Should have optimal performance indicator
        assert "X-ADHD-Performance" in result.headers
        performance_status = result.headers["X-ADHD-Performance"]
        assert performance_status in ["optimal", "acceptable", "slow"]
    
    async def test_rate_limit_cache_cleanup(self, security_middleware):
        """Test rate limit cache cleanup functionality."""
        # Add some test entries to cache
        security_middleware._rate_limit_cache = {
            "test_user_1": {
                "requests": [time.time() - 3700],  # Old request (> 1 hour)
                "blocked_until": 0
            },
            "test_user_2": {
                "requests": [time.time()],  # Recent request
                "blocked_until": 0
            }
        }
        
        # Run cleanup
        await security_middleware._cleanup_rate_limit_cache()
        
        # Verify old entries are cleaned up
        assert "test_user_1" not in security_middleware._rate_limit_cache
        assert "test_user_2" in security_middleware._rate_limit_cache


class TestCSRFMiddleware:
    """Test CSRF protection middleware."""
    
    @pytest.fixture
    def mock_app(self):
        return Mock()
    
    @pytest.fixture
    async def csrf_middleware(self, mock_app):
        return CSRFMiddleware(mock_app)
    
    @pytest.fixture
    def safe_request(self):
        """Create safe method request (GET)."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/data"
        return request
    
    @pytest.fixture
    def unsafe_request(self):
        """Create unsafe method request (POST)."""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = Mock()
        request.url.path = "/api/data"
        request.headers = {}
        request.cookies = {}
        return request
    
    async def test_safe_methods_bypass_csrf(self, csrf_middleware, safe_request):
        """Test that safe methods bypass CSRF protection."""
        async def mock_call_next(request):
            return Mock(spec=StarletteResponse)
        
        # Should pass through without CSRF check
        result = await csrf_middleware.dispatch(safe_request, mock_call_next)
        assert not isinstance(result, JSONResponse) or result.status_code != 403
    
    async def test_api_key_bypass_csrf(self, csrf_middleware, unsafe_request):
        """Test that API key authentication bypasses CSRF."""
        # Add API key authorization header
        unsafe_request.headers = {"authorization": "Bearer api_key_here"}
        
        async def mock_call_next(request):
            return Mock(spec=StarletteResponse)
        
        # Should pass through without CSRF check
        result = await csrf_middleware.dispatch(unsafe_request, mock_call_next)
        assert not isinstance(result, JSONResponse) or result.status_code != 403
    
    async def test_csrf_required_for_unsafe_methods(self, csrf_middleware, unsafe_request):
        """Test that unsafe methods require CSRF token."""
        async def mock_call_next(request):
            return Mock(spec=StarletteResponse)
        
        # Should be blocked due to missing CSRF token
        result = await csrf_middleware.dispatch(unsafe_request, mock_call_next)
        assert isinstance(result, JSONResponse)
        assert result.status_code == 403
        
        # Verify error message mentions CSRF
        response_body = result.body
        assert b"CSRF" in response_body
    
    async def test_csrf_validation_with_valid_tokens(self, csrf_middleware, unsafe_request):
        """Test CSRF validation with valid tokens."""
        # Add CSRF and session tokens
        unsafe_request.headers = {"X-CSRF-Token": "valid_csrf_token"}
        unsafe_request.cookies = {"session_id": "valid_session_id"}
        
        async def mock_call_next(request):
            return Mock(spec=StarletteResponse)
        
        # Mock session validation
        with patch('mcp_server.security_middleware.get_db_session'), \
             patch('mcp_server.security_middleware.enhanced_auth_manager') as mock_auth:
            
            # Mock valid session
            mock_session = Mock()
            mock_auth.validate_session.return_value = mock_session
            
            result = await csrf_middleware.dispatch(unsafe_request, mock_call_next)
            
            # Should pass through with valid tokens
            assert not isinstance(result, JSONResponse) or result.status_code != 403


class TestSessionCleanupMiddleware:
    """Test session cleanup middleware."""
    
    @pytest.fixture
    def mock_app(self):
        return Mock()
    
    @pytest.fixture
    async def cleanup_middleware(self, mock_app):
        return SessionCleanupMiddleware(mock_app)
    
    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/test"
        return request
    
    async def test_periodic_cleanup_trigger(self, cleanup_middleware, mock_request):
        """Test that periodic cleanup is triggered."""
        # Set last cleanup to trigger cleanup
        cleanup_middleware._last_cleanup = 0  # Force cleanup to run
        
        async def mock_call_next(request):
            return Mock(spec=StarletteResponse)
        
        # Mock cleanup functionality
        with patch('mcp_server.security_middleware.get_db_session'), \
             patch('mcp_server.security_middleware.enhanced_auth_manager') as mock_auth:
            
            mock_auth.cleanup_expired_sessions.return_value = 5
            
            result = await cleanup_middleware.dispatch(mock_request, mock_call_next)
            
            # Verify cleanup was called
            mock_auth.cleanup_expired_sessions.assert_called_once()
            
            # Verify last cleanup time was updated
            assert cleanup_middleware._last_cleanup > 0
    
    async def test_cleanup_not_triggered_when_recent(self, cleanup_middleware, mock_request):
        """Test that cleanup is not triggered when recent cleanup occurred."""
        # Set recent cleanup time
        cleanup_middleware._last_cleanup = time.time()
        
        async def mock_call_next(request):
            return Mock(spec=StarletteResponse)
        
        # Mock cleanup functionality
        with patch('mcp_server.security_middleware.get_db_session'), \
             patch('mcp_server.security_middleware.enhanced_auth_manager') as mock_auth:
            
            result = await cleanup_middleware.dispatch(mock_request, mock_call_next)
            
            # Verify cleanup was not called
            mock_auth.cleanup_expired_sessions.assert_not_called()


class TestMiddlewareIntegration:
    """Test middleware integration and interaction."""
    
    async def test_middleware_stack_order(self):
        """Test that middleware stack is applied in correct order."""
        # This would test the complete middleware stack
        pass
    
    async def test_error_handling_across_middleware(self):
        """Test error handling across multiple middleware."""
        # This would test error propagation and handling
        pass
    
    async def test_performance_impact_of_middleware_stack(self):
        """Test that middleware stack meets performance requirements."""
        # This would measure the performance impact of all security middleware
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])