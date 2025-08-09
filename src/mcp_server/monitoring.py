"""
Comprehensive Monitoring and Observability System for MCP ADHD Server.

This module provides enterprise-grade monitoring with ADHD-specific user experience metrics:
- Sentry SDK integration for error tracking
- OpenTelemetry for distributed tracing
- ADHD-specific performance metrics
- Crisis detection monitoring
- User engagement analytics
"""

import logging
import os
import time
import traceback
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from functools import wraps

import structlog
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HttpxInstrumentor
from opentelemetry.instrumentation.psutil import PsutilInstrumentor

from mcp_server.config import settings

# Initialize structured logging
logger = structlog.get_logger(__name__)


class ADHDMetricsCollector:
    """
    ADHD-specific metrics collector for user experience monitoring.
    
    Tracks:
    - Response time with <3s targets
    - Attention span and engagement
    - Task completion rates
    - Hyperfocus session detection
    - Crisis intervention effectiveness
    """
    
    def __init__(self):
        self.meter = metrics.get_meter(__name__)
        self._initialize_metrics()
        
    def _initialize_metrics(self):
        """Initialize ADHD-specific metrics instruments."""
        # Response time metrics
        self.response_time_histogram = self.meter.create_histogram(
            "adhd_response_time_seconds",
            description="Response time distribution for ADHD users",
            unit="s"
        )
        
        self.response_time_target_counter = self.meter.create_counter(
            "adhd_response_time_target_hits",
            description="Count of responses meeting <3s target"
        )
        
        # Attention and engagement metrics
        self.attention_span_gauge = self.meter.create_up_down_counter(
            "adhd_attention_span_seconds",
            description="Current attention span duration"
        )
        
        self.engagement_score_histogram = self.meter.create_histogram(
            "adhd_engagement_score",
            description="User engagement score (0-100)",
            unit="score"
        )
        
        # Task completion metrics
        self.task_completion_counter = self.meter.create_counter(
            "adhd_task_completions_total",
            description="Total task completions"
        )
        
        self.task_abandonment_counter = self.meter.create_counter(
            "adhd_task_abandonments_total",
            description="Total task abandonments"
        )
        
        # Hyperfocus detection
        self.hyperfocus_session_counter = self.meter.create_counter(
            "adhd_hyperfocus_sessions_total",
            description="Total hyperfocus sessions detected"
        )
        
        self.hyperfocus_duration_histogram = self.meter.create_histogram(
            "adhd_hyperfocus_duration_seconds",
            description="Hyperfocus session duration distribution",
            unit="s"
        )
        
        # Crisis intervention metrics
        self.crisis_detection_counter = self.meter.create_counter(
            "adhd_crisis_detections_total",
            description="Total crisis situations detected"
        )
        
        self.crisis_intervention_counter = self.meter.create_counter(
            "adhd_crisis_interventions_total",
            description="Total crisis interventions triggered"
        )
        
        # Cognitive load metrics
        self.cognitive_load_gauge = self.meter.create_up_down_counter(
            "adhd_cognitive_load_score",
            description="Current cognitive load score (0-100)"
        )
        
    def record_response_time(self, duration: float, endpoint: str, user_id: Optional[str] = None):
        """Record response time and check target compliance."""
        attributes = {"endpoint": endpoint}
        if user_id:
            attributes["user_id"] = user_id
            
        self.response_time_histogram.record(duration, attributes)
        
        # Track target compliance
        if duration <= settings.adhd_response_time_target:
            self.response_time_target_counter.add(1, {"endpoint": endpoint, "target_met": "true"})
        else:
            self.response_time_target_counter.add(1, {"endpoint": endpoint, "target_met": "false"})
    
    def record_attention_span(self, duration: float, user_id: str, activity_type: str):
        """Record attention span measurement."""
        self.attention_span_gauge.add(
            duration, 
            {"user_id": user_id, "activity_type": activity_type}
        )
    
    def record_engagement_score(self, score: float, user_id: str, context: str):
        """Record user engagement score."""
        self.engagement_score_histogram.record(
            score, 
            {"user_id": user_id, "context": context}
        )
    
    def record_task_completion(self, user_id: str, task_type: str, completion_time: float):
        """Record successful task completion."""
        self.task_completion_counter.add(
            1, 
            {"user_id": user_id, "task_type": task_type}
        )
    
    def record_task_abandonment(self, user_id: str, task_type: str, abandonment_reason: str):
        """Record task abandonment."""
        self.task_abandonment_counter.add(
            1, 
            {"user_id": user_id, "task_type": task_type, "reason": abandonment_reason}
        )
    
    def record_hyperfocus_session(self, user_id: str, duration: float, activity: str):
        """Record hyperfocus session detection."""
        self.hyperfocus_session_counter.add(1, {"user_id": user_id, "activity": activity})
        self.hyperfocus_duration_histogram.record(duration, {"user_id": user_id, "activity": activity})
    
    def record_crisis_detection(self, user_id: str, crisis_type: str, severity: str):
        """Record crisis situation detection."""
        self.crisis_detection_counter.add(
            1, 
            {"user_id": user_id, "crisis_type": crisis_type, "severity": severity}
        )
    
    def record_crisis_intervention(self, user_id: str, intervention_type: str, success: bool):
        """Record crisis intervention effectiveness."""
        self.crisis_intervention_counter.add(
            1, 
            {"user_id": user_id, "intervention_type": intervention_type, "success": str(success)}
        )
    
    def record_cognitive_load(self, user_id: str, load_score: float, context: str):
        """Record cognitive load measurement."""
        self.cognitive_load_gauge.add(
            load_score, 
            {"user_id": user_id, "context": context}
        )


class PerformanceMonitor:
    """
    System performance monitoring with ADHD-optimized alerting.
    """
    
    def __init__(self):
        self.meter = metrics.get_meter(__name__)
        self._initialize_performance_metrics()
        
    def _initialize_performance_metrics(self):
        """Initialize performance monitoring metrics."""
        # Database performance
        self.db_query_duration = self.meter.create_histogram(
            "database_query_duration_seconds",
            description="Database query execution time",
            unit="s"
        )
        
        self.db_connection_pool = self.meter.create_up_down_counter(
            "database_connection_pool_active",
            description="Active database connections"
        )
        
        # API endpoint performance
        self.api_request_duration = self.meter.create_histogram(
            "api_request_duration_seconds",
            description="API request processing time",
            unit="s"
        )
        
        self.api_request_count = self.meter.create_counter(
            "api_requests_total",
            description="Total API requests"
        )
        
        # System resources
        self.memory_usage = self.meter.create_up_down_counter(
            "system_memory_usage_percent",
            description="System memory usage percentage"
        )
        
        self.cpu_usage = self.meter.create_up_down_counter(
            "system_cpu_usage_percent",
            description="System CPU usage percentage"
        )
        
        # Business logic performance
        self.cognitive_loop_duration = self.meter.create_histogram(
            "cognitive_loop_duration_seconds",
            description="Cognitive loop processing time",
            unit="s"
        )
        
        self.llm_request_duration = self.meter.create_histogram(
            "llm_request_duration_seconds",
            description="LLM request processing time",
            unit="s"
        )
    
    def record_db_query(self, duration: float, query_type: str, table: Optional[str] = None):
        """Record database query performance."""
        attributes = {"query_type": query_type}
        if table:
            attributes["table"] = table
        self.db_query_duration.record(duration, attributes)
    
    def record_api_request(self, duration: float, method: str, endpoint: str, status_code: int):
        """Record API request performance."""
        self.api_request_duration.record(
            duration, 
            {"method": method, "endpoint": endpoint, "status_code": str(status_code)}
        )
        self.api_request_count.add(
            1, 
            {"method": method, "endpoint": endpoint, "status_code": str(status_code)}
        )
    
    def record_system_resources(self, memory_percent: float, cpu_percent: float):
        """Record system resource usage."""
        self.memory_usage.add(memory_percent, {})
        self.cpu_usage.add(cpu_percent, {})
    
    def record_cognitive_loop(self, duration: float, user_id: str, complexity: str):
        """Record cognitive loop performance."""
        self.cognitive_loop_duration.record(
            duration, 
            {"user_id": user_id, "complexity": complexity}
        )
    
    def record_llm_request(self, duration: float, model: str, tokens: int, user_id: str):
        """Record LLM request performance."""
        self.llm_request_duration.record(
            duration, 
            {"model": model, "tokens": str(tokens), "user_id": user_id}
        )


class MonitoringSystem:
    """
    Centralized monitoring system orchestrator.
    """
    
    def __init__(self):
        self.adhd_metrics = ADHDMetricsCollector()
        self.performance_monitor = PerformanceMonitor()
        self.tracer = trace.get_tracer(__name__)
        self._initialized = False
    
    async def initialize(self):
        """Initialize the complete monitoring system."""
        if self._initialized:
            return
        
        try:
            # Initialize Sentry if configured
            if settings.sentry_dsn:
                await self._initialize_sentry()
            
            # Initialize OpenTelemetry
            await self._initialize_opentelemetry()
            
            # Initialize instrumentation
            await self._initialize_instrumentation()
            
            self._initialized = True
            logger.info("Monitoring system initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize monitoring system", error=str(e))
            raise
    
    async def _initialize_sentry(self):
        """Initialize Sentry error tracking."""
        integrations = [
            FastApiIntegration(auto_enabling_integrations=True),
            SqlalchemyIntegration(),
            RedisIntegration(),
            HttpxIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
        ]
        
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            integrations=integrations,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            send_default_pii=False,  # Privacy-first for ADHD users
            before_send=self._filter_sensitive_data,
            before_send_transaction=self._filter_sensitive_transactions,
            release=getattr(settings, 'version', '1.0.0'),
            server_name=f"mcp-adhd-{settings.sentry_environment}"
        )
        
        logger.info("Sentry error tracking initialized", 
                   environment=settings.sentry_environment)
    
    def _filter_sensitive_data(self, event, hint):
        """Filter sensitive data from Sentry events."""
        # Remove sensitive headers
        if 'request' in event and 'headers' in event['request']:
            headers = event['request']['headers']
            sensitive_headers = ['authorization', 'cookie', 'x-api-key']
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = '[Filtered]'
        
        # Remove sensitive form data
        if 'request' in event and 'data' in event['request']:
            data = event['request']['data']
            if isinstance(data, dict):
                sensitive_fields = ['password', 'token', 'api_key', 'secret']
                for field in sensitive_fields:
                    if field in data:
                        data[field] = '[Filtered]'
        
        return event
    
    def _filter_sensitive_transactions(self, event, hint):
        """Filter sensitive data from transaction events."""
        # Skip certain endpoints from transaction tracking
        skip_endpoints = ['/health', '/metrics', '/favicon.ico']
        
        if 'transaction' in event:
            for endpoint in skip_endpoints:
                if endpoint in event['transaction']:
                    return None
        
        return event
    
    async def _initialize_opentelemetry(self):
        """Initialize OpenTelemetry distributed tracing."""
        # Set up resource
        resource = Resource.create({
            "service.name": settings.otel_service_name,
            "service.version": settings.otel_service_version,
            "service.instance.id": f"{os.getpid()}",
            "deployment.environment": settings.sentry_environment,
            "adhd.optimized": "true"
        })
        
        # Initialize tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        # Set up span processors
        if settings.otel_traces_exporter == "jaeger" and settings.otel_exporter_jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=14268,
            )
            span_processor = BatchSpanProcessor(jaeger_exporter)
            tracer_provider.add_span_processor(span_processor)
        
        # Initialize metrics provider
        if settings.otel_metrics_exporter == "prometheus":
            prometheus_reader = PrometheusMetricReader()
            metrics_provider = MeterProvider(
                resource=resource,
                metric_readers=[prometheus_reader]
            )
            metrics.set_meter_provider(metrics_provider)
        
        logger.info("OpenTelemetry initialized",
                   service_name=settings.otel_service_name,
                   traces_exporter=settings.otel_traces_exporter,
                   metrics_exporter=settings.otel_metrics_exporter)
    
    async def _initialize_instrumentation(self):
        """Initialize automatic instrumentation."""
        # FastAPI instrumentation
        FastAPIInstrumentor.instrument()
        
        # Database instrumentation
        SQLAlchemyInstrumentor.instrument(enable_commenter=True)
        
        # Redis instrumentation
        RedisInstrumentor.instrument()
        
        # HTTP client instrumentation
        HttpxInstrumentor.instrument()
        
        # System metrics instrumentation
        PsutilInstrumentor.instrument()
        
        logger.info("Automatic instrumentation initialized")
    
    @asynccontextmanager
    async def trace_operation(self, operation_name: str, **attributes):
        """Create a traced operation context."""
        with self.tracer.start_as_current_span(operation_name) as span:
            # Add ADHD-specific attributes
            span.set_attribute("adhd.operation", operation_name)
            span.set_attribute("adhd.timestamp", datetime.utcnow().isoformat())
            
            # Add custom attributes
            for key, value in attributes.items():
                span.set_attribute(f"adhd.{key}", str(value))
            
            start_time = time.time()
            try:
                yield span
            except Exception as e:
                span.set_attribute("adhd.error", True)
                span.set_attribute("adhd.error.type", type(e).__name__)
                span.set_attribute("adhd.error.message", str(e))
                raise
            finally:
                duration = time.time() - start_time
                span.set_attribute("adhd.duration", duration)
    
    async def shutdown(self):
        """Shutdown monitoring system gracefully."""
        if not self._initialized:
            return
            
        try:
            # Shutdown OpenTelemetry
            if hasattr(trace, 'get_tracer_provider'):
                tracer_provider = trace.get_tracer_provider()
                if hasattr(tracer_provider, 'shutdown'):
                    tracer_provider.shutdown()
            
            # Flush Sentry events
            if settings.sentry_dsn:
                sentry_sdk.flush(timeout=5.0)
            
            logger.info("Monitoring system shutdown complete")
            
        except Exception as e:
            logger.error("Error during monitoring system shutdown", error=str(e))


def adhd_performance_monitor(operation_name: str):
    """
    Decorator for monitoring ADHD-specific performance metrics.
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            user_id = kwargs.get('user_id') or getattr(args[0] if args else None, 'user_id', None)
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record performance metrics
                monitoring_system.adhd_metrics.record_response_time(
                    duration, operation_name, user_id
                )
                
                # Check for performance issues
                if duration > settings.adhd_response_time_target:
                    logger.warning("ADHD response time target exceeded",
                                 operation=operation_name,
                                 duration=duration,
                                 target=settings.adhd_response_time_target,
                                 user_id=user_id)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error("Operation failed",
                           operation=operation_name,
                           duration=duration,
                           error=str(e),
                           user_id=user_id)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            user_id = kwargs.get('user_id') or getattr(args[0] if args else None, 'user_id', None)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record performance metrics
                monitoring_system.adhd_metrics.record_response_time(
                    duration, operation_name, user_id
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error("Operation failed",
                           operation=operation_name,
                           duration=duration,
                           error=str(e),
                           user_id=user_id)
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global monitoring system instance
monitoring_system = MonitoringSystem()

# Export commonly used functions and classes
__all__ = [
    'MonitoringSystem',
    'ADHDMetricsCollector', 
    'PerformanceMonitor',
    'monitoring_system',
    'adhd_performance_monitor'
]