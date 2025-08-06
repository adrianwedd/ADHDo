"""
MCP Integration endpoints for the main ADHD server.

Provides endpoints for managing MCP tools and browser-based authentication.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from mcp_server.auth import get_current_user
from mcp_server.models import User
from mcp_client import MCPClient
from mcp_client.browser_auth import BrowserAuth, OAUTH_CONFIGS
from mcp_client.models import ToolConfig, ToolType, AuthType, ToolCapability
from mcp_tools import GmailTool

logger = structlog.get_logger()

# Router for MCP endpoints
mcp_router = APIRouter(prefix="/api/mcp", tags=["MCP Tools"])

# Global MCP client instances (per user)
mcp_clients: Dict[str, MCPClient] = {}
browser_auth: Optional[BrowserAuth] = None


class ToolRegistrationRequest(BaseModel):
    """Request to register a new MCP tool."""
    tool_type: str
    name: Optional[str] = None
    auth_config: Dict[str, Any] = {}


class AuthenticationRequest(BaseModel):
    """Request to authenticate with a tool."""
    tool_id: str
    oauth_provider: Optional[str] = None
    credentials: Dict[str, Any] = {}


class ToolInvocationRequest(BaseModel):
    """Request to invoke a tool operation."""
    tool_id: str
    operation: str
    parameters: Dict[str, Any] = {}


async def get_user_mcp_client(current_user: User = Depends(get_current_user)) -> MCPClient:
    """Get or create MCP client for current user."""
    user_id = current_user.user_id
    
    if user_id not in mcp_clients:
        # Create new MCP client for user
        client = MCPClient(user_id)
        await client.initialize()
        mcp_clients[user_id] = client
    
    return mcp_clients[user_id]


async def initialize_mcp_system():
    """Initialize the MCP system."""
    global browser_auth
    
    try:
        # Initialize browser auth
        browser_auth = BrowserAuth()
        await browser_auth.initialize()
        
        logger.info("MCP system initialized successfully")
        return True
        
    except Exception as e:
        logger.error("MCP system initialization failed", error=str(e))
        return False


async def shutdown_mcp_system():
    """Shutdown the MCP system."""
    global browser_auth
    
    try:
        # Close all MCP clients
        for client in mcp_clients.values():
            await client.close()
        mcp_clients.clear()
        
        # Close browser auth
        if browser_auth:
            await browser_auth.close()
        
        logger.info("MCP system shutdown complete")
        
    except Exception as e:
        logger.error("MCP system shutdown error", error=str(e))


@mcp_router.get("/tools")
async def list_available_tools(
    mcp_client: MCPClient = Depends(get_user_mcp_client)
) -> Dict[str, Any]:
    """List all available MCP tools."""
    try:
        tools = await mcp_client.discover_tools()
        
        return {
            'tools': [
                {
                    'tool_id': tool.config.tool_id,
                    'name': tool.config.name,
                    'description': tool.config.description,
                    'tool_type': tool.config.tool_type.value,
                    'status': tool.status.value,
                    'connected': tool.status.value == 'connected',
                    'adhd_friendly': tool.config.adhd_friendly,
                    'cognitive_load': tool.config.cognitive_load,
                    'focus_safe': tool.config.focus_safe,
                    'capabilities': [cap.value for cap in tool.config.capabilities],
                    'operations': tool.config.supported_operations
                }
                for tool in tools
            ],
            'total_count': len(tools),
            'connected_count': len([t for t in tools if t.status.value == 'connected'])
        }
        
    except Exception as e:
        logger.error("Failed to list tools", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/tools/register")
async def register_tool(
    request: ToolRegistrationRequest,
    mcp_client: MCPClient = Depends(get_user_mcp_client)
) -> Dict[str, Any]:
    """Register a new MCP tool."""
    try:
        tool_type = request.tool_type.lower()
        
        # Create tool instance based on type
        if tool_type == 'gmail':
            tool = GmailTool(mcp_client.user_id)
            tool_config = tool.get_tool_config()
            
            # Register with MCP client
            success = await mcp_client.register_tool(tool_config)
            
            if success:
                return {
                    'success': True,
                    'message': f'Gmail tool registered successfully',
                    'tool_id': tool_config.tool_id,
                    'requires_auth': True,
                    'auth_type': 'oauth2'
                }
            else:
                raise HTTPException(status_code=400, detail="Tool registration failed")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported tool type: {tool_type}")
            
    except Exception as e:
        logger.error("Tool registration failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/tools/authenticate")
async def authenticate_tool(
    request: AuthenticationRequest,
    mcp_client: MCPClient = Depends(get_user_mcp_client)
) -> Dict[str, Any]:
    """Authenticate with a tool using browser OAuth."""
    try:
        if not browser_auth:
            raise HTTPException(status_code=500, detail="Browser auth not initialized")
        
        # Get tool configuration
        tool = await mcp_client.get_tool(request.tool_id)
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")
        
        if tool.config.auth_type != AuthType.OAUTH2:
            raise HTTPException(status_code=400, detail="Tool does not use OAuth2")
        
        # Get OAuth config
        provider = request.oauth_provider or request.tool_id
        if provider not in OAUTH_CONFIGS:
            raise HTTPException(status_code=400, detail=f"OAuth config not found for {provider}")
        
        oauth_config = OAUTH_CONFIGS[provider].copy()
        
        # Update with user credentials
        if 'client_id' in request.credentials:
            oauth_config['client_id'] = request.credentials['client_id']
        if 'client_secret' in request.credentials:
            oauth_config['client_secret'] = request.credentials['client_secret']
        
        if not oauth_config.get('client_id') or not oauth_config.get('client_secret'):
            raise HTTPException(
                status_code=400, 
                detail="OAuth client_id and client_secret are required"
            )
        
        # Start browser authentication
        success = await browser_auth.authenticate_tool(tool.config, oauth_config)
        
        if success:
            # Connect the tool in MCP client
            await mcp_client.connect_tool(request.tool_id)
            
            return {
                'success': True,
                'message': f'Authentication successful for {request.tool_id}',
                'authenticated': True
            }
        else:
            return {
                'success': False,
                'message': 'Authentication failed',
                'authenticated': False
            }
            
    except Exception as e:
        logger.error("Tool authentication failed", 
                    tool_id=request.tool_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/tools/{tool_id}/invoke")
async def invoke_tool(
    tool_id: str,
    request: ToolInvocationRequest,
    mcp_client: MCPClient = Depends(get_user_mcp_client)
) -> Dict[str, Any]:
    """Invoke an operation on a connected tool."""
    try:
        # Get current ADHD context (would be from context manager)
        context = mcp_client.get_context()
        
        # Invoke tool
        result = await mcp_client.invoke_tool(
            tool_id=tool_id,
            operation=request.operation,
            parameters=request.parameters,
            context=context
        )
        
        return {
            'success': result.success,
            'data': result.data,
            'message': result.message,
            'error': result.error,
            'execution_time_ms': result.execution_time_ms,
            'cognitive_load_impact': result.cognitive_load_impact,
            'follow_up_suggested': result.follow_up_suggested
        }
        
    except Exception as e:
        logger.error("Tool invocation failed", 
                    tool_id=tool_id, 
                    operation=request.operation,
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.get("/tools/{tool_id}/status")
async def get_tool_status(
    tool_id: str,
    mcp_client: MCPClient = Depends(get_user_mcp_client)
) -> Dict[str, Any]:
    """Get status of a specific tool."""
    try:
        tool = await mcp_client.get_tool(tool_id)
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")
        
        return {
            'tool_id': tool_id,
            'name': tool.config.name,
            'status': tool.status.value,
            'connected': tool.status.value == 'connected',
            'last_used': tool.last_used.isoformat() if tool.last_used else None,
            'total_invocations': tool.total_invocations,
            'success_rate': (tool.successful_invocations / tool.total_invocations * 100) if tool.total_invocations > 0 else 0,
            'average_response_time_ms': tool.average_response_time_ms,
            'last_error': {
                'type': tool.last_error.error_type,
                'message': tool.last_error.message,
                'retryable': tool.last_error.retryable
            } if tool.last_error else None
        }
        
    except Exception as e:
        logger.error("Failed to get tool status", tool_id=tool_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.get("/integrations")
async def list_integrations(
    mcp_client: MCPClient = Depends(get_user_mcp_client)
) -> Dict[str, Any]:
    """List available workflow integrations."""
    try:
        integrations = mcp_client.workflow_engine.list_integrations()
        
        return {
            'integrations': integrations,
            'count': len(integrations)
        }
        
    except Exception as e:
        logger.error("Failed to list integrations", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/integrations/{integration_id}/execute")
async def execute_integration(
    integration_id: str,
    parameters: Dict[str, Any] = {},
    mcp_client: MCPClient = Depends(get_user_mcp_client)
) -> Dict[str, Any]:
    """Execute a workflow integration."""
    try:
        result = await mcp_client.execute_workflow(integration_id, parameters)
        
        return result
        
    except Exception as e:
        logger.error("Integration execution failed", 
                    integration_id=integration_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.get("/oauth/configs")
async def get_oauth_configs() -> Dict[str, Any]:
    """Get available OAuth configurations."""
    return {
        'providers': {
            provider: {
                'name': provider.replace('_', ' ').title(),
                'authorization_url': config['authorization_url'],
                'required_fields': ['client_id', 'client_secret'],
                'scope': config.get('scope', '')
            }
            for provider, config in OAUTH_CONFIGS.items()
        }
    }


@mcp_router.get("/stats")
async def get_mcp_stats(
    mcp_client: MCPClient = Depends(get_user_mcp_client)
) -> Dict[str, Any]:
    """Get MCP system statistics."""
    try:
        tools = await mcp_client.discover_tools()
        active_tools = await mcp_client.list_active_tools()
        
        return {
            'total_tools': len(tools),
            'active_tools': len(active_tools),
            'tool_types': list(set(t.config.tool_type.value for t in tools)),
            'adhd_friendly_tools': len([t for t in tools if t.config.adhd_friendly]),
            'focus_safe_tools': len([t for t in tools if t.config.focus_safe]),
            'average_cognitive_load': sum(t.config.cognitive_load for t in tools) / len(tools) if tools else 0
        }
        
    except Exception as e:
        logger.error("Failed to get MCP stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))