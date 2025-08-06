"""
MCP ADHD Server - FastAPI application entry point.

Meta-Cognitive Protocol server for ADHD executive function support.
A recursive, context-aware AI orchestration system.
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Optional

import structlog
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server import __version__
from mcp_server.config import settings
from mcp_server.models import MCPFrame, User, Task, NudgeTier
from mcp_server.cognitive_loop import cognitive_loop
from mcp_server.auth import auth_manager, get_current_user, get_optional_user
from mcp_server.database import init_database, close_database, get_database_session
from mcp_server.repositories import (
    UserRepository, TaskRepository, TraceMemoryRepository, 
    SessionRepository, APIKeyRepository, SystemHealthRepository
)
from mcp_server.health_monitor import health_monitor
from mcp_server.db_service import DatabaseService
from mcp_server.metrics import metrics_collector
from mcp_server.middleware import (
    MetricsMiddleware, PerformanceMiddleware, 
    HealthCheckMiddleware, ADHDOptimizationMiddleware, SecurityMiddleware
)
from mcp_server.alerting import alert_manager
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
    message: str
    task_focus: Optional[str] = None
    nudge_tier: NudgeTier = NudgeTier.GENTLE


class LoginRequest(BaseModel):
    """Request model for login endpoint."""
    username: str
    password: str


class CreateAPIKeyRequest(BaseModel):
    """Request model for API key creation."""
    name: str


class CreateUserRequest(BaseModel):
    """Request model for user creation."""
    name: str
    telegram_chat_id: Optional[str] = None


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
    
    # Initialize database connection
    try:
        await init_database()
        logger.info("✅ Database connection initialized successfully")
    except Exception as e:
        logger.error("❌ Database connection failed", error=str(e))
        raise
    
    # Start alert monitoring
    try:
        await alert_manager.start_monitoring(check_interval_seconds=60)
        logger.info("✅ Alert monitoring started")
    except Exception as e:
        logger.warning("⚠️ Alert monitoring failed to start", error=str(e))
    
    # TODO: Initialize Telegram bot
    # TODO: Start background nudge scheduler
    
    yield
    
    logger.info("🧠⚡ MCP ADHD Server shutting down...")
    # Cleanup connections
    try:
        await alert_manager.stop_monitoring()
        await trace_memory.disconnect()
        await close_database()
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

# Add custom middleware (order matters - last added runs first)
app.add_middleware(SecurityMiddleware)
app.add_middleware(ADHDOptimizationMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(PerformanceMiddleware, timeout_seconds=30.0)
app.add_middleware(HealthCheckMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for web interface
import os
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info("Mounted static files", directory=static_dir)
else:
    logger.warning("Static directory not found", expected_path=static_dir)


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


# === HEALTH CHECK ENDPOINTS ===

@app.get("/health")
async def basic_health_check():
    """Basic health check endpoint for load balancers."""
    return {
        "status": "healthy", 
        "version": __version__,
        "message": "Executive function orchestrator online",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check with all components."""
    return await health_monitor.get_overall_health()

@app.get("/health/{component}")
async def component_health_check(component: str):
    """Get health status for a specific component."""
    return await health_monitor.get_component_health(component)

@app.get("/health/metrics/system")
async def system_metrics():
    """Get current system performance metrics."""
    metrics = health_monitor.get_system_metrics()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_percent": metrics.cpu_percent,
        "memory_percent": metrics.memory_percent,
        "memory_available_mb": metrics.memory_available_mb,
        "disk_usage_percent": metrics.disk_usage_percent,
        "disk_free_gb": metrics.disk_free_gb,
        "load_average": metrics.load_average,
        "uptime_seconds": metrics.uptime_seconds,
        "process_count": metrics.process_count,
        "network_io": metrics.network_io,
        "disk_io": metrics.disk_io
    }

@app.get("/health/history/{component}")
async def component_health_history(
    component: str,
    hours: int = 24,
    db_session: AsyncSession = Depends(get_database_session)
):
    """Get health history for a component from database."""
    db_service = DatabaseService(db_session)
    health_history = await db_service.health.get_health_history(component, hours)
    
    return {
        "component": component,
        "hours": hours,
        "data_points": len(health_history),
        "history": [
            {
                "timestamp": record.measured_at.isoformat(),
                "status": record.status,
                "response_time_ms": record.response_time_ms,
                "error_rate": record.error_rate,
                "cpu_usage_percent": record.cpu_usage_percent,
                "memory_usage_mb": record.memory_usage_mb,
                "details": record.details
            }
            for record in health_history
        ]
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    metrics_data = metrics_collector.export_metrics()
    return Response(
        content=metrics_data,
        media_type=metrics_collector.get_content_type()
    )

@app.get("/metrics/summary")
async def metrics_summary():
    """Get summary of key metrics for debugging."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics_collector.get_metrics_summary()
    }

# === ALERTING ENDPOINTS ===

@app.get("/alerts")
async def get_active_alerts():
    """Get all active alerts."""
    return {
        "active_alerts": alert_manager.get_active_alerts(),
        "statistics": alert_manager.get_alert_statistics()
    }

@app.get("/alerts/history")
async def get_alert_history(limit: int = 50):
    """Get alert history."""
    return {
        "history": alert_manager.get_alert_history(limit),
        "total_count": len(alert_manager.alert_history)
    }

@app.get("/alerts/statistics")
async def get_alert_statistics():
    """Get alerting statistics."""
    return alert_manager.get_alert_statistics()

@app.post("/alerts/check")
async def manual_alert_check():
    """Manually trigger alert check."""
    return await alert_manager.manual_alert_check()

@app.post("/alerts/rules/{rule_name}/disable")
async def disable_alert_rule(rule_name: str):
    """Disable an alert rule."""
    success = alert_manager.disable_rule(rule_name)
    if success:
        return {"message": f"Rule '{rule_name}' disabled successfully"}
    else:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_name}' not found")

@app.post("/alerts/rules/{rule_name}/enable")
async def enable_alert_rule(rule_name: str):
    """Enable an alert rule."""
    success = alert_manager.enable_rule(rule_name)
    if success:
        return {"message": f"Rule '{rule_name}' enabled successfully"}
    else:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_name}' not found")

@app.get("/alerts/rules")
async def get_alert_rules():
    """Get all alert rules."""
    return {
        "rules": [
            {
                "name": rule.name,
                "component": rule.component,
                "metric_path": rule.metric_path,
                "condition": rule.condition,
                "threshold": rule.threshold,
                "severity": rule.severity.value,
                "cooldown_minutes": rule.cooldown_minutes,
                "consecutive_failures": rule.consecutive_failures,
                "enabled": rule.enabled,
                "failure_count": rule.failure_count,
                "last_alert_time": rule.last_alert_time.isoformat() if rule.last_alert_time else None,
                "last_check_time": rule.last_check_time.isoformat() if rule.last_check_time else None
            }
            for rule in alert_manager.alert_rules
        ]
    }


# Root endpoint with some personality
@app.get("/")
async def serve_web_interface():
    """Serve the main web interface."""
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        # Fallback to API info if no web interface
        return {
            "service": "MCP ADHD Server",
            "version": __version__,
            "description": "Meta-Cognitive Protocol for Executive Function Support",
            "tagline": "Because Executive Function Is a Liar.",
            "status": "🧠⚡ Recursion unleashed",
            "docs": "/docs" if settings.debug else "Documentation disabled in production",
            "web_interface": "Static files not found - API only mode"
        }

@app.get("/dashboard")
async def serve_dashboard():
    """Serve the performance analytics dashboard."""
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
    dashboard_path = os.path.join(static_dir, "dashboard.html")
    
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    else:
        return JSONResponse(
            status_code=404,
            content={"detail": "Dashboard not found. Please ensure static files are available."}
        )

# API info endpoint
@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "service": "MCP ADHD Server",
        "version": __version__,
        "description": "Meta-Cognitive Protocol for Executive Function Support",
        "tagline": "Because Executive Function Is a Liar.",
        "status": "🧠⚡ Recursion unleashed",
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
        "dashboard": "/dashboard",
        "web_interface": "/",
        "metrics": "/metrics"
    }

# === AUTHENTICATION ENDPOINTS ===

@app.post("/auth/login")
async def login(request: LoginRequest, response: JSONResponse):
    """Login and create session."""
    # Simple username/password check (TODO: use proper password hashing)
    if (
        request.username == settings.admin_username and 
        request.password == settings.admin_password
    ):
        # Create session
        session_id = auth_manager.create_session(
            user_id="admin",
            user_agent=None,  # TODO: extract from request
            ip_address=None   # TODO: extract from request
        )
        
        # Set session cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=not settings.debug,
            samesite="lax",
            max_age=settings.session_duration_hours * 3600
        )
        
        return {
            "success": True,
            "message": "Logged in successfully",
            "user_id": "admin"
        }
    
    raise HTTPException(
        status_code=401,
        detail="Invalid credentials"
    )


@app.post("/auth/logout")
async def logout(response: JSONResponse, current_user: User = Depends(get_current_user)):
    """Logout and destroy session."""
    # Remove session cookie
    response.delete_cookie("session_id")
    
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@app.post("/auth/api-keys")
async def create_api_key(
    request: CreateAPIKeyRequest, 
    current_user: User = Depends(get_current_user)
):
    """Create new API key for user."""
    key_id, api_key = auth_manager.generate_api_key(
        user_id=current_user.user_id,
        name=request.name
    )
    
    return {
        "key_id": key_id,
        "api_key": api_key,
        "name": request.name,
        "created_at": datetime.utcnow().isoformat()
    }


@app.delete("/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str, 
    current_user: User = Depends(get_current_user)
):
    """Revoke API key."""
    success = auth_manager.revoke_api_key(key_id)
    
    if success:
        return {"success": True, "message": "API key revoked"}
    else:
        raise HTTPException(status_code=404, detail="API key not found")


@app.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "user_id": current_user.user_id,
        "name": current_user.name,
        "preferred_nudge_methods": current_user.preferred_nudge_methods,
        "timezone": current_user.timezone,
        "telegram_configured": bool(current_user.telegram_chat_id)
    }


# === CORE MCP ENDPOINTS ===

@app.post("/chat")
async def chat_with_system(
    request: ChatRequest, 
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the MCP ADHD system - main user interaction endpoint.
    
    This is the primary endpoint where users interact with the cognitive loop.
    The system builds context, processes the input through safety checks and LLM routing,
    and returns an intelligent, ADHD-appropriate response.
    """
    logger.info("Processing chat request", 
               user_id=current_user.user_id, 
               task_focus=request.task_focus,
               nudge_tier=request.nudge_tier.name)
    
    try:
        # Process through the cognitive loop
        result = await cognitive_loop.process_user_input(
            user_id=current_user.user_id,
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
                    user_id=current_user.user_id, 
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