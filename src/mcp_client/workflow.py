"""
MCP Workflow Engine

Executes complex workflows combining multiple tools for ADHD-optimized productivity.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
import uuid

import structlog
from pydantic import BaseModel

from .models import (
    Integration, WorkflowStep, ToolResult, ToolError,
    ContextFrame, ToolStatus
)

logger = structlog.get_logger()


class WorkflowExecution(BaseModel):
    """Represents a workflow execution instance."""
    execution_id: str
    integration_id: str
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "running"  # running, completed, failed, cancelled
    
    # Execution state
    current_step: Optional[str] = None
    completed_steps: List[str] = []
    failed_steps: List[str] = []
    step_results: Dict[str, ToolResult] = {}
    
    # ADHD metrics
    total_cognitive_load: float = 0.0
    peak_cognitive_load: float = 0.0
    interruptions_count: int = 0
    focus_breaks_taken: int = 0
    
    # Metadata
    parameters: Dict[str, Any] = {}
    error_message: Optional[str] = None


class WorkflowEngine:
    """Executes workflows combining multiple MCP tools."""
    
    def __init__(self, mcp_client):
        """Initialize workflow engine."""
        self.mcp_client = mcp_client
        self.integrations: Dict[str, Integration] = {}
        self.active_executions: Dict[str, WorkflowExecution] = {}
        
        # ADHD-specific settings
        self.max_parallel_steps = 3  # Limit cognitive load
        self.cognitive_load_threshold = 0.8
        self.focus_break_interval = 1800  # 30 minutes
        
        # Load predefined integrations
        asyncio.create_task(self._load_integrations())
    
    async def register_integration(self, integration: Integration) -> bool:
        """Register a new workflow integration."""
        try:
            # Validate integration
            if not await self._validate_integration(integration):
                return False
            
            self.integrations[integration.integration_id] = integration
            
            logger.info("Integration registered", 
                       integration_id=integration.integration_id,
                       name=integration.name)
            
            return True
            
        except Exception as e:
            logger.error("Integration registration failed", 
                        integration_id=integration.integration_id,
                        error=str(e))
            return False
    
    async def execute_workflow(
        self,
        integration_id: str,
        parameters: Dict[str, Any] = None,
        context: Optional[ContextFrame] = None
    ) -> Dict[str, Any]:
        """Execute a workflow integration."""
        execution_id = str(uuid.uuid4())
        
        try:
            # Get integration
            integration = self.integrations.get(integration_id)
            if not integration:
                raise ValueError(f"Integration {integration_id} not found")
            
            # Create execution instance
            execution = WorkflowExecution(
                execution_id=execution_id,
                integration_id=integration_id,
                user_id=self.mcp_client.user_id,
                started_at=datetime.utcnow(),
                parameters=parameters or {}
            )
            
            self.active_executions[execution_id] = execution
            
            logger.info("Workflow execution started",
                       execution_id=execution_id,
                       integration_id=integration_id,
                       user_id=self.mcp_client.user_id)
            
            # Use current context if none provided
            if context is None:
                context = self.mcp_client.get_context()
            
            # Execute workflow steps
            result = await self._execute_workflow_steps(
                integration, execution, context
            )
            
            # Mark as completed
            execution.completed_at = datetime.utcnow()
            execution.status = "completed"
            
            # Calculate final metrics
            execution_time = (execution.completed_at - execution.started_at).total_seconds()
            
            result.update({
                'execution_id': execution_id,
                'execution_time_seconds': execution_time,
                'cognitive_load_peak': execution.peak_cognitive_load,
                'steps_completed': len(execution.completed_steps),
                'steps_failed': len(execution.failed_steps),
                'focus_breaks': execution.focus_breaks_taken,
                'adhd_optimized': integration.adhd_optimized
            })
            
            logger.info("Workflow execution completed",
                       execution_id=execution_id,
                       execution_time=execution_time,
                       success=result.get('success', False))
            
            return result
            
        except Exception as e:
            # Mark execution as failed
            if execution_id in self.active_executions:
                execution = self.active_executions[execution_id]
                execution.status = "failed"
                execution.error_message = str(e)
                execution.completed_at = datetime.utcnow()
            
            logger.error("Workflow execution failed",
                        execution_id=execution_id,
                        integration_id=integration_id,
                        error=str(e))
            
            return {
                'success': False,
                'error': str(e),
                'execution_id': execution_id
            }
        finally:
            # Clean up execution
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel a running workflow."""
        try:
            execution = self.active_executions.get(execution_id)
            if not execution:
                return False
            
            execution.status = "cancelled"
            execution.completed_at = datetime.utcnow()
            
            logger.info("Workflow cancelled", execution_id=execution_id)
            return True
            
        except Exception as e:
            logger.error("Workflow cancellation failed", 
                        execution_id=execution_id, 
                        error=str(e))
            return False
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow execution."""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return None
        
        return {
            'execution_id': execution_id,
            'integration_id': execution.integration_id,
            'status': execution.status,
            'current_step': execution.current_step,
            'progress': len(execution.completed_steps) / len(self.integrations[execution.integration_id].workflow_steps),
            'cognitive_load': execution.total_cognitive_load,
            'started_at': execution.started_at.isoformat(),
            'error': execution.error_message
        }
    
    def list_integrations(self) -> List[Dict[str, Any]]:
        """List available integrations."""
        return [
            {
                'integration_id': integration.integration_id,
                'name': integration.name,
                'description': integration.description,
                'tools_required': integration.tools,
                'adhd_optimized': integration.adhd_optimized,
                'focus_mode_compatible': integration.focus_mode_compatible,
                'max_cognitive_load': integration.max_cognitive_load,
                'enabled': integration.enabled
            }
            for integration in self.integrations.values()
            if integration.enabled
        ]
    
    # Private Methods
    
    async def _execute_workflow_steps(
        self,
        integration: Integration,
        execution: WorkflowExecution,
        context: Optional[ContextFrame]
    ) -> Dict[str, Any]:
        """Execute all steps in a workflow."""
        steps = integration.workflow_steps
        results = {}
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(steps)
        
        # Execute steps respecting dependencies and ADHD constraints
        completed_steps = set()
        running_steps = set()
        
        while len(completed_steps) < len(steps):
            # Find steps ready to execute
            ready_steps = []
            
            for step in steps:
                if (step.step_id not in completed_steps and 
                    step.step_id not in running_steps and
                    all(dep in completed_steps for dep in step.depends_on)):
                    ready_steps.append(step)
            
            if not ready_steps:
                # Check if we're stuck waiting for running steps
                if running_steps:
                    await asyncio.sleep(0.1)
                    continue
                else:
                    break  # No more steps can execute
            
            # Apply ADHD constraints
            ready_steps = self._apply_adhd_constraints(
                ready_steps, execution, context
            )
            
            # Execute steps (parallel where possible)
            tasks = []
            for step in ready_steps[:self.max_parallel_steps]:
                if step.parallel or len(ready_steps) == 1:
                    task = self._execute_step(step, execution, context)
                    tasks.append((step.step_id, task))
                    running_steps.add(step.step_id)
            
            # Wait for at least one step to complete
            if tasks:
                done, pending = await asyncio.wait(
                    [task for _, task in tasks],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Process completed steps
                for step_id, task in tasks:
                    if task in done:
                        try:
                            step_result = await task
                            results[step_id] = step_result
                            execution.step_results[step_id] = step_result
                            
                            if step_result.success:
                                completed_steps.add(step_id)
                                execution.completed_steps.append(step_id)
                            else:
                                execution.failed_steps.append(step_id)
                            
                            running_steps.discard(step_id)
                            
                        except Exception as e:
                            logger.error("Step execution error", 
                                        step_id=step_id, 
                                        error=str(e))
                            execution.failed_steps.append(step_id)
                            running_steps.discard(step_id)
            
            # Check for focus break needs
            if context:
                await self._check_focus_break_needs(execution, context)
        
        # Determine overall success
        success = len(execution.failed_steps) == 0
        
        return {
            'success': success,
            'results': results,
            'completed_steps': len(completed_steps),
            'failed_steps': len(execution.failed_steps)
        }
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        context: Optional[ContextFrame]
    ) -> ToolResult:
        """Execute a single workflow step."""
        try:
            execution.current_step = step.step_id
            
            # Check if step condition is met
            if step.condition and not self._evaluate_condition(step.condition, execution):
                return ToolResult(
                    success=True,
                    message="Step skipped due to condition"
                )
            
            # Check cognitive load budget
            if (context and step.cognitive_load_budget and 
                context.cognitive_load > step.cognitive_load_budget):
                
                # Suggest focus break
                execution.focus_breaks_taken += 1
                await asyncio.sleep(2)  # Brief pause
            
            # Prepare parameters (merge step params with execution params)
            parameters = {**execution.parameters, **step.parameters}
            
            # Resolve parameter references
            parameters = self._resolve_parameter_references(parameters, execution)
            
            # Execute the tool operation
            result = await self.mcp_client.invoke_tool(
                tool_id=step.tool_id,
                operation=step.operation,
                parameters=parameters,
                context=context
            )
            
            # Update cognitive load tracking
            if result.cognitive_load_impact:
                execution.total_cognitive_load += result.cognitive_load_impact
                execution.peak_cognitive_load = max(
                    execution.peak_cognitive_load,
                    result.cognitive_load_impact
                )
            
            # Handle interruptions for ADHD
            if (not step.interruption_safe and 
                result.focus_disruption_level > 0.5):
                execution.interruptions_count += 1
            
            logger.debug("Workflow step completed",
                        step_id=step.step_id,
                        tool_id=step.tool_id,
                        operation=step.operation,
                        success=result.success)
            
            return result
            
        except Exception as e:
            logger.error("Workflow step execution failed",
                        step_id=step.step_id,
                        error=str(e))
            
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def _build_dependency_graph(self, steps: List[WorkflowStep]) -> Dict[str, Set[str]]:
        """Build a dependency graph for workflow steps."""
        graph = {}
        
        for step in steps:
            graph[step.step_id] = set(step.depends_on)
        
        return graph
    
    def _apply_adhd_constraints(
        self,
        steps: List[WorkflowStep],
        execution: WorkflowExecution,
        context: Optional[ContextFrame]
    ) -> List[WorkflowStep]:
        """Apply ADHD-specific constraints to step selection."""
        filtered_steps = []
        
        for step in steps:
            # Check cognitive load
            if context:
                projected_load = context.cognitive_load
                if step.cognitive_load_budget:
                    projected_load += step.cognitive_load_budget
                
                if projected_load > self.cognitive_load_threshold:
                    continue  # Skip high cognitive load steps
            
            # Check focus requirements
            if step.focus_required and context and context.focus_level < 0.6:
                continue  # Skip focus-requiring steps when focus is low
            
            filtered_steps.append(step)
        
        return filtered_steps
    
    def _evaluate_condition(self, condition: str, execution: WorkflowExecution) -> bool:
        """Evaluate a step condition."""
        # Simple condition evaluation - would be more sophisticated in practice
        # For now, just check if previous steps succeeded
        if "previous_step_success" in condition:
            return len(execution.failed_steps) == 0
        
        return True
    
    def _resolve_parameter_references(
        self,
        parameters: Dict[str, Any],
        execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Resolve parameter references from previous step results."""
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("${"):
                # Extract reference (e.g., "${step1.result.data}")
                ref = value[2:-1]  # Remove ${ and }
                
                # Simple reference resolution
                if "." in ref:
                    parts = ref.split(".")
                    step_id = parts[0]
                    
                    if step_id in execution.step_results:
                        result = execution.step_results[step_id]
                        resolved_value = result.data
                        
                        # Navigate nested properties
                        for part in parts[1:]:
                            if isinstance(resolved_value, dict) and part in resolved_value:
                                resolved_value = resolved_value[part]
                            else:
                                resolved_value = None
                                break
                        
                        resolved[key] = resolved_value
                    else:
                        resolved[key] = None
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        
        return resolved
    
    async def _check_focus_break_needs(
        self,
        execution: WorkflowExecution,
        context: ContextFrame
    ):
        """Check if user needs a focus break."""
        elapsed_time = (datetime.utcnow() - execution.started_at).total_seconds()
        
        # Suggest break every 30 minutes for ADHD users
        if (elapsed_time > self.focus_break_interval * (execution.focus_breaks_taken + 1) and
            context.cognitive_load > 0.7):
            
            execution.focus_breaks_taken += 1
            
            # In a real implementation, this would send a nudge to the user
            logger.info("Focus break recommended",
                       execution_id=execution.execution_id,
                       elapsed_time=elapsed_time,
                       cognitive_load=context.cognitive_load)
    
    async def _validate_integration(self, integration: Integration) -> bool:
        """Validate an integration configuration."""
        try:
            # Check required tools exist
            for tool_id in integration.tools:
                tool = await self.mcp_client.get_tool(tool_id)
                if not tool:
                    logger.error("Integration requires non-existent tool", 
                               integration_id=integration.integration_id,
                               tool_id=tool_id)
                    return False
            
            # Validate workflow steps
            for step in integration.workflow_steps:
                if step.tool_id not in integration.tools:
                    logger.error("Workflow step uses tool not in integration", 
                               integration_id=integration.integration_id,
                               step_id=step.step_id,
                               tool_id=step.tool_id)
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Integration validation failed", 
                        integration_id=integration.integration_id,
                        error=str(e))
            return False
    
    async def _load_integrations(self):
        """Load predefined integrations."""
        # This would load integrations from configuration files
        # For now, we'll start with an empty set
        logger.info("Workflow integrations loaded", count=len(self.integrations))