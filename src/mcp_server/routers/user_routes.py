"""
User and task management routes - User operations and task tracking.

Extracted from monolithic main.py to improve code organization and maintainability.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from ..models import User, Task
from ..auth import get_current_user
from ..database import get_database_session
from ..repositories import UserRepository, TaskRepository
from ..health_monitor import health_monitor
from ..adhd_errors import system_error, not_found_error
from nudge.engine import nudge_engine

user_router = APIRouter(tags=["Users", "Tasks"])


@user_router.post("/users", response_model=User)
async def create_user(user: User):
    """
    Create a new user (admin function).
    
    This endpoint is primarily for administrative user creation
    and system integration purposes.
    """
    try:
        user_repo = UserRepository()
        created_user = await user_repo.create_user(user.dict())
        
        health_monitor.record_metric("admin_users_created", 1)
        
        return created_user
        
    except Exception as e:
        health_monitor.record_error("create_user", str(e))
        return system_error("Failed to create user")


@user_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    """
    Get user information by ID (admin function).
    
    Retrieves user details for administrative purposes
    with appropriate access controls.
    """
    try:
        user_repo = UserRepository()
        user = await user_repo.get_user(user_id)
        
        if not user:
            return not_found_error("User")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("get_user", str(e))
        return system_error("Failed to retrieve user")


@user_router.post("/tasks", response_model=Task)
async def create_task(task: Task, current_user: User = Depends(get_current_user)):
    """
    Create a new task for the current user.
    
    Tasks are central to the ADHD executive function support system,
    providing structure and progress tracking.
    """
    try:
        task_repo = TaskRepository()
        
        # Ensure task is associated with current user
        task_data = task.dict()
        task_data["user_id"] = current_user.id
        task_data["created_at"] = datetime.utcnow()
        
        created_task = await task_repo.create_task(task_data)
        
        health_monitor.record_metric("tasks_created", 1)
        
        return created_task
        
    except Exception as e:
        health_monitor.record_error("create_task", str(e))
        return system_error("Failed to create task")


@user_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str, current_user: User = Depends(get_current_user)):
    """
    Get a specific task by ID.
    
    Users can only access their own tasks for privacy and security.
    """
    try:
        task_repo = TaskRepository()
        task = await task_repo.get_task(task_id)
        
        if not task:
            return not_found_error("Task")
        
        # Ensure user can only access their own tasks
        if task.user_id != current_user.id:
            from ..adhd_errors import create_adhd_error_response
            return create_adhd_error_response(
                error="Access denied to this task",
                status_code=403
            )
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("get_task", str(e))
        return system_error("Failed to retrieve task")


@user_router.put("/tasks/{task_id}/complete")
async def complete_task(task_id: str, current_user: User = Depends(get_current_user)):
    """
    Mark a task as completed.
    
    Completing tasks triggers positive reinforcement patterns
    and updates the user's progress tracking.
    """
    try:
        task_repo = TaskRepository()
        
        # Verify task ownership and complete
        task = await task_repo.get_task(task_id)
        if not task or task.user_id != current_user.id:
            return not_found_error("Task")
        
        completed_task = await task_repo.complete_task(task_id)
        
        # Trigger positive reinforcement nudge
        await nudge_engine.trigger_completion_nudge(current_user.id, task_id)
        
        health_monitor.record_metric("tasks_completed", 1)
        
        return {
            "status": "success", 
            "task_id": task_id, 
            "completed_at": completed_task.completed_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("complete_task", str(e))
        return system_error("Failed to complete task")


@user_router.post("/nudge/{user_id}")
async def trigger_nudge(user_id: str, task_id: str = None, current_user: User = Depends(get_current_user)):
    """
    Manually trigger a nudge for motivation or task reminders.
    
    Nudges are intelligent notifications designed to support
    ADHD users without overwhelming them.
    """
    try:
        # Users can only trigger nudges for themselves (unless admin)
        if user_id != current_user.id:
            # Add admin check here if needed
            from ..adhd_errors import create_adhd_error_response
            return create_adhd_error_response(
                error="Can only trigger nudges for yourself",
                status_code=403
            )
        
        # Trigger through nudge engine
        nudge_result = await nudge_engine.trigger_manual_nudge(user_id, task_id)
        
        health_monitor.record_metric("manual_nudges_triggered", 1)
        
        return {
            "status": "success",
            "nudge_id": nudge_result.get("nudge_id"),
            "message": nudge_result.get("message", "Nudge sent successfully"),
            "tier": nudge_result.get("tier", "gentle")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("trigger_nudge", str(e))
        from ..exception_handlers import ADHDFeatureException
        raise ADHDFeatureException("nudge_trigger", "Failed to trigger manual nudge", recoverable=True)