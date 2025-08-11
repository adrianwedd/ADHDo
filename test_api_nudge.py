#!/usr/bin/env python3
"""
Minimal API server to test the fresh discovery nudge approach in FastAPI context.
This tests if the threading issue is resolved.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI, BackgroundTasks
from mcp_server.nest_nudges import NestNudgeSystem
import asyncio
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
nudge_system = None

@app.on_event("startup")
async def startup():
    global nudge_system
    nudge_system = NestNudgeSystem()
    logger.info("📱 Minimal API server started with nudge system")

@app.post("/test-nudge")
async def test_nudge():
    """Test endpoint to send a nudge using fresh discovery."""
    if not nudge_system:
        return {"error": "Nudge system not initialized"}
    
    test_message = "API nudge test - fresh discovery approach"
    logger.info(f"🚀 API endpoint called: {test_message}")
    
    success = await nudge_system.send_nudge(
        message=test_message,
        volume=0.5
    )
    
    return {
        "success": success,
        "message": test_message,
        "method": "fresh_discovery"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)