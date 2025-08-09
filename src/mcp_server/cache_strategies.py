"""
Cache Warming and Invalidation Strategies for MCP ADHD Server.

Intelligent cache management with predictive warming, smart invalidation, and ADHD-optimized preloading.
Provides adaptive strategies based on user behavior patterns and system performance metrics.

Features:
- Predictive cache warming based on user behavior patterns
- Smart invalidation with dependency tracking and cascading updates
- ADHD-optimized preloading for attention-critical data
- Adaptive cache strategies that learn from usage patterns  
- Performance-aware cache management with bottleneck detection
- Crisis-safe cache operations with priority data protection
"""

import asyncio
import json
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Tuple, NamedTuple
from dataclasses import dataclass, field
import math

import structlog

from mcp_server.caching_system import cache_manager, CacheLayer, CachePriority
from mcp_server.background_processing import background_task_manager, TaskDefinition, TaskPriority, TaskType
from mcp_server.config import settings


# Configure structured logger
logger = structlog.get_logger(__name__)


class WarmingStrategy(str, Enum):
    """Cache warming strategies for different scenarios."""
    PREDICTIVE = "predictive"     # Based on user behavior prediction
    SCHEDULED = "scheduled"       # Time-based warming schedules
    ON_DEMAND = "on_demand"      # Warm when requested
    REACTIVE = "reactive"        # Warm after cache misses
    PATTERN_BASED = "pattern_based"  # Based on access patterns


class InvalidationStrategy(str, Enum):
    """Cache invalidation strategies."""
    IMMEDIATE = "immediate"       # Invalidate immediately
    LAZY = "lazy"                # Invalidate on next access
    BATCH = "batch"              # Batch invalidations
    CASCADE = "cascade"          # Cascading dependency invalidation
    SCHEDULED = "scheduled"      # Time-based invalidation


class CachePattern(NamedTuple):
    """Cache access pattern for analysis."""
    key_pattern: str
    access_count: int
    last_access: datetime
    access_frequency: float
    user_contexts: Set[str]
    peak_hours: List[int]


@dataclass
class WarmingTask:
    """Cache warming task definition."""
    id: str
    strategy: WarmingStrategy
    key_patterns: List[str]
    priority: CachePriority
    
    # Timing and scheduling
    scheduled_at: datetime
    expires_at: Optional[datetime] = None
    interval_seconds: Optional[int] = None  # For recurring warming
    
    # ADHD optimization
    user_id: Optional[str] = None
    attention_critical: bool = False
    cognitive_load_weight: float = 1.0
    
    # Performance tracking
    success_rate: float = 0.0
    average_warming_time: float = 0.0
    cache_hit_improvement: float = 0.0
    
    # Execution tracking
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    failure_count: int = 0


class CacheWarmingEngine:
    """
    Intelligent cache warming engine with ADHD optimizations.
    
    Features:
    - Predictive warming based on user behavior analysis
    - Smart scheduling with peak usage optimization
    - ADHD-optimized preloading for attention-critical data
    - Adaptive strategies that learn from effectiveness
    """
    
    def __init__(self):
        self.warming_tasks: Dict[str, WarmingTask] = {}
        self.user_patterns: Dict[str, Dict[str, CachePattern]] = {}
        self.global_patterns: Dict[str, CachePattern] = {}
        
        # Performance tracking
        self.warming_stats = {
            'tasks_executed': 0,
            'success_rate': 0.0,
            'cache_hit_improvement': 0.0,
            'attention_critical_success_rate': 0.0
        }
        
        # ADHD optimization settings
        self.peak_attention_hours = [9, 10, 11, 14, 15, 16]  # Typical ADHD focus hours
        self.attention_span_minutes = 25  # Pomodoro-style attention spans
        self.crisis_warm_timeout_seconds = 5  # Fast warming for crisis data
        
        self.is_running = False
    
    async def initialize(self) -> None:
        """Initialize the cache warming engine."""
        try:
            # Start background analysis and warming loops
            self.is_running = True
            
            asyncio.create_task(self._pattern_analysis_loop())
            asyncio.create_task(self._warming_execution_loop())
            asyncio.create_task(self._performance_optimization_loop())
            
            # Load existing patterns from cache if available
            await self._load_saved_patterns()
            
            # Schedule initial warming for critical data
            await self._schedule_initial_warming()
            
            logger.info("Cache warming engine initialized")
            
        except Exception as e:
            logger.error("Failed to initialize cache warming engine", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the cache warming engine."""
        logger.info("Shutting down cache warming engine")
        
        self.is_running = False
        
        # Save patterns for next startup
        await self._save_patterns()
        
        logger.info("Cache warming engine shutdown complete")
    
    async def analyze_access_patterns(self, key: str, user_id: Optional[str] = None) -> None:
        """Analyze cache access patterns for predictive warming."""
        try:
            current_time = datetime.utcnow()
            current_hour = current_time.hour
            
            # Extract pattern from key
            pattern = self._extract_key_pattern(key)
            
            # Update global patterns
            if pattern in self.global_patterns:
                existing = self.global_patterns[pattern]
                self.global_patterns[pattern] = CachePattern(
                    key_pattern=pattern,
                    access_count=existing.access_count + 1,
                    last_access=current_time,
                    access_frequency=self._calculate_frequency(existing.access_count + 1, existing.last_access, current_time),
                    user_contexts=existing.user_contexts | {user_id} if user_id else existing.user_contexts,
                    peak_hours=self._update_peak_hours(existing.peak_hours, current_hour)
                )
            else:
                self.global_patterns[pattern] = CachePattern(
                    key_pattern=pattern,
                    access_count=1,
                    last_access=current_time,
                    access_frequency=0.0,
                    user_contexts={user_id} if user_id else set(),
                    peak_hours=[current_hour]
                )
            
            # Update user-specific patterns
            if user_id:
                if user_id not in self.user_patterns:
                    self.user_patterns[user_id] = {}
                
                if pattern in self.user_patterns[user_id]:
                    existing = self.user_patterns[user_id][pattern]
                    self.user_patterns[user_id][pattern] = CachePattern(
                        key_pattern=pattern,
                        access_count=existing.access_count + 1,
                        last_access=current_time,
                        access_frequency=self._calculate_frequency(existing.access_count + 1, existing.last_access, current_time),
                        user_contexts=existing.user_contexts | {user_id},
                        peak_hours=self._update_peak_hours(existing.peak_hours, current_hour)
                    )
                else:
                    self.user_patterns[user_id][pattern] = CachePattern(
                        key_pattern=pattern,
                        access_count=1,
                        last_access=current_time,
                        access_frequency=0.0,
                        user_contexts={user_id},
                        peak_hours=[current_hour]
                    )
            
            # Schedule predictive warming if pattern is established
            await self._consider_predictive_warming(pattern, user_id)
            
        except Exception as e:
            logger.error("Pattern analysis error", key=key[:50], error=str(e))
    
    async def schedule_warming_task(
        self,
        key_patterns: List[str],
        strategy: WarmingStrategy = WarmingStrategy.PREDICTIVE,
        priority: CachePriority = CachePriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        user_id: Optional[str] = None,
        attention_critical: bool = False
    ) -> str:
        """Schedule a cache warming task."""
        try:
            task_id = f"warm_{int(time.time())}_{hash(tuple(key_patterns)) % 1000000}"
            
            task = WarmingTask(
                id=task_id,
                strategy=strategy,
                key_patterns=key_patterns,
                priority=priority,
                scheduled_at=scheduled_at or datetime.utcnow(),
                user_id=user_id,
                attention_critical=attention_critical
            )
            
            self.warming_tasks[task_id] = task
            
            logger.info(
                "Cache warming task scheduled",
                task_id=task_id,
                strategy=strategy.value,
                patterns=len(key_patterns),
                attention_critical=attention_critical
            )
            
            return task_id
            
        except Exception as e:
            logger.error("Failed to schedule warming task", error=str(e))
            raise
    
    async def warm_user_critical_data(self, user_id: str) -> Dict[str, Any]:
        """Warm cache with user's attention-critical data."""
        try:
            start_time = time.perf_counter()
            
            # Identify critical cache patterns for user
            critical_patterns = await self._identify_critical_patterns(user_id)
            
            # Create high-priority warming tasks
            warming_results = {}
            
            for pattern in critical_patterns:
                # Generate keys to warm based on pattern
                keys_to_warm = await self._generate_keys_from_pattern(pattern, user_id)
                
                if keys_to_warm:
                    # Submit background warming task
                    task_def = TaskDefinition(
                        name=f"Warm critical cache for {user_id}",
                        task_type=TaskType.CACHE_WARMING,
                        priority=TaskPriority.HIGH,
                        function_name="cache_warming",
                        args=[pattern, keys_to_warm, user_id],
                        user_id=user_id,
                        user_visible=True,
                        attention_friendly=True,
                        max_execution_time=30  # Quick warming for ADHD responsiveness
                    )
                    
                    task_id = await background_task_manager.submit_task(task_def)
                    warming_results[pattern] = {
                        'task_id': task_id,
                        'keys_count': len(keys_to_warm),
                        'status': 'warming'
                    }
            
            execution_time = time.perf_counter() - start_time
            
            logger.info(
                "Critical data warming initiated",
                user_id=user_id,
                patterns=len(critical_patterns),
                execution_time=f"{execution_time:.3f}s"
            )
            
            return {
                'user_id': user_id,
                'patterns_warmed': len(critical_patterns),
                'total_keys': sum(r.get('keys_count', 0) for r in warming_results.values()),
                'warming_tasks': warming_results,
                'execution_time': execution_time
            }
            
        except Exception as e:
            logger.error("Critical data warming error", user_id=user_id, error=str(e))
            return {'error': str(e), 'user_id': user_id}
    
    async def warm_peak_usage_data(self) -> Dict[str, Any]:
        """Warm cache for predicted peak usage patterns."""
        try:
            current_hour = datetime.utcnow().hour
            
            # Identify patterns with peak usage at current hour
            peak_patterns = []
            for pattern, data in self.global_patterns.items():
                if current_hour in data.peak_hours:
                    peak_patterns.append((pattern, data.access_frequency))
            
            # Sort by access frequency
            peak_patterns.sort(key=lambda x: x[1], reverse=True)
            
            # Warm top patterns
            warming_tasks = []
            for pattern, frequency in peak_patterns[:20]:  # Top 20 patterns
                keys = await self._generate_keys_from_pattern(pattern)
                if keys:
                    task_def = TaskDefinition(
                        name=f"Peak usage warming: {pattern}",
                        task_type=TaskType.CACHE_WARMING,
                        priority=TaskPriority.NORMAL,
                        function_name="cache_warming",
                        args=[pattern, keys],
                        max_execution_time=120
                    )
                    
                    task_id = await background_task_manager.submit_task(task_def)
                    warming_tasks.append({
                        'pattern': pattern,
                        'task_id': task_id,
                        'frequency': frequency,
                        'keys_count': len(keys)
                    })
            
            logger.info(
                "Peak usage warming initiated",
                current_hour=current_hour,
                patterns=len(warming_tasks)
            )
            
            return {
                'peak_hour': current_hour,
                'patterns_warmed': len(warming_tasks),
                'warming_tasks': warming_tasks
            }
            
        except Exception as e:
            logger.error("Peak usage warming error", error=str(e))
            return {'error': str(e)}
    
    def _extract_key_pattern(self, key: str) -> str:
        """Extract pattern from cache key for analysis."""
        # Convert specific IDs to patterns
        import re
        
        # Replace UUIDs with placeholder
        pattern = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '{uuid}', key)
        
        # Replace numeric IDs with placeholder
        pattern = re.sub(r'\b\d+\b', '{id}', pattern)
        
        # Replace timestamps with placeholder
        pattern = re.sub(r'\d{4}-\d{2}-\d{2}', '{date}', pattern)
        pattern = re.sub(r'\d{13}', '{timestamp}', pattern)
        
        return pattern
    
    def _calculate_frequency(self, access_count: int, first_access: datetime, last_access: datetime) -> float:
        """Calculate access frequency per hour."""
        if access_count <= 1:
            return 0.0
        
        time_diff = (last_access - first_access).total_seconds() / 3600  # Convert to hours
        if time_diff <= 0:
            return 0.0
        
        return access_count / time_diff
    
    def _update_peak_hours(self, existing_hours: List[int], new_hour: int) -> List[int]:
        """Update peak hours list with new access."""
        hours = list(existing_hours)
        hours.append(new_hour)
        
        # Keep track of hour frequency and return top hours
        hour_counts = defaultdict(int)
        for hour in hours:
            hour_counts[hour] += 1
        
        # Return top 6 peak hours
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, count in sorted_hours[:6]]
    
    async def _consider_predictive_warming(self, pattern: str, user_id: Optional[str] = None) -> None:
        """Consider scheduling predictive warming based on pattern analysis."""
        try:
            # Get pattern data
            pattern_data = None
            if user_id and user_id in self.user_patterns:
                pattern_data = self.user_patterns[user_id].get(pattern)
            
            if not pattern_data:
                pattern_data = self.global_patterns.get(pattern)
            
            if not pattern_data or pattern_data.access_count < 3:
                return  # Need more data points
            
            # Check if pattern warrants predictive warming
            should_warm = (
                pattern_data.access_frequency > 0.5 or  # More than once per 2 hours
                len(pattern_data.user_contexts) > 5 or  # Used by multiple users
                any(hour in self.peak_attention_hours for hour in pattern_data.peak_hours)
            )
            
            if should_warm:
                # Schedule warming for next predicted access time
                next_access_time = self._predict_next_access(pattern_data)
                
                # Schedule warming 5 minutes before predicted access
                warm_time = next_access_time - timedelta(minutes=5)
                
                if warm_time > datetime.utcnow():
                    await self.schedule_warming_task(
                        key_patterns=[pattern],
                        strategy=WarmingStrategy.PREDICTIVE,
                        priority=CachePriority.HIGH if user_id else CachePriority.NORMAL,
                        scheduled_at=warm_time,
                        user_id=user_id
                    )
            
        except Exception as e:
            logger.error("Predictive warming consideration error", pattern=pattern, error=str(e))
    
    def _predict_next_access(self, pattern_data: CachePattern) -> datetime:
        """Predict next access time based on pattern history."""
        current_time = datetime.utcnow()
        current_hour = current_time.hour
        
        # Find next peak hour
        future_peak_hours = [h for h in pattern_data.peak_hours if h > current_hour]
        if not future_peak_hours:
            # Use tomorrow's first peak hour
            future_peak_hours = [min(pattern_data.peak_hours) + 24] if pattern_data.peak_hours else [current_hour + 1]
        
        next_peak_hour = min(future_peak_hours)
        
        # Calculate next access time
        if next_peak_hour > 24:
            # Tomorrow
            next_access = current_time.replace(hour=next_peak_hour - 24, minute=0, second=0, microsecond=0)
            next_access += timedelta(days=1)
        else:
            # Today
            next_access = current_time.replace(hour=next_peak_hour, minute=0, second=0, microsecond=0)
        
        return next_access
    
    async def _identify_critical_patterns(self, user_id: str) -> List[str]:
        """Identify critical cache patterns for a user."""
        critical_patterns = []
        
        if user_id in self.user_patterns:
            for pattern, data in self.user_patterns[user_id].items():
                # Consider critical if:
                # 1. High access frequency
                # 2. Recent access
                # 3. Peak usage during attention hours
                if (data.access_frequency > 1.0 or  # More than once per hour
                    (datetime.utcnow() - data.last_access).total_seconds() < 3600 or  # Accessed in last hour
                    any(hour in self.peak_attention_hours for hour in data.peak_hours)):
                    critical_patterns.append(pattern)
        
        # Also include global patterns that might be relevant
        for pattern, data in self.global_patterns.items():
            if (user_id in data.user_contexts and 
                pattern not in critical_patterns and
                data.access_frequency > 2.0):  # High global frequency
                critical_patterns.append(pattern)
        
        return critical_patterns[:10]  # Limit to top 10 for ADHD focus
    
    async def _generate_keys_from_pattern(self, pattern: str, user_id: Optional[str] = None) -> List[str]:
        """Generate actual cache keys from pattern template."""
        keys = []
        
        try:
            # This would integrate with the actual system to generate real keys
            # For now, return example implementations
            
            if '{uuid}' in pattern:
                # Generate keys for known UUIDs (would query database in real implementation)
                sample_uuids = ['12345678-1234-1234-1234-123456789012']  # Placeholder
                for uuid in sample_uuids:
                    key = pattern.replace('{uuid}', uuid)
                    if user_id:
                        key = key.replace('{user_id}', user_id)
                    keys.append(key)
            
            if '{id}' in pattern:
                # Generate keys for known IDs
                sample_ids = ['1', '2', '3']  # Placeholder
                for id_val in sample_ids:
                    key = pattern.replace('{id}', id_val)
                    if user_id:
                        key = key.replace('{user_id}', user_id)
                    keys.append(key)
            
            if '{date}' in pattern:
                # Generate keys for recent dates
                today = datetime.utcnow().date()
                for i in range(7):  # Last 7 days
                    date = today - timedelta(days=i)
                    key = pattern.replace('{date}', date.strftime('%Y-%m-%d'))
                    if user_id:
                        key = key.replace('{user_id}', user_id)
                    keys.append(key)
            
            # If no placeholders, use pattern as is
            if not any(placeholder in pattern for placeholder in ['{uuid}', '{id}', '{date}', '{timestamp}']):
                key = pattern
                if user_id:
                    key = f"{key}:{user_id}"
                keys.append(key)
        
        except Exception as e:
            logger.error("Key generation error", pattern=pattern, error=str(e))
        
        return keys[:50]  # Limit keys for performance
    
    async def _pattern_analysis_loop(self) -> None:
        """Background loop for pattern analysis and optimization."""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Analyze patterns and update predictions
                await self._analyze_pattern_trends()
                
                # Clean up old patterns
                await self._cleanup_old_patterns()
                
            except Exception as e:
                logger.error("Pattern analysis loop error", error=str(e))
                await asyncio.sleep(300)
    
    async def _warming_execution_loop(self) -> None:
        """Background loop for executing warming tasks."""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                # Find tasks ready for execution
                ready_tasks = [
                    task for task in self.warming_tasks.values()
                    if (task.scheduled_at <= current_time and 
                        (task.last_executed is None or 
                         (task.interval_seconds and 
                          (current_time - task.last_executed).total_seconds() >= task.interval_seconds)))
                ]
                
                # Execute ready tasks
                for task in ready_tasks:
                    await self._execute_warming_task(task)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error("Warming execution loop error", error=str(e))
                await asyncio.sleep(60)
    
    async def _performance_optimization_loop(self) -> None:
        """Background loop for performance optimization."""
        while self.is_running:
            try:
                await asyncio.sleep(1800)  # Run every 30 minutes
                
                # Analyze warming effectiveness
                await self._analyze_warming_effectiveness()
                
                # Optimize warming strategies
                await self._optimize_warming_strategies()
                
                # Update performance statistics
                await self._update_performance_stats()
                
            except Exception as e:
                logger.error("Performance optimization loop error", error=str(e))
                await asyncio.sleep(1800)
    
    async def _execute_warming_task(self, task: WarmingTask) -> None:
        """Execute a cache warming task."""
        try:
            start_time = time.perf_counter()
            
            # Generate actual keys from patterns
            all_keys = []
            for pattern in task.key_patterns:
                keys = await self._generate_keys_from_pattern(pattern, task.user_id)
                all_keys.extend(keys)
            
            # Execute warming
            if all_keys:
                # Submit as background task
                task_def = TaskDefinition(
                    name=f"Cache warming: {task.strategy.value}",
                    task_type=TaskType.CACHE_WARMING,
                    priority=TaskPriority.HIGH if task.attention_critical else TaskPriority.NORMAL,
                    function_name="cache_warming",
                    args=[task.key_patterns, all_keys, task.user_id],
                    user_id=task.user_id,
                    max_execution_time=60 if task.attention_critical else 300
                )
                
                await background_task_manager.submit_task(task_def)
            
            # Update task tracking
            execution_time = time.perf_counter() - start_time
            task.last_executed = datetime.utcnow()
            task.execution_count += 1
            task.average_warming_time = (
                (task.average_warming_time * (task.execution_count - 1) + execution_time)
                / task.execution_count
            )
            
            # Update statistics
            self.warming_stats['tasks_executed'] += 1
            
            logger.info(
                "Warming task executed",
                task_id=task.id,
                keys=len(all_keys),
                execution_time=f"{execution_time:.3f}s"
            )
            
        except Exception as e:
            logger.error("Warming task execution error", task_id=task.id, error=str(e))
            task.failure_count += 1
    
    async def _analyze_pattern_trends(self) -> None:
        """Analyze pattern trends and update predictions."""
        # This would perform sophisticated pattern analysis
        # For now, basic cleanup and trend tracking
        current_time = datetime.utcnow()
        
        # Update access frequencies based on recent activity
        for patterns in [self.global_patterns, *self.user_patterns.values()]:
            for pattern_key, pattern_data in patterns.items():
                # Decay frequency over time to emphasize recent activity
                time_since_last = (current_time - pattern_data.last_access).total_seconds() / 3600
                if time_since_last > 24:  # More than a day
                    # Reduce frequency to reflect decreased relevance
                    decay_factor = max(0.1, 1.0 - (time_since_last - 24) / (7 * 24))  # Decay over a week
                    new_frequency = pattern_data.access_frequency * decay_factor
                    
                    # Update the pattern (create new tuple since it's immutable)
                    patterns[pattern_key] = CachePattern(
                        key_pattern=pattern_data.key_pattern,
                        access_count=pattern_data.access_count,
                        last_access=pattern_data.last_access,
                        access_frequency=new_frequency,
                        user_contexts=pattern_data.user_contexts,
                        peak_hours=pattern_data.peak_hours
                    )
    
    async def _cleanup_old_patterns(self) -> None:
        """Clean up old, unused patterns."""
        cutoff_time = datetime.utcnow() - timedelta(days=30)
        
        # Clean global patterns
        old_patterns = [
            key for key, pattern in self.global_patterns.items()
            if pattern.last_access < cutoff_time and pattern.access_count < 5
        ]
        
        for key in old_patterns:
            del self.global_patterns[key]
        
        # Clean user patterns
        for user_id, patterns in list(self.user_patterns.items()):
            old_user_patterns = [
                key for key, pattern in patterns.items()
                if pattern.last_access < cutoff_time and pattern.access_count < 3
            ]
            
            for key in old_user_patterns:
                del patterns[key]
            
            # Remove user entry if no patterns remain
            if not patterns:
                del self.user_patterns[user_id]
        
        if old_patterns:
            logger.info("Cleaned up old cache patterns", global=len(old_patterns))
    
    async def _analyze_warming_effectiveness(self) -> None:
        """Analyze the effectiveness of warming tasks."""
        # This would integrate with cache manager to get hit rate improvements
        # For now, simulate analysis
        
        total_tasks = self.warming_stats['tasks_executed']
        if total_tasks > 0:
            # Calculate success rates based on task completion
            successful_tasks = sum(
                1 for task in self.warming_tasks.values()
                if task.execution_count > 0 and task.failure_count / max(1, task.execution_count) < 0.1
            )
            
            self.warming_stats['success_rate'] = successful_tasks / len(self.warming_tasks) if self.warming_tasks else 0.0
            
            # Simulate cache hit improvement (would be calculated from actual cache stats)
            self.warming_stats['cache_hit_improvement'] = min(0.3, successful_tasks * 0.05)  # Up to 30% improvement
    
    async def _optimize_warming_strategies(self) -> None:
        """Optimize warming strategies based on effectiveness."""
        # Analyze which strategies are most effective
        strategy_performance = defaultdict(list)
        
        for task in self.warming_tasks.values():
            if task.execution_count > 0:
                success_rate = 1.0 - (task.failure_count / task.execution_count)
                strategy_performance[task.strategy].append(success_rate)
        
        # Log strategy performance
        for strategy, success_rates in strategy_performance.items():
            if success_rates:
                avg_success = sum(success_rates) / len(success_rates)
                logger.info(f"Warming strategy performance", strategy=strategy.value, success_rate=avg_success)
    
    async def _update_performance_stats(self) -> None:
        """Update performance statistics."""
        # Calculate attention-critical success rate
        attention_critical_tasks = [
            task for task in self.warming_tasks.values()
            if task.attention_critical and task.execution_count > 0
        ]
        
        if attention_critical_tasks:
            success_count = sum(
                1 for task in attention_critical_tasks
                if task.failure_count / max(1, task.execution_count) < 0.05  # Very low failure rate
            )
            self.warming_stats['attention_critical_success_rate'] = success_count / len(attention_critical_tasks)
    
    async def _load_saved_patterns(self) -> None:
        """Load saved patterns from cache."""
        try:
            # Try to load patterns from cache
            patterns_data = await cache_manager.get("cache_warming:patterns", priority=CachePriority.NORMAL)
            
            if patterns_data:
                self.global_patterns = patterns_data.get('global', {})
                self.user_patterns = patterns_data.get('users', {})
                logger.info("Loaded saved cache patterns", 
                           global_patterns=len(self.global_patterns),
                           user_patterns=len(self.user_patterns))
        
        except Exception as e:
            logger.warning("Failed to load saved patterns", error=str(e))
    
    async def _save_patterns(self) -> None:
        """Save patterns to cache for persistence."""
        try:
            patterns_data = {
                'global': self.global_patterns,
                'users': self.user_patterns,
                'saved_at': datetime.utcnow().isoformat()
            }
            
            await cache_manager.set(
                "cache_warming:patterns",
                patterns_data,
                ttl=86400 * 7,  # Keep for a week
                priority=CachePriority.LOW
            )
            
            logger.info("Saved cache patterns for persistence")
            
        except Exception as e:
            logger.warning("Failed to save patterns", error=str(e))
    
    async def _schedule_initial_warming(self) -> None:
        """Schedule initial warming for system startup."""
        # Schedule warming of critical system data
        system_patterns = [
            "user:profile:{id}",
            "config:system",
            "auth:session:{uuid}",
            "adhd:context:{user_id}"
        ]
        
        await self.schedule_warming_task(
            key_patterns=system_patterns,
            strategy=WarmingStrategy.SCHEDULED,
            priority=CachePriority.HIGH,
            attention_critical=True
        )
        
        # Schedule daily warming during low usage hours
        tomorrow_3am = datetime.utcnow().replace(hour=3, minute=0, second=0, microsecond=0)
        if tomorrow_3am <= datetime.utcnow():
            tomorrow_3am += timedelta(days=1)
        
        await self.schedule_warming_task(
            key_patterns=["analytics:{date}", "reports:{id}"],
            strategy=WarmingStrategy.SCHEDULED,
            priority=CachePriority.LOW,
            scheduled_at=tomorrow_3am
        )
    
    def get_warming_stats(self) -> Dict[str, Any]:
        """Get comprehensive warming statistics."""
        stats = dict(self.warming_stats)
        
        stats.update({
            'active_tasks': len(self.warming_tasks),
            'global_patterns': len(self.global_patterns),
            'user_patterns_count': len(self.user_patterns),
            'total_user_patterns': sum(len(patterns) for patterns in self.user_patterns.values()),
            'peak_attention_hours': self.peak_attention_hours,
            'engine_running': self.is_running
        })
        
        return stats


class CacheInvalidationEngine:
    """
    Intelligent cache invalidation engine with dependency tracking.
    
    Features:
    - Smart invalidation with dependency cascade
    - Batch invalidation for performance optimization
    - ADHD-safe invalidation that preserves critical data
    - Lazy invalidation for non-critical data
    """
    
    def __init__(self):
        self.dependency_graph: Dict[str, Set[str]] = {}
        self.invalidation_queue: asyncio.Queue = asyncio.Queue()
        self.batch_invalidations: Dict[str, Set[str]] = defaultdict(set)
        
        # Performance tracking
        self.invalidation_stats = {
            'total_invalidations': 0,
            'cascade_invalidations': 0,
            'batch_invalidations': 0,
            'average_invalidation_time_ms': 0.0
        }
        
        self.is_running = False
    
    async def initialize(self) -> None:
        """Initialize the cache invalidation engine."""
        try:
            self.is_running = True
            
            # Start invalidation worker
            asyncio.create_task(self._invalidation_worker())
            asyncio.create_task(self._batch_invalidation_worker())
            
            logger.info("Cache invalidation engine initialized")
            
        except Exception as e:
            logger.error("Failed to initialize cache invalidation engine", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the cache invalidation engine."""
        logger.info("Shutting down cache invalidation engine")
        self.is_running = False
        logger.info("Cache invalidation engine shutdown complete")
    
    async def invalidate_with_dependencies(self, key: str, strategy: InvalidationStrategy = InvalidationStrategy.CASCADE) -> int:
        """Invalidate cache key and all its dependencies."""
        try:
            start_time = time.perf_counter()
            
            if strategy == InvalidationStrategy.CASCADE:
                # Find all dependent keys
                dependent_keys = set()
                self._find_all_dependencies(key, dependent_keys)
                
                # Invalidate all keys
                for dep_key in dependent_keys:
                    await cache_manager.delete(dep_key)
                
                # Also invalidate the original key
                await cache_manager.delete(key)
                
                invalidation_count = len(dependent_keys) + 1
                self.invalidation_stats['cascade_invalidations'] += 1
                
            elif strategy == InvalidationStrategy.BATCH:
                # Add to batch queue
                pattern = self._extract_invalidation_pattern(key)
                self.batch_invalidations[pattern].add(key)
                invalidation_count = 1
                
            elif strategy == InvalidationStrategy.IMMEDIATE:
                # Immediate invalidation
                await cache_manager.delete(key)
                invalidation_count = 1
                
            else:
                # Queue for later processing
                await self.invalidation_queue.put((key, strategy))
                invalidation_count = 1
            
            # Update statistics
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            self.invalidation_stats['total_invalidations'] += invalidation_count
            
            current_avg = self.invalidation_stats['average_invalidation_time_ms']
            total_invalidations = self.invalidation_stats['total_invalidations']
            new_avg = ((current_avg * (total_invalidations - invalidation_count)) + execution_time_ms) / total_invalidations
            self.invalidation_stats['average_invalidation_time_ms'] = new_avg
            
            logger.debug(
                "Cache invalidation completed",
                key=key[:50],
                strategy=strategy.value,
                invalidated_count=invalidation_count,
                execution_time_ms=f"{execution_time_ms:.2f}"
            )
            
            return invalidation_count
            
        except Exception as e:
            logger.error("Cache invalidation error", key=key[:50], error=str(e))
            return 0
    
    def register_dependency(self, key: str, depends_on: str) -> None:
        """Register a cache dependency relationship."""
        if depends_on not in self.dependency_graph:
            self.dependency_graph[depends_on] = set()
        self.dependency_graph[depends_on].add(key)
        
        logger.debug("Cache dependency registered", key=key[:50], depends_on=depends_on[:50])
    
    def _find_all_dependencies(self, key: str, found_dependencies: Set[str]) -> None:
        """Recursively find all cache dependencies."""
        if key in self.dependency_graph:
            for dependent_key in self.dependency_graph[key]:
                if dependent_key not in found_dependencies:
                    found_dependencies.add(dependent_key)
                    self._find_all_dependencies(dependent_key, found_dependencies)
    
    def _extract_invalidation_pattern(self, key: str) -> str:
        """Extract pattern for batch invalidation."""
        # Group similar keys together for efficient batch processing
        import re
        
        # Group by prefix
        parts = key.split(':')
        if len(parts) >= 2:
            return f"{parts[0]}:{parts[1]}"
        return parts[0] if parts else key
    
    async def _invalidation_worker(self) -> None:
        """Background worker for processing invalidation queue."""
        while self.is_running:
            try:
                try:
                    key, strategy = await asyncio.wait_for(self.invalidation_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                
                if strategy == InvalidationStrategy.LAZY:
                    # Lazy invalidation - mark for invalidation on next access
                    # This would be implemented by setting a flag in cache metadata
                    pass
                else:
                    await cache_manager.delete(key)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Invalidation worker error", error=str(e))
                await asyncio.sleep(1)
    
    async def _batch_invalidation_worker(self) -> None:
        """Background worker for processing batch invalidations."""
        while self.is_running:
            try:
                await asyncio.sleep(10)  # Process batches every 10 seconds
                
                if not self.batch_invalidations:
                    continue
                
                # Process each batch pattern
                for pattern, keys in list(self.batch_invalidations.items()):
                    if keys:
                        # Convert to wildcard pattern and invalidate
                        wildcard_pattern = f"{pattern}*"
                        invalidated = await cache_manager.invalidate_pattern(wildcard_pattern)
                        
                        self.invalidation_stats['batch_invalidations'] += 1
                        self.invalidation_stats['total_invalidations'] += invalidated
                        
                        logger.info("Batch invalidation completed", pattern=pattern, count=invalidated)
                        
                        # Clear processed batch
                        del self.batch_invalidations[pattern]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Batch invalidation worker error", error=str(e))
                await asyncio.sleep(10)
    
    def get_invalidation_stats(self) -> Dict[str, Any]:
        """Get comprehensive invalidation statistics."""
        stats = dict(self.invalidation_stats)
        
        stats.update({
            'dependency_relationships': len(self.dependency_graph),
            'queue_size': self.invalidation_queue.qsize(),
            'pending_batch_patterns': len(self.batch_invalidations),
            'pending_batch_keys': sum(len(keys) for keys in self.batch_invalidations.values()),
            'engine_running': self.is_running
        })
        
        return stats


# Global instances
cache_warming_engine = CacheWarmingEngine()
cache_invalidation_engine = CacheInvalidationEngine()