"""
Custom middleware for MCP ADHD Server.

Handles request/response processing, metrics collection, and monitoring.
"""
import time
import asyncio
import json
import ipaddress
from typing import Callable, Dict, Any
from collections import defaultdict, deque
from urllib.parse import urlparse

import structlog
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from mcp_server.metrics import metrics_collector

logger = structlog.get_logger(__name__)

# Rate limiting storage
_rate_limit_storage = defaultdict(lambda: deque())
_blocked_ips = defaultdict(float)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing
        start_time = time.time()
        
        # Extract endpoint pattern (remove path params for consistent metrics)
        endpoint = self._get_endpoint_pattern(request.url.path)
        method = request.method
        
        # Record connection
        metrics_collector.update_active_connections("http", 1)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            metrics_collector.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration_seconds=duration
            )
            
            # Log slow requests
            if duration > 1.0:
                logger.warning(
                    "Slow HTTP request",
                    method=method,
                    endpoint=endpoint,
                    duration_seconds=duration,
                    status_code=response.status_code
                )
            
            return response
            
        except Exception as e:
            # Calculate duration for failed requests
            duration = time.time() - start_time
            
            # Record error metrics
            metrics_collector.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=500,
                duration_seconds=duration
            )
            
            logger.error(
                "HTTP request failed",
                method=method,
                endpoint=endpoint,
                duration_seconds=duration,
                error=str(e),
                exc_info=True
            )
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
        
        finally:
            # Update connection count
            metrics_collector.update_active_connections("http", -1)
    
    def _get_endpoint_pattern(self, path: str) -> str:
        """Convert URL path to endpoint pattern for consistent metrics."""
        # Map common patterns to reduce cardinality
        patterns = {
            '/health': '/health',
            '/health/detailed': '/health/detailed',
            '/health/metrics/system': '/health/metrics/system',
            '/metrics': '/metrics',
            '/metrics/summary': '/metrics/summary',
            '/chat': '/chat',
            '/auth/login': '/auth/login',
            '/auth/logout': '/auth/logout',
            '/auth/me': '/auth/me',
            '/': '/',
            '/api': '/api',
        }
        
        # Check for exact matches first
        if path in patterns:
            return patterns[path]
        
        # Check for parameterized patterns
        path_parts = path.split('/')
        
        if len(path_parts) >= 3:
            if path_parts[1] == 'health' and len(path_parts) == 3:
                return '/health/{component}'
            elif path_parts[1] == 'health' and path_parts[2] == 'history' and len(path_parts) == 4:
                return '/health/history/{component}'
            elif path_parts[1] == 'tasks' and len(path_parts) == 3:
                return '/tasks/{task_id}'
            elif path_parts[1] == 'users' and len(path_parts) == 3:
                return '/users/{user_id}'
            elif path_parts[1] == 'auth' and path_parts[2] == 'api-keys' and len(path_parts) == 4:
                return '/auth/api-keys/{key_id}'
        
        # Default fallback
        if path.startswith('/static'):
            return '/static/*'
        elif path.startswith('/docs'):
            return '/docs/*'
        else:
            return '/other'


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor performance and handle timeouts."""
    
    def __init__(self, app, timeout_seconds: float = 30.0):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            # Set timeout for request processing
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds
            )
            return response
            
        except asyncio.TimeoutError:
            logger.error(
                "Request timeout",
                method=request.method,
                url=str(request.url),
                timeout_seconds=self.timeout_seconds
            )
            
            return JSONResponse(
                status_code=504,
                content={
                    "detail": f"Request timeout after {self.timeout_seconds} seconds"
                }
            )
        except Exception as e:
            logger.error(
                "Performance middleware error",
                method=request.method,
                url=str(request.url),
                error=str(e),
                exc_info=True
            )
            raise


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """Middleware to handle health check optimization."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Fast-path for basic health checks
        if request.url.path == "/health" and request.method == "GET":
            # Bypass full application stack for load balancer health checks
            start_time = time.time()
            
            try:
                response = await call_next(request)
                
                # Record health check metrics
                duration = time.time() - start_time
                if duration > 0.1:  # Log slow health checks
                    logger.warning(
                        "Slow health check",
                        duration_seconds=duration
                    )
                
                return response
                
            except Exception as e:
                logger.error(
                    "Health check failed",
                    error=str(e),
                    exc_info=True
                )
                
                # Return minimal error response for health checks
                return JSONResponse(
                    status_code=503,
                    content={"status": "unhealthy", "error": "service_unavailable"}
                )
        
        # Normal processing for other requests
        return await call_next(request)


class ADHDOptimizationMiddleware(BaseHTTPMiddleware):
    """Middleware for ADHD-specific optimizations."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Track cognitive load for ADHD users
        user_id = None
        
        # Try to get user ID from headers (for API keys) or session
        if "X-User-ID" in request.headers:
            user_id = request.headers["X-User-ID"]
        elif "Authorization" in request.headers:
            # Could extract from JWT token
            pass
        
        # Start request processing
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Calculate cognitive load based on response time and complexity
            duration = time.time() - start_time
            cognitive_load = min(duration / 3.0, 1.0)  # Scale 0-3s to 0-1
            
            # Adjust for endpoint complexity
            if request.url.path == "/chat":
                cognitive_load *= 1.5  # Chat requires more cognitive processing
            elif request.url.path.startswith("/health"):
                cognitive_load *= 0.1  # Health checks are low cognitive load
            
            # Update metrics if we have a user
            if user_id:
                metrics_collector.update_cognitive_load(cognitive_load)
                
                # Record user session activity
                if request.url.path == "/chat":
                    metrics_collector.record_user_session_start(user_id)
            
            # Add cognitive load header for client optimization
            response.headers["X-Cognitive-Load"] = f"{cognitive_load:.2f}"
            response.headers["X-Processing-Time"] = f"{duration:.3f}"
            
            return response
            
        except Exception as e:
            # High cognitive load for errors
            if user_id:
                metrics_collector.update_cognitive_load(0.9)
            
            logger.error(
                "ADHD optimization middleware error",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Advanced rate limiting middleware with ADHD-aware limits."""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 20,
        block_duration: int = 300  # 5 minutes
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.block_duration = block_duration
        
        # ADHD-specific rate limits by endpoint
        self.endpoint_limits = {
            "/health": {"rpm": 600, "burst": 100},  # Higher limit for health checks
            "/metrics": {"rpm": 120, "burst": 30},
            "/api/chat": {"rpm": 30, "burst": 10},  # Lower limit for intensive chat
            "/api/tasks": {"rpm": 120, "burst": 30},
            "/api/users": {"rpm": 60, "burst": 20},
            "/auth": {"rpm": 20, "burst": 5},  # Strict limits for auth endpoints
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        endpoint = self._get_endpoint_pattern(request.url.path)
        now = time.time()
        
        # Check if IP is currently blocked
        if client_ip in _blocked_ips and _blocked_ips[client_ip] > now:
            remaining_time = int(_blocked_ips[client_ip] - now)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Access blocked.",
                    "retry_after": remaining_time
                },
                headers={"Retry-After": str(remaining_time)}
            )
        
        # Get rate limits for endpoint
        limits = self.endpoint_limits.get(endpoint, {
            "rpm": self.requests_per_minute,
            "burst": self.burst_size
        })
        
        # Check rate limit
        rate_limit_key = f"{client_ip}:{endpoint}"
        if not self._check_rate_limit(rate_limit_key, limits["rpm"], limits["burst"], now):
            # Block IP for repeated violations
            violation_count = self._get_violation_count(client_ip)
            if violation_count >= 5:  # Block after 5 violations
                _blocked_ips[client_ip] = now + self.block_duration
                logger.warning(
                    "IP blocked due to repeated rate limit violations",
                    client_ip=client_ip,
                    violations=violation_count,
                    block_duration=self.block_duration
                )
            
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": limits["rpm"],
                    "window": "60 seconds"
                },
                headers={
                    "X-RateLimit-Limit": str(limits["rpm"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + 60))
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self._get_remaining_requests(rate_limit_key, limits["rpm"], now)
        response.headers["X-RateLimit-Limit"] = str(limits["rpm"])
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + 60))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, considering proxy headers."""
        # Check for forwarded headers (from reverse proxy)
        if "X-Forwarded-For" in request.headers:
            # Take the first IP (original client)
            forwarded_ips = request.headers["X-Forwarded-For"].split(",")
            return forwarded_ips[0].strip()
        elif "X-Real-IP" in request.headers:
            return request.headers["X-Real-IP"]
        else:
            return request.client.host
    
    def _get_endpoint_pattern(self, path: str) -> str:
        """Get endpoint pattern for rate limiting."""
        # Use simpler patterns for rate limiting
        if path.startswith("/health"):
            return "/health"
        elif path.startswith("/metrics"):
            return "/metrics"
        elif path.startswith("/api/chat"):
            return "/api/chat"
        elif path.startswith("/api/tasks"):
            return "/api/tasks"
        elif path.startswith("/api/users"):
            return "/api/users"
        elif path.startswith("/auth") or "api-keys" in path or "sessions" in path:
            return "/auth"
        else:
            return "/other"
    
    def _check_rate_limit(self, key: str, rpm: int, burst: int, now: float) -> bool:
        """Check if request is within rate limits."""
        requests = _rate_limit_storage[key]
        
        # Remove old requests (older than 1 minute)
        while requests and requests[0] <= now - 60:
            requests.popleft()
        
        # Check burst limit
        recent_requests = sum(1 for req_time in requests if req_time > now - 10)  # Last 10 seconds
        if recent_requests >= burst:
            self._record_violation(key.split(":")[0])  # Record violation for IP
            return False
        
        # Check per-minute limit
        if len(requests) >= rpm:
            self._record_violation(key.split(":")[0])  # Record violation for IP
            return False
        
        # Add current request
        requests.append(now)
        return True
    
    def _get_remaining_requests(self, key: str, rpm: int, now: float) -> int:
        """Get remaining requests in current window."""
        requests = _rate_limit_storage[key]
        # Remove old requests
        while requests and requests[0] <= now - 60:
            requests.popleft()
        return max(0, rpm - len(requests))
    
    def _record_violation(self, ip: str) -> None:
        """Record rate limit violation for an IP."""
        violation_key = f"violations:{ip}"
        now = time.time()
        violations = _rate_limit_storage[violation_key]
        
        # Remove old violations (older than 1 hour)
        while violations and violations[0] <= now - 3600:
            violations.popleft()
        
        violations.append(now)
    
    def _get_violation_count(self, ip: str) -> int:
        """Get recent violation count for an IP."""
        violation_key = f"violations:{ip}"
        now = time.time()
        violations = _rate_limit_storage[violation_key]
        
        # Remove old violations
        while violations and violations[0] <= now - 3600:
            violations.popleft()
        
        return len(violations)


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Input validation and sanitization middleware."""
    
    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_request_size = max_request_size
        
        # Dangerous patterns to check for
        self.dangerous_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"data:text/html",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"onclick\s*=",
            r"eval\s*\(",
            r"exec\s*\(",
            r"system\s*\(",
            r"__import__",
            r"subprocess",
            r"os\.system",
            r"DROP\s+TABLE",
            r"UNION\s+SELECT",
            r"INSERT\s+INTO",
            r"DELETE\s+FROM",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            logger.warning(
                "Request rejected due to size",
                size=content_length,
                max_size=self.max_request_size,
                client_ip=request.client.host
            )
            return JSONResponse(
                status_code=413,
                content={"detail": "Request entity too large"}
            )
        
        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if content_type and not any(
                ct in content_type.lower() for ct in [
                    "application/json",
                    "application/x-www-form-urlencoded",
                    "multipart/form-data",
                    "text/plain"
                ]
            ):
                logger.warning(
                    "Request rejected due to invalid content type",
                    content_type=content_type,
                    client_ip=request.client.host
                )
                return JSONResponse(
                    status_code=415,
                    content={"detail": "Unsupported media type"}
                )
        
        # Check for suspicious patterns in URL
        url_path = str(request.url.path)
        if self._contains_dangerous_patterns(url_path):
            logger.warning(
                "Request rejected due to suspicious URL pattern",
                url=url_path,
                client_ip=request.client.host
            )
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid request"}
            )
        
        # For JSON requests, validate the body
        if (request.method in ["POST", "PUT", "PATCH"] and 
            "application/json" in request.headers.get("content-type", "")):
            
            try:
                # Read and validate JSON body
                body = await request.body()
                if body:
                    body_str = body.decode("utf-8")
                    
                    # Check for dangerous patterns in JSON body
                    if self._contains_dangerous_patterns(body_str):
                        logger.warning(
                            "Request rejected due to suspicious content",
                            client_ip=request.client.host,
                            endpoint=url_path
                        )
                        return JSONResponse(
                            status_code=400,
                            content={"detail": "Invalid request content"}
                        )
                    
                    # Validate JSON structure
                    try:
                        json.loads(body_str)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Request rejected due to invalid JSON",
                            client_ip=request.client.host
                        )
                        return JSONResponse(
                            status_code=400,
                            content={"detail": "Invalid JSON format"}
                        )
            except Exception as e:
                logger.error(
                    "Error validating request body",
                    error=str(e),
                    client_ip=request.client.host
                )
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid request"}
                )
        
        # Process request
        return await call_next(request)
    
    def _contains_dangerous_patterns(self, text: str) -> bool:
        """Check if text contains dangerous patterns."""
        import re
        text_lower = text.lower()
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False


class SecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced security middleware with ADHD-specific optimizations."""
    
    def __init__(self, app, trusted_origins: list = None):
        super().__init__(app)
        self.trusted_origins = trusted_origins or ["https://localhost", "https://127.0.0.1"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check for suspicious headers
        if self._has_suspicious_headers(request):
            logger.warning(
                "Request rejected due to suspicious headers",
                client_ip=request.client.host,
                headers=dict(request.headers)
            )
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid request headers"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Enhanced security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # ADHD-specific headers for client optimization
        response.headers["X-Service"] = "MCP-ADHD-Server"
        response.headers["X-Optimized-For"] = "Executive-Function"
        response.headers["X-Response-Optimized"] = "true"
        
        # CORS headers for trusted origins
        origin = request.headers.get("origin")
        if origin in self.trusted_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        # Content Security Policy for ADHD-optimized UI
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' wss: ws:; "
                "frame-src 'none'; "
                "object-src 'none'"
            )
        
        return response
    
    def _has_suspicious_headers(self, request: Request) -> bool:
        """Check for suspicious request headers."""
        suspicious_patterns = [
            "cmd.exe",
            "/bin/bash",
            "powershell",
            "<script",
            "javascript:",
            "data:text/html"
        ]
        
        for header_name, header_value in request.headers.items():
            header_value_lower = header_value.lower()
            for pattern in suspicious_patterns:
                if pattern in header_value_lower:
                    return True
        
        return False