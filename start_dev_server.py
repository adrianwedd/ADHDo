#!/usr/bin/env python3
"""
Development server starter with minimal dependencies.
Starts the authentication system for testing.
"""
import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set up minimal environment
os.environ["DEBUG"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379"

try:
    import uvicorn
    from mcp_server.main import app
    
    print("🧠⚡ Starting MCP ADHD Server in development mode...")
    print("📍 API docs will be available at: http://localhost:8000/docs")
    print("🔐 Authentication endpoints at: /api/auth/*")
    
    uvicorn.run(
        "mcp_server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=True
    )
    
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("💡 Try: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Server error: {e}")
    sys.exit(1)