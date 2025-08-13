"""
FastAPI endpoints for the stateful cognitive loop.
Integrates the cognitive loop with the existing server.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .stateful_cognitive_loop import (
    StatefulCognitiveLoop, 
    UserContext, 
    UserState,
    ActivityType
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/cognitive", tags=["cognitive"])

# Global cognitive loop instance
cognitive_loop: Optional[StatefulCognitiveLoop] = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    user_id: str = "default_user"
    message: str


class StateUpdateRequest(BaseModel):
    """Request to update user state."""
    user_id: str = "default_user"
    state: Optional[str] = None
    current_task: Optional[str] = None
    medication_taken: Optional[bool] = None
    

class ActivityLogRequest(BaseModel):
    """Request to log an activity."""
    user_id: str = "default_user"
    activity_type: str
    data: Dict[str, Any] = {}


async def get_cognitive_loop() -> StatefulCognitiveLoop:
    """Get or create cognitive loop instance."""
    global cognitive_loop
    if cognitive_loop is None:
        cognitive_loop = StatefulCognitiveLoop()
        await cognitive_loop.initialize()
    return cognitive_loop


@router.post("/chat")
async def cognitive_chat(request: ChatRequest) -> Dict[str, Any]:
    """
    Process user message with full context awareness.
    This is the main endpoint for cognitive interactions.
    """
    try:
        loop = await get_cognitive_loop()
        response = await loop.process_user_input(
            request.user_id,
            request.message
        )
        
        # Execute any actions returned
        if response.get('actions'):
            await execute_actions(response['actions'])
        
        return {
            "success": True,
            "response": response['message'],
            "actions_taken": response.get('actions', []),
            "context": response.get('context_used', {})
        }
    except Exception as e:
        logger.error(f"Error in cognitive chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/{user_id}")
async def get_context(user_id: str = "default_user") -> Dict[str, Any]:
    """Get current user context."""
    try:
        loop = await get_cognitive_loop()
        context = await loop.get_user_context(user_id)
        
        return {
            "success": True,
            "context": context.to_dict()
        }
    except Exception as e:
        logger.error(f"Error getting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context/update")
async def update_context(request: StateUpdateRequest) -> Dict[str, Any]:
    """Update user context/state."""
    try:
        loop = await get_cognitive_loop()
        context = await loop.get_user_context(request.user_id)
        
        # Update fields if provided
        if request.state:
            context.current_state = UserState(request.state)
        if request.current_task is not None:
            context.current_task = request.current_task
            if request.current_task:
                context.task_started_at = datetime.now()
        if request.medication_taken:
            context.last_medication = datetime.now()
            await loop.log_activity(
                request.user_id,
                ActivityType.MEDICATION_TAKEN,
                {"time": datetime.now().isoformat()}
            )
        
        # Save updated context
        await loop.save_user_context(context)
        
        return {
            "success": True,
            "message": "Context updated",
            "context": context.to_dict()
        }
    except Exception as e:
        logger.error(f"Error updating context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activity/log")
async def log_activity(request: ActivityLogRequest) -> Dict[str, Any]:
    """Log an activity for pattern tracking."""
    try:
        loop = await get_cognitive_loop()
        activity_type = ActivityType(request.activity_type)
        
        await loop.log_activity(
            request.user_id,
            activity_type,
            request.data
        )
        
        return {
            "success": True,
            "message": f"Activity {request.activity_type} logged"
        }
    except Exception as e:
        logger.error(f"Error logging activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/{user_id}")
async def get_patterns(user_id: str = "default_user") -> Dict[str, Any]:
    """Get analyzed patterns for a user."""
    try:
        loop = await get_cognitive_loop()
        patterns = await loop.analyze_patterns(user_id)
        
        return {
            "success": True,
            "patterns": patterns
        }
    except Exception as e:
        logger.error(f"Error getting patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/time-context")
async def get_time_context() -> Dict[str, Any]:
    """Get current time-based context."""
    try:
        loop = await get_cognitive_loop()
        time_context = await loop.get_time_context()
        
        return {
            "success": True,
            "time_context": time_context
        }
    except Exception as e:
        logger.error(f"Error getting time context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-interventions/{user_id}")
async def check_interventions(user_id: str = "default_user") -> Dict[str, Any]:
    """Check if any interventions are needed for the user."""
    try:
        loop = await get_cognitive_loop()
        context = await loop.get_user_context(user_id)
        time_context = await loop.get_time_context()
        
        intervention = await loop.determine_intervention(context, time_context)
        
        if intervention:
            # Execute the intervention
            await execute_intervention(intervention)
            
            return {
                "success": True,
                "intervention_needed": True,
                "intervention": intervention
            }
        else:
            return {
                "success": True,
                "intervention_needed": False,
                "message": "No intervention needed at this time"
            }
    except Exception as e:
        logger.error(f"Error checking interventions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def execute_actions(actions: List[Dict[str, Any]]):
    """Execute actions returned by the cognitive loop."""
    import aiohttp
    
    for action in actions:
        try:
            action_type = action.get('type')
            
            if action_type == 'start_music':
                mood = action.get('mood', 'focus')
                async with aiohttp.ClientSession() as session:
                    await session.post(f"http://localhost:23443/music/{mood}")
                    
            elif action_type == 'suggest_break':
                # Send a break reminder nudge
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        "http://localhost:23443/nudge/send",
                        json={
                            "message": "Time for a break! Stand up, stretch, hydrate.",
                            "urgency": "normal"
                        }
                    )
                    
            elif action_type == 'update_task':
                # Task tracking would go here
                pass
                
        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")


async def execute_intervention(intervention: Dict[str, Any]):
    """Execute an intervention."""
    import aiohttp
    
    try:
        if intervention.get('action') == 'nudge':
            async with aiohttp.ClientSession() as session:
                await session.post(
                    "http://localhost:23443/nudge/send",
                    json={
                        "message": intervention['message'],
                        "urgency": intervention.get('urgency', 'normal')
                    }
                )
    except Exception as e:
        logger.error(f"Error executing intervention: {e}")


# Background task to run periodic checks
async def periodic_intervention_check():
    """Background task to check for needed interventions."""
    loop = await get_cognitive_loop()
    await loop.run_periodic_check()