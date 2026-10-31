"""Direct browser-backed Claude endpoint retained for legacy clients."""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from .claude_browser_working import get_claude_browser

logger = logging.getLogger(__name__)
router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    success: bool

@router.post("/claude_chat", response_model=ChatResponse)
async def claude_chat(request: ChatRequest):
    try:
        client = await get_claude_browser()
        response = await client.send_message(
            "You are an ADHD support assistant. Be concise, helpful, and understanding.\n\n"
            + "User: " + request.message)
        return ChatResponse(response=response, success=True)
    except Exception:
        logger.exception("Browser-backed Claude request failed")
        raise HTTPException(status_code=503, detail="Claude browser is unavailable")
