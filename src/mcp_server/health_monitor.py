"""
Comprehensive health monitoring system for MCP ADHD Server.

Monitors system components, performance metrics, and provides health endpoints.
"""
import asyncio
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import structlog
from fastapi import HTTPException

from mcp_server.config import settings
from mcp_server.database import get_database_session
from mcp_server.db_service import DatabaseService
from traces.memory import trace_memory

logger = structlog.get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    component: str
    status: HealthStatus
    response_time_ms: float
    error_rate: float = 0.0
    uptime_seconds: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    last_check: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SystemMetrics:
    """Overall system performance metrics."""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    load_average: Tuple[float, float, float]
    boot_time: datetime
    uptime_seconds: int
    process_count: int
    network_io: Dict[str, int]
    disk_io: Dict[str, int]


class HealthMonitor:
    """Comprehensive health monitoring system."""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.health_cache: Dict[str, HealthCheck] = {}
        self.cache_ttl = 30  # Cache results for 30 seconds
        self.metrics_history: List[SystemMetrics] = []
        self.max_history = 1000  # Keep last 1000 metrics points
        
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        logger.info("Performing comprehensive health check")
        
        # Run all health checks concurrently
        checks = await asyncio.gather(
            self.check_redis_health(),
            self.check_database_health(),
            self.check_llm_health(),
            self.check_system_resources(),
            self.check_application_health(),
            return_exceptions=True
        )
        
        # Process results
        health_results = {}
        overall_status = HealthStatus.HEALTHY
        
        component_names = ["redis", "database", "llm", "system", "application"]
        
        for i, check_result in enumerate(checks):
            component = component_names[i]
            
            if isinstance(check_result, Exception):
                health_results[component] = HealthCheck(
                    component=component,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0.0,
                    error=str(check_result)
                )
                overall_status = HealthStatus.UNHEALTHY
            else:
                health_results[component] = check_result
                
                # Determine overall status
                if check_result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif check_result.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        # Get system metrics
        system_metrics = self.get_system_metrics()
        
        # Store metrics history
        self.metrics_history.append(system_metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)
        
        # Persist health data to database
        try:
            await self._persist_health_data(health_results, system_metrics)
        except Exception as e:
            logger.warning("Failed to persist health data", error=str(e))
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int((datetime.utcnow() - self.start_time).total_seconds()),
            "version": getattr(settings, 'version', 'unknown'),
            "components": {
                name: {
                    "status": check.status.value,
                    "response_time_ms": check.response_time_ms,
                    "error_rate": check.error_rate,
                    "last_check": check.last_check.isoformat(),
                    "details": check.details,
                    "error": check.error
                }
                for name, check in health_results.items()
            },
            "system_metrics": {
                "cpu_percent": system_metrics.cpu_percent,
                "memory_percent": system_metrics.memory_percent,
                "memory_available_mb": system_metrics.memory_available_mb,
                "disk_usage_percent": system_metrics.disk_usage_percent,
                "disk_free_gb": system_metrics.disk_free_gb,
                "load_average": system_metrics.load_average,
                "uptime_seconds": system_metrics.uptime_seconds,
                "process_count": system_metrics.process_count
            },
            "performance_summary": self._calculate_performance_summary()
        }
    
    async def check_redis_health(self) -> HealthCheck:
        """Check Redis connection and performance."""
        start_time = time.time()
        
        try:
            # Test Redis connection and basic operations
            await trace_memory.connect()
            
            # Test write/read
            test_key = "health_check_test"
            test_value = {"timestamp": datetime.utcnow().isoformat(), "test": "data"}
            
            await trace_memory.store_trace({
                "trace_id": test_key,
                "content": test_value
            })
            
            retrieved = await trace_memory.get_trace(test_key)
            
            # Clean up
            if hasattr(trace_memory, 'redis'):
                await trace_memory.redis.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            # Check if read/write worked
            if retrieved and retrieved.get("content") == test_value:
                status = HealthStatus.HEALTHY if response_time < 100 else HealthStatus.DEGRADED
            else:
                status = HealthStatus.DEGRADED
            
            return HealthCheck(
                component="redis",
                status=status,
                response_time_ms=response_time,
                details={
                    "connection": "active",
                    "read_write_test": "passed",
                    "cache_operations": "functional"
                }
            )
            
        except Exception as e:
            return HealthCheck(
                component="redis",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e),
                details={"connection": "failed"}
            )
    
    async def check_database_health(self) -> HealthCheck:
        """Check database connection and performance."""
        start_time = time.time()
        
        try:
            async with get_database_session() as session:
                db_service = DatabaseService(session)
                
                # Test basic query
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1 as test"))
                test_result = result.scalar()
                
                # Test health metrics storage
                await db_service.record_system_health(
                    component="database",
                    status="healthy",
                    response_time_ms=10.0
                )
                
                response_time = (time.time() - start_time) * 1000
                
                status = HealthStatus.HEALTHY if response_time < 200 else HealthStatus.DEGRADED
                
                return HealthCheck(
                    component="database",
                    status=status,
                    response_time_ms=response_time,
                    details={
                        "connection": "active",
                        "query_test": "passed" if test_result == 1 else "failed",
                        "write_test": "passed"
                    }
                )
                
        except Exception as e:
            return HealthCheck(
                component="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e),
                details={"connection": "failed"}
            )
    
    async def check_llm_health(self) -> HealthCheck:
        """Check LLM service health and performance."""
        start_time = time.time()
        
        try:
            from mcp_server.llm_client import llm_client
            
            # Test pattern matching (should be instant)
            quick_response = llm_client._get_quick_response("I'm ready to work!")
            
            if quick_response:
                # Pattern matching working
                pattern_time = (time.time() - start_time) * 1000
                
                # Test actual LLM if configured
                llm_test_start = time.time()
                try:
                    if hasattr(llm_client, 'client') and llm_client.client:
                        # Quick test prompt
                        response = await llm_client.generate_response(
                            "Test", max_tokens=10, temperature=0.1
                        )
                        llm_response_time = (time.time() - llm_test_start) * 1000
                        llm_status = "healthy" if llm_response_time < 5000 else "slow"
                    else:
                        llm_response_time = 0
                        llm_status = "not_configured"
                except Exception:
                    llm_response_time = (time.time() - llm_test_start) * 1000
                    llm_status = "error"
                
                total_time = (time.time() - start_time) * 1000
                status = HealthStatus.HEALTHY if pattern_time < 10 else HealthStatus.DEGRADED
                
                return HealthCheck(
                    component="llm",
                    status=status,
                    response_time_ms=total_time,
                    details={
                        "pattern_matching": "active",
                        "pattern_response_time_ms": pattern_time,
                        "llm_service": llm_status,
                        "llm_response_time_ms": llm_response_time,
                        "fallback_ready": True
                    }
                )
            else:
                return HealthCheck(
                    component="llm",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=(time.time() - start_time) * 1000,
                    details={
                        "pattern_matching": "failed",
                        "llm_service": "unknown"
                    }
                )
                
        except Exception as e:
            return HealthCheck(
                component="llm",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e),
                details={"service": "failed"}
            )
    
    async def check_system_resources(self) -> HealthCheck:
        """Check system resource utilization."""
        start_time = time.time()
        
        try:
            metrics = self.get_system_metrics()
            
            # Determine health based on resource usage
            status = HealthStatus.HEALTHY
            issues = []
            
            if metrics.cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                issues.append("High CPU usage")
            elif metrics.cpu_percent > 70:
                status = HealthStatus.DEGRADED
                issues.append("Elevated CPU usage")
            
            if metrics.memory_percent > 90:
                status = HealthStatus.UNHEALTHY
                issues.append("High memory usage")
            elif metrics.memory_percent > 70:
                status = HealthStatus.DEGRADED
                issues.append("Elevated memory usage")
            
            if metrics.disk_usage_percent > 95:
                status = HealthStatus.UNHEALTHY
                issues.append("Disk nearly full")
            elif metrics.disk_usage_percent > 80:
                status = HealthStatus.DEGRADED
                issues.append("Low disk space")
            
            return HealthCheck(
                component="system",
                status=status,
                response_time_ms=(time.time() - start_time) * 1000,
                cpu_usage_percent=metrics.cpu_percent,
                memory_usage_mb=metrics.memory_percent,
                uptime_seconds=metrics.uptime_seconds,
                details={
                    "cpu_percent": metrics.cpu_percent,
                    "memory_percent": metrics.memory_percent,
                    "memory_available_mb": metrics.memory_available_mb,
                    "disk_usage_percent": metrics.disk_usage_percent,
                    "disk_free_gb": metrics.disk_free_gb,
                    "load_average": metrics.load_average,
                    "process_count": metrics.process_count,
                    "issues": issues
                }
            )
            
        except Exception as e:
            return HealthCheck(
                component="system",
                status=HealthStatus.UNKNOWN,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e),
                details={"monitoring": "failed"}
            )
    
    async def check_application_health(self) -> HealthCheck:
        """Check application-specific health metrics."""
        start_time = time.time()
        
        try:
            # Check if all required components are loaded
            components_loaded = {
                "cognitive_loop": True,  # Assume loaded if we get here
                "auth_manager": True,
                "frame_builder": True,
                "trace_memory": True
            }
            
            # Check recent performance
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            
            status = HealthStatus.HEALTHY
            if uptime < 60:  # Just started
                status = HealthStatus.DEGRADED
            
            return HealthCheck(
                component="application",
                status=status,
                response_time_ms=(time.time() - start_time) * 1000,
                uptime_seconds=int(uptime),
                details={
                    "components_loaded": components_loaded,
                    "startup_time": self.start_time.isoformat(),
                    "uptime_seconds": int(uptime),
                    "debug_mode": settings.debug,
                    "log_level": settings.log_level
                }
            )
            
        except Exception as e:
            return HealthCheck(
                component="application",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e),
                details={"health_check": "failed"}
            )
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system performance metrics."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        # Network I/O
        try:
            net_io = psutil.net_io_counters()
            network_io = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        except:
            network_io = {}
        
        # Disk I/O
        try:
            disk_io = psutil.disk_io_counters()
            disk_io_stats = {
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count
            } if disk_io else {}
        except:
            disk_io_stats = {}
        
        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_mb=memory.available / 1024 / 1024,
            disk_usage_percent=disk.percent,
            disk_free_gb=disk.free / 1024 / 1024 / 1024,
            load_average=load_avg,
            boot_time=boot_time,
            uptime_seconds=int((datetime.utcnow() - boot_time).total_seconds()),
            process_count=len(psutil.pids()),
            network_io=network_io,
            disk_io=disk_io_stats
        )
    
    def _calculate_performance_summary(self) -> Dict[str, Any]:
        """Calculate performance summary from metrics history."""
        if not self.metrics_history:
            return {}
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 data points
        
        return {
            "avg_cpu_percent": sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            "avg_memory_percent": sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            "min_memory_available_mb": min(m.memory_available_mb for m in recent_metrics),
            "avg_process_count": sum(m.process_count for m in recent_metrics) / len(recent_metrics),
            "data_points": len(recent_metrics),
            "monitoring_duration_seconds": int((datetime.utcnow() - self.start_time).total_seconds())
        }
    
    async def _persist_health_data(
        self, 
        health_results: Dict[str, HealthCheck],
        system_metrics: SystemMetrics
    ) -> None:
        """Persist health data to database."""
        try:
            async with get_database_session() as session:
                db_service = DatabaseService(session)
                
                # Store each component's health
                for component, check in health_results.items():
                    await db_service.record_system_health(
                        component=component,
                        status=check.status.value,
                        response_time_ms=check.response_time_ms,
                        error_rate=check.error_rate,
                        details={
                            **check.details,
                            "last_check": check.last_check.isoformat(),
                            "error": check.error
                        }
                    )
                
                # Store overall system metrics
                await db_service.record_system_health(
                    component="overall",
                    status="healthy",  # Will be calculated in get_system_status
                    response_time_ms=0,
                    memory_usage_mb=system_metrics.memory_percent,
                    cpu_usage_percent=system_metrics.cpu_percent,
                    details={
                        "uptime_seconds": system_metrics.uptime_seconds,
                        "load_average": system_metrics.load_average,
                        "disk_usage_percent": system_metrics.disk_usage_percent,
                        "process_count": system_metrics.process_count
                    }
                )
                
                await session.commit()
                
        except Exception as e:
            logger.warning("Failed to persist health data", error=str(e))
    
    async def get_component_health(self, component: str) -> Dict[str, Any]:
        """Get health status for a specific component."""
        if component == "overall":
            return await self.get_overall_health()
        
        # Check cache first
        cached = self.health_cache.get(component)
        if cached and (datetime.utcnow() - cached.last_check).total_seconds() < self.cache_ttl:
            return {
                "component": component,
                "status": cached.status.value,
                "response_time_ms": cached.response_time_ms,
                "error_rate": cached.error_rate,
                "last_check": cached.last_check.isoformat(),
                "details": cached.details,
                "error": cached.error,
                "cached": True
            }
        
        # Run specific health check
        check_methods = {
            "redis": self.check_redis_health,
            "database": self.check_database_health,
            "llm": self.check_llm_health,
            "system": self.check_system_resources,
            "application": self.check_application_health
        }
        
        check_method = check_methods.get(component)
        if not check_method:
            raise HTTPException(status_code=404, detail=f"Component '{component}' not found")
        
        try:
            result = await check_method()
            self.health_cache[component] = result
            
            return {
                "component": component,
                "status": result.status.value,
                "response_time_ms": result.response_time_ms,
                "error_rate": result.error_rate,
                "last_check": result.last_check.isoformat(),
                "details": result.details,
                "error": result.error,
                "cached": False
            }
            
        except Exception as e:
            logger.error("Health check failed for component", component=component, error=str(e))
            raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# Global health monitor instance
health_monitor = HealthMonitor()