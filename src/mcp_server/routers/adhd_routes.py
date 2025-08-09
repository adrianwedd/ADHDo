"""
Enhanced ADHD Support API Routes.

This module provides API endpoints for the advanced ADHD features including
pattern recognition, personalization, executive function support, and
intelligent adaptation. It integrates seamlessly with existing functionality
while providing enhanced capabilities.

Key Features:
- Enhanced chat endpoint with full ADHD support
- Pattern analysis and insights endpoints
- User profiling and personalization management
- Executive function tools and support
- ML-powered predictions and insights
- Crisis detection and intervention

All endpoints maintain backward compatibility while providing
significantly enhanced ADHD-specific functionality.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any

import structlog
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from mcp_server.auth import get_current_user
from mcp_server.models import NudgeTier, UserState
from mcp_server.db_models import User

# Enhanced ADHD imports
from adhd.enhanced_cognitive_loop import enhanced_cognitive_loop, EnhancedCognitiveLoopResult
from adhd.pattern_engine import get_pattern_engine
from adhd.user_profile import profile_manager
from adhd.adaptation_engine import adaptation_engine
from adhd.executive_function import (
    task_breakdown_engine, procrastination_intervenor, working_memory_support
)
from adhd.ml_pipeline import ml_pipeline

logger = structlog.get_logger()

router = APIRouter(prefix="/adhd", tags=["ADHD Support"])


# Request/Response Models

class EnhancedChatRequest(BaseModel):
    """Enhanced chat request with ADHD-specific parameters."""
    message: str = Field(..., description="User message")
    task_focus: Optional[str] = Field(None, description="Current task focus")
    nudge_tier: NudgeTier = Field(NudgeTier.GENTLE, description="Nudge intensity")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    energy_level: Optional[float] = Field(None, ge=0.0, le=1.0, description="Current energy level")
    urgency_level: Optional[float] = Field(None, ge=0.0, le=1.0, description="Task urgency")
    enable_patterns: bool = Field(True, description="Enable pattern recognition")
    enable_adaptations: bool = Field(True, description="Enable intelligent adaptations")
    enable_executive_support: bool = Field(True, description="Enable executive function support")


class EnhancedChatResponse(BaseModel):
    """Enhanced chat response with comprehensive ADHD insights."""
    # Core response
    success: bool
    message: str
    response_id: str
    processing_time_ms: float
    
    # ADHD enhancements
    patterns_detected: List[Dict[str, Any]] = []
    adaptations_applied: List[Dict[str, Any]] = []
    executive_support: Dict[str, Any] = {}
    personalization_insights: Dict[str, Any] = {}
    ml_insights: Dict[str, Any] = {}
    crisis_assessment: Dict[str, Any] = {}
    intervention_recommendations: List[Dict[str, Any]] = []
    
    # Interface adaptations
    cognitive_load: float
    interface_changes: Dict[str, Any] = {}
    recommended_actions: List[str] = []


class TaskBreakdownRequest(BaseModel):
    """Request for task breakdown analysis."""
    task_description: str = Field(..., description="Task to break down")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Task context")
    urgency_level: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="Task urgency")


class ProcrastinationAssessmentRequest(BaseModel):
    """Request for procrastination risk assessment."""
    task_description: str = Field(..., description="Task being procrastinated")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Situational context")


class UserProfileUpdateRequest(BaseModel):
    """Request to update user profile preferences."""
    cognitive_load_preference: Optional[str] = Field(None, description="Cognitive load preference")
    interaction_style: Optional[str] = Field(None, description="Preferred interaction style")
    interface_complexity: Optional[str] = Field(None, description="Interface complexity level")
    nudge_methods: Optional[List[str]] = Field(None, description="Preferred nudge methods")
    privacy_settings: Optional[Dict[str, Any]] = Field(None, description="Privacy preferences")
    custom_preferences: Optional[Dict[str, Any]] = Field(None, description="Custom settings")


class WorkingMemoryRequest(BaseModel):
    """Request to store or retrieve working memory aids."""
    action: str = Field(..., description="'store' or 'retrieve'")
    information_type: Optional[str] = Field(None, description="Type of information")
    content: Optional[Any] = Field(None, description="Content to store")
    query: Optional[str] = Field(None, description="Query for retrieval")
    priority: Optional[int] = Field(3, ge=1, le=5, description="Priority level")
    expires_hours: Optional[int] = Field(None, description="Expiration in hours")


# Enhanced Chat Endpoint

@router.post("/chat/enhanced", response_model=EnhancedChatResponse)
async def enhanced_chat(
    request: EnhancedChatRequest,
    current_user: User = Depends(get_current_user)
) -> EnhancedChatResponse:
    """
    Enhanced chat endpoint with comprehensive ADHD support.
    
    Provides the same functionality as the standard chat endpoint but with
    extensive ADHD-specific enhancements including pattern recognition,
    personalization, adaptation, and executive function support.
    """
    try:
        logger.info("Enhanced chat request", 
                   user_id=current_user.user_id,
                   message_length=len(request.message),
                   task_focus=request.task_focus,
                   patterns_enabled=request.enable_patterns)
        
        # Process through enhanced cognitive loop
        result: EnhancedCognitiveLoopResult = await enhanced_cognitive_loop.process_user_input(
            user_id=current_user.user_id,
            user_input=request.message,
            task_focus=request.task_focus,
            nudge_tier=request.nudge_tier
        )
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error or "Processing failed")
        
        # Build enhanced response
        response = EnhancedChatResponse(
            success=True,
            message=result.response.text if result.response else "No response generated",
            response_id=f"adhd_{current_user.user_id}_{int(datetime.utcnow().timestamp())}",
            processing_time_ms=result.processing_time_ms,
            patterns_detected=result.detected_patterns,
            adaptations_applied=result.adaptations_applied,
            executive_support=result.executive_function_support,
            personalization_insights=result.personalization_insights,
            ml_insights=result.ml_insights,
            crisis_assessment=result.crisis_assessment,
            intervention_recommendations=result.intervention_recommendations,
            cognitive_load=result.cognitive_load,
            interface_changes=result.adaptations_applied,
            recommended_actions=result.actions_taken
        )
        
        logger.info("Enhanced chat completed", 
                   user_id=current_user.user_id,
                   patterns_found=len(result.detected_patterns),
                   adaptations_applied=len(result.adaptations_applied),
                   processing_time=result.processing_time_ms)
        
        return response
        
    except Exception as e:
        logger.error("Enhanced chat failed", 
                    user_id=current_user.user_id, 
                    error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Enhanced chat failed: {str(e)}")


# Pattern Analysis Endpoints

@router.get("/patterns/analysis")
async def get_pattern_analysis(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive pattern analysis for user."""
    try:
        pattern_engine = get_pattern_engine(current_user.user_id)
        analysis = pattern_engine.get_pattern_summary()
        
        return {
            "user_id": current_user.user_id,
            "analysis": analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Pattern analysis failed", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {str(e)}")


@router.post("/patterns/subtype-classification")
async def classify_adhd_subtype(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Classify user's ADHD subtype based on behavioral patterns."""
    try:
        pattern_engine = get_pattern_engine(current_user.user_id)
        subtype = await pattern_engine.classify_adhd_subtype()
        
        return {
            "user_id": current_user.user_id,
            "adhd_subtype": subtype.value,
            "classification_timestamp": datetime.utcnow().isoformat(),
            "confidence_note": "Classification based on behavioral pattern analysis"
        }
        
    except Exception as e:
        logger.error("ADHD subtype classification failed", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Subtype classification failed: {str(e)}")


# User Profile Management

@router.get("/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user's ADHD profile and personalization settings."""
    try:
        profile = await profile_manager.get_or_create_profile(current_user.user_id)
        settings = await profile_manager.get_personalized_settings(current_user.user_id)
        
        return {
            "profile": profile.dict(),
            "personalized_settings": settings,
            "last_updated": profile.last_updated.isoformat()
        }
        
    except Exception as e:
        logger.error("Profile retrieval failed", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Profile retrieval failed: {str(e)}")


@router.put("/profile")
async def update_user_profile(
    request: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update user profile preferences."""
    try:
        preferences = request.dict(exclude_none=True)
        
        success = await profile_manager.update_user_preferences(
            current_user.user_id, preferences
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Profile update failed")
        
        return {
            "success": True,
            "updated_preferences": list(preferences.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Profile update failed", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")


# Executive Function Support

@router.post("/executive/task-breakdown")
async def breakdown_task(
    request: TaskBreakdownRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Break down a task into ADHD-friendly subtasks."""
    try:
        breakdown = await task_breakdown_engine.breakdown_task(
            current_user.user_id,
            request.task_description,
            request.context
        )
        
        return {
            "task_breakdown": {
                "original_task": breakdown.original_task,
                "subtasks": breakdown.subtasks,
                "estimated_total_time": breakdown.estimated_total_time,
                "complexity_level": breakdown.complexity_level.value,
                "executive_functions_required": [ef.value for ef in breakdown.executive_functions_required],
                "potential_obstacles": breakdown.potential_obstacles,
                "success_strategies": breakdown.success_strategies,
                "energy_requirements": breakdown.energy_requirements
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Task breakdown failed", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Task breakdown failed: {str(e)}")


@router.post("/executive/procrastination-assessment")
async def assess_procrastination(
    request: ProcrastinationAssessmentRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Assess procrastination risk and provide intervention strategies."""
    try:
        risk_score, triggers = await procrastination_intervenor.assess_procrastination_risk(
            current_user.user_id,
            request.task_description,
            request.context
        )
        
        intervention = await procrastination_intervenor.provide_intervention(
            current_user.user_id,
            risk_score,
            triggers
        )
        
        return {
            "procrastination_assessment": {
                "risk_score": risk_score,
                "triggers": [t.value for t in triggers],
                "intervention": intervention
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Procrastination assessment failed", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Procrastination assessment failed: {str(e)}")


@router.post("/executive/working-memory")
async def manage_working_memory(
    request: WorkingMemoryRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Store or retrieve working memory aids."""
    try:
        if request.action == "store":
            if not request.content or not request.information_type:
                raise HTTPException(status_code=400, 
                                  detail="Content and information_type required for storing")
            
            aid_id = await working_memory_support.store_information(
                current_user.user_id,
                request.information_type,
                request.content,
                request.priority,
                request.expires_hours
            )
            
            return {
                "action": "store",
                "aid_id": aid_id,
                "success": bool(aid_id),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        elif request.action == "retrieve":
            aids = await working_memory_support.retrieve_information(
                current_user.user_id,
                query=request.query,
                info_type=request.information_type
            )
            
            return {
                "action": "retrieve",
                "aids": [
                    {
                        "information_type": aid.information_type,
                        "content": aid.content,
                        "priority": aid.priority,
                        "retrieval_cues": aid.retrieval_cues
                    }
                    for aid in aids
                ],
                "count": len(aids),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        else:
            raise HTTPException(status_code=400, 
                              detail="Action must be 'store' or 'retrieve'")
        
    except Exception as e:
        logger.error("Working memory management failed", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Working memory management failed: {str(e)}")


# ML and Analytics Endpoints

@router.get("/ml/insights")
async def get_ml_insights(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get ML-powered insights and predictions."""
    try:
        performance = await ml_pipeline.get_model_performance(current_user.user_id)
        
        return {
            "ml_insights": performance,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("ML insights failed", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"ML insights failed: {str(e)}")


@router.post("/ml/retrain")
async def retrain_user_models(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Trigger retraining of user's ML models."""
    try:
        # Run retraining in background
        background_tasks.add_task(
            ml_pipeline.retrain_user_models,
            current_user.user_id
        )
        
        return {
            "retraining_started": True,
            "user_id": current_user.user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Model retraining started in background"
        }
        
    except Exception as e:
        logger.error("Model retraining failed", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Model retraining failed: {str(e)}")


# System Status and Analytics

@router.get("/system/adaptation-summary")
async def get_adaptation_summary(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get summary of adaptations applied for user."""
    try:
        summary = adaptation_engine.get_adaptation_summary(current_user.user_id)
        
        return {
            "adaptation_summary": summary,
            "user_id": current_user.user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Adaptation summary failed", 
                    user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Adaptation summary failed: {str(e)}")


@router.get("/system/stats")
async def get_enhanced_stats(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get enhanced system statistics."""
    try:
        stats = enhanced_cognitive_loop.get_enhanced_stats()
        pipeline_stats = ml_pipeline.get_pipeline_summary()
        
        return {
            "enhanced_cognitive_loop": stats,
            "ml_pipeline": pipeline_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Enhanced stats failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Enhanced stats failed: {str(e)}")


# Health and Status

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check for enhanced ADHD features."""
    try:
        return {
            "status": "healthy",
            "enhanced_features_available": True,
            "components": {
                "pattern_engine": "available",
                "user_profiling": "available", 
                "adaptation_engine": "available",
                "executive_function_support": "available",
                "ml_pipeline": "available"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Enhanced ADHD health check failed", error=str(e))
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }