"""
Claude Authentication Router - Browser auth integration for Claude Pro/Max
"""
import asyncio
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import structlog

from mcp_server.claude_client import claude_client
from mcp_client.browser_auth import BrowserAuth, OAUTH_CONFIGS
from mcp_client.models import ToolConfig, AuthType

logger = structlog.get_logger()

router = APIRouter(prefix="/api/auth/claude", tags=["Claude Authentication"])


class ClaudeAuthRequest(BaseModel):
    """Request to authenticate with Claude via browser."""
    session_token: Optional[str] = None
    use_oauth: bool = False


class ClaudeAuthResponse(BaseModel):
    """Response from Claude authentication."""
    success: bool
    message: str
    oauth_url: Optional[str] = None
    requires_browser: bool = False


class ClaudeStatusResponse(BaseModel):
    """Claude authentication status response."""
    authenticated: bool
    subscription_type: Optional[str] = None
    usage_stats: Optional[Dict[str, Any]] = None
    available_models: list = []


@router.post("/authenticate", response_model=ClaudeAuthResponse)
async def authenticate_claude(
    auth_request: ClaudeAuthRequest,
    background_tasks: BackgroundTasks
):
    """
    Authenticate with Claude using browser session token or OAuth.
    
    For Claude Pro/Max users to use their subscription with the ADHD server.
    """
    try:
        if auth_request.session_token:
            # Direct authentication with session token
            logger.info("Attempting Claude authentication with session token")
            
            success = await claude_client.authenticate_with_token(
                auth_request.session_token
            )
            
            if success:
                return ClaudeAuthResponse(
                    success=True,
                    message="Claude authenticated successfully! You can now use Claude Pro/Max models for complex ADHD support.",
                    requires_browser=False
                )
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid Claude session token. Please check your token and try again."
                )
        
        elif auth_request.use_oauth:
            # OAuth flow (if/when Claude supports it)
            logger.info("Attempting Claude OAuth authentication")
            
            # Initialize browser auth
            browser_auth = BrowserAuth()
            await browser_auth.initialize()
            
            # Configure Claude OAuth (placeholder - Claude doesn't have public OAuth yet)
            tool_config = ToolConfig(
                tool_id="claude",
                name="Claude AI",
                auth_type=AuthType.OAUTH2
            )
            
            claude_oauth_config = OAUTH_CONFIGS.get('claude', {})
            
            if not claude_oauth_config.get('client_id'):
                return ClaudeAuthResponse(
                    success=False,
                    message="Claude OAuth is not yet available. Please use session token authentication.",
                    requires_browser=False
                )
            
            # Start OAuth flow
            auth_success = await browser_auth.authenticate_tool(
                tool_config, claude_oauth_config
            )
            
            if auth_success:
                return ClaudeAuthResponse(
                    success=True,
                    message="Claude OAuth authentication successful!",
                    requires_browser=False
                )
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Claude OAuth authentication failed"
                )
        
        else:
            # Return instructions for manual authentication
            return ClaudeAuthResponse(
                success=False,
                message=(
                    "To use your Claude Pro/Max subscription:\n\n"
                    "1. Go to claude.ai and sign in\n"
                    "2. Open browser developer tools (F12)\n"
                    "3. Go to Application > Storage > Cookies\n"
                    "4. Copy the 'sessionKey' value\n"
                    "5. Send another request with session_token set\n\n"
                    "This allows you to use Claude's advanced reasoning for complex ADHD support."
                ),
                requires_browser=True
            )
    
    except Exception as e:
        logger.error("Claude authentication error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/status", response_model=ClaudeStatusResponse)
async def get_claude_status():
    """
    Get Claude authentication status and usage information.
    """
    try:
        if not claude_client.is_available():
            return ClaudeStatusResponse(
                authenticated=False,
                available_models=[]
            )
        
        # Get usage stats from browser session
        usage_stats = None
        if claude_client.browser_session:
            usage_stats = claude_client.browser_session.get_usage_stats()
        
        return ClaudeStatusResponse(
            authenticated=True,
            subscription_type="claude_pro",  # Assumed for browser auth users
            usage_stats=usage_stats,
            available_models=[
                "claude-3-haiku-20240307",
                "claude-3-sonnet-20240229", 
                "claude-3-opus-20240229",
                "claude-3-5-sonnet-20241022"
            ]
        )
    
    except Exception as e:
        logger.error("Error getting Claude status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get Claude status")


@router.post("/disconnect")
async def disconnect_claude():
    """
    Disconnect Claude authentication.
    """
    try:
        await claude_client.close()
        
        return {
            "success": True,
            "message": "Claude disconnected successfully. Reverting to local-only mode."
        }
    
    except Exception as e:
        logger.error("Error disconnecting Claude", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to disconnect Claude")


@router.post("/test")
async def test_claude_connection():
    """
    Test Claude connection with a simple ADHD-focused prompt.
    """
    try:
        if not claude_client.is_available():
            raise HTTPException(
                status_code=400,
                detail="Claude not authenticated. Please authenticate first."
            )
        
        # Test with ADHD-specific prompt
        test_response = await claude_client.generate_response(
            user_input="I'm feeling stuck and need help starting my work",
            use_case="gentle_nudge"
        )
        
        return {
            "success": True,
            "message": "Claude connection working!",
            "test_response": test_response.text,
            "model_used": test_response.model,
            "latency_ms": round(test_response.latency_ms, 1)
        }
    
    except Exception as e:
        logger.error("Claude connection test failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Connection test failed: {str(e)}"
        )


@router.get("/instructions")
async def get_authentication_instructions():
    """
    Get detailed instructions for Claude authentication.
    """
    return {
        "title": "Connect Your Claude Pro/Max Subscription",
        "description": "Use your existing Claude subscription for advanced ADHD support",
        "methods": [
            {
                "name": "Session Token (Recommended)",
                "description": "Use your browser session to authenticate",
                "steps": [
                    "1. Sign into claude.ai in your browser",
                    "2. Open Developer Tools (F12 or Ctrl+Shift+I)",
                    "3. Go to Application tab > Storage > Cookies",
                    "4. Find the 'sessionKey' cookie for claude.ai",
                    "5. Copy the entire value (starts with 'sk-ant-')",
                    "6. Use the /authenticate endpoint with this token"
                ],
                "security_note": "Your session token stays local and is never stored permanently"
            }
        ],
        "benefits": [
            "Access to Claude Opus for complex reasoning",
            "Better breakdown of overwhelming tasks",
            "More nuanced ADHD pattern recognition",
            "Uses your existing Claude Pro/Max subscription",
            "All processing respects Claude's privacy policies"
        ],
        "privacy": {
            "data_handling": "Session tokens are used only for API calls to Claude",
            "storage": "Tokens are kept in memory only, not saved to disk",
            "sharing": "No data is shared with third parties",
            "conversations": "ADHD conversations may be subject to Claude's usage policies"
        }
    }