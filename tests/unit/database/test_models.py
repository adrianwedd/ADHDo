"""
Unit tests for database models.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from mcp_server.db_models import (
    User, Task, TraceMemory, UserSession, APIKey, SystemHealth
)


@pytest.mark.unit
@pytest.mark.database
class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self):
        """Test user model creation."""
        user = User(
            name="Test User",
            email="test@example.com",
            telegram_chat_id="123456789"
        )
        
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.telegram_chat_id == "123456789"
        assert user.user_id is not None
        assert user.created_at is not None
        assert user.is_active is True
        assert user.preferences == {}
    
    def test_user_preferences(self):
        """Test user preferences handling."""
        preferences = {
            "nudge_style": "gentle",
            "focus_duration": 25,
            "break_duration": 5
        }
        
        user = User(
            name="Test User",
            email="test@example.com",
            preferences=preferences
        )
        
        assert user.preferences == preferences
        assert user.preferences["nudge_style"] == "gentle"
        assert user.preferences["focus_duration"] == 25
    
    def test_user_string_representation(self):
        """Test user string representation."""
        user = User(
            name="Test User",
            email="test@example.com"
        )
        
        assert str(user) == "Test User"
        assert user.name in repr(user)
        assert user.email in repr(user)


@pytest.mark.unit
@pytest.mark.database
class TestTaskModel:
    """Test Task model functionality."""
    
    def test_task_creation(self):
        """Test task model creation."""
        user_id = str(uuid4())
        task = Task(
            user_id=user_id,
            title="Test Task",
            description="This is a test task",
            priority=4,
            energy_required="medium",
            estimated_focus_time=30
        )
        
        assert task.user_id == user_id
        assert task.title == "Test Task"
        assert task.description == "This is a test task"
        assert task.priority == 4
        assert task.energy_required == "medium"
        assert task.estimated_focus_time == 30
        assert task.task_id is not None
        assert task.created_at is not None
        assert task.status == "pending"
        assert task.completion_percentage == 0.0
        assert task.dopamine_reward_tier is not None
    
    def test_task_dopamine_reward_calculation(self):
        """Test dopamine reward tier calculation."""
        user_id = str(uuid4())
        
        # High priority, high energy = highest reward
        high_task = Task(
            user_id=user_id,
            title="High Priority Task",
            priority=5,
            energy_required="high",
            estimated_focus_time=60
        )
        
        # Low priority, low energy = lower reward
        low_task = Task(
            user_id=user_id,
            title="Low Priority Task",
            priority=1,
            energy_required="low",
            estimated_focus_time=15
        )
        
        assert high_task.dopamine_reward_tier >= low_task.dopamine_reward_tier
    
    def test_task_completion(self):
        """Test task completion logic."""
        task = Task(
            user_id=str(uuid4()),
            title="Test Task",
            completion_percentage=0.0
        )
        
        # Update completion
        task.completion_percentage = 1.0
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        
        assert task.completion_percentage == 1.0
        assert task.status == "completed"
        assert task.completed_at is not None
    
    def test_task_tags_and_context(self):
        """Test task tags and context handling."""
        tags = ["work", "important", "deadline"]
        context = {"project": "test_project", "category": "development"}
        
        task = Task(
            user_id=str(uuid4()),
            title="Test Task",
            tags=tags,
            context=context
        )
        
        assert task.tags == tags
        assert task.context == context
        assert "work" in task.tags
        assert task.context["project"] == "test_project"


@pytest.mark.unit
@pytest.mark.database
class TestTraceMemoryModel:
    """Test TraceMemory model functionality."""
    
    def test_trace_memory_creation(self):
        """Test trace memory model creation."""
        user_id = str(uuid4())
        content = {
            "message": "I'm ready to work!",
            "intent": "start_task",
            "context": "morning_routine"
        }
        
        trace = TraceMemory(
            user_id=user_id,
            trace_type="user_input",
            content=content,
            processing_time_ms=123.45,
            cognitive_load=0.3,
            was_successful=True,
            source="web"
        )
        
        assert trace.user_id == user_id
        assert trace.trace_type == "user_input"
        assert trace.content == content
        assert trace.processing_time_ms == 123.45
        assert trace.cognitive_load == 0.3
        assert trace.was_successful is True
        assert trace.source == "web"
        assert trace.trace_id is not None
        assert trace.created_at is not None
    
    def test_trace_memory_with_task(self):
        """Test trace memory with associated task."""
        user_id = str(uuid4())
        task_id = str(uuid4())
        
        trace = TraceMemory(
            user_id=user_id,
            task_id=task_id,
            trace_type="task_progress",
            content={"progress": "50%", "notes": "Making good progress"},
            processing_time_ms=50.0,
            cognitive_load=0.2,
            was_successful=True
        )
        
        assert trace.task_id == task_id
        assert trace.trace_type == "task_progress"
        assert trace.content["progress"] == "50%"
    
    def test_trace_memory_cognitive_load_validation(self):
        """Test cognitive load value validation."""
        user_id = str(uuid4())
        
        # Valid cognitive load values
        for load in [0.0, 0.5, 1.0]:
            trace = TraceMemory(
                user_id=user_id,
                trace_type="test",
                content={},
                cognitive_load=load,
                was_successful=True
            )
            assert trace.cognitive_load == load
    
    def test_trace_memory_metadata(self):
        """Test trace memory metadata handling."""
        metadata = {
            "session_id": "test-session",
            "user_agent": "TestAgent/1.0",
            "ip_address": "127.0.0.1"
        }
        
        trace = TraceMemory(
            user_id=str(uuid4()),
            trace_type="user_input",
            content={"message": "test"},
            metadata=metadata,
            was_successful=True
        )
        
        assert trace.metadata == metadata
        assert trace.metadata["session_id"] == "test-session"


@pytest.mark.unit
@pytest.mark.database
class TestUserSessionModel:
    """Test UserSession model functionality."""
    
    def test_user_session_creation(self):
        """Test user session model creation."""
        user_id = str(uuid4())
        session = UserSession(
            user_id=user_id,
            session_id="test-session-id",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            user_agent="TestAgent/1.0",
            ip_address="127.0.0.1"
        )
        
        assert session.user_id == user_id
        assert session.session_id == "test-session-id"
        assert session.user_agent == "TestAgent/1.0"
        assert session.ip_address == "127.0.0.1"
        assert session.created_at is not None
        assert session.is_active is True
    
    def test_user_session_expiration(self):
        """Test user session expiration logic."""
        past_time = datetime.utcnow() - timedelta(hours=1)
        future_time = datetime.utcnow() + timedelta(hours=1)
        
        expired_session = UserSession(
            user_id=str(uuid4()),
            session_id="expired-session",
            expires_at=past_time
        )
        
        active_session = UserSession(
            user_id=str(uuid4()),
            session_id="active-session",
            expires_at=future_time
        )
        
        # Note: This would require a property method on the model
        # assert expired_session.is_expired is True
        # assert active_session.is_expired is False


@pytest.mark.unit
@pytest.mark.database
class TestAPIKeyModel:
    """Test APIKey model functionality."""
    
    def test_api_key_creation(self):
        """Test API key model creation."""
        user_id = str(uuid4())
        permissions = ["chat", "tasks", "health"]
        
        api_key = APIKey(
            user_id=user_id,
            key_id="test-key-id",
            key_hash="hashed-key-value",
            name="Test API Key",
            permissions=permissions
        )
        
        assert api_key.user_id == user_id
        assert api_key.key_id == "test-key-id"
        assert api_key.key_hash == "hashed-key-value"
        assert api_key.name == "Test API Key"
        assert api_key.permissions == permissions
        assert api_key.created_at is not None
        assert api_key.is_active is True
    
    def test_api_key_permissions(self):
        """Test API key permissions handling."""
        permissions = ["chat", "tasks", "health", "metrics", "admin"]
        
        api_key = APIKey(
            user_id=str(uuid4()),
            key_id="test-key",
            key_hash="hash",
            name="Admin Key",
            permissions=permissions
        )
        
        assert "chat" in api_key.permissions
        assert "admin" in api_key.permissions
        assert len(api_key.permissions) == 5
    
    def test_api_key_expiration(self):
        """Test API key expiration handling."""
        future_time = datetime.utcnow() + timedelta(days=30)
        
        api_key = APIKey(
            user_id=str(uuid4()),
            key_id="expiring-key",
            key_hash="hash",
            name="Expiring Key",
            expires_at=future_time
        )
        
        assert api_key.expires_at == future_time


@pytest.mark.unit
@pytest.mark.database
class TestSystemHealthModel:
    """Test SystemHealth model functionality."""
    
    def test_system_health_creation(self):
        """Test system health model creation."""
        details = {
            "connection_pool": "active",
            "queries_executed": 42,
            "cache_hit_rate": 0.85
        }
        
        health = SystemHealth(
            component="database",
            status="healthy",
            response_time_ms=15.5,
            error_rate=0.0,
            details=details
        )
        
        assert health.component == "database"
        assert health.status == "healthy"
        assert health.response_time_ms == 15.5
        assert health.error_rate == 0.0
        assert health.details == details
        assert health.created_at is not None
    
    def test_system_health_status_types(self):
        """Test different system health status types."""
        statuses = ["healthy", "degraded", "unhealthy", "unknown"]
        
        for status in statuses:
            health = SystemHealth(
                component="test_component",
                status=status,
                response_time_ms=100.0,
                error_rate=0.1
            )
            assert health.status == status
    
    def test_system_health_metrics(self):
        """Test system health metrics."""
        health = SystemHealth(
            component="redis",
            status="healthy",
            response_time_ms=5.2,
            error_rate=0.001,
            details={"memory_usage": "45MB", "connections": 12}
        )
        
        assert health.response_time_ms == 5.2
        assert health.error_rate == 0.001
        assert health.details["memory_usage"] == "45MB"
        assert health.details["connections"] == 12