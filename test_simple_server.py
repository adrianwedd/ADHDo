#!/usr/bin/env python3
"""
Simplified MCP ADHD Server for testing core functionality.
Strips out enterprise monitoring and focuses on chat/cognitive loop.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MCP ADHD Server - Simplified",
    description="Core ADHD support functionality without enterprise features",
    version="0.1.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory storage for testing
user_sessions: Dict[str, Dict] = {}

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    user_id: str = "test_user"
    context: Optional[Dict] = None

class ChatResponse(BaseModel):
    response: str
    user_id: str
    timestamp: str
    context_used: bool = False

# Simulated cognitive loop
async def simple_cognitive_loop(user_id: str, message: str, context: Optional[Dict] = None) -> str:
    """
    Simplified cognitive loop for testing.
    """
    # Store session
    if user_id not in user_sessions:
        user_sessions[user_id] = {"messages": [], "context": {}}
    
    user_sessions[user_id]["messages"].append({
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Crisis detection (simple pattern matching)
    crisis_keywords = ["suicide", "kill myself", "end it all", "self harm", "hurt myself"]
    message_lower = message.lower()
    
    for keyword in crisis_keywords:
        if keyword in message_lower:
            return (
                "I'm concerned about what you're sharing. Please reach out for immediate support:\n"
                "• Crisis Hotline: 988 (US)\n"
                "• Crisis Text Line: Text HOME to 741741\n"
                "• Emergency: 911\n"
                "You don't have to go through this alone."
            )
    
    # ADHD-specific responses
    adhd_responses = {
        "can't focus": "Let's try the 2-minute rule: Pick the smallest part of your task and work on it for just 2 minutes. Often starting is the hardest part.",
        "overwhelmed": "Take a deep breath. Let's break this down: What's the ONE most important thing right now? Ignore everything else for a moment.",
        "procrastinating": "Procrastination often comes from perfectionism or overwhelm. What's the tiniest step you could take? Even opening the document counts!",
        "distracted": "That's okay! ADHD brains seek stimulation. Try: Timer for 15 min focused work, then 5 min break. Or work with background music/noise.",
        "forgot": "Working memory challenges are real. Let's set up a system: Write it down immediately, set phone reminders, or use sticky notes.",
        "time": f"Current time: {datetime.now().strftime('%I:%M %p')}. Remember to check in with yourself - have you eaten, had water, or moved recently?",
        "help": "I'm here to support your ADHD challenges. I can help with focus, time management, task breakdown, or just listen. What do you need?",
    }
    
    # Check for ADHD keywords
    for keyword, response in adhd_responses.items():
        if keyword in message_lower:
            return response
    
    # Context awareness (simple)
    if context and context.get("time_of_day") == "evening":
        return "Evening is often tough for focus. Consider winding down tasks and planning tomorrow's priorities instead."
    
    # Default supportive response
    if len(user_sessions[user_id]["messages"]) > 1:
        return f"I understand. Based on our conversation, what specific challenge can I help you tackle right now?"
    else:
        return "Hi! I'm here to help with ADHD challenges. What are you working on, or what's feeling difficult today?"

# Endpoints
@app.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "sessions_active": len(user_sessions)
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint for ADHD support.
    """
    try:
        # Process through simplified cognitive loop
        response_text = await simple_cognitive_loop(
            request.user_id,
            request.message,
            request.context
        )
        
        return ChatResponse(
            response=response_text,
            user_id=request.user_id,
            timestamp=datetime.utcnow().isoformat(),
            context_used=request.context is not None
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat processing failed")

@app.get("/sessions/{user_id}")
async def get_session(user_id: str):
    """Get session history for testing."""
    if user_id not in user_sessions:
        raise HTTPException(status_code=404, detail="User session not found")
    
    return user_sessions[user_id]

@app.delete("/sessions/{user_id}")
async def clear_session(user_id: str):
    """Clear session for testing."""
    if user_id in user_sessions:
        del user_sessions[user_id]
    return {"message": "Session cleared"}

if __name__ == "__main__":
    print("🚀 Starting Simplified MCP ADHD Server...")
    print("📍 Server running at http://localhost:8000")
    print("📝 API docs at http://localhost:8000/docs")
    print("\nThis is a simplified version for testing core functionality.")
    print("Crisis detection: ✅ | ADHD patterns: ✅ | Session tracking: ✅")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)