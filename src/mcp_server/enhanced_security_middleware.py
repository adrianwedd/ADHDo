"""
Enhanced Security Middleware for MCP ADHD Server - OWASP Level 2 Compliant.

Comprehensive security hardening implementation providing:
- OWASP Top 10 protections
- Enhanced Content Security Policy with nonces
- Advanced input validation and sanitization  
- Double-submit CSRF protection
- Security headers optimization
- Crisis support access bypasses (ADHD-specific)
- Real-time security monitoring and alerting
"""

import time
import secrets
import hashlib
import hmac
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Any, List
from urllib.parse import quote_plus
import json

import structlog
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server.config import settings
from mcp_server.database import get_db_session
from mcp_server.enhanced_auth import enhanced_auth_manager
from mcp_server.db_models import SecurityEvent
from mcp_server.input_validation import input_validator, ValidationError

logger = structlog.get_logger(__name__)


class EnhancedSecurityMiddleware(BaseHTTPMiddleware):
    """
    OWASP-compliant security middleware with ADHD-specific considerations.
    
    Features:
    - Comprehensive security headers (CSP Level 2, HSTS, etc.)
    - Advanced input validation and sanitization
    - Real-time threat detection and monitoring
    - Crisis support access bypasses
    - Performance-optimized for ADHD response times
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.crisis_patterns = [
            re.compile(r'\b(?:suicide|kill\s+myself|end\s+it\s+all|want\s+to\s+die)\b', re.IGNORECASE),
            re.compile(r'\b(?:self[\s-]?harm|hurt\s+myself|cutting|burning)\b', re.IGNORECASE),
            re.compile(r'\b(?:crisis|emergency|help\s+me\s+please)\b', re.IGNORECASE),
            re.compile(r'\b(?:can\'?t\s+go\s+on|give\s+up|no\s+hope)\b', re.IGNORECASE),
            re.compile(r'\b(?:overdose|pills|hanging|jumping)\b', re.IGNORECASE)
        ]
        
        # Security monitoring cache
        self._security_events = []
        self._rate_limit_cache: Dict[str, Dict[str, Any]] = {}
        self._failed_requests: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()
        
        # CSP nonce cache
        self._csp_nonces: Dict[str, str] = {}
    
    async def dispatch(self, request: Request, call_next):
        """Enhanced security processing pipeline."""
        start_time = time.time()
        request_id = self._generate_request_id()
        
        try:
            # Step 1: Enhanced input validation
            validation_response = await self._validate_request_input(request, request_id)
            if validation_response:
                await self._log_security_event(
                    "input_validation_failure", "high", request,
                    {"validation_error": "Input validation failed", "request_id": request_id}
                )
                return validation_response
            
            # Step 2: Crisis detection (highest priority for ADHD users)
            if await self._check_crisis_bypass(request):
                logger.info("Crisis support bypass activated", 
                          path=request.url.path, request_id=request_id)
                response = await call_next(request)
                return await self._finalize_response(request, response, start_time, request_id)
            
            # Step 3: Advanced rate limiting with threat detection
            if not await self._check_enhanced_rate_limit(request, request_id):
                await self._log_security_event(
                    "rate_limit_exceeded", "medium", request,
                    {"request_id": request_id, "threat_level": "moderate"}
                )
                return await self._create_rate_limit_response()
            
            # Step 4: Security headers injection
            await self._inject_security_context(request, request_id)
            
            # Step 5: Process request
            response = await call_next(request)
            
            # Step 6: Enhanced response processing
            return await self._finalize_response(request, response, start_time, request_id)
            
        except Exception as e:
            logger.error("Enhanced security middleware error", 
                       error=str(e), request_id=request_id)
            
            await self._log_security_event(
                "security_middleware_error", "high", request,
                {"error": str(e), "request_id": request_id}
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Security processing error. Please try again.",
                    "request_id": request_id
                }
            )
    
    async def _validate_request_input(self, request: Request, request_id: str) -> Optional[JSONResponse]:
        """Comprehensive input validation with security threat detection."""
        try:
            # Skip validation for safe endpoints
            safe_paths = ['/health', '/metrics', '/docs', '/openapi.json', '/favicon.ico']
            if any(path in str(request.url.path) for path in safe_paths):
                return None
            
            # Validate URL path for path traversal and injection
            path = str(request.url.path)
            try:
                validated_path = input_validator.validate_and_sanitize(
                    path, "url_path", crisis_detection=False
                )
                
                # Additional path security checks
                if self._detect_path_traversal_advanced(path):
                    raise ValidationError("Advanced path traversal detected", "url_path", path)
                
            except ValidationError as e:
                logger.security(
                    "Malicious URL path detected",
                    path=path,
                    client=request.client.host if request.client else 'unknown',
                    error=str(e),
                    request_id=request_id
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": "Invalid request format",
                        "code": "PATH_VALIDATION_FAILED"
                    }
                )
            
            # Validate query parameters with enhanced checks
            for param, value in request.query_params.items():
                try:
                    # Check for SQL injection in query params
                    if self._detect_sql_injection_advanced(value):
                        raise ValidationError("SQL injection attempt", f"query_{param}", value)
                    
                    # Check for XSS in query params
                    if self._detect_xss_advanced(value):
                        raise ValidationError("XSS attempt", f"query_{param}", value)
                    
                    # Standard validation
                    input_validator.validate_and_sanitize(
                        value, f"query_param_{param}", crisis_detection=False
                    )
                    
                except ValidationError as e:
                    logger.security(
                        "Malicious query parameter detected",
                        param=param,
                        value=value[:100],
                        client=request.client.host if request.client else 'unknown',
                        error=str(e),
                        request_id=request_id
                    )
                    return JSONResponse(
                        status_code=400,
                        content={
                            "success": False,
                            "message": "Invalid request parameters",
                            "code": "QUERY_VALIDATION_FAILED"
                        }
                    )
            
            # Validate critical headers
            await self._validate_request_headers(request, request_id)
            
            # Validate request body if present
            if request.method in ['POST', 'PUT', 'PATCH']:
                body_validation = await self._validate_request_body(request, request_id)
                if body_validation:
                    return body_validation
            
            return None  # Validation passed
            
        except Exception as e:
            logger.error("Input validation error", error=str(e), request_id=request_id)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Security validation error",
                    "code": "VALIDATION_ERROR"
                }
            )
    
    async def _validate_request_headers(self, request: Request, request_id: str):
        """Enhanced header validation with threat detection."""
        dangerous_headers = {
            'User-Agent': 2000,  # Max length
            'Referer': 1000,
            'X-Forwarded-For': 500,
            'X-Real-IP': 45,
            'Cookie': 4096
        }
        
        for header_name, max_length in dangerous_headers.items():
            header_value = request.headers.get(header_name, '')
            if header_value:
                # Length check
                if len(header_value) > max_length:
                    logger.security(
                        "Oversized header detected",
                        header=header_name,
                        length=len(header_value),
                        max_length=max_length,
                        request_id=request_id
                    )
                
                # Injection check
                try:
                    input_validator.validate_and_sanitize(
                        header_value, f"header_{header_name}", crisis_detection=False
                    )
                except ValidationError as e:
                    logger.security(
                        "Malicious request header detected",
                        header=header_name,
                        value=header_value[:100],
                        error=str(e),
                        request_id=request_id
                    )
    
    async def _validate_request_body(self, request: Request, request_id: str) -> Optional[JSONResponse]:
        """Validate request body with size limits and content scanning."""
        try:
            # Check Content-Length header
            content_length = request.headers.get('content-length')
            if content_length:
                length = int(content_length)
                if length > 10 * 1024 * 1024:  # 10MB limit
                    logger.security(
                        "Oversized request body",
                        content_length=length,
                        request_id=request_id
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "success": False,
                            "message": "Request body too large",
                            "code": "PAYLOAD_TOO_LARGE"
                        }
                    )
            
            # Validate JSON payloads
            content_type = request.headers.get('content-type', '')
            if 'application/json' in content_type:
                try:
                    body = await request.body()
                    if body:
                        # Parse and validate JSON
                        json_data = json.loads(body.decode('utf-8'))
                        validated_data = input_validator.validate_and_sanitize(
                            json_data, "request_body", crisis_detection=True
                        )
                        # Store validated data for use by endpoints
                        request.state.validated_body = validated_data
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.security(
                        "Invalid JSON in request body",
                        error=str(e),
                        request_id=request_id
                    )
                    return JSONResponse(
                        status_code=400,
                        content={
                            "success": False,
                            "message": "Invalid JSON format",
                            "code": "INVALID_JSON"
                        }
                    )
                except ValidationError as e:
                    logger.security(
                        "Malicious content in request body",
                        error=str(e),
                        request_id=request_id
                    )
                    return JSONResponse(
                        status_code=400,
                        content={
                            "success": False,
                            "message": "Invalid request content",
                            "code": "CONTENT_VALIDATION_FAILED"
                        }
                    )
        
        except Exception as e:
            logger.error("Request body validation error", error=str(e), request_id=request_id)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Body validation error",
                    "code": "BODY_VALIDATION_ERROR"
                }
            )
        
        return None
    
    async def _check_crisis_bypass(self, request: Request) -> bool:
        """Enhanced crisis detection with ADHD-specific patterns."""
        if not settings.crisis_bypass_auth:
            return False
        
        # Check for crisis keywords in URL path
        crisis_paths = ['/chat', '/help', '/support', '/crisis', '/emergency']
        if not any(path in str(request.url.path) for path in crisis_paths):
            return False
        
        # Check request body for crisis indicators
        if request.method == "POST":
            try:
                body = await request.body()
                if body:
                    text_content = body.decode('utf-8', errors='ignore').lower()
                    
                    # Check against enhanced crisis patterns
                    for pattern in self.crisis_patterns:
                        if pattern.search(text_content):
                            logger.critical(
                                "Crisis content detected - activating emergency support",
                                path=request.url.path,
                                client=request.client.host if request.client else 'unknown',
                                pattern_matched=True
                            )
                            return True
                    
                    # Check against configured keywords
                    for keyword in settings.crisis_keywords:
                        if keyword.lower() in text_content:
                            return True
            except Exception as e:
                logger.warning("Crisis detection body parsing error", error=str(e))
        
        return False
    
    async def _check_enhanced_rate_limit(self, request: Request, request_id: str) -> bool:
        """Enhanced rate limiting with threat detection."""
        if not request.client:
            return True
        
        # Skip rate limiting for safe paths
        skip_paths = ['/health', '/metrics', '/docs', '/openapi.json', '/favicon.ico']
        if any(skip in str(request.url.path) for skip in skip_paths):
            return True
        
        client_ip = request.client.host
        user_id = request.headers.get('X-User-ID', '')
        identifier = user_id if user_id else f"ip:{client_ip}"
        
        now = time.time()
        
        # Clean up old entries periodically
        if now - self._last_cleanup > 300:  # 5 minutes
            await self._cleanup_security_caches()
            self._last_cleanup = now
        
        # Initialize tracking for new clients
        if identifier not in self._rate_limit_cache:
            self._rate_limit_cache[identifier] = {
                'requests': [],
                'blocked_until': 0,
                'threat_score': 0,
                'failed_attempts': 0
            }
        
        cache_entry = self._rate_limit_cache[identifier]
        
        # Check if currently blocked
        if now < cache_entry['blocked_until']:
            cache_entry['threat_score'] += 1  # Increase threat score for blocked requests
            return False
        
        # Clean old requests from sliding window
        minute_ago = now - 60
        cache_entry['requests'] = [req_time for req_time in cache_entry['requests'] if req_time > minute_ago]
        
        # Dynamic rate limits based on threat score
        base_limit = settings.rate_limit_requests_per_minute
        threat_adjusted_limit = max(5, base_limit - cache_entry['threat_score'])
        
        # Check if limit exceeded
        if len(cache_entry['requests']) >= threat_adjusted_limit:
            # Calculate block duration based on threat level
            block_duration = 60 + (cache_entry['threat_score'] * 30)  # Base 60s + threat multiplier
            cache_entry['blocked_until'] = now + block_duration
            cache_entry['threat_score'] += 2
            
            logger.warning(
                "Enhanced rate limit exceeded",
                identifier=identifier,
                requests_count=len(cache_entry['requests']),
                limit=threat_adjusted_limit,
                threat_score=cache_entry['threat_score'],
                block_duration=block_duration,
                request_id=request_id
            )
            
            return False
        
        # Add current request
        cache_entry['requests'].append(now)
        
        # Decay threat score over time for good behavior
        if cache_entry['threat_score'] > 0 and len(cache_entry['requests']) < threat_adjusted_limit * 0.5:
            cache_entry['threat_score'] = max(0, cache_entry['threat_score'] - 0.1)
        
        return True
    
    async def _inject_security_context(self, request: Request, request_id: str):
        """Inject security context into request."""
        # Generate CSP nonce
        nonce = self._generate_csp_nonce()
        self._csp_nonces[request_id] = nonce
        request.state.csp_nonce = nonce
        request.state.request_id = request_id
        
        # Add security timing for monitoring
        request.state.security_start_time = time.time()
    
    async def _finalize_response(
        self, 
        request: Request, 
        response: StarletteResponse, 
        start_time: float,
        request_id: str
    ) -> StarletteResponse:
        """Enhanced response processing with comprehensive security headers."""
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Get CSP nonce
        nonce = self._csp_nonces.get(request_id, self._generate_csp_nonce())
        
        # Build comprehensive security headers
        security_headers = {
            # Enhanced HTTPS and transport security
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Enhanced Content Security Policy Level 2
            "Content-Security-Policy": self._build_enhanced_csp_header(request, nonce),
            
            # Comprehensive permissions policy
            "Permissions-Policy": self._build_permissions_policy(),
            
            # Cross-origin policies
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin", 
            "Cross-Origin-Resource-Policy": "same-origin",
            
            # Cache control for sensitive responses
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            
            # Server information hiding
            "Server": "MCP-ADHD-Server",
            "X-Powered-By": "",
            
            # Custom security headers
            "X-Response-Time": f"{response_time:.2f}ms",
            "X-Request-ID": request_id,
            "X-Content-Security": "enforced",
            "X-XSS-Protection-Enhanced": "active",
            "X-Security-Level": "owasp-level-2",
            "X-Threat-Detection": "enabled"
        }

        # Apply headers to response
        for header, value in security_headers.items():
            response.headers[header] = value

        # ADHD-friendly performance indicators
        adhd_performance = self._calculate_adhd_performance_level(response_time)
        response.headers["X-ADHD-Performance"] = adhd_performance

        if adhd_performance == "slow":
            logger.warning(
                "Slow response impacting ADHD user experience",
                response_time_ms=response_time,
                path=request.url.path,
                method=request.method,
                request_id=request_id,
                adhd_impact="attention_disruption_risk"
            )

        # Clean up nonce cache
        self._csp_nonces.pop(request_id, None)

        return response

    def _build_enhanced_csp_header(self, request: Request, nonce: str) -> str:
        """Build OWASP Level 2 Content Security Policy."""

        # Enhanced CSP directives
        csp_directives = {
            "default-src": "'self'",
            "script-src": f"'self' 'nonce-{nonce}' 'strict-dynamic'",  # CSP Level 2
            "object-src": "'none'",  # Block all plugins
            "base-uri": "'self'",
            "style-src": "'self' 'unsafe-inline'",  # Needed for ADHD-friendly UI
            "img-src": "'self' data: https: blob:",
            "font-src": "'self' https:",
            "connect-src": "'self' wss: https:",
            "media-src": "'self'",
            "frame-src": "'none'",
            "child-src": "'none'",
            "worker-src": "'self'",
            "manifest-src": "'self'",
            "form-action": "'self'",
            "frame-ancestors": "'none'",
            "require-trusted-types-for": "'script'",  # CSP Level 3 preparation
            "trusted-types": "default",
            "upgrade-insecure-requests": None
        }

        # Stricter CSP for production
        if not settings.debug:
            csp_directives["script-src"] = f"'self' 'nonce-{nonce}'"
            csp_directives["style-src"] = "'self'"

        # Build CSP string
        csp_parts = []
        for directive, value in csp_directives.items():
            if value is None:
                csp_parts.append(directive)
            else:
                csp_parts.append(f"{directive} {value}")

        return "; ".join(csp_parts)

    def _build_permissions_policy(self) -> str:
        """Build comprehensive permissions policy."""
        policies = [
            "microphone=()",
            "camera=()",
            "geolocation=()",
            "gyroscope=()",
            "accelerometer=()",
            "magnetometer=()",
            "usb=()",
            "bluetooth=()",
            "midi=()",
            "payment=()",
            "fullscreen=(self)",
            "picture-in-picture=()",
            "screen-wake-lock=()",
            "web-share=(self)"
        ]
        return ", ".join(policies)

    def _calculate_adhd_performance_level(self, response_time_ms: float) -> str:
        """Calculate ADHD-specific performance impact level."""
        if response_time_ms < 500:  # < 500ms
            return "optimal"
        elif response_time_ms < 1000:  # < 1 second
            return "good"
        elif response_time_ms < 3000:  # < 3 seconds
            return "acceptable"
        else:
            return "slow"

    def _generate_request_id(self) -> str:
        """Generate unique request identifier."""
        return secrets.token_urlsafe(16)

    def _generate_csp_nonce(self) -> str:
        """Generate cryptographically secure CSP nonce."""
        return secrets.token_urlsafe(16)

    def _detect_path_traversal_advanced(self, path: str) -> bool:
        """Advanced path traversal detection."""
        dangerous_patterns = [
            r'\.\./+',
            r'\.\\\\+',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
            r'%252e%252e%252f',
            r'\.\.\\\\',
            r'\x2e\x2e\x2f',
            r'\u002e\u002e\u002f'
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        return False

    def _detect_sql_injection_advanced(self, value: str) -> bool:
        """Advanced SQL injection detection."""
        advanced_patterns = [
            r'(?i)\b(?:union|select|insert|update|delete|drop|create|alter|exec|execute)\b.*\b(?:from|into|where|values)\b',
            r'(?i)\b(?:or|and)\s+[\'"`]?\w+[\'"`]?\s*[=<>!]+\s*[\'"`]?\w*[\'"`]?',
            r'(?i)\b(?:having|group\s+by|order\s+by|limit)\b',
            r'[\'"`];.*(?:select|union|insert|update|delete)',
            r'(?i)\b(?:benchmark|sleep|waitfor|pg_sleep)\s*\(',
            r'(?i)\b(?:load_file|into\s+outfile|into\s+dumpfile)\b'
        ]

        for pattern in advanced_patterns:
            if re.search(pattern, value):
                return True
        return False

    def _detect_xss_advanced(self, value: str) -> bool:
        """Advanced XSS detection."""
        advanced_patterns = [
            r'(?i)<\s*script[^>]*>[^<]*<\s*/\s*script\s*>',
            r'(?i)javascript\s*:',
            r'(?i)on\w+\s*=\s*[\'"][^\'"]',
            r'(?i)<\s*(?:iframe|embed|object|applet|form|input|img)\s+[^>]*(?:src|action|data)\s*=\s*[\'"]?javascript:',
            r'(?i)data\s*:\s*(?:text/html|application/javascript)',
            r'(?i)<\s*style[^>]*>[^<]*expression\s*\(',
            r'(?i)\&\#(?:x)?[0-9a-f]+;?'
        ]

        for pattern in advanced_patterns:
            if re.search(pattern, value):
                return True
        return False

    async def _create_rate_limit_response(self) -> JSONResponse:
        """Create ADHD-friendly rate limit response."""
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "message": "You're making requests too quickly. Take a breath and try again in a moment.",
                "adhd_tip": "Taking breaks is important for focus and well-being.",
                "retry_after": 60,
                "support_message": "If you're feeling overwhelmed, remember that help is available."
            },
            headers={"Retry-After": "60"}
        )

    async def _log_security_event(
        self,
        event_type: str,
        severity: str,
        request: Request,
        metadata: Dict[str, Any]
    ):
        """Log security events for monitoring and alerting."""
        try:
            event_data = {
                "event_type": event_type,
                "severity": severity,
                "timestamp": datetime.utcnow(),
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get('user-agent', ''),
                "path": str(request.url.path),
                "method": request.method,
                "metadata": metadata
            }

            # Store in memory for immediate analysis
            self._security_events.append(event_data)

            # Keep only recent events in memory
            if len(self._security_events) > 1000:
                self._security_events = self._security_events[-1000:]

            # Log to structured logging
            logger.security(
                f"Security event: {event_type}",
                **event_data
            )

            # Store in database for long-term analysis
            async with get_db_session() as db:
                await enhanced_auth_manager._log_security_event(
                    db,
                    event_type=event_type,
                    severity=severity,
                    description=f"Security event: {event_type}",
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get('user-agent', ''),
                    event_metadata=metadata
                )

        except Exception as e:
            logger.error("Failed to log security event", error=str(e))

    async def _cleanup_security_caches(self):
        """Clean up security monitoring caches."""
        now = time.time()
        cutoff = now - 3600  # 1 hour ago

        # Clean rate limit cache
        expired_keys = []
        for identifier, cache_entry in self._rate_limit_cache.items():
            cache_entry['requests'] = [
                req_time for req_time in cache_entry['requests'] if req_time > cutoff
            ]

            if (not cache_entry['requests'] and
                now > cache_entry.get('blocked_until', 0) and
                cache_entry.get('threat_score', 0) < 5):
                expired_keys.append(identifier)

        for key in expired_keys:
            del self._rate_limit_cache[key]

        # Clean security events (keep last hour)
        self._security_events = [
            event for event in self._security_events
            if (now - event['timestamp'].timestamp()) < 3600
        ]

        logger.debug(
            "Security cache cleanup completed",
            rate_limit_entries_removed=len(expired_keys),
            security_events_count=len(self._security_events)
        )

    def get_security_metrics(self) -> Dict[str, Any]:
        """Get current security metrics for monitoring."""
        now = time.time()
        recent_events = [
            event for event in self._security_events
            if (now - event['timestamp'].timestamp()) < 900  # 15 minutes
        ]

        # Count events by type and severity
        event_counts = {}
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        for event in recent_events:
            event_type = event['event_type']
            severity = event['severity']

            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            severity_counts[severity] += 1

        return {
            "monitoring_window_minutes": 15,
            "total_security_events": len(recent_events),
            "events_by_type": event_counts,
            "events_by_severity": severity_counts,
            "active_rate_limits": len(self._rate_limit_cache),
            "threat_level": self._calculate_overall_threat_level(severity_counts),
            "adhd_crisis_bypasses_active": settings.crisis_bypass_auth
        }

    def _calculate_overall_threat_level(self, severity_counts: Dict[str, int]) -> str:
        """Calculate overall threat level based on recent events."""
        if severity_counts["critical"] > 0:
            return "critical"
        elif severity_counts["high"] > 5:
            return "high"
        elif severity_counts["medium"] > 10:
            return "elevated"
        elif severity_counts["low"] > 20:
            return "moderate"
        else:
            return "low"


class EnhancedCSRFMiddleware(BaseHTTPMiddleware):
    """Enhanced CSRF protection with double-submit cookie pattern."""

    def __init__(self, app):
        super().__init__(app)
        self.safe_methods = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}
        self.csrf_secret = settings.master_encryption_key.encode('utf-8')

    async def dispatch(self, request: Request, call_next):
        """Enhanced CSRF protection with double-submit pattern."""

        # Skip CSRF check for safe methods
        if request.method in self.safe_methods:
            return await call_next(request)

        # Skip CSRF check for API key authentication
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            return await call_next(request)

        # Skip CSRF check for specific paths
        skip_paths = ['/auth/login', '/auth/register', '/webhooks/', '/health', '/metrics']
        if any(skip in str(request.url.path) for skip in skip_paths):
            return await call_next(request)

        # Enhanced CSRF token validation
        csrf_header = request.headers.get('X-CSRF-Token')
        csrf_cookie = request.cookies.get('csrf_token')
        session_id = request.cookies.get('session_id')

        # Check for CSRF tokens
        if not csrf_header or not csrf_cookie or not session_id:
            logger.warning(
                "CSRF protection: Missing required tokens",
                path=request.url.path,
                method=request.method,
                client=request.client.host if request.client else 'unknown',
                has_header=bool(csrf_header),
                has_cookie=bool(csrf_cookie),
                has_session=bool(session_id)
            )

            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "message": "CSRF protection active. Please refresh the page and try again.",
                    "code": "CSRF_TOKEN_MISSING"
                }
            )

        # Validate double-submit pattern
        if not self._validate_double_submit_csrf(csrf_header, csrf_cookie, session_id):
            logger.security(
                "CSRF validation failed - potential attack",
                path=request.url.path,
                method=request.method,
                client=request.client.host if request.client else 'unknown',
                session_id=session_id[:8] + "..."
            )

            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "message": "CSRF validation failed. Please refresh the page and try again.",
                    "code": "CSRF_VALIDATION_FAILED"
                }
            )

        # Validate session
        try:
            async with get_db_session() as db:
                session_info = await enhanced_auth_manager.validate_session(db, session_id, request)
                if not session_info:
                    return JSONResponse(
                        status_code=401,
                        content={
                            "success": False,
                            "message": "Invalid session. Please log in again.",
                            "code": "SESSION_INVALID"
                        }
                    )

                # Store session info for downstream use
                request.state.session_info = session_info

        except Exception as e:
            logger.error("CSRF session validation error", error=str(e))
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Security validation error. Please try again.",
                    "code": "CSRF_SESSION_ERROR"
                }
            )

        return await call_next(request)

    def _validate_double_submit_csrf(self, header_token: str, cookie_token: str, session_id: str) -> bool:
        """Validate CSRF tokens using double-submit cookie pattern with HMAC."""
        try:
            # Tokens must match (basic double-submit)
            if header_token != cookie_token:
                return False

            # Validate token structure and signature
            token_parts = header_token.split('.')
            if len(token_parts) != 2:
                return False

            payload, signature = token_parts

            # Verify HMAC signature
            expected_signature = hmac.new(
                self.csrf_secret,
                f"{payload}.{session_id}".encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.warning("CSRF validation error", error=str(e))
            return False

    def generate_csrf_token(self, session_id: str) -> str:
        """Generate cryptographically secure CSRF token."""
        # Create payload with timestamp
        timestamp = str(int(time.time()))
        nonce = secrets.token_urlsafe(16)
        payload = f"{timestamp}.{nonce}"

        # Create HMAC signature
        signature = hmac.new(
            self.csrf_secret,
            f"{payload}.{session_id}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return f"{payload}.{signature}"


# Export enhanced middleware classes
__all__ = [
    'EnhancedSecurityMiddleware',
    'EnhancedCSRFMiddleware'
]