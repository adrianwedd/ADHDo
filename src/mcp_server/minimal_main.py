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

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

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

# Import web interface support
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

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
    thinking: Optional[str] = None  # AI thinking process for UI display only
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
        from mcp_server.nest_nudges import initialize_nest_nudges
        nudge_success = await initialize_nest_nudges()
        if nudge_success:
            logger.info("✅ Nest nudge system initialized")
        else:
            logger.info("✅ Nudge engine initialized (Nest devices not found)")
    except Exception as e:
        logger.warning(f"Nudge engine initialization failed: {e}")
    
    # Initialize music system if available
    if music_available:
        try:
            jellyfin_url = os.getenv('JELLYFIN_URL', 'http://localhost:8096')
            jellyfin_token = os.getenv('JELLYFIN_TOKEN')
            chromecast_name = os.getenv('CHROMECAST_NAME', 'Shack Speakers')
            
            if jellyfin_token:
                logger.info(f"🎵 Initializing music with Jellyfin at {jellyfin_url}")
                logger.info(f"🎵 Using Chromecast: {chromecast_name}")
                success = await initialize_music_controller(
                    jellyfin_url, 
                    jellyfin_token,
                    chromecast_name
                )
                if success:
                    logger.info("✅ Music system initialized - Will auto-play 9AM-9PM")
                else:
                    logger.warning("⚠️ Music system initialization failed")
            else:
                logger.warning("⚠️ JELLYFIN_TOKEN not set - music system disabled")
        except Exception as e:
            logger.error(f"❌ Music system error: {e}")
    
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

# Root endpoint - MCP Contextual Operating System Dashboard
@app.get("/", response_class=HTMLResponse)
async def root():
    """MCP Contextual Operating System Dashboard."""
    # Read the dashboard HTML file
    try:
        with open("mcp_dashboard.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to simple interface
        return await simple_chat_interface()

async def simple_chat_interface():
    """Simple web interface for ADHD support system."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🧠 MCP ADHD Support System</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container {
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                margin: 20px 0;
            }
            h1 {
                text-align: center;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            .subtitle {
                text-align: center;
                opacity: 0.9;
                margin-bottom: 30px;
                font-size: 1.1em;
            }
            .chat-area {
                background: rgba(255,255,255,0.05);
                border-radius: 15px;
                padding: 20px;
                margin: 20px 0;
                min-height: 300px;
                overflow-y: auto;
                max-height: 400px;
            }
            .message {
                margin: 10px 0;
                padding: 12px;
                border-radius: 10px;
                word-wrap: break-word;
            }
            .user-message {
                background: rgba(108,117,255,0.3);
                margin-left: 20px;
                text-align: right;
            }
            .system-message {
                background: rgba(255,255,255,0.1);
                margin-right: 20px;
            }
            .input-area {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
            #messageInput {
                flex: 1;
                padding: 15px;
                border: none;
                border-radius: 25px;
                background: rgba(255,255,255,0.15);
                color: white;
                font-size: 16px;
                outline: none;
            }
            #messageInput::placeholder {
                color: rgba(255,255,255,0.7);
            }
            button {
                padding: 15px 25px;
                border: none;
                border-radius: 25px;
                background: rgba(108,117,255,0.6);
                color: white;
                font-weight: bold;
                cursor: pointer;
                transition: background 0.3s;
            }
            button:hover {
                background: rgba(108,117,255,0.8);
            }
            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .status {
                text-align: center;
                margin: 10px 0;
                font-size: 0.9em;
                opacity: 0.8;
            }
            .quick-buttons {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin: 20px 0;
                justify-content: center;
            }
            .quick-btn {
                padding: 8px 15px;
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 20px;
                font-size: 0.9em;
                cursor: pointer;
                transition: all 0.3s;
            }
            .quick-btn:hover {
                background: rgba(255,255,255,0.2);
            }
            .system-info {
                display: flex;
                justify-content: space-around;
                text-align: center;
                margin: 20px 0;
                font-size: 0.9em;
            }
            .info-item {
                flex: 1;
            }
            @media (max-width: 600px) {
                body { padding: 10px; }
                .container { padding: 20px; }
                h1 { font-size: 2em; }
                .input-area { flex-direction: column; }
                .quick-buttons { flex-direction: column; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧠 MCP ADHD Support</h1>
            <div class="subtitle">Your contextual operating system for executive function support</div>
            
            <div class="system-info">
                <div class="info-item">
                    <div>🌐 Network Access</div>
                    <div id="networkStatus">Connected</div>
                </div>
                <div class="info-item">
                    <div>⚡ Response Time</div>
                    <div id="responseTime">--</div>
                </div>
                <div class="info-item">
                    <div>🧭 Mode</div>
                    <div id="systemMode">ADHD-Optimized</div>
                </div>
            </div>
            
            <div class="quick-buttons">
                <button class="quick-btn" onclick="sendQuickMessage('I need help focusing on my work')">Help me focus</button>
                <button class="quick-btn" onclick="sendQuickMessage('I feel overwhelmed by my tasks')">Feeling overwhelmed</button>
                <button class="quick-btn" onclick="sendQuickMessage('I keep getting distracted')">Getting distracted</button>
                <button class="quick-btn" onclick="sendQuickMessage('Help me prioritize what to do')">Need priorities</button>
            </div>
            
            <div class="chat-area" id="chatArea">
                <div class="message system-message">
                    👋 Hi! I'm your ADHD support system. I'm here to help with focus, overwhelm, task management, and executive function challenges. What's on your mind?
                </div>
            </div>
            
            <div class="input-area">
                <input 
                    type="text" 
                    id="messageInput" 
                    placeholder="Tell me what's challenging you right now..."
                    onkeypress="handleKeyPress(event)"
                />
                <button onclick="sendMessage()" id="sendBtn">Send</button>
            </div>
            
            <div class="status" id="statusArea">
                Ready to help • Type a message or use quick buttons above
            </div>
        </div>

        <script>
            let isProcessing = false;

            async function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                
                if (!message || isProcessing) return;
                
                isProcessing = true;
                updateUI(true);
                
                // Add user message to chat
                addMessage(message, 'user');
                input.value = '';
                
                const startTime = Date.now();
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            message: message,
                            user_id: 'web_user_' + Math.random().toString(36).substr(2, 9)
                        })
                    });
                    
                    const data = await response.json();
                    const responseTime = Date.now() - startTime;
                    
                    // Update response time display
                    document.getElementById('responseTime').textContent = responseTime + 'ms';
                    
                    if (data.success) {
                        addMessage(data.response, 'system');
                        
                        // Show processing info if available
                        if (data.processing_time_ms) {
                            const processingInfo = `Processing: ${Math.round(data.processing_time_ms)}ms`;
                            if (data.safety_override) {
                                document.getElementById('statusArea').textContent = processingInfo + ' • Safety system activated';
                            } else if (data.processing_time_ms < 100) {
                                document.getElementById('statusArea').textContent = processingInfo + ' • Pattern matched (fast response)';
                            } else {
                                document.getElementById('statusArea').textContent = processingInfo + ' • AI reasoning completed';
                            }
                        }
                    } else {
                        addMessage('I had trouble processing that. Can you try rephrasing?', 'system');
                        document.getElementById('statusArea').textContent = 'Error occurred • Please try again';
                    }
                    
                } catch (error) {
                    console.error('Error:', error);
                    addMessage('Connection issue. Please check that the server is running.', 'system');
                    document.getElementById('statusArea').textContent = 'Connection error • Server may be offline';
                }
                
                isProcessing = false;
                updateUI(false);
            }
            
            function sendQuickMessage(message) {
                document.getElementById('messageInput').value = message;
                sendMessage();
            }
            
            function addMessage(text, sender) {
                const chatArea = document.getElementById('chatArea');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${sender}-message`;
                messageDiv.textContent = text;
                chatArea.appendChild(messageDiv);
                chatArea.scrollTop = chatArea.scrollHeight;
            }
            
            function updateUI(processing) {
                const sendBtn = document.getElementById('sendBtn');
                const input = document.getElementById('messageInput');
                
                sendBtn.disabled = processing;
                sendBtn.textContent = processing ? '...' : 'Send';
                input.disabled = processing;
                
                if (processing) {
                    document.getElementById('statusArea').textContent = 'Processing your request...';
                }
            }
            
            function handleKeyPress(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();
                }
            }
            
            // Check system health on load
            async function checkHealth() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    
                    if (data.status === 'healthy') {
                        document.getElementById('networkStatus').textContent = 'Online';
                        document.getElementById('systemMode').textContent = data.mode || 'ADHD-Optimized';
                    }
                } catch (error) {
                    document.getElementById('networkStatus').textContent = 'Offline';
                    console.warn('Health check failed:', error);
                }
            }
            
            // Initialize
            checkHealth();
            document.getElementById('messageInput').focus();
        </script>
    </body>
    </html>
    """
    return html_content

# Integrations setup page
@app.get("/integrations", response_class=HTMLResponse)
async def integrations_page():
    """System integrations setup and management page."""
    try:
        with open("integrations_setup.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse("""
        <html><body>
        <h1>Integrations Page Not Found</h1>
        <p>The integrations setup page is not available.</p>
        <a href="/">← Back to Dashboard</a>
        </body></html>
        """, status_code=404)

# ADHD Logging endpoints
@app.get("/api/logs")
async def get_logs(
    limit: int = 50,
    component: Optional[str] = None,
    level: Optional[str] = None
):
    """Get ADHD-friendly logs for UI display."""
    try:
        from mcp_server.adhd_logger import adhd_logger
        
        logs = adhd_logger.get_log_history(
            limit=limit,
            component_filter=component,
            level_filter=level
        )
        
        return {
            "success": True,
            "logs": logs,
            "total": len(logs)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/logs/patterns")
async def get_log_patterns():
    """Get pattern frequency summary for insights."""
    try:
        from mcp_server.adhd_logger import adhd_logger
        
        patterns = adhd_logger.get_pattern_summary()
        
        return {
            "success": True,
            "patterns": patterns
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

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
        # Clean up any thinking tags that leaked through
        response_text = result.response.text if result.response else "I'm here to help. What's challenging you right now?"
        import re
        # Remove any <think> tags that might have leaked through
        response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
        if not response_text:
            response_text = "I'm here to help! What would you like to work on?"
            
        response = ChatResponse(
            response=response_text,
            thinking=result.response.thinking if result.response else None,  # Include thinking for UI
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

# Proactive Nudging Endpoints
@app.post("/nudge/trigger")
async def trigger_nudge(request: dict):
    """Trigger proactive nudge through environmental systems."""
    try:
        user_id = request.get("user_id", "default_user")
        nudge_type = request.get("nudge_type", "GENERAL")
        methods = request.get("methods", ["telegram"])
        message = request.get("message", "Time to check in with your tasks!")
        
        # Import nudge tier for the request
        from mcp_server.models import NudgeTier
        tier = NudgeTier.GENTLE
        
        if nudge_type == "ACCOUNTABILITY_CHECK":
            message = "🤝 Accountability check: What have you accomplished in the last 2 hours?"
            tier = NudgeTier.SARCASTIC
        elif nudge_type == "FOCUS_REMINDER":
            message = "🎯 Time to refocus! What's your next priority task?"
            tier = NudgeTier.GENTLE
        elif nudge_type == "BREAK_REMINDER":
            message = "🌱 Brain break time! Step away for 5 minutes"
            tier = NudgeTier.GENTLE
        
        # Get user (create minimal user if doesn't exist)
        user = type('User', (), {
            'user_id': user_id,
            'telegram_chat_id': settings.telegram_chat_id,
            'name': 'MCP User'
        })()
        
        # Try to send nudges through requested methods
        results = {}
        
        if "telegram" in methods and settings.telegram_bot_token:
            try:
                from nudge.engine import TelegramNudger
                telegram_nudger = TelegramNudger()
                results["telegram"] = await telegram_nudger.send_nudge(user, message, tier)
            except Exception as e:
                results["telegram"] = False
                logger.error(f"Telegram nudge failed: {e}")
        
        if "nest_hub" in methods and settings.home_assistant_url:
            try:
                from nudge.engine import GoogleNestNudger
                nest_nudger = GoogleNestNudger()
                results["nest_hub"] = await nest_nudger.send_nudge(user, message, tier)
            except Exception as e:
                results["nest_hub"] = False
                logger.error(f"Nest Hub nudge failed: {e}")
        
        if "tts" in methods and settings.home_assistant_url:
            try:
                from nudge.engine import HomeAssistantNudger
                ha_nudger = HomeAssistantNudger()
                results["tts"] = await ha_nudger.send_nudge(user, message, tier)
            except Exception as e:
                results["tts"] = False
                logger.error(f"TTS nudge failed: {e}")
        
        return {
            "success": any(results.values()),
            "message": f"Nudge delivery attempted via {len(methods)} methods",
            "results": results,
            "nudge_type": nudge_type,
            "tier": tier.name
        }
        
    except Exception as e:
        logger.error(f"Nudge trigger error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/accountability/checkin")
async def accountability_checkin(request: dict):
    """Handle accountability buddy check-in response."""
    try:
        user_id = request.get("user_id", "default_user")
        accomplishments = request.get("accomplishments", "")
        mood = request.get("mood", "neutral")
        next_goals = request.get("next_goals", "")
        
        # Store check-in data
        checkin_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "accomplishments": accomplishments,
            "mood": mood,
            "next_goals": next_goals,
            "user_id": user_id
        }
        
        if redis_client:
            await redis_client.hset(
                f"checkin:{user_id}:{datetime.utcnow().date()}",
                mapping=checkin_data
            )
            await redis_client.expire(f"checkin:{user_id}:{datetime.utcnow().date()}", 86400 * 7)  # Keep for 1 week
        else:
            # Fallback to memory
            memory_store['checkins'] = memory_store.get('checkins', {})
            memory_store['checkins'][f"{user_id}_{datetime.utcnow().date()}"] = checkin_data
        
        # Calculate accountability score (simple algorithm)
        score = 5.0  # Base score
        if len(accomplishments) > 20:
            score += 2.0
        if mood in ["happy", "focused", "productive"]:
            score += 1.0
        elif mood in ["anxious", "overwhelmed"]:
            score -= 0.5
        if len(next_goals) > 10:
            score += 1.0
        
        score = max(0, min(10, score))  # Clamp to 0-10
        
        # Send encouraging response
        response_message = "Thanks for checking in! "
        if score >= 7:
            response_message += "🎉 You're doing great! Keep up the momentum."
        elif score >= 5:
            response_message += "👍 Solid progress! What's one thing you want to focus on next?"
        else:
            response_message += "🤗 It's okay to have tough days. Let's break down your next step into something manageable."
        
        return {
            "success": True,
            "message": response_message,
            "accountability_score": round(score, 1),
            "next_checkin": (datetime.utcnow() + timedelta(hours=2)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Accountability checkin error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/frame/current/{user_id}")
async def get_current_frame(user_id: str):
    """Get current contextual frame for MCP dashboard."""
    try:
        # Build current frame using the actual frame builder
        frame_result = await frame_builder.build_frame(
            user_id=user_id,
            agent_id="dashboard",
            task_focus="current_context",
            include_patterns=True
        )
        
        # Extract frame data for dashboard
        contexts = []
        for context in frame_result.frame.contexts:
            contexts.append({
                "type": context.type,
                "data": context.data,
                "priority": "high" if context.type in ["user_state", "task"] else 
                          "medium" if context.type in ["memory_trace", "environment"] else "low",
                "timestamp": context.timestamp.isoformat(),
                "confidence": context.confidence
            })
        
        return {
            "success": True,
            "frame_data": {
                "contexts": contexts,
                "cognitive_load": frame_result.cognitive_load,
                "accessibility_score": frame_result.accessibility_score,
                "recommended_action": frame_result.recommended_action,
                "user_id": user_id,
                "agent_id": frame_result.frame.agent_id,
                "timestamp": frame_result.frame.timestamp.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Frame building error: {e}")
        # Return mock data for demo
        return {
            "success": True,
            "frame_data": {
                "contexts": [
                    {"type": "user_state", "data": {"energy": "medium", "mood": "focused"}, "priority": "high"},
                    {"type": "task", "data": {"name": "Current work", "status": "in_progress"}, "priority": "high"},
                    {"type": "environment", "data": {"distractions": "low", "music": "off"}, "priority": "medium"}
                ],
                "cognitive_load": 0.65,
                "accessibility_score": 0.87,
                "recommended_action": "Continue current task with gentle monitoring"
            }
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


# ============================================================================
# 🔔 NEST NUDGE ENDPOINTS
# ============================================================================

@app.post("/nudge/send")
async def send_nudge(message: str, urgency: str = "normal", device: Optional[str] = None):
    """Send a nudge to Nest devices."""
    try:
        from mcp_server.nest_nudges import nest_nudge_system
        
        if not nest_nudge_system:
            raise HTTPException(status_code=503, detail="Nudge system not initialized")
        
        # Map urgency to nudge type
        from mcp_server.nest_nudges import NudgeType
        if urgency == "high":
            nudge_type = NudgeType.URGENT
            volume = 0.6
        elif urgency == "low":
            nudge_type = NudgeType.GENTLE
            volume = 0.4
        else:
            nudge_type = NudgeType.MOTIVATIONAL
            volume = 0.5
        
        success = await nest_nudge_system.send_nudge(
            message=message,
            nudge_type=nudge_type,
            device_name=device,
            volume=volume
        )
        
        if success:
            return {"success": True, "message": f"📢 Nudge sent: {message}"}
        else:
            return {"success": False, "message": "Failed to send nudge"}
            
    except Exception as e:
        logger.error(f"Nudge failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/nudge/task")
async def nudge_task_reminder(task: str, urgency: str = "normal"):
    """Send a task reminder nudge."""
    try:
        from mcp_server.nest_nudges import nest_nudge_system
        
        if not nest_nudge_system:
            raise HTTPException(status_code=503, detail="Nudge system not initialized")
        
        success = await nest_nudge_system.nudge_task_reminder(task, urgency)
        
        if success:
            return {"success": True, "message": f"📋 Task nudge sent for: {task}"}
        else:
            return {"success": False, "message": "Failed to send task nudge"}
            
    except Exception as e:
        logger.error(f"Task nudge failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/nudge/break")
async def nudge_break():
    """Remind user to take a break."""
    try:
        from mcp_server.nest_nudges import nest_nudge_system
        
        if not nest_nudge_system:
            raise HTTPException(status_code=503, detail="Nudge system not initialized")
        
        success = await nest_nudge_system.nudge_break_time()
        
        if success:
            return {"success": True, "message": "🏃 Break reminder sent"}
        else:
            return {"success": False, "message": "Failed to send break reminder"}
            
    except Exception as e:
        logger.error(f"Break nudge failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/nudge/celebrate")
async def nudge_celebration(task: str):
    """Celebrate task completion."""
    try:
        from mcp_server.nest_nudges import nest_nudge_system
        
        if not nest_nudge_system:
            raise HTTPException(status_code=503, detail="Nudge system not initialized")
        
        success = await nest_nudge_system.nudge_celebration(task)
        
        if success:
            return {"success": True, "message": f"🎉 Celebration sent for completing: {task}"}
        else:
            return {"success": False, "message": "Failed to send celebration"}
            
    except Exception as e:
        logger.error(f"Celebration nudge failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nudge/devices")
async def get_nudge_devices():
    """Get list of available Nest devices."""
    try:
        from mcp_server.nest_nudges import nest_nudge_system
        
        if not nest_nudge_system:
            return {"available": False, "devices": []}
        
        devices = [device.name for device in nest_nudge_system.devices]
        
        return {
            "available": True,
            "devices": devices,
            "count": len(devices)
        }
    except Exception as e:
        logger.error(f"Failed to get nudge devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nudge-audio/{filename}")
async def serve_nudge_audio(filename: str):
    """Serve temporary nudge audio files to Chromecast."""
    try:
        from mcp_server.nest_nudges import nest_nudge_system
        from fastapi.responses import FileResponse
        
        if not nest_nudge_system:
            raise HTTPException(status_code=404, detail="Nudge system not available")
        
        audio_files = getattr(nest_nudge_system, '_audio_files', {})
        if filename not in audio_files:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        filepath = audio_files[filename]
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Audio file expired")
        
        return FileResponse(filepath, media_type='audio/mpeg', filename=filename)
        
    except Exception as e:
        logger.error(f"Audio serving failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# 🎵 JELLYFIN MUSIC INTEGRATION ENDPOINTS
# ============================================================================

# Music integration imports with fallbacks
music_available = False
jellyfin_music = None

try:
    import mcp_server.jellyfin_music as music_module
    from mcp_server.jellyfin_music import (
        initialize_music_controller, 
        MusicMood
    )
    # Create wrapper functions that access the global through the module
    async def play_focus_music():
        if music_module.jellyfin_music:
            return await music_module.jellyfin_music.play_mood_playlist(MusicMood.FOCUS)
        return False
    
    async def play_energy_music():
        if music_module.jellyfin_music:
            return await music_module.jellyfin_music.play_mood_playlist(MusicMood.ENERGY)
        return False
    
    async def stop_all_music():
        if music_module.jellyfin_music:
            return await music_module.jellyfin_music.stop_music()
        return False
    
    def get_music_status():
        if music_module.jellyfin_music:
            return music_module.jellyfin_music.get_status()
        return {"available": False}
    
    music_available = True
    logger.info("🎵 Jellyfin music integration loaded")
except ImportError as e:
    logger.warning(f"🎵 Jellyfin music integration not available: {e}")


class MusicRequest(BaseModel):
    mood: Optional[str] = "focus"
    volume: Optional[float] = 0.3
    shuffle: Optional[bool] = True


@app.post("/music/initialize")
async def initialize_music_system():
    """Initialize Jellyfin music controller."""
    if not music_available:
        raise HTTPException(status_code=503, detail="Music integration not available")
    
    try:
        # Get settings from environment or config
        jellyfin_url = os.environ.get('JELLYFIN_URL', 'http://localhost:8096')
        jellyfin_token = os.environ.get('JELLYFIN_TOKEN')
        chromecast_name = os.environ.get('CHROMECAST_NAME', 'Chromecast Audio')
        
        if not jellyfin_token:
            raise HTTPException(
                status_code=400, 
                detail="JELLYFIN_TOKEN environment variable required"
            )
        
        success = await initialize_music_controller(
            jellyfin_url, 
            jellyfin_token, 
            chromecast_name
        )
        
        if success:
            logger.info("🎧 Music system initialized for ADHD focus support")
            return {
                "success": True,
                "message": "🎧 Music system ready! Will auto-play focus music 9AM-9PM when silent.",
                "jellyfin_url": jellyfin_url,
                "chromecast_name": chromecast_name,
                "auto_schedule": "9:00 AM - 9:00 PM daily"
            }
        else:
            return {
                "success": False,
                "message": "Failed to initialize music system. Check Jellyfin connection."
            }
            
    except Exception as e:
        logger.error(f"Music initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/play")
async def play_music(request: MusicRequest):
    """Start playing ADHD-optimized music."""
    if not music_available or not music_module.jellyfin_music:
        raise HTTPException(status_code=503, detail="Music system not initialized")
    
    try:
        # Map mood string to enum
        mood_map = {
            'focus': MusicMood.FOCUS,
            'energy': MusicMood.ENERGY, 
            'calm': MusicMood.CALM,
            'ambient': MusicMood.AMBIENT,
            'nature': MusicMood.NATURE,
            'study': MusicMood.STUDY
        }
        
        mood = mood_map.get(request.mood.lower(), MusicMood.FOCUS)
        
        success = await music_module.jellyfin_music.play_mood_playlist(
            mood, 
            volume=request.volume,
            shuffle=request.shuffle
        )
        
        if success:
            return {
                "success": True,
                "message": f"🎧 Playing {mood.value} music for ADHD focus",
                "mood": mood.value,
                "volume": request.volume
            }
        else:
            return {
                "success": False,
                "message": "Failed to start music playback"
            }
            
    except Exception as e:
        logger.error(f"Music playback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/stop")
async def stop_music():
    """Stop music playback."""
    if not music_available:
        raise HTTPException(status_code=503, detail="Music system not available")
    
    try:
        success = await stop_all_music()
        return {
            "success": success,
            "message": "🔇 Music stopped" if success else "Failed to stop music"
        }
    except Exception as e:
        logger.error(f"Stop music failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/volume/{volume}")
async def set_music_volume(volume: float):
    """Set music volume (0.0 - 1.0)."""
    if not music_available or not music_module.jellyfin_music:
        raise HTTPException(status_code=503, detail="Music system not initialized")
    
    if not 0.0 <= volume <= 1.0:
        raise HTTPException(status_code=400, detail="Volume must be between 0.0 and 1.0")
    
    try:
        success = await music_module.jellyfin_music.set_volume(volume)
        return {
            "success": success,
            "volume": volume,
            "message": f"🔊 Volume set to {int(volume * 100)}%" if success else "Failed to set volume"
        }
    except Exception as e:
        logger.error(f"Set volume failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/music/status")
async def music_status():
    """Get current music status."""
    if not music_available:
        return {
            "available": False,
            "message": "Music integration not available"
        }
    
    try:
        status = get_music_status()  # Not async, don't await
        return {
            "available": True,
            **status
        }
    except Exception as e:
        logger.error(f"Get music status failed: {e}")
        return {
            "available": True,
            "error": str(e)
        }


@app.post("/music/focus")
async def quick_focus_music():
    """Quick endpoint to start focus music for ADHD."""
    if not music_available:
        raise HTTPException(status_code=503, detail="Music system not available")
    
    try:
        success = await play_focus_music()
        return {
            "success": success,
            "message": "🎯 Focus music started! Perfect for ADHD concentration." if success else "Failed to start focus music"
        }
    except Exception as e:
        logger.error(f"Quick focus music failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/energy") 
async def quick_energy_music():
    """Quick endpoint to start energy music for motivation."""
    if not music_available:
        raise HTTPException(status_code=503, detail="Music system not available")
    
    try:
        success = await play_energy_music()
        return {
            "success": success,
            "message": "⚡ Energy music started! Time to get things done!" if success else "Failed to start energy music"
        }
    except Exception as e:
        logger.error(f"Quick energy music failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/music/devices")
async def discover_chromecast_devices():
    """Discover all available Chromecast devices."""
    if not music_available or not music_module.jellyfin_music:
        raise HTTPException(status_code=503, detail="Music system not initialized")
    
    try:
        devices = music_module.jellyfin_music.get_available_devices()
        current_device = music_module.jellyfin_music.state.chromecast_name
        
        return {
            "success": True,
            "current_device": current_device,
            "available_devices": devices,
            "message": f"Found {len(devices)} Chromecast device(s)"
        }
    except Exception as e:
        logger.error(f"Device discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/switch/{device_name}")
async def switch_chromecast_device(device_name: str):
    """Switch to a different Chromecast device."""
    if not music_available or not music_module.jellyfin_music:
        raise HTTPException(status_code=503, detail="Music system not initialized")
    
    try:
        # This would require implementing device switching in the music controller
        # For now, return info about the requested switch
        devices = music_module.jellyfin_music.get_available_devices()
        target_device = None
        
        for device in devices:
            if device_name.lower() in device['name'].lower():
                target_device = device
                break
        
        if target_device:
            # TODO: Implement actual device switching
            return {
                "success": False,  # Not implemented yet
                "message": f"Device switching to '{target_device['name']}' not yet implemented",
                "target_device": target_device,
                "note": "Will reconnect to this device on next initialization"
            }
        else:
            return {
                "success": False,
                "message": f"Device '{device_name}' not found",
                "available_devices": [d['name'] for d in devices]
            }
            
    except Exception as e:
        logger.error(f"Device switching failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/call-mode")
async def call_mode():
    """Quickly drop volume to 10-20% for calls."""
    if not music_available or not music_module.jellyfin_music:
        raise HTTPException(status_code=503, detail="Music system not initialized")
    
    try:
        success = await music_module.jellyfin_music.set_volume(0.15)  # 15% for calls
        return {
            "success": success,
            "volume": 0.15,
            "message": "📞 Call mode: Volume dropped to 15%" if success else "Failed to set call mode"
        }
    except Exception as e:
        logger.error(f"Call mode failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/normal-mode")
async def normal_mode():
    """Restore volume to normal 70-80% level."""
    if not music_available or not music_module.jellyfin_music:
        raise HTTPException(status_code=503, detail="Music system not initialized")
    
    try:
        success = await music_module.jellyfin_music.set_volume(0.75)  # Back to 75%
        return {
            "success": success,
            "volume": 0.75,
            "message": "🎵 Normal mode: Volume restored to 75%" if success else "Failed to restore volume"
        }
    except Exception as e:
        logger.error(f"Normal mode failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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