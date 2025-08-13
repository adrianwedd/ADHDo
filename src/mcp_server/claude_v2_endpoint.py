#!/usr/bin/env python3
"""
FastAPI endpoint for Claude Cognitive Engine V2
Replaces the broken cognitive loop with real Claude thinking
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from typing import Optional

from .claude_cognitive_engine_v2 import get_cognitive_engine_v2

logger = logging.getLogger(__name__)

# Request model
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"


async def create_claude_v2_endpoint(app: FastAPI):
    """Add Claude V2 cognitive endpoint to existing FastAPI app."""
    
    @app.post("/claude/v2/chat")
    async def claude_v2_chat(request: ChatRequest):
        """
        Claude V2 Cognitive Engine - Real thinking with tool awareness.
        
        This endpoint uses Claude as the actual cognitive engine with:
        - Complete system state gathering
        - Tool awareness and execution
        - Browser-only authentication
        - No fallback patterns
        """
        try:
            logger.info(f"Claude V2 processing: {request.message[:100]}...")
            
            # Get the cognitive engine
            engine = get_cognitive_engine_v2()
            
            # Process the message
            result = await engine.process(request.message, request.user_id)
            
            # Log the result
            logger.info(f"Claude V2 response: {result.get('response', 'No response')[:100]}...")
            logger.info(f"Actions taken: {len(result.get('actions_taken', []))}")
            
            return JSONResponse(content=result)
            
        except Exception as e:
            logger.error(f"Claude V2 error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/claude/v2/status")
    async def claude_v2_status():
        """Check Claude V2 engine status."""
        try:
            engine = get_cognitive_engine_v2()
            
            # Check components
            status = {
                "engine": "initialized",
                "browser_auth": "configured" if engine.claude else "not_initialized",
                "redis": "connected" if engine.redis_client else "not_connected",
                "tools_available": list(engine.tool_registry.get_available_tools().keys()),
                "state_gatherer": "ready",
                "google_integration": "available" if engine.state_gatherer.google else "not_configured"
            }
            
            return JSONResponse(content=status)
            
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return JSONResponse(
                content={"error": str(e), "engine": "error"},
                status_code=500
            )
    
    @app.get("/claude/v2/tools")
    async def get_available_tools():
        """Get list of available tools Claude can use."""
        try:
            from .claude_cognitive_engine_v2 import ToolRegistry
            tools = ToolRegistry.get_available_tools()
            
            # Format for display
            formatted_tools = {}
            for category, info in tools.items():
                formatted_tools[category] = {
                    "description": info["description"],
                    "actions": list(info["actions"].keys())
                }
            
            return JSONResponse(content=formatted_tools)
            
        except Exception as e:
            logger.error(f"Tools list error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    logger.info("✅ Claude V2 endpoints added: /claude/v2/chat, /claude/v2/status, /claude/v2/tools")


# Standalone app if running directly
def create_standalone_app():
    """Create standalone FastAPI app with Claude V2."""
    app = FastAPI(title="Claude Cognitive Engine V2")
    
    @app.get("/")
    async def root():
        return {
            "service": "Claude Cognitive Engine V2",
            "endpoints": [
                "/claude/v2/chat - Main chat endpoint",
                "/claude/v2/status - Check engine status",
                "/claude/v2/tools - List available tools"
            ]
        }
    
    # Add Claude endpoints
    import asyncio
    asyncio.create_task(create_claude_v2_endpoint(app))
    
    return app


# For uvicorn if running directly
if __name__ == "__main__":
    import uvicorn
    app = create_standalone_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)