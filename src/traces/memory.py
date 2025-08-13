"""
TraceMemory implementation - the core memory system for MCP ADHD Server.

This is the "brain" of the system that maintains persistent context
across LLM sessions, tracking intentions vs. actions and learning patterns.
"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError
import structlog
from pydantic import BaseModel

from mcp_server.config import settings
from mcp_server.models import MCPFrame, TraceMemory as TraceMemoryModel, UserState

logger = structlog.get_logger()


class TraceMemoryBackend:
    """
    Persistent, queryable memory engine for MCP frames and context.
    
    Uses Redis for hot/active memory and provides hooks for
    cold storage in Postgres and semantic storage in vector DBs.
    """
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._connection_pool = None
    
    async def connect(self) -> None:
        """Initialize Redis connection."""
        try:
            self._connection_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True,
                max_connections=50,  # Increased pool size for better integration
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError],
                socket_keepalive=True,
                socket_keepalive_options={},
                socket_connect_timeout=5,  # Increased for stability
                socket_timeout=3,  # Increased for better reliability
                health_check_interval=30,  # Connection health monitoring
            )
            self.redis = redis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis", url=settings.redis_url)
            
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.aclose()
        if self._connection_pool:
            await self._connection_pool.disconnect()
        logger.info("Disconnected from Redis")
    
    # === FRAME STORAGE ===
    
    async def store_frame(self, frame: MCPFrame) -> None:
        """Store MCP Frame in hot memory."""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        frame_key = f"frame:{frame.frame_id}"
        frame_data = frame.model_dump_json()
        
        # Store frame with TTL
        await self.redis.setex(
            frame_key, 
            settings.frame_cache_ttl, 
            frame_data
        )
        
        # Add to user's frame list
        user_frames_key = f"user:{frame.user_id}:frames"
        await self.redis.zadd(
            user_frames_key,
            {frame.frame_id: frame.timestamp.timestamp()}
        )
        
        # Set expiration on user frames list
        await self.redis.expire(user_frames_key, settings.frame_cache_ttl)
        
        logger.info(
            "Stored MCP Frame",
            frame_id=frame.frame_id,
            user_id=frame.user_id,
            ttl=settings.frame_cache_ttl
        )
    
    async def get_frame(self, frame_id: str) -> Optional[MCPFrame]:
        """Retrieve MCP Frame by ID."""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        frame_key = f"frame:{frame_id}"
        frame_data = await self.redis.get(frame_key)
        
        if frame_data:
            return MCPFrame.model_validate_json(frame_data)
        return None
    
    async def get_user_frames(
        self, 
        user_id: str, 
        limit: int = 10,
        since: Optional[datetime] = None
    ) -> List[MCPFrame]:
        """Get recent frames for a user."""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        user_frames_key = f"user:{user_id}:frames"
        
        # Get frame IDs in reverse chronological order
        min_score = since.timestamp() if since else "-inf"
        frame_ids = await self.redis.zrevrangebyscore(
            user_frames_key,
            "+inf", 
            min_score,
            start=0,
            num=limit
        )
        
        # Fetch actual frames
        frames = []
        for frame_id in frame_ids:
            frame = await self.get_frame(frame_id)
            if frame:
                frames.append(frame)
        
        return frames
    
    # === TRACE MEMORY ===
    
    async def store_trace(self, trace: TraceMemoryModel) -> None:
        """Store a trace memory event."""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        trace_key = f"trace:{trace.trace_id}"
        trace_data = trace.model_dump_json()
        
        # Store trace (longer TTL than frames)
        ttl = int(timedelta(days=settings.trace_memory_retention_days).total_seconds())
        await self.redis.setex(trace_key, ttl, trace_data)
        
        # Add to user's trace timeline
        user_traces_key = f"user:{trace.user_id}:traces"
        await self.redis.zadd(
            user_traces_key,
            {trace.trace_id: trace.timestamp.timestamp()}
        )
        await self.redis.expire(user_traces_key, ttl)
        
        # Index by event type for pattern analysis
        event_index_key = f"traces:by_event:{trace.event_type}"
        await self.redis.zadd(
            event_index_key,
            {trace.trace_id: trace.timestamp.timestamp()}
        )
        await self.redis.expire(event_index_key, ttl)
        
        # Index by task if applicable
        if trace.task_id:
            task_traces_key = f"task:{trace.task_id}:traces"
            await self.redis.zadd(
                task_traces_key,
                {trace.trace_id: trace.timestamp.timestamp()}
            )
            await self.redis.expire(task_traces_key, ttl)
        
        logger.info(
            "Stored trace memory",
            trace_id=trace.trace_id,
            user_id=trace.user_id,
            event_type=trace.event_type
        )
    
    async def get_trace(self, trace_id: str) -> Optional[TraceMemoryModel]:
        """Retrieve trace by ID."""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        trace_key = f"trace:{trace_id}"
        trace_data = await self.redis.get(trace_key)
        
        if trace_data:
            return TraceMemoryModel.model_validate_json(trace_data)
        return None
    
    async def get_user_traces(
        self,
        user_id: str,
        event_types: Optional[List[str]] = None,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[TraceMemoryModel]:
        """Get trace history for a user."""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        user_traces_key = f"user:{user_id}:traces"
        min_score = since.timestamp() if since else "-inf"
        
        trace_ids = await self.redis.zrevrangebyscore(
            user_traces_key,
            "+inf",
            min_score,
            start=0,
            num=limit
        )
        
        traces = []
        for trace_id in trace_ids:
            trace = await self.get_trace(trace_id)
            if trace and (not event_types or trace.event_type in event_types):
                traces.append(trace)
        
        return traces
    
    # === CONTEXT AGGREGATION ===
    
    async def get_current_context(self, user_id: str) -> Dict[str, Any]:
        """
        Build current context summary for a user.
        
        This is called when building MCP Frames - it aggregates
        recent traces, active tasks, and environmental state.
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        # Get recent traces (last 24 hours)
        since = datetime.utcnow() - timedelta(hours=24)
        recent_traces = await self.get_user_traces(user_id, limit=20, since=since)
        
        # Get recent frames (last 2 hours)
        frame_since = datetime.utcnow() - timedelta(hours=2)
        recent_frames = await self.get_user_frames(user_id, limit=5, since=frame_since)
        
        # Aggregate context
        context = {
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "recent_traces": [
                {
                    "event_type": trace.event_type,
                    "timestamp": trace.timestamp.isoformat(),
                    "data": trace.event_data,
                    "user_state": trace.user_state
                }
                for trace in recent_traces[:10]  # Most recent 10
            ],
            "recent_frames": [
                {
                    "frame_id": frame.frame_id,
                    "task_focus": frame.task_focus,
                    "timestamp": frame.timestamp.isoformat(),
                    "context_count": len(frame.context),
                    "action_count": len(frame.actions)
                }
                for frame in recent_frames
            ]
        }
        
        # TODO: Add pattern analysis
        # TODO: Add energy/focus predictions
        # TODO: Add environmental context
        
        return context
    
    # === USER STATE TRACKING ===
    
    async def update_user_state(
        self, 
        user_id: str, 
        state: UserState,
        source: str = "system"
    ) -> None:
        """Update user's current state."""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        state_key = f"user:{user_id}:current_state"
        state_data = {
            "state": state.value,
            "timestamp": datetime.utcnow().isoformat(),
            "source": source
        }
        
        await self.redis.setex(
            state_key,
            3600,  # 1 hour TTL
            json.dumps(state_data)
        )
        
        # Store in state history
        history_key = f"user:{user_id}:state_history"
        await self.redis.zadd(
            history_key,
            {json.dumps(state_data): datetime.utcnow().timestamp()}
        )
        
        # Keep only last 24 hours of state history
        cutoff = (datetime.utcnow() - timedelta(hours=24)).timestamp()
        await self.redis.zremrangebyscore(history_key, "-inf", cutoff)
        
        logger.info(
            "Updated user state",
            user_id=user_id,
            state=state.value,
            source=source
        )
    
    async def get_user_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's current state."""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        state_key = f"user:{user_id}:current_state"
        state_data = await self.redis.get(state_key)
        
        if state_data:
            return json.loads(state_data)
        return None
    
    # === PATTERN ANALYSIS ===
    
    async def analyze_completion_patterns(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze user's task completion patterns.
        
        This helps predict optimal timing and nudge strategies.
        """
        # Get completion traces from last 30 days
        since = datetime.utcnow() - timedelta(days=30)
        completion_traces = await self.get_user_traces(
            user_id,
            event_types=["completion", "abandonment"],
            limit=100,
            since=since
        )
        
        if not completion_traces:
            return {"status": "insufficient_data"}
        
        # Analyze patterns
        completions = [t for t in completion_traces if t.event_type == "completion"]
        abandons = [t for t in completion_traces if t.event_type == "abandonment"]
        
        completion_rate = len(completions) / len(completion_traces)
        
        # Time-of-day analysis
        completion_hours = [t.timestamp.hour for t in completions]
        best_hours = {}
        for hour in range(24):
            hour_completions = completion_hours.count(hour)
            if hour_completions > 0:
                best_hours[hour] = hour_completions
        
        return {
            "completion_rate": completion_rate,
            "total_tasks": len(completion_traces),
            "completions": len(completions),
            "abandons": len(abandons),
            "best_hours": dict(sorted(best_hours.items(), key=lambda x: x[1], reverse=True)),
            "analysis_period_days": 30
        }


# Global trace memory instance
trace_memory = TraceMemoryBackend()