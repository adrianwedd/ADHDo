"""
FrameBuilder - Context assembly and cognitive load management for ADHD users.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
from pydantic import BaseModel

from mcp_server.models import MCPFrame, FrameContext, ContextType, UserState, Task
from traces.memory import trace_memory

logger = structlog.get_logger()


class ContextualFrame(BaseModel):
    """Enhanced frame with cognitive load assessment."""
    frame: MCPFrame
    cognitive_load: float  # 0.0 - 1.0 (low to high)
    accessibility_score: float  # 0.0 - 1.0 (poor to excellent)
    recommended_action: str


class FrameBuilder:
    """
    Builds optimal context frames for ADHD users.
    
    Core principle: Minimize extraneous cognitive load while maximizing
    relevant context for decision-making.
    """
    
    def __init__(self):
        self.max_context_items = 10  # Prevent cognitive overload
        self.context_weights = {
            ContextType.USER_STATE: 1.0,      # Always most important
            ContextType.TASK: 0.9,            # Current focus
            ContextType.MEMORY_TRACE: 0.8,    # Relevant patterns
            ContextType.ENVIRONMENT: 0.7,     # Current context
            ContextType.CALENDAR: 0.6,        # Upcoming items
            ContextType.ACHIEVEMENT: 0.5,     # Recent wins
        }
    
    async def build_frame(
        self, 
        user_id: str, 
        agent_id: str,
        task_focus: Optional[str] = None,
        include_patterns: bool = True
    ) -> ContextualFrame:
        """Build an optimal context frame for the user."""
        
        # Create base frame
        frame = MCPFrame(
            user_id=user_id,
            agent_id=agent_id,
            task_focus=task_focus,
            timestamp=datetime.utcnow()
        )
        
        # Gather context components
        await self._add_user_state_context(frame, user_id)
        await self._add_task_context(frame, user_id, task_focus)
        
        if include_patterns:
            await self._add_pattern_context(frame, user_id)
        
        await self._add_environmental_context(frame, user_id)
        
        # Optimize for cognitive load
        optimized_frame = await self._optimize_cognitive_load(frame)
        
        # Calculate accessibility metrics
        cognitive_load = self._calculate_cognitive_load(optimized_frame)
        accessibility_score = self._calculate_accessibility_score(optimized_frame)
        
        # Generate recommended action
        recommended_action = await self._generate_recommendation(
            optimized_frame, cognitive_load
        )
        
        return ContextualFrame(
            frame=optimized_frame,
            cognitive_load=cognitive_load,
            accessibility_score=accessibility_score,
            recommended_action=recommended_action
        )
    
    async def _add_user_state_context(self, frame: MCPFrame, user_id: str) -> None:
        """Add current user psychological state."""
        try:
            current_state = await trace_memory.get_user_state(user_id)
            
            if current_state:
                frame.add_context(
                    ContextType.USER_STATE,
                    {
                        "current_state": current_state["state"],
                        "timestamp": current_state["timestamp"],
                        "source": current_state["source"],
                        "confidence": 0.9
                    },
                    source="trace_memory"
                )
            else:
                # Default neutral state
                frame.add_context(
                    ContextType.USER_STATE,
                    {
                        "current_state": "neutral",
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "default",
                        "confidence": 0.3
                    },
                    source="default"
                )
                
        except Exception as e:
            logger.warning("Failed to add user state context", error=str(e))
    
    async def _add_task_context(
        self, 
        frame: MCPFrame, 
        user_id: str, 
        task_focus: Optional[str]
    ) -> None:
        """Add current task and recent activity context."""
        try:
            if task_focus:
                frame.add_context(
                    ContextType.TASK,
                    {
                        "current_task": task_focus,
                        "focus_timestamp": datetime.utcnow().isoformat(),
                        "priority": "current"
                    },
                    source="user_input"
                )
            
            # Get recent task activity from trace memory
            recent_traces = await trace_memory.get_user_traces(
                user_id,
                event_types=["task_start", "task_complete", "task_abandon"],
                limit=5,
                since=datetime.utcnow() - timedelta(hours=24)
            )
            
            if recent_traces:
                recent_activity = [
                    {
                        "event": trace.event_type,
                        "task": trace.event_data.get("task_title", "Unknown"),
                        "timestamp": trace.timestamp.isoformat(),
                        "outcome": trace.event_data.get("outcome")
                    }
                    for trace in recent_traces[:3]  # Limit to prevent overload
                ]
                
                frame.add_context(
                    ContextType.TASK,
                    {"recent_activity": recent_activity},
                    source="trace_memory",
                    confidence=0.8
                )
                
        except Exception as e:
            logger.warning("Failed to add task context", error=str(e))
    
    async def _add_pattern_context(self, frame: MCPFrame, user_id: str) -> None:
        """Add relevant behavioral patterns from trace memory."""
        try:
            # Get completion patterns for context
            patterns = await trace_memory.analyze_completion_patterns(user_id)
            
            if patterns.get("status") != "insufficient_data":
                # Extract most relevant patterns
                relevant_patterns = {
                    "completion_rate": patterns.get("completion_rate", 0.0),
                    "best_hours": list(patterns.get("best_hours", {}).keys())[:3],
                    "recent_trend": self._analyze_recent_trend(patterns)
                }
                
                frame.add_context(
                    ContextType.MEMORY_TRACE,
                    relevant_patterns,
                    source="pattern_analysis",
                    confidence=0.7
                )
                
        except Exception as e:
            logger.warning("Failed to add pattern context", error=str(e))
    
    async def _add_environmental_context(self, frame: MCPFrame, user_id: str) -> None:
        """Add environmental context (time, location, etc.)."""
        try:
            now = datetime.utcnow()
            
            environmental_context = {
                "time_of_day": self._categorize_time_of_day(now.hour),
                "day_of_week": now.strftime("%A").lower(),
                "time_category": self._get_energy_time_category(now.hour),
                "timestamp": now.isoformat()
            }
            
            frame.add_context(
                ContextType.ENVIRONMENT,
                environmental_context,
                source="system",
                confidence=1.0
            )
            
        except Exception as e:
            logger.warning("Failed to add environmental context", error=str(e))
    
    async def _optimize_cognitive_load(self, frame: MCPFrame) -> MCPFrame:
        """Optimize frame to minimize cognitive load for ADHD users."""
        
        # Sort context by importance and relevance
        weighted_context = []
        for context_item in frame.context:
            weight = self.context_weights.get(context_item.type, 0.5)
            weight *= context_item.confidence
            weighted_context.append((weight, context_item))
        
        # Keep only the most important context items
        weighted_context.sort(key=lambda x: x[0], reverse=True)
        optimized_context = [
            item[1] for item in weighted_context[:self.max_context_items]
        ]
        
        # Create optimized frame
        optimized_frame = MCPFrame(
            frame_id=frame.frame_id,
            user_id=frame.user_id,
            agent_id=frame.agent_id,
            task_focus=frame.task_focus,
            timestamp=frame.timestamp,
            context=optimized_context,
            actions=frame.actions,
            priority=frame.priority,
            energy_cost=frame.energy_cost,
            dopamine_potential=frame.dopamine_potential
        )
        
        return optimized_frame
    
    def _calculate_cognitive_load(self, frame: MCPFrame) -> float:
        """Calculate cognitive load score for the frame."""
        
        # Base load from number of context items
        base_load = len(frame.context) / self.max_context_items
        
        # Additional load from complexity factors
        complexity_factors = 0.0
        
        for context_item in frame.context:
            data = context_item.data
            
            # Complex data structures increase load
            if isinstance(data, dict):
                complexity_factors += len(data) * 0.05
            
            # Multiple recent activities increase load
            if context_item.type == ContextType.TASK:
                recent_activity = data.get("recent_activity", [])
                complexity_factors += len(recent_activity) * 0.1
        
        # Normalize to 0-1 range
        total_load = min(base_load + complexity_factors, 1.0)
        
        return total_load
    
    def _calculate_accessibility_score(self, frame: MCPFrame) -> float:
        """Calculate accessibility score based on ADHD-friendly principles."""
        
        score = 1.0
        
        # Penalize for too many context items (cognitive overload)
        if len(frame.context) > 7:  # Miller's rule: 7±2 items
            score -= (len(frame.context) - 7) * 0.1
        
        # Reward for clear, specific task focus
        if frame.task_focus and len(frame.task_focus.split()) < 10:
            score += 0.1
        
        # Reward for recent positive patterns
        for context_item in frame.context:
            if context_item.type == ContextType.MEMORY_TRACE:
                completion_rate = context_item.data.get("completion_rate", 0.0)
                if completion_rate > 0.7:
                    score += 0.1
        
        return max(0.0, min(score, 1.0))
    
    async def _generate_recommendation(
        self, 
        frame: MCPFrame, 
        cognitive_load: float
    ) -> str:
        """Generate recommended action based on frame analysis."""
        
        if cognitive_load > 0.8:
            return "simplify_context"  # Too much information
        elif cognitive_load < 0.3:
            return "add_context"       # Might need more information
        elif not frame.task_focus:
            return "clarify_focus"     # Need clearer objective
        else:
            return "proceed_normal"    # Good balance
    
    def _categorize_time_of_day(self, hour: int) -> str:
        """Categorize time of day for ADHD energy patterns."""
        if 6 <= hour < 10:
            return "morning"
        elif 10 <= hour < 14:
            return "late_morning"
        elif 14 <= hour < 18:
            return "afternoon" 
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def _get_energy_time_category(self, hour: int) -> str:
        """Get energy level category based on typical ADHD patterns."""
        # Many ADHD individuals have energy peaks/valleys
        if 8 <= hour < 11:
            return "peak_morning"
        elif 11 <= hour < 14:
            return "mid_day_dip"
        elif 14 <= hour < 17:
            return "afternoon_recovery"
        elif 17 <= hour < 20:
            return "evening_peak"
        else:
            return "low_energy"
    
    def _analyze_recent_trend(self, patterns: Dict[str, Any]) -> str:
        """Analyze recent completion trend."""
        completion_rate = patterns.get("completion_rate", 0.0)
        
        if completion_rate > 0.8:
            return "strong_positive"
        elif completion_rate > 0.6:
            return "positive"
        elif completion_rate > 0.4:
            return "neutral"
        elif completion_rate > 0.2:
            return "concerning"
        else:
            return "needs_support"


# Global frame builder instance
frame_builder = FrameBuilder()