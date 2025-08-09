"""
MCP ADHD Server - Performance-Optimized FastAPI application entry point.

Meta-Cognitive Protocol server for ADHD executive function support.
A recursive, context-aware AI orchestration system with modular architecture.

Performance Optimization Features:
- Lazy loading of heavy components (evolution engine, integrations)
- Deferred initialization of optional services
- Memory-efficient startup sequence
- Sub-3 second response time targeting for ADHD users
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from datetime import datetime

# Performance tracking for startup
_startup_start_time = time.perf_counter()
_startup_metrics = {
    'import_times': {},
    'memory_snapshots': [],
    'stages': {}
}

def _record_import_time(module_name: str, start_time: float):
    """Record import time for performance monitoring."""
    _startup_metrics['import_times'][module_name] = time.perf_counter() - start_time

# Core imports only - defer heavy modules
_import_start = time.perf_counter()
import structlog
_record_import_time('structlog', _import_start)

_import_start = time.perf_counter()
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
_record_import_time('fastapi', _import_start)

# Import performance config and lazy loading utilities
from mcp_server.performance_config import (
    perf_config, lazy_importer, should_enable_service
)
from mcp_server import __version__
from mcp_server.config import settings

# Core system imports (required for basic functionality)
from mcp_server.database import init_database, close_database
from mcp_server.middleware import (
    MetricsMiddleware, PerformanceMiddleware, 
    HealthCheckMiddleware, ADHDOptimizationMiddleware, SecurityMiddleware
)
from mcp_server.health_monitor import health_monitor
from mcp_server.metrics import metrics_collector
from mcp_server.alerting import alert_manager
from mcp_server.websocket_manager import websocket_manager, start_periodic_health_check

# Import core routers only - defer optional ones
from mcp_server.routers import (
    auth_router, health_router, chat_router, user_router,
    webhook_router, beta_router
)

# Mark startup stage
_startup_metrics['stages']['core_imports'] = time.perf_counter() - _startup_start_time


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Performance-optimized FastAPI lifespan manager.
    
    Features:
    - Parallel initialization of independent components
    - Lazy loading of optional services  
    - Fast-fail for critical ADHD response times
    - Memory-efficient startup sequence
    """
    startup_timer = time.perf_counter()
    
    # Configure structured logging with performance optimizations
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
    logger.info("Starting MCP ADHD Server", version=__version__, performance_mode=True)
    
    # Store startup metrics
    _startup_metrics['stages']['lifespan_start'] = time.perf_counter() - _startup_start_time
    
    # Lazy imports for optional services
    telegram_bot_module = None
    mcp_integration_module = None
    evolution_router_module = None
    github_router_module = None
    
    try:
        # Initialize core systems in parallel where possible
        import asyncio
        
        logger.info("Initializing core systems...")
        stage_start = time.perf_counter()
        
        # Run core initializations in parallel
        core_tasks = []
        core_tasks.append(init_database())
        core_tasks.append(health_monitor.initialize())
        core_tasks.append(metrics_collector.initialize())
        core_tasks.append(alert_manager.initialize())
        
        # Wait for core systems with timeout
        await asyncio.wait_for(
            asyncio.gather(*core_tasks), 
            timeout=perf_config.startup_timeout_seconds
        )
        
        _startup_metrics['stages']['core_init'] = time.perf_counter() - stage_start
        logger.info("Core systems initialized", elapsed=f"{_startup_metrics['stages']['core_init']:.2f}s")
        
        # Initialize optional services based on configuration
        optional_services = []
        
        # Lazy load MCP integration if enabled
        if should_enable_service('mcp_integration'):
            logger.info("Loading MCP integration system...")
            mcp_integration_module = lazy_importer.get_module(
                'mcp_integration', 'mcp_server.mcp_integration'
            )
            if mcp_integration_module:
                optional_services.append(mcp_integration_module.initialize_mcp_system())
        
        # Lazy load Telegram bot if configured
        if should_enable_service('telegram_bot') and hasattr(settings, 'TELEGRAM_BOT_TOKEN') and settings.TELEGRAM_BOT_TOKEN:
            logger.info("Loading Telegram bot...")
            telegram_bot_module = lazy_importer.get_module(
                'telegram_bot', 'mcp_server.telegram_bot'
            )
            if telegram_bot_module and hasattr(telegram_bot_module, 'telegram_bot'):
                optional_services.append(telegram_bot_module.telegram_bot.initialize())
        
        # Initialize optional services in parallel
        if optional_services:
            optional_start = time.perf_counter()
            try:
                await asyncio.wait_for(
                    asyncio.gather(*optional_services, return_exceptions=True),
                    timeout=perf_config.startup_timeout_seconds
                )
                _startup_metrics['stages']['optional_init'] = time.perf_counter() - optional_start
                logger.info("Optional services initialized", elapsed=f"{_startup_metrics['stages']['optional_init']:.2f}s")
            except asyncio.TimeoutError:
                logger.warning("Some optional services timed out during initialization")
        
        # Start background tasks with error handling
        logger.info("Starting background tasks...")
        background_start = time.perf_counter()
        
        background_tasks = []
        background_tasks.append(asyncio.create_task(start_periodic_health_check()))
        background_tasks.append(asyncio.create_task(health_monitor.start_monitoring()))
        background_tasks.append(asyncio.create_task(metrics_collector.start_collection()))
        background_tasks.append(asyncio.create_task(alert_manager.start_monitoring()))
        
        # Lazy load and start evolution periodic updates if enabled
        if should_enable_service('evolution_engine'):
            evolution_router_module = lazy_importer.get_module(
                'evolution_routes', 'mcp_server.routers.evolution_routes'
            )
            if evolution_router_module and hasattr(evolution_router_module, 'broadcast_periodic_updates'):
                background_tasks.append(asyncio.create_task(evolution_router_module.broadcast_periodic_updates()))
        
        _startup_metrics['stages']['background_tasks'] = time.perf_counter() - background_start
        
        # Calculate total startup time
        total_startup_time = time.perf_counter() - startup_timer
        _startup_metrics['stages']['total_startup'] = total_startup_time
        
        # Log performance metrics
        logger.info("MCP ADHD Server startup complete", 
                   host=settings.HOST, 
                   port=settings.PORT,
                   startup_time=f"{total_startup_time:.2f}s",
                   memory_efficient=True,
                   performance_optimized=True)
        
        # Log import statistics
        import_stats = lazy_importer.get_import_stats()
        if import_stats:
            logger.info("Lazy import performance", import_times=import_stats)
        
        # Performance warning if startup took too long
        if total_startup_time > 5.0:
            logger.warning("Startup time exceeded target", 
                          actual=f"{total_startup_time:.2f}s", 
                          target="5.0s",
                          adhd_impact="May affect user experience")
        
        # Store metrics in app state for monitoring
        app.state.startup_metrics = _startup_metrics
        
        yield  # Server runs here
        
    except Exception as e:
        logger.error("Failed to start server", error=str(e), elapsed=f"{time.perf_counter() - startup_timer:.2f}s")
        raise
    
    finally:
        # Performance-optimized shutdown sequence
        logger.info("Shutting down MCP ADHD Server")
        shutdown_start = time.perf_counter()
        
        try:
            # Shutdown tasks with timeout to prevent hanging
            shutdown_tasks = []
            
            # Shutdown MCP system
            if mcp_integration_module and hasattr(mcp_integration_module, 'shutdown_mcp_system'):
                shutdown_tasks.append(mcp_integration_module.shutdown_mcp_system())
            
            # Shutdown Telegram bot
            if telegram_bot_module and hasattr(telegram_bot_module, 'telegram_bot'):
                shutdown_tasks.append(telegram_bot_module.telegram_bot.shutdown())
            
            # Shutdown monitoring systems
            shutdown_tasks.extend([
                alert_manager.shutdown(),
                metrics_collector.shutdown(),
                health_monitor.shutdown()
            ])
            
            # Run shutdowns in parallel with timeout
            if shutdown_tasks:
                await asyncio.wait_for(
                    asyncio.gather(*shutdown_tasks, return_exceptions=True),
                    timeout=10.0  # Quick shutdown for ADHD users
                )
            
            # Close database connections
            await close_database()
            
            shutdown_time = time.perf_counter() - shutdown_start
            logger.info("MCP ADHD Server shutdown complete", shutdown_time=f"{shutdown_time:.2f}s")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))


def create_app() -> FastAPI:
    """
    Performance-optimized application factory.
    
    Features:
    - Lazy loading of optional routers
    - Memory-efficient middleware ordering
    - ADHD-optimized response configuration
    - Built-in performance monitoring
    
    Returns:
        Configured FastAPI application with all routes and middleware
    """
    app_creation_start = time.perf_counter()
    
    # Create FastAPI application with performance optimizations
    app = FastAPI(
        title="MCP ADHD Server",
        description="Meta-Cognitive Protocol server for ADHD executive function support",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production for performance
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        # Performance optimizations for ADHD users
        default_response_class=JSONResponse,
        generate_unique_id_function=lambda route: f"{route.tags[0]}-{route.name}" if route.tags else route.name
    )
    
    # Configure CORS with performance optimizations
    cors_origins = getattr(settings, 'ALLOWED_ORIGINS', ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods for performance
        allow_headers=["*"],
        max_age=3600 if not settings.DEBUG else 0  # Cache preflight requests in production
    )
    
    # Add custom middleware stack in performance-optimized order
    # Security first (fail fast for unauthorized requests)
    app.add_middleware(SecurityMiddleware)
    
    # ADHD optimizations early in the stack (critical for user experience)
    app.add_middleware(ADHDOptimizationMiddleware)
    
    # Performance monitoring (track response times for ADHD requirements)
    app.add_middleware(PerformanceMiddleware)
    
    # Metrics collection (efficient data gathering)
    app.add_middleware(MetricsMiddleware)
    
    # Health checks last (less critical path)
    app.add_middleware(HealthCheckMiddleware)
    
    # Mount static files with caching
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    except RuntimeError:
        # Handle case where static directory doesn't exist
        logger = structlog.get_logger(__name__)
        logger.warning("Static directory not found, skipping static file mounting")
    
    # Register core routers (always needed)
    app.include_router(auth_router, tags=["Authentication"])
    app.include_router(health_router, tags=["Health"])
    app.include_router(chat_router, tags=["Chat"])  # Critical for ADHD users
    app.include_router(user_router, tags=["Users"])
    app.include_router(webhook_router, tags=["Webhooks"])
    app.include_router(beta_router, tags=["Beta"])
    
    # Lazy load optional routers based on configuration
    if should_enable_service('evolution_engine'):
        # Import evolution router lazily
        evolution_router_module = lazy_importer.get_module(
            'evolution_routes', 'mcp_server.routers.evolution_routes'
        )
        if evolution_router_module and hasattr(evolution_router_module, 'evolution_router'):
            app.include_router(evolution_router_module.evolution_router, tags=["Evolution"])
    
    # Lazy load GitHub automation endpoints
    if should_enable_service('github_automation'):
        github_router_module = lazy_importer.get_module(
            'github_automation', 'mcp_server.github_automation_endpoints'
        )
        if github_router_module and hasattr(github_router_module, 'github_router'):
            app.include_router(
                github_router_module.github_router, 
                prefix="/api/github", 
                tags=["GitHub Automation"]
            )
    
    # Performance monitoring endpoints
    @app.get("/api/performance/startup")
    async def get_startup_metrics():
        """Get server startup performance metrics."""
        if hasattr(app.state, 'startup_metrics'):
            return {
                "startup_metrics": app.state.startup_metrics,
                "import_stats": lazy_importer.get_import_stats(),
                "performance_config": {
                    "lazy_loading": perf_config.lazy_import_enabled,
                    "parallel_startup": perf_config.parallel_startup_enabled,
                    "memory_threshold_mb": perf_config.memory_threshold_mb
                }
            }
        return {"error": "Startup metrics not available"}
    
    @app.get("/api/performance/memory")
    async def get_memory_usage():
        """Get current memory usage statistics."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            "memory_usage_mb": memory_info.rss / 1024 / 1024,
            "memory_percent": process.memory_percent(),
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads(),
            "open_files": len(process.open_files()) if hasattr(process, 'open_files') else 0,
            "connections": len(process.connections()) if hasattr(process, 'connections') else 0
        }

    # Global exception handler with performance optimization
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler with ADHD-optimized error responses."""
        logger = structlog.get_logger(__name__)
        
        # Fast logging for performance (structured but minimal)
        logger.error("Unhandled exception", 
                    path=str(request.url.path),
                    method=request.method,
                    error=str(exc)[:200])  # Truncate long errors for performance
        
        # Record error metric (non-blocking)
        try:
            health_monitor.record_error("global_exception", str(exc)[:100])
        except Exception:
            pass  # Don't let error recording cause more errors
        
        # Return ADHD-friendly error response (fast and clear)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Something went wrong. Please try again in a moment.",
                "support": "If this continues, please contact support.",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": getattr(request.state, 'request_id', None)
            },
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache"
            }
        )
    
    # Performance-optimized web interface routes
    @app.get("/")
    async def serve_web_interface():
        """Serve the main web interface for ADHD users with performance optimization."""
        try:
            return FileResponse(
                path="static/index.html",
                media_type="text/html",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Content-Type-Options": "nosniff",  # Security optimization
                    "X-Frame-Options": "DENY"  # Security optimization
                }
            )
        except FileNotFoundError:
            # Return basic HTML if static files not available
            return JSONResponse(
                content={"message": "MCP ADHD Server is running", "version": __version__},
                headers={"Cache-Control": "no-cache"}
            )
        except Exception as e:
            try:
                health_monitor.record_error("serve_web_interface", str(e)[:100])
            except Exception:
                pass
            raise HTTPException(status_code=500, detail="Web interface unavailable")
    
    @app.get("/dashboard")
    async def serve_dashboard():
        """Serve the ADHD-optimized dashboard interface with performance caching."""
        try:
            return FileResponse(
                path="static/dashboard.html", 
                media_type="text/html",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "X-Content-Type-Options": "nosniff"
                }
            )
        except FileNotFoundError:
            return JSONResponse(
                content={"message": "Dashboard not available in this deployment"},
                status_code=404
            )
        except Exception as e:
            try:
                health_monitor.record_error("serve_dashboard", str(e)[:100])
            except Exception:
                pass
            raise HTTPException(status_code=500, detail="Dashboard unavailable")
    
    @app.get("/favicon.ico")
    async def favicon():
        """Serve favicon with aggressive caching for performance."""
        try:
            return FileResponse(
                path="static/favicon.ico",
                media_type="image/x-icon",
                headers={
                    "Cache-Control": f"public, max-age={perf_config.static_cache_ttl}",
                    "ETag": f'"{__version__}"'  # Version-based etag
                }
            )
        except FileNotFoundError:
            try:
                return FileResponse(
                    path="static/favicon.svg",
                    media_type="image/svg+xml",
                    headers={"Cache-Control": f"public, max-age={perf_config.static_cache_ttl}"}
                )
            except FileNotFoundError:
                # Return 204 No Content instead of 404 for favicon
                return JSONResponse(content=None, status_code=204)
    
    @app.get("/api")
    async def api_info():
        """API information with performance optimization and conditional features."""
        base_info = {
            "name": "MCP ADHD Server API",
            "version": __version__,
            "description": "Meta-Cognitive Protocol server for ADHD executive function support",
            "performance_optimized": True,
            "adhd_friendly": True
        }
        
        # Only include documentation links in debug mode for performance
        if settings.DEBUG:
            base_info["documentation"] = {
                "openapi": "/openapi.json",
                "swagger_ui": "/docs",
                "redoc": "/redoc"
            }
        
        base_info["endpoints"] = {
            "health": "/health",
            "metrics": "/metrics", 
            "chat": "/chat",
            "authentication": "/api/auth",
            "beta": "/api/beta",
            "performance": "/api/performance"
        }
        
        # Add evolution endpoint only if enabled
        if should_enable_service('evolution_engine'):
            base_info["endpoints"]["evolution"] = "/api/evolution"
            base_info["websockets"] = {"evolution": "/api/evolution/ws"}
            
        # Add github endpoint only if enabled
        if should_enable_service('github_automation'):
            base_info["endpoints"]["github"] = "/api/github"
        
        return JSONResponse(
            content=base_info,
            headers={"Cache-Control": f"public, max-age={perf_config.health_cache_ttl}"}
        )
    
    # Record app creation time
    app_creation_time = time.perf_counter() - app_creation_start
    _startup_metrics['stages']['app_creation'] = app_creation_time
    
    # Store performance configuration in app state
    app.state.performance_config = perf_config
    
    logger = structlog.get_logger(__name__)
    logger.info("Application factory completed", 
               creation_time=f"{app_creation_time:.3f}s",
               lazy_loading_enabled=perf_config.lazy_import_enabled)
    
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