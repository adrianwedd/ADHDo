"""
Unit tests for database layer components.

Tests models, repositories, and services with comprehensive coverage.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from mcp_server.db_models import User, Task, TraceMemory, Session, APIKey, SystemHealth
from mcp_server.repositories import (
    UserRepository, TaskRepository, TraceMemoryRepository,
    SessionRepository, APIKeyRepository, SystemHealthRepository
)
from mcp_server.db_service import DatabaseService


class TestDatabaseModels:
    """Test database model functionality."""

    @pytest.mark.unit
    @pytest.mark.database
    async def test_user_model_creation(self, db_session, test_data_factory):
        """Test User model creation and validation."""
        user_data = test_data_factory.create_user_data()
        user = User(**user_data)
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.user_id is not None
        assert user.name == user_data['name']
        assert user.email == user_data['email']
        assert user.is_active is True
        assert user.preferred_nudge_methods == ['web', 'telegram']
        assert 'peak_hours' in user.energy_patterns

    @pytest.mark.unit
    @pytest.mark.database
    async def test_task_model_adhd_features(self, db_session, test_user, test_data_factory):
        """Test Task model ADHD-specific features."""
        task_data = test_data_factory.create_task_data(test_user.user_id)
        task_data.update({
            'energy_required': 'high',
            'dopamine_reward_tier': 5,
            'hyperfocus_compatible': True,
            'estimated_focus_time': 120
        })
        
        task = Task(**task_data)
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        
        assert task.energy_required == 'high'
        assert task.dopamine_reward_tier == 5
        assert task.hyperfocus_compatible is True
        assert task.estimated_focus_time == 120
        assert task.completion_percentage == 0.0
        assert task.nudge_count == 0

    @pytest.mark.unit
    @pytest.mark.database
    async def test_trace_memory_model(self, db_session, test_user, test_data_factory):
        """Test TraceMemory model for context tracking."""
        trace_data = test_data_factory.create_trace_data(test_user.user_id)
        trace_data.update({
            'cognitive_load': 0.65,
            'processing_time_ms': 125.5,
            'was_successful': True
        })
        
        trace = TraceMemory(**trace_data)
        db_session.add(trace)
        await db_session.commit()
        await db_session.refresh(trace)
        
        assert trace.cognitive_load == 0.65
        assert trace.processing_time_ms == 125.5
        assert trace.was_successful is True
        assert trace.trace_type == 'user_input'
        assert 'message' in trace.content

    @pytest.mark.unit
    @pytest.mark.database
    async def test_model_relationships(self, db_session, test_user, test_task, test_trace):
        """Test relationships between models."""
        # Reload user with relationships
        user = await db_session.get(User, test_user.user_id)
        await db_session.refresh(user, ['tasks', 'traces'])
        
        assert len(user.tasks) >= 1
        assert len(user.traces) >= 1
        assert user.tasks[0].user_id == user.user_id
        assert user.traces[0].user_id == user.user_id


class TestUserRepository:
    """Test UserRepository operations."""

    @pytest.mark.unit
    @pytest.mark.database
    async def test_create_user(self, db_session, test_data_factory):
        """Test user creation."""
        repo = UserRepository(db_session)
        user_data = test_data_factory.create_user_data()
        
        user = await repo.create(user_data)
        
        assert user.user_id is not None
        assert user.name == user_data['name']
        assert user.is_active is True

    @pytest.mark.unit
    @pytest.mark.database
    async def test_get_user_by_id(self, db_session, test_user):
        """Test user retrieval by ID."""
        repo = UserRepository(db_session)
        
        user = await repo.get_by_id(test_user.user_id)
        
        assert user is not None
        assert user.user_id == test_user.user_id
        assert user.name == test_user.name

    @pytest.mark.unit
    @pytest.mark.database
    async def test_get_user_by_email(self, db_session, test_user):
        """Test user retrieval by email."""
        repo = UserRepository(db_session)
        
        user = await repo.get_by_email(test_user.email)
        
        assert user is not None
        assert user.email == test_user.email

    @pytest.mark.unit
    @pytest.mark.database
    async def test_update_user(self, db_session, test_user):
        """Test user update."""
        repo = UserRepository(db_session)
        
        updated_user = await repo.update(test_user.user_id, {
            'name': 'Updated ADHD User',
            'preferred_nudge_methods': ['telegram', 'email']
        })
        
        assert updated_user.name == 'Updated ADHD User'
        assert 'email' in updated_user.preferred_nudge_methods

    @pytest.mark.unit
    @pytest.mark.database
    async def test_update_last_login(self, db_session, test_user):
        """Test last login update."""
        repo = UserRepository(db_session)
        original_login = test_user.last_login
        
        await repo.update_last_login(test_user.user_id)
        await db_session.refresh(test_user)
        
        assert test_user.last_login != original_login
        assert test_user.last_login is not None


class TestTaskRepository:
    """Test TaskRepository ADHD-specific operations."""

    @pytest.mark.unit
    @pytest.mark.database
    async def test_create_task_with_adhd_features(self, db_session, test_user, test_data_factory):
        """Test task creation with ADHD features."""
        repo = TaskRepository(db_session)
        task_data = test_data_factory.create_task_data(test_user.user_id)
        task_data.update({
            'energy_required': 'low',
            'dopamine_reward_tier': 4,
            'hyperfocus_compatible': True
        })
        
        task = await repo.create(task_data)
        
        assert task.energy_required == 'low'
        assert task.dopamine_reward_tier == 4
        assert task.hyperfocus_compatible is True

    @pytest.mark.unit
    @pytest.mark.database
    async def test_get_pending_tasks(self, db_session, test_user, test_data_factory):
        """Test retrieval of pending tasks."""
        repo = TaskRepository(db_session)
        
        # Create multiple tasks with different statuses
        for status in ['pending', 'in_progress', 'completed']:
            task_data = test_data_factory.create_task_data(test_user.user_id)
            task_data['status'] = status
            await repo.create(task_data)
        
        pending_tasks = await repo.get_pending_tasks(test_user.user_id)
        
        assert len(pending_tasks) >= 2  # pending and in_progress
        for task in pending_tasks:
            assert task.status in ['pending', 'in_progress']

    @pytest.mark.unit
    @pytest.mark.database
    async def test_get_overdue_tasks(self, db_session, test_user, test_data_factory):
        """Test retrieval of overdue tasks."""
        repo = TaskRepository(db_session)
        
        # Create overdue task
        task_data = test_data_factory.create_task_data(test_user.user_id)
        task_data['due_date'] = datetime.utcnow() - timedelta(days=1)
        task_data['status'] = 'pending'
        await repo.create(task_data)
        
        overdue_tasks = await repo.get_overdue_tasks(test_user.user_id)
        
        assert len(overdue_tasks) >= 1
        assert all(task.due_date < datetime.utcnow() for task in overdue_tasks)

    @pytest.mark.unit
    @pytest.mark.database
    async def test_complete_task(self, db_session, test_task):
        """Test task completion."""
        repo = TaskRepository(db_session)
        
        completed_task = await repo.complete_task(test_task.task_id)
        
        assert completed_task.status == 'completed'
        assert completed_task.completion_percentage == 1.0
        assert completed_task.completed_at is not None

    @pytest.mark.unit
    @pytest.mark.database
    async def test_increment_nudge_count(self, db_session, test_task):
        """Test nudge count increment."""
        repo = TaskRepository(db_session)
        original_count = test_task.nudge_count
        
        await repo.increment_nudge_count(test_task.task_id)
        await db_session.refresh(test_task)
        
        assert test_task.nudge_count == original_count + 1
        assert test_task.last_nudge_at is not None


class TestTraceMemoryRepository:
    """Test TraceMemoryRepository for context tracking."""

    @pytest.mark.unit
    @pytest.mark.database
    async def test_create_trace(self, db_session, test_user, test_data_factory):
        """Test trace memory creation."""
        repo = TraceMemoryRepository(db_session)
        trace_data = test_data_factory.create_trace_data(test_user.user_id)
        
        trace = await repo.create(trace_data)
        
        assert trace.user_id == test_user.user_id
        assert trace.cognitive_load == trace_data['cognitive_load']
        assert trace.was_successful is True

    @pytest.mark.unit
    @pytest.mark.database
    async def test_get_user_traces(self, db_session, test_user, test_data_factory):
        """Test user trace retrieval."""
        repo = TraceMemoryRepository(db_session)
        
        # Create multiple traces
        for trace_type in ['user_input', 'system_response', 'nudge']:
            trace_data = test_data_factory.create_trace_data(test_user.user_id)
            trace_data['trace_type'] = trace_type
            await repo.create(trace_data)
        
        traces = await repo.get_user_traces(test_user.user_id)
        
        assert len(traces) >= 3
        assert all(trace.user_id == test_user.user_id for trace in traces)

    @pytest.mark.unit
    @pytest.mark.database
    async def test_get_session_traces(self, db_session, test_user, test_data_factory):
        """Test session trace retrieval."""
        repo = TraceMemoryRepository(db_session)
        session_id = "test-session-123"
        
        # Create traces for specific session
        for i in range(3):
            trace_data = test_data_factory.create_trace_data(test_user.user_id)
            trace_data['session_id'] = session_id
            await repo.create(trace_data)
        
        session_traces = await repo.get_session_traces(session_id)
        
        assert len(session_traces) == 3
        assert all(trace.session_id == session_id for trace in session_traces)

    @pytest.mark.unit
    @pytest.mark.database
    async def test_cleanup_old_traces(self, db_session, test_user, test_data_factory):
        """Test old trace cleanup."""
        repo = TraceMemoryRepository(db_session)
        
        # Create old trace
        old_trace_data = test_data_factory.create_trace_data(test_user.user_id)
        old_trace = TraceMemory(**old_trace_data)
        old_trace.created_at = datetime.utcnow() - timedelta(days=100)
        db_session.add(old_trace)
        await db_session.commit()
        
        # Create recent trace
        recent_trace_data = test_data_factory.create_trace_data(test_user.user_id)
        await repo.create(recent_trace_data)
        
        cleanup_count = await repo.cleanup_old_traces(days=90)
        
        assert cleanup_count >= 1


class TestDatabaseService:
    """Test DatabaseService business logic."""

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.adhd
    async def test_create_user_with_adhd_defaults(self, db_session):
        """Test user creation with ADHD defaults."""
        service = DatabaseService(db_session)
        
        user = await service.create_user(
            name="ADHD Test User",
            email="adhd@example.com"
        )
        
        assert user.name == "ADHD Test User"
        assert 'web' in user.preferred_nudge_methods
        assert 'peak_hours' in user.energy_patterns
        assert 'hyperfocus_indicators' in user.__dict__

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.adhd
    async def test_create_task_with_dopamine_optimization(self, db_session, test_user):
        """Test task creation with dopamine optimization."""
        service = DatabaseService(db_session)
        
        task = await service.create_task(
            user_id=test_user.user_id,
            title="High priority ADHD task",
            priority=5,
            energy_required="high",
            estimated_focus_time=90
        )
        
        assert task.dopamine_reward_tier == 5  # Should match priority
        assert task.hyperfocus_compatible is True  # >60 minutes
        assert task.energy_required == "high"

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.adhd
    async def test_suggest_next_task_energy_matching(self, db_session, test_user, test_data_factory):
        """Test task suggestion with energy matching."""
        service = DatabaseService(db_session)
        
        # Create tasks with different energy requirements
        for energy in ['low', 'medium', 'high']:
            task_data = test_data_factory.create_task_data(test_user.user_id)
            task_data.update({
                'energy_required': energy,
                'priority': 3,
                'status': 'pending'
            })
            await service.create_task(**task_data)
        
        # Test energy matching
        suggested_task = await service.suggest_next_task(test_user.user_id, current_energy="low")
        
        assert suggested_task is not None
        # Should suggest low or medium energy task when user has low energy

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.adhd
    async def test_complete_task_with_reward(self, db_session, test_task):
        """Test task completion with dopamine reward calculation."""
        service = DatabaseService(db_session)
        
        completed_task, reward = await service.complete_task_with_reward(test_task.task_id)
        
        assert completed_task.status == 'completed'
        assert reward['points'] == test_task.dopamine_reward_tier * 10
        assert reward['celebration_level'] == test_task.dopamine_reward_tier
        assert 'message' in reward

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.adhd
    async def test_get_user_context_analysis(self, db_session, test_user, test_data_factory):
        """Test user context analysis for ADHD patterns."""
        service = DatabaseService(db_session)
        
        # Create various traces to build context
        trace_types = ['user_input', 'system_response', 'completion']
        for trace_type in trace_types:
            for i in range(3):
                trace_data = test_data_factory.create_trace_data(test_user.user_id)
                trace_data.update({
                    'trace_type': trace_type,
                    'was_successful': True,
                    'cognitive_load': 0.3 + (i * 0.1),
                    'processing_time_ms': 50 + (i * 20)
                })
                await service.record_trace(**trace_data)
        
        context = await service.get_user_context(test_user.user_id)
        
        assert 'recent_interactions' in context
        assert 'active_task_count' in context
        assert 'avg_response_time' in context
        assert 'cognitive_load_trend' in context
        assert context['cognitive_load_trend'] in ['stable', 'increasing', 'decreasing']

    @pytest.mark.unit
    @pytest.mark.database
    async def test_record_trace_with_context(self, db_session, test_user, test_task):
        """Test trace recording with full context."""
        service = DatabaseService(db_session)
        
        trace = await service.record_trace(
            user_id=test_user.user_id,
            trace_type='completion',
            content={'task_completed': True, 'satisfaction': 'high'},
            task_id=test_task.task_id,
            processing_time_ms=150.0,
            cognitive_load=0.4,
            was_successful=True,
            source='web'
        )
        
        assert trace.user_id == test_user.user_id
        assert trace.task_id == test_task.task_id
        assert trace.cognitive_load == 0.4
        assert trace.source == 'web'

    @pytest.mark.unit
    @pytest.mark.database
    async def test_session_management(self, db_session, test_user):
        """Test session creation and validation."""
        service = DatabaseService(db_session)
        
        # Create session
        session_id = await service.create_session(
            user_id=test_user.user_id,
            duration_hours=24,
            user_agent="Test-Agent/1.0"
        )
        
        assert session_id is not None
        assert len(session_id) > 20  # Should be a substantial token
        
        # Validate session
        validated_user = await service.validate_session(session_id)
        assert validated_user is not None
        assert validated_user.user_id == test_user.user_id

    @pytest.mark.unit
    @pytest.mark.database
    async def test_api_key_management(self, db_session, test_user):
        """Test API key creation and validation."""
        service = DatabaseService(db_session)
        
        # Create API key
        key_id, api_key = await service.create_api_key(
            user_id=test_user.user_id,
            name="Test API Key",
            permissions=['chat', 'tasks']
        )
        
        assert key_id.startswith('mk_')
        assert '.' in api_key
        assert api_key.startswith(key_id)
        
        # Validate API key
        validated_user = await service.validate_api_key(api_key)
        assert validated_user is not None
        assert validated_user.user_id == test_user.user_id

    @pytest.mark.unit
    @pytest.mark.database
    async def test_system_health_recording(self, db_session):
        """Test system health metrics recording."""
        service = DatabaseService(db_session)
        
        await service.record_system_health(
            component='database',
            status='healthy',
            response_time_ms=25.5,
            error_rate=0.01,
            details={'queries_executed': 150, 'connection_pool': 'active'}
        )
        
        # Verify health record was created
        health_records = await service.health.get_health_history('database', hours=1)
        assert len(health_records) >= 1
        
        latest_health = health_records[-1]
        assert latest_health.component == 'database'
        assert latest_health.status == 'healthy'
        assert latest_health.response_time_ms == 25.5

    @pytest.mark.unit
    @pytest.mark.database
    async def test_password_hashing(self, db_session):
        """Test password hashing functionality."""
        service = DatabaseService(db_session)
        
        password = "secure_adhd_password_123"
        hashed = service._hash_password(password)
        
        assert ':' in hashed  # Salt:hash format
        assert service._verify_password(password, hashed) is True
        assert service._verify_password("wrong_password", hashed) is False

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.performance
    async def test_database_performance(self, db_session, test_user, performance_thresholds):
        """Test database operations meet performance requirements."""
        service = DatabaseService(db_session)
        
        import time
        
        # Test user retrieval performance
        start_time = time.time()
        user = await service.users.get_by_id(test_user.user_id)
        query_time_ms = (time.time() - start_time) * 1000
        
        assert query_time_ms < performance_thresholds['max_database_query_ms']
        assert user is not None
        
        # Test task creation performance
        start_time = time.time()
        task = await service.create_task(
            user_id=test_user.user_id,
            title="Performance test task"
        )
        creation_time_ms = (time.time() - start_time) * 1000
        
        assert creation_time_ms < performance_thresholds['max_database_query_ms']
        assert task is not None