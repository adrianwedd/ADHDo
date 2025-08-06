"""
Unit tests for database repositories.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from tests.utils import TestDataFactory, DatabaseAssertions


@pytest.mark.unit
@pytest.mark.database
class TestUserRepository:
    """Test UserRepository functionality."""
    
    async def test_create_user(self, db_service):
        """Test user creation through repository."""
        user_data = TestDataFactory.create_user_data(
            name="Repository Test User",
            email="repo@example.com"
        )
        
        user = await db_service.create_user(**user_data)
        
        assert user.name == "Repository Test User"
        assert user.email == "repo@example.com"
        assert user.user_id is not None
        assert user.created_at is not None
        
        # Verify user exists in database
        retrieved_user = await db_service.users.get_by_id(user.user_id)
        assert retrieved_user is not None
        assert retrieved_user.name == user.name
    
    async def test_get_user_by_email(self, db_service):
        """Test getting user by email."""
        user_data = TestDataFactory.create_user_data(
            email="unique@example.com"
        )
        created_user = await db_service.create_user(**user_data)
        
        # Get by email
        retrieved_user = await db_service.users.get_by_email("unique@example.com")
        assert retrieved_user is not None
        assert retrieved_user.user_id == created_user.user_id
        assert retrieved_user.email == "unique@example.com"
    
    async def test_get_user_by_telegram_id(self, db_service):
        """Test getting user by Telegram chat ID."""
        user_data = TestDataFactory.create_user_data(
            telegram_chat_id="987654321"
        )
        created_user = await db_service.create_user(**user_data)
        
        # Get by Telegram ID
        retrieved_user = await db_service.users.get_by_telegram_id("987654321")
        assert retrieved_user is not None
        assert retrieved_user.user_id == created_user.user_id
        assert retrieved_user.telegram_chat_id == "987654321"
    
    async def test_update_user_preferences(self, db_service, test_user):
        """Test updating user preferences."""
        new_preferences = {
            "nudge_style": "structured",
            "focus_duration": 45,
            "break_duration": 10,
            "theme": "dark"
        }
        
        updated_user = await db_service.users.update_preferences(
            test_user.user_id, new_preferences
        )
        
        assert updated_user.preferences == new_preferences
        assert updated_user.preferences["nudge_style"] == "structured"
        assert updated_user.preferences["focus_duration"] == 45
    
    async def test_deactivate_user(self, db_service, test_user):
        """Test user deactivation."""
        # Deactivate user
        deactivated_user = await db_service.users.deactivate(test_user.user_id)
        assert deactivated_user.is_active is False
        
        # Verify user is deactivated in database
        retrieved_user = await db_service.users.get_by_id(test_user.user_id)
        assert retrieved_user.is_active is False
    
    async def test_get_active_users(self, db_service):
        """Test getting active users only."""
        # Create active user
        active_user_data = TestDataFactory.create_user_data(
            email="active@example.com"
        )
        active_user = await db_service.create_user(**active_user_data)
        
        # Create and deactivate user
        inactive_user_data = TestDataFactory.create_user_data(
            email="inactive@example.com"
        )
        inactive_user = await db_service.create_user(**inactive_user_data)
        await db_service.users.deactivate(inactive_user.user_id)
        
        # Get active users
        active_users = await db_service.users.get_active_users()
        active_user_ids = [u.user_id for u in active_users]
        
        assert active_user.user_id in active_user_ids
        assert inactive_user.user_id not in active_user_ids


@pytest.mark.unit
@pytest.mark.database
class TestTaskRepository:
    """Test TaskRepository functionality."""
    
    async def test_create_task(self, db_service, test_user):
        """Test task creation through repository."""
        task_data = TestDataFactory.create_task_data(
            user_id=test_user.user_id,
            title="Repository Test Task",
            priority=5
        )
        
        task = await db_service.create_task(**task_data)
        
        assert task.title == "Repository Test Task"
        assert task.user_id == test_user.user_id
        assert task.priority == 5
        assert task.task_id is not None
        assert task.status == "pending"
        assert task.completion_percentage == 0.0
    
    async def test_get_user_tasks(self, db_service, test_user):
        """Test getting tasks for a user."""
        # Create multiple tasks
        for i in range(3):
            task_data = TestDataFactory.create_task_data(
                user_id=test_user.user_id,
                title=f"Task {i+1}",
                priority=i+1
            )
            await db_service.create_task(**task_data)
        
        # Get user tasks
        user_tasks = await db_service.get_user_active_tasks(test_user.user_id)
        assert len(user_tasks) == 3
        
        # Check sorting (should be by priority descending)
        priorities = [task.priority for task in user_tasks]
        assert priorities == sorted(priorities, reverse=True)
    
    async def test_update_task_status(self, db_service, test_task):
        """Test updating task status."""
        # Update to in_progress
        updated_task = await db_service.tasks.update_status(
            test_task.task_id, "in_progress"
        )
        assert updated_task.status == "in_progress"
        
        # Update to completed
        completed_task = await db_service.tasks.update_status(
            test_task.task_id, "completed", completion_percentage=1.0
        )
        assert completed_task.status == "completed"
        assert completed_task.completion_percentage == 1.0
        assert completed_task.completed_at is not None
    
    async def test_task_completion_with_reward(self, db_service, test_task):
        """Test task completion with reward calculation."""
        completed_task, reward = await db_service.complete_task_with_reward(
            test_task.task_id
        )
        
        assert completed_task.status == "completed"
        assert completed_task.completion_percentage == 1.0
        assert completed_task.completed_at is not None
        
        assert reward is not None
        assert "points" in reward
        assert "message" in reward
        assert reward["points"] > 0
    
    async def test_suggest_next_task(self, db_service, test_user):
        """Test task suggestion algorithm."""
        # Create tasks with different priorities and energy requirements
        high_priority_task = await db_service.create_task(
            user_id=test_user.user_id,
            title="High Priority Task",
            priority=5,
            energy_required="low",
            estimated_focus_time=15
        )
        
        medium_task = await db_service.create_task(
            user_id=test_user.user_id,
            title="Medium Task",
            priority=3,
            energy_required="medium",
            estimated_focus_time=30
        )
        
        low_priority_task = await db_service.create_task(
            user_id=test_user.user_id,
            title="Low Priority Task",
            priority=1,
            energy_required="high",
            estimated_focus_time=60
        )
        
        # Test suggestion for low energy
        suggested_low = await db_service.suggest_next_task(
            test_user.user_id, "low"
        )
        assert suggested_low is not None
        assert suggested_low.task_id == high_priority_task.task_id  # High priority, low energy
        
        # Test suggestion for high energy
        suggested_high = await db_service.suggest_next_task(
            test_user.user_id, "high"
        )
        assert suggested_high is not None
        # Should suggest highest priority among high energy tasks
    
    async def test_get_overdue_tasks(self, db_service, test_user):
        """Test getting overdue tasks."""
        # Create task with past due date
        past_due_date = datetime.utcnow() - timedelta(days=1)
        overdue_task = await db_service.create_task(
            user_id=test_user.user_id,
            title="Overdue Task",
            priority=4,
            due_date=past_due_date
        )
        
        # Create task with future due date
        future_due_date = datetime.utcnow() + timedelta(days=1)
        future_task = await db_service.create_task(
            user_id=test_user.user_id,
            title="Future Task",
            priority=4,
            due_date=future_due_date
        )
        
        # Get overdue tasks
        overdue_tasks = await db_service.tasks.get_overdue_tasks(test_user.user_id)
        overdue_task_ids = [task.task_id for task in overdue_tasks]
        
        assert overdue_task.task_id in overdue_task_ids
        assert future_task.task_id not in overdue_task_ids


@pytest.mark.unit
@pytest.mark.database
class TestTraceMemoryRepository:
    """Test TraceMemoryRepository functionality."""
    
    async def test_record_trace(self, db_service, test_user):
        """Test recording trace memory."""
        trace_data = TestDataFactory.create_trace_data(
            user_id=test_user.user_id,
            trace_type="system_response",
            content={"response": "Test AI response", "confidence": 0.95}
        )
        
        trace = await db_service.record_trace(**trace_data)
        
        assert trace.user_id == test_user.user_id
        assert trace.trace_type == "system_response"
        assert trace.content["response"] == "Test AI response"
        assert trace.content["confidence"] == 0.95
        assert trace.trace_id is not None
    
    async def test_get_user_traces(self, db_service, test_user):
        """Test getting user traces."""
        # Create multiple traces
        trace_types = ["user_input", "system_response", "task_progress"]
        for i, trace_type in enumerate(trace_types):
            trace_data = TestDataFactory.create_trace_data(
                user_id=test_user.user_id,
                trace_type=trace_type,
                content={"index": i, "type": trace_type}
            )
            await db_service.record_trace(**trace_data)
        
        # Get user traces
        user_traces = await db_service.get_user_traces(test_user.user_id, limit=10)
        assert len(user_traces) == 3
        
        # Check ordering (should be most recent first)
        assert user_traces[0].created_at >= user_traces[1].created_at
        assert user_traces[1].created_at >= user_traces[2].created_at
    
    async def test_get_user_context(self, db_service, test_user, test_task):
        """Test getting user context from traces."""
        # Create various traces to build context
        traces_data = [
            {
                "trace_type": "user_input",
                "content": {"message": "I'm feeling overwhelmed", "intent": "support"},
                "cognitive_load": 0.8
            },
            {
                "trace_type": "system_response",
                "content": {"response": "Let's break this down", "strategy": "decomposition"},
                "cognitive_load": 0.6
            },
            {
                "trace_type": "task_progress",
                "content": {"progress": "25%", "task_id": test_task.task_id},
                "cognitive_load": 0.4,
                "task_id": test_task.task_id
            }
        ]
        
        for trace_data in traces_data:
            full_trace_data = TestDataFactory.create_trace_data(
                user_id=test_user.user_id,
                **trace_data
            )
            await db_service.record_trace(**full_trace_data)
        
        # Get user context
        context = await db_service.get_user_context(test_user.user_id)
        
        assert "recent_interactions" in context
        assert "active_task_count" in context
        assert "avg_cognitive_load" in context
        assert "pattern_indicators" in context
        
        assert context["recent_interactions"] == 3
        assert context["active_task_count"] >= 1  # At least the test_task
        assert 0.0 <= context["avg_cognitive_load"] <= 1.0
    
    async def test_get_traces_by_type(self, db_service, test_user):
        """Test filtering traces by type."""
        # Create traces of different types
        for i in range(2):
            await db_service.record_trace(
                user_id=test_user.user_id,
                trace_type="user_input",
                content={"message": f"Input {i}"},
                was_successful=True
            )
        
        for i in range(3):
            await db_service.record_trace(
                user_id=test_user.user_id,
                trace_type="system_response",
                content={"response": f"Response {i}"},
                was_successful=True
            )
        
        # Get traces by type
        user_input_traces = await db_service.trace_memory.get_by_type(
            test_user.user_id, "user_input"
        )
        system_response_traces = await db_service.trace_memory.get_by_type(
            test_user.user_id, "system_response"
        )
        
        assert len(user_input_traces) == 2
        assert len(system_response_traces) == 3
        
        # Verify trace types
        for trace in user_input_traces:
            assert trace.trace_type == "user_input"
        for trace in system_response_traces:
            assert trace.trace_type == "system_response"


@pytest.mark.unit
@pytest.mark.database
class TestSessionRepository:
    """Test SessionRepository functionality."""
    
    async def test_create_session(self, db_service, test_user):
        """Test session creation."""
        session_id = await db_service.create_session(
            user_id=test_user.user_id,
            duration_hours=24,
            user_agent="TestAgent/1.0",
            ip_address="127.0.0.1"
        )
        
        assert session_id is not None
        assert len(session_id) > 20  # Should be a reasonable length
        
        # Validate session
        session_user = await db_service.validate_session(session_id)
        assert session_user is not None
        assert session_user.user_id == test_user.user_id
    
    async def test_session_expiration(self, db_service, test_user):
        """Test session expiration handling."""
        # Create short-lived session (1 second)
        short_session_id = await db_service.create_session(
            user_id=test_user.user_id,
            duration_hours=0.0003,  # ~1 second
            user_agent="TestAgent/1.0"
        )
        
        # Should be valid immediately
        user = await db_service.validate_session(short_session_id)
        assert user is not None
        
        # Wait and test expiration (in real implementation)
        # Note: This would require actual time passing or mocking
    
    async def test_invalidate_session(self, db_service, test_user_session):
        """Test session invalidation."""
        # Session should be valid initially
        user = await db_service.validate_session(test_user_session)
        assert user is not None
        
        # Invalidate session
        await db_service.sessions.invalidate(test_user_session)
        
        # Session should no longer be valid
        invalid_user = await db_service.validate_session(test_user_session)
        assert invalid_user is None
    
    async def test_get_user_sessions(self, db_service, test_user):
        """Test getting user sessions."""
        # Create multiple sessions
        session_ids = []
        for i in range(3):
            session_id = await db_service.create_session(
                user_id=test_user.user_id,
                duration_hours=24,
                user_agent=f"TestAgent{i}/1.0"
            )
            session_ids.append(session_id)
        
        # Get user sessions
        user_sessions = await db_service.sessions.get_user_sessions(test_user.user_id)
        
        assert len(user_sessions) == 3
        retrieved_session_ids = [s.session_id for s in user_sessions]
        
        for session_id in session_ids:
            assert session_id in retrieved_session_ids


@pytest.mark.unit
@pytest.mark.database
class TestAPIKeyRepository:
    """Test APIKeyRepository functionality."""
    
    async def test_create_api_key(self, db_service, test_user):
        """Test API key creation."""
        permissions = ["chat", "tasks", "health"]
        key_id, api_key = await db_service.create_api_key(
            user_id=test_user.user_id,
            name="Test API Key",
            permissions=permissions
        )
        
        assert key_id is not None
        assert api_key is not None
        assert len(api_key) > 30  # Should be reasonably long
        
        # Validate API key
        api_user = await db_service.validate_api_key(api_key)
        assert api_user is not None
        assert api_user.user_id == test_user.user_id
    
    async def test_api_key_permissions(self, db_service, test_api_key):
        """Test API key permissions validation."""
        key_id, api_key = test_api_key
        
        # Get API key record
        api_key_record = await db_service.api_keys.get_by_key_id(key_id)
        assert api_key_record is not None
        assert "chat" in api_key_record.permissions
        assert "tasks" in api_key_record.permissions
        assert "health" in api_key_record.permissions
        assert "metrics" in api_key_record.permissions
    
    async def test_revoke_api_key(self, db_service, test_api_key):
        """Test API key revocation."""
        key_id, api_key = test_api_key
        
        # Key should be valid initially
        user = await db_service.validate_api_key(api_key)
        assert user is not None
        
        # Revoke key
        await db_service.api_keys.revoke(key_id)
        
        # Key should no longer be valid
        invalid_user = await db_service.validate_api_key(api_key)
        assert invalid_user is None
    
    async def test_get_user_api_keys(self, db_service, test_user):
        """Test getting user API keys."""
        # Create multiple API keys
        key_names = ["Key 1", "Key 2", "Admin Key"]
        created_keys = []
        
        for name in key_names:
            key_id, api_key = await db_service.create_api_key(
                user_id=test_user.user_id,
                name=name,
                permissions=["chat"]
            )
            created_keys.append(key_id)
        
        # Get user API keys
        user_keys = await db_service.api_keys.get_user_keys(test_user.user_id)
        
        assert len(user_keys) == 3
        retrieved_key_ids = [k.key_id for k in user_keys]
        
        for key_id in created_keys:
            assert key_id in retrieved_key_ids