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