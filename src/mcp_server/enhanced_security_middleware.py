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
            "X-Response-Time": f\"{response_time:.2f}ms\",\n            \"X-Request-ID\": request_id,\n            \"X-Content-Security\": \"enforced\",\n            \"X-XSS-Protection-Enhanced\": \"active\",\n            \"X-Security-Level\": \"owasp-level-2\",\n            \"X-Threat-Detection\": \"enabled\"\n        }\n        \n        # Apply headers to response\n        for header, value in security_headers.items():\n            response.headers[header] = value\n        \n        # ADHD-friendly performance indicators\n        adhd_performance = self._calculate_adhd_performance_level(response_time)\n        response.headers[\"X-ADHD-Performance\"] = adhd_performance\n        \n        if adhd_performance == \"slow\":\n            logger.warning(\n                \"Slow response impacting ADHD user experience\",\n                response_time_ms=response_time,\n                path=request.url.path,\n                method=request.method,\n                request_id=request_id,\n                adhd_impact=\"attention_disruption_risk\"\n            )\n        \n        # Clean up nonce cache\n        self._csp_nonces.pop(request_id, None)\n        \n        return response\n    \n    def _build_enhanced_csp_header(self, request: Request, nonce: str) -> str:\n        \"\"\"Build OWASP Level 2 Content Security Policy.\"\"\"\n        \n        # Enhanced CSP directives\n        csp_directives = {\n            \"default-src\": \"'self'\",\n            \"script-src\": f\"'self' 'nonce-{nonce}' 'strict-dynamic'\",  # CSP Level 2\n            \"object-src\": \"'none'\",  # Block all plugins\n            \"base-uri\": \"'self'\",\n            \"style-src\": \"'self' 'unsafe-inline'\",  # Needed for ADHD-friendly UI\n            \"img-src\": \"'self' data: https: blob:\",\n            \"font-src\": \"'self' https:\",\n            \"connect-src\": \"'self' wss: https:\",\n            \"media-src\": \"'self'\",\n            \"frame-src\": \"'none'\",\n            \"child-src\": \"'none'\",\n            \"worker-src\": \"'self'\",\n            \"manifest-src\": \"'self'\",\n            \"form-action\": \"'self'\",\n            \"frame-ancestors\": \"'none'\",\n            \"require-trusted-types-for\": \"'script'\",  # CSP Level 3 preparation\n            \"trusted-types\": \"default\",\n            \"upgrade-insecure-requests\": None\n        }\n        \n        # Stricter CSP for production\n        if not settings.DEBUG:\n            csp_directives[\"script-src\"] = f\"'self' 'nonce-{nonce}'\"\n            csp_directives[\"style-src\"] = \"'self'\"\n        \n        # Build CSP string\n        csp_parts = []\n        for directive, value in csp_directives.items():\n            if value is None:\n                csp_parts.append(directive)\n            else:\n                csp_parts.append(f\"{directive} {value}\")\n        \n        return \"; \".join(csp_parts)\n    \n    def _build_permissions_policy(self) -> str:\n        \"\"\"Build comprehensive permissions policy.\"\"\"\n        policies = [\n            \"microphone=()\",\n            \"camera=()\", \n            \"geolocation=()\",\n            \"gyroscope=()\",\n            \"accelerometer=()\",\n            \"magnetometer=()\",\n            \"usb=()\",\n            \"bluetooth=()\",\n            \"midi=()\",\n            \"payment=()\",\n            \"fullscreen=(self)\",\n            \"picture-in-picture=()\",\n            \"screen-wake-lock=()\",\n            \"web-share=(self)\"\n        ]\n        return \", \".join(policies)\n    \n    def _calculate_adhd_performance_level(self, response_time_ms: float) -> str:\n        \"\"\"Calculate ADHD-specific performance impact level.\"\"\"\n        if response_time_ms < 500:  # < 500ms\n            return \"optimal\"\n        elif response_time_ms < 1000:  # < 1 second\n            return \"good\" \n        elif response_time_ms < 3000:  # < 3 seconds\n            return \"acceptable\"\n        else:\n            return \"slow\"\n    \n    def _generate_request_id(self) -> str:\n        \"\"\"Generate unique request identifier.\"\"\"\n        return secrets.token_urlsafe(16)\n    \n    def _generate_csp_nonce(self) -> str:\n        \"\"\"Generate cryptographically secure CSP nonce.\"\"\"\n        return secrets.token_urlsafe(16)\n    \n    def _detect_path_traversal_advanced(self, path: str) -> bool:\n        \"\"\"Advanced path traversal detection.\"\"\"\n        dangerous_patterns = [\n            r'\\.\\./+',\n            r'\\.\\\\\\\\+', \n            r'%2e%2e%2f',\n            r'%2e%2e%5c',\n            r'%252e%252e%252f',\n            r'\\.\\.\\\\\\\\',\n            r'\\x2e\\x2e\\x2f',\n            r'\\u002e\\u002e\\u002f'\n        ]\n        \n        for pattern in dangerous_patterns:\n            if re.search(pattern, path, re.IGNORECASE):\n                return True\n        return False\n    \n    def _detect_sql_injection_advanced(self, value: str) -> bool:\n        \"\"\"Advanced SQL injection detection.\"\"\"\n        advanced_patterns = [\n            r'(?i)\\b(?:union|select|insert|update|delete|drop|create|alter|exec|execute)\\b.*\\b(?:from|into|where|values)\\b',\n            r'(?i)\\b(?:or|and)\\s+[\\'\"`]?\\w+[\\'\"`]?\\s*[=<>!]+\\s*[\\'\"`]?\\w*[\\'\"`]?',\n            r'(?i)\\b(?:having|group\\s+by|order\\s+by|limit)\\b',\n            r'[\\'\"`];.*(?:select|union|insert|update|delete)',\n            r'(?i)\\b(?:benchmark|sleep|waitfor|pg_sleep)\\s*\\(',\n            r'(?i)\\b(?:load_file|into\\s+outfile|into\\s+dumpfile)\\b'\n        ]\n        \n        for pattern in advanced_patterns:\n            if re.search(pattern, value):\n                return True\n        return False\n    \n    def _detect_xss_advanced(self, value: str) -> bool:\n        \"\"\"Advanced XSS detection.\"\"\"\n        advanced_patterns = [\n            r'(?i)<\\s*script[^>]*>[^<]*<\\s*/\\s*script\\s*>',\n            r'(?i)javascript\\s*:',\n            r'(?i)on\\w+\\s*=\\s*[\\'\"][^\\'\"]',\n            r'(?i)<\\s*(?:iframe|embed|object|applet|form|input|img)\\s+[^>]*(?:src|action|data)\\s*=\\s*[\\'\"]?javascript:',\n            r'(?i)data\\s*:\\s*(?:text/html|application/javascript)',\n            r'(?i)<\\s*style[^>]*>[^<]*expression\\s*\\(',\n            r'(?i)\\&\\#(?:x)?[0-9a-f]+;?'\n        ]\n        \n        for pattern in advanced_patterns:\n            if re.search(pattern, value):\n                return True\n        return False\n    \n    async def _create_rate_limit_response(self) -> JSONResponse:\n        \"\"\"Create ADHD-friendly rate limit response.\"\"\"\n        return JSONResponse(\n            status_code=429,\n            content={\n                \"success\": False,\n                \"message\": \"You're making requests too quickly. Take a breath and try again in a moment.\",\n                \"adhd_tip\": \"Taking breaks is important for focus and well-being.\",\n                \"retry_after\": 60,\n                \"support_message\": \"If you're feeling overwhelmed, remember that help is available.\"\n            },\n            headers={\"Retry-After\": \"60\"}\n        )\n    \n    async def _log_security_event(\n        self, \n        event_type: str, \n        severity: str, \n        request: Request,\n        metadata: Dict[str, Any]\n    ):\n        \"\"\"Log security events for monitoring and alerting.\"\"\"\n        try:\n            event_data = {\n                \"event_type\": event_type,\n                \"severity\": severity,\n                \"timestamp\": datetime.utcnow(),\n                \"ip_address\": request.client.host if request.client else None,\n                \"user_agent\": request.headers.get('user-agent', ''),\n                \"path\": str(request.url.path),\n                \"method\": request.method,\n                \"metadata\": metadata\n            }\n            \n            # Store in memory for immediate analysis\n            self._security_events.append(event_data)\n            \n            # Keep only recent events in memory\n            if len(self._security_events) > 1000:\n                self._security_events = self._security_events[-1000:]\n            \n            # Log to structured logging\n            logger.security(\n                f\"Security event: {event_type}\",\n                **event_data\n            )\n            \n            # Store in database for long-term analysis\n            async with get_db_session() as db:\n                await enhanced_auth_manager._log_security_event(\n                    db,\n                    event_type=event_type,\n                    severity=severity,\n                    description=f\"Security event: {event_type}\",\n                    ip_address=request.client.host if request.client else None,\n                    user_agent=request.headers.get('user-agent', ''),\n                    event_metadata=metadata\n                )\n                \n        except Exception as e:\n            logger.error(\"Failed to log security event\", error=str(e))\n    \n    async def _cleanup_security_caches(self):\n        \"\"\"Clean up security monitoring caches.\"\"\"\n        now = time.time()\n        cutoff = now - 3600  # 1 hour ago\n        \n        # Clean rate limit cache\n        expired_keys = []\n        for identifier, cache_entry in self._rate_limit_cache.items():\n            cache_entry['requests'] = [\n                req_time for req_time in cache_entry['requests'] if req_time > cutoff\n            ]\n            \n            if (not cache_entry['requests'] and \n                now > cache_entry.get('blocked_until', 0) and\n                cache_entry.get('threat_score', 0) < 5):\n                expired_keys.append(identifier)\n        \n        for key in expired_keys:\n            del self._rate_limit_cache[key]\n        \n        # Clean security events (keep last hour)\n        self._security_events = [\n            event for event in self._security_events \n            if (now - event['timestamp'].timestamp()) < 3600\n        ]\n        \n        logger.debug(\n            \"Security cache cleanup completed\",\n            rate_limit_entries_removed=len(expired_keys),\n            security_events_count=len(self._security_events)\n        )\n    \n    def get_security_metrics(self) -> Dict[str, Any]:\n        \"\"\"Get current security metrics for monitoring.\"\"\"\n        now = time.time()\n        recent_events = [\n            event for event in self._security_events\n            if (now - event['timestamp'].timestamp()) < 900  # 15 minutes\n        ]\n        \n        # Count events by type and severity\n        event_counts = {}\n        severity_counts = {\"low\": 0, \"medium\": 0, \"high\": 0, \"critical\": 0}\n        \n        for event in recent_events:\n            event_type = event['event_type']\n            severity = event['severity']\n            \n            event_counts[event_type] = event_counts.get(event_type, 0) + 1\n            severity_counts[severity] += 1\n        \n        return {\n            \"monitoring_window_minutes\": 15,\n            \"total_security_events\": len(recent_events),\n            \"events_by_type\": event_counts,\n            \"events_by_severity\": severity_counts,\n            \"active_rate_limits\": len(self._rate_limit_cache),\n            \"threat_level\": self._calculate_overall_threat_level(severity_counts),\n            \"adhd_crisis_bypasses_active\": settings.crisis_bypass_auth\n        }\n    \n    def _calculate_overall_threat_level(self, severity_counts: Dict[str, int]) -> str:\n        \"\"\"Calculate overall threat level based on recent events.\"\"\"\n        if severity_counts[\"critical\"] > 0:\n            return \"critical\"\n        elif severity_counts[\"high\"] > 5:\n            return \"high\"\n        elif severity_counts[\"medium\"] > 10:\n            return \"elevated\"\n        elif severity_counts[\"low\"] > 20:\n            return \"moderate\"\n        else:\n            return \"low\"\n\n\nclass EnhancedCSRFMiddleware(BaseHTTPMiddleware):\n    \"\"\"Enhanced CSRF protection with double-submit cookie pattern.\"\"\"\n    \n    def __init__(self, app):\n        super().__init__(app)\n        self.safe_methods = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}\n        self.csrf_secret = settings.master_encryption_key.encode('utf-8')\n    \n    async def dispatch(self, request: Request, call_next):\n        \"\"\"Enhanced CSRF protection with double-submit pattern.\"\"\"\n        \n        # Skip CSRF check for safe methods\n        if request.method in self.safe_methods:\n            return await call_next(request)\n        \n        # Skip CSRF check for API key authentication\n        auth_header = request.headers.get('authorization', '')\n        if auth_header.startswith('Bearer '):\n            return await call_next(request)\n        \n        # Skip CSRF check for specific paths\n        skip_paths = ['/auth/login', '/auth/register', '/webhooks/', '/health', '/metrics']\n        if any(skip in str(request.url.path) for skip in skip_paths):\n            return await call_next(request)\n        \n        # Enhanced CSRF token validation\n        csrf_header = request.headers.get('X-CSRF-Token')\n        csrf_cookie = request.cookies.get('csrf_token')\n        session_id = request.cookies.get('session_id')\n        \n        # Check for CSRF tokens\n        if not csrf_header or not csrf_cookie or not session_id:\n            logger.warning(\n                \"CSRF protection: Missing required tokens\",\n                path=request.url.path,\n                method=request.method,\n                client=request.client.host if request.client else 'unknown',\n                has_header=bool(csrf_header),\n                has_cookie=bool(csrf_cookie),\n                has_session=bool(session_id)\n            )\n            \n            return JSONResponse(\n                status_code=403,\n                content={\n                    \"success\": False,\n                    \"message\": \"CSRF protection active. Please refresh the page and try again.\",\n                    \"code\": \"CSRF_TOKEN_MISSING\"\n                }\n            )\n        \n        # Validate double-submit pattern\n        if not self._validate_double_submit_csrf(csrf_header, csrf_cookie, session_id):\n            logger.security(\n                \"CSRF validation failed - potential attack\",\n                path=request.url.path,\n                method=request.method,\n                client=request.client.host if request.client else 'unknown',\n                session_id=session_id[:8] + \"...\"\n            )\n            \n            return JSONResponse(\n                status_code=403,\n                content={\n                    \"success\": False,\n                    \"message\": \"CSRF validation failed. Please refresh the page and try again.\",\n                    \"code\": \"CSRF_VALIDATION_FAILED\"\n                }\n            )\n        \n        # Validate session\n        try:\n            async with get_db_session() as db:\n                session_info = await enhanced_auth_manager.validate_session(db, session_id, request)\n                if not session_info:\n                    return JSONResponse(\n                        status_code=401,\n                        content={\n                            \"success\": False,\n                            \"message\": \"Invalid session. Please log in again.\",\n                            \"code\": \"SESSION_INVALID\"\n                        }\n                    )\n                \n                # Store session info for downstream use\n                request.state.session_info = session_info\n                \n        except Exception as e:\n            logger.error(\"CSRF session validation error\", error=str(e))\n            return JSONResponse(\n                status_code=500,\n                content={\n                    \"success\": False,\n                    \"message\": \"Security validation error. Please try again.\",\n                    \"code\": \"CSRF_SESSION_ERROR\"\n                }\n            )\n        \n        return await call_next(request)\n    \n    def _validate_double_submit_csrf(self, header_token: str, cookie_token: str, session_id: str) -> bool:\n        \"\"\"Validate CSRF tokens using double-submit cookie pattern with HMAC.\"\"\"\n        try:\n            # Tokens must match (basic double-submit)\n            if header_token != cookie_token:\n                return False\n            \n            # Validate token structure and signature\n            token_parts = header_token.split('.')\n            if len(token_parts) != 2:\n                return False\n            \n            payload, signature = token_parts\n            \n            # Verify HMAC signature\n            expected_signature = hmac.new(\n                self.csrf_secret,\n                f\"{payload}.{session_id}\".encode('utf-8'),\n                hashlib.sha256\n            ).hexdigest()\n            \n            return hmac.compare_digest(signature, expected_signature)\n            \n        except Exception as e:\n            logger.warning(\"CSRF validation error\", error=str(e))\n            return False\n    \n    def generate_csrf_token(self, session_id: str) -> str:\n        \"\"\"Generate cryptographically secure CSRF token.\"\"\"\n        # Create payload with timestamp\n        timestamp = str(int(time.time()))\n        nonce = secrets.token_urlsafe(16)\n        payload = f\"{timestamp}.{nonce}\"\n        \n        # Create HMAC signature\n        signature = hmac.new(\n            self.csrf_secret,\n            f\"{payload}.{session_id}\".encode('utf-8'),\n            hashlib.sha256\n        ).hexdigest()\n        \n        return f\"{payload}.{signature}\"\n\n\n# Export enhanced middleware classes\n__all__ = [\n    'EnhancedSecurityMiddleware',\n    'EnhancedCSRFMiddleware'\n]