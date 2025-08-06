#!/usr/bin/env python3
"""
Start the MCP ADHD Server with all components.

This script starts:
- Redis connection
- FastAPI server with web interface 
- LLM routing with optimizations
- Telegram bot (if configured)
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_server.main import app
from mcp_server.config import settings
from traces.memory import trace_memory
import uvicorn

async def startup():
    """Initialize all components."""
    print("🧠⚡ Starting MCP ADHD Server")
    print("=" * 40)
    
    # Connect to Redis
    try:
        await trace_memory.connect()
        print("✅ Connected to Redis")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("   Continuing in limited mode...")
    
    print(f"🌐 Web interface: http://{settings.host}:{settings.port}")
    print(f"📚 API docs: http://{settings.host}:{settings.port}/docs")
    print(f"🔧 Debug mode: {'ON' if settings.debug else 'OFF'}")
    
    if settings.telegram_bot_token:
        print("📱 Telegram bot: Configured")
    else:
        print("📱 Telegram bot: Not configured")
    
    print("\n🚀 Server starting...")

if __name__ == "__main__":
    try:
        # Run startup
        asyncio.run(startup())
        
        # Start the server
        uvicorn.run(
            "mcp_server.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower()
        )
    except KeyboardInterrupt:
        print("\n⚠️ Server interrupted by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        import traceback
        traceback.print_exc()