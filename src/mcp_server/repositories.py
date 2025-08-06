"""Repository layer for database operations."""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update, delete, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mcp_server.db_models import (
    User as DBUser, Task as DBTask, TraceMemory as DBTraceMemory, 
    Session as DBSession, APIKey as DBAPIKey, SystemHealth as DBSystemHealth
)
from mcp_server.models import User, Task, TraceMemory


class UserRepository:
    """Repository for user operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user_data: Dict[str, Any]) -> DBUser:
        """Create a new user."""
        user = DBUser(
            user_id=user_data.get('user_id', str(uuid4())),
            **user_data
        )
        self.session.add(user)
        await self.session.flush()
        return user
    
    async def get_by_id(self, user_id: str) -> Optional[DBUser]:
        """Get user by ID."""
        result = await self.session.execute(
            select(DBUser).where(DBUser.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[DBUser]:
        """Get user by email."""
        result = await self.session.execute(
            select(DBUser).where(DBUser.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_telegram_id(self, chat_id: str) -> Optional[DBUser]:
        """Get user by Telegram chat ID."""
        result = await self.session.execute(
            select(DBUser).where(DBUser.telegram_chat_id == chat_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, user_id: str, user_data: Dict[str, Any]) -> Optional[DBUser]:
        """Update user data."""
        user_data['updated_at'] = datetime.utcnow()
        await self.session.execute(
            update(DBUser)
            .where(DBUser.user_id == user_id)
            .values(**user_data)
        )
        return await self.get_by_id(user_id)
    
    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        await self.session.execute(
            update(DBUser)
            .where(DBUser.user_id == user_id)
            .values(last_login=datetime.utcnow())
        )
    
    async def delete(self, user_id: str) -> bool:
        """Delete user (soft delete by setting is_active=False)."""
        result = await self.session.execute(
            update(DBUser)
            .where(DBUser.user_id == user_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        return result.rowcount > 0


class TaskRepository:
    """Repository for task operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, task_data: Dict[str, Any]) -> DBTask:
        """Create a new task."""
        task = DBTask(
            task_id=task_data.get('task_id', str(uuid4())),
            **task_data
        )
        self.session.add(task)
        await self.session.flush()
        return task
    
    async def get_by_id(self, task_id: str) -> Optional[DBTask]:
        """Get task by ID."""
        result = await self.session.execute(
            select(DBTask)
            .options(selectinload(DBTask.user))
            .where(DBTask.task_id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_tasks(
        self, 
        user_id: str, 
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DBTask]:
        """Get user's tasks with optional filtering."""
        query = select(DBTask).where(DBTask.user_id == user_id)
        
        if status:
            query = query.where(DBTask.status == status)
        
        query = query.order_by(desc(DBTask.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_pending_tasks(self, user_id: str) -> List[DBTask]:
        """Get all pending tasks for user."""
        result = await self.session.execute(
            select(DBTask)
            .where(and_(
                DBTask.user_id == user_id,
                DBTask.status.in_(['pending', 'in_progress'])
            ))
            .order_by(DBTask.priority.desc(), DBTask.created_at)
        )
        return list(result.scalars().all())
    
    async def get_overdue_tasks(self, user_id: str) -> List[DBTask]:
        """Get overdue tasks for user."""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(DBTask)
            .where(and_(
                DBTask.user_id == user_id,
                DBTask.status.in_(['pending', 'in_progress']),
                DBTask.due_date < now
            ))
            .order_by(DBTask.due_date)
        )
        return list(result.scalars().all())
    
    async def update(self, task_id: str, task_data: Dict[str, Any]) -> Optional[DBTask]:
        """Update task data."""
        task_data['updated_at'] = datetime.utcnow()
        await self.session.execute(
            update(DBTask)
            .where(DBTask.task_id == task_id)
            .values(**task_data)
        )
        return await self.get_by_id(task_id)
    
    async def complete_task(self, task_id: str) -> Optional[DBTask]:
        """Mark task as completed."""
        now = datetime.utcnow()
        await self.session.execute(
            update(DBTask)
            .where(DBTask.task_id == task_id)
            .values(
                status='completed',
                completion_percentage=1.0,
                completed_at=now,
                updated_at=now
            )
        )
        return await self.get_by_id(task_id)
    
    async def increment_nudge_count(self, task_id: str) -> None:
        """Increment nudge count for task."""
        now = datetime.utcnow()
        await self.session.execute(
            update(DBTask)
            .where(DBTask.task_id == task_id)
            .values(
                nudge_count=DBTask.nudge_count + 1,
                last_nudge_at=now,
                updated_at=now
            )
        )
    
    async def delete(self, task_id: str) -> bool:
        """Delete task."""
        result = await self.session.execute(
            delete(DBTask).where(DBTask.task_id == task_id)
        )
        return result.rowcount > 0


class TraceMemoryRepository:
    """Repository for trace memory operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, trace_data: Dict[str, Any]) -> DBTraceMemory:
        """Create a new trace memory."""
        trace = DBTraceMemory(
            trace_id=trace_data.get('trace_id', str(uuid4())),
            **trace_data
        )
        self.session.add(trace)
        await self.session.flush()
        return trace
    
    async def get_by_id(self, trace_id: str) -> Optional[DBTraceMemory]:
        """Get trace by ID."""
        result = await self.session.execute(
            select(DBTraceMemory).where(DBTraceMemory.trace_id == trace_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_traces(
        self, 
        user_id: str,
        trace_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DBTraceMemory]:
        """Get user's trace memories."""
        query = select(DBTraceMemory).where(DBTraceMemory.user_id == user_id)
        
        if trace_type:
            query = query.where(DBTraceMemory.trace_type == trace_type)
        
        query = query.order_by(desc(DBTraceMemory.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_session_traces(self, session_id: str) -> List[DBTraceMemory]:
        """Get all traces for a session."""
        result = await self.session.execute(
            select(DBTraceMemory)
            .where(DBTraceMemory.session_id == session_id)
            .order_by(DBTraceMemory.created_at)
        )
        return list(result.scalars().all())
    
    async def get_task_traces(self, task_id: str) -> List[DBTraceMemory]:
        """Get all traces for a task."""
        result = await self.session.execute(
            select(DBTraceMemory)
            .where(DBTraceMemory.task_id == task_id)
            .order_by(DBTraceMemory.created_at)
        )
        return list(result.scalars().all())
    
    async def cleanup_old_traces(self, days: int = 90) -> int:
        """Clean up old trace memories."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            delete(DBTraceMemory).where(DBTraceMemory.created_at < cutoff_date)
        )
        return result.rowcount


class SessionRepository:
    """Repository for session operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, session_data: Dict[str, Any]) -> DBSession:
        """Create a new session."""
        session_obj = DBSession(**session_data)
        self.session.add(session_obj)
        await self.session.flush()
        return session_obj
    
    async def get_by_id(self, session_id: str) -> Optional[DBSession]:
        """Get session by ID."""
        result = await self.session.execute(
            select(DBSession)
            .options(selectinload(DBSession.user))
            .where(DBSession.session_id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_session(self, session_id: str) -> Optional[DBSession]:
        """Get active session by ID."""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(DBSession)
            .options(selectinload(DBSession.user))
            .where(and_(
                DBSession.session_id == session_id,
                DBSession.is_active == True,
                DBSession.expires_at > now
            ))
        )
        return result.scalar_one_or_none()
    
    async def update_last_accessed(self, session_id: str) -> None:
        """Update session's last accessed timestamp."""
        await self.session.execute(
            update(DBSession)
            .where(DBSession.session_id == session_id)
            .values(last_accessed=datetime.utcnow())
        )
    
    async def deactivate(self, session_id: str) -> bool:
        """Deactivate session."""
        result = await self.session.execute(
            update(DBSession)
            .where(DBSession.session_id == session_id)
            .values(is_active=False)
        )
        return result.rowcount > 0
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        now = datetime.utcnow()
        result = await self.session.execute(
            delete(DBSession).where(DBSession.expires_at < now)
        )
        return result.rowcount


class APIKeyRepository:
    """Repository for API key operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, api_key_data: Dict[str, Any]) -> DBAPIKey:
        """Create a new API key."""
        api_key = DBAPIKey(**api_key_data)
        self.session.add(api_key)
        await self.session.flush()
        return api_key
    
    async def get_by_hash(self, key_hash: str) -> Optional[DBAPIKey]:
        """Get API key by hash."""
        result = await self.session.execute(
            select(DBAPIKey)
            .options(selectinload(DBAPIKey.user))
            .where(and_(
                DBAPIKey.key_hash == key_hash,
                DBAPIKey.is_active == True
            ))
        )
        api_key = result.scalar_one_or_none()
        
        if api_key:
            # Update last used timestamp
            await self.session.execute(
                update(DBAPIKey)
                .where(DBAPIKey.key_id == api_key.key_id)
                .values(
                    last_used_at=datetime.utcnow(),
                    total_requests=DBAPIKey.total_requests + 1
                )
            )
        
        return api_key
    
    async def get_user_keys(self, user_id: str) -> List[DBAPIKey]:
        """Get all API keys for user."""
        result = await self.session.execute(
            select(DBAPIKey)
            .where(and_(
                DBAPIKey.user_id == user_id,
                DBAPIKey.is_active == True
            ))
            .order_by(desc(DBAPIKey.created_at))
        )
        return list(result.scalars().all())
    
    async def revoke(self, key_id: str) -> bool:
        """Revoke API key."""
        result = await self.session.execute(
            update(DBAPIKey)
            .where(DBAPIKey.key_id == key_id)
            .values(is_active=False)
        )
        return result.rowcount > 0


class SystemHealthRepository:
    """Repository for system health operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def record_health(self, health_data: Dict[str, Any]) -> DBSystemHealth:
        """Record system health metrics."""
        health = DBSystemHealth(**health_data)
        self.session.add(health)
        await self.session.flush()
        return health
    
    async def get_latest_health(self, component: str) -> Optional[DBSystemHealth]:
        """Get latest health record for component."""
        result = await self.session.execute(
            select(DBSystemHealth)
            .where(DBSystemHealth.component == component)
            .order_by(desc(DBSystemHealth.measured_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_health_history(
        self, 
        component: str, 
        hours: int = 24
    ) -> List[DBSystemHealth]:
        """Get health history for component."""
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await self.session.execute(
            select(DBSystemHealth)
            .where(and_(
                DBSystemHealth.component == component,
                DBSystemHealth.measured_at > since
            ))
            .order_by(DBSystemHealth.measured_at)
        )
        return list(result.scalars().all())
    
    async def cleanup_old_health_records(self, days: int = 30) -> int:
        """Clean up old health records."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            delete(DBSystemHealth).where(DBSystemHealth.measured_at < cutoff_date)
        )
        return result.rowcount