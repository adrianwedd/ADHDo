"""
Chat and MCP interaction routes - Core conversation and cognitive processing.

Extracted from monolithic main.py to improve code organization and maintainability.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

from ..models import MCPFrame, User
from ..auth import get_current_user, get_optional_user
from ..cognitive_loop import cognitive_loop
from ..health_monitor import health_monitor
from ..adhd_errors import (
    create_adhd_error_response, system_error, adhd_feature_error,
    not_found_error
)
from ..exception_handlers import ADHDFeatureException
from traces.memory import trace_memory
from frames.builder import frame_builder

chat_router = APIRouter(tags=["Chat"])


class ChatRequest(BaseModel):
    """
    Chat request with ADHD-optimized processing options.
    
    This is the primary interface for user interaction with the MCP system,
    designed to handle both regular conversations and crisis situations.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "I'm feeling overwhelmed and can't focus on my work",
                    "context": {
                        "current_task": "Writing report",
                        "energy_level": "low",
                        "distractions": ["phone notifications", "messy desk"]
                    },
                    "emergency": False
                },
                {
                    "message": "I'm having thoughts of self-harm",
                    "emergency": True
                }
            ]
        }
    )
    
    message: str = Field(
        description="User's message or question for the MCP system",
        min_length=1,
        max_length=2000,
        examples=["I can't focus today", "Help me break down this big task"]
    )
    context: Optional[dict] = Field(
        default=None,
        description="Additional context about user's current situation",
        examples=[{
            "current_task": "Project deadline",
            "energy_level": "medium", 
            "time_available": "2 hours"
        }]
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User ID for anonymous requests (authenticated users don't need this)",
        examples=["anon_user_123", "temp_session_456"]
    )
    emergency: bool = Field(
        default=False,
        description="Flag for crisis situations requiring immediate intervention"
    )


@chat_router.post("/chat", 
                  summary="Chat with MCP System",
                  description="Primary endpoint for user interaction with the MCP cognitive system")
async def chat_with_system(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Process user message through the MCP cognitive loop.
    
    Handles both authenticated and anonymous interactions with appropriate
    safety measures and context management for ADHD users.
    """
    try:
        user_id = current_user.id if current_user else request.user_id or "anonymous"
        
        # Record chat interaction metric
        health_monitor.record_metric("chat_requests", 1)
        
        # Build contextual frame optimized for ADHD patterns
        frame_data = {
            "user_message": request.message,
            "user_id": user_id,
            "context": request.context or {},
            "emergency": request.emergency,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Create frame through frame builder
        frame = await frame_builder.create_frame(frame_data)
        
        # Process through cognitive loop with safety monitoring
        response = await cognitive_loop.process(
            frame=frame,
            user_id=user_id,
            emergency=request.emergency
        )
        
        # Record successful processing
        health_monitor.record_metric("successful_chat_responses", 1)
        
        # Update trace memory for learning
        await trace_memory.record_interaction(
            user_id=user_id,
            input_frame=frame,
            response=response
        )
        
        return {
            "response": response.get("message", ""),
            "frame_id": frame.id,
            "processing_time": response.get("processing_time", 0),
            "safety_level": response.get("safety_level", "safe"),
            "nudge_triggered": response.get("nudge_triggered", False),
            "context_updated": response.get("context_updated", False)
        }
        
    except Exception as e:
        health_monitor.record_error("chat_processing", str(e))
        # For chat errors, return a supportive JSON response rather than HTTP error
        # This maintains the chat interface UX while still being ADHD-friendly
        return {
            "response": "I'm having a small hiccup processing that request. No worries - this happens sometimes! Please try rephrasing or ask something else, and I'll do my best to help.",
            "error": True,
            "frame_id": None,
            "safety_level": "safe",
            "support_message": "Every conversation system has its moments - you're doing great!",
            "next_steps": [
                "Try rephrasing your request",
                "Ask about something else", 
                "Refresh and try again if needed"
            ]
        }


@chat_router.post("/frames", response_model=MCPFrame)
async def create_frame(frame: MCPFrame):
    """
    Create a new contextual frame for MCP processing.
    
    Frames are the core data structure for context management
    in the Meta-Cognitive Protocol system.
    """
    try:
        # Validate and create frame
        created_frame = await frame_builder.create_frame(frame.dict())
        
        health_monitor.record_metric("frames_created", 1)
        
        return created_frame
        
    except Exception as e:
        health_monitor.record_error("create_frame", str(e))
        raise ADHDFeatureException("frame_creation", "Unable to create context frame", recoverable=True)


@chat_router.get("/frames/{frame_id}", response_model=MCPFrame)  
async def get_frame(frame_id: str):
    """
    Retrieve a specific frame by ID for analysis or debugging.
    
    Used for context reconstruction and interaction analysis.
    """
    try:
        frame = await frame_builder.get_frame(frame_id)
        
        if not frame:
            raise HTTPException(status_code=404, detail="Context frame not found")
        
        return frame
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("get_frame", str(e))
        raise ADHDFeatureException("frame_retrieval", "Unable to retrieve context frame", recoverable=True)


@chat_router.post("/context/{user_id}")
async def update_context(user_id: str, context_data: dict):
    """
    Update user context for improved MCP processing.
    
    Allows external systems to provide additional context
    for more personalized and effective responses.
    """
    try:
        # Update user context through trace memory
        await trace_memory.update_user_context(user_id, context_data)
        
        # Record context update
        health_monitor.record_metric("context_updates", 1)
        
        return {
            "status": "success",
            "user_id": user_id,
            "context_keys_updated": list(context_data.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        health_monitor.record_error("update_context", str(e))
        raise ADHDFeatureException("context_update", "Unable to update user context", recoverable=True)