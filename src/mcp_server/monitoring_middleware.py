"""
Enhanced monitoring middleware for MCP ADHD Server.

Integrates with the comprehensive monitoring system to provide:
- Distributed tracing for all requests
- ADHD-specific performance monitoring
- Crisis detection patterns
- User engagement analytics
- System performance tracking
"""

import time
import asyncio
from typing import Callable, Optional
from datetime import datetime

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from mcp_server.monitoring import monitoring_system
from mcp_server.adhd_errors import create_adhd_error_response
from mcp_server.config import settings

logger = structlog.get_logger(__name__)


class ComprehensiveMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive monitoring middleware that integrates all observability features.
    
    Features:
    - Distributed tracing with OpenTelemetry
    - ADHD-specific metrics collection
    - Performance monitoring and alerting
    - User experience tracking
    - Crisis pattern detection
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing and extract metadata
        start_time = time.time()
        endpoint = self._get_endpoint_pattern(request.url.path)
        method = request.method
        user_id = self._extract_user_id(request)
        session_id = request.headers.get("X-Session-ID")
        
        # Start comprehensive tracing
        operation_name = f"http_{method.lower()}_{endpoint.replace('/', '_').strip('_')}"
        
        async with monitoring_system.trace_operation(
            operation_name,
            method=method,
            endpoint=endpoint,
            user_id=user_id,
            session_id=session_id,
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent", "unknown")
        ) as span:
            
            try:
                # Pre-request monitoring
                await self._record_pre_request_metrics(request, user_id, endpoint)
                
                # Process request
                response = await call_next(request)
                
                # Post-request monitoring
                duration = time.time() - start_time
                await self._record_post_request_metrics(
                    request, response, duration, user_id, endpoint, method, span
                )
                
                return response
                
            except Exception as e:
                # Error monitoring
                duration = time.time() - start_time
                await self._record_error_metrics(
                    request, e, duration, user_id, endpoint, method, span
                )
                
                # Return ADHD-optimized error response
                return create_adhd_error_response(
                    error=e,
                    status_code=500,
                    request=request
                )
    
    async def _record_pre_request_metrics(self, request: Request, user_id: Optional[str], endpoint: str):
        """Record metrics before processing the request."""
        # Track active requests
        monitoring_system.performance_monitor.api_request_count.add(
            1, {"endpoint": endpoint, "status": "started"}
        )
        
        # Detect potential crisis patterns in request
        if user_id and settings.adhd_crisis_detection_enabled:
            await self._check_crisis_patterns(request, user_id)
        
        # Track engagement patterns
        if user_id and settings.user_engagement_tracking:
            await self._track_engagement_start(request, user_id, endpoint)
    
    async def _record_post_request_metrics(
        self, 
        request: Request, 
        response: Response, 
        duration: float,
        user_id: Optional[str],
        endpoint: str,
        method: str,
        span
    ):
        """Record comprehensive metrics after successful request processing."""
        
        # Update span attributes
        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.response_time_ms", duration * 1000)
        span.set_attribute("adhd.target_met", duration <= settings.adhd_response_time_target)
        
        # Record performance metrics
        monitoring_system.performance_monitor.record_api_request(
            duration, method, endpoint, response.status_code
        )
        
        # Record ADHD-specific metrics
        if settings.performance_monitoring_enabled:
            monitoring_system.adhd_metrics.record_response_time(
                duration, endpoint, user_id
            )
            
            # Check performance targets
            if duration > settings.adhd_response_time_target:
                logger.warning(
                    "ADHD response time target exceeded",
                    endpoint=endpoint,
                    duration=duration,
                    target=settings.adhd_response_time_target,
                    user_id=user_id,
                    severity="high_attention_impact"
                )
                
                # Alert if this is a critical endpoint
                if endpoint in ["/chat", "/api/tasks", "/crisis"]:
                    await self._trigger_performance_alert(
                        endpoint, duration, user_id, "response_time_exceeded"
                    )
        
        # Track user engagement
        if user_id and settings.user_engagement_tracking:
            await self._track_engagement_completion(
                request, response, duration, user_id, endpoint
            )
        
        # Detect hyperfocus patterns
        if user_id and settings.adhd_hyperfocus_detection_enabled:
            await self._detect_hyperfocus_patterns(request, duration, user_id, endpoint)
        
        # Add monitoring headers to response
        self._add_monitoring_headers(response, duration, user_id)
    
    async def _record_error_metrics(
        self,
        request: Request,
        error: Exception,
        duration: float,
        user_id: Optional[str],
        endpoint: str,
        method: str,
        span
    ):
        """Record comprehensive error metrics and patterns."""
        
        # Update span with error information
        span.set_attribute("error", True)
        span.set_attribute("error.type", type(error).__name__)
        span.set_attribute("error.message", str(error))
        span.set_attribute("adhd.error_impact", "high_disruption")
        
        # Record performance metrics for errors
        monitoring_system.performance_monitor.record_api_request(
            duration, method, endpoint, 500
        )
        
        # Track error patterns that might indicate user stress
        if user_id:
            await self._analyze_error_patterns(error, user_id, endpoint)
        
        # Enhanced error logging with ADHD context
        logger.error(
            "Request processing error with ADHD impact analysis",
            endpoint=endpoint,
            method=method,
            error_type=type(error).__name__,
            error_message=str(error),
            duration=duration,
            user_id=user_id,
            potential_adhd_triggers=[
                "attention_disruption",
                "task_interruption", 
                "cognitive_overload"
            ],
            recommended_actions=[
                "simplify_next_interaction",
                "provide_calming_response",
                "check_user_wellbeing"
            ],
            exc_info=True
        )
        
        # Trigger alerts for critical errors
        if endpoint in ["/chat", "/crisis", "/emergency"] or "critical" in str(error).lower():
            await self._trigger_critical_error_alert(error, user_id, endpoint)
    
    async def _check_crisis_patterns(self, request: Request, user_id: str):
        """Check for crisis patterns in incoming requests."""
        try:
            # Analyze request patterns that might indicate crisis
            rapid_requests = await self._check_rapid_request_pattern(user_id)
            unusual_timing = await self._check_unusual_timing_pattern(user_id)
            
            if rapid_requests or unusual_timing:
                monitoring_system.adhd_metrics.record_crisis_detection(
                    user_id, 
                    "behavioral_pattern", 
                    "medium"
                )
                
                logger.info(
                    "Potential crisis pattern detected",
                    user_id=user_id,
                    rapid_requests=rapid_requests,
                    unusual_timing=unusual_timing,
                    timestamp=datetime.utcnow().isoformat()
                )
                
        except Exception as e:
            logger.error("Error in crisis pattern detection", error=str(e))
    
    async def _track_engagement_start(self, request: Request, user_id: str, endpoint: str):
        """Track the start of user engagement."""
        try:
            # Calculate engagement score based on request patterns
            engagement_score = await self._calculate_engagement_score(user_id, endpoint)
            
            monitoring_system.adhd_metrics.record_engagement_score(
                engagement_score, user_id, f"start_{endpoint}"
            )
            
        except Exception as e:
            logger.error("Error tracking engagement start", error=str(e))
    
    async def _track_engagement_completion(
        self, 
        request: Request,
        response: Response, 
        duration: float,
        user_id: str, 
        endpoint: str
    ):
        """Track engagement completion and patterns."""
        try:
            # Calculate completion engagement score
            engagement_score = await self._calculate_completion_engagement(
                duration, response.status_code, endpoint
            )
            
            monitoring_system.adhd_metrics.record_engagement_score(
                engagement_score, user_id, f"complete_{endpoint}"
            )
            
            # Track task completion patterns
            if endpoint in ["/api/tasks", "/chat"] and response.status_code < 300:
                monitoring_system.adhd_metrics.record_task_completion(
                    user_id, endpoint, duration
                )
            
        except Exception as e:
            logger.error("Error tracking engagement completion", error=str(e))
    
    async def _detect_hyperfocus_patterns(
        self, 
        request: Request, 
        duration: float,
        user_id: str, 
        endpoint: str
    ):
        """Detect potential hyperfocus sessions."""
        try:
            # Check for hyperfocus indicators
            session_duration = await self._get_session_duration(user_id)
            
            # Hyperfocus detection criteria
            if (session_duration > 3600 and  # More than 1 hour
                duration < 1.0 and  # Fast responses indicate flow state
                endpoint in ["/chat", "/api/tasks"]):  # Focus-intensive endpoints
                
                monitoring_system.adhd_metrics.record_hyperfocus_session(
                    user_id, session_duration, endpoint
                )
                
                logger.info(
                    "Hyperfocus session detected",
                    user_id=user_id,
                    session_duration=session_duration,
                    endpoint=endpoint,
                    recommended_action="gentle_break_reminder"
                )
                
        except Exception as e:
            logger.error("Error detecting hyperfocus patterns", error=str(e))
    
    async def _analyze_error_patterns(self, error: Exception, user_id: str, endpoint: str):
        """Analyze error patterns for user stress indicators."""
        try:
            error_type = type(error).__name__
            error_message = str(error).lower()
            
            # Check for stress-indicating error patterns
            stress_indicators = [
                "timeout", "overload", "too_many", "rate_limit",
                "connection_error", "server_error"
            ]
            
            is_stress_related = any(indicator in error_message for indicator in stress_indicators)
            
            if is_stress_related:
                # Record potential stress-related error
                monitoring_system.adhd_metrics.record_cognitive_load(
                    user_id, 95.0, f"error_{endpoint}"  # High cognitive load for errors
                )
                
                logger.warning(
                    "Stress-related error pattern detected",
                    user_id=user_id,
                    error_type=error_type,
                    endpoint=endpoint,
                    stress_level="elevated",
                    recommended_intervention="calming_response"
                )
                
        except Exception as e:
            logger.error("Error analyzing error patterns", error=str(e))
    
    async def _trigger_performance_alert(
        self, 
        endpoint: str, 
        duration: float, 
        user_id: Optional[str],
        alert_type: str
    ):
        """Trigger performance-related alerts."""
        try:
            alert_data = {
                "alert_type": alert_type,
                "endpoint": endpoint,
                "duration": duration,
                "target": settings.adhd_response_time_target,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "severity": "high" if duration > 5.0 else "medium"
            }
            
            logger.warning("Performance alert triggered", **alert_data)
            
            # TODO: Integrate with actual alerting system (Slack, PagerDuty, etc.)
            
        except Exception as e:
            logger.error("Error triggering performance alert", error=str(e))
    
    async def _trigger_critical_error_alert(
        self, 
        error: Exception, 
        user_id: Optional[str], 
        endpoint: str
    ):
        """Trigger alerts for critical errors."""
        try:
            alert_data = {
                "alert_type": "critical_error",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "endpoint": endpoint,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "severity": "critical"
            }
            
            logger.critical("Critical error alert triggered", **alert_data)
            
            # TODO: Integrate with incident management system
            
        except Exception as e:
            logger.error("Error triggering critical error alert", error=str(e))
    
    def _add_monitoring_headers(self, response: Response, duration: float, user_id: Optional[str]):
        """Add monitoring and performance headers to response."""
        response.headers["X-Response-Time"] = f"{duration:.3f}"
        response.headers["X-ADHD-Optimized"] = "true"
        response.headers["X-Target-Met"] = str(duration <= settings.adhd_response_time_target)
        
        if user_id:
            response.headers["X-User-Tracked"] = "true"
        
        # Add performance guidance headers
        if duration > settings.adhd_response_time_target:
            response.headers["X-Performance-Warning"] = "response_time_exceeded"
            response.headers["X-Recommendation"] = "consider_simpler_request"
    
    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from various sources in the request."""
        # Try header first
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
        
        # Try to extract from Authorization header (JWT)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # TODO: Implement JWT token parsing to extract user_id
                pass
            except Exception:
                pass
        
        # Try to extract from session cookie
        # TODO: Implement session-based user extraction
        
        return None
    
    def _get_endpoint_pattern(self, path: str) -> str:
        """Convert URL path to endpoint pattern for consistent metrics."""
        patterns = {
            '/health': '/health',
            '/health/detailed': '/health/detailed', 
            '/metrics': '/metrics',
            '/chat': '/chat',
            '/api/tasks': '/api/tasks',
            '/api/users': '/api/users',
            '/auth/login': '/auth/login',
            '/auth/logout': '/auth/logout',
            '/crisis': '/crisis',
            '/emergency': '/emergency',
            '/': '/'
        }
        
        # Check for exact matches
        if path in patterns:
            return patterns[path]
        
        # Check for parameterized patterns
        path_parts = path.split('/')
        
        if len(path_parts) >= 3:
            if path_parts[1] == 'api' and path_parts[2] == 'tasks':
                return '/api/tasks/{id}' if len(path_parts) > 3 else '/api/tasks'
            elif path_parts[1] == 'api' and path_parts[2] == 'users':
                return '/api/users/{id}' if len(path_parts) > 3 else '/api/users'
            elif path_parts[1] == 'health':
                return '/health/{component}'
        
        # Default patterns
        if path.startswith('/static'):
            return '/static/*'
        elif path.startswith('/docs'):
            return '/docs/*'
        elif path.startswith('/api'):
            return '/api/*'
        else:
            return '/other'
    
    async def _check_rapid_request_pattern(self, user_id: str) -> bool:
        """Check if user is making unusually rapid requests (crisis indicator)."""
        # TODO: Implement request frequency analysis
        return False
    
    async def _check_unusual_timing_pattern(self, user_id: str) -> bool:
        """Check for unusual timing patterns (e.g., very late night activity)."""
        # TODO: Implement timing pattern analysis
        return False
    
    async def _calculate_engagement_score(self, user_id: str, endpoint: str) -> float:
        """Calculate user engagement score based on various factors."""
        # TODO: Implement comprehensive engagement scoring
        return 75.0  # Default neutral engagement
    
    async def _calculate_completion_engagement(
        self, 
        duration: float, 
        status_code: int, 
        endpoint: str
    ) -> float:
        """Calculate engagement score based on completion patterns."""
        base_score = 70.0
        
        # Adjust for response time
        if duration <= settings.adhd_response_time_target:
            base_score += 10.0
        elif duration > 5.0:
            base_score -= 20.0
        
        # Adjust for success
        if status_code < 300:
            base_score += 15.0
        elif status_code >= 400:
            base_score -= 25.0
        
        # Adjust for endpoint type
        if endpoint in ["/chat", "/api/tasks"]:
            base_score += 5.0  # Higher engagement endpoints
        
        return min(100.0, max(0.0, base_score))
    
    async def _get_session_duration(self, user_id: str) -> float:
        """Get current session duration for user."""
        # TODO: Implement session duration tracking
        return 0.0


class ADHDUserExperienceMiddleware(BaseHTTPMiddleware):
    """
    Specialized middleware for ADHD user experience optimization.
    
    Features:
    - Cognitive load assessment
    - Attention span tracking
    - Context switching detection
    - Executive function support metrics
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        user_id = request.headers.get("X-User-ID")
        
        if not user_id or not settings.adhd_cognitive_load_monitoring:
            # Skip ADHD-specific monitoring if no user or disabled
            return await call_next(request)
        
        try:
            # Pre-request ADHD analysis
            cognitive_context = await self._analyze_cognitive_context(request, user_id)
            
            # Process request
            response = await call_next(request)
            
            # Post-request ADHD analysis
            duration = time.time() - start_time
            await self._analyze_adhd_response_patterns(
                request, response, duration, user_id, cognitive_context
            )
            
            # Add ADHD-specific response headers
            self._add_adhd_headers(response, duration, cognitive_context)
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # High cognitive load for errors
            monitoring_system.adhd_metrics.record_cognitive_load(
                user_id, 90.0, f"error_{request.url.path}"
            )
            
            logger.error(
                "ADHD UX middleware error",
                user_id=user_id,
                error=str(e),
                duration=duration,
                cognitive_impact="high_disruption"
            )
            raise
    
    async def _analyze_cognitive_context(self, request: Request, user_id: str) -> dict:
        """Analyze current cognitive context for the user."""
        context = {
            "request_complexity": self._assess_request_complexity(request),
            "potential_context_switch": await self._detect_context_switch(request, user_id),
            "current_cognitive_load": await self._get_current_cognitive_load(user_id),
            "time_of_day_factor": self._calculate_time_factor()
        }
        
        return context
    
    async def _analyze_adhd_response_patterns(
        self,
        request: Request,
        response: Response, 
        duration: float,
        user_id: str,
        cognitive_context: dict
    ):
        """Analyze response patterns specific to ADHD user experience."""
        
        # Calculate cognitive load impact
        cognitive_load = self._calculate_cognitive_load(
            duration, response, cognitive_context
        )
        
        # Record cognitive load metrics
        monitoring_system.adhd_metrics.record_cognitive_load(
            user_id, cognitive_load, request.url.path
        )
        
        # Detect executive function patterns
        if request.url.path in ["/api/tasks", "/chat"]:
            await self._analyze_executive_function_usage(
                request, response, duration, user_id, cognitive_load
            )
        
        # Track attention patterns
        await self._track_attention_patterns(
            request, duration, user_id, cognitive_load
        )
    
    def _assess_request_complexity(self, request: Request) -> float:
        """Assess the cognitive complexity of the request."""
        complexity_score = 1.0
        
        # Endpoint complexity
        endpoint_complexity = {
            "/chat": 3.0,
            "/api/tasks": 2.5,
            "/api/users": 2.0,
            "/health": 0.5
        }
        
        path = request.url.path
        for endpoint, score in endpoint_complexity.items():
            if path.startswith(endpoint):
                complexity_score = score
                break
        
        # Method complexity
        method_complexity = {
            "GET": 1.0,
            "POST": 1.5,
            "PUT": 1.8,
            "DELETE": 2.0
        }
        complexity_score *= method_complexity.get(request.method, 1.0)
        
        # Body complexity
        content_length = request.headers.get("content-length")
        if content_length:
            size_factor = min(int(content_length) / 1024, 5.0)  # Cap at 5x
            complexity_score *= (1.0 + size_factor * 0.1)
        
        return min(complexity_score, 5.0)  # Cap at 5.0
    
    async def _detect_context_switch(self, request: Request, user_id: str) -> bool:
        """Detect if this request represents a context switch."""
        # TODO: Implement context switch detection based on request patterns
        return False
    
    async def _get_current_cognitive_load(self, user_id: str) -> float:
        """Get the current cognitive load for the user."""
        # TODO: Implement current cognitive load tracking
        return 50.0  # Default moderate load
    
    def _calculate_time_factor(self) -> float:
        """Calculate time-of-day factor for cognitive load."""
        from datetime import datetime
        
        current_hour = datetime.now().hour
        
        # ADHD attention patterns throughout the day
        if 6 <= current_hour <= 10:  # Morning peak
            return 0.8
        elif 10 <= current_hour <= 14:  # Late morning/early afternoon
            return 1.0
        elif 14 <= current_hour <= 16:  # Afternoon dip
            return 1.3
        elif 16 <= current_hour <= 19:  # Evening recovery
            return 0.9
        elif 19 <= current_hour <= 22:  # Evening
            return 1.1
        else:  # Late night/early morning
            return 1.5
    
    def _calculate_cognitive_load(
        self, 
        duration: float, 
        response: Response,
        cognitive_context: dict
    ) -> float:
        """Calculate comprehensive cognitive load score."""
        
        base_load = cognitive_context["current_cognitive_load"]
        
        # Duration impact
        duration_factor = min(duration / 3.0, 2.0)  # Cap at 2x
        
        # Request complexity impact
        complexity_factor = cognitive_context["request_complexity"] / 5.0
        
        # Context switch penalty
        context_switch_penalty = 20.0 if cognitive_context["potential_context_switch"] else 0.0
        
        # Time of day factor
        time_factor = cognitive_context["time_of_day_factor"]
        
        # Response status impact
        status_factor = 1.0
        if response.status_code >= 400:
            status_factor = 1.5  # Errors increase cognitive load
        
        # Calculate final cognitive load
        cognitive_load = (
            base_load * time_factor * status_factor +
            duration_factor * 15.0 +
            complexity_factor * 25.0 +
            context_switch_penalty
        )
        
        return min(cognitive_load, 100.0)  # Cap at 100
    
    async def _analyze_executive_function_usage(
        self,
        request: Request,
        response: Response,
        duration: float,
        user_id: str,
        cognitive_load: float
    ):
        """Analyze patterns related to executive function usage."""
        
        # Detect task management patterns
        if request.url.path.startswith("/api/tasks"):
            if request.method == "POST" and response.status_code < 300:
                # Successful task creation
                monitoring_system.adhd_metrics.record_task_completion(
                    user_id, "task_creation", duration
                )
            elif response.status_code >= 400:
                # Task management difficulty
                monitoring_system.adhd_metrics.record_task_abandonment(
                    user_id, "task_management", "error_encountered"
                )
        
        # Detect planning and organization patterns
        if cognitive_load > 70 and duration > 2.0:
            # High cognitive load + slow response = potential executive function strain
            logger.info(
                "Executive function strain detected",
                user_id=user_id,
                cognitive_load=cognitive_load,
                duration=duration,
                endpoint=request.url.path,
                recommendation="provide_executive_function_support"
            )
    
    async def _track_attention_patterns(
        self,
        request: Request,
        duration: float, 
        user_id: str,
        cognitive_load: float
    ):
        """Track attention patterns and focus sustainability."""
        
        # Calculate attention score based on response time and cognitive load
        attention_sustainability = 100.0 - cognitive_load
        
        if duration <= 1.0:
            attention_sustainability += 10.0  # Quick responses indicate good focus
        elif duration > 3.0:
            attention_sustainability -= 15.0  # Slow responses indicate attention difficulties
        
        # Record attention metrics
        monitoring_system.adhd_metrics.record_attention_span(
            duration, user_id, f"request_{request.url.path}"
        )
        
        # Detect attention difficulties
        if attention_sustainability < 30:
            logger.warning(
                "Attention difficulties detected",
                user_id=user_id,
                attention_sustainability=attention_sustainability,
                cognitive_load=cognitive_load,
                duration=duration,
                recommendation="suggest_break_or_simplification"
            )
    
    def _add_adhd_headers(self, response: Response, duration: float, cognitive_context: dict):
        """Add ADHD-specific headers to help client optimization."""
        response.headers["X-Cognitive-Load"] = f"{cognitive_context['current_cognitive_load']:.1f}"
        response.headers["X-Request-Complexity"] = f"{cognitive_context['request_complexity']:.1f}"
        response.headers["X-Attention-Friendly"] = str(duration <= 2.0)
        response.headers["X-Executive-Function-Load"] = "low" if duration <= 1.0 else "high"