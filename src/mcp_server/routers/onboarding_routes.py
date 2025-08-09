"""
Enhanced Onboarding Routes - Comprehensive ADHD-optimized onboarding system.

Provides progressive disclosure onboarding with:
- ADHD assessment and personalization
- Google Calendar integration
- Telegram bot setup  
- Crisis support configuration
- Energy pattern mapping
- API access for power users
- Real-time progress tracking
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import structlog

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..models import User
from ..onboarding import onboarding_manager, OnboardingStep
from ..health_monitor import health_monitor
from ..metrics import metrics_collector

logger = structlog.get_logger()

# Create router
onboarding_router = APIRouter(
    prefix="/api/onboarding",
    tags=["Enhanced Onboarding"],
    dependencies=[Depends(get_current_user)]
)


class OnboardingStepRequest(BaseModel):
    """Request model for processing onboarding steps."""
    step_data: Dict[str, Any] = Field(..., description="Data for the current step")
    skip: bool = Field(False, description="Whether to skip this step")
    action: Optional[str] = Field(None, description="Specific action to take")


class OnboardingProgressResponse(BaseModel):
    """Response model for onboarding progress."""
    status: str = Field(..., description="Overall onboarding status")
    current_step: str = Field(..., description="Current onboarding step")
    progress_percentage: float = Field(..., description="Completion percentage")
    completed_steps: List[str] = Field(..., description="List of completed steps")
    total_steps: int = Field(..., description="Total number of steps")
    estimated_remaining_minutes: int = Field(..., description="Estimated time to complete")
    can_resume: bool = Field(..., description="Whether onboarding can be resumed")


@onboarding_router.get("/status",
                      summary="Get enhanced onboarding progress",
                      description="Returns detailed onboarding progress with step tracking and analytics",
                      response_model=OnboardingProgressResponse)
async def get_enhanced_onboarding_status(current_user: User = Depends(get_current_user)) -> OnboardingProgressResponse:
    """
    Get comprehensive onboarding status and progress tracking.
    
    Returns detailed information about:
    - Current step and overall progress
    - Completed vs remaining steps  
    - Time estimates and analytics
    - Resume capability
    """
    try:
        progress_data = await onboarding_manager.get_onboarding_progress(current_user.id)
        
        health_monitor.record_metric("onboarding_status_checks", 1)
        
        return OnboardingProgressResponse(
            status=progress_data.get("status", "not_started"),
            current_step=progress_data.get("current_step", "welcome"),
            progress_percentage=progress_data.get("progress_percentage", 0),
            completed_steps=progress_data.get("completed_steps", []),
            total_steps=progress_data.get("total_steps", 11),
            estimated_remaining_minutes=progress_data.get("estimated_remaining_minutes", 12),
            can_resume=progress_data.get("can_resume", True)
        )
        
    except Exception as e:
        logger.error("Failed to get enhanced onboarding status", 
                    user_id=current_user.id, error=str(e))
        health_monitor.record_error("get_enhanced_onboarding_status", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve onboarding status")


@onboarding_router.post("/start",
                       summary="Start enhanced onboarding",
                       description="Initialize comprehensive ADHD-optimized onboarding process")
async def start_enhanced_onboarding(
    skip_to_step: Optional[str] = Query(None, description="Skip directly to a specific step"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Start the enhanced onboarding process.
    
    Features:
    - Progressive disclosure design
    - ADHD-friendly pacing
    - Resume capability
    - Comprehensive feature integration
    """
    try:
        skip_to_step_enum = None
        if skip_to_step:
            try:
                skip_to_step_enum = OnboardingStep(skip_to_step)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid step: {skip_to_step}")
        
        onboarding_session = await onboarding_manager.start_onboarding(
            current_user.id, 
            skip_to_step_enum
        )
        
        # Get initial step content
        step_content = await onboarding_manager._get_step_content(
            onboarding_session, 
            onboarding_session.current_step
        )
        
        health_monitor.record_metric("enhanced_onboarding_sessions_started", 1)
        logger.info("Enhanced onboarding session started", 
                   user_id=current_user.id,
                   skip_to_step=skip_to_step)
        
        return {
            "success": True,
            "message": "Enhanced onboarding started successfully",
            "session_id": current_user.id,
            "started_at": onboarding_session.started_at.isoformat(),
            **step_content
        }
        
    except Exception as e:
        logger.error("Failed to start enhanced onboarding", 
                    user_id=current_user.id, error=str(e))
        health_monitor.record_error("start_enhanced_onboarding", str(e))
        raise HTTPException(status_code=500, detail="Failed to start enhanced onboarding")


@onboarding_router.post("/step",
                       summary="Process onboarding step",
                       description="Process user input for current onboarding step with progress tracking")
async def process_enhanced_onboarding_step(
    request: OnboardingStepRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Process user input for the current onboarding step.
    
    Features:
    - Comprehensive step validation
    - Progress tracking and analytics
    - Error handling and retry logic
    - Next step preparation
    """
    try:
        # Add skip flag to step data if requested
        step_data = request.step_data.copy()
        if request.skip:
            step_data["skip"] = True
        if request.action:
            step_data["action"] = request.action
        
        result = await onboarding_manager.process_step(current_user.id, step_data)
        
        # Track metrics
        health_monitor.record_metric("enhanced_onboarding_steps_processed", 1)
        if request.skip:
            health_monitor.record_metric("onboarding_steps_skipped", 1)
        
        # Add user context to response
        result["user_id"] = current_user.id
        result["processed_at"] = datetime.utcnow().isoformat()
        
        logger.info("Enhanced onboarding step processed", 
                   user_id=current_user.id,
                   step_status=result.get("status"),
                   next_step=result.get("next_step"),
                   skipped=request.skip)
        
        return result
        
    except ValueError as e:
        logger.warning("Invalid onboarding step request", 
                      user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to process enhanced onboarding step", 
                    user_id=current_user.id, error=str(e))
        health_monitor.record_error("process_enhanced_onboarding_step", str(e))
        raise HTTPException(status_code=500, detail="Failed to process onboarding step")


@onboarding_router.post("/skip-to/{step}",
                       summary="Skip to specific onboarding step",
                       description="Jump directly to a specific onboarding step")
async def skip_to_onboarding_step(
    step: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Skip directly to a specific onboarding step.
    
    Useful for:
    - Users who want to configure specific features
    - Testing and development
    - Resume from abandoned sessions
    """
    try:
        # Validate step
        try:
            target_step = OnboardingStep(step)
        except ValueError:
            available_steps = [s.value for s in OnboardingStep]
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid step '{step}'. Available: {available_steps}"
            )
        
        result = await onboarding_manager.skip_to_step(current_user.id, target_step)
        
        health_monitor.record_metric("onboarding_step_skips", 1)
        logger.info("Skipped to onboarding step", 
                   user_id=current_user.id, target_step=step)
        
        return {
            "success": True,
            "message": f"Skipped to step: {step}",
            "skipped_to": step,
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to skip to onboarding step", 
                    user_id=current_user.id, target_step=step, error=str(e))
        health_monitor.record_error("skip_to_onboarding_step", str(e))
        raise HTTPException(status_code=500, detail="Failed to skip to onboarding step")


@onboarding_router.get("/steps",
                      summary="Get available onboarding steps",
                      description="Returns list of all onboarding steps with descriptions")
async def get_onboarding_steps(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get comprehensive list of onboarding steps.
    
    Returns step information for:
    - Navigation and progress display
    - Direct step access
    - Development and testing
    """
    try:
        steps_info = []
        for i, step in enumerate(OnboardingStep, 1):
            step_info = {
                "step": step.value,
                "step_number": i,
                "title": _get_step_title(step),
                "description": _get_step_description(step),
                "estimated_time": _get_step_estimated_time(step),
                "can_skip": _can_skip_step(step),
                "requires_external_auth": _requires_external_auth(step)
            }
            steps_info.append(step_info)
        
        return {
            "steps": steps_info,
            "total_steps": len(OnboardingStep),
            "estimated_total_time": "10-12 minutes",
            "features_covered": [
                "ADHD Assessment & Personalization",
                "Energy Pattern Mapping",
                "Crisis Support & Safety Net",
                "Google Calendar Integration", 
                "Telegram Bot Setup",
                "API Access for Power Users",
                "Comprehensive Preference Configuration"
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get onboarding steps", user_id=current_user.id, error=str(e))
        health_monitor.record_error("get_onboarding_steps", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve onboarding steps")


@onboarding_router.delete("/reset",
                         summary="Reset onboarding progress",
                         description="Reset onboarding to start fresh (development/testing)")
async def reset_onboarding_progress(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Reset onboarding progress to start fresh.
    
    **Warning:** This will lose all onboarding progress and collected preferences.
    Primarily intended for development and testing.
    """
    try:
        # Remove from onboarding sessions
        if current_user.id in onboarding_manager._onboarding_sessions:
            del onboarding_manager._onboarding_sessions[current_user.id]
        
        if current_user.id in onboarding_manager._progress_tracking:
            del onboarding_manager._progress_tracking[current_user.id]
        
        if current_user.id in onboarding_manager._analytics:
            del onboarding_manager._analytics[current_user.id]
        
        health_monitor.record_metric("onboarding_resets", 1)
        logger.info("Onboarding progress reset", user_id=current_user.id)
        
        return {
            "success": True,
            "message": "Onboarding progress has been reset",
            "reset_at": datetime.utcnow().isoformat(),
            "next_action": "Call /start to begin fresh onboarding"
        }
        
    except Exception as e:
        logger.error("Failed to reset onboarding progress", user_id=current_user.id, error=str(e))
        health_monitor.record_error("reset_onboarding_progress", str(e))
        raise HTTPException(status_code=500, detail="Failed to reset onboarding progress")


@onboarding_router.get("/analytics",
                      summary="Get onboarding analytics",
                      description="Returns onboarding completion analytics and insights")
async def get_onboarding_analytics(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get detailed onboarding analytics and insights.
    
    Returns:
    - Completion metrics
    - Time spent per step
    - Feature adoption rates
    - Personalization insights
    """
    try:
        analytics = onboarding_manager._analytics.get(current_user.id)
        progress = onboarding_manager._progress_tracking.get(current_user.id, {})
        
        if not analytics:
            return {
                "status": "no_data",
                "message": "No onboarding analytics available"
            }
        
        # Calculate step-by-step timing
        step_timings = {}
        for step, progress_data in progress.items():
            if progress_data.completed_at and progress_data.started_at:
                duration = (progress_data.completed_at - progress_data.started_at).total_seconds()
                step_timings[step.value] = {
                    "duration_seconds": duration,
                    "completed": progress_data.is_completed,
                    "skipped": progress_data.is_skipped,
                    "retry_count": progress_data.retry_count
                }
        
        return {
            "analytics": {
                "total_time_minutes": analytics.total_time_minutes,
                "steps_completed": analytics.steps_completed,
                "steps_skipped": analytics.steps_skipped,
                "feature_adoption": analytics.feature_adoption,
                "satisfaction_rating": analytics.satisfaction_rating
            },
            "step_timings": step_timings,
            "completion_rate": (analytics.steps_completed / len(OnboardingStep)) * 100,
            "efficiency_score": _calculate_efficiency_score(analytics, step_timings)
        }
        
    except Exception as e:
        logger.error("Failed to get onboarding analytics", user_id=current_user.id, error=str(e))
        health_monitor.record_error("get_onboarding_analytics", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve onboarding analytics")


# Helper functions for step metadata

def _get_step_title(step: OnboardingStep) -> str:
    """Get human-readable title for onboarding step."""
    titles = {
        OnboardingStep.WELCOME: "Welcome to Your ADHD Support System!",
        OnboardingStep.PRIVACY_AGREEMENT: "Privacy & Data Protection",
        OnboardingStep.ADHD_ASSESSMENT: "Your ADHD Profile",
        OnboardingStep.ENERGY_PATTERNS: "Energy & Focus Patterns",
        OnboardingStep.CRISIS_SUPPORT: "Crisis Support & Safety",
        OnboardingStep.NUDGE_PREFERENCES: "Nudge & Communication Preferences",
        OnboardingStep.GOOGLE_CALENDAR: "Google Calendar Integration",
        OnboardingStep.TELEGRAM_SETUP: "Telegram Bot Setup",
        OnboardingStep.API_INTRODUCTION: "API Access (Optional)",
        OnboardingStep.FIRST_SUCCESS: "Your First Success!",
        OnboardingStep.CELEBRATION: "Setup Complete!",
        OnboardingStep.COMPLETED: "Onboarding Completed"
    }
    return titles.get(step, step.value.replace('_', ' ').title())


def _get_step_description(step: OnboardingStep) -> str:
    """Get description for onboarding step."""
    descriptions = {
        OnboardingStep.WELCOME: "Introduction to your AI-powered executive function support system",
        OnboardingStep.PRIVACY_AGREEMENT: "Review privacy policies and data collection consent",
        OnboardingStep.ADHD_ASSESSMENT: "Comprehensive ADHD assessment for personalization",
        OnboardingStep.ENERGY_PATTERNS: "Map your daily energy and focus patterns",
        OnboardingStep.CRISIS_SUPPORT: "Configure crisis detection and safety resources",
        OnboardingStep.NUDGE_PREFERENCES: "Set up personalized nudges and communication style",
        OnboardingStep.GOOGLE_CALENDAR: "Connect calendar for context-aware support",
        OnboardingStep.TELEGRAM_SETUP: "Set up mobile chat and notifications",
        OnboardingStep.API_INTRODUCTION: "Generate API access for developers",
        OnboardingStep.FIRST_SUCCESS: "Set up your first task for immediate value",
        OnboardingStep.CELEBRATION: "Celebrate setup completion and next steps",
        OnboardingStep.COMPLETED: "Onboarding process fully completed"
    }
    return descriptions.get(step, "Onboarding step configuration")


def _get_step_estimated_time(step: OnboardingStep) -> str:
    """Get estimated time for onboarding step."""
    times = {
        OnboardingStep.WELCOME: "1 minute",
        OnboardingStep.PRIVACY_AGREEMENT: "1 minute", 
        OnboardingStep.ADHD_ASSESSMENT: "3-4 minutes",
        OnboardingStep.ENERGY_PATTERNS: "2-3 minutes",
        OnboardingStep.CRISIS_SUPPORT: "2 minutes",
        OnboardingStep.NUDGE_PREFERENCES: "2 minutes",
        OnboardingStep.GOOGLE_CALENDAR: "1 minute",
        OnboardingStep.TELEGRAM_SETUP: "1-2 minutes",
        OnboardingStep.API_INTRODUCTION: "1 minute",
        OnboardingStep.FIRST_SUCCESS: "1 minute",
        OnboardingStep.CELEBRATION: "30 seconds",
        OnboardingStep.COMPLETED: "Complete"
    }
    return times.get(step, "1-2 minutes")


def _can_skip_step(step: OnboardingStep) -> bool:
    """Check if step can be skipped."""
    required_steps = {
        OnboardingStep.WELCOME,
        OnboardingStep.PRIVACY_AGREEMENT,
        OnboardingStep.FIRST_SUCCESS,
        OnboardingStep.CELEBRATION
    }
    return step not in required_steps


def _requires_external_auth(step: OnboardingStep) -> bool:
    """Check if step requires external authentication."""
    external_auth_steps = {
        OnboardingStep.GOOGLE_CALENDAR,
        OnboardingStep.TELEGRAM_SETUP
    }
    return step in external_auth_steps


def _calculate_efficiency_score(analytics, step_timings: Dict) -> float:
    """Calculate onboarding efficiency score (0-100)."""
    if not analytics.total_time_minutes:
        return 0.0
    
    # Base score on completion rate and time efficiency
    completion_rate = analytics.steps_completed / len(OnboardingStep)
    
    # Ideal time is 12 minutes, score decreases for longer times
    ideal_time = 12.0
    time_efficiency = min(1.0, ideal_time / analytics.total_time_minutes) if analytics.total_time_minutes else 0
    
    # Penalty for skipped steps (but not too harsh)
    skip_penalty = analytics.steps_skipped * 0.05
    
    efficiency_score = (completion_rate * 0.6 + time_efficiency * 0.4 - skip_penalty) * 100
    return max(0.0, min(100.0, efficiency_score))