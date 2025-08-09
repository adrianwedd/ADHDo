"""
Cognitive Loop Integration with Background Processing and Caching Systems.

Integrates the existing cognitive loop with the new background processing and caching
infrastructure to provide enterprise-scale performance while maintaining ADHD optimizations.

Features:
- Cognitive loop operations offloaded to background processing for improved responsiveness
- Intelligent caching of cognitive patterns and user contexts
- Crisis-safe integration that preserves immediate response for safety situations
- Pattern analysis and memory updates handled asynchronously
- Performance monitoring with ADHD-specific metrics
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

import structlog

from mcp_server.cognitive_loop import cognitive_loop, CognitiveLoopResult, CircuitBreakerState
from mcp_server.background_processing import (
    background_task_manager, TaskDefinition, TaskPriority, TaskType
)
from mcp_server.caching_system import cache_manager, CacheLayer, CachePriority
from mcp_server.cache_strategies import cache_warming_engine, cache_invalidation_engine
from mcp_server.task_monitoring import task_monitoring_system, ProgressUpdateType
from mcp_server.models import MCPFrame, UserState, NudgeTier, TraceMemory as TraceMemoryModel
from mcp_server.llm_client import LLMResponse
from frames.builder import ContextualFrame
from mcp_server.config import settings


# Configure structured logger
logger = structlog.get_logger(__name__)


class EnhancedCognitiveLoop:
    """
    Enhanced cognitive loop with integrated background processing and caching.
    
    Extends the existing cognitive loop to leverage background processing for
    non-critical operations and intelligent caching for improved performance.
    Maintains ADHD optimizations and crisis-safe operation.
    """
    
    def __init__(self):
        self.original_loop = cognitive_loop
        self.performance_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'background_operations': 0,
            'immediate_responses': 0,
            'crisis_responses': 0,
            'average_response_time_ms': 0.0
        }
        
        # ADHD optimization settings
        self.crisis_response_time_target_ms = 100  # 100ms for crisis situations
        self.user_response_time_target_ms = 1000   # 1 second for user interactions
        self.background_processing_threshold_ms = 500  # Offload tasks taking >500ms
        
        # Caching strategies
        self.context_cache_ttl = 300  # 5 minutes for context frames
        self.pattern_cache_ttl = 3600  # 1 hour for pattern analysis
        
    async def process_user_input(
        self,
        user_id: str,
        user_input: str,
        task_focus: Optional[str] = None,
        nudge_tier: NudgeTier = NudgeTier.GENTLE
    ) -> CognitiveLoopResult:
        """
        Enhanced user input processing with background operations and caching.
        
        Provides immediate crisis response while offloading non-critical operations
        to background processing for improved performance.
        """
        start_time = time.perf_counter()
        
        try:
            self.performance_stats['total_requests'] += 1
            
            # Step 1: Crisis Detection (Always Immediate)
            crisis_detected = await self._detect_crisis_input(user_input)
            if crisis_detected:
                return await self._handle_crisis_input(
                    user_id, user_input, task_focus, nudge_tier, start_time
                )
            
            # Step 2: Check Circuit Breaker State (Cached)
            circuit_state = await self._get_cached_circuit_breaker_state(user_id)
            if circuit_state and circuit_state.is_open and not circuit_state.should_test():
                return await self._handle_circuit_open_cached(user_id, circuit_state, start_time)
            
            # Step 3: Fast Context Retrieval (Multi-layer Cache)
            contextual_frame = await self._get_cached_context_frame(
                user_id, task_focus, user_input
            )
            
            if not contextual_frame:
                # Background context building for complex requests
                if len(user_input) > 200 or (task_focus and len(task_focus) > 100):
                    return await self._handle_complex_request(
                        user_id, user_input, task_focus, nudge_tier, start_time
                    )
                
                # Build context synchronously for simple requests
                contextual_frame = await self._build_context_frame_fast(
                    user_id, task_focus, user_input
                )
            else:
                self.performance_stats['cache_hits'] += 1
            
            # Step 4: LLM Processing with Performance Monitoring
            llm_start_time = time.perf_counter()
            llm_response = await self.original_loop.llm_router.process_request(
                user_input=user_input,
                context=contextual_frame.frame,
                nudge_tier=nudge_tier
            )
            llm_processing_time = (time.perf_counter() - llm_start_time) * 1000
            
            # Step 5: Background Operations for Non-Critical Tasks
            background_tasks = []
            
            # Memory updates
            background_tasks.append(self._schedule_memory_update(
                user_id, user_input, llm_response, contextual_frame
            ))
            
            # Pattern analysis
            background_tasks.append(self._schedule_pattern_analysis(
                user_id, user_input, contextual_frame, llm_response
            ))
            
            # Circuit breaker updates
            background_tasks.append(self._schedule_circuit_breaker_update(
                user_id, success=True
            ))
            
            # Cache warming for related contexts
            background_tasks.append(self._schedule_context_cache_warming(
                user_id, contextual_frame
            ))
            
            # Execute background tasks asynchronously
            await asyncio.gather(*background_tasks, return_exceptions=True)
            self.performance_stats['background_operations'] += len(background_tasks)
            
            # Step 6: Immediate Actions (Synchronous for User Experience)
            actions_taken = await self._execute_immediate_actions(
                user_id, contextual_frame, llm_response
            )
            
            # Calculate and record performance metrics
            total_time_ms = (time.perf_counter() - start_time) * 1000
            await self._update_performance_metrics(total_time_ms, llm_processing_time)
            
            self.performance_stats['immediate_responses'] += 1
            
            logger.info(
                "Enhanced cognitive loop completed",
                user_id=user_id,
                total_time_ms=f"{total_time_ms:.2f}",
                llm_time_ms=f"{llm_processing_time:.2f}",
                cache_hit=bool(contextual_frame),
                background_tasks=len(background_tasks)
            )
            
            return CognitiveLoopResult(
                success=True,
                response=llm_response,
                actions_taken=actions_taken,
                context_frame=contextual_frame.frame,
                cognitive_load=contextual_frame.cognitive_load,
                processing_time_ms=total_time_ms
            )
            
        except Exception as e:
            logger.error("Enhanced cognitive loop error", user_id=user_id, error=str(e))
            
            # Fallback to original cognitive loop
            return await self.original_loop.process_user_input(
                user_id, user_input, task_focus, nudge_tier
            )
    
    async def initiate_proactive_nudge(
        self,
        user_id: str,
        task_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CognitiveLoopResult:
        """
        Enhanced proactive nudging with background processing and caching.
        
        Uses cached user patterns and background analysis to generate
        more effective proactive nudges.
        """
        try:
            # Check if user has attention-critical tasks in progress
            active_tasks = task_monitoring_system.get_active_tasks_for_user(user_id)
            crisis_tasks = [t for t in active_tasks if t.get('priority') == 'crisis']
            
            # Defer nudge if user has crisis tasks
            if crisis_tasks:
                logger.info("Deferring proactive nudge due to crisis tasks", 
                           user_id=user_id, task_id=task_id)
                return CognitiveLoopResult(
                    success=True,
                    actions_taken=['nudge_deferred'],
                    processing_time_ms=1.0
                )
            
            # Use cached nudge patterns for personalization
            nudge_patterns = await self._get_cached_nudge_patterns(user_id)
            
            # Generate personalized nudge using background analysis
            nudge_task = TaskDefinition(
                name=f"Generate proactive nudge for {task_id}",
                task_type=TaskType.PATTERN_ANALYSIS,
                priority=TaskPriority.HIGH,
                function_name="generate_personalized_nudge",
                args=[user_id, task_id, nudge_patterns],
                user_id=user_id,
                user_visible=True,
                attention_friendly=True,
                max_execution_time=30
            )
            
            task_id_bg = await background_task_manager.submit_task(nudge_task)
            
            # Monitor nudge generation
            tracker = task_monitoring_system.start_task_tracking(nudge_task)
            
            logger.info(
                "Proactive nudge scheduled for background processing",
                user_id=user_id,
                task_id=task_id,
                background_task_id=task_id_bg
            )
            
            return CognitiveLoopResult(
                success=True,
                actions_taken=['proactive_nudge_scheduled'],
                processing_time_ms=5.0
            )
            
        except Exception as e:
            logger.error("Enhanced proactive nudge error", user_id=user_id, error=str(e))
            
            # Fallback to original implementation
            return await self.original_loop.initiate_proactive_nudge(
                user_id, task_id, context
            )
    
    async def _detect_crisis_input(self, user_input: str) -> bool:
        """Fast crisis detection using cached patterns."""
        crisis_keywords = [
            'crisis', 'emergency', 'help', 'suicide', 'self-harm',
            'kill myself', 'end it all', 'can\'t take it', 'hopeless'
        ]
        
        user_input_lower = user_input.lower()
        return any(keyword in user_input_lower for keyword in crisis_keywords)
    
    async def _handle_crisis_input(
        self,
        user_id: str,
        user_input: str,
        task_focus: Optional[str],
        nudge_tier: NudgeTier,
        start_time: float
    ) -> CognitiveLoopResult:
        """Handle crisis input with immediate response (no background processing)."""
        self.performance_stats['crisis_responses'] += 1
        
        # Use original cognitive loop for crisis situations (fastest path)
        result = await self.original_loop.process_user_input(
            user_id, user_input, task_focus, nudge_tier
        )
        
        # Schedule background crisis analysis (non-blocking)
        asyncio.create_task(self._schedule_crisis_analysis(user_id, user_input))
        
        processing_time = (time.perf_counter() - start_time) * 1000
        
        logger.warning(
            "Crisis input detected - immediate response",
            user_id=user_id,
            processing_time_ms=f"{processing_time:.2f}"
        )
        
        return result
    
    async def _get_cached_circuit_breaker_state(self, user_id: str) -> Optional[CircuitBreakerState]:
        """Get circuit breaker state from cache."""
        try:
            cache_key = f"circuit_breaker:{user_id}"
            cached_state = await cache_manager.get(
                cache_key,
                priority=CachePriority.HIGH,
                user_id=user_id
            )
            
            if cached_state:
                return CircuitBreakerState(**cached_state)
            
            # Get from original loop and cache it
            original_state = await self.original_loop._check_circuit_breaker(user_id)
            
            # Cache for 5 minutes
            await cache_manager.set(
                cache_key,
                original_state.model_dump(),
                ttl=300,
                priority=CachePriority.HIGH,
                user_id=user_id
            )
            
            return original_state
            
        except Exception as e:
            logger.error("Circuit breaker cache error", user_id=user_id, error=str(e))
            return None
    
    async def _handle_circuit_open_cached(
        self,
        user_id: str,
        circuit_state: CircuitBreakerState,
        start_time: float
    ) -> CognitiveLoopResult:
        """Handle circuit breaker open state with cached response."""
        try:
            # Try to get cached anchor response
            cache_key = f"anchor_response:{user_id}"
            cached_response = await cache_manager.get(
                cache_key,
                priority=CachePriority.HIGH,
                user_id=user_id
            )
            
            if cached_response:
                response = LLMResponse(**cached_response)
            else:
                # Generate and cache anchor response
                response = await self._generate_anchor_response(user_id)
                await cache_manager.set(
                    cache_key,
                    response.model_dump(),
                    ttl=3600,  # Cache for 1 hour
                    priority=CachePriority.HIGH,
                    user_id=user_id
                )
            
            processing_time = (time.perf_counter() - start_time) * 1000
            
            return CognitiveLoopResult(
                success=True,
                response=response,
                actions_taken=['anchor_mode_cached'],
                cognitive_load=0.1,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error("Cached circuit open error", user_id=user_id, error=str(e))
            return await self.original_loop._handle_circuit_open(user_id, circuit_state)
    
    async def _get_cached_context_frame(
        self,
        user_id: str,
        task_focus: Optional[str],
        user_input: str
    ) -> Optional[ContextualFrame]:
        """Get context frame from multi-layer cache."""
        try:
            # Create cache key based on user, task, and input hash
            input_hash = hash(user_input) % 10000  # Simple hash for cache key
            cache_key = f"context_frame:{user_id}:{task_focus}:{input_hash}"
            
            # Try memory cache first (fastest)
            cached_frame = await cache_manager.get(
                cache_key,
                priority=CachePriority.HIGH,
                user_id=user_id
            )
            
            if cached_frame:
                # Validate cache freshness (ADHD users need current context)
                cache_time = datetime.fromisoformat(cached_frame.get('cached_at', ''))
                if (datetime.utcnow() - cache_time).total_seconds() < self.context_cache_ttl:
                    logger.debug("Context frame cache hit", user_id=user_id, cache_key=cache_key[:50])
                    return ContextualFrame(**cached_frame['frame_data'])
            
            return None
            
        except Exception as e:
            logger.error("Context frame cache error", user_id=user_id, error=str(e))
            return None
    
    async def _build_context_frame_fast(
        self,
        user_id: str,
        task_focus: Optional[str],
        user_input: str
    ) -> ContextualFrame:
        """Build context frame with performance optimization."""
        try:
            # Use enhanced frame builder if available
            if hasattr(self.original_loop, 'enhanced_frame_builder') and self.original_loop.enhanced_frame_builder:
                frame = await self.original_loop.enhanced_frame_builder.build_frame(
                    user_id=user_id,
                    agent_id="enhanced_cognitive_loop",
                    task_focus=task_focus,
                    include_patterns=True,
                    include_calendar=True
                )
            else:
                # Use standard frame builder
                from frames.builder import frame_builder
                frame = await frame_builder.build_frame(
                    user_id=user_id,
                    agent_id="enhanced_cognitive_loop",
                    task_focus=task_focus,
                    include_patterns=True
                )
            
            # Cache the frame
            await self._cache_context_frame(user_id, task_focus, user_input, frame)
            
            return frame
            
        except Exception as e:
            logger.error("Fast context frame building error", user_id=user_id, error=str(e))
            raise
    
    async def _handle_complex_request(
        self,
        user_id: str,
        user_input: str,
        task_focus: Optional[str],
        nudge_tier: NudgeTier,
        start_time: float
    ) -> CognitiveLoopResult:
        """Handle complex requests with background processing."""
        try:
            # Provide immediate acknowledgment
            immediate_response = LLMResponse(
                text="I'm processing your request. This might take a moment for the best response...",
                source="background_processing",
                confidence=1.0,
                model_used="immediate_ack"
            )
            
            # Schedule complex processing in background
            complex_task = TaskDefinition(
                name=f"Complex cognitive processing",
                task_type=TaskType.PATTERN_ANALYSIS,
                priority=TaskPriority.HIGH,
                function_name="complex_cognitive_processing",
                args=[user_id, user_input, task_focus, nudge_tier.value],
                user_id=user_id,
                user_visible=True,
                attention_friendly=True,
                max_execution_time=120
            )
            
            task_id = await background_task_manager.submit_task(complex_task)
            
            # Start progress tracking
            tracker = task_monitoring_system.start_task_tracking(complex_task)
            
            processing_time = (time.perf_counter() - start_time) * 1000
            self.performance_stats['background_operations'] += 1
            
            logger.info(
                "Complex request scheduled for background processing",
                user_id=user_id,
                task_id=task_id,
                processing_time_ms=f"{processing_time:.2f}"
            )
            
            return CognitiveLoopResult(
                success=True,
                response=immediate_response,
                actions_taken=['background_processing_scheduled'],
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error("Complex request handling error", user_id=user_id, error=str(e))
            # Fallback to synchronous processing
            return await self.original_loop.process_user_input(
                user_id, user_input, task_focus, nudge_tier
            )
    
    async def _schedule_memory_update(
        self,
        user_id: str,
        user_input: str,
        llm_response: LLMResponse,
        contextual_frame: ContextualFrame
    ) -> None:
        """Schedule memory update as background task."""
        try:
            memory_task = TaskDefinition(
                name="Update trace memory",
                task_type=TaskType.DATA_AGGREGATION,
                priority=TaskPriority.NORMAL,
                function_name="update_trace_memory",
                args=[user_id, user_input, llm_response.model_dump(), contextual_frame.model_dump()],
                user_id=user_id,
                max_execution_time=30
            )
            
            await background_task_manager.submit_task(memory_task)
            
        except Exception as e:
            logger.error("Memory update scheduling error", user_id=user_id, error=str(e))
    
    async def _schedule_pattern_analysis(
        self,
        user_id: str,
        user_input: str,
        contextual_frame: ContextualFrame,
        llm_response: LLMResponse
    ) -> None:
        """Schedule pattern analysis as background task."""
        try:
            pattern_task = TaskDefinition(
                name="Analyze interaction patterns",
                task_type=TaskType.PATTERN_ANALYSIS,
                priority=TaskPriority.NORMAL,
                function_name="analyze_interaction_patterns",
                args=[user_id, user_input, contextual_frame.cognitive_load, llm_response.confidence],
                user_id=user_id,
                max_execution_time=60
            )
            
            await background_task_manager.submit_task(pattern_task)
            
            # Trigger cache pattern analysis
            await cache_warming_engine.analyze_access_patterns(
                f"user_patterns:{user_id}",
                user_id=user_id
            )
            
        except Exception as e:
            logger.error("Pattern analysis scheduling error", user_id=user_id, error=str(e))
    
    async def _schedule_circuit_breaker_update(self, user_id: str, success: bool) -> None:
        """Schedule circuit breaker update as background task."""
        try:
            # Update cached circuit breaker state
            cache_key = f"circuit_breaker:{user_id}"
            current_state = await cache_manager.get(cache_key, user_id=user_id)
            
            if current_state:
                circuit_state = CircuitBreakerState(**current_state)
                
                if success:
                    circuit_state.is_open = False
                    circuit_state.failure_count = 0
                    circuit_state.last_failure = None
                    circuit_state.next_test_time = None
                else:
                    circuit_state.failure_count += 1
                    circuit_state.last_failure = datetime.utcnow()
                    
                    if circuit_state.should_trip():
                        circuit_state.is_open = True
                        circuit_state.next_test_time = datetime.utcnow() + timedelta(hours=2)
                
                # Update cache
                await cache_manager.set(
                    cache_key,
                    circuit_state.model_dump(),
                    ttl=300,
                    priority=CachePriority.HIGH,
                    user_id=user_id
                )
            
        except Exception as e:
            logger.error("Circuit breaker update error", user_id=user_id, error=str(e))
    
    async def _schedule_context_cache_warming(
        self,
        user_id: str,
        contextual_frame: ContextualFrame
    ) -> None:
        """Schedule context cache warming for related patterns."""
        try:
            # Identify related context patterns to warm
            if contextual_frame.frame.task_focus:
                related_patterns = [
                    f"context_frame:{user_id}:{contextual_frame.frame.task_focus}:*",
                    f"user_patterns:{user_id}",
                    f"task_context:{contextual_frame.frame.task_focus}"
                ]
                
                await cache_warming_engine.schedule_warming_task(
                    key_patterns=related_patterns,
                    priority=CachePriority.NORMAL,
                    user_id=user_id
                )
            
        except Exception as e:
            logger.error("Context cache warming error", user_id=user_id, error=str(e))
    
    async def _execute_immediate_actions(
        self,
        user_id: str,
        contextual_frame: ContextualFrame,
        llm_response: LLMResponse
    ) -> List[str]:
        """Execute actions that require immediate feedback."""
        actions_taken = []
        
        try:
            # High cognitive load warning (immediate for ADHD users)
            if contextual_frame.cognitive_load > 0.8:
                actions_taken.append("cognitive_load_warning")
                
                # Cache high cognitive load state for future optimization
                await cache_manager.set(
                    f"cognitive_load_state:{user_id}",
                    {"high_load": True, "timestamp": datetime.utcnow().isoformat()},
                    ttl=1800,  # 30 minutes
                    priority=CachePriority.HIGH,
                    user_id=user_id
                )
            
            # Crisis detection (immediate action required)
            if llm_response.source == "hard_coded":
                actions_taken.append("crisis_response")
                
                # Invalidate non-essential caches to free resources
                await cache_invalidation_engine.invalidate_with_dependencies(
                    f"user_cache:{user_id}:non_essential"
                )
            
            return actions_taken
            
        except Exception as e:
            logger.error("Immediate actions execution error", user_id=user_id, error=str(e))
            return actions_taken
    
    async def _cache_context_frame(
        self,
        user_id: str,
        task_focus: Optional[str],
        user_input: str,
        frame: ContextualFrame
    ) -> None:
        """Cache context frame for future use."""
        try:
            input_hash = hash(user_input) % 10000
            cache_key = f"context_frame:{user_id}:{task_focus}:{input_hash}"
            
            cache_data = {
                'frame_data': frame.model_dump(),
                'cached_at': datetime.utcnow().isoformat()
            }
            
            await cache_manager.set(
                cache_key,
                cache_data,
                ttl=self.context_cache_ttl,
                priority=CachePriority.HIGH,
                user_id=user_id
            )
            
        except Exception as e:
            logger.error("Context frame caching error", user_id=user_id, error=str(e))
    
    async def _get_cached_nudge_patterns(self, user_id: str) -> Dict[str, Any]:
        """Get cached nudge patterns for personalization."""
        try:
            cache_key = f"nudge_patterns:{user_id}"
            patterns = await cache_manager.get(
                cache_key,
                priority=CachePriority.NORMAL,
                user_id=user_id
            )
            
            return patterns or {}
            
        except Exception as e:
            logger.error("Nudge patterns cache error", user_id=user_id, error=str(e))
            return {}
    
    async def _generate_anchor_response(self, user_id: str) -> LLMResponse:
        """Generate personalized anchor response for circuit breaker."""
        return LLMResponse(
            text="I notice you might need some space right now. I'm here when you're ready, no pressure. Take care of yourself. 💙",
            source="anchor_mode_cached",
            confidence=1.0,
            model_used="circuit_breaker_cached"
        )
    
    async def _schedule_crisis_analysis(self, user_id: str, user_input: str) -> None:
        """Schedule crisis analysis in background (non-blocking)."""
        try:
            crisis_task = TaskDefinition(
                name="Crisis situation analysis",
                task_type=TaskType.SAFETY_INTERVENTION,
                priority=TaskPriority.CRISIS,
                function_name="analyze_crisis_situation",
                args=[user_id, user_input],
                user_id=user_id,
                max_execution_time=60
            )
            
            await background_task_manager.submit_task(crisis_task)
            
        except Exception as e:
            logger.error("Crisis analysis scheduling error", user_id=user_id, error=str(e))
    
    async def _update_performance_metrics(
        self,
        total_time_ms: float,
        llm_time_ms: float
    ) -> None:
        """Update performance metrics."""
        try:
            # Update running average
            current_avg = self.performance_stats['average_response_time_ms']
            total_requests = self.performance_stats['total_requests']
            
            new_avg = ((current_avg * (total_requests - 1)) + total_time_ms) / total_requests
            self.performance_stats['average_response_time_ms'] = new_avg
            
            # Cache performance metrics
            await cache_manager.set(
                "cognitive_loop_performance",
                self.performance_stats,
                ttl=300,  # 5 minutes
                priority=CachePriority.NORMAL
            )
            
        except Exception as e:
            logger.error("Performance metrics update error", error=str(e))
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced cognitive loop statistics."""
        original_stats = self.original_loop.get_stats()
        
        enhanced_stats = {
            **original_stats,
            'enhanced_performance': self.performance_stats,
            'cache_integration': {
                'cache_hit_rate': (
                    self.performance_stats['cache_hits'] / 
                    max(self.performance_stats['total_requests'], 1)
                ),
                'background_operation_rate': (
                    self.performance_stats['background_operations'] /
                    max(self.performance_stats['total_requests'], 1)
                ),
                'average_response_time_ms': self.performance_stats['average_response_time_ms']
            },
            'adhd_optimization': {
                'crisis_response_time_target_ms': self.crisis_response_time_target_ms,
                'user_response_time_target_ms': self.user_response_time_target_ms,
                'crisis_responses_immediate': self.performance_stats['crisis_responses'],
                'performance_targets_met': (
                    self.performance_stats['average_response_time_ms'] <= 
                    self.user_response_time_target_ms
                )
            }
        }
        
        return enhanced_stats


# Global enhanced cognitive loop instance
enhanced_cognitive_loop = EnhancedCognitiveLoop()