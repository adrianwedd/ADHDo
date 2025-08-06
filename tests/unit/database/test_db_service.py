"""
Unit tests for DatabaseService.
"""
import pytest
from datetime import datetime, timedelta

from tests.utils import TestDataFactory, DatabaseAssertions


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseService:
    """Test DatabaseService functionality."""
    
    async def test_service_initialization(self, test_db_session):
        """Test database service initialization."""
        from mcp_server.db_service import DatabaseService
        
        db_service = DatabaseService(test_db_session)
        
        assert db_service.session == test_db_session
        assert hasattr(db_service, 'users')
        assert hasattr(db_service, 'tasks')
        assert hasattr(db_service, 'trace_memory')
        assert hasattr(db_service, 'sessions')
        assert hasattr(db_service, 'api_keys')
        assert hasattr(db_service, 'system_health')
    
    async def test_create_user_with_validation(self, db_service):
        """Test user creation with validation."""
        # Valid user data
        user = await db_service.create_user(
            name="Valid User",
            email="valid@example.com",
            telegram_chat_id="123456789"
        )
        
        assert user.name == "Valid User"
        assert user.email == "valid@example.com"
        assert user.telegram_chat_id == "123456789"
        
        # Test duplicate email handling
        with pytest.raises(Exception):  # Should raise integrity error
            await db_service.create_user(
                name="Duplicate User",
                email="valid@example.com",  # Same email
                telegram_chat_id="987654321"
            )
    
    async def test_create_task_with_defaults(self, db_service, test_user):
        """Test task creation with default values."""
        task = await db_service.create_task(
            user_id=test_user.user_id,
            title="Minimal Task",
            description="A task with minimal information"
        )
        
        assert task.title == "Minimal Task"
        assert task.user_id == test_user.user_id
        assert task.priority == 3  # Default priority
        assert task.energy_required == "medium"  # Default energy
        assert task.estimated_focus_time == 25  # Default focus time
        assert task.status == "pending"
        assert task.completion_percentage == 0.0
        assert task.dopamine_reward_tier is not None
    
    async def test_complete_task_workflow(self, db_service, test_user):
        """Test complete task workflow from creation to completion."""
        # Create task
        task = await db_service.create_task(
            user_id=test_user.user_id,
            title="Workflow Test Task",
            priority=4,
            energy_required="high"
        )
        
        # Start task
        started_task = await db_service.tasks.update_status(
            task.task_id, "in_progress"
        )
        assert started_task.status == "in_progress"
        
        # Update progress
        progress_task = await db_service.tasks.update_status(
            task.task_id, "in_progress", completion_percentage=0.5
        )
        assert progress_task.completion_percentage == 0.5
        
        # Complete task with reward
        completed_task, reward = await db_service.complete_task_with_reward(
            task.task_id
        )
        
        assert completed_task.status == "completed"
        assert completed_task.completion_percentage == 1.0
        assert completed_task.completed_at is not None
        assert reward["points"] > 0
        assert "congratulations" in reward["message"].lower() or "great" in reward["message"].lower()
    
    async def test_trace_memory_context_building(self, db_service, test_user, test_task):
        """Test trace memory and context building."""
        # Record various traces to build user context
        trace_scenarios = [
            {
                "trace_type": "user_input",
                "content": {"message": "I'm feeling stuck on this task", "emotion": "frustrated"},
                "cognitive_load": 0.7,
                "was_successful": True
            },
            {
                "trace_type": "system_response", 
                "content": {"response": "Let's break this down into smaller steps", "strategy": "decomposition"},
                "cognitive_load": 0.5,
                "was_successful": True
            },
            {
                "trace_type": "task_progress",
                "content": {"progress": "Started working", "focus_time": 15},
                "cognitive_load": 0.4,
                "was_successful": True,
                "task_id": test_task.task_id
            },
            {
                "trace_type": "user_input",
                "content": {"message": "This is working better now", "emotion": "encouraged"},
                "cognitive_load": 0.3,
                "was_successful": True
            }
        ]
        
        # Record all traces
        for scenario in trace_scenarios:
            await db_service.record_trace(
                user_id=test_user.user_id,
                **scenario
            )
        
        # Get user context
        context = await db_service.get_user_context(test_user.user_id)
        
        assert context["recent_interactions"] == 4
        assert context["active_task_count"] >= 1
        assert 0.3 <= context["avg_cognitive_load"] <= 0.7  # Average of our test values
        
        # Check pattern indicators
        assert "pattern_indicators" in context
        patterns = context["pattern_indicators"]
        
        # Should detect emotional progression from frustrated to encouraged
        assert any("emotional" in str(pattern).lower() for pattern in patterns)
    
    async def test_session_management(self, db_service, test_user):
        """Test session management functionality."""
        # Create session
        session_id = await db_service.create_session(
            user_id=test_user.user_id,
            duration_hours=24,
            user_agent="Test/1.0",
            ip_address="192.168.1.100"
        )
        
        assert session_id is not None
        
        # Validate session
        user = await db_service.validate_session(session_id)
        assert user is not None
        assert user.user_id == test_user.user_id
        
        # Test session info retrieval
        session_info = await db_service.get_session_info(session_id)
        assert session_info is not None
        assert session_info["user_id"] == test_user.user_id
        assert session_info["user_agent"] == "Test/1.0"
        assert session_info["ip_address"] == "192.168.1.100"
    
    async def test_api_key_management(self, db_service, test_user):
        """Test API key management functionality."""
        # Create API key
        key_id, api_key = await db_service.create_api_key(
            user_id=test_user.user_id,
            name="Test Integration Key",
            permissions=["chat", "tasks", "health", "metrics"]
        )
        
        assert key_id is not None
        assert api_key is not None
        
        # Validate API key
        user = await db_service.validate_api_key(api_key)
        assert user is not None
        assert user.user_id == test_user.user_id
        
        # Test API key permissions
        permissions = await db_service.get_api_key_permissions(api_key)
        assert "chat" in permissions
        assert "tasks" in permissions
        assert "health" in permissions
        assert "metrics" in permissions
        
        # Test API key usage tracking
        await db_service.record_api_key_usage(api_key, "GET", "/health")
        usage_stats = await db_service.get_api_key_usage(key_id)
        assert usage_stats["total_requests"] >= 1
    
    async def test_system_health_recording(self, db_service):
        """Test system health recording functionality."""
        # Record health for different components
        components = ["database", "redis", "llm", "system", "application"]
        
        for i, component in enumerate(components):
            await db_service.record_system_health(
                component=component,
                status="healthy" if i % 2 == 0 else "degraded",
                response_time_ms=10.0 + i * 5,
                error_rate=0.0 if i % 2 == 0 else 0.1,
                details={
                    "test_run": True,
                    "component_index": i,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Get system status
        system_status = await db_service.get_system_status()
        
        assert "overall" in system_status
        assert "database" in system_status
        assert "redis" in system_status
        assert "llm" in system_status
        assert "system" in system_status
        assert "application" in system_status
        
        # Check overall status calculation
        overall_status = system_status["overall"]["status"]
        assert overall_status in ["healthy", "degraded", "unhealthy"]
    
    async def test_user_analytics(self, db_service, test_user):
        """Test user analytics functionality."""
        # Create some data for analytics
        tasks = []
        for i in range(5):
            task = await db_service.create_task(
                user_id=test_user.user_id,
                title=f"Analytics Task {i+1}",
                priority=((i % 5) + 1),
                energy_required=["low", "medium", "high"][i % 3]
            )
            tasks.append(task)
        
        # Complete some tasks
        for i in range(3):
            await db_service.complete_task_with_reward(tasks[i].task_id)
        
        # Record some traces
        for i in range(10):
            await db_service.record_trace(
                user_id=test_user.user_id,
                trace_type="user_input",
                content={"message": f"Test input {i}", "iteration": i},
                cognitive_load=0.1 + (i * 0.08),  # Increasing cognitive load
                was_successful=True
            )
        
        # Get user analytics
        analytics = await db_service.get_user_analytics(test_user.user_id)
        
        assert "tasks" in analytics
        assert analytics["tasks"]["total"] == 5
        assert analytics["tasks"]["completed"] == 3
        assert analytics["tasks"]["completion_rate"] == 0.6
        
        assert "traces" in analytics
        assert analytics["traces"]["total"] >= 10
        
        assert "cognitive_load" in analytics
        assert "avg_cognitive_load" in analytics["cognitive_load"]
        assert "trend" in analytics["cognitive_load"]
        
        # Check if trend is detected (should be increasing)
        assert analytics["cognitive_load"]["trend"] in ["increasing", "stable", "decreasing"]
    
    async def test_task_scheduling_suggestions(self, db_service, test_user):
        """Test task scheduling and suggestion logic."""
        # Create tasks with different characteristics
        urgent_task = await db_service.create_task(
            user_id=test_user.user_id,
            title="Urgent Task",
            priority=5,
            energy_required="low",
            estimated_focus_time=15,
            due_date=datetime.utcnow() + timedelta(hours=2)
        )
        
        important_task = await db_service.create_task(
            user_id=test_user.user_id,
            title="Important Task",
            priority=4,
            energy_required="medium",
            estimated_focus_time=45
        )
        
        easy_task = await db_service.create_task(
            user_id=test_user.user_id,
            title="Easy Task",
            priority=2,
            energy_required="low",
            estimated_focus_time=10
        )
        
        # Test suggestions for different energy levels
        low_energy_suggestion = await db_service.suggest_next_task(
            test_user.user_id, "low"
        )
        assert low_energy_suggestion is not None
        assert low_energy_suggestion.energy_required == "low"
        # Should prefer urgent task over easy task due to priority
        assert low_energy_suggestion.task_id == urgent_task.task_id
        
        high_energy_suggestion = await db_service.suggest_next_task(
            test_user.user_id, "high"
        )
        assert high_energy_suggestion is not None
        # Should suggest the important medium energy task for high energy state
        assert high_energy_suggestion.task_id == important_task.task_id
    
    async def test_database_transaction_handling(self, db_service, test_user):
        """Test database transaction handling and rollback."""
        initial_task_count = len(await db_service.get_user_active_tasks(test_user.user_id))
        
        try:
            # Start a transaction that will fail
            async with db_service.session.begin():
                # Create a task
                task = await db_service.create_task(
                    user_id=test_user.user_id,
                    title="Transaction Test Task"
                )
                
                # Simulate an error that should cause rollback
                raise ValueError("Simulated transaction error")
        
        except ValueError:
            pass  # Expected error
        
        # Verify that the task was not committed due to rollback
        final_task_count = len(await db_service.get_user_active_tasks(test_user.user_id))
        assert final_task_count == initial_task_count
    
    async def test_performance_metrics(self, db_service, test_user):
        """Test performance metrics collection."""
        import time
        
        # Test database operation timing
        start_time = time.time()
        
        # Perform various operations
        user = await db_service.users.get_by_id(test_user.user_id)
        task = await db_service.create_task(
            user_id=test_user.user_id,
            title="Performance Test Task"
        )
        traces = await db_service.get_user_traces(test_user.user_id, limit=5)
        context = await db_service.get_user_context(test_user.user_id)
        
        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert total_time_ms < 1000  # Less than 1 second for basic operations
        
        # Test bulk operations performance
        bulk_start = time.time()
        
        # Create multiple traces
        for i in range(20):
            await db_service.record_trace(
                user_id=test_user.user_id,
                trace_type="bulk_test",
                content={"index": i},
                cognitive_load=0.1,
                was_successful=True
            )
        
        bulk_end = time.time()
        bulk_time_ms = (bulk_end - bulk_start) * 1000
        
        # Bulk operations should also complete reasonably quickly
        assert bulk_time_ms < 2000  # Less than 2 seconds for 20 trace records
        
        # Average time per operation should be reasonable
        avg_time_per_trace = bulk_time_ms / 20
        assert avg_time_per_trace < 100  # Less than 100ms per trace record