"""
Beta testing and onboarding routes - Beta user management and quick setup.

Extracted from monolithic main.py to improve code organization and maintainability.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from ..models import User
from ..auth import get_current_user
from ..beta_onboarding import beta_onboarding, QuickSetupRequest, BetaInvite
from ..onboarding import onboarding_manager
from ..health_monitor import health_monitor

beta_router = APIRouter(prefix="/api/beta", tags=["Beta"])


class CreateUserRequest(BaseModel):
    email: str
    username: Optional[str] = None
    invite_code: str


@beta_router.post("/create-invite")
async def create_beta_invite(
    invite_data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new beta invite code.
    
    Allows authorized users to create invitation codes
    for beta testing program participants.
    """
    try:
        # Check if user has permission to create invites
        # This should be expanded with proper role checking
        if not getattr(current_user, 'is_admin', False):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        invite = await beta_onboarding.create_invite(
            created_by=current_user.id,
            **invite_data
        )
        
        health_monitor.record_metric("beta_invites_created", 1)
        
        return {
            "invite_code": invite.code,
            "expires_at": invite.expires_at,
            "max_uses": invite.max_uses,
            "created_by": current_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("create_beta_invite", str(e))
        raise HTTPException(status_code=500, detail="Failed to create beta invite")


@beta_router.get("/invite/{invite_code}")
async def get_beta_invite(invite_code: str) -> dict:
    """
    Get beta invite information for validation.
    
    Returns invite details and validity status
    for the beta registration process.
    """
    try:
        invite = await beta_onboarding.get_invite(invite_code)
        
        if not invite:
            raise HTTPException(status_code=404, detail="Beta invite not found")
        
        if not invite.is_valid():
            raise HTTPException(status_code=410, detail="Beta invite has expired or been exhausted")
        
        return {
            "code": invite.code,
            "valid": True,
            "expires_at": invite.expires_at,
            "uses_remaining": invite.max_uses - invite.uses_count if invite.max_uses else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("get_beta_invite", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve beta invite")


@beta_router.post("/quick-setup")
async def beta_quick_setup(setup_request: QuickSetupRequest) -> dict:
    """
    Quick setup endpoint for beta users.
    
    Streamlined onboarding process for beta testers
    with pre-configured ADHD-optimized settings.
    """
    try:
        # Validate beta invite
        invite = await beta_onboarding.get_invite(setup_request.invite_code)
        if not invite or not invite.is_valid():
            raise HTTPException(status_code=400, detail="Invalid or expired beta invite")
        
        # Process quick setup
        setup_result = await beta_onboarding.quick_setup(setup_request)
        
        health_monitor.record_metric("beta_quick_setups", 1)
        
        return setup_result
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("beta_quick_setup", str(e))
        raise HTTPException(status_code=500, detail="Beta setup failed")


@beta_router.get("/setup")
async def beta_setup_page(invite: str):
    """
    Serve beta setup page with invite pre-filled.
    
    Returns the HTML setup page for beta user onboarding
    with invite code validation and form pre-population.
    """
    try:
        # Validate invite exists (but don't consume it yet)
        invite_obj = await beta_onboarding.get_invite(invite)
        if not invite_obj:
            raise HTTPException(status_code=404, detail="Beta invite not found")
        
        # Return setup page HTML
        return FileResponse(
            path="/home/pi/repos/ADHDo/static/mcp_setup.html",
            media_type="text/html"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("beta_setup_page", str(e))
        raise HTTPException(status_code=500, detail="Failed to serve beta setup page")


@beta_router.get("/stats")
async def get_beta_stats() -> dict:
    """
    Get beta testing program statistics.
    
    Returns metrics and insights about beta testing
    participation and system usage.
    """
    try:
        stats = await beta_onboarding.get_beta_stats()
        return stats
        
    except Exception as e:
        health_monitor.record_error("get_beta_stats", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve beta stats")


# Onboarding endpoints (moved from main routes)
@beta_router.get("/onboarding/status",
                 summary="Get user onboarding status",
                 description="Returns the current onboarding progress and next steps for the user")
async def get_onboarding_status(current_user: User = Depends(get_current_user)) -> dict:
    """
    Get current user's onboarding status and progress.
    
    Provides detailed information about completed steps,
    remaining tasks, and personalized next actions.
    """
    try:
        status = await onboarding_manager.get_user_status(current_user.id)
        
        return {
            "user_id": current_user.id,
            "onboarding_completed": status.get("completed", False),
            "current_step": status.get("current_step"),
            "steps_completed": status.get("steps_completed", []),
            "next_steps": status.get("next_steps", []),
            "completion_percentage": status.get("completion_percentage", 0),
            "estimated_time_remaining": status.get("estimated_time_remaining")
        }
        
    except Exception as e:
        health_monitor.record_error("get_onboarding_status", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve onboarding status")


@beta_router.post("/onboarding/start")
async def start_onboarding(current_user: User = Depends(get_current_user)) -> dict:
    """
    Initialize the onboarding process for a user.
    
    Sets up personalized onboarding flow based on user
    preferences and ADHD-specific needs assessment.
    """
    try:
        result = await onboarding_manager.start_onboarding(current_user.id)
        
        health_monitor.record_metric("onboarding_sessions_started", 1)
        
        return result
        
    except Exception as e:
        health_monitor.record_error("start_onboarding", str(e))
        raise HTTPException(status_code=500, detail="Failed to start onboarding")


@beta_router.post("/onboarding/step")
async def process_onboarding_step(
    step_data: dict,
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Process a completed onboarding step.
    
    Handles user responses to onboarding questions
    and advances to the next appropriate step.
    """
    try:
        result = await onboarding_manager.process_step(current_user.id, step_data)
        
        health_monitor.record_metric("onboarding_steps_completed", 1)
        
        return result
        
    except Exception as e:
        health_monitor.record_error("process_onboarding_step", str(e))
        raise HTTPException(status_code=500, detail="Failed to process onboarding step")


@beta_router.post("/onboarding/skip")
async def skip_onboarding(current_user: User = Depends(get_current_user)) -> dict:
    """
    Skip onboarding process (with user consent).
    
    Allows users to bypass onboarding while still
    providing essential system configuration.
    """
    try:
        result = await onboarding_manager.skip_onboarding(current_user.id)
        
        health_monitor.record_metric("onboarding_sessions_skipped", 1)
        
        return result
        
    except Exception as e:
        health_monitor.record_error("skip_onboarding", str(e))
        raise HTTPException(status_code=500, detail="Failed to skip onboarding")