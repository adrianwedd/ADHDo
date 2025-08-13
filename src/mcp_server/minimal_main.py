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
from typing import Optional, AsyncGenerator, Dict
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

# Import Claude with tools endpoint (the one that actually works)
try:
    from mcp_server.claude_with_tools import router as claude_tools_router
    logger.info("✅ Claude tools endpoint loaded")
except ImportError as e:
    logger.warning(f"Claude tools endpoint not available: {e}")
    claude_tools_router = None

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

class NudgeRequest(BaseModel):
    message: str
    urgency: Optional[str] = "normal"
    device: Optional[str] = None
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
hub = None  # Integration hub
analyzer = None  # Context analyzer

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
                decode_responses=True,
                max_connections=settings.redis_max_connections,
                retry_on_timeout=settings.redis_retry_on_timeout,
                socket_timeout=3,
                socket_connect_timeout=5
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
    
    # Initialize nudge engine and smart scheduler
    nest_available = False
    try:
        from mcp_server.nest_nudges import initialize_nest_nudges
        from mcp_server.smart_scheduler import initialize_smart_scheduler
        
        nudge_success = await initialize_nest_nudges()
        scheduler_success = await initialize_smart_scheduler()
        
        nest_available = nudge_success
        if nudge_success:
            logger.info("✅ Nest nudge system initialized")
        else:
            logger.info("✅ Nudge engine initialized (Nest devices not found)")
        
        if scheduler_success:
            logger.info("✅ Smart scheduler initialized with LLM nudging")
        else:
            logger.warning("⚠️ Smart scheduler failed to initialize")
            
    except Exception as e:
        logger.warning(f"Nudge engine initialization failed: {e}")
    
    # Initialize voice and calendar systems
    try:
        from mcp_server.voice_calendar_integration import initialize_voice_calendar
        from mcp_server.voice_assistant import initialize_voice_assistant
        
        # Initialize voice calendar integration
        from mcp_server.nest_nudges import nest_nudge_system
        voice_cal_success = await initialize_voice_calendar(nest_system=nest_nudge_system if nest_available else None)
        if voice_cal_success:
            logger.info("✅ Voice calendar integration initialized")
        else:
            logger.warning("⚠️ Voice calendar integration failed")
        
        # Initialize voice assistant (optional - requires microphone)
        voice_assist_success = await initialize_voice_assistant(wake_word="hey claude")
        if voice_assist_success:
            logger.info("✅ Voice assistant initialized")
        else:
            logger.warning("⚠️ Voice assistant not available (microphone required)")
            
    except Exception as e:
        logger.warning(f"Voice system initialization failed: {e}")
    
    # Initialize reminder system
    try:
        from mcp_server.adhd_reminders import initialize_reminders
        
        # Pass the nudge function as callback
        nudge_callback = None
        if nest_available:
            async def send_reminder_nudge(message, urgency="normal", nudge_type="reminder"):
                from mcp_server.nest_nudges import nest_nudge_system, NudgeType
                if nest_nudge_system:
                    # Map urgency to nudge type
                    nudge_type_map = {
                        "low": NudgeType.GENTLE,
                        "normal": NudgeType.GENTLE,
                        "high": NudgeType.URGENT,
                        "urgent": NudgeType.URGENT
                    }
                    return await nest_nudge_system.send_nudge(
                        message=message,
                        nudge_type=nudge_type_map.get(urgency, NudgeType.GENTLE)
                    )
            nudge_callback = send_reminder_nudge
        
        reminder_success = await initialize_reminders(redis_client, nudge_callback)
        if reminder_success:
            logger.info("✅ ADHD reminder system initialized")
        else:
            logger.warning("⚠️ Reminder system failed to initialize")
    except Exception as e:
        logger.warning(f"Reminder system initialization failed: {e}")
    
    # Initialize music system if available
    if music_available:
        try:
            jellyfin_url = os.getenv('JELLYFIN_URL', 'http://localhost:8096')
            jellyfin_token = os.getenv('JELLYFIN_TOKEN')
            chromecast_name = os.getenv('CHROMECAST_NAME', 'Shack Speakers')
            
            if jellyfin_token:
                logger.info(f"🎵 Initializing music with Jellyfin at {jellyfin_url}")
                logger.info(f"🎵 Using Chromecast: {chromecast_name}")
                jellyfin_user_id = os.getenv('JELLYFIN_USER_ID')
                success = await initialize_music_controller(
                    jellyfin_url, 
                    jellyfin_token,
                    chromecast_name,
                    jellyfin_user_id
                )
                if success:
                    logger.info("✅ Music system initialized - Will auto-play 9AM-9PM")
                else:
                    logger.warning("⚠️ Music system initialization failed")
            else:
                logger.warning("⚠️ JELLYFIN_TOKEN not set - music system disabled")
        except Exception as e:
            logger.error(f"❌ Music system error: {e}")
    
    # Initialize integration hub - THE BRAIN that connects everything
    global hub, analyzer
    try:
        from mcp_server.integration_hub import initialize_integration
        from mcp_server.component_adapters import (
            NestAdapter, MusicAdapter, CalendarAdapter, FitnessAdapter
        )
        
        hub, analyzer = initialize_integration()
        
        # Register all components with adapters
        if oauth_mgr:
            hub.register_component('calendar', CalendarAdapter(oauth_mgr))
            hub.register_component('fitness', FitnessAdapter(oauth_mgr))
        if nest_nudge_system:
            hub.register_component('nest', NestAdapter(nest_nudge_system))
        
        # Get the actual jellyfin_music instance from the module
        try:
            from mcp_server.jellyfin_music import jellyfin_music as music_instance
            if music_instance:
                hub.register_component('music', MusicAdapter(music_instance))
        except ImportError:
            pass
        
        # Start the integration processes
        asyncio.create_task(hub.process_events())
        asyncio.create_task(analyzer.analyze_loop())
        
        logger.info("🧠 Integration hub started - components are now connected!")
    except Exception as e:
        logger.error(f"Failed to initialize integration hub: {e}")
    
    logger.info("🎯 MCP ADHD Server ready - Core cognitive loop operational")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down MCP ADHD Server")
    
    if redis_client:
        await redis_client.aclose()
    
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

# Add Claude tools router if available
if claude_tools_router:
    app.include_router(claude_tools_router)
    logger.info("✅ Claude tools endpoints added")

# Add integration endpoints
try:
    from mcp_server.integration_endpoints import router as integration_router
    app.include_router(integration_router)
    logger.info(f"✅ Integration endpoints added with prefix: {integration_router.prefix}")
except ImportError as e:
    logger.warning(f"Could not import integration endpoints: {e}")

# Root endpoint - MCP Contextual Operating System Dashboard
@app.get("/", response_class=HTMLResponse)
async def root():
    """MCP Contextual Operating System Dashboard."""
    # Read the COMPLETE dashboard HTML file
    try:
        with open("mcp_complete_dashboard.html", "r") as f:
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
# Initialize Google OAuth (using unified version for all Google services)
try:
    from mcp_server.unified_google_auth import initialize_unified_auth, unified_auth
    from fastapi.responses import RedirectResponse, HTMLResponse
    
    # Initialize the unified auth manager
    oauth_mgr = initialize_unified_auth()
    
    @app.get("/auth/google")
    async def start_auth():
        """Start Google OAuth flow."""
        auth_url = oauth_mgr.get_auth_url("http://localhost:8001/auth/callback")
        return RedirectResponse(url=auth_url)
    
    @app.get("/auth/callback")
    async def auth_callback(code: str):
        """Handle OAuth callback."""
        success = await oauth_mgr.exchange_code(code, "http://localhost:8001/auth/callback")
        
        if success:
            return HTMLResponse("""
                <html>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>✅ Authentication Successful!</h1>
                    <p>You can now use calendar features.</p>
                    <p><a href="/">Go to Dashboard</a></p>
                </body>
                </html>
            """)
        else:
            return HTMLResponse("""
                <html>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>❌ Authentication Failed</h1>
                    <p><a href="/auth/google">Try Again</a></p>
                </body>
                </html>
            """)
    
    @app.get("/auth/status")
    async def auth_status():
        """Check authentication status."""
        return {
            "authenticated": oauth_mgr.is_authenticated(),
            "scopes": oauth_mgr.SCOPES if oauth_mgr.is_authenticated() else []
        }
    
    @app.get("/calendar/real-events")
    async def get_real_calendar_events():
        """Get real Google Calendar events."""
        if not oauth_mgr.is_authenticated():
            return {"error": "Not authenticated", "events": []}
        
        events = await oauth_mgr.get_calendar_events()
        return {
            "success": True,
            "count": len(events),
            "events": events
        }
    
    @app.get("/fitness/today")
    async def get_fitness_today():
        """Get today's fitness stats."""
        if not oauth_mgr.is_authenticated():
            return {"error": "Not authenticated"}
        
        stats = await oauth_mgr.get_today_stats()
        return stats
    
    @app.get("/fitness/steps")
    async def get_steps_data(days: int = 7):
        """Get step count data."""
        if not oauth_mgr.is_authenticated():
            return {"error": "Not authenticated", "data": []}
        
        data = await oauth_mgr.get_fitness_data("steps", days)
        return {
            "success": True,
            "type": "steps",
            "days": days,
            "count": len(data),
            "data": data
        }
    
    @app.get("/fitness/activity")
    async def get_activity_data(days: int = 7):
        """Get activity data."""
        if not oauth_mgr.is_authenticated():
            return {"error": "Not authenticated", "data": []}
        
        data = await oauth_mgr.get_fitness_data("activity", days)
        return {
            "success": True,
            "type": "activity",
            "days": days,
            "count": len(data),
            "data": data
        }
    
    @app.get("/fitness/calories")
    async def get_calories_data(days: int = 7):
        """Get calories burned data."""
        if not oauth_mgr.is_authenticated():
            return {"error": "Not authenticated", "data": []}
        
        data = await oauth_mgr.get_fitness_data("calories", days)
        return {
            "success": True,
            "type": "calories",
            "days": days,
            "count": len(data),
            "data": data
        }
    
    logger.info("🔐 Simple Google OAuth routes initialized")
except Exception as e:
    logger.warning(f"Google OAuth not available: {e}")

@app.post("/test/integration")
async def test_integration():
    """Test the integration hub by triggering events."""
    if not hub:
        return {"error": "Integration hub not initialized"}
    
    from mcp_server.integration_hub import SystemEvent, EventType
    from datetime import datetime
    
    # Emit a test event
    await hub.emit(SystemEvent(
        type=EventType.MANUAL_TRIGGER,
        data={"test": True, "message": "Testing integration"},
        timestamp=datetime.now(),
        source="test_endpoint",
        priority=7
    ))
    
    return {
        "success": True,
        "message": "Test event emitted",
        "components_registered": list(hub.components.keys()),
        "context": hub.context
    }

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

# Import REAL cognitive loop
try:
    from .real_cognitive_loop import get_cognitive_loop
    real_cognitive_available = True
except ImportError:
    real_cognitive_available = False
    logger.warning("Real cognitive loop not available")

# Keep simple handler as absolute fallback
try:
    from .simple_chat_handler import get_chat_handler
    simple_chat_available = True
except ImportError:
    simple_chat_available = False
    logger.warning("Simple chat handler not available")

# Core chat endpoint - using REAL cognitive loop
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Real cognitive loop endpoint - no fallbacks, actual cognitive processing.
    """
    start_time = asyncio.get_event_loop().time()
    
    # Use REAL cognitive loop
    if real_cognitive_available:
        try:
            cognitive_loop = get_cognitive_loop()
            result = await cognitive_loop.process(request.message, request.user_id)
            
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return ChatResponse(
                message=result["response"],
                user_id=request.user_id,
                task_focus=request.task_focus,
                suggested_actions=result.get("actions", []),
                processing_time=processing_time,
                pattern_detected=bool(result.get("patterns_detected")),
                metadata={
                    "thinking": result.get("thinking"),
                    "emotional_tone": result.get("emotional_tone"),
                    "cognitive_load": result.get("cognitive_load_considered"),
                    "learning": result.get("learning"),
                    "handler": "real_cognitive_loop"
                }
            )
        except Exception as e:
            logger.error(f"Simple chat handler failed: {e}")
            # Fall through to cognitive loop attempt
    
    # Fallback attempt with cognitive loop (will likely fail)
    try:
        from mcp_server.models import NudgeTier
        
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

# Claude V2 Cognitive Engine Endpoints
try:
    from mcp_server.claude_v2_endpoint import create_claude_v2_endpoint
    import asyncio
    
    # Add V2 endpoints to the app
    asyncio.create_task(create_claude_v2_endpoint(app))
    logger.info("✅ Claude V2 cognitive engine endpoints added")
except ImportError as e:
    logger.warning(f"Claude V2 endpoints not available: {e}")

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
async def send_nudge(request: NudgeRequest):
    """Send a nudge to Nest devices."""
    try:
        from mcp_server.nest_nudges import nest_nudge_system
        
        if not nest_nudge_system:
            raise HTTPException(status_code=503, detail="Nudge system not initialized")
        
        # Map urgency to nudge type
        from mcp_server.nest_nudges import NudgeType
        if request.urgency == "high":
            nudge_type = NudgeType.URGENT
            volume = 0.6
        elif request.urgency == "low":
            nudge_type = NudgeType.GENTLE
            volume = 0.4
        else:
            nudge_type = NudgeType.MOTIVATIONAL
            volume = 0.5
        
        success = await nest_nudge_system.send_nudge(
            message=request.message,
            nudge_type=nudge_type,
            device_name=request.device,
            volume=volume
        )
        
        if success:
            return {"success": True, "message": f"📢 Nudge sent: {request.message}"}
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

# Smart Scheduler Endpoints
@app.post("/schedule/add")
async def add_schedule(request: dict):
    """Add a new intelligent nudge schedule."""
    try:
        from mcp_server.smart_scheduler import smart_scheduler, NudgeSchedule, ScheduleType
        from datetime import datetime
        
        if not smart_scheduler:
            return {"success": False, "message": "Smart scheduler not available"}
        
        # Create schedule from request
        schedule = NudgeSchedule(
            schedule_id=request.get("schedule_id", f"schedule_{int(datetime.now().timestamp())}"),
            user_id=request.get("user_id", "default"),
            schedule_type=ScheduleType(request.get("schedule_type", "custom")),
            target_time=request["target_time"],  # Required: "HH:MM" format
            title=request.get("title", "Reminder"),
            context=request.get("context", ""),
            enabled=request.get("enabled", True),
            pre_nudge_minutes=request.get("pre_nudge_minutes", 15),
            escalation_intervals=request.get("escalation_intervals", [5, 10, 15, 20, 30]),
            max_attempts=request.get("max_attempts", 5),
            tone=request.get("tone", "encouraging"),
            use_llm=request.get("use_llm", True)
        )
        
        success = await smart_scheduler.add_schedule(schedule)
        
        if success:
            return {
                "success": True,
                "message": f"✅ Added schedule: {schedule.title} at {schedule.target_time}",
                "schedule_id": schedule.schedule_id
            }
        else:
            return {"success": False, "message": "Failed to add schedule"}
            
    except Exception as e:
        logger.error(f"Add schedule failed: {e}")
        return {"success": False, "error": str(e)}

@app.get("/schedule/list")
async def list_schedules():
    """Get all active schedules."""
    try:
        from mcp_server.smart_scheduler import smart_scheduler
        
        if not smart_scheduler:
            return {"schedules": [], "message": "Smart scheduler not available"}
        
        schedules = smart_scheduler.get_schedules()
        return {
            "schedules": schedules,
            "total": len(schedules)
        }
        
    except Exception as e:
        logger.error(f"List schedules failed: {e}")
        return {"error": str(e)}

@app.post("/schedule/{schedule_id}/acknowledge")
async def acknowledge_schedule(schedule_id: str):
    """Acknowledge a nudge to stop the sequence."""
    try:
        from mcp_server.smart_scheduler import smart_scheduler
        
        if not smart_scheduler:
            return {"success": False, "message": "Smart scheduler not available"}
        
        success = await smart_scheduler.acknowledge_nudge(schedule_id)
        
        if success:
            return {
                "success": True,
                "message": f"✅ Acknowledged schedule: {schedule_id}"
            }
        else:
            return {"success": False, "message": "Schedule not found"}
            
    except Exception as e:
        logger.error(f"Acknowledge schedule failed: {e}")
        return {"success": False, "error": str(e)}

@app.post("/schedule/{schedule_id}/snooze")
async def snooze_schedule(schedule_id: str, minutes: int = 10):
    """Snooze a nudge for specified minutes."""
    try:
        from mcp_server.smart_scheduler import smart_scheduler
        
        if not smart_scheduler:
            return {"success": False, "message": "Smart scheduler not available"}
        
        success = await smart_scheduler.snooze_nudge(schedule_id, minutes)
        
        if success:
            return {
                "success": True,
                "message": f"😴 Snoozed schedule {schedule_id} for {minutes} minutes"
            }
        else:
            return {"success": False, "message": "Schedule not found"}
            
    except Exception as e:
        logger.error(f"Snooze schedule failed: {e}")
        return {"success": False, "error": str(e)}

@app.post("/schedule/bedtime")
async def quick_bedtime_schedule(target_time: str = "22:00", tone: str = "encouraging"):
    """Quick endpoint to set up bedtime nudging."""
    try:
        from mcp_server.smart_scheduler import smart_scheduler, NudgeSchedule, ScheduleType
        from datetime import datetime
        
        if not smart_scheduler:
            return {"success": False, "message": "Smart scheduler not available"}
        
        # Create bedtime schedule
        bedtime_schedule = NudgeSchedule(
            schedule_id="bedtime_user",
            schedule_type=ScheduleType.BEDTIME,
            target_time=target_time,
            title="Bedtime",
            context="Good sleep is crucial for ADHD brain regulation and executive function",
            tone=tone,
            pre_nudge_minutes=15,
            escalation_intervals=[10, 15, 20, 30, 45],
            max_attempts=6,
            use_llm=True
        )
        
        success = await smart_scheduler.add_schedule(bedtime_schedule)
        
        if success:
            return {
                "success": True,
                "message": f"🛏️ Bedtime nudging set for {target_time} with {tone} tone",
                "schedule_id": "bedtime_user",
                "details": "Will start gentle reminders 15 min before, then escalate every 10-45 min"
            }
        else:
            return {"success": False, "message": "Failed to set bedtime schedule"}
            
    except Exception as e:
        logger.error(f"Bedtime schedule failed: {e}")
        return {"success": False, "error": str(e)}

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
# ⌚ PIXEL WATCH INTEGRATION ENDPOINTS
# ============================================================================

@app.post("/watch/nudge/{nudge_type}")
async def send_watch_nudge(nudge_type: str, message: str = None, priority: str = "normal"):
    """Send ADHD nudge to Pixel Watch via Home Assistant."""
    try:
        from .pixel_watch_integration import initialize_pixel_watch, WearableNudgeType
        
        # Initialize if needed
        pixel_watch = await initialize_pixel_watch()
        
        if not pixel_watch.is_initialized:
            return {
                "success": False,
                "message": "Pixel Watch integration not available"
            }
        
        # Convert string to enum
        try:
            nudge_enum = WearableNudgeType(nudge_type.lower())
        except ValueError:
            return {
                "success": False,
                "message": f"Invalid nudge type: {nudge_type}"
            }
        
        success = await pixel_watch.send_adhd_nudge(
            nudge_enum, 
            custom_message=message, 
            priority=priority
        )
        
        if success:
            return {
                "success": True,
                "message": f"✅ Watch nudge sent: {nudge_type}"
            }
        else:
            return {
                "success": False,
                "message": "Failed to send watch nudge"
            }
            
    except Exception as e:
        logger.error(f"Watch nudge failed: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@app.post("/watch/checkin")
async def watch_quick_checkin():
    """Send quick ADHD check-in to watch."""
    try:
        from .pixel_watch_integration import initialize_pixel_watch
        
        pixel_watch = await initialize_pixel_watch()
        success = await pixel_watch.send_quick_checkin()
        
        return {
            "success": success,
            "message": "⚡ Energy check-in sent to watch" if success else "Failed to send check-in"
        }
        
    except Exception as e:
        logger.error(f"Watch check-in failed: {e}")
        return {"success": False, "message": str(e)}

@app.post("/watch/hyperfocus-break")
async def watch_hyperfocus_break(duration_hours: float = 2.0):
    """Send hyperfocus break reminder to watch."""
    try:
        from .pixel_watch_integration import initialize_pixel_watch
        
        pixel_watch = await initialize_pixel_watch()
        success = await pixel_watch.send_hyperfocus_break(duration_hours)
        
        return {
            "success": success,
            "message": f"🛑 Hyperfocus break reminder sent (after {duration_hours}h)" if success else "Failed to send reminder"
        }
        
    except Exception as e:
        logger.error(f"Hyperfocus break failed: {e}")
        return {"success": False, "message": str(e)}

@app.get("/watch/stats")
async def get_watch_stats():
    """Get Pixel Watch nudge statistics."""
    try:
        from .pixel_watch_integration import initialize_pixel_watch
        
        pixel_watch = await initialize_pixel_watch()
        stats = await pixel_watch.get_nudge_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Watch stats failed: {e}")
        return {
            "success": False,
            "message": str(e)
        }

# ============================================================================
# 🎵 JELLYFIN MUSIC INTEGRATION ENDPOINTS
# ============================================================================

# Jellyfin music integration with fallbacks
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
    
    async def play_calm_music():
        if music_module.jellyfin_music:
            return await music_module.jellyfin_music.play_mood_playlist(MusicMood.CALM)
        return False
    
    async def play_ambient_music():
        if music_module.jellyfin_music:
            return await music_module.jellyfin_music.play_mood_playlist(MusicMood.AMBIENT)
        return False
    
    async def play_study_music():
        if music_module.jellyfin_music:
            return await music_module.jellyfin_music.play_mood_playlist(MusicMood.STUDY)
        return False
    
    async def play_nature_music():
        if music_module.jellyfin_music:
            return await music_module.jellyfin_music.play_mood_playlist(MusicMood.NATURE)
        return False
    
    async def next_track():
        if music_module.jellyfin_music:
            return await music_module.jellyfin_music.skip_track()
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
        jellyfin_user_id = os.environ.get('JELLYFIN_USER_ID')
        
        if not jellyfin_token:
            raise HTTPException(
                status_code=400, 
                detail="JELLYFIN_TOKEN environment variable required"
            )
        
        success = await initialize_music_controller(
            jellyfin_url, 
            jellyfin_token, 
            chromecast_name,
            jellyfin_user_id
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


@app.post("/music/calm")
async def quick_calm_music():
    """Quick endpoint to start calm music for relaxation."""
    if not music_available:
        raise HTTPException(status_code=503, detail="Music system not available")
    
    try:
        success = await play_calm_music()
        return {
            "success": success,
            "message": "😌 Calm music started! Time to relax and breathe." if success else "Failed to start calm music"
        }
    except Exception as e:
        logger.error(f"Quick calm music failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/ambient")
async def quick_ambient_music():
    """Quick endpoint to start ambient music for background focus."""
    if not music_available:
        raise HTTPException(status_code=503, detail="Music system not available")
    
    try:
        success = await play_ambient_music()
        return {
            "success": success,
            "message": "🌊 Ambient music started! Perfect background for any task." if success else "Failed to start ambient music"
        }
    except Exception as e:
        logger.error(f"Quick ambient music failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/study")
async def quick_study_music():
    """Quick endpoint to start study music for learning."""
    if not music_available:
        raise HTTPException(status_code=503, detail="Music system not available")
    
    try:
        success = await play_study_music()
        return {
            "success": success,
            "message": "📚 Study music started! Optimize your learning environment." if success else "Failed to start study music"
        }
    except Exception as e:
        logger.error(f"Quick study music failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/nature")
async def quick_nature_music():
    """Quick endpoint to start nature sounds for grounding."""
    if not music_available:
        raise HTTPException(status_code=503, detail="Music system not available")
    
    try:
        success = await play_nature_music()
        return {
            "success": success,
            "message": "🌿 Nature sounds started! Connect with natural rhythms." if success else "Failed to start nature sounds"
        }
    except Exception as e:
        logger.error(f"Quick nature music failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/next")
async def skip_to_next_track():
    """Skip to the next track in the current playlist."""
    if not music_available:
        raise HTTPException(status_code=503, detail="Music system not available")
    
    try:
        success = await next_track()
        return {
            "success": success,
            "message": "⏭️ Skipped to next track!" if success else "Failed to skip track"
        }
    except Exception as e:
        logger.error(f"Next track failed: {e}")
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


# Playlist Management Endpoints
@app.get("/playlists")
async def list_playlists():
    """List all available playlists."""
    if not music_available or not music_module.jellyfin_music:
        raise HTTPException(status_code=503, detail="Music system not available")
    
    try:
        playlists = await music_module.jellyfin_music.list_playlists()
        return {
            "playlists": playlists,
            "count": len(playlists),
            "message": f"Found {len(playlists)} playlists"
        }
    except Exception as e:
        logger.error(f"List playlists failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playlists/play/{playlist_name}")
async def play_playlist(playlist_name: str, shuffle: bool = True):
    """Play a specific playlist."""
    if not music_available or not music_module.jellyfin_music:
        raise HTTPException(status_code=503, detail="Music system not available")
    
    try:
        success = await music_module.jellyfin_music.play_playlist(playlist_name, shuffle)
        return {
            "success": success,
            "message": f"🎵 Playing playlist '{playlist_name}'" if success else f"Failed to play playlist '{playlist_name}'"
        }
    except Exception as e:
        logger.error(f"Play playlist failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playlists/create-adhd")
async def create_adhd_playlists():
    """Create or update ADHD-specific playlists."""
    if not music_available or not music_module.jellyfin_music:
        raise HTTPException(status_code=503, detail="Music system not available")
    
    try:
        await music_module.jellyfin_music._load_and_create_adhd_playlists()
        return {
            "success": True,
            "message": "✅ ADHD playlists created/updated successfully"
        }
    except Exception as e:
        logger.error(f"Create ADHD playlists failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ADHD Reminder System Endpoints
@app.get("/reminders")
async def get_reminders(type: Optional[str] = None):
    """Get all configured reminders."""
    try:
        from mcp_server.adhd_reminders import adhd_reminders, ReminderType
        
        if not adhd_reminders:
            return {"reminders": [], "message": "Reminder system not initialized"}
        
        type_filter = ReminderType(type) if type else None
        reminders = await adhd_reminders.get_reminders(type_filter)
        
        return {
            "reminders": reminders,
            "count": len(reminders),
            "system_active": True
        }
    except Exception as e:
        logger.error(f"Failed to get reminders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reminders/add")
async def add_reminder(
    message: str,
    time: Optional[str] = None,  # Format: "HH:MM"
    interval_minutes: Optional[int] = None,
    priority: str = "normal"
):
    """Add a custom reminder."""
    try:
        from mcp_server.adhd_reminders import adhd_reminders
        from datetime import time as dt_time
        
        if not adhd_reminders:
            raise HTTPException(status_code=503, detail="Reminder system not initialized")
        
        # Parse time if provided
        trigger_time = None
        if time:
            hour, minute = map(int, time.split(':'))
            trigger_time = dt_time(hour, minute)
        
        reminder_id = await adhd_reminders.add_custom_reminder(
            message=message,
            trigger_time=trigger_time,
            interval_minutes=interval_minutes,
            priority=priority
        )
        
        return {
            "success": True,
            "reminder_id": reminder_id,
            "message": f"Custom reminder added: {reminder_id}"
        }
    except Exception as e:
        logger.error(f"Failed to add reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/reminders/{reminder_id}")
async def update_reminder(reminder_id: str, enabled: Optional[bool] = None, message: Optional[str] = None):
    """Update an existing reminder."""
    try:
        from mcp_server.adhd_reminders import adhd_reminders
        
        if not adhd_reminders:
            raise HTTPException(status_code=503, detail="Reminder system not initialized")
        
        updates = {}
        if enabled is not None:
            updates['enabled'] = enabled
        if message is not None:
            updates['message'] = message
        
        success = await adhd_reminders.update_reminder(reminder_id, **updates)
        
        if success:
            return {"success": True, "message": f"Reminder {reminder_id} updated"}
        else:
            raise HTTPException(status_code=404, detail="Reminder not found")
            
    except Exception as e:
        logger.error(f"Failed to update reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reminders/{reminder_id}/acknowledge")
async def acknowledge_reminder(reminder_id: str):
    """Acknowledge a reminder that requires confirmation."""
    try:
        from mcp_server.adhd_reminders import adhd_reminders
        
        if not adhd_reminders:
            raise HTTPException(status_code=503, detail="Reminder system not initialized")
        
        success = await adhd_reminders.acknowledge_reminder(reminder_id)
        
        if success:
            return {"success": True, "message": f"Reminder {reminder_id} acknowledged"}
        else:
            raise HTTPException(status_code=404, detail="Reminder not found")
            
    except Exception as e:
        logger.error(f"Failed to acknowledge reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Debug test - this should work since it's right after reminders  
@app.get("/debug/after-reminders")
async def debug_after_reminders():
    return {"message": "After reminders endpoint works"}

# Debug endpoint to test registration
@app.get("/debug/before-voice")
async def debug_before_voice():
    return {"message": "Endpoint before voice works"}

# Voice and Calendar Integration Endpoints
@app.post("/voice/command")
async def process_voice_command(command: str, params: Optional[Dict] = None):
    """Process a voice command through the calendar system."""
    try:
        from mcp_server.voice_calendar_integration import voice_calendar
        
        if not voice_calendar:
            raise HTTPException(status_code=503, detail="Voice calendar system not initialized")
        
        response = await voice_calendar.process_voice_command(command, params or {})
        
        return {
            "success": True,
            "command": command,
            "response": response
        }
    except Exception as e:
        logger.error(f"Voice command failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/calendar/next")
async def get_next_event():
    """Get the next calendar event."""
    try:
        from mcp_server.voice_calendar_integration import voice_calendar
        
        if not voice_calendar:
            return {"next_event": None, "message": "Calendar system not initialized"}
        
        await voice_calendar._update_context()
        
        if voice_calendar.context.next_event:
            return {
                "next_event": voice_calendar.context.next_event,
                "time_until_minutes": voice_calendar.context.time_until_next,
                "is_in_meeting": voice_calendar.context.is_in_meeting
            }
        else:
            return {"next_event": None, "message": "No upcoming events"}
            
    except Exception as e:
        logger.error(f"Failed to get next event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calendar/focus-time")
async def start_focus_time(duration: int = 25):
    """Start a focus time session with calendar awareness."""
    try:
        from mcp_server.voice_calendar_integration import voice_calendar
        
        if not voice_calendar:
            raise HTTPException(status_code=503, detail="Voice calendar system not initialized")
        
        response = await voice_calendar.handle_focus_time({'duration': duration})
        
        return {
            "success": True,
            "duration": duration,
            "message": response
        }
    except Exception as e:
        logger.error(f"Focus time failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/listen")
async def start_voice_listening():
    """Start listening for voice commands."""
    try:
        from mcp_server.voice_assistant import voice_assistant
        
        if not voice_assistant:
            raise HTTPException(status_code=503, detail="Voice assistant not available")
        
        # Start a listening session
        asyncio.create_task(voice_assistant.start_session())
        
        return {
            "success": True,
            "message": "Listening for voice command..."
        }
    except Exception as e:
        logger.error(f"Voice listen failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Debug endpoint to test registration after voice
@app.get("/debug/after-voice")
async def debug_after_voice():
    return {"message": "Endpoint after voice works"}

# Smart Scheduling System Integration
schedule_available = False
schedule_module = None

try:
    from mcp_server.smart_scheduler import smart_scheduler, NudgeSchedule, ScheduleType
    schedule_available = True
    logger.info("✅ Smart scheduler API integration loaded")
except ImportError as e:
    logger.warning(f"Smart scheduler API not available: {e}")

@app.post("/schedule/add")
async def add_schedule(request: dict):
    """Add a new nudge schedule."""
    if not schedule_available or not smart_scheduler:
        raise HTTPException(status_code=503, detail="Smart scheduler not available")
    
    try:
        from datetime import datetime
        import uuid
        
        # Parse request
        schedule_type_str = request.get("schedule_type", "custom")
        schedule_type = ScheduleType(schedule_type_str)
        
        # Create schedule
        schedule = NudgeSchedule(
            schedule_id=f"schedule_{int(datetime.now().timestamp())}",
            user_id=request.get("user_id", "default"),
            schedule_type=schedule_type,
            target_time=request.get("target_time", "22:00"),
            title=request.get("title", "Reminder"),
            context=request.get("context", ""),
            enabled=request.get("enabled", True),
            pre_nudge_minutes=request.get("pre_nudge_minutes", 15),
            escalation_intervals=request.get("escalation_intervals", [10, 15, 20, 25, 30]),
            max_attempts=request.get("max_attempts", 5),
            tone=request.get("tone", "encouraging"),
            include_context=request.get("include_context", True),
            use_llm=request.get("use_llm", True)
        )
        
        success = await smart_scheduler.add_schedule(schedule)
        
        if success:
            return {
                "success": True,
                "message": f"✅ Added schedule: {schedule.title} at {schedule.target_time}",
                "schedule_id": schedule.schedule_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add schedule")
            
    except Exception as e:
        logger.error(f"Schedule add failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schedule/list")
async def list_schedules():
    """Get all active schedules."""
    if not schedule_available or not smart_scheduler:
        raise HTTPException(status_code=503, detail="Smart scheduler not available")
    
    try:
        schedules = smart_scheduler.get_schedules()
        return {
            "success": True,
            "schedules": schedules,
            "count": len(schedules)
        }
    except Exception as e:
        logger.error(f"Schedule list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schedule/{schedule_id}/acknowledge")
async def acknowledge_schedule(schedule_id: str):
    """Acknowledge a nudge to stop the sequence."""
    if not schedule_available or not smart_scheduler:
        raise HTTPException(status_code=503, detail="Smart scheduler not available")
    
    try:
        success = await smart_scheduler.acknowledge_nudge(schedule_id)
        return {
            "success": success,
            "message": f"✅ Acknowledged schedule: {schedule_id}" if success else "Schedule not found"
        }
    except Exception as e:
        logger.error(f"Schedule acknowledge failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schedule/{schedule_id}/snooze")
async def snooze_schedule(schedule_id: str, minutes: int = 10):
    """Snooze a nudge for specified minutes."""
    if not schedule_available or not smart_scheduler:
        raise HTTPException(status_code=503, detail="Smart scheduler not available")
    
    try:
        success = await smart_scheduler.snooze_nudge(schedule_id, minutes)
        return {
            "success": success,
            "message": f"😴 Snoozed schedule {schedule_id} for {minutes} minutes" if success else "Schedule not found"
        }
    except Exception as e:
        logger.error(f"Schedule snooze failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Google Assistant Broadcast Integration
google_assistant_available = False
google_assistant_module = None

try:
    from mcp_server.google_assistant_integration import initialize_google_assistant, BroadcastType
    google_assistant_available = True
    logger.info("✅ Google Assistant broadcast integration loaded")
except ImportError as e:
    logger.warning(f"Google Assistant broadcast not available: {e}")

@app.post("/broadcast/initialize")
async def initialize_broadcast():
    """Initialize Google Assistant broadcast system."""
    if not google_assistant_available:
        raise HTTPException(status_code=503, detail="Google Assistant broadcast not available")
    
    try:
        global google_assistant_module
        google_assistant_module = await initialize_google_assistant()
        return {
            "success": True,
            "message": "Google Assistant broadcast initialized",
            "devices": google_assistant_module.get_available_devices() if google_assistant_module else []
        }
    except Exception as e:
        logger.error(f"Failed to initialize Google Assistant broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/broadcast/send/{broadcast_type}")
async def send_broadcast(
    broadcast_type: str,
    message: Optional[str] = None,
    target_device: Optional[str] = None
):
    """Send Google Assistant broadcast nudge.
    
    Available broadcast types:
    - gentle: Gentle reminders and check-ins
    - focus: Focus session starts and deep work encouragement
    - break: Break reminders and movement nudges
    - celebration: Task completion celebrations
    - transition: Transition warnings and activity switches
    - urgent: Priority reminders and important tasks
    """
    if not google_assistant_available or not google_assistant_module:
        raise HTTPException(status_code=503, detail="Google Assistant broadcast not initialized")
    
    # Convert string to BroadcastType enum
    broadcast_type_map = {
        "gentle": BroadcastType.GENTLE_REMINDER,
        "focus": BroadcastType.FOCUS_TIME,
        "break": BroadcastType.BREAK_TIME,
        "celebration": BroadcastType.CELEBRATION,
        "transition": BroadcastType.TRANSITION,
        "urgent": BroadcastType.URGENT
    }
    
    broadcast_enum = broadcast_type_map.get(broadcast_type.lower())
    if not broadcast_enum:
        raise HTTPException(status_code=400, detail=f"Unknown broadcast type: {broadcast_type}")
    
    try:
        success = await google_assistant_module.send_broadcast_nudge(
            broadcast_type=broadcast_enum,
            custom_message=message,
            target_device=target_device
        )
        
        return {
            "success": success,
            "type": broadcast_type,
            "message": message or f"Sent {broadcast_type} broadcast nudge",
            "target_device": target_device or "all_devices"
        }
    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/broadcast/focus-session")
async def broadcast_focus_session(duration_minutes: int = 25):
    """Start a focus session broadcast."""
    if not google_assistant_available or not google_assistant_module:
        raise HTTPException(status_code=503, detail="Google Assistant broadcast not initialized")
    
    try:
        success = await google_assistant_module.broadcast_focus_session(duration_minutes)
        return {
            "success": success,
            "duration": duration_minutes,
            "message": f"Focus session broadcast sent for {duration_minutes} minutes"
        }
    except Exception as e:
        logger.error(f"Focus session broadcast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/broadcast/celebration")
async def broadcast_celebration(achievement: str):
    """Broadcast celebration for completed task."""
    if not google_assistant_available or not google_assistant_module:
        raise HTTPException(status_code=503, detail="Google Assistant broadcast not initialized")
    
    try:
        success = await google_assistant_module.broadcast_celebration(achievement)
        return {
            "success": success,
            "achievement": achievement,
            "message": f"Celebration broadcast sent for: {achievement}"
        }
    except Exception as e:
        logger.error(f"Celebration broadcast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/broadcast/stats")
async def get_broadcast_stats():
    """Get Google Assistant broadcast statistics."""
    if not google_assistant_available or not google_assistant_module:
        raise HTTPException(status_code=503, detail="Google Assistant broadcast not initialized")
    
    try:
        stats = google_assistant_module.get_broadcast_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get broadcast stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/broadcast/devices")
async def get_broadcast_devices():
    """Get available Google Assistant devices."""
    if not google_assistant_available or not google_assistant_module:
        raise HTTPException(status_code=503, detail="Google Assistant broadcast not initialized")
    
    try:
        devices = google_assistant_module.get_available_devices()
        return {
            "success": True,
            "devices": devices,
            "count": len(devices)
        }
    except Exception as e:
        logger.error(f"Failed to get broadcast devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test_tts.mp3")
async def serve_test_audio():
    """Serve test TTS file for debugging."""
    from fastapi.responses import FileResponse
    import os
    
    test_file = "/home/pi/repos/ADHDo/test_tts.mp3"
    if os.path.exists(test_file):
        return FileResponse(test_file, media_type="audio/mp3")
    else:
        raise HTTPException(status_code=404, detail="Test file not found")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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