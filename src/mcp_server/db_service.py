"""Database service layer for business logic operations."""
import hashlib
import secrets
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server.db_models import User as DBUser, Task as DBTask, TraceMemory as DBTraceMemory
from mcp_server.repositories import (
    UserRepository, TaskRepository, TraceMemoryRepository,
    SessionRepository, APIKeyRepository, SystemHealthRepository
)
from mcp_server.models import User, Task, NudgeTier


class DatabaseService:
    """Service layer for database operations with business logic."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.tasks = TaskRepository(session)
        self.traces = TraceMemoryRepository(session)
        self.sessions = SessionRepository(session)
        self.api_keys = APIKeyRepository(session)
        self.health = SystemHealthRepository(session)
    
    # === USER OPERATIONS ===
    
    async def create_user(
        self, 
        name: str, 
        email: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        **kwargs
    ) -> DBUser:
        """Create a new user with default ADHD settings."""
        user_data = {
            'name': name,
            'email': email,
            'telegram_chat_id': telegram_chat_id,
            'preferred_nudge_methods': ['web', 'telegram'] if telegram_chat_id else ['web'],
            'nudge_timing_preferences': {
                'morning': '09:00',
                'afternoon': '14:00', 
                'evening': '18:00'
            },
            'energy_patterns': {
                'peak_hours': [9, 10, 11, 14, 15, 16],
                'low_hours': [12, 13, 17, 18, 19]
            },
            'hyperfocus_indicators': [
                'long_sessions', 
                'delayed_responses', 
                'task_completion_streaks'
            ],
            **kwargs
        }
        return await self.users.create(user_data)
    
    async def get_or_create_user(self, user_id: str, name: str, **kwargs) -> DBUser:
        """Get existing user or create new one."""
        user = await self.users.get_by_id(user_id)
        if not user:
            user = await self.create_user(name=name, **kwargs)
        return user
    
    async def authenticate_user(self, username: str, password: str) -> Optional[DBUser]:
        """Authenticate user with username/password."""
        user = await self.users.get_by_email(username)
        if not user or not user.password_hash:
            return None
        
        # Simple password check (in production, use proper hashing)
        if self._verify_password(password, user.password_hash):
            await self.users.update_last_login(user.user_id)
            return user
        
        return None
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt."""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{pwd_hash.hex()}"
    
    def _verify_password(self, password: str, hash_with_salt: str) -> bool:
        """Verify password against hash."""
        try:
            salt, stored_hash = hash_with_salt.split(':')
            pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return pwd_hash.hex() == stored_hash
        except ValueError:
            return False
    
    # === TASK OPERATIONS ===
    
    async def create_task(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        priority: int = 3,
        energy_required: str = "medium",
        estimated_focus_time: Optional[int] = None,
        **kwargs
    ) -> DBTask:
        """Create a new task with ADHD-optimized defaults."""
        task_data = {
            'user_id': user_id,
            'title': title,
            'description': description,
            'priority': priority,
            'energy_required': energy_required,
            'estimated_focus_time': estimated_focus_time,
            'dopamine_reward_tier': min(priority, 5),  # Higher priority = higher reward
            'hyperfocus_compatible': estimated_focus_time and estimated_focus_time > 60,
            'tags': kwargs.get('tags', []),
            'context_triggers': kwargs.get('context_triggers', ['time', 'energy', 'location']),
            'preferred_time_blocks': kwargs.get('preferred_time_blocks', ['morning', 'afternoon']),
            **kwargs
        }
        return await self.tasks.create(task_data)
    
    async def get_user_active_tasks(self, user_id: str) -> List[DBTask]:
        """Get user's active tasks prioritized for ADHD."""
        return await self.tasks.get_pending_tasks(user_id)
    
    async def suggest_next_task(self, user_id: str, current_energy: str = "medium") -> Optional[DBTask]:
        """Suggest next task based on ADHD patterns and current energy."""
        tasks = await self.get_user_active_tasks(user_id)
        
        if not tasks:
            return None
        
        # Filter by energy requirements
        suitable_tasks = [
            task for task in tasks 
            if self._energy_match(task.energy_required, current_energy)
        ]
        
        if not suitable_tasks:
            suitable_tasks = tasks  # Fallback to all tasks
        
        # Sort by priority and dopamine potential
        suitable_tasks.sort(
            key=lambda t: (t.priority, t.dopamine_reward_tier), 
            reverse=True
        )
        
        return suitable_tasks[0]
    
    def _energy_match(self, required: str, available: str) -> bool:
        """Check if available energy matches task requirements."""
        energy_levels = {'low': 1, 'medium': 2, 'high': 3}
        return energy_levels.get(available, 2) >= energy_levels.get(required, 2)
    
    async def complete_task_with_reward(self, task_id: str) -> Tuple[DBTask, Dict[str, Any]]:
        """Complete task and calculate dopamine reward."""
        task = await self.tasks.complete_task(task_id)
        
        if not task:
            return None, {}
        
        # Calculate reward based on task completion
        reward = {
            'points': task.dopamine_reward_tier * 10,
            'streak_bonus': 0,  # TODO: Calculate completion streaks
            'message': self._get_completion_message(task.dopamine_reward_tier),
            'celebration_level': task.dopamine_reward_tier
        }
        
        # Record completion trace
        await self.record_trace(
            user_id=task.user_id,
            trace_type='completion',
            content={
                'task_id': task_id,
                'task_title': task.title,
                'completion_time': task.completed_at.isoformat(),
                'reward': reward
            },
            task_id=task_id,
            was_successful=True
        )
        
        return task, reward
    
    def _get_completion_message(self, tier: int) -> str:
        """Get celebration message based on reward tier."""
        messages = {
            1: "Nice work! 🎯",
            2: "Great job! 🌟", 
            3: "Excellent! 🚀",
            4: "Outstanding! 🏆",
            5: "LEGENDARY! 🎉🔥"
        }
        return messages.get(tier, "Task completed! ✅")
    
    # === TRACE MEMORY OPERATIONS ===
    
    async def record_trace(
        self,
        user_id: str,
        trace_type: str,
        content: Dict[str, Any],
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        processing_time_ms: Optional[float] = None,
        cognitive_load: Optional[float] = None,
        was_successful: Optional[bool] = None,
        source: str = "system",
        **kwargs
    ) -> DBTraceMemory:
        """Record a trace memory with context."""
        trace_data = {
            'user_id': user_id,
            'trace_type': trace_type,
            'content': content,
            'task_id': task_id,
            'session_id': session_id,
            'processing_time_ms': processing_time_ms,
            'cognitive_load': cognitive_load,
            'was_successful': was_successful,
            'source': source,
            **kwargs
        }
        return await self.traces.create(trace_data)
    
    async def get_user_context(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get user's recent context for cognitive loop."""
        recent_traces = await self.traces.get_user_traces(
            user_id=user_id,
            limit=50
        )
        
        active_tasks = await self.get_user_active_tasks(user_id)
        
        # Analyze patterns
        context = {
            'recent_interactions': len(recent_traces),
            'active_task_count': len(active_tasks),
            'high_priority_tasks': len([t for t in active_tasks if t.priority >= 4]),
            'overdue_tasks': len(await self.tasks.get_overdue_tasks(user_id)),
            'recent_completions': len([
                t for t in recent_traces 
                if t.trace_type == 'completion' and t.was_successful
            ]),
            'avg_response_time': self._calculate_avg_response_time(recent_traces),
            'cognitive_load_trend': self._calculate_cognitive_load_trend(recent_traces),
            'last_activity': recent_traces[0].created_at if recent_traces else None
        }
        
        return context
    
    def _calculate_avg_response_time(self, traces: List[DBTraceMemory]) -> float:
        """Calculate average response time from traces."""
        response_times = [
            t.processing_time_ms for t in traces 
            if t.processing_time_ms is not None
        ]
        return sum(response_times) / len(response_times) if response_times else 0.0
    
    def _calculate_cognitive_load_trend(self, traces: List[DBTraceMemory]) -> str:
        """Calculate cognitive load trend."""
        loads = [
            t.cognitive_load for t in traces[-10:] 
            if t.cognitive_load is not None
        ]
        
        if len(loads) < 2:
            return "stable"
        
        avg_recent = sum(loads[-5:]) / len(loads[-5:]) if len(loads) >= 5 else loads[-1]
        avg_older = sum(loads[:-5]) / len(loads[:-5]) if len(loads) >= 10 else loads[0]
        
        if avg_recent > avg_older + 0.1:
            return "increasing"
        elif avg_recent < avg_older - 0.1:
            return "decreasing"
        else:
            return "stable"
    
    # === SESSION MANAGEMENT ===
    
    async def create_session(
        self, 
        user_id: str, 
        duration_hours: int = 24,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """Create a new user session."""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'expires_at': expires_at,
            'user_agent': user_agent,
            'ip_address': ip_address
        }
        
        await self.sessions.create(session_data)
        return session_id
    
    async def validate_session(self, session_id: str) -> Optional[DBUser]:
        """Validate session and return user."""
        session = await self.sessions.get_active_session(session_id)
        if session:
            await self.sessions.update_last_accessed(session_id)
            return session.user
        return None
    
    # === API KEY MANAGEMENT ===
    
    async def create_api_key(
        self, 
        user_id: str, 
        name: str,
        permissions: Optional[List[str]] = None
    ) -> Tuple[str, str]:
        """Create API key and return key_id and full key."""
        key_id = f"mk_{secrets.token_urlsafe(8)}"
        api_key = f"{key_id}.{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        api_key_data = {
            'key_id': key_id,
            'user_id': user_id,
            'key_hash': key_hash,
            'name': name,
            'permissions': permissions or ['chat', 'tasks', 'context']
        }
        
        await self.api_keys.create(api_key_data)
        return key_id, api_key
    
    async def validate_api_key(self, api_key: str) -> Optional[DBUser]:
        """Validate API key and return user."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        api_key_obj = await self.api_keys.get_by_hash(key_hash)
        return api_key_obj.user if api_key_obj else None
    
    # === SYSTEM HEALTH ===
    
    async def record_system_health(
        self, 
        component: str, 
        status: str,
        response_time_ms: Optional[float] = None,
        error_rate: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record system health metrics."""
        health_data = {
            'component': component,
            'status': status,
            'response_time_ms': response_time_ms,
            'error_rate': error_rate,
            'details': details or {}
        }
        await self.health.record_health(health_data)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        components = ['redis', 'database', 'llm', 'telegram']
        status = {}
        
        for component in components:
            health = await self.health.get_latest_health(component)
            status[component] = {
                'status': health.status if health else 'unknown',
                'last_check': health.measured_at if health else None,
                'response_time_ms': health.response_time_ms if health else None
            }
        
        # Calculate overall status
        statuses = [v['status'] for v in status.values()]
        if 'unhealthy' in statuses:
            overall_status = 'unhealthy'
        elif 'degraded' in statuses:
            overall_status = 'degraded'
        elif 'unknown' in statuses:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        status['overall'] = {'status': overall_status}
        return status