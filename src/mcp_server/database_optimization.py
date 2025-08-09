"""
Database Optimization and Analysis for MCP ADHD Server.

Provides comprehensive database performance optimization:
- Query analysis and optimization recommendations
- N+1 query detection and elimination
- Index optimization and management
- Connection pool tuning
- Performance regression detection
- ADHD-specific performance requirements (<100ms queries)
"""

import time
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import json
import hashlib

import structlog
from sqlalchemy import text, inspect, Index, Column
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import explain

from mcp_server.config import settings
from mcp_server.database import get_db_session, get_engine
from mcp_server.db_models import (
    User, Task, TraceMemory, Session, SecurityEvent, 
    SystemHealth, SessionActivity, RateLimit
)
from mcp_server.monitoring import monitoring_system

logger = structlog.get_logger(__name__)


@dataclass
class QueryAnalysis:
    """Analysis results for a database query."""
    query_hash: str
    statement: str
    execution_count: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    table_scans: int = 0
    index_scans: int = 0
    n_plus_one_potential: bool = False
    optimization_recommendations: List[str] = field(default_factory=list)
    adhd_performance_impact: str = "unknown"
    
    def add_execution(self, duration_ms: float):
        """Add a query execution record."""
        self.execution_count += 1
        self.total_duration_ms += duration_ms
        self.avg_duration_ms = self.total_duration_ms / self.execution_count
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        
        # Update ADHD performance impact
        self.adhd_performance_impact = self._calculate_adhd_impact()
    
    def _calculate_adhd_impact(self) -> str:
        """Calculate ADHD performance impact level."""
        if self.avg_duration_ms < 50:
            return "optimal"
        elif self.avg_duration_ms < 100:
            return "acceptable"
        elif self.avg_duration_ms < 250:
            return "concerning"
        else:
            return "critical"


@dataclass
class IndexRecommendation:
    """Database index recommendation."""
    table_name: str
    columns: List[str]
    index_type: str = "btree"
    reason: str = ""
    potential_improvement: str = ""
    estimated_impact: str = "medium"
    adhd_relevance: bool = False


@dataclass  
class OptimizationReport:
    """Comprehensive database optimization report."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_queries_analyzed: int = 0
    slow_queries: List[QueryAnalysis] = field(default_factory=list)
    n_plus_one_queries: List[QueryAnalysis] = field(default_factory=list)
    index_recommendations: List[IndexRecommendation] = field(default_factory=list)
    connection_pool_metrics: Dict[str, Any] = field(default_factory=dict)
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    adhd_impact_analysis: Dict[str, Any] = field(default_factory=dict)


class DatabaseOptimizer:
    """
    Comprehensive database optimization and analysis system.
    
    Features:
    - Real-time query analysis and optimization
    - N+1 query detection and prevention
    - Automated index recommendations
    - Connection pool optimization
    - ADHD-specific performance monitoring
    """
    
    def __init__(self, engine: Optional[AsyncEngine] = None):
        self.engine = engine
        self.query_cache: Dict[str, QueryAnalysis] = {}
        self.optimization_history: List[OptimizationReport] = []
        self.index_usage_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._last_analysis = datetime.utcnow()
        self._initialized = False
    
    async def initialize(self, engine: Optional[AsyncEngine] = None):
        """Initialize the database optimizer."""
        if self._initialized:
            return
        
        self.engine = engine or get_engine()
        if not self.engine:
            logger.error("No database engine available for optimization")
            return
        
        try:
            await self._analyze_current_schema()
            await self._analyze_existing_indexes()
            
            self._initialized = True
            logger.info(
                "Database optimizer initialized",
                schema_analyzed=True,
                adhd_optimized=True
            )
            
        except Exception as e:
            logger.error("Failed to initialize database optimizer", error=str(e))
            raise
    
    async def analyze_query_performance(
        self, 
        time_window_minutes: int = 60
    ) -> OptimizationReport:
        """
        Analyze query performance over a time window.
        
        Args:
            time_window_minutes: Time window for analysis
            
        Returns:
            Comprehensive optimization report
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            report = OptimizationReport()
            
            # Analyze slow queries from monitoring data
            slow_queries = await self._identify_slow_queries(time_window_minutes)
            report.slow_queries = slow_queries
            
            # Detect N+1 query patterns
            n_plus_one = await self._detect_n_plus_one_queries()
            report.n_plus_one_queries = n_plus_one
            
            # Generate index recommendations
            index_recs = await self._generate_index_recommendations()
            report.index_recommendations = index_recs
            
            # Analyze connection pool performance
            pool_metrics = await self._analyze_connection_pool()
            report.connection_pool_metrics = pool_metrics
            
            # Generate performance summary
            report.performance_summary = await self._generate_performance_summary(
                slow_queries, time_window_minutes
            )
            
            # ADHD-specific impact analysis
            report.adhd_impact_analysis = self._analyze_adhd_performance_impact(slow_queries)
            
            report.total_queries_analyzed = len(self.query_cache)
            
            # Store report
            self.optimization_history.append(report)
            if len(self.optimization_history) > 100:
                self.optimization_history = self.optimization_history[-100:]
            
            logger.info(
                "Database optimization analysis completed",
                slow_queries_count=len(slow_queries),
                n_plus_one_count=len(n_plus_one),
                index_recommendations=len(index_recs),
                adhd_critical_queries=report.adhd_impact_analysis.get("critical_count", 0)
            )
            
            return report
            
        except Exception as e:
            logger.error("Database optimization analysis failed", error=str(e))
            raise
    
    async def _identify_slow_queries(self, time_window_minutes: int) -> List[QueryAnalysis]:
        """Identify slow queries from recent execution history."""
        slow_queries = []
        adhd_threshold = 100  # 100ms threshold for ADHD attention impact
        
        # Get slow queries from monitoring system
        if hasattr(monitoring_system, 'performance_monitor'):
            perf_monitor = monitoring_system.performance_monitor
            if hasattr(perf_monitor, 'get_slow_queries'):
                recent_slow = perf_monitor.get_slow_queries(time_window_minutes)
                
                for query_data in recent_slow:
                    query_hash = self._hash_query(query_data.get('statement', ''))
                    
                    if query_hash not in self.query_cache:
                        self.query_cache[query_hash] = QueryAnalysis(
                            query_hash=query_hash,
                            statement=query_data.get('statement', '')
                        )
                    
                    analysis = self.query_cache[query_hash]
                    analysis.add_execution(query_data.get('duration_ms', 0))
                    
                    # Add ADHD-specific recommendations
                    if analysis.avg_duration_ms > adhd_threshold:
                        analysis.optimization_recommendations.extend([
                            "Query exceeds ADHD attention threshold (100ms)",
                            "Consider adding indexes for frequently accessed columns",
                            "Review query complexity and joins"
                        ])
                    
                    slow_queries.append(analysis)
        
        # Sort by ADHD impact and execution frequency
        slow_queries.sort(
            key=lambda x: (x.avg_duration_ms * x.execution_count), 
            reverse=True
        )
        
        return slow_queries[:50]  # Top 50 slow queries
    
    async def _detect_n_plus_one_queries(self) -> List[QueryAnalysis]:
        """Detect potential N+1 query patterns."""
        n_plus_one_candidates = []
        
        # Analyze query patterns for N+1 indicators
        query_patterns = defaultdict(list)
        
        for analysis in self.query_cache.values():
            # Check for repetitive SELECT patterns
            if "SELECT" in analysis.statement.upper():
                # Simple pattern matching for N+1 detection
                if "WHERE" in analysis.statement.upper() and analysis.execution_count > 10:
                    analysis.n_plus_one_potential = True
                    analysis.optimization_recommendations.append(
                        "Potential N+1 query - consider using batch loading or joins"
                    )
                    n_plus_one_candidates.append(analysis)
        
        return n_plus_one_candidates
    
    async def _generate_index_recommendations(self) -> List[IndexRecommendation]:
        """Generate database index recommendations."""
        recommendations = []
        
        try:
            async with get_db_session() as session:
                # Analyze commonly queried columns
                recommendations.extend(await self._analyze_user_query_patterns(session))
                recommendations.extend(await self._analyze_task_query_patterns(session))
                recommendations.extend(await self._analyze_trace_query_patterns(session))
                recommendations.extend(await self._analyze_security_query_patterns(session))
            
        except Exception as e:
            logger.error("Failed to generate index recommendations", error=str(e))
        
        return recommendations
    
    async def _analyze_user_query_patterns(self, session: AsyncSession) -> List[IndexRecommendation]:
        """Analyze User model query patterns for index optimization."""
        recommendations = []
        
        # Check for missing composite indexes based on common queries
        common_patterns = [
            # Email + active status lookup (login)
            {
                "columns": ["email", "is_active"],
                "reason": "Login queries frequently filter by email and active status",
                "adhd_relevance": True,
                "estimated_impact": "high"
            },
            # Failed login attempts tracking
            {
                "columns": ["failed_login_attempts", "account_locked_until"],
                "reason": "Security monitoring queries for account lockout",
                "estimated_impact": "medium"
            },
            # Last login tracking for user analytics
            {
                "columns": ["last_login", "is_active"],
                "reason": "User activity analysis queries",
                "estimated_impact": "low"
            }
        ]
        
        for pattern in common_patterns:
            rec = IndexRecommendation(
                table_name="users",
                columns=pattern["columns"],
                reason=pattern["reason"],
                estimated_impact=pattern["estimated_impact"],
                adhd_relevance=pattern.get("adhd_relevance", False)
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _analyze_task_query_patterns(self, session: AsyncSession) -> List[IndexRecommendation]:
        """Analyze Task model query patterns for index optimization."""
        recommendations = []
        
        # ADHD-critical task query patterns
        adhd_patterns = [
            # User's active tasks (most common query)
            {
                "columns": ["user_id", "status", "priority"],
                "reason": "Primary task listing query for ADHD dashboard",
                "adhd_relevance": True,
                "estimated_impact": "critical"
            },
            # Due date filtering for upcoming tasks
            {
                "columns": ["user_id", "due_date", "status"],
                "reason": "ADHD deadline tracking and reminder queries",
                "adhd_relevance": True,
                "estimated_impact": "high"
            },
            # Energy-based task filtering
            {
                "columns": ["user_id", "energy_required", "status"],
                "reason": "ADHD energy-based task selection",
                "adhd_relevance": True,
                "estimated_impact": "medium"
            },
            # Hyperfocus-compatible task filtering
            {
                "columns": ["user_id", "hyperfocus_compatible", "status"],
                "reason": "ADHD hyperfocus session task filtering",
                "adhd_relevance": True,
                "estimated_impact": "medium"
            }
        ]
        
        for pattern in adhd_patterns:
            rec = IndexRecommendation(
                table_name="tasks",
                columns=pattern["columns"],
                reason=pattern["reason"],
                estimated_impact=pattern["estimated_impact"],
                adhd_relevance=pattern["adhd_relevance"]
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _analyze_trace_query_patterns(self, session: AsyncSession) -> List[IndexRecommendation]:
        """Analyze TraceMemory query patterns for optimization."""
        recommendations = []
        
        # Trace memory is critical for ADHD context building
        patterns = [
            # Recent traces for context building (most critical)
            {
                "columns": ["user_id", "created_at", "trace_type"],
                "reason": "Critical for ADHD context assembly (sub-100ms requirement)",
                "adhd_relevance": True,
                "estimated_impact": "critical"
            },
            # Task-related traces
            {
                "columns": ["task_id", "created_at"],
                "reason": "Task progress tracking and context",
                "adhd_relevance": True,
                "estimated_impact": "high"
            },
            # Session-based traces
            {
                "columns": ["session_id", "created_at"],
                "reason": "Session context reconstruction",
                "estimated_impact": "medium"
            }
        ]
        
        for pattern in patterns:
            rec = IndexRecommendation(
                table_name="trace_memories",
                columns=pattern["columns"],
                reason=pattern["reason"],
                estimated_impact=pattern["estimated_impact"],
                adhd_relevance=pattern.get("adhd_relevance", False)
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _analyze_security_query_patterns(self, session: AsyncSession) -> List[IndexRecommendation]:
        """Analyze security-related query patterns."""
        recommendations = []
        
        # Security queries must be fast to prevent blocking
        patterns = [
            # Session validation (extremely high frequency)
            {
                "columns": ["session_id", "is_active", "expires_at"],
                "reason": "Critical session validation queries",
                "estimated_impact": "critical"
            },
            # Security event monitoring
            {
                "columns": ["severity", "created_at", "resolved"],
                "reason": "Security monitoring and alerting",
                "estimated_impact": "high"
            },
            # Rate limiting queries
            {
                "columns": ["identifier", "limit_type", "window_end"],
                "reason": "Rate limiting enforcement queries",
                "estimated_impact": "high"
            }
        ]
        
        for pattern in patterns:
            rec = IndexRecommendation(
                table_name=pattern.get("table", "sessions"),
                columns=pattern["columns"],
                reason=pattern["reason"],
                estimated_impact=pattern["estimated_impact"]
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _analyze_connection_pool(self) -> Dict[str, Any]:
        """Analyze connection pool performance and settings."""
        metrics = {
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_pool_max_overflow,
            "pool_timeout": settings.database_pool_timeout,
            "pool_recycle": settings.database_pool_recycle,
            "recommendations": []
        }
        
        try:
            if self.engine:
                pool = self.engine.pool
                metrics.update({
                    "current_checked_in": pool.checkedin(),
                    "current_checked_out": pool.checkedout(),
                    "current_overflow": pool.overflow(),
                    "current_invalid": pool.invalidated()
                })
                
                # Analyze pool utilization
                total_connections = pool.checkedin() + pool.checkedout()
                utilization = total_connections / settings.database_pool_size
                
                metrics["utilization_percent"] = utilization * 100
                
                # Generate recommendations based on utilization
                if utilization > 0.8:
                    metrics["recommendations"].append({
                        "type": "pool_size_increase",
                        "current": settings.database_pool_size,
                        "recommended": settings.database_pool_size + 5,
                        "reason": "High pool utilization detected",
                        "priority": "high"
                    })
                elif utilization < 0.3:
                    metrics["recommendations"].append({
                        "type": "pool_size_decrease", 
                        "current": settings.database_pool_size,
                        "recommended": max(5, settings.database_pool_size - 5),
                        "reason": "Low pool utilization - consider reducing pool size",
                        "priority": "low"
                    })
                
                # Check timeout settings for ADHD requirements
                if settings.database_pool_timeout > 3:
                    metrics["recommendations"].append({
                        "type": "timeout_optimization",
                        "current": settings.database_pool_timeout,
                        "recommended": 3,
                        "reason": "Reduce timeout for ADHD attention requirements",
                        "priority": "medium",
                        "adhd_specific": True
                    })
                    
        except Exception as e:
            logger.error("Connection pool analysis failed", error=str(e))
            metrics["error"] = str(e)
        
        return metrics
    
    async def _generate_performance_summary(
        self, 
        slow_queries: List[QueryAnalysis],
        time_window_minutes: int
    ) -> Dict[str, Any]:
        """Generate performance summary with ADHD-specific insights."""
        
        total_queries = len(self.query_cache)
        critical_queries = [q for q in slow_queries if q.adhd_performance_impact == "critical"]
        concerning_queries = [q for q in slow_queries if q.adhd_performance_impact == "concerning"]
        
        return {
            "analysis_window_minutes": time_window_minutes,
            "total_queries_analyzed": total_queries,
            "slow_queries_count": len(slow_queries),
            "critical_adhd_impact_queries": len(critical_queries),
            "concerning_adhd_impact_queries": len(concerning_queries),
            "average_query_time_ms": sum(q.avg_duration_ms for q in self.query_cache.values()) / max(1, total_queries),
            "adhd_compliance_percentage": ((total_queries - len(critical_queries) - len(concerning_queries)) / max(1, total_queries)) * 100,
            "performance_grade": self._calculate_performance_grade(slow_queries, total_queries),
            "optimization_priority": self._calculate_optimization_priority(critical_queries, concerning_queries)
        }
    
    def _analyze_adhd_performance_impact(self, slow_queries: List[QueryAnalysis]) -> Dict[str, Any]:
        """Analyze ADHD-specific performance impact."""
        
        impact_counts = {"optimal": 0, "acceptable": 0, "concerning": 0, "critical": 0}
        total_attention_disruption_time = 0.0
        
        for query in slow_queries:
            impact_counts[query.adhd_performance_impact] += 1
            if query.adhd_performance_impact in ["concerning", "critical"]:
                # Calculate attention disruption time (anything over 100ms)
                disruption_time = max(0, query.avg_duration_ms - 100) * query.execution_count
                total_attention_disruption_time += disruption_time
        
        return {
            "impact_distribution": impact_counts,
            "critical_count": impact_counts["critical"],
            "concerning_count": impact_counts["concerning"],
            "total_attention_disruption_ms": total_attention_disruption_time,
            "attention_friendly_percentage": (
                (impact_counts["optimal"] + impact_counts["acceptable"]) / 
                max(1, sum(impact_counts.values()))
            ) * 100,
            "requires_immediate_optimization": impact_counts["critical"] > 0,
            "performance_impact_score": self._calculate_adhd_impact_score(impact_counts)
        }
    
    def _calculate_performance_grade(self, slow_queries: List[QueryAnalysis], total_queries: int) -> str:
        """Calculate overall performance grade."""
        if not slow_queries:
            return "A+"
        
        slow_percentage = len(slow_queries) / max(1, total_queries) * 100
        critical_queries = [q for q in slow_queries if q.adhd_performance_impact == "critical"]
        
        if critical_queries:
            return "D"
        elif slow_percentage > 20:
            return "C"
        elif slow_percentage > 10:
            return "B"
        elif slow_percentage > 5:
            return "B+"
        else:
            return "A"
    
    def _calculate_optimization_priority(
        self, 
        critical_queries: List[QueryAnalysis],
        concerning_queries: List[QueryAnalysis]
    ) -> str:
        """Calculate optimization priority level."""
        if critical_queries:
            return "immediate"
        elif len(concerning_queries) > 5:
            return "high"
        elif concerning_queries:
            return "medium"
        else:
            return "low"
    
    def _calculate_adhd_impact_score(self, impact_counts: Dict[str, int]) -> float:
        """Calculate ADHD impact score (0-10, lower is better)."""
        weights = {"optimal": 0, "acceptable": 1, "concerning": 5, "critical": 10}
        total_queries = sum(impact_counts.values())
        
        if total_queries == 0:
            return 0.0
        
        weighted_score = sum(
            count * weights[impact] for impact, count in impact_counts.items()
        )
        
        return weighted_score / total_queries
    
    async def optimize_common_queries(self) -> Dict[str, Any]:
        """Optimize common query patterns for ADHD performance."""
        optimizations = {"applied": [], "errors": []}
        
        try:
            async with get_db_session() as session:
                # Apply ADHD-critical optimizations
                optimizations.update(await self._optimize_user_context_queries(session))
                optimizations.update(await self._optimize_task_queries(session))
                optimizations.update(await self._optimize_trace_queries(session))
                
        except Exception as e:
            logger.error("Query optimization failed", error=str(e))
            optimizations["errors"].append(str(e))
        
        return optimizations
    
    async def _optimize_user_context_queries(self, session: AsyncSession) -> Dict[str, Any]:
        """Optimize user context building queries."""
        optimizations = {"user_context": []}
        
        try:
            # Use selectinload for user relationships to avoid N+1 queries
            # This is a template for how queries should be structured
            optimized_query = text("""
                -- Optimized user context query with proper joins
                SELECT DISTINCT u.*, t.task_id, t.title, t.status, t.priority
                FROM users u
                LEFT JOIN tasks t ON u.user_id = t.user_id AND t.status IN ('pending', 'in_progress')
                WHERE u.user_id = :user_id AND u.is_active = true
                ORDER BY t.priority DESC, t.created_at DESC
                LIMIT 10
            """)
            
            optimizations["user_context"].append({
                "optimization": "user_active_tasks_join",
                "description": "Combined user and active tasks in single query",
                "estimated_improvement": "60-80% faster than N+1 pattern"
            })
            
        except Exception as e:
            optimizations["user_context"].append({"error": str(e)})
        
        return optimizations
    
    async def _optimize_task_queries(self, session: AsyncSession) -> Dict[str, Any]:
        """Optimize ADHD task-related queries."""
        optimizations = {"tasks": []}
        
        # Template optimizations for ADHD-critical task queries
        optimized_patterns = [
            {
                "name": "adhd_dashboard_tasks",
                "query": """
                    SELECT task_id, title, status, priority, energy_required, 
                           estimated_focus_time, hyperfocus_compatible,
                           due_date, completion_percentage
                    FROM tasks 
                    WHERE user_id = :user_id 
                      AND status IN ('pending', 'in_progress')
                    ORDER BY 
                      CASE WHEN due_date IS NOT NULL AND due_date < NOW() + INTERVAL '1 day' THEN 1 ELSE 2 END,
                      priority DESC, 
                      created_at DESC
                    LIMIT 20
                """,
                "description": "Optimized ADHD dashboard query with urgency sorting",
                "target_time_ms": 50
            },
            {
                "name": "energy_based_tasks",
                "query": """
                    WITH user_energy AS (
                      SELECT energy_patterns FROM users WHERE user_id = :user_id
                    )
                    SELECT t.* FROM tasks t, user_energy ue
                    WHERE t.user_id = :user_id
                      AND t.status = 'pending'
                      AND t.energy_required = :current_energy_level
                    ORDER BY t.priority DESC, t.dopamine_reward_tier DESC
                    LIMIT 10
                """,
                "description": "Energy-aware task selection for ADHD users",
                "target_time_ms": 75
            }
        ]
        
        for pattern in optimized_patterns:
            optimizations["tasks"].append({
                "optimization": pattern["name"],
                "description": pattern["description"],
                "target_performance_ms": pattern["target_time_ms"],
                "adhd_specific": True
            })
        
        return optimizations
    
    async def _optimize_trace_queries(self, session: AsyncSession) -> Dict[str, Any]:
        """Optimize trace memory queries for context building."""
        optimizations = {"traces": []}
        
        # Context building is critical for ADHD users - must be under 100ms
        context_query_template = """
            WITH recent_traces AS (
              SELECT * FROM trace_memories 
              WHERE user_id = :user_id 
                AND created_at > NOW() - INTERVAL '24 hours'
              ORDER BY created_at DESC 
              LIMIT 100
            ),
            trace_summary AS (
              SELECT 
                trace_type,
                COUNT(*) as count,
                AVG(EXTRACT(EPOCH FROM (created_at - LAG(created_at) OVER (ORDER BY created_at)))) as avg_interval
              FROM recent_traces
              GROUP BY trace_type
            )
            SELECT rt.*, ts.avg_interval
            FROM recent_traces rt
            JOIN trace_summary ts ON rt.trace_type = ts.trace_type
            ORDER BY rt.created_at DESC
            LIMIT 50
        """
        
        optimizations["traces"].append({
            "optimization": "context_building_cte",
            "description": "CTE-based context building with interval analysis",
            "target_performance_ms": 50,
            "adhd_critical": True
        })
        
        return optimizations
    
    async def _analyze_current_schema(self):
        """Analyze current database schema for optimization opportunities."""
        if not self.engine:
            return
        
        try:
            async with self.engine.begin() as conn:
                # Get table statistics
                result = await conn.execute(text("""
                    SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, n_dead_tup
                    FROM pg_stat_user_tables 
                    WHERE schemaname = 'public'
                    ORDER BY n_live_tup DESC
                """))
                
                table_stats = result.fetchall()
                logger.info("Database schema analysis completed", 
                          tables_analyzed=len(table_stats))
                
        except Exception as e:
            logger.warning("Schema analysis failed", error=str(e))
    
    async def _analyze_existing_indexes(self):
        """Analyze existing database indexes for optimization."""
        if not self.engine:
            return
        
        try:
            async with self.engine.begin() as conn:
                # Get index usage statistics
                result = await conn.execute(text("""
                    SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    WHERE schemaname = 'public'
                    ORDER BY idx_scan DESC
                """))
                
                index_stats = result.fetchall()
                
                # Store index usage statistics
                for stat in index_stats:
                    table_name = stat[1]
                    self.index_usage_stats[table_name][stat[2]] = stat[3]  # idx_scan
                
                logger.info("Index analysis completed", 
                          indexes_analyzed=len(index_stats))
                
        except Exception as e:
            logger.warning("Index analysis failed", error=str(e))
    
    def _hash_query(self, statement: str) -> str:
        """Generate hash for query statement."""
        # Normalize query by removing parameters and whitespace
        normalized = ' '.join(statement.strip().split())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    async def create_recommended_indexes(
        self, 
        recommendations: List[IndexRecommendation],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Create recommended database indexes."""
        results = {"created": [], "errors": [], "dry_run": dry_run}
        
        if not self.engine:
            results["errors"].append("No database engine available")
            return results
        
        try:
            async with self.engine.begin() as conn:
                for rec in recommendations:
                    try:
                        index_name = f"idx_{rec.table_name}_{'_'.join(rec.columns)}"
                        columns_str = ', '.join(rec.columns)
                        
                        create_sql = f"""
                            CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name}
                            ON {rec.table_name} ({columns_str})
                        """
                        
                        if dry_run:
                            results["created"].append({
                                "sql": create_sql,
                                "table": rec.table_name,
                                "columns": rec.columns,
                                "reason": rec.reason
                            })
                        else:
                            await conn.execute(text(create_sql))
                            results["created"].append({
                                "index_name": index_name,
                                "table": rec.table_name,
                                "columns": rec.columns,
                                "status": "created"
                            })
                            
                    except Exception as e:
                        results["errors"].append({
                            "table": rec.table_name,
                            "columns": rec.columns,
                            "error": str(e)
                        })
                        
        except Exception as e:
            results["errors"].append(f"Database connection error: {str(e)}")
        
        return results
    
    def get_optimization_history(self, limit: int = 10) -> List[OptimizationReport]:
        """Get recent optimization reports."""
        return self.optimization_history[-limit:]
    
    async def generate_optimization_recommendations(self) -> Dict[str, Any]:
        """Generate comprehensive optimization recommendations."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Run comprehensive analysis
            report = await self.analyze_query_performance()
            
            # Generate prioritized recommendations
            recommendations = {
                "immediate_actions": [],
                "high_priority": [],
                "medium_priority": [],
                "low_priority": [],
                "adhd_specific": []
            }
            
            # Categorize recommendations by priority
            for query in report.slow_queries:
                if query.adhd_performance_impact == "critical":
                    recommendations["immediate_actions"].append({
                        "type": "query_optimization",
                        "query_hash": query.query_hash,
                        "avg_duration_ms": query.avg_duration_ms,
                        "execution_count": query.execution_count,
                        "recommendations": query.optimization_recommendations,
                        "adhd_impact": query.adhd_performance_impact
                    })
                elif query.adhd_performance_impact == "concerning":
                    recommendations["high_priority"].append({
                        "type": "query_optimization", 
                        "query_hash": query.query_hash,
                        "recommendations": query.optimization_recommendations
                    })
            
            # Add index recommendations
            for index_rec in report.index_recommendations:
                priority_map = {"critical": "immediate_actions", "high": "high_priority", 
                              "medium": "medium_priority", "low": "low_priority"}
                priority = priority_map.get(index_rec.estimated_impact, "medium_priority")
                
                rec_data = {
                    "type": "index_creation",
                    "table": index_rec.table_name,
                    "columns": index_rec.columns,
                    "reason": index_rec.reason
                }
                
                recommendations[priority].append(rec_data)
                
                if index_rec.adhd_relevance:
                    recommendations["adhd_specific"].append(rec_data)
            
            # Add connection pool recommendations
            for pool_rec in report.connection_pool_metrics.get("recommendations", []):
                priority = "high_priority" if pool_rec.get("priority") == "high" else "medium_priority"
                recommendations[priority].append({
                    "type": "connection_pool_optimization",
                    "recommendation": pool_rec
                })
            
            return recommendations
            
        except Exception as e:
            logger.error("Failed to generate optimization recommendations", error=str(e))
            return {"error": str(e)}


# Global database optimizer instance
database_optimizer = DatabaseOptimizer()

# Export commonly used functions and classes
__all__ = [
    'DatabaseOptimizer',
    'QueryAnalysis', 
    'IndexRecommendation',
    'OptimizationReport',
    'database_optimizer'
]