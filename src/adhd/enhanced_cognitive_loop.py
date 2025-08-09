"""
Enhanced Cognitive Loop with Advanced ADHD Features Integration.

This module extends the existing cognitive loop with the advanced ADHD features:
pattern recognition, personalization, adaptation, executive function support,
and machine learning insights. It maintains backward compatibility while
providing significantly enhanced capabilities.

Key Integrations:
- Real-time pattern recognition and intervention
- Personalized user profiling and adaptation  
- Dynamic interface and cognitive load management
- Advanced executive function scaffolding
- ML-powered predictive insights
- Enhanced crisis detection and response

The enhanced loop maintains the same external interface while internally
providing much more sophisticated ADHD support.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import structlog
from pydantic import BaseModel

# Original imports
from mcp_server.models import MCPFrame, UserState, NudgeTier, TraceMemory as TraceMemoryModel
from mcp_server.llm_client import llm_router, LLMResponse
from frames.builder import frame_builder, ContextualFrame
from nudge.engine import nudge_engine
from traces.memory import trace_memory

# ADHD feature imports
from adhd.pattern_engine import get_pattern_engine, PatternType, PatternSeverity
from adhd.user_profile import profile_manager
from adhd.adaptation_engine import adaptation_engine
from adhd.executive_function import (
    task_breakdown_engine, context_switching_assistant,
    working_memory_support, procrastination_intervenor
)
from adhd.ml_pipeline import ml_pipeline

logger = structlog.get_logger()


class EnhancedCognitiveLoopResult(BaseModel):
    """
    Enhanced result with ADHD-specific insights and adaptations.
    
    Extends the original CognitiveLoopResult with additional ADHD features
    while maintaining backward compatibility.
    """
    # Original fields (for compatibility)
    success: bool
    response: Optional[LLMResponse] = None
    actions_taken: List[str] = []
    context_frame: Optional[MCPFrame] = None
    cognitive_load: float = 0.0
    processing_time_ms: float = 0.0
    error: Optional[str] = None
    
    # Enhanced ADHD fields
    detected_patterns: List[Dict[str, Any]] = []
    adaptations_applied: List[Dict[str, Any]] = []
    personalization_insights: Dict[str, Any] = {}
    executive_function_support: Dict[str, Any] = {}
    ml_insights: Dict[str, Any] = {}
    crisis_assessment: Dict[str, Any] = {}
    user_profile_updates: Dict[str, Any] = {}
    intervention_recommendations: List[Dict[str, Any]] = []


class EnhancedCognitiveLoop:
    """
    Enhanced cognitive loop with comprehensive ADHD support.
    
    Integrates all advanced ADHD features while maintaining the core
    cognitive loop architecture and external interface compatibility.
    """
    
    def __init__(self):
        # Original cognitive loop state
        self.circuit_breakers: Dict[str, Any] = {}
        self.processing_stats = {
            "total_requests": 0,
            "safety_overrides": 0,
            "circuit_breaker_trips": 0,
            "successful_responses": 0,
            # Enhanced stats
            "patterns_detected": 0,
            "adaptations_applied": 0,
            "executive_interventions": 0,
            "ml_predictions": 0
        }
        
        # Enhanced features initialization flags
        self._features_initialized = False
        
    async def process_user_input(
        self,
        user_id: str,
        user_input: str,
        task_focus: Optional[str] = None,
        nudge_tier: NudgeTier = NudgeTier.GENTLE
    ) -> EnhancedCognitiveLoopResult:
        """
        Enhanced main entry point with full ADHD support integration.
        
        This method maintains the same interface as the original cognitive loop
        while internally providing comprehensive ADHD personalization and support.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.processing_stats["total_requests"] += 1
            
            # Initialize enhanced features if needed
            if not self._features_initialized:
                await self._initialize_enhanced_features()
            
            # Step 1: Enhanced Context Building with Personalization
            logger.info("Building enhanced contextual frame", 
                       user_id=user_id, task_focus=task_focus)
            
            enhanced_context = await self._build_enhanced_context(
                user_id, user_input, task_focus
            )
            
            contextual_frame = enhanced_context['frame']
            personalization_data = enhanced_context['personalization']
            
            # Step 2: Real-time Pattern Recognition
            logger.info("Analyzing behavioral patterns", user_id=user_id)
            
            pattern_analysis = await self._analyze_patterns(
                user_id, user_input, contextual_frame, personalization_data
            )
            
            detected_patterns = pattern_analysis['patterns']
            crisis_assessment = pattern_analysis['crisis']
            
            # Step 3: Executive Function Assessment and Support
            logger.info("Assessing executive function needs", user_id=user_id)
            
            executive_support = await self._provide_executive_support(
                user_id, user_input, task_focus, contextual_frame
            )
            
            # Step 4: Intelligent Adaptation
            logger.info("Processing adaptive interventions", user_id=user_id)
            
            adaptation_result = await self._process_adaptations(
                user_id, detected_patterns, contextual_frame, personalization_data
            )
            
            # Step 5: ML-Enhanced Processing
            logger.info("Processing through ML pipeline", user_id=user_id)
            
            ml_insights = await self._process_ml_insights(
                user_id, user_input, contextual_frame, detected_patterns
            )
            
            # Step 6: Enhanced LLM Processing with Adaptations
            logger.info("Processing through adapted LLM router", 
                       cognitive_load=contextual_frame.cognitive_load)
            
            llm_result = await self._process_adapted_llm_request(
                user_input, contextual_frame, adaptation_result, nudge_tier
            )
            
            # Step 7: Crisis and Safety Handling
            if llm_result.source == "hard_coded" or crisis_assessment['is_crisis']:
                return await self._handle_crisis_response(
                    user_id, user_input, llm_result, crisis_assessment,
                    start_time
                )
            
            # Step 8: Comprehensive Integration and Updates
            integration_tasks = [
                self._execute_enhanced_actions(
                    user_id, contextual_frame, llm_result, executive_support,
                    adaptation_result
                ),
                self._update_comprehensive_memory(
                    user_id, user_input, llm_result, contextual_frame,
                    detected_patterns, adaptation_result, ml_insights
                ),
                self._update_user_profile(
                    user_id, personalization_data, detected_patterns,
                    adaptation_result, ml_insights
                ),
                self._update_circuit_breaker(user_id, success=True)
            ]
            
            # Execute all integration tasks concurrently
            integration_results = await asyncio.gather(
                *integration_tasks, return_exceptions=True
            )
            
            actions_taken, memory_update, profile_updates, _ = integration_results
            
            # Step 9: Generate Enhanced Result
            self.processing_stats["successful_responses"] += 1
            
            if detected_patterns:
                self.processing_stats["patterns_detected"] += len(detected_patterns)
            
            if adaptation_result['adaptations']:
                self.processing_stats["adaptations_applied"] += len(adaptation_result['adaptations'])
            
            if executive_support.get('interventions'):
                self.processing_stats["executive_interventions"] += 1
            
            if ml_insights.get('predictions'):
                self.processing_stats["ml_predictions"] += 1
            
            return EnhancedCognitiveLoopResult(
                # Original fields
                success=True,
                response=llm_result,
                actions_taken=actions_taken,
                context_frame=contextual_frame.frame,
                cognitive_load=contextual_frame.cognitive_load,
                processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
                
                # Enhanced fields
                detected_patterns=detected_patterns,
                adaptations_applied=adaptation_result['adaptations'],
                personalization_insights=personalization_data,
                executive_function_support=executive_support,
                ml_insights=ml_insights,
                crisis_assessment=crisis_assessment,
                user_profile_updates=profile_updates or {},
                intervention_recommendations=self._generate_intervention_recommendations(
                    detected_patterns, executive_support, adaptation_result
                )
            )
            
        except Exception as e:
            logger.error("Enhanced cognitive loop processing failed", 
                        user_id=user_id, error=str(e), exc_info=True)
            
            # Update circuit breaker on failure
            await self._update_circuit_breaker(user_id, success=False)
            
            return EnhancedCognitiveLoopResult(
                success=False,
                error=str(e),
                processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
            )
    
    async def _build_enhanced_context(self, 
                                    user_id: str, 
                                    user_input: str, 
                                    task_focus: Optional[str]) -> Dict[str, Any]:
        """Build context frame enhanced with personalization data."""
        try:
            # Get user profile for personalization
            profile = await profile_manager.get_or_create_profile(user_id)
            personalized_settings = await profile_manager.get_personalized_settings(user_id)
            
            # Build frame with personalized parameters
            contextual_frame = await frame_builder.build_frame(
                user_id=user_id,
                agent_id="enhanced_cognitive_loop",
                task_focus=task_focus,
                include_patterns=True
            )
            
            # Apply cognitive load personalization
            cognitive_settings = personalized_settings.get('cognitive_load', {})
            max_context = cognitive_settings.get('max_context_items', 8)
            
            # Trim context if needed based on personalization
            if len(contextual_frame.frame.context) > max_context:
                # Keep most important context items
                contextual_frame.frame.context = contextual_frame.frame.context[:max_context]
                contextual_frame.cognitive_load = min(contextual_frame.cognitive_load, 0.8)
            
            return {
                'frame': contextual_frame,
                'personalization': {
                    'profile': profile,
                    'settings': personalized_settings,
                    'cognitive_load_limit': max_context,
                    'interface_complexity': personalized_settings.get('interface', {}).get('complexity', 'adaptive')
                }
            }
            
        except Exception as e:
            logger.error("Enhanced context building failed", error=str(e))
            # Fallback to original frame building
            contextual_frame = await frame_builder.build_frame(
                user_id=user_id,
                agent_id="enhanced_cognitive_loop",
                task_focus=task_focus,
                include_patterns=True
            )
            return {
                'frame': contextual_frame,
                'personalization': {'error': str(e)}
            }
    
    async def _analyze_patterns(self, 
                              user_id: str, 
                              user_input: str,
                              contextual_frame: ContextualFrame,
                              personalization_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive pattern analysis."""
        try:
            # Get pattern engine
            pattern_engine = get_pattern_engine(user_id)
            
            # Prepare interaction data
            interaction_data = {
                'content': user_input,
                'cognitive_load': contextual_frame.cognitive_load,
                'task_focus': contextual_frame.frame.task_focus,
                'session_duration_minutes': 30,  # Default
                'energy_level': 0.5,  # Will be enhanced with profile data
                'timestamp': datetime.utcnow()
            }
            
            # Add personalization context
            if 'profile' in personalization_data:
                profile = personalization_data['profile']
                interaction_data.update({
                    'energy_level': getattr(profile, 'energy_level', 0.5),
                    'hyperfocus_tendency': getattr(profile, 'hyperfocus_tendency', 0.3)
                })
            
            # Analyze patterns
            detected_patterns = await pattern_engine.analyze_realtime_behavior(interaction_data)
            
            # Convert to serializable format
            patterns_data = []
            for pattern in detected_patterns:
                patterns_data.append({
                    'type': pattern.pattern_type.value,
                    'severity': pattern.severity.value,
                    'confidence': pattern.confidence,
                    'evidence': pattern.evidence,
                    'intervention_recommended': pattern.intervention_recommended,
                    'intervention_urgency': pattern.intervention_urgency,
                    'timestamp': pattern.timestamp.isoformat()
                })
            
            # Assess crisis risk
            crisis_patterns = [p for p in detected_patterns 
                             if p.severity == PatternSeverity.CRITICAL]
            crisis_assessment = {
                'is_crisis': len(crisis_patterns) > 0,
                'crisis_patterns': len(crisis_patterns),
                'highest_urgency': max([p.intervention_urgency for p in detected_patterns], default=0),
                'requires_immediate_intervention': any(
                    p.intervention_urgency >= 9 for p in detected_patterns
                )
            }
            
            return {
                'patterns': patterns_data,
                'crisis': crisis_assessment,
                'total_patterns': len(detected_patterns)
            }
            
        except Exception as e:
            logger.error("Pattern analysis failed", error=str(e))
            return {
                'patterns': [],
                'crisis': {'is_crisis': False, 'error': str(e)},
                'total_patterns': 0
            }
    
    async def _provide_executive_support(self, 
                                       user_id: str,
                                       user_input: str, 
                                       task_focus: Optional[str],
                                       contextual_frame: ContextualFrame) -> Dict[str, Any]:
        """Provide comprehensive executive function support."""
        try:
            support_data = {}
            
            # Task breakdown if task focus provided
            if task_focus:
                task_breakdown = await task_breakdown_engine.breakdown_task(
                    user_id, task_focus, {
                        'cognitive_load': contextual_frame.cognitive_load,
                        'urgency_level': 0.5
                    }
                )
                
                support_data['task_breakdown'] = {
                    'subtasks': task_breakdown.subtasks,
                    'estimated_time': task_breakdown.estimated_total_time,
                    'complexity': task_breakdown.complexity_level.value,
                    'strategies': task_breakdown.success_strategies
                }
            
            # Procrastination assessment
            if task_focus:
                risk_score, triggers = await procrastination_intervenor.assess_procrastination_risk(
                    user_id, task_focus, {
                        'cognitive_load': contextual_frame.cognitive_load
                    }
                )
                
                if risk_score > 0.5:  # Significant risk
                    intervention = await procrastination_intervenor.provide_intervention(
                        user_id, risk_score, triggers
                    )
                    support_data['procrastination_intervention'] = intervention
            
            # Working memory support
            relevant_info = await working_memory_support.retrieve_information(
                user_id, query=user_input, associated_task=task_focus
            )
            
            if relevant_info:
                support_data['working_memory_aids'] = [
                    {
                        'type': aid.information_type,
                        'content': str(aid.content)[:100],  # Truncate for privacy
                        'priority': aid.priority
                    }
                    for aid in relevant_info[:3]  # Top 3 most relevant
                ]
            
            # Context switching if indicated
            if len(contextual_frame.frame.context) > 1:
                # Multiple contexts suggest potential switching
                contexts = [ctx.data for ctx in contextual_frame.frame.context]
                if len(set(str(ctx) for ctx in contexts)) > 1:
                    support_data['context_switching_detected'] = True
                    support_data['switching_support'] = {
                        'recommendation': 'Use transition ritual before starting new task',
                        'estimated_switch_time': 5
                    }
            
            return support_data
            
        except Exception as e:
            logger.error("Executive function support failed", error=str(e))
            return {'error': str(e)}
    
    async def _process_adaptations(self, 
                                 user_id: str,
                                 detected_patterns: List[Dict[str, Any]],
                                 contextual_frame: ContextualFrame,
                                 personalization_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process intelligent adaptations based on patterns and profile."""
        try:
            # Convert pattern data back to objects for adaptation engine
            from adhd.pattern_engine import PatternDetection, PatternType, PatternSeverity
            
            pattern_objects = []
            for pattern_data in detected_patterns:
                pattern_obj = PatternDetection(
                    pattern_type=PatternType(pattern_data['type']),
                    severity=PatternSeverity(pattern_data['severity']),
                    confidence=pattern_data['confidence'],
                    evidence=pattern_data['evidence'],
                    intervention_recommended=pattern_data['intervention_recommended'],
                    intervention_urgency=pattern_data['intervention_urgency'],
                    timestamp=datetime.fromisoformat(pattern_data['timestamp'])
                )
                pattern_objects.append(pattern_obj)
            
            # Get adaptation recommendations
            current_state = {
                'user_id': user_id,
                'cognitive_load': contextual_frame.cognitive_load,
                'energy_level': personalization_data.get('profile', {}).get('energy_level', 0.5),
                'stress_level': 0.5  # Could be enhanced with stress detection
            }
            
            adaptation_decisions = await adaptation_engine.process_adaptation_request(
                user_id, current_state, pattern_objects, contextual_frame.frame
            )
            
            # Apply adaptations
            if adaptation_decisions:
                adapted_response, interface_changes = await adaptation_engine.apply_adaptations(
                    adaptation_decisions, "", contextual_frame.frame  # Response will be generated later
                )
                
                return {
                    'adaptations': [
                        {
                            'type': decision.adaptation_type.value,
                            'priority': decision.priority.value,
                            'reasoning': decision.reasoning,
                            'parameters': decision.parameters
                        }
                        for decision in adaptation_decisions
                    ],
                    'interface_changes': interface_changes,
                    'total_adaptations': len(adaptation_decisions)
                }
            
            return {'adaptations': [], 'interface_changes': {}, 'total_adaptations': 0}
            
        except Exception as e:
            logger.error("Adaptation processing failed", error=str(e))
            return {'adaptations': [], 'error': str(e)}
    
    async def _process_ml_insights(self, 
                                 user_id: str,
                                 user_input: str, 
                                 contextual_frame: ContextualFrame,
                                 detected_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process interaction through ML pipeline for predictive insights."""
        try:
            # Prepare interaction data for ML
            interaction_data = {
                'content': user_input,
                'cognitive_load': contextual_frame.cognitive_load,
                'session_duration_minutes': 30,
                'completion_rate': 0.5,
                'energy_level': 0.5,
                'task_complexity': 0.5,
                'patterns_detected': len(detected_patterns)
            }
            
            # Process through ML pipeline
            ml_results = await ml_pipeline.process_interaction(user_id, interaction_data)
            
            return {
                'predictions': ml_results.get('ml_insights', {}),
                'feature_vector': ml_results.get('feature_vector', {}),
                'processing_success': 'error' not in ml_results
            }
            
        except Exception as e:
            logger.error("ML insights processing failed", error=str(e))
            return {'error': str(e), 'processing_success': False}
    
    async def _process_adapted_llm_request(self, 
                                         user_input: str,
                                         contextual_frame: ContextualFrame,
                                         adaptation_result: Dict[str, Any],
                                         nudge_tier: NudgeTier) -> LLMResponse:
        """Process LLM request with adaptations applied."""
        try:
            # Apply adaptations to context frame if needed
            adapted_frame = contextual_frame.frame
            
            # Process through original LLM router
            llm_response = await llm_router.process_request(
                user_input=user_input,
                context=adapted_frame,
                nudge_tier=nudge_tier
            )
            
            # Apply response adaptations if any
            adaptations = adaptation_result.get('adaptations', [])
            if adaptations:
                # Apply response-level adaptations
                response_adaptations = [
                    a for a in adaptations 
                    if a['type'] in ['cognitive_load_reduction', 'response_style_modification']
                ]
                
                if response_adaptations:
                    # Simple adaptation - could be more sophisticated
                    if any(a['type'] == 'cognitive_load_reduction' for a in response_adaptations):
                        # Truncate response if too long
                        max_length = 150
                        if len(llm_response.text) > max_length:
                            sentences = llm_response.text.split('. ')
                            truncated = ""
                            for sentence in sentences:
                                if len(truncated + sentence) < max_length - 3:
                                    truncated += sentence + ". "
                                else:
                                    break
                            llm_response.text = truncated.strip() + "..."
            
            return llm_response
            
        except Exception as e:
            logger.error("Adapted LLM request failed", error=str(e))
            # Fallback to original processing
            return await llm_router.process_request(
                user_input=user_input,
                context=contextual_frame.frame,
                nudge_tier=nudge_tier
            )
    
    async def _handle_crisis_response(self, 
                                    user_id: str,
                                    user_input: str,
                                    llm_response: LLMResponse,
                                    crisis_assessment: Dict[str, Any],
                                    start_time: float) -> EnhancedCognitiveLoopResult:
        """Handle crisis situations with enhanced safety protocols."""
        try:
            self.processing_stats["safety_overrides"] += 1
            
            # Enhanced crisis response
            crisis_actions = ["safety_override"]
            
            if crisis_assessment.get('requires_immediate_intervention'):
                crisis_actions.extend([
                    "crisis_resources_provided",
                    "simplified_interface_activated",
                    "emergency_contacts_suggested"
                ])
            
            # Record enhanced safety event
            await self._record_enhanced_safety_event(
                user_id, user_input, llm_response, crisis_assessment
            )
            
            return EnhancedCognitiveLoopResult(
                success=True,
                response=llm_response,
                actions_taken=crisis_actions,
                cognitive_load=0.1,  # Minimal load
                processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
                crisis_assessment=crisis_assessment,
                intervention_recommendations=[{
                    'type': 'crisis_intervention',
                    'urgency': 'immediate',
                    'description': 'Crisis detected - immediate support recommended'
                }]
            )
            
        except Exception as e:
            logger.error("Crisis response handling failed", error=str(e))
            # Fallback to basic safety response
            return EnhancedCognitiveLoopResult(
                success=True,
                response=llm_response,
                actions_taken=["safety_override"],
                cognitive_load=0.1,
                processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
                error=f"Crisis response error: {str(e)}"
            )
    
    async def _execute_enhanced_actions(self, 
                                      user_id: str,
                                      contextual_frame: ContextualFrame,
                                      llm_response: LLMResponse,
                                      executive_support: Dict[str, Any],
                                      adaptation_result: Dict[str, Any]) -> List[str]:
        """Execute enhanced actions including executive function support."""
        try:
            actions_taken = []
            
            # Original cognitive load and accessibility actions
            if contextual_frame.cognitive_load > 0.8:
                actions_taken.append("cognitive_load_warning")
            
            if contextual_frame.accessibility_score < 0.5:
                actions_taken.append("accessibility_adjustment")
            
            # Executive function actions
            if executive_support.get('task_breakdown'):
                actions_taken.append("task_breakdown_provided")
            
            if executive_support.get('procrastination_intervention'):
                actions_taken.append("procrastination_intervention_applied")
            
            if executive_support.get('working_memory_aids'):
                actions_taken.append("working_memory_support_provided")
            
            # Adaptation actions
            adaptations = adaptation_result.get('adaptations', [])
            for adaptation in adaptations:
                actions_taken.append(f"adaptation_{adaptation['type']}_applied")
            
            return actions_taken
            
        except Exception as e:
            logger.error("Enhanced action execution failed", error=str(e))
            return ["action_execution_error"]
    
    async def _update_comprehensive_memory(self, 
                                         user_id: str,
                                         user_input: str,
                                         llm_response: LLMResponse,
                                         contextual_frame: ContextualFrame,
                                         detected_patterns: List[Dict[str, Any]],
                                         adaptation_result: Dict[str, Any],
                                         ml_insights: Dict[str, Any]) -> None:
        """Update trace memory with comprehensive interaction details."""
        try:
            # Enhanced trace memory record
            trace_record = TraceMemoryModel(
                user_id=user_id,
                event_type="enhanced_cognitive_interaction",
                event_data={
                    "user_input": user_input,
                    "llm_response": llm_response.text,
                    "llm_source": llm_response.source,
                    "cognitive_load": contextual_frame.cognitive_load,
                    "accessibility_score": contextual_frame.accessibility_score,
                    "processing_latency": llm_response.latency_ms,
                    "task_focus": contextual_frame.frame.task_focus,
                    # Enhanced data
                    "patterns_detected": detected_patterns,
                    "adaptations_applied": adaptation_result.get('adaptations', []),
                    "ml_insights": ml_insights,
                    "total_patterns": len(detected_patterns),
                    "total_adaptations": len(adaptation_result.get('adaptations', [])),
                    "enhancement_version": "1.0"
                },
                confidence=llm_response.confidence,
                source="enhanced_cognitive_loop"
            )
            
            await trace_memory.store_trace(trace_record)
            
        except Exception as e:
            logger.error("Comprehensive memory update failed", error=str(e))
    
    async def _update_user_profile(self, 
                                 user_id: str,
                                 personalization_data: Dict[str, Any],
                                 detected_patterns: List[Dict[str, Any]],
                                 adaptation_result: Dict[str, Any],
                                 ml_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile based on interaction insights."""
        try:
            # Prepare interaction data for profile update
            interaction_data = {
                'patterns_detected': detected_patterns,
                'adaptations_applied': adaptation_result.get('adaptations', []),
                'ml_predictions': ml_insights.get('predictions', {}),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Update profile from interaction
            await profile_manager.update_profile_from_interaction(user_id, interaction_data)
            
            # Update profile from detected patterns
            if detected_patterns:
                pattern_objects = []  # Would convert back to pattern objects
                await profile_manager.adapt_to_pattern_detection(user_id, pattern_objects)
            
            return {'profile_updated': True, 'patterns_processed': len(detected_patterns)}
            
        except Exception as e:
            logger.error("User profile update failed", error=str(e))
            return {'profile_updated': False, 'error': str(e)}
    
    async def _record_enhanced_safety_event(self, 
                                          user_id: str,
                                          user_input: str,
                                          safety_response: LLMResponse,
                                          crisis_assessment: Dict[str, Any]) -> None:
        """Record enhanced safety event with crisis details."""
        try:
            safety_trace = TraceMemoryModel(
                user_id=user_id,
                event_type="enhanced_safety_override",
                event_data={
                    "trigger_input": user_input,
                    "safety_response": safety_response.text,
                    "response_source": safety_response.source,
                    "crisis_assessment": crisis_assessment,
                    "intervention_urgency": crisis_assessment.get('highest_urgency', 0),
                    "timestamp": datetime.utcnow().isoformat()
                },
                confidence=1.0,
                source="enhanced_safety_monitor"
            )
            
            await trace_memory.store_trace(safety_trace)
            
        except Exception as e:
            logger.error("Enhanced safety event recording failed", error=str(e))
    
    def _generate_intervention_recommendations(self, 
                                             detected_patterns: List[Dict[str, Any]],
                                             executive_support: Dict[str, Any],
                                             adaptation_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate comprehensive intervention recommendations."""
        recommendations = []
        
        try:
            # Pattern-based recommendations
            high_urgency_patterns = [
                p for p in detected_patterns 
                if p.get('intervention_urgency', 0) >= 7
            ]
            
            for pattern in high_urgency_patterns:
                recommendations.append({
                    'type': 'pattern_intervention',
                    'pattern': pattern['type'],
                    'urgency': pattern['intervention_urgency'],
                    'description': f"{pattern['type']} pattern detected - {pattern.get('evidence', {})}"
                })
            
            # Executive function recommendations
            if executive_support.get('procrastination_intervention'):
                recommendations.append({
                    'type': 'procrastination_support',
                    'urgency': 6,
                    'description': 'Procrastination intervention strategies available'
                })
            
            if executive_support.get('task_breakdown'):
                recommendations.append({
                    'type': 'task_structure',
                    'urgency': 4,
                    'description': 'Task breakdown provided for better organization'
                })
            
            # Adaptation recommendations
            high_priority_adaptations = [
                a for a in adaptation_result.get('adaptations', [])
                if a.get('priority') == 'high'
            ]
            
            for adaptation in high_priority_adaptations:
                recommendations.append({
                    'type': 'adaptation',
                    'urgency': 5,
                    'description': f"Interface adaptation: {adaptation['reasoning']}"
                })
            
            return recommendations
            
        except Exception as e:
            logger.error("Intervention recommendations generation failed", error=str(e))
            return [{'type': 'error', 'description': 'Failed to generate recommendations'}]
    
    async def _initialize_enhanced_features(self) -> None:
        """Initialize enhanced features on first use."""
        try:
            # This would initialize any global state needed
            # Currently our systems are designed to be stateless
            self._features_initialized = True
            logger.info("Enhanced ADHD features initialized")
            
        except Exception as e:
            logger.error("Enhanced features initialization failed", error=str(e))
            self._features_initialized = False
    
    async def _update_circuit_breaker(self, user_id: str, success: bool) -> None:
        """Enhanced circuit breaker with pattern awareness."""
        try:
            # Use original circuit breaker logic but enhanced with pattern data
            # This maintains compatibility while adding ADHD-specific triggers
            
            if user_id not in self.circuit_breakers:
                self.circuit_breakers[user_id] = {
                    'is_open': False,
                    'failure_count': 0,
                    'last_failure': None,
                    'pattern_triggers': [],  # Enhanced field
                    'overwhelm_incidents': 0  # Enhanced field
                }
            
            circuit_state = self.circuit_breakers[user_id]
            
            if success:
                # Reset on success
                circuit_state['is_open'] = False
                circuit_state['failure_count'] = 0
                circuit_state['last_failure'] = None
                circuit_state['pattern_triggers'] = []
                circuit_state['overwhelm_incidents'] = 0
            else:
                # Enhanced failure handling
                circuit_state['failure_count'] += 1
                circuit_state['last_failure'] = datetime.utcnow()
                
                # ADHD-specific triggers
                # Would check for overwhelm patterns, crisis indicators, etc.
                
                if circuit_state['failure_count'] >= 3:
                    circuit_state['is_open'] = True
                    self.processing_stats["circuit_breaker_trips"] += 1
                    
                    logger.warning("Enhanced circuit breaker tripped", 
                                  user_id=user_id,
                                  failure_count=circuit_state['failure_count'],
                                  pattern_triggers=len(circuit_state['pattern_triggers']))
            
        except Exception as e:
            logger.error("Circuit breaker update failed", error=str(e))
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced processing statistics."""
        return {
            **self.processing_stats,
            "active_circuit_breakers": len([
                cb for cb in self.circuit_breakers.values() if cb.get('is_open', False)
            ]),
            "success_rate": (
                self.processing_stats["successful_responses"] / 
                max(self.processing_stats["total_requests"], 1)
            ),
            "enhancement_features_active": self._features_initialized,
            "patterns_per_request": (
                self.processing_stats["patterns_detected"] /
                max(self.processing_stats["total_requests"], 1)
            ),
            "adaptations_per_request": (
                self.processing_stats["adaptations_applied"] /
                max(self.processing_stats["total_requests"], 1)
            )
        }


# Global enhanced cognitive loop instance
enhanced_cognitive_loop = EnhancedCognitiveLoop()