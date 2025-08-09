"""
ADHD-Friendly Error Handling System for MCP ADHD Server.

This module transforms technical error messages into supportive, actionable,
ADHD-friendly communications that help rather than overwhelm users.

Key Principles:
1. Clarity Over Technical Detail - Simple, plain language explanations
2. Supportive Tone - Encouraging, non-blaming language  
3. Actionable Guidance - Clear next steps the user can take
4. Cognitive Load Reduction - Break complex problems into simple steps
"""

import re
import logging
import structlog
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

logger = structlog.get_logger(__name__)


class ErrorCategory(str, Enum):
    """Categories of errors for ADHD-optimized handling."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization" 
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    ADHD_FEATURE = "adhd_feature"
    COGNITIVE_OVERLOAD = "cognitive_overload"
    CIRCUIT_BREAKER = "circuit_breaker"
    SAFETY = "safety"


class ErrorSeverity(str, Enum):
    """Severity levels for error prioritization."""
    LOW = "low"          # Minor issues, user can continue
    MEDIUM = "medium"    # Moderate issues, some features affected
    HIGH = "high"        # Major issues, significant disruption
    CRITICAL = "critical"  # Critical issues, immediate attention needed


@dataclass
class ErrorContext:
    """Context information for error message generation."""
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    user_agent: Optional[str] = None
    session_duration: Optional[float] = None
    recent_errors: List[str] = None
    is_repeat_error: bool = False
    cognitive_load: float = 0.0
    user_preferences: Dict[str, Any] = None

    def __post_init__(self):
        if self.recent_errors is None:
            self.recent_errors = []
        if self.user_preferences is None:
            self.user_preferences = {}


@dataclass
class ADHDFriendlyError:
    """ADHD-optimized error response structure."""
    title: str                    # Short, clear title
    message: str                 # Main supportive message
    next_steps: List[str]        # Actionable steps user can take
    explanation: Optional[str]    # Optional simple explanation
    help_resources: List[str]    # Helpful links or resources
    recovery_suggestions: List[str]  # Alternative approaches
    severity: ErrorSeverity
    category: ErrorCategory
    technical_details: Optional[str]  # Hidden by default, available for debugging
    estimated_fix_time: Optional[str]  # When issue might be resolved
    user_impact: str             # How this affects the user
    support_message: str         # Encouraging note
    timestamp: datetime
    request_id: Optional[str] = None

    def to_response(self, include_technical: bool = False) -> Dict[str, Any]:
        """Convert to API response format."""
        response = {
            "error": {
                "title": self.title,
                "message": self.message,
                "next_steps": self.next_steps,
                "severity": self.severity.value,
                "category": self.category.value,
                "user_impact": self.user_impact,
                "support_message": self.support_message,
                "timestamp": self.timestamp.isoformat()
            }
        }
        
        # Add optional fields if present
        if self.explanation:
            response["error"]["explanation"] = self.explanation
        
        if self.help_resources:
            response["error"]["help_resources"] = self.help_resources
        
        if self.recovery_suggestions:
            response["error"]["recovery_suggestions"] = self.recovery_suggestions
        
        if self.estimated_fix_time:
            response["error"]["estimated_fix_time"] = self.estimated_fix_time
            
        if self.request_id:
            response["error"]["request_id"] = self.request_id
        
        # Include technical details only if explicitly requested
        if include_technical and self.technical_details:
            response["error"]["technical_details"] = self.technical_details
        
        return response


class ADHDErrorTransformer:
    """Transforms technical errors into ADHD-friendly messages."""
    
    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.encouragement_phrases = [
            "You've got this!",
            "No worries, this happens to everyone.",
            "Let's get this sorted out together.",
            "This is totally fixable.",
            "Don't stress - we'll figure this out.",
            "You're doing great, just a small hiccup.",
            "Every expert was once a beginner.",
            "Progress, not perfection!"
        ]
    
    def _initialize_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize error pattern matching and transformations."""
        return {
            # Authentication Errors
            "invalid_credentials": {
                "patterns": [
                    r"invalid.credentials",
                    r"authentication.failed",
                    r"login.failed",
                    r"incorrect.password",
                    r"user.not.found"
                ],
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Sign-In Help Needed",
                "message": "Let's get you signed in! Double-check your email and password, or try resetting your password if you're not sure.",
                "next_steps": [
                    "Check that your email is spelled correctly",
                    "Try entering your password again carefully", 
                    "Use the 'Forgot Password' link if needed",
                    "Clear your browser cache and try again"
                ],
                "recovery_suggestions": [
                    "Reset your password using the link below",
                    "Contact support if you're still having trouble"
                ]
            },
            
            "session_expired": {
                "patterns": [
                    r"session.expired",
                    r"token.expired",
                    r"authentication.timeout"
                ],
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.LOW,
                "title": "Session Timeout",
                "message": "Your session timed out for security - totally normal! Just sign in again to continue where you left off.",
                "next_steps": [
                    "Click the sign-in button",
                    "Enter your credentials",
                    "You'll be back to your work in no time"
                ],
                "user_impact": "Your progress is saved, just need to sign in again"
            },
            
            "invalid_api_key": {
                "patterns": [
                    r"invalid.api.key",
                    r"api.key.not.found",
                    r"unauthorized.api.access"
                ],
                "category": ErrorCategory.AUTHORIZATION,
                "severity": ErrorSeverity.MEDIUM,
                "title": "API Key Issue",
                "message": "Your API key isn't being recognized. Let's get that sorted out quickly.",
                "next_steps": [
                    "Double-check your API key for any typos",
                    "Make sure you're using the full key",
                    "Try generating a new key in your account settings",
                    "Check that your key hasn't expired"
                ]
            },
            
            # Validation Errors
            "missing_required_field": {
                "patterns": [
                    r"field.required",
                    r"missing.required.field",
                    r"required.field.missing"
                ],
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.LOW,
                "title": "Missing Information",
                "message": "Looks like we need a bit more info to complete that request.",
                "next_steps": [
                    "Check for any empty required fields",
                    "Fill in the highlighted fields",
                    "Try submitting again"
                ],
                "explanation": "Some fields are required for the system to work properly"
            },
            
            "invalid_format": {
                "patterns": [
                    r"invalid.format",
                    r"format.error",
                    r"validation.error",
                    r"invalid.email",
                    r"invalid.phone"
                ],
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.LOW,
                "title": "Format Check Needed",
                "message": "The format looks a bit different than expected. Here's what we're looking for:",
                "next_steps": [
                    "Check the example format provided",
                    "Remove any extra spaces or special characters",
                    "Make sure dates are in MM/DD/YYYY format",
                    "Email addresses need an @ symbol"
                ]
            },
            
            # Rate Limiting
            "rate_limit_exceeded": {
                "patterns": [
                    r"rate.limit.exceeded",
                    r"too.many.requests",
                    r"request.limit.reached"
                ],
                "category": ErrorCategory.RATE_LIMIT,
                "severity": ErrorSeverity.LOW,
                "title": "Taking a Breather",
                "message": "You're working fast! Please wait a moment before trying again to give our servers a breather.",
                "next_steps": [
                    "Wait about 60 seconds",
                    "Try your request again", 
                    "Take a quick break - you've been productive!"
                ],
                "explanation": "This helps keep the system running smoothly for everyone"
            },
            
            # System Errors
            "database_connection": {
                "patterns": [
                    r"database.connection.failed",
                    r"database.error",
                    r"connection.timeout",
                    r"database.unavailable"
                ],
                "category": ErrorCategory.DATABASE,
                "severity": ErrorSeverity.HIGH,
                "title": "Connection Hiccup",
                "message": "We're having trouble connecting to our database right now. This should resolve shortly.",
                "next_steps": [
                    "Wait about 2-3 minutes",
                    "Refresh the page",
                    "Try your action again"
                ],
                "user_impact": "Your data is safe - just a temporary connection issue",
                "estimated_fix_time": "Usually resolves in 2-5 minutes"
            },
            
            "external_api_failure": {
                "patterns": [
                    r"external.service.unavailable",
                    r"api.timeout",
                    r"service.down",
                    r"upstream.error"
                ],
                "category": ErrorCategory.EXTERNAL_API,
                "severity": ErrorSeverity.MEDIUM,
                "title": "External Service Break",
                "message": "One of our connected services is taking a break. Your data is safe, and we'll retry automatically.",
                "next_steps": [
                    "No action needed - we'll keep trying",
                    "Check back in a few minutes",
                    "Your information is safely stored"
                ],
                "estimated_fix_time": "Usually back within 10-15 minutes"
            },
            
            "request_timeout": {
                "patterns": [
                    r"request.timeout",
                    r"operation.timeout",
                    r"processing.timeout"
                ],
                "category": ErrorCategory.TIMEOUT,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Taking Longer Than Expected",
                "message": "This is taking longer than usual. Let's try that again, or contact support if it keeps happening.",
                "next_steps": [
                    "Try the action again",
                    "Check your internet connection",
                    "Refresh the page if needed",
                    "Contact support if this continues"
                ]
            },
            
            # ADHD-Specific Features
            "nudge_failure": {
                "patterns": [
                    r"nudge.failed",
                    r"notification.error",
                    r"reminder.failed"
                ],
                "category": ErrorCategory.ADHD_FEATURE,
                "severity": ErrorSeverity.LOW,
                "title": "Nudge Couldn't Be Sent",
                "message": "Your nudge couldn't be sent right now. We'll try again shortly, or you can manually check your tasks.",
                "next_steps": [
                    "Check your notification settings",
                    "Review your tasks manually for now",
                    "We'll retry sending nudges automatically"
                ],
                "recovery_suggestions": [
                    "Visit your task list directly",
                    "Set a phone reminder as backup"
                ]
            },
            
            "focus_session_error": {
                "patterns": [
                    r"focus.session.interrupted",
                    r"session.error",
                    r"focus.timer.failed"
                ],
                "category": ErrorCategory.ADHD_FEATURE,
                "severity": ErrorSeverity.LOW,
                "title": "Focus Session Hiccup",
                "message": "Something interrupted your focus session. No worries - your progress is saved!",
                "next_steps": [
                    "Start a new focus session when ready",
                    "Your completed work is safely stored",
                    "Take a quick break if you need to"
                ],
                "user_impact": "Your progress from this session is preserved"
            },
            
            "context_building_error": {
                "patterns": [
                    r"context.error",
                    r"frame.building.failed",
                    r"context.unavailable"
                ],
                "category": ErrorCategory.ADHD_FEATURE,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Context Loading Issue",
                "message": "We're having trouble gathering your full context right now. Working with basic info for now.",
                "next_steps": [
                    "Your core features still work normally",
                    "Context will restore automatically soon",
                    "Try refreshing if you notice issues"
                ],
                "user_impact": "Some personalization temporarily unavailable"
            },
            
            # Circuit Breaker / Cognitive Overload
            "circuit_breaker_open": {
                "patterns": [
                    r"circuit.breaker.open",
                    r"service.temporarily.unavailable",
                    r"cognitive.overload.detected"
                ],
                "category": ErrorCategory.CIRCUIT_BREAKER,
                "severity": ErrorSeverity.HIGH,
                "title": "Taking a Protective Break",
                "message": "Our system is taking a protective break to prevent overwhelming you. This is designed to help, not hinder!",
                "next_steps": [
                    "Take 15-30 minutes for self-care",
                    "Try some deep breathing or a short walk",
                    "System will restore automatically",
                    "Your progress is completely safe"
                ],
                "explanation": "This feature protects against cognitive overload",
                "estimated_fix_time": "2-4 hours for full recovery",
                "user_impact": "Temporary reduced functionality to protect your wellbeing"
            },
            
            # Generic fallbacks
            "generic_400": {
                "patterns": [r"bad.request", r"invalid.request"],
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Request Format Issue",
                "message": "Something about the request format isn't quite right. Let's fix that together.",
                "next_steps": [
                    "Double-check your input for any errors",
                    "Make sure all required fields are filled",
                    "Try refreshing and submitting again"
                ]
            },
            
            "generic_500": {
                "patterns": [r"internal.server.error", r"server.error"],
                "category": ErrorCategory.SYSTEM,
                "severity": ErrorSeverity.HIGH,
                "title": "System Hiccup",
                "message": "We hit a small bump on our end. This isn't your fault - we're looking into it!",
                "next_steps": [
                    "Try refreshing the page",
                    "Wait a minute and try again",
                    "Contact support if this continues"
                ],
                "user_impact": "Temporary issue, your data is safe"
            }
        }
    
    def transform_error(
        self, 
        error: Union[Exception, HTTPException, str], 
        context: Optional[ErrorContext] = None,
        status_code: Optional[int] = None
    ) -> ADHDFriendlyError:
        """
        Transform any error into an ADHD-friendly response.
        
        Args:
            error: The original error (Exception, HTTPException, or error string)
            context: Additional context for personalization
            status_code: HTTP status code if available
            
        Returns:
            ADHDFriendlyError with user-friendly messaging
        """
        if context is None:
            context = ErrorContext()
        
        # Extract error information
        error_text, original_status = self._extract_error_info(error, status_code)
        
        # Find matching pattern
        pattern_match = self._find_matching_pattern(error_text)
        
        if pattern_match:
            error_config = self.error_patterns[pattern_match]
        else:
            # Use generic fallback based on status code
            error_config = self._get_generic_fallback(original_status)
        
        # Create ADHD-friendly error
        friendly_error = self._build_friendly_error(
            error_config, 
            error_text, 
            context, 
            original_status
        )
        
        # Add personalization based on context
        self._personalize_error(friendly_error, context)
        
        # Log the error for monitoring
        self._log_error(friendly_error, error_text, context)
        
        return friendly_error
    
    def _extract_error_info(self, error: Union[Exception, HTTPException, str], status_code: Optional[int]) -> Tuple[str, int]:
        """Extract error text and status code from various error types."""
        if isinstance(error, HTTPException):
            return str(error.detail).lower(), error.status_code
        elif isinstance(error, ValidationError):
            return str(error).lower(), 422
        elif isinstance(error, Exception):
            return str(error).lower(), status_code or 500
        else:
            return str(error).lower(), status_code or 500
    
    def _find_matching_pattern(self, error_text: str) -> Optional[str]:
        """Find the best matching error pattern."""
        for pattern_name, config in self.error_patterns.items():
            for pattern in config.get("patterns", []):
                if re.search(pattern, error_text, re.IGNORECASE):
                    return pattern_name
        return None
    
    def _get_generic_fallback(self, status_code: int) -> Dict[str, Any]:
        """Get generic fallback error configuration based on status code."""
        if status_code == 400:
            return self.error_patterns["generic_400"]
        elif status_code == 401:
            return self.error_patterns.get("invalid_credentials", self.error_patterns["generic_400"])
        elif status_code == 403:
            return {
                "category": ErrorCategory.AUTHORIZATION,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Access Not Permitted",
                "message": "You don't have permission for this action right now.",
                "next_steps": [
                    "Check if you're signed in to the right account",
                    "Contact your administrator if needed",
                    "Try signing out and back in"
                ]
            }
        elif status_code == 404:
            return {
                "category": ErrorCategory.NOT_FOUND,
                "severity": ErrorSeverity.LOW,
                "title": "Page Not Found",
                "message": "The page or resource you're looking for isn't available right now.",
                "next_steps": [
                    "Check the URL for any typos",
                    "Try going back and clicking the link again",
                    "Use the search function to find what you need"
                ]
            }
        elif status_code == 429:
            return self.error_patterns["rate_limit_exceeded"]
        else:
            return self.error_patterns["generic_500"]
    
    def _build_friendly_error(
        self, 
        config: Dict[str, Any], 
        original_error: str, 
        context: ErrorContext, 
        status_code: int
    ) -> ADHDFriendlyError:
        """Build the ADHD-friendly error from configuration."""
        
        # Select random encouragement phrase
        import random
        support_message = random.choice(self.encouragement_phrases)
        
        # Build the error object
        friendly_error = ADHDFriendlyError(
            title=config.get("title", "Something Went Wrong"),
            message=config.get("message", "We're working on fixing this."),
            next_steps=config.get("next_steps", ["Try refreshing the page", "Contact support if this continues"]),
            explanation=config.get("explanation"),
            help_resources=config.get("help_resources", []),
            recovery_suggestions=config.get("recovery_suggestions", []),
            severity=config.get("severity", ErrorSeverity.MEDIUM),
            category=config.get("category", ErrorCategory.SYSTEM),
            technical_details=original_error,
            estimated_fix_time=config.get("estimated_fix_time"),
            user_impact=config.get("user_impact", "Temporary issue affecting this feature"),
            support_message=support_message,
            timestamp=datetime.utcnow(),
            request_id=getattr(context, 'request_id', None)
        )
        
        return friendly_error
    
    def _personalize_error(self, error: ADHDFriendlyError, context: ErrorContext):
        """Add personalization based on user context."""
        
        # Adjust messaging based on cognitive load
        if context.cognitive_load > 0.7:  # High cognitive load
            # Simplify the message and reduce options
            error.next_steps = error.next_steps[:2]  # Limit to 2 steps
            error.message = f"Let's keep this simple: {error.message.split('.')[0]}."
            error.support_message = "Take your time - no pressure!"
        
        # Adjust for repeat errors
        if context.is_repeat_error:
            error.support_message = "This seems to be happening repeatedly. That's frustrating, but we'll get through it!"
            error.next_steps.append("Contact support - they can help resolve recurring issues")
            error.recovery_suggestions.append("Try a different browser or device")
        
        # Add session-specific guidance
        if context.session_duration and context.session_duration > 3600:  # Long session
            error.next_steps.append("Consider taking a short break - you've been working hard!")
        
        # Adjust based on user preferences
        if context.user_preferences:
            if context.user_preferences.get("verbose_errors", False):
                # User wants more detail
                if not error.explanation:
                    error.explanation = "This type of error usually happens when the system is under load or updating."
            else:
                # User prefers minimal information
                error.next_steps = error.next_steps[:3]  # Limit to 3 steps
    
    def _log_error(self, friendly_error: ADHDFriendlyError, original_error: str, context: ErrorContext):
        """Log the error for monitoring and improvement."""
        logger.info(
            "ADHD-friendly error generated",
            category=friendly_error.category.value,
            severity=friendly_error.severity.value,
            user_id=context.user_id,
            endpoint=context.endpoint,
            original_error=original_error[:200],  # Truncate for logs
            cognitive_load=context.cognitive_load,
            is_repeat_error=context.is_repeat_error
        )


# Global transformer instance
error_transformer = ADHDErrorTransformer()


def create_adhd_error_response(
    error: Union[Exception, HTTPException, str],
    status_code: int,
    request: Optional[Request] = None,
    include_technical: bool = False
) -> JSONResponse:
    """
    Create an ADHD-friendly error response.
    
    This is the main function used throughout the application to generate
    user-friendly error responses.
    
    Args:
        error: The original error
        status_code: HTTP status code
        request: FastAPI request object for context
        include_technical: Whether to include technical details
        
    Returns:
        JSONResponse with ADHD-friendly error message
    """
    
    # Build context from request
    context = ErrorContext()
    if request:
        context.endpoint = request.url.path
        context.user_agent = request.headers.get("user-agent")
        context.user_id = request.headers.get("X-User-ID")
        context.cognitive_load = float(request.headers.get("X-Cognitive-Load", "0.0"))
        
        # Generate request ID for tracking
        import uuid
        context.request_id = str(uuid.uuid4())[:8]
    
    # Transform the error
    friendly_error = error_transformer.transform_error(error, context, status_code)
    
    # Create response
    response_data = friendly_error.to_response(include_technical)
    
    # Add ADHD-optimized headers
    headers = {
        "X-Error-Category": friendly_error.category.value,
        "X-Error-Severity": friendly_error.severity.value,
        "X-ADHD-Optimized": "true",
        "X-Support-Available": "true",
        "Cache-Control": "no-cache, no-store, must-revalidate"
    }
    
    if context.request_id:
        headers["X-Request-ID"] = context.request_id
    
    return JSONResponse(
        status_code=status_code,
        content=response_data,
        headers=headers
    )


# Convenience functions for common error types
def authentication_error(message: str = "Authentication required") -> JSONResponse:
    """Create ADHD-friendly authentication error."""
    return create_adhd_error_response(
        HTTPException(status_code=401, detail=message),
        401
    )


def validation_error(message: str = "Validation failed") -> JSONResponse:
    """Create ADHD-friendly validation error."""
    return create_adhd_error_response(
        HTTPException(status_code=400, detail=message),
        400
    )


def rate_limit_error(retry_after: int = 60) -> JSONResponse:
    """Create ADHD-friendly rate limit error."""
    response = create_adhd_error_response(
        HTTPException(status_code=429, detail="Rate limit exceeded"),
        429
    )
    response.headers["Retry-After"] = str(retry_after)
    return response


def system_error(message: str = "System error") -> JSONResponse:
    """Create ADHD-friendly system error."""
    return create_adhd_error_response(
        HTTPException(status_code=500, detail=message),
        500
    )


def not_found_error(resource: str = "Resource") -> JSONResponse:
    """Create ADHD-friendly not found error."""
    return create_adhd_error_response(
        HTTPException(status_code=404, detail=f"{resource} not found"),
        404
    )


def adhd_feature_error(feature: str, message: str) -> JSONResponse:
    """Create ADHD-friendly feature-specific error."""
    error_message = f"{feature} error: {message}"
    return create_adhd_error_response(
        HTTPException(status_code=500, detail=error_message),
        500
    )