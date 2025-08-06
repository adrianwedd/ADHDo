"""
Unit tests for health monitoring system.

Tests health checks, status tracking, and ADHD-specific optimizations.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

from mcp_server.health_monitor import (
    HealthMonitor, ComponentStatus, SystemHealth, 
    HealthCheckError, check_database_health, check_llm_health,
    check_redis_health, check_system_resources
)
from mcp_server.db_models import SystemHealth as SystemHealthModel


class TestHealthMonitor:
    """Test HealthMonitor core functionality."""

    @pytest.mark.unit
    @pytest.mark.health
    def test_health_monitor_initialization(self, db_session):
        """Test HealthMonitor initialization."""
        monitor = HealthMonitor(db_session)
        
        assert monitor.db_session == db_session
        assert monitor._health_cache == {}
        assert monitor._last_check_time is None
        assert monitor._check_interval == 30  # seconds
        assert len(monitor._components) == 4  # database, llm, redis, system

    @pytest.mark.unit
    @pytest.mark.health
    async def test_perform_health_check_all_healthy(self, db_session, mock_system_metrics):
        """Test health check when all components are healthy."""
        monitor = HealthMonitor(db_session)
        
        with patch('mcp_server.health_monitor.check_database_health') as mock_db, \
             patch('mcp_server.health_monitor.check_llm_health') as mock_llm, \
             patch('mcp_server.health_monitor.check_redis_health') as mock_redis, \
             patch('mcp_server.health_monitor.check_system_resources') as mock_system:
            
            # Mock all health checks as healthy
            mock_db.return_value = ComponentStatus(
                name='database', status='healthy', response_time_ms=25.5,
                details={'queries_executed': 100, 'connections': 5}
            )
            mock_llm.return_value = ComponentStatus(
                name='llm', status='healthy', response_time_ms=150.2,
                details={'model': 'gpt-4', 'tokens_used': 1500}
            )
            mock_redis.return_value = ComponentStatus(
                name='redis', status='healthy', response_time_ms=5.1,
                details={'memory_usage': '45MB', 'connections': 3}
            )
            mock_system.return_value = ComponentStatus(
                name='system', status='healthy', response_time_ms=10.0,
                details={'cpu_percent': 45.2, 'memory_percent': 62.1}
            )
            
            health = await monitor.perform_health_check()
            
            assert health.overall_status == 'healthy'
            assert len(health.components) == 4
            assert all(comp.status == 'healthy' for comp in health.components.values())
            assert health.response_time_ms > 0
            assert 'database' in health.components
            assert 'llm' in health.components
            assert 'redis' in health.components
            assert 'system' in health.components

    @pytest.mark.unit
    @pytest.mark.health
    async def test_perform_health_check_with_degraded_component(self, db_session):
        """Test health check with one degraded component."""
        monitor = HealthMonitor(db_session)
        
        with patch('mcp_server.health_monitor.check_database_health') as mock_db, \
             patch('mcp_server.health_monitor.check_llm_health') as mock_llm, \
             patch('mcp_server.health_monitor.check_redis_health') as mock_redis, \
             patch('mcp_server.health_monitor.check_system_resources') as mock_system:
            
            # Mock database as degraded
            mock_db.return_value = ComponentStatus(
                name='database', status='degraded', response_time_ms=250.5,
                details={'queries_executed': 50, 'slow_queries': 5}
            )
            mock_llm.return_value = ComponentStatus(
                name='llm', status='healthy', response_time_ms=150.2
            )
            mock_redis.return_value = ComponentStatus(
                name='redis', status='healthy', response_time_ms=5.1
            )
            mock_system.return_value = ComponentStatus(
                name='system', status='healthy', response_time_ms=10.0
            )
            
            health = await monitor.perform_health_check()
            
            assert health.overall_status == 'degraded'
            assert health.components['database'].status == 'degraded'
            assert health.components['llm'].status == 'healthy'

    @pytest.mark.unit
    @pytest.mark.health
    async def test_perform_health_check_with_unhealthy_component(self, db_session):
        """Test health check with one unhealthy component."""
        monitor = HealthMonitor(db_session)
        
        with patch('mcp_server.health_monitor.check_database_health') as mock_db, \
             patch('mcp_server.health_monitor.check_llm_health') as mock_llm, \
             patch('mcp_server.health_monitor.check_redis_health') as mock_redis, \
             patch('mcp_server.health_monitor.check_system_resources') as mock_system:
            
            # Mock LLM as unhealthy
            mock_db.return_value = ComponentStatus(
                name='database', status='healthy', response_time_ms=25.5
            )
            mock_llm.return_value = ComponentStatus(
                name='llm', status='unhealthy', response_time_ms=5000.0,
                error='OpenAI API timeout', details={'error_count': 5}
            )
            mock_redis.return_value = ComponentStatus(
                name='redis', status='healthy', response_time_ms=5.1
            )
            mock_system.return_value = ComponentStatus(
                name='system', status='healthy', response_time_ms=10.0
            )
            
            health = await monitor.perform_health_check()
            
            assert health.overall_status == 'unhealthy'
            assert health.components['llm'].status == 'unhealthy'
            assert health.components['llm'].error == 'OpenAI API timeout'

    @pytest.mark.unit
    @pytest.mark.health
    async def test_health_caching(self, db_session):
        """Test health check result caching."""
        monitor = HealthMonitor(db_session)
        monitor._check_interval = 30  # 30 seconds
        
        with patch('mcp_server.health_monitor.check_database_health') as mock_db, \
             patch('mcp_server.health_monitor.check_llm_health') as mock_llm, \
             patch('mcp_server.health_monitor.check_redis_health') as mock_redis, \
             patch('mcp_server.health_monitor.check_system_resources') as mock_system:
            
            # Setup mocks
            mock_db.return_value = ComponentStatus('database', 'healthy', 25.5)
            mock_llm.return_value = ComponentStatus('llm', 'healthy', 150.2)
            mock_redis.return_value = ComponentStatus('redis', 'healthy', 5.1)
            mock_system.return_value = ComponentStatus('system', 'healthy', 10.0)
            
            # First call should perform actual health check
            health1 = await monitor.get_health()
            assert mock_db.called
            
            # Second call within cache interval should use cached result
            mock_db.reset_mock()
            health2 = await monitor.get_health()
            assert not mock_db.called
            assert health1.overall_status == health2.overall_status

    @pytest.mark.unit
    @pytest.mark.health
    async def test_cache_expiration(self, db_session):
        """Test health check cache expiration."""
        monitor = HealthMonitor(db_session)
        monitor._check_interval = 0.1  # 0.1 seconds for fast test
        
        with patch('mcp_server.health_monitor.check_database_health') as mock_db, \
             patch('mcp_server.health_monitor.check_llm_health') as mock_llm, \
             patch('mcp_server.health_monitor.check_redis_health') as mock_redis, \
             patch('mcp_server.health_monitor.check_system_resources') as mock_system:
            
            # Setup mocks
            mock_db.return_value = ComponentStatus('database', 'healthy', 25.5)
            mock_llm.return_value = ComponentStatus('llm', 'healthy', 150.2)
            mock_redis.return_value = ComponentStatus('redis', 'healthy', 5.1)
            mock_system.return_value = ComponentStatus('system', 'healthy', 10.0)
            
            # First call
            await monitor.get_health()
            assert mock_db.called
            
            # Wait for cache to expire
            import asyncio
            await asyncio.sleep(0.2)
            
            # Second call should perform new health check
            mock_db.reset_mock()
            await monitor.get_health()
            assert mock_db.called

    @pytest.mark.unit
    @pytest.mark.health
    async def test_record_health_metrics(self, db_session):
        """Test health metrics recording to database."""
        monitor = HealthMonitor(db_session)
        
        with patch('mcp_server.health_monitor.check_database_health') as mock_db, \
             patch('mcp_server.health_monitor.check_llm_health') as mock_llm, \
             patch('mcp_server.health_monitor.check_redis_health') as mock_redis, \
             patch('mcp_server.health_monitor.check_system_resources') as mock_system:
            
            # Setup mocks
            mock_db.return_value = ComponentStatus(
                'database', 'healthy', 25.5, 
                details={'queries': 100, 'connections': 5}
            )
            mock_llm.return_value = ComponentStatus('llm', 'degraded', 250.2)
            mock_redis.return_value = ComponentStatus('redis', 'healthy', 5.1)
            mock_system.return_value = ComponentStatus('system', 'healthy', 10.0)
            
            # Perform health check (should record to database)
            await monitor.get_health()
            
            # Check that health records were created
            from sqlalchemy import select
            result = await db_session.execute(
                select(SystemHealthModel).where(SystemHealthModel.component == 'database')
            )
            health_record = result.scalar_one_or_none()
            
            assert health_record is not None
            assert health_record.status == 'healthy'
            assert health_record.response_time_ms == 25.5
            assert health_record.details['queries'] == 100

    @pytest.mark.unit
    @pytest.mark.health 
    @pytest.mark.performance
    async def test_health_check_performance(self, db_session, performance_thresholds):
        """Test health check meets performance requirements."""
        monitor = HealthMonitor(db_session)
        
        import time
        start_time = time.time()
        await monitor.get_health()
        duration_ms = (time.time() - start_time) * 1000
        
        # Health check should be fast for ADHD users
        assert duration_ms < performance_thresholds['max_health_check_ms']


class TestComponentHealthChecks:
    """Test individual component health check functions."""

    @pytest.mark.unit
    @pytest.mark.health
    @pytest.mark.database
    async def test_check_database_health_success(self, db_session):
        """Test successful database health check."""
        status = await check_database_health(db_session)
        
        assert status.name == 'database'
        assert status.status == 'healthy'
        assert status.response_time_ms > 0
        assert status.response_time_ms < 100  # Should be very fast
        assert 'connection_pool' in status.details

    @pytest.mark.unit
    @pytest.mark.health
    @pytest.mark.database
    async def test_check_database_health_failure(self):
        """Test database health check failure."""
        # Mock a failing database session
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Connection failed")
        
        status = await check_database_health(mock_session)
        
        assert status.name == 'database'
        assert status.status == 'unhealthy'
        assert status.error == "Connection failed"

    @pytest.mark.unit
    @pytest.mark.health
    @pytest.mark.database
    async def test_check_database_health_slow_response(self):
        """Test database health check with slow response."""
        mock_session = AsyncMock()
        
        # Mock slow database response
        async def slow_execute(*args):
            import asyncio
            await asyncio.sleep(0.3)  # 300ms delay
            return MagicMock()
        
        mock_session.execute = slow_execute
        
        status = await check_database_health(mock_session)
        
        assert status.name == 'database'
        assert status.status == 'degraded'  # Slow but working
        assert status.response_time_ms >= 300

    @pytest.mark.unit
    @pytest.mark.health
    @pytest.mark.llm
    async def test_check_llm_health_success(self, mock_openai):
        """Test successful LLM health check."""
        status = await check_llm_health()
        
        assert status.name == 'llm'
        assert status.status == 'healthy'
        assert status.response_time_ms > 0
        assert 'model' in status.details

    @pytest.mark.unit
    @pytest.mark.health
    @pytest.mark.llm
    async def test_check_llm_health_failure(self):
        """Test LLM health check failure."""
        with patch('mcp_server.llm_client.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = Exception("API error")
            mock_openai.return_value = mock_client
            
            status = await check_llm_health()
            
            assert status.name == 'llm'
            assert status.status == 'unhealthy'
            assert status.error == "API error"

    @pytest.mark.unit
    @pytest.mark.health
    @pytest.mark.redis
    async def test_check_redis_health_success(self, mock_redis):
        """Test successful Redis health check."""
        status = await check_redis_health()
        
        assert status.name == 'redis'
        assert status.status == 'healthy'
        assert status.response_time_ms > 0

    @pytest.mark.unit
    @pytest.mark.health
    @pytest.mark.redis
    async def test_check_redis_health_failure(self):
        """Test Redis health check failure."""
        with patch('mcp_server.health_monitor.trace_memory') as mock_redis:
            mock_redis.redis.ping.side_effect = Exception("Redis connection failed")
            
            status = await check_redis_health()
            
            assert status.name == 'redis'
            assert status.status == 'unhealthy'
            assert "Redis connection failed" in status.error

    @pytest.mark.unit
    @pytest.mark.health
    async def test_check_system_resources_healthy(self, mock_system_metrics):
        """Test system resources health check when healthy."""
        status = await check_system_resources()
        
        assert status.name == 'system'
        assert status.status == 'healthy'
        assert status.details['cpu_percent'] == 45.2
        assert status.details['memory_percent'] == 62.1
        assert status.details['disk_percent'] == 78.5

    @pytest.mark.unit
    @pytest.mark.health
    async def test_check_system_resources_high_cpu(self):
        """Test system resources health check with high CPU usage."""
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_cpu.return_value = 92.5  # High CPU
            mock_memory.return_value = MagicMock()
            mock_memory.return_value.percent = 45.0
            mock_disk.return_value = MagicMock()
            mock_disk.return_value.percent = 60.0
            
            status = await check_system_resources()
            
            assert status.name == 'system'
            assert status.status == 'degraded'  # High CPU causes degradation
            assert status.details['cpu_percent'] == 92.5

    @pytest.mark.unit
    @pytest.mark.health
    async def test_check_system_resources_high_memory(self):
        """Test system resources health check with high memory usage."""
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_cpu.return_value = 45.0
            mock_memory.return_value = MagicMock()
            mock_memory.return_value.percent = 95.5  # High memory
            mock_disk.return_value = MagicMock()
            mock_disk.return_value.percent = 60.0
            
            status = await check_system_resources()
            
            assert status.name == 'system'
            assert status.status == 'unhealthy'  # Very high memory causes unhealthy
            assert status.details['memory_percent'] == 95.5


class TestSystemHealth:
    """Test SystemHealth data class."""

    @pytest.mark.unit
    @pytest.mark.health
    def test_system_health_creation(self):
        """Test SystemHealth object creation."""
        components = {
            'database': ComponentStatus('database', 'healthy', 25.5),
            'llm': ComponentStatus('llm', 'degraded', 250.0)
        }
        
        health = SystemHealth(
            overall_status='degraded',
            components=components,
            timestamp=datetime.utcnow(),
            response_time_ms=150.0
        )
        
        assert health.overall_status == 'degraded'
        assert len(health.components) == 2
        assert health.components['database'].status == 'healthy'
        assert health.components['llm'].status == 'degraded'
        assert health.response_time_ms == 150.0

    @pytest.mark.unit
    @pytest.mark.health
    def test_system_health_to_dict(self):
        """Test SystemHealth serialization to dictionary."""
        components = {
            'database': ComponentStatus(
                'database', 'healthy', 25.5,
                details={'connections': 5}
            )
        }
        
        health = SystemHealth(
            overall_status='healthy',
            components=components,
            timestamp=datetime.utcnow(),
            response_time_ms=50.0
        )
        
        health_dict = health.to_dict()
        
        assert health_dict['overall_status'] == 'healthy'
        assert health_dict['response_time_ms'] == 50.0
        assert 'components' in health_dict
        assert health_dict['components']['database']['status'] == 'healthy'
        assert health_dict['components']['database']['details']['connections'] == 5

    @pytest.mark.unit
    @pytest.mark.health
    def test_determine_overall_status_all_healthy(self):
        """Test overall status determination with all healthy components."""
        components = {
            'database': ComponentStatus('database', 'healthy', 25.5),
            'llm': ComponentStatus('llm', 'healthy', 150.0),
            'redis': ComponentStatus('redis', 'healthy', 5.0)
        }
        
        health = SystemHealth(
            overall_status='',  # Will be determined
            components=components,
            timestamp=datetime.utcnow(),
            response_time_ms=100.0
        )
        
        status = health._determine_overall_status()
        assert status == 'healthy'

    @pytest.mark.unit
    @pytest.mark.health
    def test_determine_overall_status_with_degraded(self):
        """Test overall status determination with degraded components."""
        components = {
            'database': ComponentStatus('database', 'healthy', 25.5),
            'llm': ComponentStatus('llm', 'degraded', 300.0),
            'redis': ComponentStatus('redis', 'healthy', 5.0)
        }
        
        health = SystemHealth(
            overall_status='',
            components=components,
            timestamp=datetime.utcnow(),
            response_time_ms=100.0
        )
        
        status = health._determine_overall_status()
        assert status == 'degraded'

    @pytest.mark.unit
    @pytest.mark.health
    def test_determine_overall_status_with_unhealthy(self):
        """Test overall status determination with unhealthy components."""
        components = {
            'database': ComponentStatus('database', 'healthy', 25.5),
            'llm': ComponentStatus('llm', 'unhealthy', 5000.0, error='Timeout'),
            'redis': ComponentStatus('redis', 'degraded', 150.0)
        }
        
        health = SystemHealth(
            overall_status='',
            components=components,
            timestamp=datetime.utcnow(),
            response_time_ms=200.0
        )
        
        status = health._determine_overall_status()
        assert status == 'unhealthy'


class TestComponentStatus:
    """Test ComponentStatus data class."""

    @pytest.mark.unit
    @pytest.mark.health
    def test_component_status_creation_basic(self):
        """Test basic ComponentStatus creation."""
        status = ComponentStatus(
            name='database',
            status='healthy',
            response_time_ms=25.5
        )
        
        assert status.name == 'database'
        assert status.status == 'healthy'
        assert status.response_time_ms == 25.5
        assert status.error is None
        assert status.details == {}

    @pytest.mark.unit
    @pytest.mark.health
    def test_component_status_creation_with_error(self):
        """Test ComponentStatus creation with error."""
        status = ComponentStatus(
            name='llm',
            status='unhealthy',
            response_time_ms=5000.0,
            error='API timeout after 5 seconds',
            details={'retry_count': 3, 'last_success': '2024-01-01T00:00:00Z'}
        )
        
        assert status.name == 'llm'
        assert status.status == 'unhealthy'
        assert status.error == 'API timeout after 5 seconds'
        assert status.details['retry_count'] == 3

    @pytest.mark.unit
    @pytest.mark.health
    def test_component_status_to_dict(self):
        """Test ComponentStatus serialization to dictionary."""
        status = ComponentStatus(
            name='redis',
            status='degraded',
            response_time_ms=200.0,
            details={'memory_usage': '500MB', 'connection_pool': 10}
        )
        
        status_dict = status.to_dict()
        
        assert status_dict['name'] == 'redis'
        assert status_dict['status'] == 'degraded'
        assert status_dict['response_time_ms'] == 200.0
        assert status_dict['details']['memory_usage'] == '500MB'
        assert status_dict['error'] is None


class TestHealthCheckError:
    """Test HealthCheckError exception."""

    @pytest.mark.unit
    @pytest.mark.health
    def test_health_check_error_creation(self):
        """Test HealthCheckError creation."""
        error = HealthCheckError(
            component='database',
            message='Connection timeout',
            details={'timeout_seconds': 30, 'retry_attempts': 3}
        )
        
        assert error.component == 'database'
        assert error.message == 'Connection timeout'
        assert error.details['timeout_seconds'] == 30
        assert str(error) == 'Health check failed for database: Connection timeout'

    @pytest.mark.unit
    @pytest.mark.health
    def test_health_check_error_without_details(self):
        """Test HealthCheckError creation without details."""
        error = HealthCheckError(
            component='llm',
            message='API key invalid'
        )
        
        assert error.component == 'llm'
        assert error.message == 'API key invalid'
        assert error.details == {}


class TestADHDHealthOptimizations:
    """Test ADHD-specific health monitoring optimizations."""

    @pytest.mark.unit
    @pytest.mark.health
    @pytest.mark.adhd
    async def test_health_check_cognitive_load_impact(self, db_session):
        """Test health check has minimal cognitive load impact."""
        monitor = HealthMonitor(db_session)
        
        # Health check should not add significant cognitive load
        health = await monitor.get_health()
        
        # Fast response time is critical for ADHD users
        assert health.response_time_ms < 500  # <0.5s for health check
        
        # Should provide clear, simple status information
        assert health.overall_status in ['healthy', 'degraded', 'unhealthy']
        
        # Should include essential information without overwhelming detail
        assert len(health.components) <= 5  # Limited number of components

    @pytest.mark.unit
    @pytest.mark.health
    @pytest.mark.adhd
    async def test_health_status_adhd_friendly_format(self, db_session):
        """Test health status format is ADHD-friendly."""
        monitor = HealthMonitor(db_session)
        health = await monitor.get_health()
        
        health_dict = health.to_dict()
        
        # Should have clear, simple status indicators
        assert health_dict['overall_status'] in ['healthy', 'degraded', 'unhealthy']
        
        # Should include response time for performance awareness
        assert 'response_time_ms' in health_dict
        
        # Component details should be concise
        for component_name, component in health_dict['components'].items():
            assert 'status' in component
            assert 'response_time_ms' in component
            # Details shouldn't be overwhelming
            if 'details' in component:
                assert len(component['details']) <= 5

    @pytest.mark.unit
    @pytest.mark.health
    @pytest.mark.adhd
    @pytest.mark.performance
    async def test_health_monitoring_performance_under_load(self, db_session, performance_thresholds):
        """Test health monitoring performance under load."""
        monitor = HealthMonitor(db_session)
        
        import asyncio
        import time
        
        # Simulate concurrent health checks
        async def timed_health_check():
            start = time.time()
            await monitor.get_health()
            return (time.time() - start) * 1000
        
        # Run 5 concurrent health checks
        tasks = [timed_health_check() for _ in range(5)]
        response_times = await asyncio.gather(*tasks)
        
        # All health checks should meet ADHD performance requirements
        for response_time in response_times:
            assert response_time < performance_thresholds['max_health_check_ms']
        
        # Average response time should be reasonable
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < performance_thresholds['max_health_check_ms'] / 2