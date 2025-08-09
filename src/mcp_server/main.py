"""
MCP ADHD Server - Refactored FastAPI application entry point.

Meta-Cognitive Protocol server for ADHD executive function support.
A recursive, context-aware AI orchestration system with modular architecture.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from datetime import datetime

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from mcp_server import __version__
from mcp_server.config import settings
from mcp_server.database import init_database, close_database
from mcp_server.middleware import (
    MetricsMiddleware, PerformanceMiddleware, 
    HealthCheckMiddleware, ADHDOptimizationMiddleware, SecurityMiddleware
)
from mcp_server.health_monitor import health_monitor
from mcp_server.metrics import metrics_collector
from mcp_server.alerting import alert_manager
from mcp_server.telegram_bot import telegram_bot
from mcp_server.mcp_integration import initialize_mcp_system, shutdown_mcp_system
from mcp_server.websocket_manager import websocket_manager, start_periodic_health_check

# Import all routers
from mcp_server.routers import (
    auth_router, health_router, chat_router, user_router,
    webhook_router, beta_router, evolution_router
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan manager - handles startup and shutdown.
    
    Initializes all system components, starts background tasks,
    and ensures clean shutdown of all services.
    """
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logger = structlog.get_logger(__name__)
    logger.info("Starting MCP ADHD Server", version=__version__)
    
    try:
        # Initialize core systems
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize health monitoring
        await health_monitor.initialize()
        logger.info("Health monitoring system initialized")
        
        # Initialize metrics collection
        await metrics_collector.initialize()
        logger.info("Metrics collection system initialized")
        
        # Initialize alerting system
        await alert_manager.initialize()
        logger.info("Alerting system initialized")
        
        # Initialize MCP integration system
        await initialize_mcp_system()
        logger.info("MCP integration system initialized")
        
        # Initialize Telegram bot if configured
        if hasattr(settings, 'TELEGRAM_BOT_TOKEN') and settings.TELEGRAM_BOT_TOKEN:
            await telegram_bot.initialize()
            logger.info("Telegram bot initialized")
        
        # Start background tasks
        import asyncio
        asyncio.create_task(start_periodic_health_check())
        asyncio.create_task(health_monitor.start_monitoring())
        asyncio.create_task(metrics_collector.start_collection())
        asyncio.create_task(alert_manager.start_monitoring())
        
        # Import and start evolution periodic updates
        from mcp_server.routers.evolution_routes import broadcast_periodic_updates
        asyncio.create_task(broadcast_periodic_updates())
        
        logger.info("All background tasks started")
        logger.info("MCP ADHD Server startup complete", 
                   host=settings.HOST, port=settings.PORT)
        
        yield  # Server runs here
        
    except Exception as e:
        logger.error("Failed to start server", error=str(e))
        raise
    
    finally:
        # Shutdown sequence
        logger.info("Shutting down MCP ADHD Server")
        
        try:
            # Shutdown MCP system
            await shutdown_mcp_system()
            logger.info("MCP integration system shutdown complete")
            
            # Shutdown Telegram bot
            if hasattr(settings, 'TELEGRAM_BOT_TOKEN') and settings.TELEGRAM_BOT_TOKEN:
                await telegram_bot.shutdown()
                logger.info("Telegram bot shutdown complete")
            
            # Shutdown monitoring systems
            await alert_manager.shutdown()
            await metrics_collector.shutdown() 
            await health_monitor.shutdown()
            logger.info("Monitoring systems shutdown complete")
            
            # Close database connections
            await close_database()
            logger.info("Database connections closed")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))
        
        logger.info("MCP ADHD Server shutdown complete")


def create_app() -> FastAPI:
    """
    Application factory - creates and configures FastAPI application.
    
    Returns:
        Configured FastAPI application with all routes and middleware
    """
    # Create FastAPI application
    app = FastAPI(
        title="MCP ADHD Server",
        description="Meta-Cognitive Protocol server for ADHD executive function support",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware stack (order matters)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(ADHDOptimizationMiddleware)
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(HealthCheckMiddleware)
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Register all routers
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(user_router)
    app.include_router(webhook_router)
    app.include_router(beta_router)
    app.include_router(evolution_router)
    
    # Add GitHub automation endpoints
    from mcp_server.github_automation_endpoints import github_router
    app.include_router(github_router, prefix="/api/github", tags=["GitHub Automation"])
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler with ADHD-optimized error responses."""
        logger = structlog.get_logger(__name__)
        logger.error("Unhandled exception", 
                    path=str(request.url.path),
                    method=request.method,
                    error=str(exc))
        
        # Record error metric
        health_monitor.record_error("global_exception", str(exc))
        
        # Return ADHD-friendly error response
        return JSONResponse(
            status_code=500,
            content={
                "error": "Something went wrong. Please try again in a moment.",
                "support": "If this continues, please contact support.",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    # Basic web interface routes
    @app.get("/")
    async def serve_web_interface():
        """Serve the main web interface for ADHD users."""
        try:
            return FileResponse(
                path="static/index.html",
                media_type="text/html",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        except Exception as e:
            health_monitor.record_error("serve_web_interface", str(e))
            raise HTTPException(status_code=500, detail="Web interface unavailable")
    
    @app.get("/dashboard")
    async def serve_dashboard():
        """Serve the ADHD-optimized dashboard interface."""
        try:
            return FileResponse(
                path="static/dashboard.html", 
                media_type="text/html",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate"
                }
            )
        except Exception as e:
            health_monitor.record_error("serve_dashboard", str(e))
            raise HTTPException(status_code=500, detail="Dashboard unavailable")
    
    @app.get("/favicon.ico")
    async def favicon():
        """Serve favicon with appropriate caching headers."""
        try:
            return FileResponse(
                path="static/favicon.ico",
                media_type="image/x-icon",
                headers={
                    "Cache-Control": "public, max-age=3600"
                }
            )
        except Exception:
            # Fallback to SVG favicon
            return FileResponse(
                path="static/favicon.svg",
                media_type="image/svg+xml"
            )
    
    @app.get("/api")
    async def api_info():
        """API information and documentation links."""
        return {
            "name": "MCP ADHD Server API",
            "version": __version__,
            "description": "Meta-Cognitive Protocol server for ADHD executive function support",
            "documentation": {
                "openapi": "/openapi.json",
                "swagger_ui": "/docs",
                "redoc": "/redoc"
            },
            "endpoints": {
                "health": "/health",
                "metrics": "/metrics",
                "chat": "/chat",
                "authentication": "/api/auth",
                "beta": "/api/beta",
                "evolution": "/api/evolution"
            },
            "websockets": {
                "evolution": "/api/evolution/ws"
            }
        }
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    from datetime import datetime
    
    # Add startup timestamp import
    
    print(f"🧠 MCP ADHD Server v{__version__}")
    print(f"🚀 Starting server at {datetime.now()}")
    print(f"📡 http://{settings.HOST}:{settings.PORT}")
    print(f"📖 API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )