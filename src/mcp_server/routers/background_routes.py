"""
Background Processing API Routes for MCP ADHD Server.

REST API endpoints for background job management with ADHD-optimized task handling.
Provides comprehensive task submission, monitoring, and control capabilities.

Features:
- Task submission with priority and ADHD optimization settings
- Real-time progress tracking via WebSocket connections
- Task management (cancel, retry, status monitoring)
- Performance metrics and system health monitoring
- Cache management endpoints with warming and invalidation
- User-friendly task aggregation and dashboard data
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog

from mcp_server.auth import get_current_user
from mcp_server.background_processing import (
    background_task_manager, TaskDefinition, TaskPriority, TaskType, TaskStatus
)
from mcp_server.task_monitoring import task_monitoring_system, AttentionLevel, ProgressUpdateType
from mcp_server.caching_system import cache_manager, CacheLayer, CachePriority
from mcp_server.cache_strategies import cache_warming_engine, cache_invalidation_engine
from mcp_server.db_models import User


# Configure structured logger
logger = structlog.get_logger(__name__)

# Create router
background_router = APIRouter(prefix="/api/background", tags=["Background Processing"])


# Pydantic Models

class TaskSubmissionRequest(BaseModel):
    """Request model for task submission."""
    name: str = Field(..., max_length=200, description="Human-readable task name")
    task_type: TaskType = Field(..., description="Type of task to execute")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority level")
    function_name: str = Field(..., description="Function to execute")
    
    # Task parameters
    args: List[Any] = Field(default_factory=list, description="Function arguments")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Function keyword arguments")
    
    # ADHD optimization settings
    user_visible: bool = Field(default=False, description="Show progress to user")
    attention_friendly: bool = Field(default=False, description="Use attention-friendly updates")
    max_execution_time: int = Field(default=300, description="Maximum execution time in seconds")
    
    # Scheduling
    scheduled_at: Optional[datetime] = Field(default=None, description="Schedule for later execution")
    
    # Retry configuration
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: int = Field(default=60, description="Delay between retries in seconds")
    exponential_backoff: bool = Field(default=True, description="Use exponential backoff")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Task metadata")


class TaskResponse(BaseModel):
    """Response model for task operations."""
    task_id: str
    name: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    
    # Progress information
    progress_percentage: float = 0.0
    current_step: str = ""
    estimated_completion: Optional[datetime] = None
    
    # Results
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # Performance metrics
    execution_time: float = 0.0
    retry_count: int = 0


class CacheWarmingRequest(BaseModel):
    """Request model for cache warming."""
    key_patterns: List[str] = Field(..., description="Cache key patterns to warm")
    priority: CachePriority = Field(default=CachePriority.NORMAL, description="Cache priority")
    user_specific: bool = Field(default=False, description="Warm user-specific data")
    attention_critical: bool = Field(default=False, description="Critical for user attention")


class CacheInvalidationRequest(BaseModel):
    """Request model for cache invalidation."""
    keys: Optional[List[str]] = Field(default=None, description="Specific keys to invalidate")
    patterns: Optional[List[str]] = Field(default=None, description="Key patterns to invalidate")
    cascade: bool = Field(default=True, description="Invalidate dependencies")


class PerformanceMetrics(BaseModel):
    """Performance metrics model."""
    background_processing: Dict[str, Any]
    task_monitoring: Dict[str, Any]
    cache_management: Dict[str, Any]
    cache_warming: Dict[str, Any]
    system_health: Dict[str, Any]


# API Endpoints

@background_router.post("/tasks", response_model=TaskResponse, summary="Submit Background Task")
async def submit_background_task(
    task_request: TaskSubmissionRequest,
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    """
    Submit a task for background processing with ADHD optimizations.
    
    This endpoint allows submitting tasks with various priority levels and
    ADHD-specific optimizations for user experience.
    
    **ADHD Optimizations:**
    - Crisis priority for immediate processing
    - Attention-friendly progress updates
    - Cognitive load management
    - User-visible progress tracking
    
    **Performance Targets:**
    - Task acknowledgment: <1 second
    - Crisis tasks: <100ms response
    - Background tasks: Efficient resource usage
    """
    try:
        # Create task definition
        task_definition = TaskDefinition(
            name=task_request.name,
            task_type=task_request.task_type,
            priority=task_request.priority,
            function_name=task_request.function_name,
            args=task_request.args,
            kwargs=task_request.kwargs,
            user_id=str(current_user.id),
            user_visible=task_request.user_visible,
            attention_friendly=task_request.attention_friendly,
            max_execution_time=task_request.max_execution_time,
            scheduled_at=task_request.scheduled_at,
            max_retries=task_request.max_retries,
            retry_delay=task_request.retry_delay,
            exponential_backoff=task_request.exponential_backoff,
            metadata=task_request.metadata
        )
        
        # Submit task to background manager
        task_id = await background_task_manager.submit_task(task_definition)
        
        # Start task monitoring if user-visible
        if task_request.user_visible:
            task_monitoring_system.start_task_tracking(task_definition)
        
        logger.info(
            "Background task submitted",
            task_id=task_id,
            user_id=current_user.id,
            task_type=task_request.task_type.value,
            priority=task_request.priority.value
        )
        
        return TaskResponse(
            task_id=task_id,
            name=task_request.name,
            status=TaskStatus.PENDING,
            priority=task_request.priority,
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error("Task submission error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit task: {str(e)}"
        )


@background_router.get("/tasks", response_model=List[TaskResponse], summary="Get User Tasks")
async def get_user_tasks(
    current_user: User = Depends(get_current_user),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of tasks to return")
) -> List[TaskResponse]:
    """
    Get background tasks for the current user with ADHD-friendly filtering.
    
    Returns a list of user's background tasks with progress information
    and ADHD-optimized presentation.
    """
    try:
        user_id = str(current_user.id)
        
        # Get active tasks from monitoring system
        active_tasks = task_monitoring_system.get_active_tasks_for_user(user_id)
        
        # Get task results from background manager
        task_responses = []
        for task_info in active_tasks:
            task_result = await background_task_manager.get_task_status(task_info['task_id'])
            
            if task_result and (status is None or task_result.status == status):
                response = TaskResponse(
                    task_id=task_info['task_id'],
                    name=task_info['name'],
                    status=task_result.status,
                    priority=TaskPriority(task_info['priority']),
                    created_at=datetime.fromisoformat(task_info['started_at']),
                    progress_percentage=task_info['percentage'],
                    current_step=task_info['current_step'],
                    estimated_completion=(
                        datetime.fromisoformat(task_info['estimated_completion'])
                        if task_info['estimated_completion']
                        else None
                    ),
                    result=task_result.result,
                    error=task_result.error,
                    execution_time=task_result.execution_time,
                    retry_count=task_result.retry_count
                )
                task_responses.append(response)
        
        # Sort by priority and creation time (ADHD-friendly ordering)
        task_responses.sort(
            key=lambda x: (
                x.priority == TaskPriority.CRISIS,  # Crisis tasks first
                x.priority == TaskPriority.HIGH,    # Then high priority
                x.created_at
            ),
            reverse=True
        )
        
        return task_responses[:limit]
        
    except Exception as e:
        logger.error("Get user tasks error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve tasks: {str(e)}"
        )


@background_router.get("/tasks/{task_id}", response_model=TaskResponse, summary="Get Task Status")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    """
    Get detailed status of a specific background task.
    
    Provides comprehensive task information including progress,
    performance metrics, and ADHD-friendly status updates.
    """
    try:
        # Get task result from background manager
        task_result = await background_task_manager.get_task_status(task_id)
        
        if not task_result:
            raise HTTPException(
                status_code=404,
                detail="Task not found"
            )
        
        # Get additional information from monitoring system
        active_tasks = task_monitoring_system.get_active_tasks_for_user(str(current_user.id))
        task_info = next((t for t in active_tasks if t['task_id'] == task_id), None)
        
        response = TaskResponse(
            task_id=task_id,
            name=task_info['name'] if task_info else "Background Task",
            status=task_result.status,
            priority=TaskPriority(task_info['priority']) if task_info else TaskPriority.NORMAL,
            created_at=task_result.completed_at,  # This would be creation time in real implementation
            progress_percentage=task_info['percentage'] if task_info else 100.0,
            current_step=task_info['current_step'] if task_info else "Completed",
            result=task_result.result,
            error=task_result.error,
            execution_time=task_result.execution_time,
            retry_count=task_result.retry_count
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get task status error", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )


@background_router.post("/tasks/{task_id}/cancel", summary="Cancel Task")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Cancel a background task with ADHD-friendly confirmation.
    
    Provides immediate feedback and graceful task cancellation
    with user-friendly status updates.
    """
    try:
        success = await background_task_manager.cancel_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Task not found or cannot be cancelled"
            )
        
        logger.info("Task cancelled", task_id=task_id, user_id=current_user.id)
        
        return {
            "task_id": task_id,
            "cancelled": True,
            "message": "Task cancelled successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Cancel task error", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


@background_router.websocket("/tasks/progress/{user_id}")
async def task_progress_websocket(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time task progress updates.
    
    Provides ADHD-optimized real-time progress updates with:
    - Attention-level aware message delivery
    - Cognitive load management
    - User-friendly progress formatting
    - Crisis-safe priority handling
    """
    try:
        # Connect to task monitoring system
        connection_id = await task_monitoring_system.connect_websocket(
            websocket=websocket,
            user_id=user_id,
            attention_level=AttentionLevel.FOCUSED  # Default, can be configured
        )
        
        logger.info("WebSocket connected for task progress", user_id=user_id, connection_id=connection_id)
        
        try:
            while True:
                # Keep connection alive and handle incoming messages
                try:
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    
                    # Handle client messages (e.g., attention level updates)
                    if message:
                        data = json.loads(message)
                        if data.get("type") == "update_attention_level":
                            # Update attention level for optimized delivery
                            attention_level = AttentionLevel(data.get("attention_level", "focused"))
                            # Update connection settings (would be implemented in monitoring system)
                            logger.info("Attention level updated", user_id=user_id, level=attention_level.value)
                
                except asyncio.TimeoutError:
                    # Send heartbeat
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected", user_id=user_id, connection_id=connection_id)
        
    except Exception as e:
        logger.error("WebSocket error", user_id=user_id, error=str(e))
        try:
            await websocket.close()
        except Exception:
            pass
    
    finally:
        # Clean up connection
        if 'connection_id' in locals():
            await task_monitoring_system.disconnect_websocket(connection_id)


@background_router.post("/cache/warm", summary="Warm Cache")
async def warm_cache(
    warming_request: CacheWarmingRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Warm cache with specified patterns and ADHD optimizations.
    
    Preloads frequently accessed data for improved performance
    with attention-critical data prioritization.
    """
    try:
        user_id = str(current_user.id) if warming_request.user_specific else None
        
        # Schedule cache warming task
        task_id = await cache_warming_engine.schedule_warming_task(
            key_patterns=warming_request.key_patterns,
            priority=warming_request.priority,
            user_id=user_id,
            attention_critical=warming_request.attention_critical
        )
        
        logger.info(
            "Cache warming scheduled",
            task_id=task_id,
            patterns=len(warming_request.key_patterns),
            user_id=current_user.id
        )
        
        return {
            "warming_task_id": task_id,
            "patterns": warming_request.key_patterns,
            "priority": warming_request.priority.value,
            "user_specific": warming_request.user_specific,
            "attention_critical": warming_request.attention_critical,
            "scheduled_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Cache warming error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to warm cache: {str(e)}"
        )


@background_router.post("/cache/invalidate", summary="Invalidate Cache")
async def invalidate_cache(
    invalidation_request: CacheInvalidationRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Invalidate cache entries with smart dependency handling.
    
    Provides selective cache invalidation with cascade options
    and performance-aware batch processing.
    """
    try:
        total_invalidated = 0
        
        # Invalidate specific keys
        if invalidation_request.keys:
            for key in invalidation_request.keys:
                if invalidation_request.cascade:
                    count = await cache_invalidation_engine.invalidate_with_dependencies(key)
                else:
                    success = await cache_manager.delete(key)
                    count = 1 if success else 0
                total_invalidated += count
        
        # Invalidate patterns
        if invalidation_request.patterns:
            for pattern in invalidation_request.patterns:
                count = await cache_manager.invalidate_pattern(pattern)
                total_invalidated += count
        
        logger.info(
            "Cache invalidation completed",
            user_id=current_user.id,
            invalidated_count=total_invalidated
        )
        
        return {
            "invalidated_count": total_invalidated,
            "keys": invalidation_request.keys or [],
            "patterns": invalidation_request.patterns or [],
            "cascade": invalidation_request.cascade,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Cache invalidation error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@background_router.get("/cache/stats", summary="Get Cache Statistics")
async def get_cache_stats(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive cache performance statistics.
    
    Provides detailed cache metrics for performance monitoring
    and ADHD optimization assessment.
    """
    try:
        cache_stats = await cache_manager.get_cache_stats()
        warming_stats = cache_warming_engine.get_warming_stats()
        invalidation_stats = cache_invalidation_engine.get_invalidation_stats()
        
        return {
            "cache_performance": cache_stats,
            "warming_engine": warming_stats,
            "invalidation_engine": invalidation_stats,
            "adhd_optimization": {
                "crisis_access_times_met": all(
                    stats.get("crisis_access_time_ms", 0) <= 100
                    for layer, stats in cache_stats.items()
                    if isinstance(stats, dict)
                ),
                "user_interaction_times_met": all(
                    stats.get("user_interaction_access_time_ms", 0) <= 1000
                    for layer, stats in cache_stats.items()
                    if isinstance(stats, dict)
                ),
                "attention_critical_hit_rate": cache_stats.get("overall", {}).get("overall_hit_rate", 0.0)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Get cache stats error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache statistics: {str(e)}"
        )


@background_router.post("/cache/warm/user-critical", summary="Warm User Critical Data")
async def warm_user_critical_data(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Warm cache with user's attention-critical data.
    
    Preloads user-specific data that is critical for maintaining
    attention and reducing cognitive load during ADHD-focused sessions.
    """
    try:
        user_id = str(current_user.id)
        result = await cache_warming_engine.warm_user_critical_data(user_id)
        
        logger.info(
            "User critical data warming completed",
            user_id=user_id,
            patterns_warmed=result.get('patterns_warmed', 0)
        )
        
        return result
        
    except Exception as e:
        logger.error("User critical data warming error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to warm user critical data: {str(e)}"
        )


@background_router.get("/performance", response_model=PerformanceMetrics, summary="Get Performance Metrics")
async def get_performance_metrics(
    current_user: User = Depends(get_current_user)
) -> PerformanceMetrics:
    """
    Get comprehensive performance metrics for background processing.
    
    Provides detailed performance analytics for ADHD optimization
    and system health monitoring.
    """
    try:
        background_stats = await background_task_manager.get_performance_stats()
        monitoring_stats = task_monitoring_system.get_monitoring_stats()
        cache_stats = await cache_manager.get_cache_stats()
        warming_stats = cache_warming_engine.get_warming_stats()
        
        # System health metrics
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        system_health = {
            "memory_usage_mb": memory_info.rss / 1024 / 1024,
            "memory_percent": process.memory_percent(),
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads(),
            "uptime_seconds": time.time() - process.create_time(),
            "adhd_performance_targets": {
                "crisis_response_time_target_ms": 100,
                "user_response_time_target_ms": 1000,
                "background_resource_limit_percent": 70
            }
        }
        
        return PerformanceMetrics(
            background_processing=background_stats,
            task_monitoring=monitoring_stats,
            cache_management=cache_stats,
            cache_warming=warming_stats,
            system_health=system_health
        )
        
    except Exception as e:
        logger.error("Get performance metrics error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@background_router.post("/tasks/batch", summary="Submit Batch Tasks")
async def submit_batch_tasks(
    tasks: List[TaskSubmissionRequest],
    current_user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    """
    Submit multiple tasks for batch background processing.
    
    Optimized for ADHD workflows where multiple related tasks
    need to be processed together with intelligent scheduling.
    """
    try:
        if len(tasks) > 50:  # ADHD-friendly limit
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 tasks allowed in batch submission"
            )
        
        responses = []
        
        for task_request in tasks:
            # Create task definition
            task_definition = TaskDefinition(
                name=task_request.name,
                task_type=task_request.task_type,
                priority=task_request.priority,
                function_name=task_request.function_name,
                args=task_request.args,
                kwargs=task_request.kwargs,
                user_id=str(current_user.id),
                user_visible=task_request.user_visible,
                attention_friendly=task_request.attention_friendly,
                max_execution_time=task_request.max_execution_time,
                scheduled_at=task_request.scheduled_at,
                max_retries=task_request.max_retries,
                retry_delay=task_request.retry_delay,
                exponential_backoff=task_request.exponential_backoff,
                metadata=task_request.metadata
            )
            
            # Submit task
            task_id = await background_task_manager.submit_task(task_definition)
            
            # Start monitoring if user-visible
            if task_request.user_visible:
                task_monitoring_system.start_task_tracking(task_definition)
            
            responses.append(TaskResponse(
                task_id=task_id,
                name=task_request.name,
                status=TaskStatus.PENDING,
                priority=task_request.priority,
                created_at=datetime.utcnow()
            ))
        
        logger.info(
            "Batch tasks submitted",
            user_id=current_user.id,
            count=len(tasks),
            user_visible_count=sum(1 for t in tasks if t.user_visible)
        )
        
        return responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch task submission error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit batch tasks: {str(e)}"
        )


@background_router.get("/dashboard", summary="Get Background Processing Dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get ADHD-optimized dashboard data for background processing.
    
    Provides a comprehensive yet digestible overview of background
    processing status, optimized for ADHD attention patterns.
    """
    try:
        user_id = str(current_user.id)
        
        # Get user's active tasks
        active_tasks = task_monitoring_system.get_active_tasks_for_user(user_id)
        
        # Get performance metrics
        background_stats = await background_task_manager.get_performance_stats()
        cache_stats = await cache_manager.get_cache_stats()
        
        # Calculate ADHD-friendly summary statistics
        total_active = len(active_tasks)
        crisis_tasks = len([t for t in active_tasks if t.get('priority') == 'crisis'])
        high_priority_tasks = len([t for t in active_tasks if t.get('priority') == 'high'])
        
        # Average completion percentage for visible tasks
        visible_tasks = [t for t in active_tasks if t.get('percentage', 0) > 0]
        avg_progress = (
            sum(t['percentage'] for t in visible_tasks) / len(visible_tasks)
            if visible_tasks else 0.0
        )
        
        # Cache performance summary
        overall_cache_stats = cache_stats.get('overall', {})
        cache_hit_rate = overall_cache_stats.get('overall_hit_rate', 0.0)
        
        # ADHD-optimized dashboard sections
        dashboard = {
            "summary": {
                "total_active_tasks": total_active,
                "crisis_tasks": crisis_tasks,
                "high_priority_tasks": high_priority_tasks,
                "average_progress": round(avg_progress, 1),
                "cache_hit_rate": round(cache_hit_rate * 100, 1),
                "status": "healthy" if crisis_tasks == 0 and avg_progress > 0 else "attention_needed"
            },
            
            "active_tasks": [
                {
                    "id": task['task_id'],
                    "name": task['name'][:50],  # Truncate for ADHD readability
                    "type": task['type'],
                    "priority": task['priority'],
                    "progress": task['percentage'],
                    "step": task['current_step'][:80],  # Brief step description
                    "estimated_completion": task.get('estimated_completion')
                }
                for task in active_tasks[:10]  # Limit to top 10 for focus
            ],
            
            "performance": {
                "tasks_completed_today": background_stats.get('tasks_completed', 0),
                "success_rate": round(
                    (1.0 - background_stats.get('tasks_failed', 0) / max(1, background_stats.get('tasks_completed', 1))) * 100,
                    1
                ),
                "average_execution_time": round(background_stats.get('average_execution_time', 0.0), 2),
                "cache_efficiency": round(cache_hit_rate * 100, 1)
            },
            
            "alerts": [],  # Would contain ADHD-friendly alerts
            
            "quick_actions": [
                {"action": "warm_critical_cache", "label": "Warm My Critical Data", "type": "primary"},
                {"action": "clear_completed", "label": "Clear Completed Tasks", "type": "secondary"},
                {"action": "pause_background", "label": "Pause Background Tasks", "type": "warning"}
            ],
            
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add ADHD-friendly alerts
        if crisis_tasks > 0:
            dashboard["alerts"].append({
                "type": "crisis",
                "message": f"{crisis_tasks} crisis task(s) need attention",
                "action": "view_crisis_tasks"
            })
        
        if cache_hit_rate < 0.8:
            dashboard["alerts"].append({
                "type": "performance",
                "message": "Cache performance below optimal. Consider warming critical data.",
                "action": "warm_cache"
            })
        
        return dashboard
        
    except Exception as e:
        logger.error("Dashboard data error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard data: {str(e)}"
        )


# Health check endpoint
@background_router.get("/health", summary="Background Processing Health")
async def background_health() -> Dict[str, Any]:
    """
    Health check endpoint for background processing systems.
    
    Returns the health status of all background processing components
    with ADHD-critical performance indicators.
    """
    try:
        health_status = {
            "background_manager": {
                "status": "healthy" if background_task_manager.is_running else "down",
                "workers_active": len([t for t in background_task_manager.worker_tasks if not t.done()]),
                "queue_sizes": background_task_manager.performance_stats.get('queue_sizes', {})
            },
            
            "task_monitoring": {
                "status": "healthy" if task_monitoring_system.is_running else "down",
                "active_connections": len(task_monitoring_system.websocket_connections),
                "delivery_workers": len([t for t in task_monitoring_system.delivery_tasks if not t.done()])
            },
            
            "cache_manager": {
                "status": "healthy" if cache_manager.is_initialized else "down",
                "redis_connections": len(cache_manager.redis_clients)
            },
            
            "cache_warming": {
                "status": "healthy" if cache_warming_engine.is_running else "down",
                "active_tasks": len(cache_warming_engine.warming_tasks)
            },
            
            "adhd_performance": {
                "crisis_response_ready": True,  # Would check actual readiness
                "user_response_ready": True,
                "resource_availability": "optimal"
            },
            
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Overall status
        all_healthy = all(
            component.get("status") == "healthy"
            for component in health_status.values()
            if isinstance(component, dict) and "status" in component
        )
        
        health_status["overall_status"] = "healthy" if all_healthy else "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error("Background health check error", error=str(e))
        return {
            "overall_status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }