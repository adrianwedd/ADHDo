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
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server import __version__
from mcp_server.config import settings
from mcp_server.models import MCPFrame, User, Task, NudgeTier
from mcp_server.cognitive_loop import cognitive_loop
from mcp_server.auth import (
    auth_manager, get_current_user, get_optional_user,
    RegistrationRequest, LoginRequest, PasswordResetRequest, 
    PasswordResetConfirm, UserProfile, AuthResponse
)
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
from mcp_server.telegram_bot import telegram_bot
from mcp_server.onboarding import onboarding_manager
from mcp_server.mcp_integration import mcp_router, initialize_mcp_system, shutdown_mcp_system
from mcp_server.beta_onboarding import beta_onboarding, QuickSetupRequest, BetaInvite
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
    

    # Initialize MCP system
    try:
        await initialize_mcp_system()
        logger.info("✅ MCP system initialized successfully")
    except Exception as e:
        logger.warning("⚠️ MCP system initialization failed", error=str(e))
    # TODO: Initialize Telegram bot
    # TODO: Start background nudge scheduler
    
    yield
    
    logger.info("🧠⚡ MCP ADHD Server shutting down...")
    # Cleanup connections
    try:
        await alert_manager.stop_monitoring()
        await trace_memory.disconnect()
        await close_database()
        await shutdown_mcp_system()
        logger.info("✅ All connections closed cleanly")
    except Exception as e:
        logger.warning("⚠️ Some connections failed to close cleanly", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="MCP ADHD Server",
    description=(
        "🧠⚡ Meta-Cognitive Protocol server for ADHD executive function support.\n\n"
        "A recursive, context-aware AI orchestration system specifically designed "
        "for neurodivergent minds. Features ultra-fast responses (<3s), "
        "cognitive load management, hyperfocus detection, and crisis intervention.\n\n"
        "**Key Features:**\n"
        "- 🚀 Ultra-fast ADHD-optimized responses\n"
        "- 🎯 Context-aware task support\n" 
        "- 📱 Telegram bot integration\n"
        "- 🧠 ADHD-specific onboarding\n"
        "- 🏆 Built-in celebration system\n"
        "- 🚨 Overwhelm detection & intervention\n"
        "- 🔒 Privacy-first architecture\n\n"
        "Built by neurodivergent developers for neurodivergent users."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    contact={
        "name": "MCP ADHD Server Support",
        "url": "https://github.com/your-org/mcp-adhd-server",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.mcpadhd.com",
            "description": "Production server"
        }
    ],
    tags_metadata=[
        {
            "name": "Authentication",
            "description": "🔐 User registration, login, and session management with ADHD-optimized flows."
        },
        {
            "name": "Onboarding", 
            "description": "🧠 ADHD-specific onboarding system to customize user experience."
        },
        {
            "name": "Chat",
            "description": "💬 Core ADHD support chat API with context awareness and crisis detection."
        },
        {
            "name": "Health",
            "description": "❤️ System health monitoring and performance metrics."
        },
        {
            "name": "Telegram",
            "description": "📱 Telegram bot integration for mobile ADHD support."
        },
        {
            "name": "Webhooks",
            "description": "🔗 Integration webhooks for external services."
        }
    ]
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


# Include MCP integration router
app.include_router(mcp_router)

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

@app.get("/health", tags=["Health"], summary="Basic Health Check")
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
        "metrics": "/metrics",
        "auth": {
            "register": "/api/auth/register",
            "login": "/api/auth/login",
            "logout": "/api/auth/logout",
            "profile": "/api/auth/me"
        }
    }


# === AUTHENTICATION ENDPOINTS ===

@app.post("/api/auth/register", response_model=AuthResponse, tags=["Authentication"], 
         summary="Register New User", 
         description="Create a new ADHD-optimized user account with secure authentication.")
async def register_user(registration: RegistrationRequest, request: Request) -> AuthResponse:
    """Register a new user account.
    
    Creates a new user account with ADHD-optimized defaults and validation.
    Passwords must be at least 8 characters with letters and numbers.
    """
    try:
        # Rate limiting for registration
        client_ip = request.client.host
        if not auth_manager.check_rate_limit(f"register:{client_ip}", limit=5, window=3600):
            raise HTTPException(
                status_code=429,
                detail="Too many registration attempts. Please try again in an hour."
            )
        
        result = auth_manager.register_user(registration)
        
        if result.success:
            logger.info("User registration successful", email=registration.email)
            # Track registration metric
            metrics_collector.increment_counter("adhd_user_registrations_total")
        else:
            logger.warning("User registration failed", email=registration.email, reason=result.message)
        
        return result
        
    except ValueError as e:
        logger.warning("Registration validation error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Registration error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Let's try that again! Something went wrong with creating your account. Please check your info and give it another go.")


@app.post("/api/auth/login", response_model=AuthResponse)  
async def login_user(login: LoginRequest, request: Request) -> AuthResponse:
    """Login with email and password.
    
    Creates a secure session and returns user information.
    Sessions expire after the configured duration (default 24 hours).
    """
    try:
        # Rate limiting for login attempts
        client_ip = request.client.host
        if not auth_manager.check_rate_limit(f"login:{client_ip}", limit=10, window=3600):
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Please try again later."
            )
        
        user_agent = request.headers.get("user-agent")
        result = auth_manager.login_user(login, user_agent, client_ip)
        
        if result.success:
            logger.info("User login successful", email=login.email)
            # Track login metric
            metrics_collector.increment_counter("adhd_user_logins_total")
            
            # Set secure session cookie if successful
            response = JSONResponse(result.dict())
            if result.session_id:
                response.set_cookie(
                    key="session_id",
                    value=result.session_id,
                    httponly=True,
                    secure=not settings.debug,  # HTTPS only in production
                    samesite="lax",
                    max_age=86400 * 7  # 7 days
                )
            return response
        else:
            logger.warning("User login failed", email=login.email)
            # Add delay for failed attempts to prevent brute force
            import asyncio
            await asyncio.sleep(2)
        
        return result
        
    except Exception as e:
        logger.error("Login error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed. Please try again.")


@app.post("/api/auth/logout", response_model=AuthResponse)
async def logout_user(request: Request) -> AuthResponse:
    """Logout current user and invalidate session.
    
    Revokes the current session and clears the session cookie.
    """
    try:
        # Get session from cookie
        session_id = request.cookies.get("session_id")
        
        if session_id:
            result = auth_manager.logout_user(session_id)
            logger.info("User logout", session_id=session_id[:8])
        else:
            result = AuthResponse(
                success=True,
                message="Already logged out."
            )
        
        # Clear session cookie
        response = JSONResponse(result.dict())
        response.delete_cookie("session_id")
        
        return response
        
    except Exception as e:
        logger.error("Logout error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Logout failed.")


@app.get("/api/auth/me")
async def get_current_user_profile(current_user: User = Depends(get_current_user)) -> dict:
    """Get current user profile information.
    
    Returns the authenticated user's profile data and ADHD preferences.
    Requires valid session or API key authentication.
    """
    return {
        "user_id": current_user.user_id,
        "name": current_user.name,
        "email": getattr(current_user, 'email', None),
        "timezone": current_user.timezone,
        "preferred_nudge_methods": current_user.preferred_nudge_methods,
        "energy_patterns": current_user.energy_patterns,
        "hyperfocus_indicators": current_user.hyperfocus_indicators,
        "nudge_timing_preferences": current_user.nudge_timing_preferences,
        "created_at": datetime.utcnow().isoformat()  # TODO: get actual creation date
    }


@app.put("/api/auth/me", response_model=AuthResponse)
async def update_user_profile(
    profile: UserProfile, 
    current_user: User = Depends(get_current_user)
) -> AuthResponse:
    """Update current user profile.
    
    Updates user preferences and ADHD-specific settings.
    All fields are optional - only provided fields will be updated.
    """
    try:
        result = auth_manager.update_user_profile(current_user.user_id, profile)
        
        if result.success:
            logger.info("User profile updated", user_id=current_user.user_id)
            # Track profile update metric
            metrics_collector.increment_counter("adhd_profile_updates_total")
        
        return result
        
    except Exception as e:
        logger.error("Profile update error", user_id=current_user.user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Profile update failed. Please try again.")


@app.post("/api/auth/forgot-password", response_model=AuthResponse)
async def request_password_reset(
    reset_request: PasswordResetRequest, 
    request: Request
) -> AuthResponse:
    """Request password reset email.
    
    Sends password reset instructions to the provided email address.
    For security, always returns success regardless of email validity.
    """
    try:
        # Rate limiting for password reset
        client_ip = request.client.host
        if not auth_manager.check_rate_limit(f"reset:{client_ip}", limit=5, window=3600):
            raise HTTPException(
                status_code=429,
                detail="Too many password reset attempts. Please try again in an hour."
            )
        
        result = auth_manager.request_password_reset(reset_request.email)
        
        logger.info("Password reset requested", email=reset_request.email)
        # Track reset request metric
        metrics_collector.increment_counter("adhd_password_resets_requested_total")
        
        return result
        
    except Exception as e:
        logger.error("Password reset request error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Password reset request failed.")


@app.post("/api/auth/reset-password", response_model=AuthResponse)
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    request: Request
) -> AuthResponse:
    """Confirm password reset with token.
    
    Resets the password using the token from the reset email.
    All existing sessions will be invalidated for security.
    """
    try:
        # Rate limiting for reset confirmation
        client_ip = request.client.host
        if not auth_manager.check_rate_limit(f"reset_confirm:{client_ip}", limit=10, window=3600):
            raise HTTPException(
                status_code=429,
                detail="Too many password reset attempts. Please try again later."
            )
        
        result = auth_manager.reset_password(reset_confirm)
        
        if result.success:
            logger.info("Password reset completed successfully")
            # Track reset completion metric
            metrics_collector.increment_counter("adhd_password_resets_completed_total")
        else:
            logger.warning("Password reset failed", reason=result.message)
        
        return result
        
    except ValueError as e:
        logger.warning("Password reset validation error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Password reset error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Password reset failed. Please try again.")


# === END AUTHENTICATION ENDPOINTS ===

# === ONBOARDING ENDPOINTS ===

@app.get("/api/onboarding/status", tags=["Onboarding"], 
         summary="Get Onboarding Status",
         description="Check current user's ADHD onboarding progress and completion status.")
async def get_onboarding_status(current_user: User = Depends(get_current_user)) -> dict:
    """Get current user's onboarding status."""
    try:
        status = await onboarding_manager.get_onboarding_status(current_user.user_id)
        
        if not status:
            # Start onboarding if not started
            status = await onboarding_manager.start_onboarding(current_user.user_id)
        
        return {
            "user_id": status.user_id,
            "current_step": status.current_step,
            "is_completed": status.is_completed,
            "started_at": status.started_at.isoformat(),
            "completed_at": status.completed_at.isoformat() if status.completed_at else None
        }
        
    except Exception as e:
        logger.error("Get onboarding status failed", user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get onboarding status")


@app.post("/api/onboarding/start")
async def start_onboarding(current_user: User = Depends(get_current_user)) -> dict:
    """Start or restart the onboarding process."""
    try:
        onboarding = await onboarding_manager.start_onboarding(current_user.user_id)
        
        # Get the welcome step content
        welcome_response = await onboarding_manager.process_step(current_user.user_id, {})
        
        logger.info("Onboarding started", user_id=current_user.user_id)
        metrics_collector.increment_counter("adhd_onboarding_started_total")
        
        return {
            "status": "started",
            "onboarding_id": onboarding.user_id,
            "current_step": onboarding.current_step,
            **welcome_response
        }
        
    except Exception as e:
        logger.error("Start onboarding failed", user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start onboarding")


@app.post("/api/onboarding/step")
async def process_onboarding_step(
    step_input: dict,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Process user input for current onboarding step."""
    try:
        result = await onboarding_manager.process_step(current_user.user_id, step_input)
        
        # Track completion
        if result.get("status") == "completed":
            logger.info("Onboarding completed", user_id=current_user.user_id)
            metrics_collector.increment_counter("adhd_onboarding_completed_total")
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Process onboarding step failed", user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process onboarding step")


@app.post("/api/onboarding/skip")
async def skip_onboarding(current_user: User = Depends(get_current_user)) -> dict:
    """Skip the onboarding process and use defaults."""
    try:
        result = await onboarding_manager.skip_onboarding(current_user.user_id)
        
        logger.info("Onboarding skipped", user_id=current_user.user_id)
        metrics_collector.increment_counter("adhd_onboarding_skipped_total")
        
        return result
        
    except Exception as e:
        logger.error("Skip onboarding failed", user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to skip onboarding")


# === END ONBOARDING ENDPOINTS ===

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

@app.post("/chat", tags=["Chat"], 
         summary="Chat with ADHD AI Assistant", 
         description="Main interaction endpoint for ADHD support with context awareness, crisis detection, and ultra-fast responses (<3s).")
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

@app.post("/webhooks/telegram", tags=["Telegram"], 
         summary="Telegram Bot Webhook",
         description="Handle incoming Telegram updates for ADHD support bot.")
async def telegram_webhook(update: dict):
    """Handle incoming Telegram updates via webhook."""
    logger.info("Telegram webhook received", update_id=update.get("update_id"))
    
    try:
        # Import telegram Update class for proper parsing
        from telegram import Update
        
        # Convert dict to Update object
        telegram_update = Update.de_json(update, telegram_bot.bot)
        
        if telegram_update and telegram_bot.application:
            # Process the update through the bot's handlers
            await telegram_bot.application.process_update(telegram_update)
            
            # Track webhook processing
            metrics_collector.increment_counter("telegram_webhooks_processed_total")
            
            return {"status": "processed"}
        else:
            logger.warning("Invalid Telegram update or bot not initialized")
            return {"status": "error", "message": "Bot not available"}
            
    except Exception as e:
        logger.error("Telegram webhook processing failed", error=str(e), exc_info=True)
        return {"status": "error", "message": "Processing failed"}


@app.post("/webhooks/telegram/set")
async def set_telegram_webhook():
    """Set up the Telegram webhook (for production deployment)."""
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="Telegram bot token not configured")
    
    try:
        webhook_url = f"{settings.host}/webhooks/telegram"
        if settings.host.startswith("localhost") or settings.host.startswith("127.0.0.1"):
            raise HTTPException(status_code=400, detail="Cannot set webhook for localhost")
        
        # Set webhook
        success = await telegram_bot.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        
        if success:
            logger.info("Telegram webhook set successfully", url=webhook_url)
            return {"status": "success", "webhook_url": webhook_url}
        else:
            raise HTTPException(status_code=500, detail="Failed to set webhook")
            
    except Exception as e:
        logger.error("Failed to set Telegram webhook", error=str(e))
        raise HTTPException(status_code=500, detail=f"Webhook setup failed: {str(e)}")


@app.get("/webhooks/telegram/info")
async def get_telegram_webhook_info():
    """Get current Telegram webhook information."""
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="Telegram bot token not configured")
    
    try:
        webhook_info = await telegram_bot.bot.get_webhook_info()
        
        return {
            "webhook_url": webhook_info.url,
            "has_custom_certificate": webhook_info.has_custom_certificate,
            "pending_update_count": webhook_info.pending_update_count,
            "last_error_date": webhook_info.last_error_date,
            "last_error_message": webhook_info.last_error_message,
            "max_connections": webhook_info.max_connections,
            "allowed_updates": webhook_info.allowed_updates
        }
        
    except Exception as e:
        logger.error("Failed to get Telegram webhook info", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get webhook info: {str(e)}")


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


# === BETA ONBOARDING ENDPOINTS ===

@app.post("/api/beta/create-invite", tags=["Beta"])
async def create_beta_invite(
    expires_hours: int = 168,
    email: Optional[str] = None,
    name: Optional[str] = None
) -> dict:
    """Create a new beta tester invite."""
    invite = beta_onboarding.create_invite(expires_hours, email, name)
    
    setup_url = beta_onboarding.generate_setup_url(invite.invite_code)
    qr_code = beta_onboarding.generate_qr_code(invite.invite_code)
    
    return {
        "invite_code": invite.invite_code,
        "setup_url": setup_url,
        "qr_code": qr_code,
        "expires_at": invite.expires_at.isoformat(),
        "email": invite.email,
        "name": invite.name
    }


@app.get("/api/beta/invite/{invite_code}", tags=["Beta"])
async def get_beta_invite(invite_code: str) -> dict:
    """Get beta invite details."""
    invite = beta_onboarding.get_invite(invite_code)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    return {
        "invite_code": invite.invite_code,
        "name": invite.name,
        "email": invite.email,
        "expires_at": invite.expires_at.isoformat(),
        "is_valid": beta_onboarding.is_invite_valid(invite_code),
        "used_at": invite.used_at.isoformat() if invite.used_at else None
    }


@app.post("/api/beta/quick-setup", tags=["Beta"])
async def beta_quick_setup(setup_request: QuickSetupRequest) -> dict:
    """Complete automated beta user setup."""
    try:
        result = await beta_onboarding.quick_setup(setup_request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Beta quick setup failed", error=str(e))
        raise HTTPException(status_code=500, detail="Setup failed")


@app.get("/beta/setup", tags=["Beta"])
async def beta_setup_page(invite: str):
    """Serve the beta setup page."""
    # Validate invite
    if not beta_onboarding.is_invite_valid(invite):
        raise HTTPException(status_code=400, detail="Invalid or expired invite")
    
    invite_obj = beta_onboarding.get_invite(invite)
    
    # Return HTML setup page
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MCP ADHD Server - Beta Setup</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen">
        <div class="container mx-auto px-4 py-8 max-w-md">
            <div class="bg-white rounded-lg shadow-xl p-6">
                <div class="text-center mb-6">
                    <h1 class="text-2xl font-bold text-gray-900 mb-2">🧠⚡ Welcome Beta Tester!</h1>
                    <p class="text-gray-600">Let's set up your MCP ADHD Server</p>
                </div>
                
                <form id="setup-form">
                    <input type="hidden" name="invite_code" value="{invite}">
                    
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Name</label>
                        <input type="text" name="name" required 
                               value="{invite_obj.name or ''}"
                               class="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                    </div>
                    
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Email</label>
                        <input type="email" name="email" required 
                               value="{invite_obj.email or ''}"
                               class="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                    </div>
                    
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Password</label>
                        <input type="password" name="password" required 
                               class="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                        <p class="text-xs text-gray-600 mt-1">8+ characters with letters and numbers</p>
                    </div>
                    
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Telegram Chat ID (Optional)
                        </label>
                        <input type="text" name="telegram_chat_id" 
                               class="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                        <p class="text-xs text-gray-600 mt-1">
                            For nudges! Message @userinfobot to get your ID
                        </p>
                    </div>
                    
                    <button type="submit" 
                            class="w-full bg-blue-500 hover:bg-blue-600 text-white py-3 px-4 rounded-lg font-medium transition">
                        🚀 Set Up My ADHD Assistant
                    </button>
                </form>
                
                <div id="result" class="hidden mt-4"></div>
            </div>
        </div>
        
        <script>
            document.getElementById('setup-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData);
                
                try {{
                    const response = await fetch('/api/beta/quick-setup', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(data)
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        document.getElementById('result').innerHTML = `
                            <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
                                <h3 class="font-bold">✅ Setup Complete!</h3>
                                <p class="mt-2">${{result.message}}</p>
                                <div class="mt-4">
                                    <a href="/" class="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded">
                                        Start Using Your Assistant →
                                    </a>
                                </div>
                            </div>
                        `;
                        document.getElementById('setup-form').style.display = 'none';
                    }} else {{
                        throw new Error(result.detail || 'Setup failed');
                    }}
                    
                    document.getElementById('result').classList.remove('hidden');
                }} catch (error) {{
                    document.getElementById('result').innerHTML = `
                        <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                            <h3 class="font-bold">❌ Setup Failed</h3>
                            <p class="mt-2">${{error.message}}</p>
                        </div>
                    `;
                    document.getElementById('result').classList.remove('hidden');
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return Response(content=html_content, media_type="text/html")


@app.get("/api/beta/stats", tags=["Beta"])
async def get_beta_stats() -> dict:
    """Get beta program statistics."""
    return beta_onboarding.get_invite_stats()

# === END BETA ONBOARDING ENDPOINTS ===

        log_level=settings.log_level.lower()
    )