"""
Health monitoring routes - System health, metrics, and alerting.

Extracted from monolithic main.py to improve code organization and maintainability.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from typing import Optional
from datetime import datetime, timedelta

from ..health_monitor import health_monitor
from ..metrics import metrics_collector
from ..alerting import alert_manager
from ..database import (
    get_db_performance_metrics, perform_database_health_check,
    create_database_backup, validate_database_schema
)
from ..database_migration import migration_manager
from ..database_testing import database_test_suite

health_router = APIRouter(tags=["Health"])


@health_router.get("/health", summary="Basic Health Check")
async def basic_health_check():
    """Basic health check endpoint for load balancers and monitoring."""
    try:
        status = await health_monitor.get_system_health()
        return {
            "status": "healthy" if status.get("overall_health", "unknown") == "healthy" else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"  # Could be imported from __version__
        }
    except Exception:
        return {"status": "unhealthy", "timestamp": datetime.utcnow().isoformat()}


@health_router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    return await health_monitor.get_detailed_health()


@health_router.get("/health/{component}")
async def component_health_check(component: str):
    """Get health status for specific component."""
    return await health_monitor.get_component_health(component)


@health_router.get("/health/metrics/system")
async def system_metrics():
    """Get current system metrics for monitoring dashboards."""
    try:
        return {
            "cpu_usage": await health_monitor.get_cpu_usage(),
            "memory_usage": await health_monitor.get_memory_usage(),
            "disk_usage": await health_monitor.get_disk_usage(),
            "active_connections": await health_monitor.get_active_connections(),
            "response_times": await health_monitor.get_response_times(),
            "error_rates": await health_monitor.get_error_rates(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        health_monitor.record_error("system_metrics", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve system metrics")


@health_router.get("/health/history/{component}")
async def component_health_history(
    component: str, 
    hours: int = 24,
    interval: str = "1h"
):
    """Get historical health data for a component."""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        history = await health_monitor.get_component_history(
            component, 
            start_time, 
            end_time, 
            interval
        )
        
        return {
            "component": component,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": interval,
            "data_points": history
        }
    except Exception as e:
        health_monitor.record_error("component_health_history", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history for {component}")


@health_router.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    try:
        metrics_data = await metrics_collector.get_prometheus_metrics()
        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        health_monitor.record_error("prometheus_metrics", str(e))
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@health_router.get("/metrics/summary")
async def metrics_summary():
    """Human-readable metrics summary for dashboards."""
    try:
        return await metrics_collector.get_metrics_summary()
    except Exception as e:
        health_monitor.record_error("metrics_summary", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics summary")


@health_router.get("/alerts")
async def get_active_alerts():
    """Get currently active system alerts."""
    try:
        return await alert_manager.get_active_alerts()
    except Exception as e:
        health_monitor.record_error("get_active_alerts", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@health_router.get("/alerts/history")
async def get_alert_history(limit: int = 50):
    """Get alert history for analysis and debugging."""
    try:
        return await alert_manager.get_alert_history(limit=limit)
    except Exception as e:
        health_monitor.record_error("get_alert_history", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve alert history")


@health_router.get("/alerts/statistics")
async def get_alert_statistics():
    """Get alert statistics and trends."""
    try:
        return await alert_manager.get_alert_statistics()
    except Exception as e:
        health_monitor.record_error("get_alert_statistics", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve alert statistics")


@health_router.post("/alerts/check")
async def manual_alert_check():
    """Manually trigger alert rule evaluation."""
    try:
        results = await alert_manager.run_alert_checks()
        return {"status": "success", "checks_run": len(results), "results": results}
    except Exception as e:
        health_monitor.record_error("manual_alert_check", str(e))
        raise HTTPException(status_code=500, detail="Failed to run alert checks")


@health_router.post("/alerts/rules/{rule_name}/disable")
async def disable_alert_rule(rule_name: str):
    """Disable a specific alert rule."""
    try:
        success = await alert_manager.disable_rule(rule_name)
        if success:
            return {"status": "success", "message": f"Alert rule '{rule_name}' disabled"}
        else:
            raise HTTPException(status_code=404, detail=f"Alert rule '{rule_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("disable_alert_rule", str(e))
        raise HTTPException(status_code=500, detail="Failed to disable alert rule")


@health_router.post("/alerts/rules/{rule_name}/enable")
async def enable_alert_rule(rule_name: str):
    """Enable a specific alert rule."""
    try:
        success = await alert_manager.enable_rule(rule_name)
        if success:
            return {"status": "success", "message": f"Alert rule '{rule_name}' enabled"}
        else:
            raise HTTPException(status_code=404, detail=f"Alert rule '{rule_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("enable_alert_rule", str(e))
        raise HTTPException(status_code=500, detail="Failed to enable alert rule")


@health_router.get("/alerts/rules")
async def get_alert_rules():
    """Get all configured alert rules and their status."""
    try:
        return await alert_manager.get_alert_rules()
    except Exception as e:
        health_monitor.record_error("get_alert_rules", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve alert rules")


# =============================================================================
# DATABASE HEALTH AND MANAGEMENT ENDPOINTS
# =============================================================================

@health_router.get("/database/health", summary="Database Health Check")
async def database_health_check():
    """
    Comprehensive database health check for production monitoring.
    
    Checks:
    - PostgreSQL connectivity and performance
    - Connection pool health and utilization
    - Query response times (ADHD compliance)
    - Active connections and long-running queries
    - Circuit breaker status
    """
    try:
        health_status = await perform_database_health_check()
        return health_status
    except Exception as e:
        health_monitor.record_error("database_health_check", str(e))
        raise HTTPException(status_code=500, detail=f"Database health check failed: {str(e)}")


@health_router.get("/database/performance", summary="Database Performance Metrics")
async def database_performance_metrics():
    """
    Get comprehensive database performance metrics.
    
    Includes:
    - Connection pool metrics and utilization
    - Query performance statistics (avg, max, p95)
    - ADHD compliance metrics (<100ms queries)
    - Circuit breaker status and statistics
    - Slow query analysis
    """
    try:
        performance_metrics = await get_db_performance_metrics()
        return performance_metrics
    except Exception as e:
        health_monitor.record_error("database_performance_metrics", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve database metrics: {str(e)}")


@health_router.get("/database/schema", summary="Database Schema Validation")
async def database_schema_validation():
    """
    Validate database schema integrity and performance optimization.
    
    Checks:
    - Table existence and structure
    - Index optimization for ADHD performance requirements
    - Constraint validation
    - Performance-critical schema elements
    """
    try:
        schema_status = await validate_database_schema()
        return schema_status
    except Exception as e:
        health_monitor.record_error("database_schema_validation", str(e))
        raise HTTPException(status_code=500, detail=f"Schema validation failed: {str(e)}")


@health_router.post("/database/backup", summary="Create Database Backup")
async def create_database_backup_endpoint():
    """
    Create database backup with point-in-time recovery capability.
    
    Features:
    - PostgreSQL logical dump
    - Backup validation and integrity checks
    - Automated backup status tracking
    - Production-safe backup procedures
    """
    try:
        backup_result = await create_database_backup()
        return backup_result
    except Exception as e:
        health_monitor.record_error("create_database_backup", str(e))
        raise HTTPException(status_code=500, detail=f"Backup creation failed: {str(e)}")


@health_router.get("/database/migrations/status", summary="Migration Status")
async def migration_status():
    """
    Get database migration status and pending migrations.
    
    Information includes:
    - Current database schema version
    - Pending migrations
    - Migration history
    - Migration safety status
    """
    try:
        await migration_manager.initialize()
        status = await migration_manager.get_migration_status()
        return status
    except Exception as e:
        health_monitor.record_error("migration_status", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get migration status: {str(e)}")


@health_router.post("/database/migrations/run", summary="Run Database Migrations")
async def run_database_migrations(target_revision: Optional[str] = None):
    """
    Run database migrations with comprehensive monitoring.
    
    Features:
    - Production-safe migration execution
    - Performance monitoring during migration
    - Automatic rollback capability
    - Migration validation and testing
    
    Args:
        target_revision: Specific revision to migrate to (default: head)
    """
    try:
        await migration_manager.initialize()
        
        # Validate migration safety first
        safety_check = await migration_manager.validate_migration_safety(target_revision or "head")
        if not safety_check.get("safe_to_migrate", False):
            return {
                "status": "BLOCKED",
                "message": "Migration blocked by safety checks",
                "safety_report": safety_check
            }
        
        migration_result = await migration_manager.run_migrations(target_revision)
        return migration_result
    except Exception as e:
        health_monitor.record_error("run_database_migrations", str(e))
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


@health_router.post("/database/migrations/rollback", summary="Rollback Database Migration")
async def rollback_database_migration(target_revision: str):
    """
    Rollback database to specific revision with safety checks.
    
    WARNING: This operation may result in data loss. Use with caution.
    
    Args:
        target_revision: Revision to rollback to
    """
    try:
        await migration_manager.initialize()
        rollback_result = await migration_manager.rollback_migration(target_revision)
        return rollback_result
    except Exception as e:
        health_monitor.record_error("rollback_database_migration", str(e))
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")


@health_router.get("/database/migrations/safety/{target_revision}", summary="Validate Migration Safety")
async def validate_migration_safety(target_revision: str):
    """
    Validate migration safety before execution.
    
    Checks:
    - Database health status
    - Active connections and load
    - Estimated downtime
    - ADHD-specific considerations
    - Safety recommendations
    
    Args:
        target_revision: Revision to validate migration safety for
    """
    try:
        await migration_manager.initialize()
        safety_report = await migration_manager.validate_migration_safety(target_revision)
        return safety_report
    except Exception as e:
        health_monitor.record_error("validate_migration_safety", str(e))
        raise HTTPException(status_code=500, detail=f"Safety validation failed: {str(e)}")


@health_router.post("/database/test/full-suite", summary="Run Full Database Test Suite")
async def run_full_database_test_suite():
    """
    Run comprehensive database test suite for production readiness.
    
    Tests include:
    - PostgreSQL enforcement validation
    - Connection pool performance
    - ADHD performance requirements (<100ms queries)
    - Circuit breaker functionality
    - Load testing (1000+ concurrent users)
    - Data integrity validation
    - Backup and recovery procedures
    - Migration system testing
    """
    try:
        test_results = await database_test_suite.run_full_test_suite()
        return test_results
    except Exception as e:
        health_monitor.record_error("run_full_database_test_suite", str(e))
        raise HTTPException(status_code=500, detail=f"Database test suite failed: {str(e)}")


@health_router.post("/database/test/adhd-performance", summary="Test ADHD Performance Requirements")
async def test_adhd_performance_requirements():
    """
    Test database performance against ADHD-specific requirements.
    
    Requirements tested:
    - Query response times <100ms (95th percentile)
    - Connection establishment <50ms
    - Concurrent user simulation (ADHD multitasking patterns)
    - Circuit breaker impact on ADHD users
    """
    try:
        performance_test = await database_test_suite._test_adhd_performance_requirements()
        return performance_test
    except Exception as e:
        health_monitor.record_error("test_adhd_performance_requirements", str(e))
        raise HTTPException(status_code=500, detail=f"ADHD performance test failed: {str(e)}")


@health_router.post("/database/test/connection-pooling", summary="Test Connection Pooling")
async def test_connection_pooling():
    """
    Test connection pooling configuration and performance.
    
    Tests:
    - Pool size and configuration validation
    - Concurrent connection handling
    - Pool utilization and overflow handling
    - Connection recycling and cleanup
    """
    try:
        pool_test = await database_test_suite._test_connection_pooling()
        return pool_test
    except Exception as e:
        health_monitor.record_error("test_connection_pooling", str(e))
        raise HTTPException(status_code=500, detail=f"Connection pooling test failed: {str(e)}")


@health_router.post("/database/test/load-performance", summary="Test Load Performance")
async def test_load_performance():
    """
    Test database performance under load.
    
    Load tests:
    - 100 concurrent operations
    - Connection pool stress testing
    - Performance degradation analysis
    - Success rate monitoring
    """
    try:
        load_test = await database_test_suite._test_load_performance()
        return load_test
    except Exception as e:
        health_monitor.record_error("test_load_performance", str(e))
        raise HTTPException(status_code=500, detail=f"Load performance test failed: {str(e)}")