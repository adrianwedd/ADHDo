"""
Advanced Executive Function Support Tools for ADHD.

This module implements comprehensive executive function support designed
specifically for ADHD cognitive patterns. It provides intelligent task
breakdown, context-switching assistance, working memory support, and
procrastination intervention while respecting user autonomy.

Core Features:
- Intelligent task breakdown and sequencing
- Context-switching assistance with transition protocols
- Working memory support with external cognition tools
- Planning and organization assistance with ADHD-optimized methodologies
- Procrastination intervention with graduated support levels
- Time estimation training with feedback loops
- Energy-aware workload distribution

The system is designed to augment rather than replace executive function,
empowering users to develop their own strategies while providing scaffolding.
"""
import asyncio
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from collections import deque, defaultdict

import structlog
from pydantic import BaseModel, Field

from mcp_server.models import TraceMemory as TraceMemoryModel, Task
from traces.memory import trace_memory
from adhd.pattern_engine import get_pattern_engine, PatternType
from adhd.user_profile import profile_manager

logger = structlog.get_logger()


class TaskComplexity(Enum):
    """Task complexity levels for ADHD-friendly breakdown."""
    MICRO = "micro"          # 2-5 minutes
    MINI = "mini"            # 5-15 minutes  
    SMALL = "small"          # 15-30 minutes
    MEDIUM = "medium"        # 30-60 minutes
    LARGE = "large"          # 1-2 hours
    COMPLEX = "complex"      # Multi-session


class ExecutiveFunction(Enum):
    """Executive function domains."""
    INITIATION = "initiation"              # Starting tasks
    WORKING_MEMORY = "working_memory"      # Holding information
    COGNITIVE_FLEXIBILITY = "cognitive_flexibility"  # Task switching
    INHIBITORY_CONTROL = "inhibitory_control"       # Impulse control
    PLANNING = "planning"                  # Future-oriented thinking
    ORGANIZATION = "organization"          # Systematic arrangement
    TIME_MANAGEMENT = "time_management"    # Temporal processing
    EMOTIONAL_REGULATION = "emotional_regulation"  # Managing feelings


class ProcrastinationTrigger(Enum):
    """Common ADHD procrastination triggers."""
    OVERWHELM = "overwhelm"                # Task feels too big
    PERFECTIONISM = "perfectionism"       # Fear of not doing well enough
    BOREDOM = "boredom"                   # Task lacks interest/stimulation
    UNCLEAR_REQUIREMENTS = "unclear_requirements"  # Don't know what to do
    ENERGY_MISMATCH = "energy_mismatch"   # Wrong energy level for task
    CONTEXT_SWITCHING = "context_switching"  # Hard to shift focus
    FEAR_FAILURE = "fear_failure"         # Afraid of making mistakes
    LACK_STRUCTURE = "lack_structure"     # No clear process


@dataclass
class TaskBreakdown:
    """Result of intelligent task breakdown."""
    original_task: str
    subtasks: List[Dict[str, Any]]
    estimated_total_time: int  # minutes
    complexity_level: TaskComplexity
    executive_functions_required: List[ExecutiveFunction]
    potential_obstacles: List[str]
    success_strategies: List[str]
    energy_requirements: Dict[str, float]  # energy type -> level needed


@dataclass
class ContextSwitchPlan:
    """Plan for transitioning between contexts/tasks."""
    from_context: str
    to_context: str
    transition_steps: List[str]
    estimated_switch_time: int  # minutes
    mental_prep_needed: bool
    physical_prep_needed: bool
    potential_friction_points: List[str]
    success_strategies: List[str]


@dataclass
class WorkingMemoryAid:
    """External working memory support."""
    information_type: str
    content: Any
    priority: int
    expires_at: Optional[datetime]
    retrieval_cues: List[str]
    associated_task: Optional[str]


class TaskBreakdownEngine:
    """
    Intelligent task breakdown engine optimized for ADHD cognitive patterns.
    
    Automatically decomposes complex tasks into ADHD-friendly chunks that
    account for attention span, dopamine needs, and executive function
    capabilities.
    """
    
    def __init__(self):
        self.breakdown_history: Dict[str, List[TaskBreakdown]] = defaultdict(list)
        self.success_patterns: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # ADHD-optimized parameters
        self.max_micro_task_time = 5    # minutes
        self.ideal_focus_block = 25     # Pomodoro-style
        self.max_continuous_work = 90   # minutes before mandatory break
        
    async def breakdown_task(self, 
                           user_id: str,
                           task_description: str,
                           context: Dict[str, Any]) -> TaskBreakdown:
        """Break down a task into ADHD-friendly subtasks."""
        try:
            # Get user profile for personalization
            profile = await profile_manager.get_or_create_profile(user_id)
            
            # Analyze task complexity
            complexity = await self._assess_task_complexity(task_description, context)
            
            # Generate subtasks based on complexity and user patterns
            subtasks = await self._generate_subtasks(
                task_description, complexity, profile, context
            )
            
            # Estimate time requirements
            total_time = await self._estimate_total_time(subtasks, profile)
            
            # Identify required executive functions
            exec_functions = await self._identify_executive_functions(
                task_description, subtasks
            )
            
            # Predict obstacles and strategies
            obstacles = await self._predict_obstacles(
                subtasks, exec_functions, profile
            )
            strategies = await self._suggest_strategies(
                obstacles, exec_functions, profile
            )
            
            # Calculate energy requirements
            energy_req = await self._calculate_energy_requirements(
                subtasks, exec_functions
            )
            
            breakdown = TaskBreakdown(
                original_task=task_description,
                subtasks=subtasks,
                estimated_total_time=total_time,
                complexity_level=complexity,
                executive_functions_required=exec_functions,
                potential_obstacles=obstacles,
                success_strategies=strategies,
                energy_requirements=energy_req
            )
            
            # Store for learning
            self.breakdown_history[user_id].append(breakdown)
            
            logger.info("Task breakdown completed", 
                       user_id=user_id,
                       original_task=task_description[:50],
                       subtask_count=len(subtasks),
                       complexity=complexity.value)
            
            return breakdown
            
        except Exception as e:
            logger.error("Task breakdown failed", 
                        user_id=user_id, 
                        task=task_description, 
                        error=str(e))
            
            # Return simple fallback breakdown
            return TaskBreakdown(
                original_task=task_description,
                subtasks=[{"title": task_description, "time_estimate": 30}],
                estimated_total_time=30,
                complexity_level=TaskComplexity.MEDIUM,
                executive_functions_required=[ExecutiveFunction.INITIATION],
                potential_obstacles=["Getting started"],
                success_strategies=["Just begin with any small step"],
                energy_requirements={"mental": 0.5}
            )
    
    async def _assess_task_complexity(self, 
                                    task_description: str, 
                                    context: Dict[str, Any]) -> TaskComplexity:
        """Assess the complexity level of a task."""
        try:
            # Analyze task description
            word_count = len(task_description.split())
            complexity_indicators = 0
            
            # Complexity indicators
            complex_words = ['analyze', 'design', 'research', 'implement', 'coordinate', 
                           'develop', 'create', 'plan', 'organize', 'manage']
            complexity_indicators += sum(1 for word in complex_words 
                                       if word in task_description.lower())
            
            # Multi-step indicators
            step_words = ['then', 'next', 'after', 'before', 'first', 'second', 
                         'finally', 'and', 'also']
            complexity_indicators += sum(1 for word in step_words 
                                       if word in task_description.lower())
            
            # Context complexity
            if context.get('deadline_pressure', False):
                complexity_indicators += 1
            if context.get('involves_others', False):
                complexity_indicators += 1
            if context.get('new_skill_required', False):
                complexity_indicators += 2
            
            # Determine complexity level
            if word_count <= 5 and complexity_indicators == 0:
                return TaskComplexity.MICRO
            elif word_count <= 10 and complexity_indicators <= 1:
                return TaskComplexity.MINI
            elif word_count <= 15 and complexity_indicators <= 2:
                return TaskComplexity.SMALL
            elif word_count <= 25 and complexity_indicators <= 3:
                return TaskComplexity.MEDIUM
            elif word_count <= 40 and complexity_indicators <= 5:
                return TaskComplexity.LARGE
            else:
                return TaskComplexity.COMPLEX
            
        except Exception as e:
            logger.warning("Task complexity assessment failed", error=str(e))
            return TaskComplexity.MEDIUM
    
    async def _generate_subtasks(self, 
                               task_description: str,
                               complexity: TaskComplexity,
                               profile: Any,
                               context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate ADHD-friendly subtasks."""
        try:
            subtasks = []
            
            if complexity == TaskComplexity.MICRO:
                # Single micro task
                subtasks.append({
                    "title": task_description,
                    "time_estimate": 3,
                    "dopamine_reward": "completion_check",
                    "prerequisites": [],
                    "context_required": "minimal"
                })
                
            elif complexity == TaskComplexity.MINI:
                # 2-3 micro tasks
                if 'email' in task_description.lower():
                    subtasks = [
                        {"title": "Open email client", "time_estimate": 1},
                        {"title": "Compose message", "time_estimate": 8},
                        {"title": "Review and send", "time_estimate": 2}
                    ]
                else:
                    # Generic breakdown
                    subtasks = [
                        {"title": f"Start: {task_description}", "time_estimate": 2},
                        {"title": f"Complete: {task_description}", "time_estimate": 10},
                        {"title": f"Review: {task_description}", "time_estimate": 3}
                    ]
            
            elif complexity in [TaskComplexity.SMALL, TaskComplexity.MEDIUM]:
                # Break into logical steps
                if 'write' in task_description.lower():
                    subtasks = [
                        {"title": "Gather materials/research", "time_estimate": 10},
                        {"title": "Create outline", "time_estimate": 5},
                        {"title": "Write first draft", "time_estimate": 20},
                        {"title": "Review and edit", "time_estimate": 10},
                        {"title": "Final check and submit", "time_estimate": 5}
                    ]
                elif 'plan' in task_description.lower():
                    subtasks = [
                        {"title": "Define objectives", "time_estimate": 8},
                        {"title": "List required resources", "time_estimate": 7},
                        {"title": "Create timeline", "time_estimate": 10},
                        {"title": "Identify potential issues", "time_estimate": 8},
                        {"title": "Finalize plan", "time_estimate": 7}
                    ]
                else:
                    # Generic breakdown for medium complexity
                    subtasks = [
                        {"title": "Prepare and gather resources", "time_estimate": 8},
                        {"title": "Begin main task", "time_estimate": 15},
                        {"title": "Complete core work", "time_estimate": 12},
                        {"title": "Review and refine", "time_estimate": 8},
                        {"title": "Wrap up and organize", "time_estimate": 7}
                    ]
            
            elif complexity in [TaskComplexity.LARGE, TaskComplexity.COMPLEX]:
                # Multi-session breakdown
                subtasks = [
                    {"title": "Project planning session", "time_estimate": 30},
                    {"title": "Research and preparation", "time_estimate": 45},
                    {"title": "Core work - Session 1", "time_estimate": 60},
                    {"title": "Break and review progress", "time_estimate": 15},
                    {"title": "Core work - Session 2", "time_estimate": 45},
                    {"title": "Integration and refinement", "time_estimate": 30},
                    {"title": "Final review and completion", "time_estimate": 20}
                ]
            
            # Add ADHD-specific enhancements to each subtask
            for i, subtask in enumerate(subtasks):
                subtask.update({
                    "order": i + 1,
                    "dopamine_reward": self._suggest_dopamine_reward(subtask),
                    "break_after": subtask.get("time_estimate", 15) > 20,
                    "hyperfocus_risk": subtask.get("time_estimate", 15) > 30,
                    "context_switching_required": i > 0,
                    "working_memory_load": self._assess_working_memory_load(subtask)
                })
            
            return subtasks
            
        except Exception as e:
            logger.error("Subtask generation failed", error=str(e))
            return [{"title": task_description, "time_estimate": 30}]
    
    async def _estimate_total_time(self, 
                                 subtasks: List[Dict[str, Any]], 
                                 profile: Any) -> int:
        """Estimate total time accounting for ADHD factors."""
        try:
            base_time = sum(task.get("time_estimate", 15) for task in subtasks)
            
            # ADHD adjustment factors
            adjustment_factor = 1.0
            
            # Task switching overhead (5 minutes per switch for ADHD)
            if len(subtasks) > 1:
                switching_time = (len(subtasks) - 1) * 5
                base_time += switching_time
            
            # Attention span considerations
            if profile and hasattr(profile, 'attention_span_average'):
                attention_span = profile.attention_span_average
                if attention_span < 20:  # Short attention span
                    adjustment_factor += 0.3  # 30% buffer
                elif attention_span > 45:  # Strong sustained attention
                    adjustment_factor -= 0.1  # 10% less time needed
            
            # Hyperfocus tendency adjustment
            if profile and hasattr(profile, 'hyperfocus_tendency'):
                if profile.hyperfocus_tendency > 0.7:
                    # High hyperfocus might actually reduce time on engaging tasks
                    adjustment_factor -= 0.1
                elif profile.hyperfocus_tendency < 0.3:
                    # Low hyperfocus might need more time
                    adjustment_factor += 0.2
            
            return int(base_time * adjustment_factor)
            
        except Exception as e:
            logger.warning("Time estimation failed", error=str(e))
            return sum(task.get("time_estimate", 15) for task in subtasks)
    
    async def _identify_executive_functions(self, 
                                          task_description: str,
                                          subtasks: List[Dict[str, Any]]) -> List[ExecutiveFunction]:
        """Identify required executive functions."""
        functions = []
        
        # All tasks require initiation
        functions.append(ExecutiveFunction.INITIATION)
        
        # Analyze task for other functions
        text = task_description.lower()
        
        if any(word in text for word in ['remember', 'keep track', 'hold']):
            functions.append(ExecutiveFunction.WORKING_MEMORY)
        
        if any(word in text for word in ['switch', 'change', 'different', 'various']):
            functions.append(ExecutiveFunction.COGNITIVE_FLEXIBILITY)
        
        if any(word in text for word in ['plan', 'schedule', 'future', 'deadline']):
            functions.append(ExecutiveFunction.PLANNING)
        
        if any(word in text for word in ['organize', 'sort', 'arrange', 'structure']):
            functions.append(ExecutiveFunction.ORGANIZATION)
        
        if any(word in text for word in ['time', 'when', 'deadline', 'schedule']):
            functions.append(ExecutiveFunction.TIME_MANAGEMENT)
        
        if any(word in text for word in ['frustrating', 'difficult', 'stressful']):
            functions.append(ExecutiveFunction.EMOTIONAL_REGULATION)
        
        # Multiple subtasks suggest need for cognitive flexibility
        if len(subtasks) > 3:
            if ExecutiveFunction.COGNITIVE_FLEXIBILITY not in functions:
                functions.append(ExecutiveFunction.COGNITIVE_FLEXIBILITY)
        
        return functions
    
    async def _predict_obstacles(self, 
                               subtasks: List[Dict[str, Any]],
                               exec_functions: List[ExecutiveFunction],
                               profile: Any) -> List[str]:
        """Predict potential obstacles based on ADHD patterns."""
        obstacles = []
        
        # Common ADHD obstacles
        if ExecutiveFunction.INITIATION in exec_functions:
            obstacles.append("Difficulty getting started")
        
        if ExecutiveFunction.WORKING_MEMORY in exec_functions:
            obstacles.append("Forgetting steps or requirements")
        
        if len(subtasks) > 5:
            obstacles.append("Feeling overwhelmed by number of steps")
        
        if any(task.get("time_estimate", 0) > 30 for task in subtasks):
            obstacles.append("Losing focus during longer subtasks")
        
        if ExecutiveFunction.TIME_MANAGEMENT in exec_functions:
            obstacles.append("Time blindness affecting scheduling")
        
        # Profile-specific obstacles
        if profile:
            if hasattr(profile, 'hyperfocus_tendency') and profile.hyperfocus_tendency < 0.3:
                obstacles.append("Difficulty maintaining sustained attention")
            
            if hasattr(profile, 'task_switching_pattern') and profile.task_switching_pattern == "high":
                obstacles.append("Getting distracted by other tasks")
        
        return obstacles
    
    async def _suggest_strategies(self, 
                                obstacles: List[str],
                                exec_functions: List[ExecutiveFunction],
                                profile: Any) -> List[str]:
        """Suggest ADHD-friendly success strategies."""
        strategies = []
        
        # General ADHD strategies
        strategies.append("Set up your environment before starting")
        strategies.append("Use a timer to create urgency and track progress")
        
        # Obstacle-specific strategies
        if "Difficulty getting started" in obstacles:
            strategies.append("Use the '2-minute rule' - just start for 2 minutes")
            strategies.append("Start with the easiest subtask to build momentum")
        
        if "Forgetting steps" in obstacles:
            strategies.append("Keep a visible checklist or notes")
            strategies.append("Set reminders for each major step")
        
        if "Feeling overwhelmed" in obstacles:
            strategies.append("Focus on only the current step, hide the rest")
            strategies.append("Take breaks between subtasks")
        
        if "Losing focus" in obstacles:
            strategies.append("Use body doubling (work alongside someone)")
            strategies.append("Change location or position periodically")
        
        # Executive function specific strategies
        if ExecutiveFunction.WORKING_MEMORY in exec_functions:
            strategies.append("Externalize information - write everything down")
        
        if ExecutiveFunction.TIME_MANAGEMENT in exec_functions:
            strategies.append("Use visual time indicators (clock, timer apps)")
        
        if ExecutiveFunction.EMOTIONAL_REGULATION in exec_functions:
            strategies.append("Plan self-care breaks and rewards")
        
        return strategies
    
    async def _calculate_energy_requirements(self, 
                                           subtasks: List[Dict[str, Any]],
                                           exec_functions: List[ExecutiveFunction]) -> Dict[str, float]:
        """Calculate different types of energy required."""
        energy_req = {"mental": 0.5, "emotional": 0.3, "physical": 0.2}
        
        # Adjust based on subtasks
        total_time = sum(task.get("time_estimate", 15) for task in subtasks)
        if total_time > 60:
            energy_req["mental"] += 0.2
        
        # Adjust based on executive functions
        if ExecutiveFunction.EMOTIONAL_REGULATION in exec_functions:
            energy_req["emotional"] += 0.3
        
        if ExecutiveFunction.WORKING_MEMORY in exec_functions:
            energy_req["mental"] += 0.2
        
        if ExecutiveFunction.COGNITIVE_FLEXIBILITY in exec_functions:
            energy_req["mental"] += 0.1
        
        # Normalize to 0-1 range
        for key in energy_req:
            energy_req[key] = min(energy_req[key], 1.0)
        
        return energy_req
    
    def _suggest_dopamine_reward(self, subtask: Dict[str, Any]) -> str:
        """Suggest appropriate dopamine reward for subtask completion."""
        time_estimate = subtask.get("time_estimate", 15)
        
        if time_estimate < 5:
            return "checkmark_celebration"
        elif time_estimate < 15:
            return "small_treat_or_break"
        elif time_estimate < 30:
            return "favorite_snack_or_music"
        else:
            return "meaningful_break_activity"
    
    def _assess_working_memory_load(self, subtask: Dict[str, Any]) -> str:
        """Assess working memory load for subtask."""
        title = subtask.get("title", "").lower()
        
        if any(word in title for word in ['remember', 'keep track', 'compare', 'analyze']):
            return "high"
        elif any(word in title for word in ['organize', 'plan', 'coordinate']):
            return "medium"
        else:
            return "low"


class ContextSwitchingAssistant:
    """
    Assistant for managing context switches and task transitions.
    
    Helps ADHD users transition between different tasks, contexts,
    and mental states with minimal cognitive friction.
    """
    
    def __init__(self):
        self.transition_patterns: Dict[str, Dict[str, Any]] = {}
        self.context_stack: Dict[str, List[str]] = defaultdict(list)
        
    async def plan_context_switch(self, 
                                user_id: str,
                                from_context: str,
                                to_context: str,
                                urgency: str = "normal") -> ContextSwitchPlan:
        """Plan an effective context switch."""
        try:
            # Analyze contexts
            from_analysis = await self._analyze_context(from_context)
            to_analysis = await self._analyze_context(to_context)
            
            # Generate transition steps
            transition_steps = await self._generate_transition_steps(
                from_analysis, to_analysis, urgency
            )
            
            # Estimate switching time
            switch_time = await self._estimate_switch_time(
                from_analysis, to_analysis, urgency
            )
            
            # Identify preparation needs
            mental_prep = from_analysis["cognitive_load"] != to_analysis["cognitive_load"]
            physical_prep = from_analysis["environment"] != to_analysis["environment"]
            
            # Predict friction points
            friction_points = await self._predict_friction_points(
                from_analysis, to_analysis
            )
            
            # Generate success strategies
            strategies = await self._generate_switch_strategies(
                from_analysis, to_analysis, friction_points
            )
            
            plan = ContextSwitchPlan(
                from_context=from_context,
                to_context=to_context,
                transition_steps=transition_steps,
                estimated_switch_time=switch_time,
                mental_prep_needed=mental_prep,
                physical_prep_needed=physical_prep,
                potential_friction_points=friction_points,
                success_strategies=strategies
            )
            
            # Update context stack
            self.context_stack[user_id].append(to_context)
            if len(self.context_stack[user_id]) > 5:
                self.context_stack[user_id].pop(0)
            
            logger.info("Context switch plan created", 
                       user_id=user_id,
                       from_context=from_context[:20],
                       to_context=to_context[:20],
                       estimated_time=switch_time)
            
            return plan
            
        except Exception as e:
            logger.error("Context switch planning failed", 
                        user_id=user_id, error=str(e))
            
            # Return minimal plan
            return ContextSwitchPlan(
                from_context=from_context,
                to_context=to_context,
                transition_steps=["Take a deep breath", f"Begin {to_context}"],
                estimated_switch_time=5,
                mental_prep_needed=True,
                physical_prep_needed=False,
                potential_friction_points=["Mental adjustment needed"],
                success_strategies=["Take a moment to refocus"]
            )
    
    async def _analyze_context(self, context_description: str) -> Dict[str, Any]:
        """Analyze a context to understand its characteristics."""
        analysis = {
            "type": "unknown",
            "cognitive_load": 0.5,
            "environment": "neutral",
            "tools_required": [],
            "mental_state": "focused"
        }
        
        text = context_description.lower()
        
        # Determine context type
        if any(word in text for word in ['email', 'message', 'communication']):
            analysis["type"] = "communication"
            analysis["cognitive_load"] = 0.6
        elif any(word in text for word in ['write', 'document', 'create']):
            analysis["type"] = "creative"
            analysis["cognitive_load"] = 0.7
        elif any(word in text for word in ['plan', 'organize', 'schedule']):
            analysis["type"] = "planning"
            analysis["cognitive_load"] = 0.8
        elif any(word in text for word in ['meet', 'call', 'discussion']):
            analysis["type"] = "social"
            analysis["cognitive_load"] = 0.7
            analysis["mental_state"] = "interactive"
        
        # Determine environment
        if any(word in text for word in ['computer', 'screen', 'digital']):
            analysis["environment"] = "digital"
        elif any(word in text for word in ['paper', 'physical', 'hands-on']):
            analysis["environment"] = "physical"
        
        return analysis
    
    async def _generate_transition_steps(self, 
                                       from_analysis: Dict[str, Any],
                                       to_analysis: Dict[str, Any],
                                       urgency: str) -> List[str]:
        """Generate specific transition steps."""
        steps = []
        
        if urgency == "urgent":
            steps.append("Quick mental reset (3 deep breaths)")
        else:
            steps.append("Complete current thought or save current work")
            steps.append("Take a moment to mentally close the previous task")
        
        # Environment changes
        if from_analysis["environment"] != to_analysis["environment"]:
            if to_analysis["environment"] == "digital":
                steps.append("Open necessary applications")
            elif to_analysis["environment"] == "physical":
                steps.append("Gather physical materials")
        
        # Cognitive load adjustments
        from_load = from_analysis["cognitive_load"]
        to_load = to_analysis["cognitive_load"]
        
        if to_load > from_load + 0.2:
            steps.append("Take a few minutes to mentally prepare for increased focus")
        elif from_load > to_load + 0.2:
            steps.append("Allow your mind to decompress from the previous task")
        
        # Context-specific preparations
        if to_analysis["type"] == "creative":
            steps.append("Clear mental space for creative thinking")
        elif to_analysis["type"] == "social":
            steps.append("Shift to interactive mindset")
        elif to_analysis["type"] == "planning":
            steps.append("Gather overview perspective")
        
        steps.append(f"Begin {to_analysis['type']} task with full attention")
        
        return steps
    
    async def _estimate_switch_time(self, 
                                  from_analysis: Dict[str, Any],
                                  to_analysis: Dict[str, Any],
                                  urgency: str) -> int:
        """Estimate time needed for context switch."""
        base_time = 3 if urgency == "urgent" else 7
        
        # Add time for cognitive load differences
        load_diff = abs(from_analysis["cognitive_load"] - to_analysis["cognitive_load"])
        base_time += int(load_diff * 10)
        
        # Add time for environment changes
        if from_analysis["environment"] != to_analysis["environment"]:
            base_time += 5
        
        # Add time for mental state changes
        if from_analysis["mental_state"] != to_analysis["mental_state"]:
            base_time += 3
        
        return min(base_time, 20)  # Cap at 20 minutes
    
    async def _predict_friction_points(self, 
                                     from_analysis: Dict[str, Any],
                                     to_analysis: Dict[str, Any]) -> List[str]:
        """Predict potential difficulties in switching."""
        friction_points = []
        
        # Large cognitive load increases
        if to_analysis["cognitive_load"] > from_analysis["cognitive_load"] + 0.3:
            friction_points.append("Mental resistance to increased complexity")
        
        # Environment changes
        if from_analysis["environment"] != to_analysis["environment"]:
            friction_points.append("Physical setup and tool switching")
        
        # Creative to analytical switches
        if (from_analysis["type"] == "creative" and 
            to_analysis["type"] in ["planning", "analytical"]):
            friction_points.append("Right-brain to left-brain transition")
        
        # Solo to social switches
        if (from_analysis["mental_state"] == "focused" and 
            to_analysis["mental_state"] == "interactive"):
            friction_points.append("Shifting from internal to external focus")
        
        return friction_points
    
    async def _generate_switch_strategies(self, 
                                        from_analysis: Dict[str, Any],
                                        to_analysis: Dict[str, Any],
                                        friction_points: List[str]) -> List[str]:
        """Generate strategies for smooth switching."""
        strategies = []
        
        # General strategies
        strategies.append("Use a consistent switching ritual")
        strategies.append("Set a clear intention for the new task")
        
        # Friction-specific strategies
        if "Mental resistance to increased complexity" in friction_points:
            strategies.append("Start with the simplest part of the new task")
            strategies.append("Use a warm-up activity to gradually increase focus")
        
        if "Physical setup and tool switching" in friction_points:
            strategies.append("Prepare the new environment before switching")
            strategies.append("Use a checklist for setup requirements")
        
        if "Right-brain to left-brain transition" in friction_points:
            strategies.append("Do a brief analytical warm-up exercise")
            strategies.append("Review structured information before starting")
        
        if "Shifting from internal to external focus" in friction_points:
            strategies.append("Practice a few social interactions first")
            strategies.append("Review talking points or social context")
        
        return strategies


class WorkingMemorySupport:
    """
    External working memory support system for ADHD users.
    
    Provides cognitive offloading tools to reduce working memory burden
    and help users track information across tasks and sessions.
    """
    
    def __init__(self):
        self.memory_aids: Dict[str, List[WorkingMemoryAid]] = defaultdict(list)
        self.retrieval_success: Dict[str, float] = defaultdict(lambda: 0.7)
        
    async def store_information(self, 
                              user_id: str,
                              info_type: str,
                              content: Any,
                              priority: int = 3,
                              expires_hours: Optional[int] = None,
                              retrieval_cues: List[str] = None,
                              associated_task: str = None) -> str:
        """Store information in external working memory."""
        try:
            expires_at = None
            if expires_hours:
                expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            
            aid = WorkingMemoryAid(
                information_type=info_type,
                content=content,
                priority=priority,
                expires_at=expires_at,
                retrieval_cues=retrieval_cues or [],
                associated_task=associated_task
            )
            
            self.memory_aids[user_id].append(aid)
            
            # Clean up expired items
            await self._cleanup_expired(user_id)
            
            aid_id = f"{user_id}_{len(self.memory_aids[user_id])}"
            
            logger.info("Information stored in working memory", 
                       user_id=user_id,
                       info_type=info_type,
                       priority=priority)
            
            return aid_id
            
        except Exception as e:
            logger.error("Working memory storage failed", 
                        user_id=user_id, error=str(e))
            return ""
    
    async def retrieve_information(self, 
                                 user_id: str,
                                 query: str = None,
                                 info_type: str = None,
                                 associated_task: str = None) -> List[WorkingMemoryAid]:
        """Retrieve relevant information from working memory."""
        try:
            await self._cleanup_expired(user_id)
            
            all_aids = self.memory_aids.get(user_id, [])
            relevant_aids = []
            
            for aid in all_aids:
                relevance_score = 0.0
                
                # Type match
                if info_type and aid.information_type == info_type:
                    relevance_score += 0.4
                
                # Task match
                if associated_task and aid.associated_task == associated_task:
                    relevance_score += 0.4
                
                # Query match
                if query:
                    query_lower = query.lower()
                    content_str = str(aid.content).lower()
                    
                    if query_lower in content_str:
                        relevance_score += 0.3
                    
                    # Check retrieval cues
                    for cue in aid.retrieval_cues:
                        if cue.lower() in query_lower:
                            relevance_score += 0.2
                            break
                
                # Priority boost
                relevance_score += aid.priority * 0.1
                
                if relevance_score > 0.3:  # Relevance threshold
                    relevant_aids.append((relevance_score, aid))
            
            # Sort by relevance and return
            relevant_aids.sort(key=lambda x: x[0], reverse=True)
            return [aid for score, aid in relevant_aids]
            
        except Exception as e:
            logger.error("Working memory retrieval failed", 
                        user_id=user_id, error=str(e))
            return []
    
    async def _cleanup_expired(self, user_id: str) -> None:
        """Remove expired working memory items."""
        try:
            current_time = datetime.utcnow()
            self.memory_aids[user_id] = [
                aid for aid in self.memory_aids[user_id]
                if aid.expires_at is None or aid.expires_at > current_time
            ]
        except Exception as e:
            logger.warning("Working memory cleanup failed", error=str(e))


class ProcrastinationIntervenor:
    """
    Graduated procrastination intervention system.
    
    Provides escalating support to help users overcome procrastination
    blocks using ADHD-specific strategies.
    """
    
    def __init__(self):
        self.intervention_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.trigger_patterns: Dict[str, Dict[ProcrastinationTrigger, int]] = defaultdict(lambda: defaultdict(int))
        
    async def assess_procrastination_risk(self, 
                                        user_id: str,
                                        task_description: str,
                                        context: Dict[str, Any]) -> Tuple[float, List[ProcrastinationTrigger]]:
        """Assess procrastination risk and identify triggers."""
        try:
            risk_score = 0.0
            triggers = []
            
            # Analyze task characteristics
            if len(task_description.split()) > 20:  # Long description = complexity
                risk_score += 0.2
                triggers.append(ProcrastinationTrigger.OVERWHELM)
            
            if any(word in task_description.lower() for word in 
                  ['perfect', 'important', 'critical', 'must be']):
                risk_score += 0.3
                triggers.append(ProcrastinationTrigger.PERFECTIONISM)
            
            if not any(word in task_description.lower() for word in 
                      ['fun', 'interesting', 'enjoy', 'like']):
                risk_score += 0.2
                triggers.append(ProcrastinationTrigger.BOREDOM)
            
            # Context factors
            if context.get('unclear_requirements', False):
                risk_score += 0.3
                triggers.append(ProcrastinationTrigger.UNCLEAR_REQUIREMENTS)
            
            if context.get('energy_mismatch', False):
                risk_score += 0.2
                triggers.append(ProcrastinationTrigger.ENERGY_MISMATCH)
            
            if context.get('requires_context_switch', False):
                risk_score += 0.2
                triggers.append(ProcrastinationTrigger.CONTEXT_SWITCHING)
            
            # Historical patterns
            user_patterns = self.trigger_patterns[user_id]
            if user_patterns:
                common_triggers = sorted(user_patterns.items(), 
                                       key=lambda x: x[1], reverse=True)[:3]
                for trigger, count in common_triggers:
                    if trigger not in triggers:
                        risk_score += 0.1
                        triggers.append(trigger)
            
            risk_score = min(risk_score, 1.0)
            
            return risk_score, triggers
            
        except Exception as e:
            logger.error("Procrastination risk assessment failed", 
                        user_id=user_id, error=str(e))
            return 0.5, [ProcrastinationTrigger.UNCLEAR_REQUIREMENTS]
    
    async def provide_intervention(self, 
                                 user_id: str,
                                 risk_score: float,
                                 triggers: List[ProcrastinationTrigger],
                                 urgency_level: int = 1) -> Dict[str, Any]:
        """Provide appropriate intervention based on risk and triggers."""
        try:
            intervention = {
                "level": self._determine_intervention_level(risk_score, urgency_level),
                "strategies": [],
                "immediate_actions": [],
                "mindset_shifts": [],
                "environmental_changes": []
            }
            
            # Trigger-specific interventions
            for trigger in triggers:
                trigger_interventions = await self._get_trigger_interventions(trigger)
                for key in intervention:
                    if key in trigger_interventions:
                        intervention[key].extend(trigger_interventions[key])
            
            # Level-specific additions
            level = intervention["level"]
            
            if level >= 2:  # Moderate intervention
                intervention["immediate_actions"].extend([
                    "Set a 5-minute timer and just start",
                    "Find an accountability partner",
                    "Change your physical environment"
                ])
            
            if level >= 3:  # Intensive intervention
                intervention["immediate_actions"].extend([
                    "Use body doubling - work with someone",
                    "Break task into 2-minute micro-steps",
                    "Implement reward system for each step"
                ])
            
            if level >= 4:  # Crisis intervention
                intervention["immediate_actions"].extend([
                    "Reach out for help immediately",
                    "Consider task modification or delegation",
                    "Address underlying emotional blocks"
                ])
            
            # Remove duplicates
            for key in intervention:
                if isinstance(intervention[key], list):
                    intervention[key] = list(set(intervention[key]))
            
            # Track intervention
            self.intervention_history[user_id].append({
                "timestamp": datetime.utcnow(),
                "risk_score": risk_score,
                "triggers": [t.value for t in triggers],
                "intervention_level": level
            })
            
            logger.info("Procrastination intervention provided", 
                       user_id=user_id,
                       risk_score=risk_score,
                       level=level,
                       triggers=len(triggers))
            
            return intervention
            
        except Exception as e:
            logger.error("Procrastination intervention failed", 
                        user_id=user_id, error=str(e))
            return {"level": 1, "strategies": ["Just start with any small step"]}
    
    def _determine_intervention_level(self, risk_score: float, urgency: int) -> int:
        """Determine intervention intensity level."""
        base_level = 1
        
        if risk_score > 0.7:
            base_level = 3
        elif risk_score > 0.5:
            base_level = 2
        
        # Urgency modifier
        if urgency > 3:
            base_level += 1
        
        return min(base_level, 4)
    
    async def _get_trigger_interventions(self, trigger: ProcrastinationTrigger) -> Dict[str, List[str]]:
        """Get interventions specific to procrastination trigger."""
        interventions = {
            ProcrastinationTrigger.OVERWHELM: {
                "strategies": ["Break into smallest possible steps", "Focus only on next step"],
                "immediate_actions": ["Write down just the first step"],
                "mindset_shifts": ["Progress over perfection"],
                "environmental_changes": ["Clear workspace of distractions"]
            },
            
            ProcrastinationTrigger.PERFECTIONISM: {
                "strategies": ["Set 'good enough' standards", "Time-box the work"],
                "immediate_actions": ["Commit to a rough first draft"],
                "mindset_shifts": ["Done is better than perfect", "You can improve it later"],
                "environmental_changes": ["Remove editing tools initially"]
            },
            
            ProcrastinationTrigger.BOREDOM: {
                "strategies": ["Gamify the task", "Add music or novelty"],
                "immediate_actions": ["Find one interesting aspect", "Set up rewards"],
                "mindset_shifts": ["Focus on learning or growth opportunity"],
                "environmental_changes": ["Change location or setup"]
            },
            
            ProcrastinationTrigger.UNCLEAR_REQUIREMENTS: {
                "strategies": ["Seek clarification", "Start with what you know"],
                "immediate_actions": ["List what you DO know", "Identify information gaps"],
                "mindset_shifts": ["It's okay to ask questions"],
                "environmental_changes": ["Gather available resources"]
            },
            
            ProcrastinationTrigger.ENERGY_MISMATCH: {
                "strategies": ["Wait for better energy match", "Modify task for current energy"],
                "immediate_actions": ["Do an energy assessment", "Adjust task complexity"],
                "mindset_shifts": ["Honor your natural rhythms"],
                "environmental_changes": ["Optimize lighting and temperature"]
            },
            
            ProcrastinationTrigger.CONTEXT_SWITCHING: {
                "strategies": ["Use transition rituals", "Schedule switching time"],
                "immediate_actions": ["Complete transition protocol"],
                "mindset_shifts": ["Switching is part of the process"],
                "environmental_changes": ["Set up new context in advance"]
            },
            
            ProcrastinationTrigger.FEAR_FAILURE: {
                "strategies": ["Reframe failure as learning", "Lower stakes"],
                "immediate_actions": ["Remind yourself of past successes"],
                "mindset_shifts": ["Focus on effort over outcome"],
                "environmental_changes": ["Create safe practice space"]
            },
            
            ProcrastinationTrigger.LACK_STRUCTURE: {
                "strategies": ["Create artificial structure", "Use templates"],
                "immediate_actions": ["Set up clear process", "Define success criteria"],
                "mindset_shifts": ["Structure enables creativity"],
                "environmental_changes": ["Organize tools and materials"]
            }
        }
        
        return interventions.get(trigger, {
            "strategies": ["Take it one step at a time"],
            "immediate_actions": ["Just start"],
            "mindset_shifts": ["You can do this"],
            "environmental_changes": ["Set up for success"]
        })


# Global instances
task_breakdown_engine = TaskBreakdownEngine()
context_switching_assistant = ContextSwitchingAssistant()
working_memory_support = WorkingMemorySupport()
procrastination_intervenor = ProcrastinationIntervenor()