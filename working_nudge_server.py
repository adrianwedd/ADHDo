#!/usr/bin/env python3
"""
Working Nudge Server with Fixed Threading
A production-ready server that actually works with the nudge system.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import asyncio
import uvicorn
import logging
from datetime import datetime

# Import nudge system
from mcp_server.nest_nudges import NestNudgeSystem, NudgeType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ADHD Nudge Server", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global nudge system
nudge_system: Optional[NestNudgeSystem] = None

# Request/Response models
class NudgeRequest(BaseModel):
    message: str
    urgency: str = "normal"  # low, normal, high
    device: Optional[str] = None
    volume: Optional[float] = 0.5

class NudgeResponse(BaseModel):
    success: bool
    message: str
    device: Optional[str] = None
    timestamp: str

@app.on_event("startup")
async def startup():
    """Initialize nudge system on startup."""
    global nudge_system
    try:
        nudge_system = NestNudgeSystem()
        success = await nudge_system.initialize()
        if success:
            logger.info("✅ Nudge system initialized successfully")
        else:
            logger.warning("⚠️ Nudge system initialized with warnings")
    except Exception as e:
        logger.error(f"❌ Failed to initialize nudge system: {e}")
        nudge_system = NestNudgeSystem()  # Create anyway for fresh discovery

@app.on_event("shutdown")
async def shutdown():
    """Clean up nudge system on shutdown."""
    global nudge_system
    if nudge_system:
        await nudge_system.cleanup()

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ADHD Nudge Server",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "nudge": "/nudge/send",
            "devices": "/nudge/devices",
            "task_reminder": "/nudge/task",
            "break": "/nudge/break",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "nudge_system": nudge_system is not None
    }

@app.post("/nudge/send", response_model=NudgeResponse)
async def send_nudge(request: NudgeRequest):
    """Send a nudge to Nest devices."""
    if not nudge_system:
        raise HTTPException(status_code=503, detail="Nudge system not initialized")
    
    # Map urgency to nudge type and volume
    if request.urgency == "high":
        nudge_type = NudgeType.URGENT
        volume = request.volume or 0.6
    elif request.urgency == "low":
        nudge_type = NudgeType.GENTLE
        volume = request.volume or 0.4
    else:
        nudge_type = NudgeType.MOTIVATIONAL
        volume = request.volume or 0.5
    
    # Send the nudge
    success = await nudge_system.send_nudge(
        message=request.message,
        nudge_type=nudge_type,
        device_name=request.device,
        volume=volume
    )
    
    return NudgeResponse(
        success=success,
        message=request.message,
        device=request.device,
        timestamp=datetime.now().isoformat()
    )

@app.get("/nudge/devices")
async def list_devices():
    """List available Nest devices."""
    if not nudge_system:
        return {"devices": [], "error": "Nudge system not initialized"}
    
    # Do fresh discovery to get current devices
    await nudge_system._immediate_device_discovery()
    
    devices = []
    for device in nudge_system.devices:
        devices.append({
            "name": device.name,
            "model": device.model_name,
            "id": device.uuid
        })
    
    return {"devices": devices, "count": len(devices)}

@app.post("/nudge/task")
async def nudge_task_reminder(task: str, urgency: str = "normal"):
    """Send a task reminder nudge."""
    if not nudge_system:
        raise HTTPException(status_code=503, detail="Nudge system not initialized")
    
    success = await nudge_system.nudge_task_reminder(task, urgency)
    
    return {
        "success": success,
        "task": task,
        "urgency": urgency,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/nudge/break")
async def nudge_break():
    """Remind user to take a break."""
    if not nudge_system:
        raise HTTPException(status_code=503, detail="Nudge system not initialized")
    
    success = await nudge_system.nudge_break_time()
    
    return {
        "success": success,
        "type": "break",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/nudge/celebration")
async def nudge_celebration(task: str):
    """Celebrate task completion."""
    if not nudge_system:
        raise HTTPException(status_code=503, detail="Nudge system not initialized")
    
    success = await nudge_system.nudge_celebration(task)
    
    return {
        "success": success,
        "task": task,
        "type": "celebration",
        "timestamp": datetime.now().isoformat()
    }

# Serve audio files for nudges
@app.get("/nudge-audio/{filename}")
async def serve_nudge_audio(filename: str):
    """Serve generated TTS audio files."""
    if nudge_system and hasattr(nudge_system, '_audio_files'):
        filepath = nudge_system._audio_files.get(filename)
        if filepath and os.path.exists(filepath):
            return FileResponse(filepath, media_type='audio/mpeg')
    
    raise HTTPException(status_code=404, detail="Audio file not found")

# Serve static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=23443)