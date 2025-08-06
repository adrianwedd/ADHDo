"""
Comprehensive test configuration and fixtures for MCP ADHD Server.

Provides test database, mocks, and utilities for all test types.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi.testclient import TestClient
import httpx

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_server.database import Base
from mcp_server.db_models import User, Task, TraceMemory, Session, APIKey, SystemHealth
from mcp_server.models import NudgeTier
from mcp_server.config import settings


# === TEST DATABASE SETUP ===

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    # Use in-memory SQLite for fast tests
    database_url = "sqlite+aiosqlite:///:memory:"
    
    engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Create isolated database session for each test."""
    SessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


# === MOCK FIXTURES ===

@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    with patch('traces.memory.trace_memory') as mock:
        mock.connect = AsyncMock()
        mock.disconnect = AsyncMock()
        mock.store_trace = AsyncMock()
        mock.get_trace = AsyncMock(return_value={"content": {"test": "data"}})
        mock.get_context = AsyncMock(return_value=[])
        mock.redis = MagicMock()
        yield mock


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Test LLM response for ADHD support"
    
    with patch('mcp_server.llm_client.AsyncOpenAI') as mock:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_telegram():
    """Mock Telegram Bot API."""
    with patch('mcp_server.telegram_bot.AsyncHTTPXClient') as mock:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {}}
        mock_client.post = AsyncMock(return_value=mock_response)
        mock.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_client


@pytest.fixture
def mock_system_metrics():
    """Mock system metrics for health monitoring."""
    with patch('psutil.cpu_percent') as mock_cpu, \
         patch('psutil.virtual_memory') as mock_memory, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.getloadavg') as mock_load:
        
        mock_cpu.return_value = 45.2
        
        mock_memory.return_value = MagicMock()
        mock_memory.return_value.percent = 62.1
        mock_memory.return_value.available = 2048 * 1024 * 1024  # 2GB
        
        mock_disk.return_value = MagicMock()
        mock_disk.return_value.percent = 78.5
        mock_disk.return_value.free = 50 * 1024 * 1024 * 1024  # 50GB
        
        mock_load.return_value = (1.2, 1.4, 1.6)
        
        yield {
            'cpu': mock_cpu,
            'memory': mock_memory,
            'disk': mock_disk,
            'load': mock_load
        }


# === TEST DATA FACTORIES ===

class TestDataFactory:
    """Factory for creating realistic test data."""
    
    @staticmethod
    def create_user_data(**kwargs) -> Dict[str, Any]:
        """Create test user data."""
        defaults = {
            'user_id': f'test-user-{datetime.utcnow().timestamp()}',
            'name': 'Test ADHD User',
            'email': 'test@adhd.example.com',
            'timezone': 'UTC',
            'preferred_nudge_methods': ['web', 'telegram'],
            'nudge_timing_preferences': {
                'morning': '09:00',
                'afternoon': '14:00',
                'evening': '18:00'
            },
            'energy_patterns': {
                'peak_hours': [9, 10, 11, 14, 15, 16],
                'low_hours': [12, 13, 17, 18, 19]
            },
            'hyperfocus_indicators': ['long_sessions', 'delayed_responses']
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_task_data(user_id: str, **kwargs) -> Dict[str, Any]:
        """Create test task data."""
        defaults = {
            'user_id': user_id,
            'title': 'Complete important project task',
            'description': 'This is a test task for ADHD management',
            'priority': 3,
            'energy_required': 'medium',
            'estimated_focus_time': 45,
            'dopamine_reward_tier': 3,
            'hyperfocus_compatible': False,
            'tags': ['work', 'project', 'important'],
            'context_triggers': ['time', 'energy', 'location'],
            'preferred_time_blocks': ['morning', 'afternoon']
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_trace_data(user_id: str, **kwargs) -> Dict[str, Any]:
        """Create test trace memory data."""
        defaults = {
            'user_id': user_id,
            'trace_type': 'user_input',
            'content': {
                'message': "I'm feeling overwhelmed with tasks",
                'context': 'user_interaction',
                'intent': 'help_request'
            },
            'processing_time_ms': 85.5,
            'cognitive_load': 0.7,
            'was_successful': True,
            'source': 'web'
        }
        defaults.update(kwargs)
        return defaults


@pytest.fixture
def test_data_factory():
    """Provide test data factory."""
    return TestDataFactory


# === DATABASE FIXTURES ===

@pytest.fixture
async def test_user(db_session, test_data_factory):
    """Create test user in database."""
    user_data = test_data_factory.create_user_data()
    user = User(**user_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_task(db_session, test_user, test_data_factory):
    """Create test task in database."""
    task_data = test_data_factory.create_task_data(test_user.user_id)
    task = Task(**task_data)
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.fixture
async def test_trace(db_session, test_user, test_data_factory):
    """Create test trace memory in database."""
    trace_data = test_data_factory.create_trace_data(test_user.user_id)
    trace = TraceMemory(**trace_data)
    db_session.add(trace)
    await db_session.commit()
    await db_session.refresh(trace)
    return trace


# === APPLICATION FIXTURES ===

@pytest.fixture
def app_with_mocks(mock_redis, mock_openai, mock_system_metrics):
    """Create FastAPI app with all external dependencies mocked."""
    # Import here to ensure mocks are in place
    from mcp_server.main import app
    return app


@pytest.fixture
def test_client(app_with_mocks):
    """Create test client with mocked dependencies."""
    return TestClient(app_with_mocks)


@pytest.fixture
async def async_client(app_with_mocks):
    """Create async test client."""
    async with httpx.AsyncClient(app=app_with_mocks, base_url="http://test") as client:
        yield client


# === ADHD-SPECIFIC TEST UTILITIES ===

class ADHDTestHelpers:
    """Utilities for testing ADHD-specific functionality."""
    
    @staticmethod
    def generate_adhd_scenarios() -> List[Dict[str, Any]]:
        """Generate common ADHD interaction scenarios."""
        return [
            {
                'name': 'overwhelmed_state',
                'input': "I have so many tasks I don't know where to start",
                'expected_cognitive_load': 0.8,
                'expected_response_time_ms': 1500,
                'expected_pattern': 'overwhelmed'
            },
            {
                'name': 'ready_state',
                'input': "I'm ready to work!",
                'expected_cognitive_load': 0.2,
                'expected_response_time_ms': 10,
                'expected_pattern': 'ready'
            },
            {
                'name': 'stuck_state',
                'input': "I'm stuck and can't make progress",
                'expected_cognitive_load': 0.6,
                'expected_response_time_ms': 800,
                'expected_pattern': 'stuck'
            },
            {
                'name': 'hyperfocus_entry',
                'input': "I want to dive deep into this project",
                'expected_cognitive_load': 0.3,
                'expected_response_time_ms': 500,
                'expected_pattern': 'focus'
            },
            {
                'name': 'break_needed',
                'input': "I need a break, I'm getting tired",
                'expected_cognitive_load': 0.7,
                'expected_response_time_ms': 200,
                'expected_pattern': 'break'
            }
        ]
    
    @staticmethod
    def validate_adhd_response(response: Dict[str, Any], scenario: Dict[str, Any]) -> bool:
        """Validate response meets ADHD-specific requirements."""
        # Check response time is ADHD-appropriate (fast enough to maintain focus)
        response_time = response.get('processing_time_ms', float('inf'))
        if response_time > scenario['expected_response_time_ms']:
            return False
        
        # Check cognitive load is calculated
        if 'cognitive_load' not in response:
            return False
        
        # Check response is helpful and not overwhelming
        response_text = response.get('response', '')
        if len(response_text) > 500:  # Too long for ADHD attention span
            return False
        
        return True


@pytest.fixture
def adhd_helpers():
    """Provide ADHD test helpers."""
    return ADHDTestHelpers


# === PERFORMANCE TEST UTILITIES ===

class PerformanceAssertions:
    """Assertions for ADHD-specific performance requirements."""
    
    @staticmethod
    def assert_response_time_adhd_friendly(response_time_ms: float, max_time_ms: float = 3000):
        """Assert response time meets ADHD requirements."""
        assert response_time_ms < max_time_ms, \
            f"Response time {response_time_ms}ms exceeds ADHD-friendly limit of {max_time_ms}ms"
    
    @staticmethod
    def assert_cognitive_load_reasonable(cognitive_load: float):
        """Assert cognitive load is within reasonable bounds."""
        assert 0.0 <= cognitive_load <= 1.0, \
            f"Cognitive load {cognitive_load} must be between 0.0 and 1.0"
    
    @staticmethod
    def assert_pattern_match_fast(response_time_ms: float):
        """Assert pattern matching is ultra-fast for ADHD."""
        assert response_time_ms < 100, \
            f"Pattern matching took {response_time_ms}ms, should be <100ms for ADHD users"


@pytest.fixture
def performance_assertions():
    """Provide performance assertion utilities."""
    return PerformanceAssertions


# === HEALTH CHECK UTILITIES ===

class HealthCheckAssertions:
    """Utilities for testing health check functionality."""
    
    @staticmethod
    def assert_health_response_valid(health_data: Dict[str, Any]):
        """Assert health response has required fields."""
        required_fields = ['status', 'timestamp', 'components']
        for field in required_fields:
            assert field in health_data, f"Health response missing required field: {field}"
    
    @staticmethod
    def assert_component_health_valid(component_data: Dict[str, Any]):
        """Assert component health data is valid."""
        required_fields = ['status', 'response_time_ms']
        for field in required_fields:
            assert field in component_data, f"Component health missing field: {field}"
        
        valid_statuses = ['healthy', 'degraded', 'unhealthy']
        assert component_data['status'] in valid_statuses, \
            f"Invalid health status: {component_data['status']}"


# === METRICS TEST UTILITIES ===

class MetricsAssertions:
    """Utilities for testing Prometheus metrics."""
    
    @staticmethod
    def assert_prometheus_format_valid(metrics_text: str):
        """Assert metrics text is valid Prometheus format."""
        assert len(metrics_text) > 0, "Metrics text is empty"
        assert "# HELP" in metrics_text, "Metrics missing HELP comments"
        assert "# TYPE" in metrics_text, "Metrics missing TYPE comments"
    
    @staticmethod
    def assert_adhd_metrics_present(metrics_text: str):
        """Assert ADHD-specific metrics are present."""
        adhd_metrics = [
            'mcp_adhd_server_cognitive_load',
            'mcp_adhd_server_tasks_completed_total',
            'mcp_adhd_server_pattern_matches_total',
            'mcp_adhd_server_nudges_sent_total'
        ]
        
        for metric in adhd_metrics:
            assert metric in metrics_text, f"Missing ADHD metric: {metric}"


@pytest.fixture
def health_assertions():
    """Provide health check assertion utilities."""
    return HealthCheckAssertions


@pytest.fixture
def metrics_assertions():
    """Provide metrics assertion utilities."""
    return MetricsAssertions


# === CONFIGURATION OVERRIDES ===

@pytest.fixture(autouse=True)
def configure_test_settings():
    """Configure settings for testing."""
    # Override settings for tests
    original_debug = settings.debug
    original_database_url = settings.database_url
    
    settings.debug = True
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    
    yield
    
    # Restore original settings
    settings.debug = original_debug
    settings.database_url = original_database_url


# === SESSION SCOPED FIXTURES ===

@pytest.fixture(scope="session")
def performance_thresholds():
    """Define performance thresholds for ADHD optimization."""
    return {
        'max_response_time_ms': 3000,
        'max_pattern_match_ms': 100,
        'max_cognitive_processing_ms': 1000,
        'max_database_query_ms': 500,
        'max_health_check_ms': 200,
        'min_cache_hit_rate': 0.8,
        'max_memory_usage_mb': 512,
        'max_cpu_usage_percent': 80.0
    }