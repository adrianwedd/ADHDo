"""
Evolution and observatory routes - System evolution and monitoring.

Extracted from monolithic main.py to improve code organization and maintainability.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import json

from ..health_monitor import health_monitor
from ..emergent_evolution import emergent_evolution
from ..optimization_engine import optimization_engine
from ..websocket_manager import websocket_manager

evolution_router = APIRouter(prefix="/api/evolution", tags=["Evolution"])


async def get_current_evolution_state() -> Dict[str, Any]:
    """Get current evolution state for WebSocket clients."""
    try:
        return {
            "evolution_active": await emergent_evolution.is_active(),
            "current_generation": await emergent_evolution.get_current_generation(),
            "optimization_metrics": await optimization_engine.get_current_metrics(),
            "system_health": await health_monitor.get_system_health(),
            "active_experiments": await emergent_evolution.get_active_experiments()
        }
    except Exception as e:
        health_monitor.record_error("get_evolution_state", str(e))
        return {"error": "Failed to get evolution state"}


@evolution_router.get("/status",
                      summary="Get Evolution System Status",
                      description="Returns current status of the evolution system including active processes and metrics")
async def get_evolution_status():
    """
    Get comprehensive evolution system status.
    
    Returns detailed information about evolutionary processes,
    optimization metrics, and system adaptation progress.
    """
    try:
        # Collect evolution system status
        status = {
            "evolution_active": False,
            "current_generation": 0,
            "optimization_cycles_completed": 0,
            "adaptive_improvements": [],
            "performance_metrics": {},
            "learning_insights": [],
            "system_adaptations": {}
        }
        
        # Check if evolution system is available and active
        try:
            status["evolution_active"] = await emergent_evolution.is_active()
            status["current_generation"] = await emergent_evolution.get_current_generation()
            status["optimization_cycles_completed"] = await optimization_engine.get_cycles_completed()
            
            # Get recent adaptive improvements
            status["adaptive_improvements"] = await emergent_evolution.get_recent_improvements()
            
            # Get performance metrics
            status["performance_metrics"] = await optimization_engine.get_current_metrics()
            
            # Get learning insights
            status["learning_insights"] = await emergent_evolution.get_learning_insights()
            
            # Get system adaptations
            status["system_adaptations"] = await emergent_evolution.get_system_adaptations()
            
        except Exception as e:
            health_monitor.record_error("evolution_status_collection", str(e))
            status["error"] = "Some evolution metrics unavailable"
        
        # Add timestamp and health info
        status.update({
            "timestamp": datetime.utcnow().isoformat(),
            "system_health": await health_monitor.get_system_health(),
            "memory_usage": await health_monitor.get_memory_usage(),
            "cpu_usage": await health_monitor.get_cpu_usage()
        })
        
        health_monitor.record_metric("evolution_status_requests", 1)
        
        return status
        
    except Exception as e:
        health_monitor.record_error("get_evolution_status", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve evolution status")


@evolution_router.post("/trigger",
                       summary="Trigger Evolution Cycle",
                       description="Manually trigger an evolution cycle for system optimization")
async def trigger_evolution():
    """
    Manually trigger a system evolution cycle.
    
    Initiates adaptive optimization processes and
    system improvement algorithms with safety monitoring.
    """
    try:
        # Check if evolution is already active
        if await emergent_evolution.is_active():
            return {
                "status": "already_active",
                "message": "Evolution cycle already in progress",
                "current_generation": await emergent_evolution.get_current_generation()
            }
        
        # Trigger evolution cycle
        result = await emergent_evolution.trigger_evolution_cycle()
        
        # Broadcast update to connected WebSocket clients
        await websocket_manager.broadcast_to_group("evolution", {
            "type": "evolution_update",
            "event": "evolution_triggered",
            "generation": result.get("generation"),
            "expected_duration": result.get("expected_duration"),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        health_monitor.record_metric("evolution_cycles_triggered", 1)
        
        return {
            "status": "triggered",
            "generation": result.get("generation"),
            "started_at": result.get("started_at"),
            "expected_duration": result.get("expected_duration"),
            "optimization_targets": result.get("targets", [])
        }
        
    except Exception as e:
        health_monitor.record_error("trigger_evolution", str(e))
        raise HTTPException(status_code=500, detail="Failed to trigger evolution cycle")


@evolution_router.post("/reset",
                       summary="Reset Evolution System", 
                       description="Reset the evolution system to initial state (admin function)")
async def reset_evolution():
    """
    Reset the evolution system to its initial state.
    
    Clears evolution history, resets optimization parameters,
    and reinitializes the adaptive learning system.
    """
    try:
        # Perform evolution system reset
        result = await emergent_evolution.reset_system()
        
        # Broadcast reset notification
        await websocket_manager.broadcast_to_group("evolution", {
            "type": "evolution_update",
            "event": "evolution_reset",
            "timestamp": datetime.utcnow().isoformat(),
            "reset_reason": "manual_reset"
        })
        
        health_monitor.record_metric("evolution_resets", 1)
        
        return {
            "status": "reset_complete",
            "message": "Evolution system has been reset to initial state",
            "reset_at": result.get("reset_at"),
            "preserved_data": result.get("preserved_data", []),
            "cleared_data": result.get("cleared_data", [])
        }
        
    except Exception as e:
        health_monitor.record_error("reset_evolution", str(e))
        raise HTTPException(status_code=500, detail="Failed to reset evolution system")


# Static file routes for evolution observatory
@evolution_router.get("/observatory",
                      summary="Evolution Observatory Dashboard",
                      description="Web interface for monitoring system evolution and optimization")
async def evolution_observatory():
    """
    Serve the Evolution Observatory dashboard.
    
    Returns the interactive web interface for monitoring
    system evolution, optimization metrics, and adaptive improvements.
    """
    try:
        return FileResponse(
            path="/home/pi/repos/ADHDo/static/evolution-observatory.html",
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache",
                "X-Evolution-Observatory": "v1.0"
            }
        )
    except Exception as e:
        health_monitor.record_error("serve_evolution_observatory", str(e))
        raise HTTPException(status_code=500, detail="Failed to serve evolution observatory")


@evolution_router.websocket("/ws")
async def evolution_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time evolution monitoring.
    
    Provides live updates about system evolution, optimization
    progress, and performance metrics to connected clients.
    """
    try:
        # Extract client information
        client_info = {
            "client_host": websocket.client.host if websocket.client else "unknown",
            "connected_at": datetime.utcnow().isoformat(),
            "user_agent": websocket.headers.get("user-agent", "unknown")
        }
        
        # Connect to WebSocket manager
        await websocket_manager.connect(websocket, "evolution", client_info)
        
        # Send initial evolution state
        initial_state = await get_current_evolution_state()
        await websocket_manager.send_to_connection(websocket, {
            "type": "initial_state",
            "data": initial_state,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        try:
            # Keep connection alive and handle incoming messages
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    message_type = message.get("type", "unknown")
                    
                    # Handle different message types
                    if message_type == "ping":
                        # Respond to ping
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                    
                    elif message_type == "request_update":
                        # Send current evolution state
                        current_state = await get_current_evolution_state()
                        await websocket_manager.send_to_connection(websocket, {
                            "type": "evolution_update",
                            "data": current_state,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    elif message_type == "subscribe_metrics":
                        # Handle metric subscription requests
                        metrics = message.get("metrics", [])
                        await websocket_manager.subscribe_to_topic(websocket, metrics)
                    
                except json.JSONDecodeError:
                    # Invalid JSON message
                    await websocket_manager.send_to_connection(websocket, {
                        "type": "error",
                        "message": "Invalid JSON message format"
                    })
                
        except WebSocketDisconnect:
            # Client disconnected normally
            pass
        
    except Exception as e:
        health_monitor.record_error("evolution_websocket", str(e))
        
    finally:
        # Clean up connection
        websocket_manager.disconnect(websocket)


# Background task for periodic evolution updates
async def broadcast_periodic_updates():
    """
    Background task to broadcast periodic evolution updates.
    
    Sends regular updates to all connected WebSocket clients
    about system evolution progress and metrics.
    """
    while True:
        try:
            # Get current evolution metrics
            current_metrics = {
                "type": "evolution_update",
                "data": {
                    "system_health": await health_monitor.get_system_health(),
                    "evolution_active": await emergent_evolution.is_active(),
                    "optimization_metrics": await optimization_engine.get_current_metrics()
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Broadcast to evolution group
            await websocket_manager.broadcast_to_group("evolution", current_metrics)
            
            # Wait before next update (30 seconds)
            await asyncio.sleep(30)
            
        except Exception as e:
            health_monitor.record_error("broadcast_periodic_updates", str(e))
            await asyncio.sleep(60)  # Wait longer on error