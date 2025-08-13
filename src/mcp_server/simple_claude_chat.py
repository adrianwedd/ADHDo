"""
Simple Claude-only chatbot endpoint.
Bypasses all the complex routing and just uses Claude directly.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from mcp_server.claude_browser_working import ClaudeBrowserClient

logger = logging.getLogger(__name__)

router = APIRouter()

# Global Claude client
_claude_client: Optional[ClaudeBrowserClient] = None

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    success: bool

async def get_claude():
    """Get or create Claude browser client."""
    global _claude_client
    
    if _claude_client is None:
        _claude_client = ClaudeBrowserClient(headless=True)
        if not await _claude_client.initialize():
            raise Exception("Failed to initialize Claude")
    
    return _claude_client

@router.post("/claude_chat", response_model=ChatResponse)
async def claude_chat(request: ChatRequest):
    """Direct Claude chat - no routing, no complexity, just Claude."""
    try:
        client = await get_claude()
        
        # Add ADHD context  
        prompt = f"""You are an ADHD support assistant. Be concise, helpful, and understanding.

User: {request.message} < /dev/null