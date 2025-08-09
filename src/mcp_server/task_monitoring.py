"""
Task Monitoring and Progress Tracking System for MCP ADHD Server.

Real-time task monitoring with ADHD-optimized progress updates and user-friendly notifications.
Provides WebSocket-based progress tracking, intelligent status updates, and attention-friendly messaging.

Features:
- Real-time progress updates via WebSocket connections
- ADHD-optimized progress messaging with cognitive load management
- Intelligent progress aggregation for complex multi-step tasks
- User attention tracking and interruption-friendly updates
- Crisis-safe monitoring with priority escalation
- Performance metrics and bottleneck detection
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Union
from uuid import uuid4
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
import structlog

from mcp_server.background_processing import TaskDefinition, TaskResult, TaskStatus, TaskPriority
from mcp_server.config import settings


# Configure structured logger
logger = structlog.get_logger(__name__)


class ProgressUpdateType(str, Enum):
    """Types of progress updates for different user attention needs."""
    IMMEDIATE = "immediate"       # Crisis/safety updates, show immediately
    HIGH_PRIORITY = "high"        # User-initiated tasks, show prominently
    BACKGROUND = "background"     # Background tasks, minimal interruption
    SUMMARY = "summary"           # Aggregated progress for multiple tasks
    COMPLETION = "completion"     # Task completion notifications


class AttentionLevel(str, Enum):
    """User attention levels for optimizing progress updates."""
    FOCUSED = "focused"           # User is focused, can handle detailed updates
    MULTITASKING = "multitasking" # User is multitasking, brief updates only
    DISTRACTED = "distracted"     # User is distracted, minimal interruptions
    HYPERFOCUS = "hyperfocus"     # User in hyperfocus, emergency updates only
    AWAY = "away"                 # User is away, queue updates for return


class ProgressUpdate(BaseModel):
    """Progress update message optimized for ADHD users."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    update_type: ProgressUpdateType
    
    # Progress information
    percentage: float = Field(ge=0, le=100)
    current_step: str
    total_steps: int
    estimated_completion: Optional[datetime] = None
    
    # ADHD-optimized messaging
    brief_message: str = Field(max_length=80)  # Tweet-length for quick scanning
    detailed_message: str = Field(max_length=200)  # Longer but still digestible
    friendly_message: str = Field(max_length=150)  # Encouraging, positive tone
    
    # User experience optimization
    requires_attention: bool = False
    allows_interruption: bool = True
    cognitive_load_score: float = Field(default=1.0, ge=0, le=5.0)
    
    # Timing and context
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    
    # Visual and interaction hints
    color_hint: str = "blue"  # blue, green, yellow, red for different states
    icon_hint: str = "progress"  # Icon suggestions for UI
    action_buttons: List[Dict[str, str]] = Field(default_factory=list)


class TaskProgressTracker:
    """Tracks progress for individual tasks with ADHD optimizations."""
    
    def __init__(self, task: TaskDefinition):
        self.task = task
        self.updates: List[ProgressUpdate] = []
        self.current_percentage = 0.0
        self.current_step = "Preparing..."
        self.total_steps = 1
        self.started_at = datetime.utcnow()
        self.last_update_at = datetime.utcnow()
        
        # ADHD optimization tracking
        self.attention_friendly_updates = 0
        self.user_interruptions = 0
        self.pause_count = 0
        self.resume_count = 0
    
    def update_progress(
        self,
        percentage: float,
        current_step: str,
        total_steps: Optional[int] = None,
        brief_message: Optional[str] = None,
        update_type: ProgressUpdateType = ProgressUpdateType.BACKGROUND
    ) -> ProgressUpdate:
        """Update task progress with ADHD-optimized messaging."""
        
        self.current_percentage = min(100.0, max(0.0, percentage))
        self.current_step = current_step
        if total_steps:
            self.total_steps = total_steps
        
        # Generate ADHD-optimized messages
        if not brief_message:
            brief_message = self._generate_brief_message()
        
        detailed_message = self._generate_detailed_message()
        friendly_message = self._generate_friendly_message()
        
        # Calculate estimated completion
        elapsed_time = (datetime.utcnow() - self.started_at).total_seconds()
        if percentage > 0:
            estimated_total_time = elapsed_time / (percentage / 100.0)
            remaining_time = estimated_total_time - elapsed_time
            estimated_completion = datetime.utcnow() + timedelta(seconds=remaining_time)
        else:
            estimated_completion = None
        
        # Create progress update
        update = ProgressUpdate(
            task_id=self.task.id,
            update_type=update_type,
            percentage=self.current_percentage,
            current_step=current_step,
            total_steps=self.total_steps,
            estimated_completion=estimated_completion,
            brief_message=brief_message,
            detailed_message=detailed_message,
            friendly_message=friendly_message,
            user_id=self.task.user_id,
            requires_attention=(
                self.task.priority == TaskPriority.CRISIS or 
                update_type == ProgressUpdateType.IMMEDIATE
            ),
            allows_interruption=(
                self.task.priority != TaskPriority.CRISIS and 
                update_type != ProgressUpdateType.IMMEDIATE
            ),
            cognitive_load_score=self._calculate_cognitive_load(),
            color_hint=self._get_color_hint(),
            icon_hint=self._get_icon_hint()
        )
        
        self.updates.append(update)
        self.last_update_at = datetime.utcnow()
        
        # Track ADHD optimization metrics
        if update.cognitive_load_score <= 2.0:
            self.attention_friendly_updates += 1
        
        return update
    
    def _generate_brief_message(self) -> str:
        """Generate brief, scannable message for quick user comprehension."""
        if self.current_percentage == 0:
            return f"Starting {self.task.name}..."
        elif self.current_percentage == 100:
            return f"✅ {self.task.name} complete!"
        else:
            return f"{self.task.name}: {int(self.current_percentage)}% ({self.current_step})"
    
    def _generate_detailed_message(self) -> str:
        """Generate detailed message with context for focused users."""
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        elapsed_str = f"{int(elapsed//60)}m {int(elapsed%60)}s" if elapsed >= 60 else f"{int(elapsed)}s"
        
        if self.current_percentage == 100:
            return f"Task '{self.task.name}' completed successfully in {elapsed_str}. All steps finished."
        else:
            return f"Task '{self.task.name}' is {int(self.current_percentage)}% complete. Currently: {self.current_step} (Step {self.total_steps - int((100 - self.current_percentage) / 100 * self.total_steps)} of {self.total_steps}). Runtime: {elapsed_str}."
    
    def _generate_friendly_message(self) -> str:
        """Generate encouraging, positive message for user motivation."""
        if self.current_percentage == 0:
            return f"🚀 Getting started with {self.task.name}. You've got this!"
        elif self.current_percentage < 25:
            return f"🌱 Making progress on {self.task.name}. Great start!"
        elif self.current_percentage < 50:
            return f"⚡ {self.task.name} is moving along nicely. Keep it up!"
        elif self.current_percentage < 75:
            return f"🔥 Over halfway done with {self.task.name}. You're crushing it!"
        elif self.current_percentage < 100:
            return f"🎯 Almost there! {self.task.name} is nearly complete."
        else:
            return f"🎉 Awesome! {self.task.name} is all done. Time to celebrate!"
    
    def _calculate_cognitive_load(self) -> float:
        """Calculate cognitive load score for ADHD optimization."""
        base_load = 1.0
        
        # Increase load for crisis tasks
        if self.task.priority == TaskPriority.CRISIS:
            base_load += 2.0
        
        # Increase load for user-visible tasks
        if self.task.user_visible:
            base_load += 0.5
        
        # Reduce load for background tasks
        if not self.task.user_visible:
            base_load -= 0.3
        
        # Adjust based on task complexity (estimated by execution time)
        if self.task.max_execution_time > 300:  # > 5 minutes
            base_load += 0.5
        
        return max(0.0, min(5.0, base_load))
    
    def _get_color_hint(self) -> str:
        """Get color hint based on task status and priority."""
        if self.task.priority == TaskPriority.CRISIS:
            return "red"
        elif self.current_percentage == 100:
            return "green"
        elif self.current_percentage >= 75:
            return "blue"
        elif self.current_percentage >= 50:
            return "yellow"
        else:
            return "gray"
    
    def _get_icon_hint(self) -> str:
        """Get icon hint based on task type and status."""
        if self.current_percentage == 100:
            return "check-circle"
        elif self.task.priority == TaskPriority.CRISIS:
            return "alert-triangle"
        elif self.task.user_visible:
            return "activity"
        else:
            return "clock"


@dataclass
class WebSocketConnection:
    """WebSocket connection with user context and preferences."""
    websocket: WebSocket
    user_id: str
    connection_id: str = field(default_factory=lambda: str(uuid4()))
    connected_at: datetime = field(default_factory=datetime.utcnow)
    
    # ADHD optimization preferences
    attention_level: AttentionLevel = AttentionLevel.FOCUSED
    max_updates_per_minute: int = 10
    preferred_message_type: str = "brief"  # brief, detailed, friendly
    
    # Tracking
    messages_sent: int = 0
    last_activity: datetime = field(default_factory=datetime.utcnow)


class TaskMonitoringSystem:
    """
    Real-time task monitoring system with ADHD optimizations.
    
    Features:
    - WebSocket-based real-time progress updates
    - ADHD-optimized message delivery and cognitive load management
    - User attention tracking and interruption management
    - Intelligent progress aggregation for complex workflows
    - Performance monitoring and bottleneck detection
    """
    
    def __init__(self):
        self.active_trackers: Dict[str, TaskProgressTracker] = {}
        self.websocket_connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        
        # Progress update queue for delivery optimization
        self.update_queue: asyncio.Queue = asyncio.Queue()
        self.delivery_tasks: List[asyncio.Task] = []
        
        # Performance tracking
        self.monitoring_stats = {
            'total_updates_sent': 0,
            'average_delivery_time_ms': 0.0,
            'connections_active': 0,
            'attention_friendly_delivery_rate': 0.0
        }
        
        self.is_running = False
    
    async def initialize(self) -> None:
        """Initialize the task monitoring system."""
        try:
            # Start delivery workers
            self.is_running = True
            
            # Start background tasks
            for i in range(3):  # 3 delivery workers for high throughput
                worker = asyncio.create_task(
                    self._delivery_worker(i),
                    name=f"progress-delivery-worker-{i}"
                )
                self.delivery_tasks.append(worker)
            
            # Start monitoring and cleanup tasks
            asyncio.create_task(self._monitoring_loop())
            asyncio.create_task(self._cleanup_loop())
            
            logger.info("Task monitoring system initialized")
            
        except Exception as e:
            logger.error("Failed to initialize task monitoring system", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the task monitoring system gracefully."""
        logger.info("Shutting down task monitoring system")
        
        self.is_running = False
        
        # Close all WebSocket connections
        for connection in list(self.websocket_connections.values()):
            try:
                await connection.websocket.close()
            except Exception:
                pass  # Connection might already be closed
        
        # Cancel delivery tasks
        for task in self.delivery_tasks:
            if not task.done():
                task.cancel()
        
        if self.delivery_tasks:
            await asyncio.gather(*self.delivery_tasks, return_exceptions=True)
        
        logger.info("Task monitoring system shutdown complete")
    
    async def connect_websocket(
        self,
        websocket: WebSocket,
        user_id: str,
        attention_level: AttentionLevel = AttentionLevel.FOCUSED
    ) -> str:
        """Connect a WebSocket for real-time progress updates."""
        try:
            await websocket.accept()
            
            connection = WebSocketConnection(
                websocket=websocket,
                user_id=user_id,
                attention_level=attention_level
            )
            
            # Store connection
            self.websocket_connections[connection.connection_id] = connection
            
            # Track user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection.connection_id)
            
            # Update statistics
            self.monitoring_stats['connections_active'] = len(self.websocket_connections)
            
            logger.info(
                "WebSocket connected for task monitoring",
                user_id=user_id,
                connection_id=connection.connection_id,
                attention_level=attention_level.value
            )
            
            # Send welcome message with connection info
            await self._send_to_connection(connection, {
                "type": "connection_established",
                "connection_id": connection.connection_id,
                "message": "Connected to task monitoring system",
                "features": ["real_time_progress", "adhd_optimized", "attention_aware"]
            })
            
            return connection.connection_id
            
        except Exception as e:
            logger.error("Failed to connect WebSocket", user_id=user_id, error=str(e))
            raise
    
    async def disconnect_websocket(self, connection_id: str) -> None:
        """Disconnect a WebSocket connection."""
        try:
            if connection_id in self.websocket_connections:
                connection = self.websocket_connections[connection_id]
                
                # Remove from user connections
                if connection.user_id in self.user_connections:
                    self.user_connections[connection.user_id].discard(connection_id)
                    if not self.user_connections[connection.user_id]:
                        del self.user_connections[connection.user_id]
                
                # Remove connection
                del self.websocket_connections[connection_id]
                
                # Update statistics
                self.monitoring_stats['connections_active'] = len(self.websocket_connections)
                
                logger.info("WebSocket disconnected", connection_id=connection_id)
        
        except Exception as e:
            logger.error("Error disconnecting WebSocket", connection_id=connection_id, error=str(e))
    
    def start_task_tracking(self, task: TaskDefinition) -> TaskProgressTracker:
        """Start tracking progress for a task."""
        tracker = TaskProgressTracker(task)
        self.active_trackers[task.id] = tracker
        
        # Send initial progress update
        initial_update = tracker.update_progress(
            0.0,
            "Task started",
            update_type=ProgressUpdateType.HIGH_PRIORITY if task.user_visible else ProgressUpdateType.BACKGROUND
        )
        
        # Queue for delivery
        asyncio.create_task(self._queue_update(initial_update))
        
        logger.info("Started task tracking", task_id=task.id, task_name=task.name)
        return tracker
    
    def update_task_progress(
        self,
        task_id: str,
        percentage: float,
        current_step: str,
        total_steps: Optional[int] = None,
        brief_message: Optional[str] = None,
        update_type: ProgressUpdateType = ProgressUpdateType.BACKGROUND
    ) -> Optional[ProgressUpdate]:
        """Update task progress and notify connected clients."""
        
        if task_id not in self.active_trackers:
            logger.warning("Attempted to update progress for unknown task", task_id=task_id)
            return None
        
        tracker = self.active_trackers[task_id]
        
        # Update progress
        update = tracker.update_progress(
            percentage=percentage,
            current_step=current_step,
            total_steps=total_steps,
            brief_message=brief_message,
            update_type=update_type
        )
        
        # Queue update for delivery
        asyncio.create_task(self._queue_update(update))
        
        logger.debug(
            "Task progress updated",
            task_id=task_id,
            percentage=percentage,
            step=current_step
        )
        
        return update
    
    def complete_task_tracking(self, task_id: str, result: TaskResult) -> None:
        """Complete task tracking and send final update."""
        
        if task_id not in self.active_trackers:
            logger.warning("Attempted to complete tracking for unknown task", task_id=task_id)
            return
        
        tracker = self.active_trackers[task_id]
        
        # Create completion update
        if result.status == TaskStatus.COMPLETED:
            update = tracker.update_progress(
                100.0,
                "Task completed successfully",
                update_type=ProgressUpdateType.COMPLETION
            )
            update.color_hint = "green"
            update.icon_hint = "check-circle"
        else:
            update = tracker.update_progress(
                tracker.current_percentage,
                f"Task {result.status.value}",
                update_type=ProgressUpdateType.COMPLETION
            )
            update.color_hint = "red" if result.status == TaskStatus.FAILED else "yellow"
            update.icon_hint = "x-circle" if result.status == TaskStatus.FAILED else "pause-circle"
        
        # Add action buttons for failed tasks
        if result.status == TaskStatus.FAILED and tracker.task.max_retries > result.retry_count:
            update.action_buttons.append({
                "action": "retry",
                "label": "Retry Task",
                "variant": "primary"
            })
        
        # Queue completion update
        asyncio.create_task(self._queue_update(update))
        
        # Clean up tracker
        del self.active_trackers[task_id]
        
        logger.info("Task tracking completed", task_id=task_id, status=result.status.value)
    
    def get_active_tasks_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active tasks for a specific user."""
        user_tasks = []
        
        for tracker in self.active_trackers.values():
            if tracker.task.user_id == user_id:
                user_tasks.append({
                    'task_id': tracker.task.id,
                    'name': tracker.task.name,
                    'type': tracker.task.task_type.value,
                    'priority': tracker.task.priority.value,
                    'percentage': tracker.current_percentage,
                    'current_step': tracker.current_step,
                    'started_at': tracker.started_at.isoformat(),
                    'estimated_completion': (
                        tracker.updates[-1].estimated_completion.isoformat()
                        if tracker.updates and tracker.updates[-1].estimated_completion
                        else None
                    )
                })
        
        return user_tasks
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get comprehensive monitoring statistics."""
        stats = dict(self.monitoring_stats)
        
        # Add current state info
        stats.update({
            'active_tasks': len(self.active_trackers),
            'connected_users': len(self.user_connections),
            'total_connections': len(self.websocket_connections),
            'queue_size': self.update_queue.qsize(),
            'delivery_workers': len([t for t in self.delivery_tasks if not t.done()])
        })
        
        # Add ADHD optimization metrics
        total_updates = sum(len(tracker.updates) for tracker in self.active_trackers.values())
        attention_friendly_updates = sum(
            tracker.attention_friendly_updates for tracker in self.active_trackers.values()
        )
        
        if total_updates > 0:
            stats['attention_friendly_delivery_rate'] = attention_friendly_updates / total_updates
        
        return stats
    
    async def _queue_update(self, update: ProgressUpdate) -> None:
        """Queue a progress update for delivery."""
        await self.update_queue.put(update)
    
    async def _delivery_worker(self, worker_id: int) -> None:
        """Background worker for delivering progress updates."""
        logger.info("Progress delivery worker started", worker_id=worker_id)
        
        while self.is_running:
            try:
                # Wait for update with timeout
                try:
                    update = await asyncio.wait_for(self.update_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                
                # Deliver update to relevant connections
                await self._deliver_update(update)
                
                # Update statistics
                self.monitoring_stats['total_updates_sent'] += 1
                
            except asyncio.CancelledError:
                logger.info("Progress delivery worker cancelled", worker_id=worker_id)
                break
            except Exception as e:
                logger.error("Progress delivery worker error", worker_id=worker_id, error=str(e))
                await asyncio.sleep(1)  # Brief pause before retry
        
        logger.info("Progress delivery worker stopped", worker_id=worker_id)
    
    async def _deliver_update(self, update: ProgressUpdate) -> None:
        """Deliver progress update to relevant WebSocket connections."""
        delivery_start = time.perf_counter()
        
        try:
            # Find relevant connections
            target_connections = []
            
            if update.user_id:
                # Deliver to specific user's connections
                if update.user_id in self.user_connections:
                    for conn_id in self.user_connections[update.user_id]:
                        if conn_id in self.websocket_connections:
                            target_connections.append(self.websocket_connections[conn_id])
            else:
                # Deliver to all connections (system-wide updates)
                target_connections = list(self.websocket_connections.values())
            
            # Deliver to each connection with ADHD optimizations
            delivery_tasks = []
            for connection in target_connections:
                # Check if user should receive this update based on attention level
                if self._should_deliver_update(update, connection):
                    delivery_tasks.append(
                        self._deliver_to_connection(update, connection)
                    )
            
            # Send updates in parallel
            if delivery_tasks:
                await asyncio.gather(*delivery_tasks, return_exceptions=True)
            
            # Update delivery time statistics
            delivery_time = (time.perf_counter() - delivery_start) * 1000
            current_avg = self.monitoring_stats['average_delivery_time_ms']
            
            if current_avg == 0:
                self.monitoring_stats['average_delivery_time_ms'] = delivery_time
            else:
                # Update running average
                total_sent = self.monitoring_stats['total_updates_sent']
                new_avg = ((current_avg * (total_sent - 1)) + delivery_time) / total_sent
                self.monitoring_stats['average_delivery_time_ms'] = new_avg
            
        except Exception as e:
            logger.error("Update delivery error", update_id=update.id, error=str(e))
    
    def _should_deliver_update(self, update: ProgressUpdate, connection: WebSocketConnection) -> bool:
        """Determine if update should be delivered based on ADHD optimizations."""
        
        # Always deliver crisis updates
        if update.update_type == ProgressUpdateType.IMMEDIATE:
            return True
        
        # Check attention level
        if connection.attention_level == AttentionLevel.HYPERFOCUS:
            # Only deliver crisis updates during hyperfocus
            return update.update_type == ProgressUpdateType.IMMEDIATE
        
        if connection.attention_level == AttentionLevel.AWAY:
            # Queue updates for when user returns
            return False
        
        # Check rate limiting
        current_time = datetime.utcnow()
        time_window = current_time - timedelta(minutes=1)
        
        if connection.last_activity < time_window:
            # Reset message count for new time window
            connection.messages_sent = 0
            connection.last_activity = current_time
        
        if connection.messages_sent >= connection.max_updates_per_minute:
            # Rate limit exceeded, only deliver high priority updates
            return update.update_type in [ProgressUpdateType.IMMEDIATE, ProgressUpdateType.HIGH_PRIORITY]
        
        # Check cognitive load
        if update.cognitive_load_score > 3.0 and connection.attention_level == AttentionLevel.DISTRACTED:
            # Skip high cognitive load updates for distracted users
            return False
        
        return True
    
    async def _deliver_to_connection(self, update: ProgressUpdate, connection: WebSocketConnection) -> None:
        """Deliver update to a specific WebSocket connection."""
        try:
            # Choose appropriate message based on connection preferences
            message_text = update.brief_message
            if connection.preferred_message_type == "detailed":
                message_text = update.detailed_message
            elif connection.preferred_message_type == "friendly":
                message_text = update.friendly_message
            
            # Create delivery payload
            payload = {
                "type": "progress_update",
                "update_id": update.id,
                "task_id": update.task_id,
                "update_type": update.update_type.value,
                "percentage": update.percentage,
                "current_step": update.current_step,
                "total_steps": update.total_steps,
                "message": message_text,
                "estimated_completion": update.estimated_completion.isoformat() if update.estimated_completion else None,
                "requires_attention": update.requires_attention,
                "allows_interruption": update.allows_interruption,
                "color_hint": update.color_hint,
                "icon_hint": update.icon_hint,
                "action_buttons": update.action_buttons,
                "timestamp": update.created_at.isoformat()
            }
            
            # Send via WebSocket
            await self._send_to_connection(connection, payload)
            
            # Update connection tracking
            connection.messages_sent += 1
            connection.last_activity = datetime.utcnow()
            
        except Exception as e:
            logger.error(
                "Failed to deliver update to connection",
                connection_id=connection.connection_id,
                update_id=update.id,
                error=str(e)
            )
    
    async def _send_to_connection(self, connection: WebSocketConnection, payload: Dict[str, Any]) -> None:
        """Send JSON payload to WebSocket connection with error handling."""
        try:
            await connection.websocket.send_json(payload)
        except WebSocketDisconnect:
            # Connection was closed, clean up
            await self.disconnect_websocket(connection.connection_id)
        except Exception as e:
            logger.error(
                "WebSocket send error",
                connection_id=connection.connection_id,
                error=str(e)
            )
            # Try to disconnect on error
            try:
                await self.disconnect_websocket(connection.connection_id)
            except Exception:
                pass  # Ignore cleanup errors
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring and optimization loop."""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Run every 30 seconds
                
                # Clean up stale connections
                await self._cleanup_stale_connections()
                
                # Optimize delivery performance
                await self._optimize_delivery_performance()
                
                # Log performance metrics
                stats = self.get_monitoring_stats()
                logger.debug("Task monitoring performance", **stats)
                
            except Exception as e:
                logger.error("Monitoring loop error", error=str(e))
                await asyncio.sleep(30)
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for old data."""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Clean up old progress updates from completed tasks
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                
                for tracker in list(self.active_trackers.values()):
                    # Remove old updates to save memory
                    tracker.updates = [
                        u for u in tracker.updates
                        if u.created_at > cutoff_time
                    ]
                
            except Exception as e:
                logger.error("Cleanup loop error", error=str(e))
                await asyncio.sleep(300)
    
    async def _cleanup_stale_connections(self) -> None:
        """Clean up stale WebSocket connections."""
        stale_connections = []
        cutoff_time = datetime.utcnow() - timedelta(minutes=10)
        
        for conn_id, connection in self.websocket_connections.items():
            if connection.last_activity < cutoff_time:
                # Check if connection is still alive
                try:
                    await connection.websocket.ping()
                except Exception:
                    stale_connections.append(conn_id)
        
        # Clean up stale connections
        for conn_id in stale_connections:
            await self.disconnect_websocket(conn_id)
        
        if stale_connections:
            logger.info("Cleaned up stale connections", count=len(stale_connections))
    
    async def _optimize_delivery_performance(self) -> None:
        """Optimize delivery performance based on current load."""
        # Adjust worker count based on queue size
        queue_size = self.update_queue.qsize()
        active_workers = len([t for t in self.delivery_tasks if not t.done()])
        
        # Add workers if queue is backing up
        if queue_size > 100 and active_workers < 5:
            worker = asyncio.create_task(
                self._delivery_worker(len(self.delivery_tasks)),
                name=f"progress-delivery-worker-{len(self.delivery_tasks)}"
            )
            self.delivery_tasks.append(worker)
            logger.info("Added delivery worker due to queue backlog", queue_size=queue_size)


# Global task monitoring system instance
task_monitoring_system = TaskMonitoringSystem()