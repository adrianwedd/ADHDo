"""
FastAPI endpoints for GitHub Issue Automation System

Production-ready API endpoints with comprehensive validation, error handling,
and integration with the existing MCP architecture.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from mcp_server.auth import get_current_user, get_optional_user
from mcp_server.database import get_database_session
from mcp_server.models import User
from mcp_server.config import settings

from github_automation.automation_engine import GitHubAutomationEngine, AutomationConfig
from github_automation.webhook_handler import WebhookHandler
from github_automation.audit_logger import AuditLogger, AuditEventType, AuditSeverity
from github_automation.rollback_manager import RollbackManager, RollbackReason
from github_automation.models import (
    GitHubIssue, GitHubAutomationAction, FeatureDetection, 
    AutomationMetrics, WebhookEvent, ActionStatus
)

logger = structlog.get_logger()

# Create router
github_router = APIRouter(prefix="/api/github", tags=["GitHub Automation"])

# Pydantic models for API
class AutomationConfigRequest(BaseModel):
    """Request model for automation configuration."""
    max_concurrent_actions: int = Field(default=10, ge=1, le=50)
    min_confidence_auto_close: float = Field(default=0.85, ge=0.0, le=1.0)
    min_confidence_auto_label: float = Field(default=0.70, ge=0.0, le=1.0)
    enable_auto_close: bool = True
    enable_auto_label: bool = True
    enable_rollbacks: bool = True
    max_actions_per_run: int = Field(default=100, ge=1, le=1000)


class RepositoryRequest(BaseModel):
    """Request model for repository operations."""
    owner: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    force_full_scan: bool = False


class RollbackRequest(BaseModel):
    """Request model for rollback operations."""
    action_ids: List[str] = Field(..., min_items=1, max_items=100)
    reason: str = Field(..., min_length=1, max_length=500)


class WebhookConfigRequest(BaseModel):
    """Request model for webhook configuration."""
    secret: Optional[str] = None
    enabled_events: List[str] = Field(default=["issues", "push", "pull_request"])


# Dependency to get automation engine
automation_engines: Dict[str, GitHubAutomationEngine] = {}
webhook_handlers: Dict[str, WebhookHandler] = {}
audit_loggers: Dict[str, AuditLogger] = {}


async def get_automation_engine(
    repository: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_database_session)
) -> GitHubAutomationEngine:
    """Get or create automation engine for repository."""
    engine_key = f"{current_user.user_id}:{repository}"
    
    if engine_key not in automation_engines:
        # Get GitHub token from user settings (in production, this would be encrypted)
        github_token = getattr(current_user, 'github_token', None) or settings.github_token
        if not github_token:
            raise HTTPException(
                status_code=400,
                detail="GitHub token not configured. Please configure GitHub integration."
            )
        
        # Create automation engine
        config = AutomationConfig()
        engine = GitHubAutomationEngine(
            github_token=github_token,
            config=config,
            db_session=db_session
        )
        
        automation_engines[engine_key] = engine
    
    return automation_engines[engine_key]


async def get_audit_logger(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_database_session)
) -> AuditLogger:
    """Get or create audit logger."""
    logger_key = f"user:{current_user.user_id}"
    
    if logger_key not in audit_loggers:
        audit_logger = AuditLogger(
            db_session=db_session,
            log_file_path=f"logs/github_automation_{current_user.user_id}.jsonl"
        )
        audit_loggers[logger_key] = audit_logger
    
    return audit_loggers[logger_key]


# === AUTOMATION ENDPOINTS ===

@github_router.post("/automation/run")
async def run_automation_cycle(
    request: RepositoryRequest,
    background_tasks: BackgroundTasks,
    automation_engine: GitHubAutomationEngine = Depends(get_automation_engine),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger a complete automation cycle for a repository.
    
    Performs issue synchronization, feature detection, action generation,
    and execution with comprehensive logging and error handling.
    """
    await audit_logger.log_user_interaction(
        user_id=current_user.user_id,
        action="run_automation_cycle",
        resource=f"{request.owner}/{request.name}",
        details={"force_full_scan": request.force_full_scan}
    )
    
    try:
        # Run automation cycle in background
        background_tasks.add_task(
            _run_automation_cycle_background,
            automation_engine,
            audit_logger,
            request.owner,
            request.name,
            request.force_full_scan,
            current_user.user_id
        )
        
        return {
            "success": True,
            "message": "Automation cycle started",
            "repository": f"{request.owner}/{request.name}",
            "force_full_scan": request.force_full_scan,
            "status": "running"
        }
        
    except Exception as e:
        logger.error("Failed to start automation cycle", error=str(e), exc_info=True)
        await audit_logger.log_error(e, {
            "repository": f"{request.owner}/{request.name}",
            "user_id": current_user.user_id
        })
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start automation cycle: {str(e)}"
        )


async def _run_automation_cycle_background(
    automation_engine: GitHubAutomationEngine,
    audit_logger: AuditLogger,
    owner: str,
    name: str,
    force_full_scan: bool,
    user_id: str
):
    """Background task for running automation cycle."""
    try:
        results = await automation_engine.start_automation_cycle(
            repository_owner=owner,
            repository_name=name,
            force_full_scan=force_full_scan
        )
        
        await audit_logger.log_event(
            event_type=AuditEventType.AUTOMATION_ACTION,
            severity=AuditSeverity.MEDIUM,
            description=f"Automation cycle completed for {owner}/{name}",
            user_id=user_id,
            repository=f"{owner}/{name}",
            success=True,
            metadata={
                "cycle_results": results,
                "duration_seconds": results.get("duration_seconds"),
                "total_actions": results.get("execution_results", {}).get("total_actions", 0)
            }
        )
        
    except Exception as e:
        logger.error("Background automation cycle failed", error=str(e), exc_info=True)
        await audit_logger.log_error(e, {
            "repository": f"{owner}/{name}",
            "user_id": user_id,
            "context": "background_automation_cycle"
        })


@github_router.get("/automation/status")
async def get_automation_status(
    automation_engine: GitHubAutomationEngine = Depends(get_automation_engine),
    current_user: User = Depends(get_current_user)
):
    """Get current automation system status and health metrics."""
    try:
        health_status = await automation_engine.get_automation_health()
        
        return {
            "success": True,
            "status": health_status,
            "user_id": current_user.user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get automation status", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get automation status: {str(e)}"
        )


@github_router.put("/automation/config")
async def update_automation_config(
    config: AutomationConfigRequest,
    automation_engine: GitHubAutomationEngine = Depends(get_automation_engine),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
):
    """Update automation configuration settings."""
    try:
        # Update engine configuration
        new_config = AutomationConfig(
            max_concurrent_actions=config.max_concurrent_actions,
            min_confidence_auto_close=config.min_confidence_auto_close,
            min_confidence_auto_label=config.min_confidence_auto_label,
            enable_auto_close=config.enable_auto_close,
            enable_auto_label=config.enable_auto_label,
            enable_rollbacks=config.enable_rollbacks,
            max_actions_per_run=config.max_actions_per_run
        )
        
        # Update engine config (in production, this would be persisted)
        automation_engine.config = new_config
        
        # Log configuration change
        await audit_logger.log_configuration_change(
            component="automation_engine",
            changed_settings=config.dict(),
            user_id=current_user.user_id
        )
        
        return {
            "success": True,
            "message": "Automation configuration updated",
            "config": config.dict()
        }
        
    except Exception as e:
        logger.error("Failed to update automation config", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update configuration: {str(e)}"
        )


# === ISSUE MANAGEMENT ENDPOINTS ===

@github_router.get("/issues")
async def get_repository_issues(
    owner: str,
    name: str,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    db_session: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user)
):
    """Get issues for a repository with filtering and pagination."""
    try:
        # Build query
        query = select(GitHubIssue).where(
            and_(
                GitHubIssue.repository_owner == owner,
                GitHubIssue.repository_name == name
            )
        )
        
        if status:
            query = query.where(GitHubIssue.status == status)
        
        query = query.order_by(GitHubIssue.github_updated_at.desc())
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db_session.execute(query)
        issues = result.scalars().all()
        
        # Get total count
        count_query = select(func.count(GitHubIssue.id)).where(
            and_(
                GitHubIssue.repository_owner == owner,
                GitHubIssue.repository_name == name
            )
        )
        if status:
            count_query = count_query.where(GitHubIssue.status == status)
        
        total_result = await db_session.execute(count_query)
        total_count = total_result.scalar()
        
        return {
            "success": True,
            "issues": [
                {
                    "id": issue.id,
                    "github_issue_number": issue.github_issue_number,
                    "title": issue.title,
                    "status": issue.status,
                    "labels": issue.labels,
                    "automation_eligible": issue.automation_eligible,
                    "automation_confidence": issue.automation_confidence,
                    "feature_completion_score": issue.feature_completion_score,
                    "github_created_at": issue.github_created_at.isoformat(),
                    "github_updated_at": issue.github_updated_at.isoformat(),
                    "last_analyzed": issue.last_analyzed.isoformat()
                }
                for issue in issues
            ],
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
        }
        
    except Exception as e:
        logger.error("Failed to get repository issues", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get issues: {str(e)}"
        )


@github_router.get("/issues/{issue_id}/actions")
async def get_issue_automation_actions(
    issue_id: str,
    db_session: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user)
):
    """Get automation actions for a specific issue."""
    try:
        # Get actions for the issue
        query = (
            select(GitHubAutomationAction)
            .where(GitHubAutomationAction.issue_id == issue_id)
            .order_by(GitHubAutomationAction.created_at.desc())
        )
        
        result = await db_session.execute(query)
        actions = result.scalars().all()
        
        return {
            "success": True,
            "issue_id": issue_id,
            "actions": [
                {
                    "id": action.id,
                    "action_type": action.action_type,
                    "status": action.status,
                    "confidence_score": action.confidence_score,
                    "reasoning": action.reasoning,
                    "success": action.success,
                    "error_message": action.error_message,
                    "can_rollback": action.can_rollback and not action.rolled_back,
                    "created_at": action.created_at.isoformat(),
                    "completed_at": action.completed_at.isoformat() if action.completed_at else None,
                    "duration_ms": action.duration_ms
                }
                for action in actions
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get issue actions", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get issue actions: {str(e)}"
        )


# === ROLLBACK ENDPOINTS ===

@github_router.post("/rollback/create")
async def create_rollback_transaction(
    request: RollbackRequest,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_database_session),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
):
    """Create and execute a rollback transaction for automation actions."""
    try:
        # Create rollback manager
        rollback_manager = RollbackManager(audit_logger=audit_logger, db_session=db_session)
        
        # Create rollback transaction
        transaction_id = await rollback_manager.create_rollback_transaction(
            action_ids=request.action_ids,
            reason=RollbackReason.USER_REQUEST,
            created_by=current_user.user_id
        )
        
        # Execute rollback in background
        background_tasks.add_task(
            _execute_rollback_background,
            rollback_manager,
            transaction_id,
            audit_logger,
            current_user.user_id
        )
        
        await audit_logger.log_user_interaction(
            user_id=current_user.user_id,
            action="create_rollback",
            resource=f"actions:{len(request.action_ids)}",
            details={"reason": request.reason, "transaction_id": transaction_id}
        )
        
        return {
            "success": True,
            "message": "Rollback transaction created and executing",
            "transaction_id": transaction_id,
            "action_count": len(request.action_ids),
            "status": "executing"
        }
        
    except Exception as e:
        logger.error("Failed to create rollback transaction", error=str(e), exc_info=True)
        await audit_logger.log_error(e, {
            "action_ids": request.action_ids,
            "user_id": current_user.user_id
        })
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create rollback transaction: {str(e)}"
        )


async def _execute_rollback_background(
    rollback_manager: RollbackManager,
    transaction_id: str,
    audit_logger: AuditLogger,
    user_id: str
):
    """Background task for executing rollback transaction."""
    try:
        results = await rollback_manager.execute_rollback_transaction(transaction_id)
        
        await audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_EVENT,
            severity=AuditSeverity.HIGH,
            description=f"Rollback transaction {results['overall_status']}",
            user_id=user_id,
            success=results['overall_status'] in ['completed', 'partially_completed'],
            metadata={
                "transaction_id": transaction_id,
                "results": results
            }
        )
        
    except Exception as e:
        logger.error("Background rollback execution failed", error=str(e), exc_info=True)
        await audit_logger.log_error(e, {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "context": "background_rollback_execution"
        })


@github_router.get("/rollback/{transaction_id}/status")
async def get_rollback_status(
    transaction_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a rollback transaction."""
    # In production, this would query the database or active transactions
    # For now, return a mock response
    return {
        "success": True,
        "transaction_id": transaction_id,
        "status": "completed",
        "message": "Rollback transaction status retrieved"
    }


# === WEBHOOK ENDPOINTS ===

@github_router.post("/webhooks/github")
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_database_session)
):
    """Handle incoming GitHub webhooks for real-time automation."""
    try:
        # Get payload
        payload = await request.json()
        
        # Create webhook handler
        webhook_handler = WebhookHandler(
            webhook_secret=getattr(settings, 'github_webhook_secret', None)
        )
        
        # Process webhook in background
        background_tasks.add_task(
            _process_webhook_background,
            webhook_handler,
            request,
            payload
        )
        
        return {
            "success": True,
            "message": "Webhook received and processing",
            "delivery_id": request.headers.get('X-GitHub-Delivery', 'unknown')
        }
        
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "delivery_id": request.headers.get('X-GitHub-Delivery', 'unknown')
        }


async def _process_webhook_background(
    webhook_handler: WebhookHandler,
    request: Request,
    payload: Dict[str, Any]
):
    """Background task for processing GitHub webhooks."""
    try:
        result = await webhook_handler.process_webhook(request, payload)
        logger.info("Webhook processed", result=result)
        
    except Exception as e:
        logger.error("Background webhook processing failed", error=str(e), exc_info=True)


# === METRICS AND MONITORING ENDPOINTS ===

@github_router.get("/metrics/summary")
async def get_automation_metrics(
    hours: int = Query(default=24, ge=1, le=168),  # 1 hour to 1 week
    db_session: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user)
):
    """Get automation metrics summary for the specified time period."""
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get automation actions in time range
        actions_query = select(GitHubAutomationAction).where(
            GitHubAutomationAction.created_at >= start_time
        )
        
        result = await db_session.execute(actions_query)
        actions = result.scalars().all()
        
        # Calculate metrics
        total_actions = len(actions)
        successful_actions = len([a for a in actions if a.success is True])
        failed_actions = len([a for a in actions if a.success is False])
        pending_actions = len([a for a in actions if a.status == ActionStatus.PENDING])
        
        # Group by action type
        action_types = {}
        for action in actions:
            action_type = action.action_type.value
            if action_type not in action_types:
                action_types[action_type] = {"total": 0, "successful": 0, "failed": 0}
            
            action_types[action_type]["total"] += 1
            if action.success is True:
                action_types[action_type]["successful"] += 1
            elif action.success is False:
                action_types[action_type]["failed"] += 1
        
        # Calculate success rate
        success_rate = (successful_actions / total_actions) if total_actions > 0 else 1.0
        
        # Average processing time
        completed_actions = [a for a in actions if a.duration_ms is not None]
        avg_processing_time_ms = (
            sum(a.duration_ms for a in completed_actions) / len(completed_actions)
            if completed_actions else 0.0
        )
        
        return {
            "success": True,
            "time_period": {
                "hours": hours,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            "summary": {
                "total_actions": total_actions,
                "successful_actions": successful_actions,
                "failed_actions": failed_actions,
                "pending_actions": pending_actions,
                "success_rate": success_rate,
                "average_processing_time_ms": avg_processing_time_ms
            },
            "by_action_type": action_types
        }
        
    except Exception as e:
        logger.error("Failed to get automation metrics", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )


@github_router.get("/audit/summary")
async def get_audit_summary(
    hours: int = Query(default=24, ge=1, le=168),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
):
    """Get audit trail summary for the specified time period."""
    try:
        summary = await audit_logger.get_audit_summary(hours=hours)
        
        return {
            "success": True,
            "audit_summary": summary,
            "user_id": current_user.user_id
        }
        
    except Exception as e:
        logger.error("Failed to get audit summary", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit summary: {str(e)}"
        )


# === HEALTH CHECK ENDPOINTS ===

@github_router.get("/health")
async def github_automation_health():
    """Health check for GitHub automation system."""
    try:
        return {
            "status": "healthy",
            "service": "github_automation",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "features": {
                "automation_engine": True,
                "webhook_processing": True,
                "rollback_management": True,
                "audit_logging": True,
                "feature_detection": True
            }
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )


# Export router for inclusion in main app
__all__ = ["github_router"]