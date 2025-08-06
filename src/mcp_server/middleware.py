"""
Custom middleware for MCP ADHD Server.

Handles request/response processing, metrics collection, and monitoring.
"""
import time
import asyncio
from typing import Callable
from urllib.parse import urlparse

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from mcp_server.metrics import metrics_collector

logger = structlog.get_logger(__name__)


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


class SecurityMiddleware(BaseHTTPMiddleware):
    """Basic security middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Add security headers
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # ADHD-specific headers for client optimization
        response.headers["X-Service"] = "MCP-ADHD-Server"
        response.headers["X-Optimized-For"] = "Executive-Function"
        
        return response