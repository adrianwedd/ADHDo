"""
Security middleware for enhanced authentication and security monitoring.

This module provides comprehensive security middleware including:
- Security headers
- Rate limiting
- Session management
- CSRF protection
- Security event logging
- Crisis support access bypasses (ADHD-specific)
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
import hashlib
import re

import structlog
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server.config import settings
from mcp_server.database import get_db_session
from mcp_server.enhanced_auth import enhanced_auth_manager
from mcp_server.db_models import RateLimit, SecurityEvent

logger = structlog.get_logger()


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware for MCP ADHD Server."""
    
    def __init__(self, app):
        super().__init__(app)
        self.crisis_patterns = [
            re.compile(r'\b(?:suicide|kill\s+myself|end\s+it\s+all)\b', re.IGNORECASE),
            re.compile(r'\b(?:self.harm|hurt\s+myself|cutting)\b', re.IGNORECASE),
            re.compile(r'\b(?:crisis|emergency|help\s+me)\b', re.IGNORECASE),
            re.compile(r'\b(?:can\'t\s+go\s+on|give\s+up)\b', re.IGNORECASE)
        ]
        
        # In-memory rate limiting cache (for performance)
        self._rate_limit_cache: Dict[str, Dict[str, any]] = {}
        self._last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatcher."""
        start_time = time.time()
        
        try:
            # Add security headers
            await self._add_security_headers(request)
            
            # Check for crisis support bypass
            if await self._check_crisis_bypass(request):
                logger.info("Crisis support bypass activated", path=request.url.path)
                # Allow request to proceed without full authentication
                response = await call_next(request)
                return await self._finalize_response(request, response, start_time)
            
            # Rate limiting check
            if not await self._check_rate_limit(request):
                logger.warning("Rate limit exceeded", 
                             client=request.client.host if request.client else 'unknown',
                             path=request.url.path)
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "message": "You're making requests too quickly. Take a breath and try again in a moment.",
                        "retry_after": 60
                    },
                    headers={"Retry-After": "60"}
                )
            
            # Process request
            response = await call_next(request)
            
            # Post-process response
            return await self._finalize_response(request, response, start_time)
            
        except Exception as e:
            logger.error("Security middleware error", error=str(e))
            
            # Log security event for middleware failures
            try:
                async with get_db_session() as db:
                    await enhanced_auth_manager._log_security_event(
                        db,
                        event_type="unauthorized_access",
                        severity="high",
                        description=f"Security middleware error: {str(e)}",
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get('user-agent', ''),
                        event_metadata={"path": str(request.url.path), "method": request.method}
                    )
            except Exception:
                pass  # Don't let logging errors break the request
            
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "We're experiencing technical difficulties. Please try again in a moment."
                }
            )
    
    async def _add_security_headers(self, request: Request) -> None:
        """Add security headers to request context."""
        # Headers will be added in _finalize_response
        pass
    
    async def _check_crisis_bypass(self, request: Request) -> bool:
        """Check if request should bypass authentication for crisis support."""
        if not settings.crisis_bypass_auth:
            return False
        
        # Check for crisis keywords in common paths
        crisis_paths = ['/chat', '/help', '/support', '/crisis']
        if not any(path in str(request.url.path) for path in crisis_paths):
            return False
        
        # Check request body for crisis indicators
        if request.method == "POST":
            try:
                body = await request.body()
                if body:
                    text_content = body.decode('utf-8', errors='ignore').lower()
                    
                    # Check against crisis patterns
                    for pattern in self.crisis_patterns:
                        if pattern.search(text_content):
                            return True
                    
                    # Check against configured keywords
                    for keyword in settings.crisis_keywords:
                        if keyword.lower() in text_content:
                            return True
            except Exception:
                pass  # Don't let body parsing errors break crisis detection
        
        return False
    
    async def _check_rate_limit(self, request: Request) -> bool:
        """Check if request is within rate limits."""
        if not request.client:
            return True  # Allow if no client info
        
        # Skip rate limiting for certain paths
        skip_paths = ['/health', '/metrics', '/docs', '/openapi.json']
        if any(skip in str(request.url.path) for skip in skip_paths):
            return True
        
        client_ip = request.client.host
        user_id = request.headers.get('X-User-ID', '')  # Get user ID if available
        
        # Create identifier (prefer user_id over IP)
        identifier = user_id if user_id else f"ip:{client_ip}"
        
        now = time.time()
        window_size = settings.rate_limit_window_size_seconds
        requests_per_minute = settings.rate_limit_requests_per_minute
        
        # Clean up old entries periodically
        if now - self._last_cleanup > 300:  # 5 minutes
            await self._cleanup_rate_limit_cache()
            self._last_cleanup = now
        
        # Check rate limit
        if identifier not in self._rate_limit_cache:
            self._rate_limit_cache[identifier] = {
                'requests': [],
                'blocked_until': 0
            }
        
        cache_entry = self._rate_limit_cache[identifier]
        
        # Check if currently blocked
        if now < cache_entry['blocked_until']:
            return False
        
        # Clean old requests from sliding window
        minute_ago = now - 60  # 1 minute window
        cache_entry['requests'] = [
            req_time for req_time in cache_entry['requests'] 
            if req_time > minute_ago
        ]
        
        # Check if limit exceeded
        if len(cache_entry['requests']) >= requests_per_minute:
            # Block for 1 minute
            cache_entry['blocked_until'] = now + 60
            
            # Log rate limit event
            try:
                async with get_db_session() as db:
                    await enhanced_auth_manager._log_security_event(
                        db,
                        event_type="rate_limit_exceeded",
                        severity="medium",
                        description=f"Rate limit exceeded: {len(cache_entry['requests'])} requests in 1 minute",
                        user_id=user_id if user_id else None,
                        ip_address=client_ip,
                        user_agent=request.headers.get('user-agent', ''),
                        event_metadata={
                            "requests_count": len(cache_entry['requests']),
                            "limit": requests_per_minute,
                            "identifier": identifier
                        }
                    )
            except Exception:
                pass  # Don't let logging errors break rate limiting
            
            return False
        
        # Add current request
        cache_entry['requests'].append(now)
        return True
    
    async def _cleanup_rate_limit_cache(self) -> None:
        """Clean up old rate limit cache entries."""
        now = time.time()
        cutoff = now - 3600  # 1 hour ago
        
        expired_keys = []
        for identifier, cache_entry in self._rate_limit_cache.items():
            # Remove old requests
            cache_entry['requests'] = [
                req_time for req_time in cache_entry['requests'] 
                if req_time > cutoff
            ]
            
            # Mark for removal if no recent activity and not blocked
            if (not cache_entry['requests'] and 
                now > cache_entry.get('blocked_until', 0)):
                expired_keys.append(identifier)
        
        # Remove expired entries
        for key in expired_keys:
            del self._rate_limit_cache[key]
        
        if expired_keys:
            logger.debug("Cleaned up rate limit cache", removed_entries=len(expired_keys))
    
    async def _finalize_response(
        self, 
        request: Request, 
        response: StarletteResponse, 
        start_time: float
    ) -> StarletteResponse:
        """Add security headers and finalize response."""
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Add security headers
        security_headers = {
            # HTTPS and security
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Content Security Policy (restrictive for security)
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "font-src 'self'; "
                "object-src 'none'; "
                "media-src 'self'; "
                "frame-src 'none';"
            ),
            
            # Additional security headers
            "Permissions-Policy": "microphone=(), camera=(), geolocation=()",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
            
            # Custom headers for debugging and monitoring
            "X-Response-Time": f"{response_time:.2f}ms",
            "X-Request-ID": str(request.headers.get('X-Request-ID', 'unknown'))
        }
        
        # Apply headers to response
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # Add ADHD-friendly performance indicator
        if response_time < 1000:  # < 1 second
            response.headers["X-ADHD-Performance"] = "optimal"
        elif response_time < 3000:  # < 3 seconds
            response.headers["X-ADHD-Performance"] = "acceptable"
        else:
            response.headers["X-ADHD-Performance"] = "slow"
            logger.warning("Slow response detected", 
                          response_time_ms=response_time,
                          path=request.url.path,
                          method=request.method)
        
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.safe_methods = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}
    
    async def dispatch(self, request: Request, call_next):
        """Check CSRF token for state-changing requests."""
        
        # Skip CSRF check for safe methods
        if request.method in self.safe_methods:
            return await call_next(request)
        
        # Skip CSRF check for API key authentication
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            return await call_next(request)
        
        # Skip CSRF check for certain paths
        skip_paths = ['/auth/login', '/auth/register', '/webhooks/', '/health']
        if any(skip in str(request.url.path) for skip in skip_paths):
            return await call_next(request)
        
        # Check CSRF token
        csrf_token = request.headers.get('X-CSRF-Token') or request.cookies.get('csrf_token')
        session_id = request.cookies.get('session_id')
        
        if not csrf_token or not session_id:
            logger.warning("CSRF token missing", 
                         path=request.url.path,
                         method=request.method,
                         client=request.client.host if request.client else 'unknown')
            
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "message": "CSRF token required. Please refresh the page and try again."
                }
            )
        
        # Validate CSRF token against session
        try:
            async with get_db_session() as db:
                session_info = await enhanced_auth_manager.validate_session(db, session_id, request)
                if not session_info:
                    return JSONResponse(
                        status_code=401,
                        content={
                            "success": False,
                            "message": "Invalid session. Please log in again."
                        }
                    )
                
                # TODO: Add proper CSRF token validation against session
                # For now, just check that both tokens exist
                
        except Exception as e:
            logger.error("CSRF validation error", error=str(e))
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Security validation error. Please try again."
                }
            )
        
        return await call_next(request)


class SessionCleanupMiddleware(BaseHTTPMiddleware):
    """Middleware for periodic session cleanup."""
    
    def __init__(self, app):
        super().__init__(app)
        self._last_cleanup = 0
        self._cleanup_interval = settings.session_cleanup_interval_hours * 3600  # Convert to seconds
    
    async def dispatch(self, request: Request, call_next):
        """Check if session cleanup is needed."""
        
        current_time = time.time()
        
        # Run cleanup periodically
        if current_time - self._last_cleanup > self._cleanup_interval:
            try:
                async with get_db_session() as db:
                    cleaned_count = await enhanced_auth_manager.cleanup_expired_sessions(db)
                    if cleaned_count > 0:
                        logger.info("Periodic session cleanup completed", 
                                  cleaned_sessions=cleaned_count)
                
                self._last_cleanup = current_time
                
            except Exception as e:
                logger.error("Session cleanup error", error=str(e))
        
        return await call_next(request)