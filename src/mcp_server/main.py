"""
MCP ADHD Server - FastAPI application entry point.

Meta-Cognitive Protocol server for ADHD executive function support.
A recursive, context-aware AI orchestration system.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from mcp_server import __version__
from mcp_server.config import settings
from mcp_server.models import MCPFrame, User, Task, NudgeTier
from mcp_server.cognitive_loop import cognitive_loop
from traces.memory import trace_memory
from frames.builder import frame_builder


# Configure structured logging
logging.basicConfig(
    format="%(message)s",
    stream=None,
    level=getattr(logging, settings.log_level.upper()),
)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    user_id: str
    message: str
    task_focus: Optional[str] = None
    nudge_tier: NudgeTier = NudgeTier.GENTLE


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("🧠⚡ MCP ADHD Server starting up...")
    logger.info("Recursion unleashed. Context orchestration online.")
    
    # Initialize Redis connections
    try:
        await trace_memory.connect()
        logger.info("✅ Redis connection initialized successfully")
    except Exception as e:
        logger.warning("⚠️ Redis connection failed, continuing in limited mode", error=str(e))
    
    # TODO: Initialize database connection
    # TODO: Initialize Telegram bot
    # TODO: Start background nudge scheduler
    
    yield
    
    logger.info("🧠⚡ MCP ADHD Server shutting down...")
    # Cleanup connections
    try:
        await trace_memory.disconnect()
        logger.info("✅ All connections closed cleanly")
    except Exception as e:
        logger.warning("⚠️ Some connections failed to close cleanly", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="MCP ADHD Server",
    description=(
        "Meta-Cognitive Protocol server for ADHD executive function support. "
        "A recursive, context-aware AI orchestration system that helps "
        "neurodivergent minds get their shit done."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with structured logging."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "version": __version__,
        "message": "Executive function orchestrator online"
    }


# Root endpoint with some personality
@app.get("/")
async def root():
    """Root endpoint with MCP ADHD Server info.""" 
    return {
        "service": "MCP ADHD Server",
        "version": __version__,
        "description": "Meta-Cognitive Protocol for Executive Function Support",
        "tagline": "Because Executive Function Is a Liar.",
        "status": "🧠⚡ Recursion unleashed",
        "docs": "/docs" if settings.debug else "Documentation disabled in production"
    }


# === CORE MCP ENDPOINTS ===

@app.post("/chat")
async def chat_with_system(request: ChatRequest):
    """
    Chat with the MCP ADHD system - main user interaction endpoint.
    
    This is the primary endpoint where users interact with the cognitive loop.
    The system builds context, processes the input through safety checks and LLM routing,
    and returns an intelligent, ADHD-appropriate response.
    """
    logger.info("Processing chat request", 
               user_id=request.user_id, 
               task_focus=request.task_focus,
               nudge_tier=request.nudge_tier.name)
    
    try:
        # Process through the cognitive loop
        result = await cognitive_loop.process_user_input(
            user_id=request.user_id,
            user_input=request.message,
            task_focus=request.task_focus,
            nudge_tier=request.nudge_tier
        )
        
        # Return structured response
        return {
            "success": result.success,
            "response": result.response.text if result.response else None,
            "actions_taken": result.actions_taken,
            "cognitive_load": result.cognitive_load,
            "processing_time_ms": result.processing_time_ms,
            "frame_id": result.context_frame.frame_id if result.context_frame else None,
            "error": result.error
        }
        
    except Exception as e:
        logger.error("Chat endpoint failed", 
                    user_id=request.user_id, 
                    error=str(e), 
                    exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}"
        )


@app.post("/frames", response_model=MCPFrame)
async def create_frame(frame: MCPFrame):
    """
    Create a new MCP Frame for context processing.
    
    This is the core endpoint where context gets assembled
    and sent to LLM agents for processing.
    """
    logger.info("Creating MCP Frame", frame_id=frame.frame_id, user_id=frame.user_id)
    
    # TODO: Validate frame against user permissions
    # TODO: Store frame in TraceMemory
    # TODO: Route to appropriate agent
    # TODO: Process response and update context
    
    return frame


@app.get("/frames/{frame_id}", response_model=MCPFrame)  
async def get_frame(frame_id: str):
    """Retrieve an MCP Frame by ID."""
    # TODO: Fetch from storage
    raise HTTPException(status_code=404, detail="Frame not found")


@app.post("/context/{user_id}")
async def update_context(user_id: str, context_data: dict):
    """
    Update context for a user.
    
    This endpoint receives context updates from various sources:
    - Home Assistant (motion, environment)
    - Calendar integrations
    - Manual user input
    - Agent feedback
    """
    logger.info("Updating context", user_id=user_id, context_type=context_data.get("type"))
    
    # TODO: Validate and process context update
    # TODO: Trigger frame building if needed
    # TODO: Check for nudge conditions
    
    return {"status": "context_updated", "user_id": user_id}


# === USER MANAGEMENT ===

@app.post("/users", response_model=User)
async def create_user(user: User):
    """Create a new user profile."""
    logger.info("Creating user", user_id=user.user_id, name=user.name)
    
    # TODO: Store user in database
    # TODO: Initialize default preferences
    # TODO: Set up integration webhooks
    
    return user


@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    """Get user profile by ID."""
    # TODO: Fetch from database
    raise HTTPException(status_code=404, detail="User not found")


# === TASK MANAGEMENT ===

@app.post("/tasks", response_model=Task)
async def create_task(task: Task):
    """Create a new task/intention."""
    logger.info("Creating task", task_id=task.task_id, title=task.title)
    
    # TODO: Store task in database
    # TODO: Schedule nudges if needed
    # TODO: Update user context
    
    return task


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """Get task by ID."""
    # TODO: Fetch from database
    raise HTTPException(status_code=404, detail="Task not found")


@app.put("/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    """Mark a task as completed."""
    logger.info("Completing task", task_id=task_id)
    
    # TODO: Update task status
    # TODO: Record completion in trace memory
    # TODO: Calculate effectiveness metrics
    # TODO: Trigger celebration/reward
    
    return {"status": "completed", "task_id": task_id}


# === NUDGE SYSTEM ===

@app.post("/nudge/{user_id}")
async def trigger_nudge(user_id: str, task_id: str = None):
    """Manually trigger a nudge for a user."""
    logger.info("Triggering nudge", user_id=user_id, task_id=task_id)
    
    # TODO: Build context frame
    # TODO: Determine appropriate nudge tier
    # TODO: Send via configured method(s)
    # TODO: Record nudge attempt
    
    return {"status": "nudge_sent", "user_id": user_id}


# === INTEGRATION WEBHOOKS ===

@app.post("/webhooks/telegram")
async def telegram_webhook(update: dict):
    """Handle incoming Telegram updates."""
    logger.info("Telegram webhook received", update_id=update.get("update_id"))
    
    # TODO: Parse Telegram update
    # TODO: Extract user response
    # TODO: Update context/task status
    # TODO: Trigger follow-up actions
    
    return {"status": "processed"}


@app.post("/webhooks/calendar")
async def calendar_webhook(event: dict):
    """Handle calendar event updates."""
    logger.info("Calendar webhook received", event_type=event.get("type"))
    
    # TODO: Parse calendar event
    # TODO: Update user context
    # TODO: Trigger proactive planning
    
    return {"status": "processed"}


@app.post("/webhooks/home_assistant")
async def home_assistant_webhook(event: dict):
    """Handle Home Assistant state changes.""" 
    logger.info("Home Assistant webhook received", entity_id=event.get("entity_id"))
    
    # TODO: Parse HA event
    # TODO: Update environmental context
    # TODO: Trigger context-aware actions
    
    return {"status": "processed"}


# === AGENT COORDINATION ===

@app.post("/agents/{agent_id}/request_context")
async def agent_request_context(agent_id: str, request: dict):
    """Agent requests context for processing."""
    user_id = request.get("user_id")
    task_focus = request.get("task_focus")
    
    logger.info("Agent requesting context", agent_id=agent_id, user_id=user_id)
    
    # TODO: Build MCP Frame for agent
    # TODO: Include relevant context history
    # TODO: Apply user preferences/permissions
    
    return {"frame": None, "status": "context_prepared"}


@app.post("/agents/{agent_id}/submit_response")
async def agent_submit_response(agent_id: str, response: dict):
    """Agent submits response after processing context."""
    logger.info("Agent submitting response", agent_id=agent_id)
    
    # TODO: Validate agent response
    # TODO: Execute suggested actions
    # TODO: Update trace memory
    # TODO: Schedule follow-ups
    
    return {"status": "response_processed"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "mcp_server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )