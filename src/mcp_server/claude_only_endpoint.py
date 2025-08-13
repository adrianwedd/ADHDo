"""
Claude-only endpoint for ADHD support - bypasses all complexity.
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    success: bool
    source: str = "claude"

@router.post("/claude", response_model=ChatResponse)
async def claude_chat(request: ChatRequest):
    """Direct Claude chat - no routing, just Claude."""
    try:
        from .claude_browser_working import get_claude_browser
        
        client = await get_claude_browser()
        
        # ADHD-optimized prompt
        prompt = f"""You are an ADHD support assistant. Be concise (2-3 sentences max), helpful, and understanding.

User: {request.message} < /dev/null