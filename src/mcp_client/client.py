"""
MCP Client - Core Implementation

Main Model Context Protocol client for universal tool integration.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Callable
import uuid

import aiohttp
import structlog
from pydantic import ValidationError

from .models import (
    Tool, ToolConfig, ToolResult, ToolError, ToolStatus,
    Resource, ResourceConfig, ResourceResult, ResourceType,
    ContextFrame, Integration, WorkflowStep,
    ToolCapability, AuthType
)
from .registry import ToolRegistry
from .auth import AuthManager
from .workflow import WorkflowEngine

logger = structlog.get_logger()


class MCPClient:
    """
    Model Context Protocol client for universal tool integration.
    
    Provides a standardized way to integrate with external tools and services
    while maintaining ADHD-specific context and optimizations.
    """
    
    def __init__(self, user_id: str):
        """Initialize MCP client for a specific user."""
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        
        # Core components
        self.tool_registry = ToolRegistry()
        self.auth_manager = AuthManager()
        self.workflow_engine = WorkflowEngine(self)
        
        # Client state
        self.active_tools: Dict[str, Tool] = {}
        self.cached_resources: Dict[str, Any] = {}
        self.current_context: Optional[ContextFrame] = None
        
        # HTTP session for API calls
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            'tool_connected': [],
            'tool_disconnected': [],
            'tool_error': [],
            'workflow_started': [],
            'workflow_completed': [],
            'context_updated': []
        }
        
        logger.info("MCP Client initialized", user_id=user_id, session_id=self.session_id)
    
    async def initialize(self) -> bool:
        """Initialize the MCP client and establish connections."""
        try:
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=30)
            self.http_session = aiohttp.ClientSession(timeout=timeout)
            
            # Initialize auth manager
            await self.auth_manager.initialize()
            
            # Load registered tools
            await self._load_registered_tools()
            
            logger.info("MCP Client initialized successfully", user_id=self.user_id)
            return True
            
        except Exception as e:
            logger.error("MCP Client initialization failed", user_id=self.user_id, error=str(e))
            return False
    
    async def close(self):
        """Clean up client resources."""
        try:
            # Disconnect all active tools
            for tool_id in list(self.active_tools.keys()):
                await self.disconnect_tool(tool_id)
            
            # Close HTTP session
            if self.http_session:
                await self.http_session.close()
            
            logger.info("MCP Client closed", user_id=self.user_id)
            
        except Exception as e:
            logger.warning("Error closing MCP Client", user_id=self.user_id, error=str(e))
    
    # Tool Management
    
    async def register_tool(self, tool_config: ToolConfig) -> bool:
        """Register a new tool with the client."""
        try:
            # Validate configuration
            if not tool_config.tool_id or not tool_config.name:
                raise ValueError("Tool ID and name are required")
            
            # Check if already registered
            if tool_config.tool_id in self.tool_registry.tools:
                logger.warning("Tool already registered", tool_id=tool_config.tool_id)
                return False
            
            # Create tool instance
            tool = Tool(
                config=tool_config,
                status=ToolStatus.REGISTERED
            )
            
            # Register in registry
            await self.tool_registry.register_tool(tool)
            
            logger.info("Tool registered successfully", 
                       tool_id=tool_config.tool_id, 
                       name=tool_config.name,
                       tool_type=tool_config.tool_type)
            
            return True
            
        except Exception as e:
            logger.error("Tool registration failed", 
                        tool_id=tool_config.tool_id,
                        error=str(e))
            return False
    
    async def connect_tool(self, tool_id: str) -> bool:
        """Connect to a registered tool."""
        try:
            tool = await self.tool_registry.get_tool(tool_id)
            if not tool:
                raise ValueError(f"Tool {tool_id} not found")
            
            # Skip if already connected
            if tool.status == ToolStatus.CONNECTED:
                return True
            
            # Authenticate if needed
            auth_success = await self.auth_manager.authenticate_tool(tool.config)
            if not auth_success:
                tool.status = ToolStatus.ERROR
                tool.last_error = ToolError(
                    error_type="authentication_failed",
                    message="Failed to authenticate with tool",
                    retryable=True
                )
                await self.tool_registry.update_tool(tool)
                return False
            
            # Test connection
            connection_result = await self._test_tool_connection(tool)
            if connection_result:
                tool.status = ToolStatus.CONNECTED
                tool.connected_at = datetime.utcnow()
                self.active_tools[tool_id] = tool
                
                # Fire event
                await self._fire_event('tool_connected', {'tool_id': tool_id, 'tool': tool})
                
                logger.info("Tool connected successfully", tool_id=tool_id)
                return True
            else:
                tool.status = ToolStatus.ERROR
                return False
            
        except Exception as e:
            logger.error("Tool connection failed", tool_id=tool_id, error=str(e))
            return False
    
    async def disconnect_tool(self, tool_id: str) -> bool:
        """Disconnect from a tool."""
        try:
            if tool_id in self.active_tools:
                tool = self.active_tools[tool_id]
                tool.status = ToolStatus.DISCONNECTED
                
                # Remove from active tools
                del self.active_tools[tool_id]
                
                # Update registry
                await self.tool_registry.update_tool(tool)
                
                # Fire event
                await self._fire_event('tool_disconnected', {'tool_id': tool_id})
                
                logger.info("Tool disconnected", tool_id=tool_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Tool disconnection failed", tool_id=tool_id, error=str(e))
            return False
    
    # Tool Operations
    
    async def invoke_tool(
        self,
        tool_id: str, 
        operation: str,
        parameters: Dict[str, Any],
        context: Optional[ContextFrame] = None
    ) -> ToolResult:
        """Invoke a tool operation."""
        start_time = time.time()
        
        try:
            # Get tool
            tool = self.active_tools.get(tool_id)
            if not tool:
                return ToolResult(
                    success=False,
                    error="Tool not connected",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Use current context if none provided
            if context is None:
                context = self.current_context
            
            # Check ADHD constraints
            if context and not self._check_adhd_constraints(tool, context):
                return ToolResult(
                    success=False,
                    error="Operation would exceed ADHD cognitive load limits",
                    cognitive_load_impact=tool.config.cognitive_load
                )
            
            # Check rate limits
            if not await self._check_rate_limits(tool):
                return ToolResult(
                    success=False,
                    error="Rate limit exceeded",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Prepare request
            request_data = {
                'operation': operation,
                'parameters': parameters,
                'context': context.dict() if context else None,
                'session_id': self.session_id,
                'user_id': self.user_id
            }
            
            # Make API call
            result = await self._make_tool_request(tool, request_data)
            
            # Update tool statistics
            tool.total_invocations += 1
            if result.success:
                tool.successful_invocations += 1
            tool.last_used = datetime.utcnow()
            
            # Calculate average response time
            execution_time = (time.time() - start_time) * 1000
            if tool.average_response_time_ms is None:
                tool.average_response_time_ms = execution_time
            else:
                # Moving average
                tool.average_response_time_ms = (
                    tool.average_response_time_ms * 0.9 + execution_time * 0.1
                )
            
            result.execution_time_ms = execution_time
            result.cognitive_load_impact = tool.config.cognitive_load
            
            # Update tool in registry
            await self.tool_registry.update_tool(tool)
            
            logger.info("Tool invocation completed", 
                       tool_id=tool_id, 
                       operation=operation,
                       success=result.success,
                       execution_time_ms=execution_time)
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Update error in tool
            if tool_id in self.active_tools:
                tool = self.active_tools[tool_id]
                tool.last_error = ToolError(
                    error_type="invocation_error",
                    message=str(e),
                    retryable=True
                )
                await self.tool_registry.update_tool(tool)
            
            logger.error("Tool invocation failed", 
                        tool_id=tool_id, 
                        operation=operation,
                        error=str(e))
            
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    # Resource Management
    
    async def get_resource(
        self,
        tool_id: str,
        resource_id: str,
        use_cache: bool = True
    ) -> ResourceResult:
        """Get a resource from a tool."""
        try:
            # Check cache first
            cache_key = f"{tool_id}:{resource_id}"
            if use_cache and cache_key in self.cached_resources:
                cached_data = self.cached_resources[cache_key]
                if cached_data['expires_at'] > datetime.utcnow():
                    return ResourceResult(
                        success=True,
                        data=cached_data['data'],
                        from_cache=True,
                        cache_age_seconds=int(
                            (datetime.utcnow() - cached_data['cached_at']).total_seconds()
                        )
                    )
            
            # Get from tool
            result = await self.invoke_tool(
                tool_id=tool_id,
                operation='get_resource',
                parameters={'resource_id': resource_id}
            )
            
            if result.success:
                # Cache the result if cacheable
                tool = self.active_tools.get(tool_id)
                if tool:
                    # Find resource config (simplified - would be more complex in real implementation)
                    cache_ttl = 300  # 5 minutes default
                    
                    self.cached_resources[cache_key] = {
                        'data': result.data,
                        'cached_at': datetime.utcnow(),
                        'expires_at': datetime.utcnow() + timedelta(seconds=cache_ttl)
                    }
                
                return ResourceResult(
                    success=True,
                    data=result.data,
                    from_cache=False
                )
            else:
                return ResourceResult(
                    success=False,
                    error=ToolError(
                        error_type="resource_access_failed",
                        message=result.error or "Failed to get resource"
                    )
                )
            
        except Exception as e:
            logger.error("Resource access failed", 
                        tool_id=tool_id, 
                        resource_id=resource_id,
                        error=str(e))
            
            return ResourceResult(
                success=False,
                error=ToolError(
                    error_type="resource_error",
                    message=str(e)
                )
            )
    
    # Context Management
    
    def update_context(self, context: ContextFrame):
        """Update the current ADHD context."""
        self.current_context = context
        
        # Fire context updated event
        asyncio.create_task(
            self._fire_event('context_updated', {'context': context})
        )
        
        logger.debug("Context updated", 
                    user_id=self.user_id,
                    frame_id=context.frame_id,
                    cognitive_load=context.cognitive_load,
                    focus_level=context.focus_level)
    
    def get_context(self) -> Optional[ContextFrame]:
        """Get the current context frame."""
        return self.current_context
    
    # Tool Discovery
    
    async def discover_tools(self, tool_type: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Tool]:
        """Discover available tools by type or tags."""
        return await self.tool_registry.discover_tools(tool_type, tags)
    
    async def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get a specific tool by ID."""
        return await self.tool_registry.get_tool(tool_id)
    
    async def list_active_tools(self) -> List[Tool]:
        """List currently active/connected tools."""
        return list(self.active_tools.values())
    
    # Workflow Management
    
    async def execute_workflow(self, integration_id: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a predefined workflow/integration."""
        return await self.workflow_engine.execute_workflow(integration_id, parameters or {})
    
    # Event System
    
    def on(self, event_name: str, handler: Callable):
        """Register an event handler."""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    async def _fire_event(self, event_name: str, data: Dict[str, Any]):
        """Fire an event to all registered handlers."""
        handlers = self.event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.warning("Event handler error", event=event_name, error=str(e))
    
    # Private Helper Methods
    
    async def _load_registered_tools(self):
        """Load tools from the registry."""
        tools = await self.tool_registry.list_tools()
        logger.info("Loaded registered tools", count=len(tools))
    
    async def _test_tool_connection(self, tool: Tool) -> bool:
        """Test connection to a tool."""
        try:
            # Simple ping/health check
            if tool.config.endpoint_url:
                async with self.http_session.get(
                    f"{tool.config.endpoint_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
            return True  # Assume connection works if no endpoint
            
        except Exception as e:
            logger.warning("Tool connection test failed", 
                          tool_id=tool.config.tool_id, 
                          error=str(e))
            return False
    
    def _check_adhd_constraints(self, tool: Tool, context: ContextFrame) -> bool:
        """Check if tool operation respects ADHD constraints."""
        # Check cognitive load
        total_load = context.cognitive_load + tool.config.cognitive_load
        if total_load > 0.8:  # 80% cognitive load threshold
            return False
        
        # Check focus mode compatibility
        if context.focus_level > 0.7 and not tool.config.focus_safe:
            return False
        
        return True
    
    async def _check_rate_limits(self, tool: Tool) -> bool:
        """Check if tool is within rate limits."""
        # Simplified rate limiting - would be more sophisticated in practice
        if tool.config.rate_limit:
            # Check recent usage
            now = datetime.utcnow()
            minute_ago = now - timedelta(minutes=1)
            
            # This is a placeholder - real implementation would track requests
            # over time windows
            return True
        
        return True
    
    async def _make_tool_request(self, tool: Tool, request_data: Dict[str, Any]) -> ToolResult:
        """Make an API request to a tool."""
        try:
            if not tool.config.endpoint_url:
                raise ValueError("Tool has no endpoint URL")
            
            # Add authentication
            headers = await self.auth_manager.get_auth_headers(tool.config)
            headers['Content-Type'] = 'application/json'
            
            # Make request
            async with self.http_session.post(
                f"{tool.config.endpoint_url}/invoke",
                json=request_data,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    result_data = await response.json()
                    return ToolResult(**result_data)
                else:
                    error_text = await response.text()
                    return ToolResult(
                        success=False,
                        error=f"HTTP {response.status}: {error_text}"
                    )
                    
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )