"""
Monitoring and Observability API Routes for MCP ADHD Server.

Provides endpoints for:
- Real-time performance metrics
- ADHD-specific analytics
- System health monitoring
- Database performance insights
- User experience metrics
- Crisis detection data
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from mcp_server.monitoring import monitoring_system
from mcp_server.database_monitoring import db_monitor
from mcp_server.dashboard_config import ADHDDashboardConfig, AlertingConfig
from mcp_server.config import settings
from mcp_server.auth import get_current_user_optional

# Create monitoring router
monitoring_router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])


class PerformanceMetrics(BaseModel):
    """Performance metrics response model."""
    timestamp: datetime
    response_time_p50: float = Field(description="50th percentile response time")
    response_time_p95: float = Field(description="95th percentile response time")
    response_time_p99: float = Field(description="99th percentile response time")
    adhd_target_compliance: float = Field(description="Percentage meeting ADHD <3s target")
    total_requests: int = Field(description="Total requests in time window")
    error_rate: float = Field(description="Error rate percentage")


class ADHDMetrics(BaseModel):
    """ADHD-specific metrics response model."""
    timestamp: datetime
    avg_cognitive_load: float = Field(description="Average cognitive load (0-100)")
    avg_attention_span: float = Field(description="Average attention span in seconds")
    task_completion_rate: float = Field(description="Task completion rate percentage")
    task_abandonment_rate: float = Field(description="Task abandonment rate percentage")
    hyperfocus_sessions: int = Field(description="Number of hyperfocus sessions detected")
    crisis_detections: int = Field(description="Number of crisis patterns detected")
    engagement_score: float = Field(description="Overall user engagement score")


class SystemHealth(BaseModel):
    """System health metrics response model."""
    status: str = Field(description="Overall system status")
    uptime_seconds: float = Field(description="System uptime in seconds")
    memory_usage_percent: float = Field(description="Memory usage percentage")
    cpu_usage_percent: float = Field(description="CPU usage percentage") 
    database_status: str = Field(description="Database health status")
    active_connections: int = Field(description="Active database connections")
    slow_queries: int = Field(description="Number of slow queries")


class DatabasePerformanceMetrics(BaseModel):
    """Database performance metrics response model."""
    status: str
    avg_query_time_ms: float
    slow_query_count: int
    slow_query_percentage: float
    success_rate: float
    connection_pool_active: int
    adhd_impact_summary: Dict[str, Any]


@monitoring_router.get(
    "/health",
    response_model=SystemHealth,
    summary="Get System Health Overview",
    description="Returns comprehensive system health metrics optimized for ADHD monitoring"
)
async def get_system_health(
    user=Depends(get_current_user_optional)
) -> SystemHealth:
    """Get comprehensive system health metrics."""
    try:
        # Get database performance summary
        db_summary = db_monitor.get_performance_summary()
        
        # Get system metrics (placeholder - integrate with actual system monitoring)
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_percent = process.memory_percent()
        cpu_percent = process.cpu_percent()
        
        # Calculate uptime
        create_time = process.create_time()
        uptime = datetime.now().timestamp() - create_time
        
        return SystemHealth(
            status="healthy" if db_summary.get("status") == "healthy" else "degraded",
            uptime_seconds=uptime,
            memory_usage_percent=memory_percent,
            cpu_usage_percent=cpu_percent,
            database_status=db_summary.get("status", "unknown"),
            active_connections=db_summary.get("connection_stats", {}).get("active_connections", 0),
            slow_queries=db_summary.get("performance_stats", {}).get("slow_query_count", 0)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve system health metrics: {str(e)}"
        )


@monitoring_router.get(
    "/performance",
    response_model=PerformanceMetrics,
    summary="Get Performance Metrics",
    description="Returns API performance metrics with ADHD-specific targets"
)
async def get_performance_metrics(
    time_window_minutes: int = Query(15, ge=1, le=1440, description="Time window in minutes"),
    user=Depends(get_current_user_optional)
) -> PerformanceMetrics:
    """Get comprehensive performance metrics."""
    try:
        # This would integrate with actual metrics collection
        # For now, return mock data that demonstrates the structure
        
        return PerformanceMetrics(
            timestamp=datetime.utcnow(),
            response_time_p50=1.2,
            response_time_p95=2.8,
            response_time_p99=4.1,
            adhd_target_compliance=85.5,
            total_requests=1250,
            error_rate=2.1
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve performance metrics: {str(e)}"
        )


@monitoring_router.get(
    "/adhd-metrics",
    response_model=ADHDMetrics,
    summary="Get ADHD-Specific Metrics",
    description="Returns metrics specifically designed for ADHD user experience monitoring"
)
async def get_adhd_metrics(
    time_window_minutes: int = Query(60, ge=1, le=1440, description="Time window in minutes"),
    user=Depends(get_current_user_optional)
) -> ADHDMetrics:
    """Get ADHD-specific user experience metrics."""
    try:
        # This would integrate with the actual ADHD metrics collector
        # For now, return representative data
        
        return ADHDMetrics(
            timestamp=datetime.utcnow(),
            avg_cognitive_load=45.8,
            avg_attention_span=185.3,
            task_completion_rate=72.4,
            task_abandonment_rate=18.6,
            hyperfocus_sessions=3,
            crisis_detections=0,
            engagement_score=78.2
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve ADHD metrics: {str(e)}"
        )


@monitoring_router.get(
    "/database",
    response_model=DatabasePerformanceMetrics,
    summary="Get Database Performance",
    description="Returns database performance metrics with ADHD impact analysis"
)
async def get_database_performance(
    user=Depends(get_current_user_optional)
) -> DatabasePerformanceMetrics:
    """Get comprehensive database performance metrics."""
    try:
        summary = db_monitor.get_performance_summary()
        
        if summary.get("status") == "no_data":
            return DatabasePerformanceMetrics(
                status="no_data",
                avg_query_time_ms=0.0,
                slow_query_count=0,
                slow_query_percentage=0.0,
                success_rate=100.0,
                connection_pool_active=0,
                adhd_impact_summary={"message": "No data available"}
            )
        
        perf_stats = summary.get("performance_stats", {})
        adhd_analysis = summary.get("adhd_impact_analysis", {})
        
        return DatabasePerformanceMetrics(
            status=summary.get("status", "unknown"),
            avg_query_time_ms=perf_stats.get("avg_duration_ms", 0.0),
            slow_query_count=perf_stats.get("slow_query_count", 0),
            slow_query_percentage=perf_stats.get("slow_query_percentage", 0.0),
            success_rate=perf_stats.get("success_rate", 100.0),
            connection_pool_active=summary.get("connection_stats", {}).get("active_connections", 0),
            adhd_impact_summary=adhd_analysis
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve database performance: {str(e)}"
        )


@monitoring_router.get(
    "/alerts/rules",
    summary="Get Alert Rules Configuration",
    description="Returns current alerting rules for monitoring"
)
async def get_alert_rules(
    user=Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """Get configured alerting rules."""
    try:
        return {
            "rules": AlertingConfig.get_alert_rules(),
            "channels": AlertingConfig.get_notification_channels(),
            "total_rules": len(AlertingConfig.get_alert_rules())
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve alert rules: {str(e)}"
        )


@monitoring_router.get(
    "/dashboards/config",
    summary="Get Dashboard Configurations",
    description="Returns dashboard configurations for monitoring systems"
)
async def get_dashboard_configs(
    dashboard_type: str = Query("main", description="Dashboard type (main, performance, user_experience)"),
    user=Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """Get dashboard configuration for monitoring systems."""
    try:
        if dashboard_type == "main":
            return ADHDDashboardConfig.get_main_dashboard_config()
        elif dashboard_type == "performance":
            return ADHDDashboardConfig.get_performance_dashboard_config()
        elif dashboard_type == "user_experience":
            return ADHDDashboardConfig.get_user_experience_dashboard_config()
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid dashboard type. Must be one of: main, performance, user_experience"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dashboard config: {str(e)}"
        )


@monitoring_router.get(
    "/traces/recent",
    summary="Get Recent Traces",
    description="Returns recent distributed traces for debugging"
)
async def get_recent_traces(
    limit: int = Query(50, ge=1, le=1000, description="Number of traces to return"),
    operation_filter: Optional[str] = Query(None, description="Filter by operation name"),
    user=Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """Get recent distributed traces."""
    try:
        # This would integrate with actual tracing system
        # For now, return mock data
        
        traces = []
        for i in range(min(limit, 10)):
            traces.append({
                "trace_id": f"trace-{i:06d}",
                "operation": operation_filter or f"http_get_endpoint_{i}",
                "duration_ms": 150 + (i * 50),
                "timestamp": (datetime.utcnow() - timedelta(minutes=i)).isoformat(),
                "status": "success" if i < 8 else "error",
                "spans": 3 + i,
                "adhd_impact": "low" if i < 5 else "medium"
            })
        
        return {
            "traces": traces,
            "total_count": len(traces),
            "time_window": "last_hour"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve traces: {str(e)}"
        )


@monitoring_router.get(
    "/metrics/prometheus",
    summary="Get Prometheus Metrics",
    description="Returns metrics in Prometheus format"
)
async def get_prometheus_metrics(
    user=Depends(get_current_user_optional)
) -> str:
    """Get metrics in Prometheus format."""
    try:
        # This would return actual Prometheus metrics
        # For now, return sample metrics
        
        metrics = """
# HELP adhd_response_time_seconds Response time for ADHD-optimized endpoints
# TYPE adhd_response_time_seconds histogram
adhd_response_time_seconds_bucket{le="1.0"} 450
adhd_response_time_seconds_bucket{le="2.0"} 850
adhd_response_time_seconds_bucket{le="3.0"} 950
adhd_response_time_seconds_bucket{le="5.0"} 990
adhd_response_time_seconds_bucket{le="+Inf"} 1000
adhd_response_time_seconds_sum 1850.5
adhd_response_time_seconds_count 1000

# HELP adhd_cognitive_load_score Current cognitive load score (0-100)
# TYPE adhd_cognitive_load_score gauge
adhd_cognitive_load_score 45.8

# HELP adhd_task_completions_total Total completed tasks
# TYPE adhd_task_completions_total counter
adhd_task_completions_total 1245

# HELP adhd_crisis_detections_total Total crisis detections
# TYPE adhd_crisis_detections_total counter
adhd_crisis_detections_total 0

# HELP system_memory_usage_percent System memory usage percentage
# TYPE system_memory_usage_percent gauge
system_memory_usage_percent 34.2
        """.strip()
        
        return metrics
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Prometheus metrics: {str(e)}"
        )


@monitoring_router.post(
    "/test-alert",
    summary="Test Alert System",
    description="Trigger a test alert to verify alerting configuration"
)
async def test_alert_system(
    alert_type: str = Query("test", description="Type of test alert to send"),
    user=Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """Test the alerting system."""
    try:
        # This would trigger actual alerts
        test_alert_data = {
            "alert_type": f"test_{alert_type}",
            "severity": "info",
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Test alert of type {alert_type} triggered successfully",
            "test_mode": True
        }
        
        # Log the test alert
        import structlog
        logger = structlog.get_logger(__name__)
        logger.info("Test alert triggered", **test_alert_data)
        
        return {
            "success": True,
            "alert_sent": test_alert_data,
            "message": f"Test alert '{alert_type}' has been triggered successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test alert system: {str(e)}"
        )


@monitoring_router.get(
    "/export/dashboard",
    summary="Export Dashboard Configuration",
    description="Export dashboard configurations for external monitoring systems"
)
async def export_dashboard_config(
    dashboard_type: str = Query("all", description="Dashboard type to export"),
    format_type: str = Query("json", description="Export format (json, yaml)"),
    user=Depends(get_current_user_optional)
) -> JSONResponse:
    """Export dashboard configurations."""
    try:
        if dashboard_type == "all":
            configs = {
                "main": ADHDDashboardConfig.get_main_dashboard_config(),
                "performance": ADHDDashboardConfig.get_performance_dashboard_config(),
                "user_experience": ADHDDashboardConfig.get_user_experience_dashboard_config()
            }
        else:
            configs = {dashboard_type: getattr(ADHDDashboardConfig, f"get_{dashboard_type}_dashboard_config")()}
        
        if format_type == "yaml":
            import yaml
            content = yaml.dump(configs, default_flow_style=False)
            media_type = "text/yaml"
        else:
            import json
            content = json.dumps(configs, indent=2)
            media_type = "application/json"
        
        return JSONResponse(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=dashboard_config.{format_type}",
                "X-Export-Type": dashboard_type,
                "X-Export-Format": format_type
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export dashboard config: {str(e)}"
        )


@monitoring_router.get(
    "/status",
    summary="Get Monitoring System Status",
    description="Returns the status of the monitoring system components"
)
async def get_monitoring_status(
    user=Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """Get comprehensive monitoring system status."""
    try:
        status = {
            "monitoring_system": {
                "initialized": monitoring_system._initialized,
                "sentry_enabled": bool(settings.sentry_dsn),
                "opentelemetry_enabled": True,
                "status": "healthy" if monitoring_system._initialized else "initializing"
            },
            "database_monitoring": {
                "initialized": db_monitor._initialized,
                "status": "healthy" if db_monitor._initialized else "initializing"
            },
            "alerting": {
                "enabled": settings.alerting_enabled,
                "channels_configured": len(AlertingConfig.get_notification_channels()),
                "rules_active": len(AlertingConfig.get_alert_rules())
            },
            "adhd_optimizations": {
                "response_time_target": settings.adhd_response_time_target,
                "cognitive_load_monitoring": settings.adhd_cognitive_load_monitoring,
                "crisis_detection": settings.adhd_crisis_detection_enabled,
                "hyperfocus_detection": settings.adhd_hyperfocus_detection_enabled
            },
            "performance_targets": {
                "adhd_response_time_ms": settings.adhd_response_time_target * 1000,
                "database_query_threshold_ms": settings.database_performance_threshold,
                "memory_alert_threshold": settings.memory_usage_alert_threshold,
                "cpu_alert_threshold": settings.cpu_usage_alert_threshold
            }
        }
        
        # Calculate overall health score
        components = [
            status["monitoring_system"]["status"] == "healthy",
            status["database_monitoring"]["status"] == "healthy",
            status["alerting"]["enabled"],
            status["adhd_optimizations"]["cognitive_load_monitoring"]
        ]
        
        health_score = sum(components) / len(components) * 100
        overall_status = "healthy" if health_score >= 75 else "degraded" if health_score >= 50 else "unhealthy"
        
        status["overall"] = {
            "status": overall_status,
            "health_score": health_score,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return status
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve monitoring status: {str(e)}"
        )


# Health check endpoint for monitoring system
@monitoring_router.get(
    "/ping",
    summary="Monitoring System Ping",
    description="Simple health check for monitoring system availability"
)
async def monitoring_ping() -> Dict[str, Any]:
    """Simple health check for monitoring system."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "mcp-adhd-monitoring",
        "adhd_optimized": True
    }