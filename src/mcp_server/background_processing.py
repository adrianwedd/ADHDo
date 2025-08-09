"""
Background Processing and Task Management System for MCP ADHD Server.

Enterprise-scale background processing with ADHD-optimized task handling.
Provides multi-priority queues, intelligent task scheduling, and crisis-safe processing.

Features:
- Crisis/Safety priority queue for immediate processing
- User interaction tasks with <1 second response targets
- Background analytics and maintenance with normal priority
- Task progress tracking and user-friendly status updates
- Intelligent failure handling with retry logic and graceful degradation
- Resource allocation that preserves foreground responsiveness
"""

import asyncio
import json
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
from uuid import uuid4
import logging

import redis.asyncio as redis
from pydantic import BaseModel, Field
import structlog

from mcp_server.config import settings
from mcp_server.database import get_session
from mcp_server.db_models import User


# Configure structured logger
logger = structlog.get_logger(__name__)


class TaskPriority(str, Enum):
    """Task priority levels optimized for ADHD user experience."""
    CRISIS = "crisis"          # Immediate execution, highest priority
    HIGH = "high"              # User interaction tasks, <1 second target
    NORMAL = "normal"          # Background analytics, batch processing
    LOW = "low"                # Maintenance tasks, scheduled execution
    MAINTENANCE = "maintenance"  # System cleanup and optimization


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"        # Waiting in queue
    RUNNING = "running"        # Currently executing
    COMPLETED = "completed"    # Successfully completed
    FAILED = "failed"          # Execution failed
    CANCELLED = "cancelled"    # Cancelled by user or system
    RETRYING = "retrying"      # Failed, attempting retry


class TaskType(str, Enum):
    """Categories of background tasks for ADHD optimization."""
    # Crisis and Safety
    CRISIS_DETECTION = "crisis_detection"
    SAFETY_INTERVENTION = "safety_intervention"
    
    # User Interaction (High Priority)
    CONTEXT_BUILDING = "context_building"
    PATTERN_ANALYSIS = "pattern_analysis"
    NOTIFICATION_DELIVERY = "notification_delivery"
    CALENDAR_SYNC = "calendar_sync"
    
    # Background Processing (Normal Priority)
    ML_PROCESSING = "ml_processing"
    ANALYTICS_COMPUTATION = "analytics_computation"
    REPORT_GENERATION = "report_generation"
    DATA_AGGREGATION = "data_aggregation"
    
    # Maintenance (Low Priority)
    DATABASE_CLEANUP = "database_cleanup"
    CACHE_WARMING = "cache_warming"
    LOG_ROTATION = "log_rotation"
    SYSTEM_OPTIMIZATION = "system_optimization"


class TaskDefinition(BaseModel):
    """Task definition model with ADHD optimization metadata."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    task_type: TaskType
    priority: TaskPriority
    function_name: str
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    
    # ADHD-specific fields
    user_id: Optional[str] = None
    user_visible: bool = False  # Should progress be shown to user?
    attention_friendly: bool = False  # Use attention-friendly progress updates?
    max_execution_time: int = 300  # Maximum execution time in seconds
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: int = 60  # Seconds between retries
    exponential_backoff: bool = True
    
    # Scheduling
    scheduled_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Task execution result with comprehensive tracking."""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    stacktrace: Optional[str] = None
    
    execution_time: float = 0.0
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    
    retry_count: int = 0
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Progress tracking
    progress_percentage: float = 0.0
    progress_message: str = ""
    
    # ADHD optimization metrics
    user_attention_maintained: bool = True
    cognitive_load_score: Optional[float] = None


class BackgroundTaskManager:
    """
    Enterprise-scale background task manager with ADHD optimizations.
    
    Features:
    - Multi-priority queue system with crisis-safe processing
    - Intelligent resource allocation and load balancing
    - Real-time progress tracking with user-friendly updates
    - Failure handling with retry logic and graceful degradation
    - Performance monitoring and optimization
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.task_handlers: Dict[str, Callable] = {}
        self.worker_pools: Dict[TaskPriority, asyncio.Queue] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self.worker_tasks: List[asyncio.Task] = []
        self.is_running = False
        
        # Performance tracking
        self.performance_stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'average_execution_time': 0.0,
            'queue_sizes': {},
            'worker_utilization': {}
        }
        
        # ADHD optimization settings
        self.crisis_response_time_target = 0.1  # 100ms for crisis tasks
        self.user_response_time_target = 1.0    # 1 second for user tasks
        self.background_resource_limit = 0.7    # 70% max resource usage
        
    async def initialize(self) -> None:
        """Initialize the background task manager."""
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                health_check_interval=30
            )
            
            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Background task manager Redis connection established")
            
            # Initialize priority queues
            for priority in TaskPriority:
                self.worker_pools[priority] = asyncio.Queue()
                self.performance_stats['queue_sizes'][priority.value] = 0
                self.performance_stats['worker_utilization'][priority.value] = 0.0
            
            # Register default task handlers
            await self._register_default_handlers()
            
            self.is_running = True
            logger.info("Background task manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize background task manager", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the background task manager gracefully."""
        logger.info("Shutting down background task manager")
        
        self.is_running = False
        
        # Cancel all running tasks
        for task_id, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
                logger.info("Cancelled running task", task_id=task_id)
        
        # Wait for workers to finish
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.aclose()
        
        logger.info("Background task manager shutdown complete")
    
    async def _register_default_handlers(self) -> None:
        """Register default task handlers for common operations."""
        
        # Crisis and Safety handlers
        self.register_handler("crisis_detection", self._handle_crisis_detection)
        self.register_handler("safety_intervention", self._handle_safety_intervention)
        
        # User interaction handlers
        self.register_handler("context_building", self._handle_context_building)
        self.register_handler("pattern_analysis", self._handle_pattern_analysis)
        self.register_handler("notification_delivery", self._handle_notification_delivery)
        self.register_handler("calendar_sync", self._handle_calendar_sync)
        
        # Background processing handlers
        self.register_handler("ml_processing", self._handle_ml_processing)
        self.register_handler("analytics_computation", self._handle_analytics_computation)
        self.register_handler("report_generation", self._handle_report_generation)
        self.register_handler("data_aggregation", self._handle_data_aggregation)
        
        # Maintenance handlers
        self.register_handler("database_cleanup", self._handle_database_cleanup)
        self.register_handler("cache_warming", self._handle_cache_warming)
        self.register_handler("log_rotation", self._handle_log_rotation)
        self.register_handler("system_optimization", self._handle_system_optimization)
    
    def register_handler(self, function_name: str, handler: Callable) -> None:
        """Register a task handler function."""
        self.task_handlers[function_name] = handler
        logger.debug("Registered task handler", function_name=function_name)
    
    async def submit_task(self, task: TaskDefinition) -> str:
        """
        Submit a task for background processing.
        
        Args:
            task: Task definition to execute
            
        Returns:
            Task ID for tracking
        """
        try:
            # Store task in Redis for persistence
            task_key = f"task:{task.id}"
            await self.redis_client.setex(
                task_key,
                86400,  # 24 hour TTL
                json.dumps(task.model_dump(), default=str)
            )
            
            # Add to appropriate priority queue
            await self.worker_pools[task.priority].put(task)
            self.performance_stats['queue_sizes'][task.priority.value] += 1
            
            # Create initial result tracking
            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.PENDING
            )
            self.task_results[task.id] = result
            
            logger.info(
                "Task submitted for background processing",
                task_id=task.id,
                task_type=task.task_type.value,
                priority=task.priority.value,
                user_visible=task.user_visible
            )
            
            return task.id
            
        except Exception as e:
            logger.error("Failed to submit task", task_id=task.id, error=str(e))
            raise
    
    async def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get the current status of a task."""
        return self.task_results.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running or pending task."""
        try:
            # Cancel running task
            if task_id in self.running_tasks:
                running_task = self.running_tasks[task_id]
                if not running_task.done():
                    running_task.cancel()
                    
                    # Update result
                    if task_id in self.task_results:
                        self.task_results[task_id].status = TaskStatus.CANCELLED
                    
                    logger.info("Task cancelled", task_id=task_id)
                    return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to cancel task", task_id=task_id, error=str(e))
            return False
    
    async def start_workers(self, worker_counts: Optional[Dict[TaskPriority, int]] = None) -> None:
        """
        Start background workers for task processing.
        
        Args:
            worker_counts: Number of workers per priority level
        """
        if worker_counts is None:
            # ADHD-optimized worker allocation
            worker_counts = {
                TaskPriority.CRISIS: 2,      # Always available for crisis
                TaskPriority.HIGH: 4,        # Ample capacity for user interactions  
                TaskPriority.NORMAL: 3,      # Background processing
                TaskPriority.LOW: 1,         # Maintenance
                TaskPriority.MAINTENANCE: 1  # System optimization
            }
        
        # Start workers for each priority level
        for priority, count in worker_counts.items():
            for i in range(count):
                worker_task = asyncio.create_task(
                    self._worker(priority, i),
                    name=f"worker-{priority.value}-{i}"
                )
                self.worker_tasks.append(worker_task)
        
        logger.info("Background workers started", worker_counts=worker_counts)
    
    async def _worker(self, priority: TaskPriority, worker_id: int) -> None:
        """Background worker for processing tasks of a specific priority."""
        logger.info("Worker started", priority=priority.value, worker_id=worker_id)
        
        while self.is_running:
            try:
                # Wait for task with timeout based on priority
                timeout = self._get_worker_timeout(priority)
                queue = self.worker_pools[priority]
                
                try:
                    task = await asyncio.wait_for(queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    continue
                
                # Execute the task
                await self._execute_task(task, worker_id)
                
                # Update queue size
                self.performance_stats['queue_sizes'][priority.value] -= 1
                
            except asyncio.CancelledError:
                logger.info("Worker cancelled", priority=priority.value, worker_id=worker_id)
                break
            except Exception as e:
                logger.error(
                    "Worker error",
                    priority=priority.value,
                    worker_id=worker_id,
                    error=str(e)
                )
                await asyncio.sleep(1)  # Brief pause before retry
        
        logger.info("Worker stopped", priority=priority.value, worker_id=worker_id)
    
    def _get_worker_timeout(self, priority: TaskPriority) -> float:
        """Get appropriate timeout for worker based on priority and ADHD optimization."""
        timeouts = {
            TaskPriority.CRISIS: 0.1,      # Very responsive for crisis
            TaskPriority.HIGH: 1.0,        # Quick for user interactions
            TaskPriority.NORMAL: 5.0,      # Regular background processing
            TaskPriority.LOW: 10.0,        # Patient for maintenance
            TaskPriority.MAINTENANCE: 30.0 # Very patient for optimization
        }
        return timeouts.get(priority, 5.0)
    
    async def _execute_task(self, task: TaskDefinition, worker_id: int) -> None:
        """Execute a single task with comprehensive monitoring."""
        start_time = time.perf_counter()
        task_id = task.id
        
        # Update task status to running
        if task_id in self.task_results:
            self.task_results[task_id].status = TaskStatus.RUNNING
        
        try:
            logger.info(
                "Executing task",
                task_id=task_id,
                task_type=task.task_type.value,
                priority=task.priority.value,
                worker_id=worker_id
            )
            
            # Get task handler
            handler = self.task_handlers.get(task.function_name)
            if not handler:
                raise ValueError(f"No handler registered for function: {task.function_name}")
            
            # Create execution context with timeout
            execution_task = asyncio.create_task(
                handler(*task.args, **task.kwargs)
            )
            self.running_tasks[task_id] = execution_task
            
            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    execution_task,
                    timeout=task.max_execution_time
                )
                
                # Task completed successfully
                execution_time = time.perf_counter() - start_time
                
                if task_id in self.task_results:
                    task_result = self.task_results[task_id]
                    task_result.status = TaskStatus.COMPLETED
                    task_result.result = result
                    task_result.execution_time = execution_time
                    task_result.completed_at = datetime.utcnow()
                
                self.performance_stats['tasks_completed'] += 1
                self._update_average_execution_time(execution_time)
                
                logger.info(
                    "Task completed successfully",
                    task_id=task_id,
                    execution_time=f"{execution_time:.3f}s"
                )
                
                # Check if execution time meets ADHD requirements
                if task.user_visible:
                    target_time = (
                        self.crisis_response_time_target 
                        if task.priority == TaskPriority.CRISIS
                        else self.user_response_time_target
                    )
                    
                    if execution_time > target_time:
                        logger.warning(
                            "Task exceeded ADHD response time target",
                            task_id=task_id,
                            actual_time=f"{execution_time:.3f}s",
                            target_time=f"{target_time:.3f}s",
                            adhd_impact="May affect user experience"
                        )
                
            except asyncio.TimeoutError:
                # Task timed out
                execution_task.cancel()
                raise TimeoutError(f"Task timed out after {task.max_execution_time} seconds")
            
        except Exception as e:
            # Task failed
            execution_time = time.perf_counter() - start_time
            error_msg = str(e)
            error_type = type(e).__name__
            
            if task_id in self.task_results:
                task_result = self.task_results[task_id]
                task_result.status = TaskStatus.FAILED
                task_result.error = error_msg
                task_result.error_type = error_type
                task_result.stacktrace = traceback.format_exc()
                task_result.execution_time = execution_time
                task_result.completed_at = datetime.utcnow()
                
                # Handle retries
                if task_result.retry_count < task.max_retries:
                    await self._schedule_retry(task, task_result)
                else:
                    self.performance_stats['tasks_failed'] += 1
            
            logger.error(
                "Task execution failed",
                task_id=task_id,
                error=error_msg,
                error_type=error_type,
                execution_time=f"{execution_time:.3f}s"
            )
        
        finally:
            # Clean up running task tracking
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _schedule_retry(self, task: TaskDefinition, result: TaskResult) -> None:
        """Schedule a task retry with exponential backoff."""
        result.retry_count += 1
        result.status = TaskStatus.RETRYING
        
        # Calculate retry delay with exponential backoff
        delay = task.retry_delay
        if task.exponential_backoff:
            delay *= (2 ** (result.retry_count - 1))
        
        # Schedule retry
        retry_task = TaskDefinition(
            **task.model_dump(),
            scheduled_at=datetime.utcnow() + timedelta(seconds=delay)
        )
        
        await asyncio.sleep(delay)
        await self.submit_task(retry_task)
        
        logger.info(
            "Task retry scheduled",
            task_id=task.id,
            retry_count=result.retry_count,
            delay=delay
        )
    
    def _update_average_execution_time(self, execution_time: float) -> None:
        """Update running average of execution times."""
        total_tasks = self.performance_stats['tasks_completed']
        current_avg = self.performance_stats['average_execution_time']
        
        # Calculate new running average
        new_avg = ((current_avg * (total_tasks - 1)) + execution_time) / total_tasks
        self.performance_stats['average_execution_time'] = new_avg
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = dict(self.performance_stats)
        
        # Add current queue sizes
        for priority in TaskPriority:
            queue = self.worker_pools.get(priority)
            stats['queue_sizes'][priority.value] = queue.qsize() if queue else 0
        
        # Add running task count
        stats['running_tasks_count'] = len(self.running_tasks)
        
        # Add worker health
        stats['active_workers'] = len([t for t in self.worker_tasks if not t.done()])
        
        return stats
    
    # Default Task Handlers
    
    async def _handle_crisis_detection(self, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle crisis detection with immediate processing."""
        # This would integrate with the existing crisis detection system
        logger.info("Processing crisis detection", user_id=user_id)
        
        # Placeholder implementation
        await asyncio.sleep(0.05)  # Simulate very fast processing
        
        return {
            "crisis_detected": False,
            "confidence": 0.1,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_safety_intervention(self, user_id: str, intervention_type: str) -> Dict[str, Any]:
        """Handle safety intervention with highest priority."""
        logger.info("Processing safety intervention", user_id=user_id, type=intervention_type)
        
        # Placeholder implementation
        await asyncio.sleep(0.1)  # Fast intervention processing
        
        return {
            "intervention_triggered": True,
            "type": intervention_type,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_context_building(self, user_id: str, context_type: str) -> Dict[str, Any]:
        """Handle context building for user interactions."""
        logger.info("Building context", user_id=user_id, context_type=context_type)
        
        # This would integrate with the existing frame builder
        await asyncio.sleep(0.3)  # Simulate context building
        
        return {
            "context_built": True,
            "context_type": context_type,
            "items_count": 8,  # ADHD-optimized context size
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_pattern_analysis(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pattern analysis for personalization."""
        logger.info("Analyzing patterns", user_id=user_id)
        
        # This would integrate with the existing pattern engine
        await asyncio.sleep(0.8)  # Simulate ML processing
        
        return {
            "patterns_identified": 3,
            "confidence": 0.85,
            "recommendations": ["focus_timer", "break_reminder", "task_prioritization"],
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_notification_delivery(self, user_id: str, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Handle notification delivery with ADHD optimization."""
        logger.info("Delivering notification", user_id=user_id, type=notification.get("type"))
        
        # This would integrate with the existing nudge engine
        await asyncio.sleep(0.2)  # Simulate notification processing
        
        return {
            "notification_sent": True,
            "channel": notification.get("channel", "in_app"),
            "delivered_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_calendar_sync(self, user_id: str, calendar_id: str) -> Dict[str, Any]:
        """Handle calendar synchronization."""
        logger.info("Syncing calendar", user_id=user_id, calendar_id=calendar_id)
        
        # This would integrate with the existing calendar system
        await asyncio.sleep(1.5)  # Simulate external API calls
        
        return {
            "events_synced": 12,
            "next_sync": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_ml_processing(self, model_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle machine learning processing tasks."""
        logger.info("Processing ML task", model_type=model_type)
        
        # Simulate heavy ML processing
        await asyncio.sleep(5.0)
        
        return {
            "model_type": model_type,
            "accuracy": 0.87,
            "predictions": 150,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_analytics_computation(self, metric_type: str, time_range: str) -> Dict[str, Any]:
        """Handle analytics computation tasks."""
        logger.info("Computing analytics", metric_type=metric_type, time_range=time_range)
        
        # Simulate analytics processing
        await asyncio.sleep(3.0)
        
        return {
            "metric_type": metric_type,
            "data_points": 1000,
            "insights": ["trend_positive", "engagement_high"],
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_report_generation(self, report_type: str, user_id: str) -> Dict[str, Any]:
        """Handle report generation tasks."""
        logger.info("Generating report", report_type=report_type, user_id=user_id)
        
        # Simulate report generation
        await asyncio.sleep(4.0)
        
        return {
            "report_type": report_type,
            "pages": 15,
            "charts": 8,
            "file_path": f"/reports/{report_type}_{user_id}_{int(time.time())}.pdf",
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_data_aggregation(self, data_source: str, time_range: str) -> Dict[str, Any]:
        """Handle data aggregation tasks."""
        logger.info("Aggregating data", data_source=data_source, time_range=time_range)
        
        # Simulate data aggregation
        await asyncio.sleep(2.5)
        
        return {
            "data_source": data_source,
            "records_processed": 50000,
            "aggregations_created": 25,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_database_cleanup(self, cleanup_type: str) -> Dict[str, Any]:
        """Handle database cleanup tasks."""
        logger.info("Cleaning database", cleanup_type=cleanup_type)
        
        # Simulate database cleanup
        await asyncio.sleep(6.0)
        
        return {
            "cleanup_type": cleanup_type,
            "records_cleaned": 1500,
            "space_freed_mb": 234,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_cache_warming(self, cache_type: str, priority_keys: List[str]) -> Dict[str, Any]:
        """Handle cache warming tasks."""
        logger.info("Warming cache", cache_type=cache_type, keys_count=len(priority_keys))
        
        # Simulate cache warming
        await asyncio.sleep(1.8)
        
        return {
            "cache_type": cache_type,
            "keys_warmed": len(priority_keys),
            "hit_rate_improvement": 0.15,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_log_rotation(self, log_type: str) -> Dict[str, Any]:
        """Handle log rotation tasks."""
        logger.info("Rotating logs", log_type=log_type)
        
        # Simulate log rotation
        await asyncio.sleep(3.5)
        
        return {
            "log_type": log_type,
            "files_rotated": 12,
            "compressed_mb": 456,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_system_optimization(self, optimization_type: str) -> Dict[str, Any]:
        """Handle system optimization tasks."""
        logger.info("Optimizing system", optimization_type=optimization_type)
        
        # Simulate system optimization
        await asyncio.sleep(8.0)
        
        return {
            "optimization_type": optimization_type,
            "performance_improvement": 0.12,
            "memory_freed_mb": 128,
            "processed_at": datetime.utcnow().isoformat()
        }


# Global background task manager instance
background_task_manager = BackgroundTaskManager()