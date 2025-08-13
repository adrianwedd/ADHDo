#!/usr/bin/env python3
"""
Task Manager - Manages task focus and tracking
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages task focus and completion tracking."""
    
    def __init__(self):
        self.redis_client = None
        self._init_redis()
        
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
    
    async def set_focus(self, user_id: str, task_name: str, duration_minutes: Optional[int] = None) -> Dict[str, Any]:
        """Set current task focus."""
        logger.info(f"Setting focus to: {task_name}")
        
        if self.redis_client:
            # Store current focus
            await self.redis_client.set(f"current_focus:{user_id}", task_name)
            
            # Store start time
            await self.redis_client.set(
                f"task_start:{user_id}:{task_name}", 
                datetime.now().isoformat()
            )
            
            # Store expected duration if provided
            if duration_minutes:
                await self.redis_client.set(
                    f"task_duration:{user_id}:{task_name}",
                    duration_minutes
                )
        
        return {
            "status": "focused",
            "task": task_name,
            "duration": duration_minutes
        }
    
    async def add_task(self, user_id: str, title: str, priority: str = "medium", due_time: Optional[str] = None) -> Dict[str, Any]:
        """Add a new task."""
        logger.info(f"Adding task: {title} (priority: {priority})")
        
        task = {
            "title": title,
            "priority": priority,
            "due_time": due_time,
            "created": datetime.now().isoformat(),
            "status": "pending"
        }
        
        if self.redis_client:
            # Add to user's task list
            import json
            await self.redis_client.lpush(f"tasks:{user_id}", json.dumps(task))
            
            # Keep only last 100 tasks
            await self.redis_client.ltrim(f"tasks:{user_id}", 0, 99)
        
        return {
            "status": "added",
            "task": task
        }
    
    async def complete_task(self, user_id: str, task_name: str) -> Dict[str, Any]:
        """Mark a task as completed."""
        logger.info(f"Completing task: {task_name}")
        
        if self.redis_client:
            # Clear current focus if it matches
            current_focus = await self.redis_client.get(f"current_focus:{user_id}")
            if current_focus == task_name:
                await self.redis_client.delete(f"current_focus:{user_id}")
            
            # Log completion
            completion = {
                "task": task_name,
                "completed_at": datetime.now().isoformat()
            }
            
            import json
            await self.redis_client.lpush(
                f"completed_tasks:{user_id}", 
                json.dumps(completion)
            )
            
            # Keep only last 50 completions
            await self.redis_client.ltrim(f"completed_tasks:{user_id}", 0, 49)
        
        return {
            "status": "completed",
            "task": task_name
        }
    
    async def get_current_focus(self, user_id: str) -> Optional[str]:
        """Get current task focus."""
        if self.redis_client:
            return await self.redis_client.get(f"current_focus:{user_id}")
        return None
    
    async def get_tasks(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's tasks."""
        if not self.redis_client:
            return []
        
        try:
            import json
            tasks = await self.redis_client.lrange(f"tasks:{user_id}", 0, limit - 1)
            return [json.loads(t) for t in tasks] if tasks else []
        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return []