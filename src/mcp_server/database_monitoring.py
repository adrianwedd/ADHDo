"""
Database Performance Monitoring for MCP ADHD Server.

Provides comprehensive database query monitoring with ADHD-specific performance targets:
- Query execution time tracking
- Slow query detection and alerting
- Connection pool monitoring
- Database health metrics
- ADHD-optimized query performance analysis
"""

import time
import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import structlog
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

from mcp_server.monitoring import monitoring_system
from mcp_server.config import settings

logger = structlog.get_logger(__name__)


class DatabasePerformanceMonitor:
    """
    Comprehensive database performance monitoring system.
    
    Features:
    - Query execution time tracking
    - Slow query detection with ADHD-specific thresholds
    - Connection pool monitoring
    - Query pattern analysis
    - Automatic performance alerting
    """
    
    def __init__(self):
        self.slow_query_threshold = settings.database_performance_threshold / 1000.0  # Convert ms to seconds
        self.query_history = []
        self.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "failed_connections": 0,
            "connection_pool_size": 0
        }
        self._initialized = False
    
    def initialize(self, engine: Engine):
        """Initialize database monitoring with SQLAlchemy engine."""
        if self._initialized:
            return
        
        try:
            # Set up SQLAlchemy event listeners
            self._setup_query_monitoring(engine)
            self._setup_connection_monitoring(engine)
            
            self._initialized = True
            logger.info(
                "Database performance monitoring initialized",
                slow_query_threshold_ms=self.slow_query_threshold * 1000,
                adhd_optimized=True
            )
            
        except Exception as e:
            logger.error("Failed to initialize database monitoring", error=str(e))
            raise
    
    def _setup_query_monitoring(self, engine: Engine):
        """Set up query execution monitoring."""
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time."""
            context._query_start_time = time.time()
            context._query_statement = statement
            context._query_parameters = parameters
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query completion and metrics."""
            if hasattr(context, '_query_start_time'):
                duration = time.time() - context._query_start_time
                self._record_query_execution(statement, duration, parameters, success=True)
        
        @event.listens_for(engine, "handle_error")
        def handle_error(exception_context):
            """Record query errors."""
            if hasattr(exception_context, 'statement'):
                duration = getattr(exception_context, '_query_duration', 0.0)
                self._record_query_execution(
                    exception_context.statement, 
                    duration, 
                    getattr(exception_context, 'parameters', None),
                    success=False,
                    error=str(exception_context.original_exception)
                )
    
    def _setup_connection_monitoring(self, engine: Engine):
        """Set up connection pool monitoring."""
        
        @event.listens_for(engine, "connect")
        def connect(dbapi_connection, connection_record):
            """Record successful connections."""
            self.connection_stats["total_connections"] += 1
            self.connection_stats["active_connections"] += 1
            
            logger.debug("Database connection established",
                        total_connections=self.connection_stats["total_connections"],
                        active_connections=self.connection_stats["active_connections"])
        
        @event.listens_for(engine, "close")
        def close(dbapi_connection, connection_record):
            """Record connection closures."""
            self.connection_stats["active_connections"] -= 1
            
            logger.debug("Database connection closed",
                        active_connections=self.connection_stats["active_connections"])
        
        @event.listens_for(engine, "close_detached")
        def close_detached(dbapi_connection):
            """Record detached connection closures."""
            self.connection_stats["active_connections"] -= 1
        
        # Monitor connection pool if available
        if hasattr(engine.pool, 'size'):
            self.connection_stats["connection_pool_size"] = engine.pool.size()
    
    def _record_query_execution(
        self, 
        statement: str, 
        duration: float, 
        parameters: Optional[Dict],
        success: bool = True,
        error: Optional[str] = None
    ):
        """Record comprehensive query execution metrics."""
        
        # Classify query type
        query_type = self._classify_query(statement)
        table_name = self._extract_table_name(statement)
        
        # Record performance metrics
        monitoring_system.performance_monitor.record_db_query(
            duration, query_type, table_name
        )
        
        # Store query history for analysis
        query_record = {
            "timestamp": datetime.utcnow(),
            "statement": statement[:500],  # Truncate for storage
            "duration": duration,
            "query_type": query_type,
            "table": table_name,
            "success": success,
            "error": error,
            "parameters_count": len(parameters) if parameters else 0
        }
        
        self.query_history.append(query_record)
        
        # Keep only recent history (last 1000 queries)
        if len(self.query_history) > 1000:
            self.query_history = self.query_history[-1000:]
        
        # Check for slow queries
        if duration > self.slow_query_threshold:
            self._handle_slow_query(query_record)
        
        # ADHD-specific performance analysis
        if duration > 0.1:  # 100ms threshold for ADHD attention impact
            self._analyze_adhd_impact(query_record)
        
        # Log detailed query information
        log_level = "warning" if duration > self.slow_query_threshold else "debug"
        getattr(logger, log_level)(
            f"Database query executed - {'SUCCESS' if success else 'FAILED'}",
            query_type=query_type,
            table=table_name,
            duration_ms=duration * 1000,
            slow_query=duration > self.slow_query_threshold,
            adhd_impact_level=self._calculate_adhd_impact_level(duration),
            success=success,
            error=error
        )
    
    def _handle_slow_query(self, query_record: Dict):
        """Handle slow query detection and alerting."""
        
        duration_ms = query_record["duration"] * 1000
        
        logger.warning(
            "Slow database query detected",
            **query_record,
            duration_ms=duration_ms,
            threshold_ms=self.slow_query_threshold * 1000,
            performance_impact="high_adhd_disruption",
            recommended_actions=[
                "analyze_query_execution_plan",
                "check_table_indexes", 
                "consider_query_optimization",
                "monitor_database_resources"
            ]
        )
        
        # Trigger alert for extremely slow queries
        if query_record["duration"] > 1.0:  # 1 second threshold
            self._trigger_slow_query_alert(query_record)
    
    def _analyze_adhd_impact(self, query_record: Dict):
        """Analyze the ADHD-specific impact of query performance."""
        
        impact_level = self._calculate_adhd_impact_level(query_record["duration"])
        
        if impact_level in ["medium", "high", "critical"]:
            logger.info(
                "Query performance impact on ADHD users",
                query_type=query_record["query_type"],
                table=query_record["table"],
                duration_ms=query_record["duration"] * 1000,
                adhd_impact_level=impact_level,
                attention_disruption_risk=impact_level != "low",
                recommendations=self._get_adhd_optimization_recommendations(impact_level)
            )
    
    def _calculate_adhd_impact_level(self, duration: float) -> str:
        """Calculate ADHD impact level based on query duration."""
        duration_ms = duration * 1000
        
        if duration_ms < 50:
            return "none"
        elif duration_ms < 100:
            return "low" 
        elif duration_ms < 250:
            return "medium"
        elif duration_ms < 500:
            return "high"
        else:
            return "critical"
    
    def _get_adhd_optimization_recommendations(self, impact_level: str) -> List[str]:
        """Get ADHD-specific optimization recommendations."""
        base_recommendations = [
            "optimize_query_performance",
            "add_appropriate_indexes",
            "consider_query_caching"
        ]
        
        if impact_level == "high":
            base_recommendations.extend([
                "implement_query_result_caching",
                "consider_database_scaling",
                "optimize_for_adhd_attention_spans"
            ])
        elif impact_level == "critical":
            base_recommendations.extend([
                "immediate_query_optimization_required",
                "consider_architectural_changes",
                "implement_circuit_breaker_patterns",
                "add_user_feedback_for_slow_operations"
            ])
        
        return base_recommendations
    
    def _trigger_slow_query_alert(self, query_record: Dict):
        """Trigger alerting for slow queries."""
        alert_data = {
            "alert_type": "slow_database_query",
            "severity": "high" if query_record["duration"] > 2.0 else "medium",
            "query_type": query_record["query_type"],
            "table": query_record["table"],
            "duration_ms": query_record["duration"] * 1000,
            "threshold_ms": self.slow_query_threshold * 1000,
            "timestamp": query_record["timestamp"].isoformat(),
            "adhd_impact": "attention_disruption_risk"
        }
        
        logger.critical("Slow query alert triggered", **alert_data)
        
        # TODO: Integrate with external alerting system (PagerDuty, Slack, etc.)
    
    def _classify_query(self, statement: str) -> str:
        """Classify the type of database query."""
        statement_upper = statement.upper().strip()
        
        if statement_upper.startswith("SELECT"):
            return "SELECT"
        elif statement_upper.startswith("INSERT"):
            return "INSERT"
        elif statement_upper.startswith("UPDATE"):
            return "UPDATE"
        elif statement_upper.startswith("DELETE"):
            return "DELETE"
        elif statement_upper.startswith("CREATE"):
            return "CREATE"
        elif statement_upper.startswith("DROP"):
            return "DROP"
        elif statement_upper.startswith("ALTER"):
            return "ALTER"
        else:
            return "OTHER"
    
    def _extract_table_name(self, statement: str) -> Optional[str]:
        """Extract the primary table name from SQL statement."""
        try:
            statement_upper = statement.upper().strip()
            
            # Simple table name extraction
            if "FROM " in statement_upper:
                parts = statement_upper.split("FROM ")[1].split()
                return parts[0].strip('"\'`').lower()
            elif "INTO " in statement_upper:
                parts = statement_upper.split("INTO ")[1].split()
                return parts[0].strip('"\'`').lower()
            elif "UPDATE " in statement_upper:
                parts = statement_upper.split("UPDATE ")[1].split()
                return parts[0].strip('"\'`').lower()
            
            return None
            
        except Exception:
            return None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive database performance summary."""
        if not self.query_history:
            return {
                "status": "no_data",
                "message": "No query data available"
            }
        
        recent_queries = [
            q for q in self.query_history 
            if q["timestamp"] > datetime.utcnow() - timedelta(minutes=15)
        ]
        
        if not recent_queries:
            return {
                "status": "no_recent_data",
                "message": "No recent query data available"
            }
        
        # Calculate performance statistics
        durations = [q["duration"] for q in recent_queries]
        slow_queries = [q for q in recent_queries if q["duration"] > self.slow_query_threshold]
        failed_queries = [q for q in recent_queries if not q["success"]]
        
        # Query type distribution
        query_types = {}
        for query in recent_queries:
            query_type = query["query_type"]
            query_types[query_type] = query_types.get(query_type, 0) + 1
        
        # ADHD impact analysis
        adhd_impact_counts = {
            "none": 0, "low": 0, "medium": 0, "high": 0, "critical": 0
        }
        for query in recent_queries:
            impact = self._calculate_adhd_impact_level(query["duration"])
            adhd_impact_counts[impact] += 1
        
        return {
            "status": "healthy" if len(slow_queries) < 5 else "degraded",
            "time_window_minutes": 15,
            "total_queries": len(recent_queries),
            "performance_stats": {
                "avg_duration_ms": sum(durations) / len(durations) * 1000,
                "min_duration_ms": min(durations) * 1000,
                "max_duration_ms": max(durations) * 1000,
                "slow_query_count": len(slow_queries),
                "slow_query_percentage": len(slow_queries) / len(recent_queries) * 100,
                "failed_query_count": len(failed_queries),
                "success_rate": (len(recent_queries) - len(failed_queries)) / len(recent_queries) * 100
            },
            "query_distribution": query_types,
            "connection_stats": self.connection_stats,
            "adhd_impact_analysis": {
                "impact_distribution": adhd_impact_counts,
                "attention_friendly_percentage": (
                    adhd_impact_counts["none"] + adhd_impact_counts["low"]
                ) / len(recent_queries) * 100,
                "attention_disruptive_queries": adhd_impact_counts["high"] + adhd_impact_counts["critical"]
            },
            "recommendations": self._generate_performance_recommendations(recent_queries, slow_queries)
        }
    
    def _generate_performance_recommendations(
        self, 
        recent_queries: List[Dict], 
        slow_queries: List[Dict]
    ) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        slow_query_percentage = len(slow_queries) / len(recent_queries) * 100
        
        if slow_query_percentage > 10:
            recommendations.append("High percentage of slow queries detected - review database indexes")
        
        if slow_query_percentage > 20:
            recommendations.append("Critical: >20% slow queries - immediate optimization required")
        
        # Analyze query patterns
        query_types = {}
        for query in slow_queries:
            query_type = query["query_type"]
            query_types[query_type] = query_types.get(query_type, 0) + 1
        
        if query_types.get("SELECT", 0) > len(slow_queries) * 0.7:
            recommendations.append("Most slow queries are SELECTs - optimize read operations and indexes")
        
        if query_types.get("INSERT", 0) > 2:
            recommendations.append("Slow INSERT queries detected - check for index overhead or constraints")
        
        # ADHD-specific recommendations
        adhd_critical = sum(
            1 for q in recent_queries 
            if self._calculate_adhd_impact_level(q["duration"]) == "critical"
        )
        
        if adhd_critical > 0:
            recommendations.append(
                f"ADHD Impact: {adhd_critical} queries exceed attention-friendly thresholds - "
                "prioritize optimization for user experience"
            )
        
        return recommendations


def database_query_monitor(operation_name: str = None):
    """
    Decorator for monitoring database operations with ADHD-specific metrics.
    
    Usage:
        @database_query_monitor("user_lookup")
        async def get_user_by_id(user_id: str):
            # Database operation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            async with monitoring_system.trace_operation(
                f"db_operation_{op_name}",
                operation=op_name,
                function=func.__name__
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Record operation metrics
                    monitoring_system.performance_monitor.record_db_query(
                        duration, "function_call", op_name
                    )
                    
                    # Add trace attributes
                    span.set_attribute("db.operation.success", True)
                    span.set_attribute("db.operation.duration_ms", duration * 1000)
                    
                    # Check ADHD performance impact
                    impact_level = db_monitor._calculate_adhd_impact_level(duration)
                    span.set_attribute("adhd.performance_impact", impact_level)
                    
                    if duration > 0.1:  # 100ms threshold
                        logger.warning(
                            "Slow database operation detected",
                            operation=op_name,
                            duration_ms=duration * 1000,
                            adhd_impact=impact_level,
                            function=func.__name__
                        )
                    
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    
                    # Record error metrics
                    span.set_attribute("db.operation.success", False)
                    span.set_attribute("db.operation.error", str(e))
                    span.set_attribute("db.operation.duration_ms", duration * 1000)
                    
                    logger.error(
                        "Database operation failed",
                        operation=op_name,
                        duration_ms=duration * 1000,
                        error=str(e),
                        function=func.__name__,
                        adhd_impact="critical_disruption"
                    )
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record operation metrics
                monitoring_system.performance_monitor.record_db_query(
                    duration, "function_call", op_name
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "Database operation failed",
                    operation=op_name,
                    duration_ms=duration * 1000,
                    error=str(e),
                    function=func.__name__
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global database monitor instance
db_monitor = DatabasePerformanceMonitor()

# Export commonly used functions and classes
__all__ = [
    'DatabasePerformanceMonitor',
    'db_monitor',
    'database_query_monitor'
]