"""
Prometheus metrics collection and export for MCP ADHD Server.

Provides application and business metrics for monitoring and alerting.
"""
import time
from typing import Dict, Any, Optional
from collections import defaultdict, Counter
from datetime import datetime, timedelta

import structlog
from prometheus_client import (
    Counter as PrometheusCounter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)

from mcp_server import __version__
from mcp_server.config import settings

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Comprehensive metrics collection for MCP ADHD Server."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.start_time = time.time()
        
        # Initialize Prometheus metrics
        self._init_application_metrics()
        self._init_business_metrics()
        self._init_performance_metrics()
        self._init_health_metrics()
        
        # Internal counters for business metrics
        self.user_sessions: Dict[str, float] = {}
        self.task_completions: Counter = Counter()
        self.cognitive_load_samples: list = []
        self.response_time_samples: list = []
        
        logger.info("Metrics collector initialized")
    
    def _init_application_metrics(self):
        """Initialize application-level metrics."""
        # App info
        self.app_info = Info(
            'mcp_adhd_server_info',
            'Application information',
            registry=self.registry
        )
        self.app_info.info({
            'version': __version__,
            'python_version': '3.11',
            'environment': 'development' if settings.debug else 'production'
        })
        
        # Uptime
        self.uptime_seconds = Gauge(
            'mcp_adhd_server_uptime_seconds',
            'Application uptime in seconds',
            registry=self.registry
        )
        
        # Request metrics
        self.http_requests_total = PrometheusCounter(
            'mcp_adhd_server_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'mcp_adhd_server_http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Active connections
        self.active_connections = Gauge(
            'mcp_adhd_server_active_connections',
            'Number of active connections',
            ['type'],
            registry=self.registry
        )
    
    def _init_business_metrics(self):
        """Initialize ADHD-specific business metrics."""
        # User metrics
        self.active_users = Gauge(
            'mcp_adhd_server_active_users',
            'Number of active users',
            registry=self.registry
        )
        
        self.user_sessions_total = PrometheusCounter(
            'mcp_adhd_server_user_sessions_total',
            'Total user sessions created',
            registry=self.registry
        )
        
        self.user_session_duration_seconds = Histogram(
            'mcp_adhd_server_user_session_duration_seconds',
            'User session duration',
            buckets=[30, 60, 300, 900, 1800, 3600, 7200],  # 30s to 2h
            registry=self.registry
        )
        
        # Task metrics
        self.tasks_created_total = PrometheusCounter(
            'mcp_adhd_server_tasks_created_total',
            'Total tasks created',
            ['priority', 'energy_level'],
            registry=self.registry
        )
        
        self.tasks_completed_total = PrometheusCounter(
            'mcp_adhd_server_tasks_completed_total',
            'Total tasks completed',
            ['priority', 'energy_level'],
            registry=self.registry
        )
        
        self.task_completion_time_seconds = Histogram(
            'mcp_adhd_server_task_completion_time_seconds',
            'Time from task creation to completion',
            buckets=[300, 900, 1800, 3600, 10800, 21600, 86400],  # 5m to 1d
            registry=self.registry
        )
        
        self.active_tasks = Gauge(
            'mcp_adhd_server_active_tasks',
            'Number of active tasks',
            ['priority', 'status'],
            registry=self.registry
        )
        
        # ADHD-specific metrics
        self.cognitive_loop_executions_total = PrometheusCounter(
            'mcp_adhd_server_cognitive_loop_executions_total',
            'Total cognitive loop executions',
            ['outcome'],
            registry=self.registry
        )
        
        self.cognitive_load = Gauge(
            'mcp_adhd_server_cognitive_load',
            'Current average cognitive load (0-1)',
            registry=self.registry
        )
        
        self.nudges_sent_total = PrometheusCounter(
            'mcp_adhd_server_nudges_sent_total',
            'Total nudges sent',
            ['type', 'tier', 'method'],
            registry=self.registry
        )
        
        self.nudge_effectiveness = Gauge(
            'mcp_adhd_server_nudge_effectiveness',
            'Nudge effectiveness rate (0-1)',
            ['type', 'tier'],
            registry=self.registry
        )
        
        # Pattern matching metrics
        self.pattern_matches_total = PrometheusCounter(
            'mcp_adhd_server_pattern_matches_total',
            'Total pattern matches (instant responses)',
            ['pattern_type'],
            registry=self.registry
        )
        
        self.llm_fallbacks_total = PrometheusCounter(
            'mcp_adhd_server_llm_fallbacks_total',
            'Total LLM fallback responses',
            ['reason'],
            registry=self.registry
        )
    
    def _init_performance_metrics(self):
        """Initialize performance and latency metrics."""
        # Response times
        self.response_time_seconds = Histogram(
            'mcp_adhd_server_response_time_seconds',
            'Response time for different operations',
            ['operation', 'success'],
            buckets=[0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],  # 1ms to 10s
            registry=self.registry
        )
        
        # Database metrics
        self.database_connections_active = Gauge(
            'mcp_adhd_server_database_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.database_query_duration_seconds = Histogram(
            'mcp_adhd_server_database_query_duration_seconds',
            'Database query duration',
            ['query_type'],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_operations_total = PrometheusCounter(
            'mcp_adhd_server_cache_operations_total',
            'Total cache operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        self.cache_hit_rate = Gauge(
            'mcp_adhd_server_cache_hit_rate',
            'Cache hit rate (0-1)',
            registry=self.registry
        )
        
        # Memory usage
        self.memory_usage_bytes = Gauge(
            'mcp_adhd_server_memory_usage_bytes',
            'Memory usage by component',
            ['component'],
            registry=self.registry
        )
    
    def _init_health_metrics(self):
        """Initialize health and availability metrics."""
        # Component health
        self.component_health = Gauge(
            'mcp_adhd_server_component_health',
            'Component health status (1=healthy, 0.5=degraded, 0=unhealthy)',
            ['component'],
            registry=self.registry
        )
        
        # Error rates
        self.error_rate = Gauge(
            'mcp_adhd_server_error_rate',
            'Error rate by component (0-1)',
            ['component'],
            registry=self.registry
        )
        
        # Availability
        self.availability = Gauge(
            'mcp_adhd_server_availability',
            'Service availability (0-1)',
            registry=self.registry
        )
        
        # Resource usage
        self.cpu_usage_percent = Gauge(
            'mcp_adhd_server_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.memory_usage_percent = Gauge(
            'mcp_adhd_server_memory_usage_percent',
            'Memory usage percentage',
            registry=self.registry
        )
        
        self.disk_usage_percent = Gauge(
            'mcp_adhd_server_disk_usage_percent',
            'Disk usage percentage',
            registry=self.registry
        )
    
    # === UPDATE METHODS ===
    
    def update_uptime(self):
        """Update application uptime metric."""
        self.uptime_seconds.set(time.time() - self.start_time)
    
    def record_http_request(
        self, 
        method: str, 
        endpoint: str, 
        status_code: int, 
        duration_seconds: float
    ):
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method, 
            endpoint=endpoint, 
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method, 
            endpoint=endpoint
        ).observe(duration_seconds)
    
    def record_user_session_start(self, user_id: str):
        """Record user session start."""
        self.user_sessions[user_id] = time.time()
        self.user_sessions_total.inc()
        self.active_users.set(len(self.user_sessions))
    
    def record_user_session_end(self, user_id: str):
        """Record user session end."""
        if user_id in self.user_sessions:
            duration = time.time() - self.user_sessions[user_id]
            self.user_session_duration_seconds.observe(duration)
            del self.user_sessions[user_id]
            self.active_users.set(len(self.user_sessions))
    
    def record_task_created(self, priority: int, energy_level: str):
        """Record task creation."""
        self.tasks_created_total.labels(
            priority=str(priority), 
            energy_level=energy_level
        ).inc()
    
    def record_task_completed(
        self, 
        priority: int, 
        energy_level: str, 
        creation_time: datetime
    ):
        """Record task completion."""
        self.tasks_completed_total.labels(
            priority=str(priority), 
            energy_level=energy_level
        ).inc()
        
        completion_duration = (datetime.utcnow() - creation_time).total_seconds()
        self.task_completion_time_seconds.observe(completion_duration)
        
        # Update completion counter
        key = f"{priority}_{energy_level}"
        self.task_completions[key] += 1
    
    def record_cognitive_loop_execution(self, outcome: str, duration_seconds: float):
        """Record cognitive loop execution."""
        self.cognitive_loop_executions_total.labels(outcome=outcome).inc()
        self.response_time_seconds.labels(
            operation="cognitive_loop", 
            success=str(outcome == "success")
        ).observe(duration_seconds)
    
    def update_cognitive_load(self, load: float):
        """Update current cognitive load."""
        self.cognitive_load_samples.append(load)
        # Keep only last 100 samples
        if len(self.cognitive_load_samples) > 100:
            self.cognitive_load_samples.pop(0)
        
        avg_load = sum(self.cognitive_load_samples) / len(self.cognitive_load_samples)
        self.cognitive_load.set(avg_load)
    
    def record_nudge_sent(self, nudge_type: str, tier: str, method: str):
        """Record nudge sent."""
        self.nudges_sent_total.labels(
            type=nudge_type, 
            tier=tier, 
            method=method
        ).inc()
    
    def update_nudge_effectiveness(self, nudge_type: str, tier: str, effectiveness: float):
        """Update nudge effectiveness."""
        self.nudge_effectiveness.labels(type=nudge_type, tier=tier).set(effectiveness)
    
    def record_pattern_match(self, pattern_type: str, response_time_ms: float):
        """Record pattern match (instant response)."""
        self.pattern_matches_total.labels(pattern_type=pattern_type).inc()
        self.response_time_seconds.labels(
            operation="pattern_match", 
            success="true"
        ).observe(response_time_ms / 1000.0)
    
    def record_llm_fallback(self, reason: str):
        """Record LLM fallback."""
        self.llm_fallbacks_total.labels(reason=reason).inc()
    
    def record_database_query(self, query_type: str, duration_seconds: float):
        """Record database query."""
        self.database_query_duration_seconds.labels(query_type=query_type).observe(duration_seconds)
    
    def record_cache_operation(self, operation: str, result: str):
        """Record cache operation."""
        self.cache_operations_total.labels(operation=operation, result=result).inc()
        
        # Update hit rate
        if operation == "get":
            cache_metrics = self.cache_operations_total._value._value
            hits = cache_metrics.get(("get", "hit"), 0)
            misses = cache_metrics.get(("get", "miss"), 0)
            total = hits + misses
            
            if total > 0:
                hit_rate = hits / total
                self.cache_hit_rate.set(hit_rate)
    
    def update_component_health(self, component: str, status: str):
        """Update component health status."""
        health_value = {
            "healthy": 1.0,
            "degraded": 0.5,
            "unhealthy": 0.0,
            "unknown": 0.0
        }.get(status, 0.0)
        
        self.component_health.labels(component=component).set(health_value)
    
    def update_system_metrics(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """Update system resource metrics."""
        self.cpu_usage_percent.set(cpu_percent)
        self.memory_usage_percent.set(memory_percent)
        self.disk_usage_percent.set(disk_percent)
    
    def update_active_connections(self, connection_type: str, count: int):
        """Update active connection count."""
        self.active_connections.labels(type=connection_type).set(count)
    
    def update_active_tasks(self, priority: str, status: str, count: int):
        """Update active task count."""
        self.active_tasks.labels(priority=priority, status=status).set(count)
    
    # === EXPORT METHODS ===
    
    def export_metrics(self) -> bytes:
        """Export metrics in Prometheus format."""
        # Update uptime before export
        self.update_uptime()
        
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """Get Prometheus metrics content type."""
        return CONTENT_TYPE_LATEST
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of key metrics for debugging."""
        return {
            "uptime_seconds": time.time() - self.start_time,
            "active_users": len(self.user_sessions),
            "total_sessions": self.user_sessions_total._value._value,
            "total_tasks_created": sum(
                counter._value._value 
                for counter in self.tasks_created_total._children.values()
            ) if hasattr(self.tasks_created_total, '_children') else 0,
            "total_tasks_completed": sum(
                counter._value._value 
                for counter in self.tasks_completed_total._children.values()
            ) if hasattr(self.tasks_completed_total, '_children') else 0,
            "avg_cognitive_load": (
                sum(self.cognitive_load_samples) / len(self.cognitive_load_samples)
                if self.cognitive_load_samples else 0.0
            ),
            "total_pattern_matches": sum(
                counter._value._value 
                for counter in self.pattern_matches_total._children.values()
            ) if hasattr(self.pattern_matches_total, '_children') else 0,
            "cache_hit_rate": self.cache_hit_rate._value._value,
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()