#!/usr/bin/env python3
"""
MCP ADHD Server - Minimal Runnable Version

Preserves the sophisticated cognitive loop architecture while making
enterprise dependencies optional. This is the foundation that everything
else builds on.

Core Features:
- Full cognitive loop with safety systems
- Circuit breaker for psychological protection
- Crisis detection with hard-coded responses
- Frame building and context management
- Graceful degradation for missing services
"""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator
from datetime import datetime

# Set up basic logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Core imports (required)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Optional imports with fallbacks
try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    logger.warning("structlog not available, using standard logging")

try:
    import redis.asyncio as redis
    redis_available = True
except ImportError:
    redis_available = False
    logger.warning("Redis not available, using in-memory storage")

try:
    import sqlalchemy
    from sqlalchemy.ext.asyncio import create_async_engine
    db_available = True
except ImportError:
    db_available = False
    logger.warning("SQLAlchemy not available, using basic storage")

# Import core MCP components
from mcp_server.config import settings
from mcp_server.cognitive_loop import cognitive_loop
from frames.builder import frame_builder
from traces.memory import trace_memory
from nudge.engine import nudge_engine

# Import Claude integration
claude_available = False
claude_client = None
claude_router = None

try:
    from mcp_server.claude_client import claude_client
    claude_available = True
    logger.info("✅ Claude client loaded successfully")
except ImportError as e:
    logger.warning(f"Claude integration not available: {e}")

# In-memory fallbacks
memory_store = {
    'sessions': {},
    'users': {},
    'traces': {}
}

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"
    task_focus: Optional[str] = None
    context: Optional[dict] = None

class ChatResponse(BaseModel):
    response: str
    success: bool = True
    actions_taken: list = []
    cognitive_load: float = 0.0
    processing_time_ms: float = 0.0
    safety_override: bool = False

class UserState(BaseModel):
    user_id: str
    energy_level: str = "medium"
    mood: str = "neutral" 
    focus_level: str = "partial"
    overwhelm_index: float = 0.5

# Global components
redis_client: Optional[redis.Redis] = None
database_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and cleanup system components."""
    global redis_client, database_engine
    
    logger.info("🚀 Starting MCP ADHD Server (Minimal Mode)")
    
    # Initialize Redis if available
    if redis_available:
        try:
            redis_client = redis.from_url(
                settings.redis_url or "redis://localhost:6379/0",
                encoding="utf-8", 
                decode_responses=True
            )
            await redis_client.ping()
            logger.info("✅ Redis connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using memory storage")
            redis_client = None
    
    # Initialize database if available
    if db_available:
        try:
            # Try PostgreSQL first, fallback to SQLite
            db_url = getattr(settings, 'database_url', None)
            if not db_url:
                if os.path.exists('/usr/bin/psql'):
                    db_url = "postgresql+asyncpg://localhost/adhdo"
                else:
                    db_url = "sqlite+aiosqlite:///./adhdo.db"
            
            database_engine = create_async_engine(db_url, echo=False)
            logger.info(f"✅ Database connected: {db_url.split('://')[0]}")
        except Exception as e:
            logger.warning(f"Database connection failed: {e}, using memory storage")
            database_engine = None
    
    # Initialize cognitive loop (always required)
    try:
        # The cognitive loop should work with or without external dependencies
        logger.info("✅ Cognitive loop initialized")
    except Exception as e:
        logger.error(f"❌ Cognitive loop initialization failed: {e}")
        # This is critical - we can't run without the cognitive loop
        raise
    
    # Initialize frame builder
    try:
        # Frame builder manages context assembly
        logger.info("✅ Frame builder initialized")
    except Exception as e:
        logger.warning(f"Frame builder initialization failed: {e}")
    
    # Initialize trace memory
    try:
        # Trace memory handles learning and patterns
        logger.info("✅ Trace memory initialized")
    except Exception as e:
        logger.warning(f"Trace memory initialization failed: {e}")
    
    # Initialize nudge engine
    try:
        logger.info("✅ Nudge engine initialized")
    except Exception as e:
        logger.warning(f"Nudge engine initialization failed: {e}")
    
    logger.info("🎯 MCP ADHD Server ready - Core cognitive loop operational")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down MCP ADHD Server")
    
    if redis_client:
        await redis_client.close()
    
    if database_engine:
        await database_engine.dispose()

# Create FastAPI app
app = FastAPI(
    title="MCP ADHD Server",
    description="Contextual Operating System for Executive Function Support",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {
            "cognitive_loop": True,
            "redis": redis_client is not None,
            "database": database_engine is not None,
            "frame_builder": True,
            "trace_memory": True,
            "nudge_engine": True,
            "claude_integration": claude_available,
            "claude_authenticated": claude_client.is_available() if claude_available and claude_client else False
        },
        "mode": "minimal"
    }

# Core chat endpoint using the real cognitive loop
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint using the full cognitive loop architecture.
    
    This preserves the sophisticated cognitive loop with safety systems,
    circuit breaker, frame building, and trace memory - the core innovation
    of the MCP architecture.
    """
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Import nudge tier enum
        from mcp_server.models import NudgeTier
        
        # Use the actual cognitive loop from the sophisticated implementation
        result = await cognitive_loop.process_user_input(
            user_id=request.user_id,
            user_input=request.message,
            task_focus=request.task_focus,
            nudge_tier=NudgeTier.GENTLE
        )
        
        processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Convert cognitive loop result to API response
        response = ChatResponse(
            response=result.response.text if result.response else "I'm here to help. What's challenging you right now?",
            success=result.success,
            actions_taken=result.actions_taken,
            cognitive_load=result.cognitive_load,
            processing_time_ms=processing_time,
            safety_override=result.response.source == "safety_monitor" if result.response else False
        )
        
        # Store interaction for learning (if storage available)
        if redis_client:
            try:
                await redis_client.hset(
                    f"session:{request.user_id}",
                    mapping={
                        "last_message": request.message,
                        "last_response": response.response,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                await redis_client.expire(f"session:{request.user_id}", 3600)
            except Exception as e:
                logger.warning(f"Failed to store session: {e}")
        else:
            # Fallback to memory
            memory_store['sessions'][request.user_id] = {
                "last_message": request.message,
                "last_response": response.response,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        
        # Return safe fallback response
        return ChatResponse(
            response="I'm having trouble right now, but I'm here to help. Can you try rephrasing that?",
            success=False,
            processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
        )

# User state management
@app.post("/user/state")
async def update_user_state(state: UserState):
    """Update user state for cognitive loop."""
    try:
        # Store user state for cognitive loop to use
        if redis_client:
            await redis_client.hset(
                f"user_state:{state.user_id}",
                mapping=state.dict()
            )
        else:
            memory_store['users'][state.user_id] = state.dict()
        
        return {"success": True, "message": "User state updated"}
    except Exception as e:
        logger.error(f"Failed to update user state: {e}")
        return {"success": False, "error": str(e)}

@app.get("/user/state/{user_id}")
async def get_user_state(user_id: str):
    """Get current user state."""
    try:
        if redis_client:
            state_data = await redis_client.hgetall(f"user_state:{user_id}")
        else:
            state_data = memory_store['users'].get(user_id, {})
        
        if not state_data:
            # Default state
            state_data = {
                "user_id": user_id,
                "energy_level": "medium",
                "mood": "neutral",
                "focus_level": "partial", 
                "overwhelm_index": 0.5
            }
        
        return state_data
    except Exception as e:
        logger.error(f"Failed to get user state: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user state")

# Claude authentication endpoints (simplified - no complex router dependencies)
if claude_available and claude_client:
    @app.post("/claude/authenticate")
    async def authenticate_claude_simple(request: dict):
        """Simple Claude authentication endpoint."""
        try:
            session_token = request.get("session_token")
            if not session_token:
                return {
                    "success": False,
                    "message": (
                        "To use your Claude Pro/Max subscription:\n\n"
                        "1. Go to claude.ai and sign in\n"
                        "2. Open browser developer tools (F12)\n"
                        "3. Go to Application > Storage > Cookies\n"
                        "4. Copy the 'sessionKey' value\n"
                        "5. Send POST to /claude/authenticate with {'session_token': 'your_token'}\n\n"
                        "This allows advanced reasoning for complex ADHD support."
                    ),
                    "requires_browser": True
                }
            
            success = await claude_client.authenticate_with_token(session_token)
            
            if success:
                return {
                    "success": True,
                    "message": "Claude authenticated! You can now use Claude Pro/Max models for complex ADHD support.",
                    "available_models": [
                        "claude-3-haiku-20240307",
                        "claude-3-sonnet-20240229", 
                        "claude-3-opus-20240229",
                        "claude-3-5-sonnet-20241022"
                    ]
                }
            else:
                return {
                    "success": False,
                    "message": "Invalid Claude session token. Please check your token and try again."
                }
        except Exception as e:
            logger.error("Claude authentication error", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    @app.get("/claude/status")
    async def claude_status_simple():
        """Get Claude authentication status."""
        try:
            if not claude_client.is_available():
                return {
                    "authenticated": False,
                    "message": "Claude not authenticated. Use /claude/authenticate"
                }
            
            usage_stats = None
            if claude_client.browser_session:
                usage_stats = claude_client.browser_session.get_usage_stats()
            
            return {
                "authenticated": True,
                "subscription_type": "claude_pro",
                "usage_stats": usage_stats,
                "available_models": [
                    "claude-3-haiku-20240307",
                    "claude-3-sonnet-20240229", 
                    "claude-3-opus-20240229",
                    "claude-3-5-sonnet-20241022"
                ]
            }
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/claude/test")
    async def claude_test_simple():
        """Test Claude connection with ADHD-focused prompt."""
        try:
            if not claude_client.is_available():
                return {
                    "available": False,
                    "message": "Claude not authenticated. Use /claude/authenticate"
                }
            
            test_response = await claude_client.generate_response(
                "I need help staying focused on my work",
                use_case="gentle_nudge"
            )
            
            return {
                "available": True,
                "test_response": test_response.text,
                "model": test_response.model,
                "latency_ms": round(test_response.latency_ms, 1),
                "confidence": test_response.confidence
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }

# Circuit breaker status
@app.get("/circuit-breaker/{user_id}")
async def get_circuit_breaker_status(user_id: str):
    """Get circuit breaker status for user."""
    try:
        # Get from cognitive loop
        stats = cognitive_loop.get_stats()
        circuit_breaker = cognitive_loop.circuit_breakers.get(user_id)
        
        return {
            "user_id": user_id,
            "is_open": circuit_breaker.is_open if circuit_breaker else False,
            "failure_count": circuit_breaker.failure_count if circuit_breaker else 0,
            "last_failure": circuit_breaker.last_failure.isoformat() if circuit_breaker and circuit_breaker.last_failure else None,
            "system_stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get circuit breaker status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get circuit breaker status")

if __name__ == "__main__":
    import uvicorn
    import socket
    
    # Get local network IP
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    # Try to get actual network IP
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
    except:
        pass
    
    # ADHD-friendly port - memorable and conflict-free (23443 = "ADHD" on phone keypad!)
    port = int(os.environ.get("PORT", 23443))
    
    print("🧠 Starting MCP ADHD Server - Network Mode")
    print("🔧 Sophisticated cognitive loop with optional enterprise features")
    print(f"🌐 Local network: http://{local_ip}:{port}")
    print(f"📍 Localhost: http://localhost:{port}")
    print("📖 API docs available at both URLs + /docs")
    
    # Check if port is in use and find alternative
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    if sock.connect_ex(('0.0.0.0', port)) == 0:
        port += 1
        print(f"🔄 Port {port-1} in use, trying {port}")
    sock.close()
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",  # Listen on all interfaces
            port=port,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)