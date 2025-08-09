"""
Tests for ADHD-friendly error handling system.

This module tests the comprehensive error transformation system
to ensure it provides supportive, clear, and actionable error messages
optimized for users with ADHD.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError, IntegrityError
from redis.exceptions import ConnectionError as RedisConnectionError

from mcp_server.adhd_errors import (
    error_transformer, create_adhd_error_response, ErrorContext,
    ErrorCategory, ErrorSeverity, ADHDFriendlyError,
    authentication_error, validation_error, rate_limit_error,
    system_error, not_found_error, adhd_feature_error
)
from mcp_server.exception_handlers import (
    http_exception_handler, validation_exception_handler,
    database_exception_handler, redis_exception_handler,
    timeout_exception_handler, general_exception_handler,
    adhd_feature_exception_handler, cognitive_overload_exception_handler,
    circuit_breaker_exception_handler, ADHDFeatureException,
    CognitiveOverloadException, CircuitBreakerOpenException
)


class TestADHDErrorTransformer:
    """Test the core error transformation logic."""
    
    def test_transform_authentication_error(self):
        """Test transformation of authentication errors."""
        error = HTTPException(status_code=401, detail="Invalid credentials")
        context = ErrorContext(user_id="test_user")
        
        friendly_error = error_transformer.transform_error(error, context)
        
        assert friendly_error.category == ErrorCategory.AUTHENTICATION
        assert friendly_error.severity == ErrorSeverity.MEDIUM
        assert "sign" in friendly_error.title.lower()
        assert "password" in friendly_error.message.lower()
        assert len(friendly_error.next_steps) > 0
        assert friendly_error.support_message  # Should have encouragement
    
    def test_transform_validation_error(self):
        """Test transformation of validation errors."""
        error = "field required"
        context = ErrorContext(endpoint="/api/auth/register")
        
        friendly_error = error_transformer.transform_error(error, context, 422)
        
        assert friendly_error.category == ErrorCategory.VALIDATION
        assert friendly_error.severity == ErrorSeverity.LOW
        assert "missing" in friendly_error.title.lower() or "information" in friendly_error.title.lower()
        assert "field" in friendly_error.message.lower()
        assert any("fill" in step.lower() for step in friendly_error.next_steps)
    
    def test_transform_rate_limit_error(self):
        """Test transformation of rate limiting errors."""
        error = "rate limit exceeded"
        context = ErrorContext(cognitive_load=0.8)
        
        friendly_error = error_transformer.transform_error(error, context, 429)
        
        assert friendly_error.category == ErrorCategory.RATE_LIMIT
        assert friendly_error.severity == ErrorSeverity.LOW
        assert "breather" in friendly_error.message.lower() or "wait" in friendly_error.message.lower()
        assert any("wait" in step.lower() for step in friendly_error.next_steps)
    
    def test_transform_database_error(self):
        """Test transformation of database errors."""
        error = "database connection failed"
        
        friendly_error = error_transformer.transform_error(error, None, 500)
        
        assert friendly_error.category == ErrorCategory.DATABASE
        assert friendly_error.severity == ErrorSeverity.HIGH
        assert "safe" in friendly_error.user_impact.lower()
        assert friendly_error.estimated_fix_time is not None
        assert any("refresh" in step.lower() for step in friendly_error.next_steps)
    
    def test_transform_circuit_breaker_error(self):
        """Test transformation of circuit breaker errors."""
        error = "circuit breaker open"
        context = ErrorContext(user_id="adhd_user", cognitive_load=0.9)
        
        friendly_error = error_transformer.transform_error(error, context, 503)
        
        assert friendly_error.category == ErrorCategory.CIRCUIT_BREAKER
        assert friendly_error.severity == ErrorSeverity.HIGH
        assert "break" in friendly_error.message.lower() or "protective" in friendly_error.message.lower()
        assert len(friendly_error.recovery_suggestions) > 0
        assert "self-care" in friendly_error.support_message.lower() or "break" in friendly_error.support_message.lower()
    
    def test_personalization_high_cognitive_load(self):
        """Test personalization for high cognitive load."""
        error = "generic error"
        context = ErrorContext(cognitive_load=0.8)
        
        friendly_error = error_transformer.transform_error(error, context, 500)
        
        # Should limit next steps for high cognitive load
        assert len(friendly_error.next_steps) <= 2
        assert "simple" in friendly_error.message.lower() or "time" in friendly_error.support_message.lower()
    
    def test_personalization_repeat_error(self):
        """Test personalization for repeat errors."""
        context = ErrorContext(is_repeat_error=True)
        error = "same error again"
        
        friendly_error = error_transformer.transform_error(error, context, 500)
        
        assert "repeatedly" in friendly_error.support_message.lower() or "recurring" in ' '.join(friendly_error.next_steps).lower()
        assert any("support" in step.lower() for step in friendly_error.next_steps)


class TestADHDErrorResponse:
    """Test the ADHD-friendly error response generation."""
    
    def test_create_adhd_error_response_basic(self):
        """Test basic error response creation."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.headers = {}
        
        response = create_adhd_error_response(
            error="Test error",
            status_code=500,
            request=mock_request
        )
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        assert "X-ADHD-Optimized" in response.headers
        assert response.headers["X-ADHD-Optimized"] == "true"
    
    def test_create_adhd_error_response_with_context(self):
        """Test error response creation with user context."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/chat"
        mock_request.headers = {
            "X-User-ID": "test_user",
            "X-Cognitive-Load": "0.7"
        }
        
        response = create_adhd_error_response(
            error=HTTPException(status_code=429, detail="Rate limit exceeded"),
            status_code=429,
            request=mock_request
        )
        
        assert response.status_code == 429
        assert "X-Error-Category" in response.headers
        assert "X-Error-Severity" in response.headers
    
    def test_convenience_functions(self):
        """Test convenience error functions."""
        # Test authentication error
        auth_response = authentication_error("Invalid token")
        assert auth_response.status_code == 401
        
        # Test validation error
        validation_response = validation_error("Missing field")
        assert validation_response.status_code == 400
        
        # Test rate limit error
        rate_limit_response = rate_limit_error(60)
        assert rate_limit_response.status_code == 429
        assert "Retry-After" in rate_limit_response.headers
        
        # Test system error
        system_response = system_error("Database error")
        assert system_response.status_code == 500
        
        # Test not found error
        not_found_response = not_found_error("User")
        assert not_found_response.status_code == 404


class TestExceptionHandlers:
    """Test the FastAPI exception handlers."""
    
    @pytest.mark.asyncio
    async def test_http_exception_handler(self):
        """Test HTTP exception handler."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.headers = {}
        
        exc = HTTPException(status_code=404, detail="Not found")
        
        with patch('mcp_server.exception_handlers.health_monitor') as mock_health:
            response = await http_exception_handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        mock_health.record_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validation_exception_handler(self):
        """Test validation exception handler."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/auth/register"
        mock_request.headers = {}
        
        # Create mock validation error
        mock_validation_error = Mock()
        mock_validation_error.errors.return_value = [
            {"type": "missing", "loc": ["email"], "msg": "field required"},
            {"type": "missing", "loc": ["password"], "msg": "field required"}
        ]
        
        with patch('mcp_server.exception_handlers.health_monitor') as mock_health:
            response = await validation_exception_handler(mock_request, mock_validation_error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        mock_health.record_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_exception_handler(self):
        """Test database exception handler."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/users"
        mock_request.headers = {}
        
        exc = OperationalError("connection failed", None, None)
        
        with patch('mcp_server.exception_handlers.health_monitor') as mock_health:
            response = await database_exception_handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        mock_health.record_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_exception_handler(self):
        """Test Redis exception handler."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/cache"
        mock_request.headers = {}
        
        exc = RedisConnectionError("Redis connection failed")
        
        with patch('mcp_server.exception_handlers.health_monitor') as mock_health:
            response = await redis_exception_handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 503
        mock_health.record_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_timeout_exception_handler(self):
        """Test timeout exception handler."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/slow"
        mock_request.headers = {}
        
        exc = asyncio.TimeoutError()
        
        with patch('mcp_server.exception_handlers.health_monitor') as mock_health:
            response = await timeout_exception_handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 504
        mock_health.record_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_adhd_feature_exception_handler(self):
        """Test ADHD feature exception handler."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/nudge"
        mock_request.headers = {}
        
        exc = ADHDFeatureException("nudge", "Failed to send nudge", recoverable=True)
        
        with patch('mcp_server.exception_handlers.health_monitor') as mock_health:
            response = await adhd_feature_exception_handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        assert "X-Error-Category" in response.headers
        assert response.headers["X-Error-Category"] == "adhd_feature"
        mock_health.record_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cognitive_overload_exception_handler(self):
        """Test cognitive overload exception handler."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/chat"
        mock_request.headers = {}
        
        exc = CognitiveOverloadException(current_load=0.9, threshold=0.8)
        
        with patch('mcp_server.exception_handlers.health_monitor') as mock_health:
            response = await cognitive_overload_exception_handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert "X-Protection-Active" in response.headers
        mock_health.record_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_exception_handler(self):
        """Test circuit breaker exception handler."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/chat"
        mock_request.headers = {}
        
        exc = CircuitBreakerOpenException(recovery_time="2 hours")
        
        with patch('mcp_server.exception_handlers.health_monitor') as mock_health:
            response = await circuit_breaker_exception_handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 503
        assert "X-Circuit-Breaker" in response.headers
        assert response.headers["X-Circuit-Breaker"] == "open"
        mock_health.record_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """Test general exception handler fallback."""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/unknown"
        mock_request.headers = {}
        
        exc = Exception("Unexpected error")
        
        with patch('mcp_server.exception_handlers.health_monitor') as mock_health:
            response = await general_exception_handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        assert "X-ADHD-Optimized" in response.headers
        mock_health.record_error.assert_called_once()


class TestADHDFriendlyErrorObject:
    """Test the ADHDFriendlyError data structure."""
    
    def test_error_object_creation(self):
        """Test creating ADHD-friendly error object."""
        from datetime import datetime
        
        error = ADHDFriendlyError(
            title="Test Error",
            message="Something went wrong, but don't worry!",
            next_steps=["Try again", "Contact support"],
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SYSTEM,
            user_impact="Temporary issue",
            support_message="You're doing great!",
            timestamp=datetime.utcnow()
        )
        
        assert error.title == "Test Error"
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.category == ErrorCategory.SYSTEM
        assert len(error.next_steps) == 2
    
    def test_error_to_response_basic(self):
        """Test converting error to API response format."""
        from datetime import datetime
        
        error = ADHDFriendlyError(
            title="Test Error",
            message="Test message",
            next_steps=["Step 1", "Step 2"],
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            user_impact="Minor issue",
            support_message="All good!",
            timestamp=datetime.utcnow()
        )
        
        response = error.to_response()
        
        assert "error" in response
        assert response["error"]["title"] == "Test Error"
        assert response["error"]["severity"] == "low"
        assert response["error"]["category"] == "validation"
        assert len(response["error"]["next_steps"]) == 2
    
    def test_error_to_response_with_technical(self):
        """Test converting error to response with technical details."""
        from datetime import datetime
        
        error = ADHDFriendlyError(
            title="Test Error",
            message="Test message",
            next_steps=["Step 1"],
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.SYSTEM,
            user_impact="System issue",
            support_message="Support available",
            timestamp=datetime.utcnow(),
            technical_details="Stack trace here"
        )
        
        response = error.to_response(include_technical=True)
        
        assert "technical_details" in response["error"]
        assert response["error"]["technical_details"] == "Stack trace here"
        
        # Test without technical details
        response_no_tech = error.to_response(include_technical=False)
        assert "technical_details" not in response_no_tech["error"]


class TestErrorPatternMatching:
    """Test error pattern matching and categorization."""
    
    def test_authentication_patterns(self):
        """Test authentication error pattern matching."""
        auth_errors = [
            "invalid credentials",
            "authentication failed", 
            "login failed",
            "incorrect password",
            "user not found"
        ]
        
        for error_text in auth_errors:
            friendly_error = error_transformer.transform_error(error_text, None, 401)
            assert friendly_error.category == ErrorCategory.AUTHENTICATION
    
    def test_validation_patterns(self):
        """Test validation error pattern matching."""
        validation_errors = [
            "field required",
            "missing required field",
            "invalid format",
            "validation error"
        ]
        
        for error_text in validation_errors:
            friendly_error = error_transformer.transform_error(error_text, None, 422)
            assert friendly_error.category == ErrorCategory.VALIDATION
    
    def test_system_error_patterns(self):
        """Test system error pattern matching."""
        system_errors = [
            "database connection failed",
            "external service unavailable",
            "request timeout",
            "internal server error"
        ]
        
        for error_text in system_errors:
            friendly_error = error_transformer.transform_error(error_text, None, 500)
            assert friendly_error.category in [
                ErrorCategory.DATABASE, 
                ErrorCategory.EXTERNAL_API, 
                ErrorCategory.TIMEOUT,
                ErrorCategory.SYSTEM
            ]


class TestErrorContextPersonalization:
    """Test error personalization based on user context."""
    
    def test_endpoint_specific_context(self):
        """Test error personalization based on endpoint."""
        chat_context = ErrorContext(endpoint="/api/chat")
        auth_context = ErrorContext(endpoint="/api/auth/login")
        
        chat_error = error_transformer.transform_error("generic error", chat_context, 500)
        auth_error = error_transformer.transform_error("generic error", auth_context, 500)
        
        # Context should influence the response
        assert chat_error.message != auth_error.message or chat_error.next_steps != auth_error.next_steps
    
    def test_cognitive_load_adaptation(self):
        """Test adaptation based on cognitive load."""
        low_load = ErrorContext(cognitive_load=0.2)
        high_load = ErrorContext(cognitive_load=0.8)
        
        low_load_error = error_transformer.transform_error("complex error", low_load, 500)
        high_load_error = error_transformer.transform_error("complex error", high_load, 500)
        
        # High cognitive load should result in simplified responses
        assert len(high_load_error.next_steps) <= len(low_load_error.next_steps)
    
    def test_user_preferences_integration(self):
        """Test integration with user preferences."""
        verbose_context = ErrorContext(
            user_preferences={"verbose_errors": True}
        )
        minimal_context = ErrorContext(
            user_preferences={"verbose_errors": False}
        )
        
        verbose_error = error_transformer.transform_error("error", verbose_context, 500)
        minimal_error = error_transformer.transform_error("error", minimal_context, 500)
        
        # Verbose preference might add explanation
        assert len(verbose_error.next_steps) >= len(minimal_error.next_steps)


@pytest.mark.integration
class TestIntegrationWithMiddleware:
    """Integration tests with middleware error handling."""
    
    @pytest.mark.asyncio
    async def test_middleware_error_transformation(self):
        """Test that middleware properly transforms errors."""
        # This would require a full FastAPI app setup
        # For now, we'll test the transformation logic directly
        pass
    
    @pytest.mark.asyncio  
    async def test_end_to_end_error_flow(self):
        """Test complete error flow from exception to response."""
        # This would test the full pipeline:
        # Exception -> Handler -> Transformer -> Response
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])