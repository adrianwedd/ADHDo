"""
Core Cognitive Loop - The brain of the MCP ADHD Server.

This module implements the recursive meta-cognitive protocol that forms the heart
of the ADHD support system. It orchestrates the flow from user input to contextual
response, maintaining psychological safety and learning patterns over time.

The cognitive loop follows these steps:
1. **Context Assembly**: FrameBuilder gathers relevant context while minimizing
   cognitive load according to ACCESS framework principles
2. **Safety Assessment**: SafetyMonitor checks for crisis situations requiring
   immediate hard-coded responses (no LLM involved)
3. **Circuit Breaker**: Implements Dynamic Systems Theory to prevent overwhelming
   users during vulnerable states
4. **LLM Processing**: Routes to appropriate local/cloud models based on complexity
5. **Action Execution**: Triggers environmental changes, nudges, or other interventions
6. **Memory Update**: Records interaction patterns for future personalization

This is designed specifically for neurodivergent users following neurodiversity-
affirming principles: empowering rather than pathologizing, user-controlled, and
built with ADHD cognitive patterns as the foundation rather than an afterthought.

Key Features:
- **Recursive Learning**: Each interaction improves future responses
- **Circuit Breaking**: Prevents system from overwhelming struggling users
- **Safety First**: Crisis detection with deterministic responses
- **Cognitive Load Management**: Optimizes information density for ADHD brains
- **Privacy Preserving**: Sensitive processing stays local

Example Usage:
    ```python
    from mcp_server.cognitive_loop import cognitive_loop
    
    # Main user interaction
    result = await cognitive_loop.process_user_input(
        user_id="user123",
        user_input="I'm struggling to start this email",
        task_focus="Write response to Sarah",
        nudge_tier=NudgeTier.GENTLE
    )
    
    # Proactive environmental nudging
    result = await cognitive_loop.initiate_proactive_nudge(
        user_id="user123", 
        task_id="weekly_report",
        context={"trigger": "calendar_reminder"}
    )
    ```

Architecture Notes:
- Implements orchestrator-worker pattern from multi-agent systems research
- Uses circuit breaker pattern from resilient systems engineering
- Follows cognitive load theory for neurodiversity-affirming design
- Incorporates therapeutic alliance principles from clinical psychology
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
from pydantic import BaseModel

from mcp_server.config import settings
from mcp_server.models import MCPFrame, UserState, NudgeTier, TraceMemory as TraceMemoryModel
from mcp_server.llm_client import llm_router, LLMResponse
from frames.builder import frame_builder, ContextualFrame
from calendar_integration.context import EnhancedFrameBuilder
from calendar_integration.client import CalendarClient
from calendar_integration.processor import ADHDCalendarProcessor
from nudge.engine import nudge_engine
from traces.memory import trace_memory

logger = structlog.get_logger()


class CognitiveLoopResult(BaseModel):
    """
    Result of a cognitive loop execution.
    
    This is the primary output of the cognitive loop, containing all information
    about how the system processed a user interaction. It's designed to provide
    transparency and debuggability for both users and developers.
    
    Attributes:
        success (bool): Whether the cognitive loop completed successfully
        response (Optional[LLMResponse]): The LLM-generated response, if any
        actions_taken (List[str]): List of actions the system took (nudges, 
            environmental changes, safety overrides, etc.)
        context_frame (Optional[MCPFrame]): The contextual frame that was built
            for this interaction, useful for debugging and analysis
        cognitive_load (float): Calculated cognitive load (0.0-1.0) of the
            interaction, important for ADHD users
        processing_time_ms (float): How long the entire loop took to process
        error (Optional[str]): Error message if processing failed
    
    Usage:
        This result can be used to:
        - Provide feedback to users about system reasoning
        - Debug issues in the cognitive loop
        - Analyze system performance and load
        - Track patterns in user interactions
        - Implement time-travel debugging for ADHD pattern analysis
    """
    success: bool
    response: Optional[LLMResponse] = None
    actions_taken: List[str] = []
    context_frame: Optional[MCPFrame] = None
    cognitive_load: float = 0.0
    processing_time_ms: float = 0.0
    error: Optional[str] = None


class CircuitBreakerState(BaseModel):
    """
    Circuit breaker state for psychological stability.
    
    Implements the circuit breaker pattern from resilient systems engineering,
    adapted for psychological safety in ADHD support. Based on Dynamic Systems
    Theory, this prevents the system from overwhelming users who are in a
    vulnerable or non-responsive state.
    
    The circuit breaker has three states:
    1. **Closed**: Normal operation, interventions proceed as usual
    2. **Open**: User is struggling, system switches to minimal "anchor mode"  
    3. **Half-Open**: Testing if user has recovered, ready to resume normal operation
    
    This is critical for ADHD users who may experience:
    - Executive paralysis (inability to respond to complex interventions)
    - Overwhelm from too many nudges during low periods
    - Shame spirals from feeling like they're "failing" the system
    
    Attributes:
        user_id (str): The user this circuit breaker protects
        is_open (bool): Whether the circuit is currently "tripped" (in anchor mode)
        failure_count (int): Number of consecutive negative responses
        last_failure (Optional[datetime]): When the most recent failure occurred
        next_test_time (Optional[datetime]): When to test for recovery
    
    Example:
        A user stops responding to nudges for 3 consecutive days and their
        mood scores are declining. The circuit breaker trips, switching the
        system to gentle "anchor mode" responses like "I'm here when you're ready,
        no pressure" instead of task-focused interventions.
    """
    user_id: str
    is_open: bool = False
    failure_count: int = 0
    last_failure: Optional[datetime] = None
    next_test_time: Optional[datetime] = None
    
    def should_trip(self, max_failures: int = 3) -> bool:
        """
        Check if circuit breaker should trip to protect user.
        
        Args:
            max_failures (int): Threshold for consecutive failures before tripping.
                Default is 3, based on clinical observation that 3 consecutive
                days of non-response often indicates a vulnerable state.
        
        Returns:
            bool: True if the circuit should trip to anchor mode
        """
        return self.failure_count >= max_failures
    
    def should_test(self) -> bool:
        """
        Check if we should test for user recovery.
        
        After the circuit trips, we wait a recovery period (typically 2-4 hours)
        before gently testing if the user is ready for normal interventions again.
        This prevents premature re-engagement that could cause another spiral.
        
        Returns:
            bool: True if it's time to test for recovery
        """
        if not self.is_open or not self.next_test_time:
            return False
        return datetime.utcnow() >= self.next_test_time


class CognitiveLoop:
    """
    The main cognitive processing loop for MCP ADHD Server.
    
    Implements the recursive meta-cognitive protocol with safety controls,
    circuit breaking for psychological stability, and adaptive learning.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.processing_stats = {
            "total_requests": 0,
            "safety_overrides": 0,
            "circuit_breaker_trips": 0,
            "successful_responses": 0
        }
        
        # Initialize calendar-enhanced frame builder if calendar is enabled
        if settings.google_calendar_enabled:
            calendar_client = CalendarClient()
            calendar_processor = ADHDCalendarProcessor()
            self.enhanced_frame_builder = EnhancedFrameBuilder(calendar_client, calendar_processor)
        else:
            self.enhanced_frame_builder = None
    
    async def process_user_input(
        self,
        user_id: str,
        user_input: str,
        task_focus: Optional[str] = None,
        nudge_tier: NudgeTier = NudgeTier.GENTLE
    ) -> CognitiveLoopResult:
        """
        Main entry point for processing user input through the cognitive loop.
        
        This is where the magic happens - the recursive meta-cognitive protocol
        that learns patterns, provides context-aware responses, and evolves.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.processing_stats["total_requests"] += 1
            
            # Step 1: Check circuit breaker state
            circuit_state = await self._check_circuit_breaker(user_id)
            if circuit_state.is_open and not circuit_state.should_test():
                return await self._handle_circuit_open(user_id, circuit_state)
            
            # Step 2: Build contextual frame (with calendar integration if available)
            logger.info("Building contextual frame", user_id=user_id, task_focus=task_focus)
            
            if self.enhanced_frame_builder:
                # Use enhanced frame builder with calendar context
                contextual_frame = await self.enhanced_frame_builder.build_frame(
                    user_id=user_id,
                    agent_id="main_cognitive_loop",
                    task_focus=task_focus,
                    include_patterns=True,
                    include_calendar=True
                )
                logger.info("Enhanced frame with calendar context", 
                           user_id=user_id, 
                           cognitive_load=contextual_frame.cognitive_load)
            else:
                # Use standard frame builder
                contextual_frame = await frame_builder.build_frame(
                    user_id=user_id,
                    agent_id="main_cognitive_loop",
                    task_focus=task_focus,
                    include_patterns=True
                )
            
            # Step 3: Process through LLM router (includes safety monitoring)
            logger.info("Processing through LLM router", 
                       cognitive_load=contextual_frame.cognitive_load)
            
            llm_response = await llm_router.process_request(
                user_input=user_input,
                context=contextual_frame.frame,
                nudge_tier=nudge_tier
            )
            
            # Step 4: Handle safety overrides
            if llm_response.source == "hard_coded":
                self.processing_stats["safety_overrides"] += 1
                await self._record_safety_event(user_id, user_input, llm_response)
                
                return CognitiveLoopResult(
                    success=True,
                    response=llm_response,
                    actions_taken=["safety_override"],
                    context_frame=contextual_frame.frame,
                    cognitive_load=contextual_frame.cognitive_load,
                    processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
                )
            
            # Step 5-7: Parallel execution for better integration efficiency
            # Execute actions, update memory, and circuit breaker concurrently
            actions_task = self._execute_actions(
                user_id, contextual_frame, llm_response
            )
            memory_task = self._update_trace_memory(
                user_id, user_input, llm_response, contextual_frame, []  # Actions added after
            )
            circuit_task = self._update_circuit_breaker(user_id, success=True)
            
            # Wait for all integration tasks to complete
            actions_taken, _, _ = await asyncio.gather(
                actions_task, memory_task, circuit_task, return_exceptions=True
            )
            
            self.processing_stats["successful_responses"] += 1
            
            return CognitiveLoopResult(
                success=True,
                response=llm_response,
                actions_taken=actions_taken,
                context_frame=contextual_frame.frame,
                cognitive_load=contextual_frame.cognitive_load,
                processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
            )
            
        except Exception as e:
            logger.error("Cognitive loop processing failed", 
                        user_id=user_id, error=str(e), exc_info=True)
            
            # Update circuit breaker on failure
            await self._update_circuit_breaker(user_id, success=False)
            
            return CognitiveLoopResult(
                success=False,
                error=str(e),
                processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
            )
    
    async def initiate_proactive_nudge(
        self,
        user_id: str,
        task_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CognitiveLoopResult:
        """
        Initiate a proactive nudge based on patterns or environmental triggers.
        
        This is called by background processes, Home Assistant webhooks, etc.
        """
        try:
            # Build frame for proactive nudging (with calendar context if available)
            if self.enhanced_frame_builder:
                # Use enhanced frame builder with calendar context for better nudge timing
                contextual_frame = await self.enhanced_frame_builder.build_frame(
                    user_id=user_id,
                    agent_id="proactive_nudge_system",
                    task_focus=f"Task reminder: {task_id}",
                    include_patterns=True,
                    include_calendar=True
                )
            else:
                # Use standard frame builder
                contextual_frame = await frame_builder.build_frame(
                    user_id=user_id,
                    agent_id="proactive_nudge_system",
                    task_focus=f"Task reminder: {task_id}",
                    include_patterns=True
                )
            
            # Generate proactive nudge content
            nudge_prompt = await self._generate_proactive_nudge_prompt(
                task_id, contextual_frame
            )
            
            # Process through cognitive loop
            return await self.process_user_input(
                user_id=user_id,
                user_input=nudge_prompt,
                task_focus=f"Proactive nudge for {task_id}",
                nudge_tier=NudgeTier.GENTLE
            )
            
        except Exception as e:
            logger.error("Proactive nudge failed", 
                        user_id=user_id, task_id=task_id, error=str(e))
            return CognitiveLoopResult(
                success=False,
                error=f"Proactive nudge failed: {str(e)}"
            )
    
    async def _check_circuit_breaker(self, user_id: str) -> CircuitBreakerState:
        """Check circuit breaker state for user."""
        if user_id not in self.circuit_breakers:
            self.circuit_breakers[user_id] = CircuitBreakerState(user_id=user_id)
        
        return self.circuit_breakers[user_id]
    
    async def _handle_circuit_open(
        self, 
        user_id: str, 
        circuit_state: CircuitBreakerState
    ) -> CognitiveLoopResult:
        """Handle when circuit breaker is open (anchor mode)."""
        
        logger.info("Circuit breaker open - anchor mode", user_id=user_id)
        
        # Provide minimal, non-demanding response
        anchor_response = LLMResponse(
            text=(
                "I notice you might need some space right now. "
                "I'm here when you're ready, no pressure. "
                "Take care of yourself. 💙"
            ),
            source="anchor_mode",
            confidence=1.0,
            model_used="circuit_breaker"
        )
        
        return CognitiveLoopResult(
            success=True,
            response=anchor_response,
            actions_taken=["anchor_mode"],
            cognitive_load=0.1,  # Minimal load
            processing_time_ms=1.0  # Instant response
        )
    
    async def _execute_actions(
        self,
        user_id: str,
        contextual_frame: ContextualFrame,
        llm_response: LLMResponse
    ) -> List[str]:
        """Execute any actions recommended by the frame analysis."""
        
        actions_taken = []
        
        try:
            # Handle high cognitive load
            if contextual_frame.cognitive_load > 0.8:
                actions_taken.append("cognitive_load_warning")
                # Could trigger simplification suggestions
            
            # Handle low accessibility score
            if contextual_frame.accessibility_score < 0.5:
                actions_taken.append("accessibility_adjustment")
                # Could trigger interface modifications
            
            # Execute frame recommendations
            if contextual_frame.recommended_action == "simplify_context":
                actions_taken.append("context_simplification")
            elif contextual_frame.recommended_action == "clarify_focus":
                actions_taken.append("focus_clarification")
            
            return actions_taken
            
        except Exception as e:
            logger.error("Action execution failed", error=str(e))
            return actions_taken
    
    async def _update_trace_memory(
        self,
        user_id: str,
        user_input: str,
        llm_response: LLMResponse,
        contextual_frame: ContextualFrame,
        actions_taken: List[str]
    ) -> None:
        """Update trace memory with interaction details."""
        
        try:
            # Create trace memory record
            trace_record = TraceMemoryModel(
                user_id=user_id,
                event_type="cognitive_interaction",
                event_data={
                    "user_input": user_input,
                    "llm_response": llm_response.text,
                    "llm_source": llm_response.source,
                    "cognitive_load": contextual_frame.cognitive_load,
                    "accessibility_score": contextual_frame.accessibility_score,
                    "actions_taken": actions_taken,
                    "processing_latency": llm_response.latency_ms,
                    "task_focus": contextual_frame.frame.task_focus
                },
                confidence=llm_response.confidence,
                source="cognitive_loop"
            )
            
            await trace_memory.store_trace(trace_record)
            
        except Exception as e:
            logger.error("Failed to update trace memory", error=str(e))
    
    async def _update_circuit_breaker(self, user_id: str, success: bool) -> None:
        """Update circuit breaker state based on interaction outcome."""
        
        circuit_state = self.circuit_breakers.get(user_id)
        if not circuit_state:
            return
        
        if success:
            # Reset circuit breaker on success
            if circuit_state.is_open:
                logger.info("Circuit breaker recovery detected", user_id=user_id)
            
            circuit_state.is_open = False
            circuit_state.failure_count = 0
            circuit_state.last_failure = None
            circuit_state.next_test_time = None
            
        else:
            # Increment failure count
            circuit_state.failure_count += 1
            circuit_state.last_failure = datetime.utcnow()
            
            # Trip circuit breaker if threshold reached
            if circuit_state.should_trip():
                logger.warning("Circuit breaker tripped", 
                              user_id=user_id, 
                              failure_count=circuit_state.failure_count)
                
                circuit_state.is_open = True
                circuit_state.next_test_time = (
                    datetime.utcnow() + 
                    timedelta(hours=2)  # Test recovery in 2 hours
                )
                
                self.processing_stats["circuit_breaker_trips"] += 1
    
    async def _record_safety_event(
        self, 
        user_id: str, 
        user_input: str, 
        safety_response: LLMResponse
    ) -> None:
        """Record safety override event in trace memory."""
        
        try:
            safety_trace = TraceMemoryModel(
                user_id=user_id,
                event_type="safety_override",
                event_data={
                    "trigger_input": user_input,
                    "safety_response": safety_response.text,
                    "response_source": safety_response.source,
                    "timestamp": datetime.utcnow().isoformat()
                },
                confidence=1.0,
                source="safety_monitor"
            )
            
            await trace_memory.store_trace(safety_trace)
            
        except Exception as e:
            logger.error("Failed to record safety event", error=str(e))
    
    async def _generate_proactive_nudge_prompt(
        self,
        task_id: str,
        contextual_frame: ContextualFrame
    ) -> str:
        """Generate a prompt for proactive nudging."""
        
        # Analyze context to create appropriate nudge
        current_state = None
        for context_item in contextual_frame.frame.context:
            if context_item.type.value == "user_state":
                current_state = context_item.data.get("current_state")
                break
        
        if current_state == "low":
            return f"Gentle check-in about {task_id} when you're ready"
        elif current_state == "energized":
            return f"You seem energized! Good time to tackle {task_id}?"
        else:
            return f"Friendly reminder about {task_id}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cognitive loop processing statistics."""
        return {
            **self.processing_stats,
            "active_circuit_breakers": len([
                cb for cb in self.circuit_breakers.values() if cb.is_open
            ]),
            "success_rate": (
                self.processing_stats["successful_responses"] / 
                max(self.processing_stats["total_requests"], 1)
            )
        }


# Global cognitive loop instance
cognitive_loop = CognitiveLoop()