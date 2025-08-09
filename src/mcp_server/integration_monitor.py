"""
Integration Performance Monitor for MCP ADHD Server.

Monitors cross-component data flow efficiency and provides optimization insights.
"""
import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque

import structlog
from mcp_server.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class IntegrationMetrics:
    """Metrics for integration performance tracking."""
    component_name: str
    response_time_ms: float
    success: bool
    timestamp: float
    operation_type: str = "unknown"
    data_size_bytes: int = 0
    
    
@dataclass 
class DataFlowMetrics:
    """Metrics for data flow between components."""
    source_component: str
    target_component: str
    transfer_time_ms: float
    data_size_bytes: int
    success: bool
    timestamp: float
    operation_id: str = ""


class IntegrationPerformanceMonitor:
    """
    Monitor and optimize cross-component integration performance.
    
    Tracks data flows, identifies bottlenecks, and provides optimization
    recommendations for the MCP system integration.
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.integration_metrics: deque = deque(maxlen=window_size)
        self.dataflow_metrics: deque = deque(maxlen=window_size)
        self.component_health: Dict[str, float] = {}
        self.optimization_suggestions: List[str] = []
        
    def record_component_operation(
        self,
        component_name: str,
        response_time_ms: float,
        success: bool,
        operation_type: str = "unknown",
        data_size_bytes: int = 0
    ) -> None:
        """Record a component operation for performance tracking."""
        metric = IntegrationMetrics(
            component_name=component_name,
            response_time_ms=response_time_ms,
            success=success,
            timestamp=time.time(),
            operation_type=operation_type,
            data_size_bytes=data_size_bytes
        )
        
        self.integration_metrics.append(metric)
        self._update_component_health(component_name, response_time_ms, success)
        
        # Log slow operations
        if response_time_ms > settings.database_performance_threshold:
            logger.warning(
                "Slow component operation detected",
                component=component_name,
                response_time_ms=response_time_ms,
                operation_type=operation_type
            )
    
    def record_data_flow(
        self,
        source_component: str,
        target_component: str,
        transfer_time_ms: float,
        data_size_bytes: int,
        success: bool,
        operation_id: str = ""
    ) -> None:
        """Record data flow between components."""
        metric = DataFlowMetrics(
            source_component=source_component,
            target_component=target_component,
            transfer_time_ms=transfer_time_ms,
            data_size_bytes=data_size_bytes,
            success=success,
            timestamp=time.time(),
            operation_id=operation_id
        )
        
        self.dataflow_metrics.append(metric)
        
        # Calculate data throughput
        if data_size_bytes > 0:
            throughput_mbps = (data_size_bytes / 1024 / 1024) / (transfer_time_ms / 1000)
            if throughput_mbps < 1.0:  # Less than 1 MB/s
                logger.warning(
                    "Slow data flow detected",
                    source=source_component,
                    target=target_component,
                    throughput_mbps=throughput_mbps
                )
    
    def _update_component_health(self, component: str, response_time: float, success: bool) -> None:
        """Update component health score based on recent performance."""
        # Health score based on success rate and response time
        time_score = max(0, 100 - (response_time / 10))  # Penalty for slow responses
        success_score = 100 if success else 0
        
        # Weighted average with recent performance
        current_health = self.component_health.get(component, 80.0)
        new_health = (current_health * 0.8) + ((time_score + success_score) / 2 * 0.2)
        self.component_health[component] = max(0, min(100, new_health))
    
    def get_integration_efficiency(self) -> float:
        """Calculate overall integration efficiency percentage."""
        if not self.integration_metrics:
            return 100.0
        
        recent_metrics = list(self.integration_metrics)[-20:]  # Last 20 operations
        
        success_rate = sum(1 for m in recent_metrics if m.success) / len(recent_metrics)
        avg_response_time = sum(m.response_time_ms for m in recent_metrics) / len(recent_metrics)
        
        # Efficiency formula: balance success rate with response time
        time_efficiency = max(0, 100 - (avg_response_time / 100))  # Penalty for >100ms
        overall_efficiency = (success_rate * 100 * 0.7) + (time_efficiency * 0.3)
        
        return min(100, max(0, overall_efficiency))
    
    def get_bottleneck_analysis(self) -> Dict[str, any]:
        """Analyze current integration bottlenecks."""
        if not self.integration_metrics:
            return {"status": "insufficient_data"}
        
        # Group metrics by component
        component_stats = {}
        for metric in self.integration_metrics:
            if metric.component_name not in component_stats:
                component_stats[metric.component_name] = {
                    "total_operations": 0,
                    "total_time": 0,
                    "failures": 0,
                    "avg_response_time": 0
                }
            
            stats = component_stats[metric.component_name]
            stats["total_operations"] += 1
            stats["total_time"] += metric.response_time_ms
            if not metric.success:
                stats["failures"] += 1
        
        # Calculate averages and identify bottlenecks
        bottlenecks = []
        for component, stats in component_stats.items():
            stats["avg_response_time"] = stats["total_time"] / stats["total_operations"]
            stats["error_rate"] = stats["failures"] / stats["total_operations"]
            
            # Identify bottlenecks
            if stats["avg_response_time"] > settings.database_performance_threshold:
                bottlenecks.append({
                    "component": component,
                    "issue": "high_latency",
                    "avg_response_time": stats["avg_response_time"],
                    "threshold": settings.database_performance_threshold
                })
            
            if stats["error_rate"] > 0.05:  # >5% error rate
                bottlenecks.append({
                    "component": component,
                    "issue": "high_error_rate", 
                    "error_rate": stats["error_rate"]
                })
        
        return {
            "bottlenecks": bottlenecks,
            "component_stats": component_stats,
            "overall_efficiency": self.get_integration_efficiency()
        }
    
    def get_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on current metrics."""
        recommendations = []
        analysis = self.get_bottleneck_analysis()
        
        efficiency = analysis.get("overall_efficiency", 100)
        if efficiency < settings.integration_efficiency_threshold:
            recommendations.append(
                f"⚠️ Integration efficiency ({efficiency:.1f}%) below threshold "
                f"({settings.integration_efficiency_threshold}%)"
            )
        
        for bottleneck in analysis.get("bottlenecks", []):
            component = bottleneck["component"]
            issue = bottleneck["issue"]
            
            if issue == "high_latency":
                if component == "redis":
                    recommendations.append(
                        f"🔧 Optimize Redis connection pool for {component} "
                        f"(current: {bottleneck['avg_response_time']:.1f}ms)"
                    )
                elif component == "database":
                    recommendations.append(
                        f"🔧 Consider database connection optimization for {component} "
                        f"(current: {bottleneck['avg_response_time']:.1f}ms)"
                    )
                else:
                    recommendations.append(
                        f"🔧 Investigate {component} performance issues"
                    )
            
            elif issue == "high_error_rate":
                recommendations.append(
                    f"❌ Address error rate in {component} "
                    f"({bottleneck['error_rate']*100:.1f}% failures)"
                )
        
        # Positive recommendations
        if not recommendations:
            recommendations.append("✅ Integration performance is optimal")
        
        return recommendations
    
    def get_health_summary(self) -> Dict[str, any]:
        """Get comprehensive health summary for integration monitoring."""
        return {
            "integration_efficiency": self.get_integration_efficiency(),
            "component_health": dict(self.component_health),
            "bottleneck_analysis": self.get_bottleneck_analysis(),
            "optimization_recommendations": self.get_optimization_recommendations(),
            "metrics_collected": len(self.integration_metrics),
            "dataflow_metrics": len(self.dataflow_metrics)
        }


# Global integration monitor instance
integration_monitor = IntegrationPerformanceMonitor()


# Context manager for tracking operations
class track_integration_operation:
    """Context manager to track integration operations automatically."""
    
    def __init__(self, component_name: str, operation_type: str = "unknown"):
        self.component_name = component_name
        self.operation_type = operation_type
        self.start_time = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            response_time_ms = (time.time() - self.start_time) * 1000
            success = exc_type is None
            
            integration_monitor.record_component_operation(
                component_name=self.component_name,
                response_time_ms=response_time_ms,
                success=success,
                operation_type=self.operation_type
            )


# Usage examples:
# async with track_integration_operation("redis", "cache_store"):
#     await redis_client.set(key, value)
#
# async with track_integration_operation("database", "user_query"):
#     result = await db.query(User).filter(User.id == user_id).first()