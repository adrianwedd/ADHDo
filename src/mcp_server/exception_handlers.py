"""
Custom Exception Handlers for ADHD-Friendly Error Responses.

This module provides FastAPI exception handlers that automatically transform
various error types into ADHD-optimized responses using the ADHD error system.
"""

import asyncio
import structlog
from typing import Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from .adhd_errors import create_adhd_error_response, ErrorContext, error_transformer
from .health_monitor import health_monitor

logger = structlog.get_logger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTPException with ADHD-friendly responses.
    
    Transforms standard FastAPI HTTP exceptions into supportive,
    actionable error messages.
    """
    try:
        # Record the error for monitoring
        health_monitor.record_error("http_exception", f"{exc.status_code}: {exc.detail}")
        
        # Create ADHD-friendly response
        return create_adhd_error_response(
            error=exc,
            status_code=exc.status_code,
            request=request,
            include_technical=False
        )
    
    except Exception as e:
        logger.error("Error in HTTP exception handler", error=str(e), exc_info=True)
        # Fallback to basic error response
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "title": "Something Went Wrong",
                    "message": "We encountered an issue and are working to fix it. Please try again in a moment.",
                    "support_message": "Don't worry - these things happen!",
                    "next_steps": ["Try refreshing the page", "Contact support if this continues"]
                }
            }
        )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors with ADHD-friendly guidance.
    
    Transforms complex validation errors into simple, actionable instructions.
    """
    try:
        # Extract validation errors and make them user-friendly
        validation_errors = []
        missing_fields = []
        format_errors = []
        
        for error in exc.errors():
            error_type = error.get("type", "")
            field = ".".join(str(loc) for loc in error.get("loc", []))
            
            if "missing" in error_type:
                missing_fields.append(field)
            elif "type_error" in error_type or "value_error" in error_type:
                format_errors.append(field)
            else:
                validation_errors.append(f"{field}: {error.get('msg', 'Invalid format')}")
        
        # Build user-friendly message
        if missing_fields:
            primary_message = f"We need some additional information to complete your request."
            next_steps = [f"Please fill in: {', '.join(missing_fields)}", "Double-check all required fields", "Try submitting again"]
        elif format_errors:
            primary_message = f"Some information isn't in the expected format."
            next_steps = [f"Please check the format for: {', '.join(format_errors)}", "Look for examples or hints near the field", "Make sure dates, emails, etc. are correctly formatted"]
        else:
            primary_message = "There are some issues with the information provided."
            next_steps = ["Review the highlighted fields", "Check the format requirements", "Try making the corrections and submitting again"]
        
        # Record validation error for monitoring
        health_monitor.record_error("validation_error", f"Fields: {missing_fields + format_errors}")
        
        # Create friendly validation error
        fake_exc = HTTPException(
            status_code=422,
            detail=f"Validation error: {'; '.join(validation_errors[:3])}"  # Limit details
        )
        
        response = create_adhd_error_response(
            error=fake_exc,
            status_code=422,
            request=request,
            include_technical=False
        )
        
        # Override with specific validation messaging
        response_data = response.body.decode('utf-8')
        import json
        content = json.loads(response_data)
        content["error"]["message"] = primary_message
        content["error"]["next_steps"] = next_steps
        content["error"]["title"] = "Form Check Needed"
        content["error"]["validation_details"] = {
            "missing_fields": missing_fields,
            "format_errors": format_errors
        }
        
        return JSONResponse(
            status_code=422,
            content=content,
            headers=response.headers
        )
    
    except Exception as e:
        logger.error("Error in validation exception handler", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "title": "Form Check Needed",
                    "message": "Please double-check the information you entered and try again.",
                    "next_steps": ["Review all fields for accuracy", "Make sure required fields are filled", "Try submitting again"],
                    "support_message": "No worries - forms can be tricky sometimes!"
                }
            }
        )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle database-related errors with ADHD-friendly messaging.
    
    Transforms database errors into reassuring messages about data safety.
    """
    try:
        # Determine the type of database error
        if isinstance(exc, OperationalError):
            error_message = "Database connection error"
            user_message = "We're having trouble connecting to our database right now. Your data is safe - just a temporary hiccup!"
            next_steps = [
                "Wait about 2-3 minutes for the connection to restore",
                "Try refreshing the page",
                "Your information is securely stored"
            ]
            estimated_time = "Usually resolves in 2-5 minutes"
        
        elif isinstance(exc, IntegrityError):
            error_message = "Data integrity error"
            user_message = "There's a conflict with existing data. This helps keep your information accurate and consistent."
            next_steps = [
                "Check if this information already exists",
                "Try using different values",
                "Contact support if you're not sure what's wrong"
            ]
            estimated_time = None
            
        else:
            error_message = "Database error"
            user_message = "We encountered a database issue. Don't worry - your data is protected!"
            next_steps = [
                "Try your action again in a moment",
                "Refresh the page if needed", 
                "Contact support if this keeps happening"
            ]
            estimated_time = "Usually temporary"
        
        # Record database error for monitoring
        health_monitor.record_error("database_error", error_message)
        
        # Create ADHD-friendly database error
        fake_exc = HTTPException(status_code=500, detail=error_message)
        response = create_adhd_error_response(
            error=fake_exc,
            status_code=500,
            request=request
        )
        
        # Override with database-specific messaging
        response_data = response.body.decode('utf-8')
        import json
        content = json.loads(response_data)
        content["error"]["title"] = "Database Hiccup"
        content["error"]["message"] = user_message
        content["error"]["next_steps"] = next_steps
        content["error"]["user_impact"] = "Your data is completely safe"
        if estimated_time:
            content["error"]["estimated_fix_time"] = estimated_time
        
        return JSONResponse(
            status_code=500,
            content=content,
            headers=response.headers
        )
    
    except Exception as e:
        logger.error("Error in database exception handler", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "title": "Database Issue",
                    "message": "We're having a small database issue. Your data is safe, and we're working on it!",
                    "next_steps": ["Try again in a few minutes", "Your information is securely stored"],
                    "support_message": "Technical hiccups happen - we've got your back!"
                }
            }
        )


async def redis_exception_handler(request: Request, exc: RedisError) -> JSONResponse:
    """
    Handle Redis/caching errors with ADHD-friendly messaging.
    
    Transforms cache errors into reassuring messages about core functionality.
    """
    try:
        if isinstance(exc, RedisConnectionError):
            error_message = "Cache connection error"
            user_message = "Our caching system is taking a break. Everything still works, just might be a tiny bit slower."
        else:
            error_message = "Cache error"
            user_message = "We're having a small issue with our speed optimization system. Core features work normally!"
        
        # Record Redis error for monitoring
        health_monitor.record_error("redis_error", error_message)
        
        fake_exc = HTTPException(status_code=503, detail=error_message)
        response = create_adhd_error_response(
            error=fake_exc,
            status_code=503,
            request=request
        )
        
        # Override with cache-specific messaging
        response_data = response.body.decode('utf-8')
        import json
        content = json.loads(response_data)
        content["error"]["title"] = "Speed System Hiccup"
        content["error"]["message"] = user_message
        content["error"]["next_steps"] = [
            "Everything works normally, just slightly slower",
            "No action needed on your part",
            "Speed will return to normal soon"
        ]
        content["error"]["user_impact"] = "Slightly slower responses, but all features work"
        content["error"]["estimated_fix_time"] = "Usually resolves quickly"
        
        return JSONResponse(
            status_code=503,
            content=content,
            headers=response.headers
        )
    
    except Exception as e:
        logger.error("Error in Redis exception handler", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "title": "Performance System Issue",
                    "message": "Our speed optimization system is having a small issue. Everything still works normally!",
                    "next_steps": ["No action needed", "All features remain available"],
                    "support_message": "Just a minor hiccup - you're all set!"
                }
            }
        )


async def timeout_exception_handler(request: Request, exc: asyncio.TimeoutError) -> JSONResponse:
    """
    Handle timeout errors with ADHD-friendly patience and guidance.
    """
    try:
        # Record timeout error
        health_monitor.record_error("timeout_error", f"Timeout on {request.url.path}")
        
        fake_exc = HTTPException(status_code=504, detail="Request timeout")
        response = create_adhd_error_response(
            error=fake_exc,
            status_code=504,
            request=request
        )
        
        # Override with timeout-specific messaging
        response_data = response.body.decode('utf-8')
        import json
        content = json.loads(response_data)
        content["error"]["title"] = "Taking Longer Than Expected"
        content["error"]["message"] = "This request is taking longer than usual. Sometimes the system just needs a moment!"
        content["error"]["next_steps"] = [
            "Try the same action again",
            "Check your internet connection", 
            "Wait a minute and refresh if needed",
            "Contact support if this keeps happening"
        ]
        content["error"]["user_impact"] = "Temporary delay, your data and progress are safe"
        content["error"]["support_message"] = "Patience is a virtue - and you're being very patient!"
        
        return JSONResponse(
            status_code=504,
            content=content,
            headers=response.headers
        )
    
    except Exception as e:
        logger.error("Error in timeout exception handler", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=504,
            content={
                "error": {
                    "title": "Slow Response",
                    "message": "The request is taking longer than expected. Please try again!",
                    "next_steps": ["Try again", "Check your connection", "Be patient with the system"],
                    "support_message": "Sometimes these things take time!"
                }
            }
        )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle any unhandled exceptions with ADHD-friendly fallback messaging.
    
    This is the last resort handler for any errors not caught by specific handlers.
    """
    try:
        # Log the unexpected error for debugging
        logger.error(
            "Unhandled exception",
            path=str(request.url.path),
            method=request.method,
            error=str(exc)[:200],  # Truncate long errors
            exc_info=True
        )
        
        # Record for monitoring
        health_monitor.record_error("unhandled_exception", str(exc)[:100])
        
        # Create a gentle, ADHD-friendly response
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "title": "Unexpected Issue",
                    "message": "We hit an unexpected bump. This isn't your fault - sometimes these things just happen!",
                    "next_steps": [
                        "Try refreshing the page",
                        "Wait a moment and try your action again",
                        "Contact support if this keeps happening"
                    ],
                    "support_message": "Every system has its quirks - we're here to help!",
                    "user_impact": "Temporary issue, your data and progress remain safe",
                    "category": "system",
                    "severity": "medium"
                }
            },
            headers={
                "X-Error-Category": "system",
                "X-Error-Severity": "medium", 
                "X-ADHD-Optimized": "true",
                "Cache-Control": "no-cache, no-store, must-revalidate"
            }
        )
    
    except Exception as e:
        # If even our error handler fails, provide absolute minimal response
        logger.critical("Exception handler failed", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Something went wrong. Please try again or contact support.",
                    "support_message": "We're here to help!"
                }
            }
        )


# ADHD-specific exception handlers
class ADHDFeatureException(Exception):
    """Custom exception for ADHD-specific feature errors."""
    def __init__(self, feature: str, message: str, recoverable: bool = True):
        self.feature = feature
        self.message = message
        self.recoverable = recoverable
        super().__init__(f"{feature}: {message}")


class CognitiveOverloadException(Exception):
    """Exception raised when cognitive load exceeds safe thresholds."""
    def __init__(self, current_load: float, threshold: float):
        self.current_load = current_load
        self.threshold = threshold
        super().__init__(f"Cognitive load {current_load} exceeds threshold {threshold}")


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open for user protection."""
    def __init__(self, recovery_time: str):
        self.recovery_time = recovery_time
        super().__init__(f"Circuit breaker open, recovery in {recovery_time}")


async def adhd_feature_exception_handler(request: Request, exc: ADHDFeatureException) -> JSONResponse:
    """Handle ADHD-specific feature errors with supportive messaging."""
    try:
        # Record ADHD feature error
        health_monitor.record_error("adhd_feature_error", f"{exc.feature}: {exc.message}")
        
        # Create supportive response
        if exc.feature.lower() == "nudge":
            title = "Nudge Couldn't Be Sent"
            message = "Your nudge couldn't be sent right now. We'll try again shortly, or you can manually check your tasks."
            next_steps = [
                "Check your notification settings",
                "Review your tasks manually for now", 
                "We'll retry sending nudges automatically"
            ]
        elif exc.feature.lower() == "focus":
            title = "Focus Session Hiccup"
            message = "Something interrupted your focus session. No worries - your progress is saved!"
            next_steps = [
                "Start a new focus session when ready",
                "Your completed work is safely stored",
                "Take a quick break if you need to"
            ]
        else:
            title = f"{exc.feature} Issue"
            message = f"We're having a small issue with {exc.feature}. Your core features still work normally!"
            next_steps = [
                "Try the action again",
                "Core functionality remains available",
                "This feature will restore automatically"
            ]
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "title": title,
                    "message": message,
                    "next_steps": next_steps,
                    "category": "adhd_feature",
                    "severity": "low" if exc.recoverable else "medium",
                    "user_impact": "Specific feature temporarily affected",
                    "support_message": "These specialized features have extra complexity - totally normal!",
                    "recovery_suggestions": [
                        "Use core features while this resolves",
                        "Check back in a few minutes"
                    ] if exc.recoverable else ["Contact support for assistance"]
                }
            },
            headers={
                "X-Error-Category": "adhd_feature",
                "X-ADHD-Optimized": "true",
                "Cache-Control": "no-cache"
            }
        )
    
    except Exception as e:
        logger.error("Error in ADHD feature exception handler", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "title": f"{exc.feature} Issue",
                    "message": f"We're having a small issue with {exc.feature}, but everything else works fine!",
                    "support_message": "Specialized features sometimes need extra care!"
                }
            }
        )


async def cognitive_overload_exception_handler(request: Request, exc: CognitiveOverloadException) -> JSONResponse:
    """Handle cognitive overload with protective, caring messaging."""
    try:
        # Record cognitive overload event
        health_monitor.record_error("cognitive_overload", f"Load: {exc.current_load}, Threshold: {exc.threshold}")
        
        return JSONResponse(
            status_code=429,  # Too Many Requests - appropriate for overload protection
            content={
                "error": {
                    "title": "Taking a Protective Break",
                    "message": "Our system detected you might be getting overwhelmed. Let's take a moment to breathe and reset.",
                    "next_steps": [
                        "Take 10-15 minutes for yourself",
                        "Try some deep breathing or a short walk",
                        "Grab some water or a healthy snack",
                        "The system will be ready when you return"
                    ],
                    "explanation": "This feature is designed to prevent cognitive overload and protect your wellbeing",
                    "category": "cognitive_overload",
                    "severity": "high",
                    "user_impact": "Temporary reduced functionality to protect your mental resources",
                    "support_message": "Self-care isn't selfish - it's necessary! You're doing great.",
                    "estimated_fix_time": "System will restore after your break",
                    "recovery_suggestions": [
                        "Practice mindfulness for a few minutes",
                        "Step away from the screen briefly",
                        "Return when you feel refreshed"
                    ]
                }
            },
            headers={
                "X-Error-Category": "cognitive_overload",
                "X-ADHD-Optimized": "true",
                "X-Protection-Active": "true",
                "Retry-After": "900",  # 15 minutes
                "Cache-Control": "no-cache"
            }
        )
    
    except Exception as e:
        logger.error("Error in cognitive overload exception handler", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "title": "Time for a Break",
                    "message": "The system thinks you might need a quick breather. Self-care is important!",
                    "support_message": "Taking breaks is a sign of wisdom, not weakness!"
                }
            }
        )


async def circuit_breaker_exception_handler(request: Request, exc: CircuitBreakerOpenException) -> JSONResponse:
    """Handle circuit breaker with understanding and patience."""
    try:
        # Record circuit breaker event
        health_monitor.record_error("circuit_breaker_open", f"Recovery: {exc.recovery_time}")
        
        return JSONResponse(
            status_code=503,  # Service Unavailable
            content={
                "error": {
                    "title": "System Protection Active",
                    "message": "Our protective systems are giving both you and the server a chance to reset. This is designed to help, not hinder!",
                    "next_steps": [
                        f"System will recover automatically in {exc.recovery_time}",
                        "Use this time for self-care or other activities",
                        "Your progress and data are completely safe",
                        "No action needed from you"
                    ],
                    "explanation": "Circuit breakers prevent system overload and user overwhelm",
                    "category": "circuit_breaker", 
                    "severity": "high",
                    "user_impact": "Temporary service pause for protective recovery",
                    "support_message": "Rest and recovery are productive activities too!",
                    "estimated_fix_time": exc.recovery_time,
                    "recovery_suggestions": [
                        "Take this as a sign to pause and recharge",
                        "Do something enjoyable during the wait",
                        "Remember: this is protection, not punishment"
                    ]
                }
            },
            headers={
                "X-Error-Category": "circuit_breaker",
                "X-ADHD-Optimized": "true",
                "X-Circuit-Breaker": "open",
                "Retry-After": "7200",  # 2 hours default
                "Cache-Control": "no-cache"
            }
        )
    
    except Exception as e:
        logger.error("Error in circuit breaker exception handler", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "title": "Protection Mode Active",
                    "message": "The system is taking a protective break. Use this time for self-care!",
                    "support_message": "Breaks are necessary and healthy!"
                }
            }
        )


def register_exception_handlers(app):
    """
    Register all ADHD-friendly exception handlers with the FastAPI app.
    
    Call this function during app initialization to set up comprehensive
    error handling throughout the application.
    """
    
    # Core FastAPI/HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Database exceptions
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    
    # Redis/Cache exceptions
    app.add_exception_handler(RedisError, redis_exception_handler)
    
    # Async/Timeout exceptions
    app.add_exception_handler(asyncio.TimeoutError, timeout_exception_handler)
    
    # ADHD-specific exceptions
    app.add_exception_handler(ADHDFeatureException, adhd_feature_exception_handler)
    app.add_exception_handler(CognitiveOverloadException, cognitive_overload_exception_handler)
    app.add_exception_handler(CircuitBreakerOpenException, circuit_breaker_exception_handler)
    
    # Catch-all exception handler (must be last)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("ADHD-friendly exception handlers registered successfully")