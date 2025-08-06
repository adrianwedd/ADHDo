"""
Unit tests for health monitoring system.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from tests.utils import HealthCheckAssertions, PerformanceAssertions


@pytest.mark.unit
@pytest.mark.health
class TestHealthMonitor:
    """Test HealthMonitor functionality."""
    
    def test_health_monitor_initialization(self, health_monitor):
        """Test health monitor initialization."""
        assert health_monitor is not None
        assert hasattr(health_monitor, 'redis_client')
        assert hasattr(health_monitor, 'database_engine')
        assert hasattr(health_monitor, 'llm_client')
        assert health_monitor.start_time is not None
    
    async def test_basic_health_check(self, health_monitor):
        """Test basic health check functionality."""
        health_status = await health_monitor.get_health_status()
        
        assert "status" in health_status
        assert health_status["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in health_status
        assert "uptime_seconds" in health_status
        assert "version" in health_status
        
        HealthCheckAssertions.assert_healthy_response(health_status)
    
    async def test_detailed_health_check(self, health_monitor):
        """Test detailed health check with all components."""
        detailed_health = await health_monitor.get_detailed_health()
        
        assert "status" in detailed_health
        assert "components" in detailed_health
        assert "system_metrics" in detailed_health
        assert "uptime_seconds" in detailed_health
        
        # Check required components
        components = detailed_health["components"]
        required_components = ["database", "redis", "llm", "system", "application"]
        
        for component in required_components:
            assert component in components
            HealthCheckAssertions.assert_component_health(
                detailed_health, component
            )
    
    async def test_redis_health_check(self, health_monitor, mock_redis):
        """Test Redis health check."""
        # Mock successful Redis ping
        mock_redis.ping.return_value = True
        
        redis_health = await health_monitor.check_redis_health()
        
        assert redis_health["status"] == "healthy"
        assert "response_time_ms" in redis_health
        assert redis_health["response_time_ms"] >= 0
        assert "last_check" in redis_health
        
        # Test Redis failure
        mock_redis.ping.side_effect = Exception("Redis connection failed")
        
        redis_health_failed = await health_monitor.check_redis_health()
        
        assert redis_health_failed["status"] == "unhealthy"
        assert "error" in redis_health_failed
    
    async def test_database_health_check(self, health_monitor, test_db_session):
        """Test database health check."""
        database_health = await health_monitor.check_database_health()
        
        assert database_health["status"] == "healthy"
        assert "response_time_ms" in database_health
        assert database_health["response_time_ms"] >= 0
        assert "connection_pool" in database_health
    
    async def test_llm_health_check(self, health_monitor, mock_openai):
        """Test LLM health check."""
        # Mock successful LLM response
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "Health check response"
        mock_openai.return_value.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )
        
        llm_health = await health_monitor.check_llm_health()
        
        assert llm_health["status"] == "healthy"
        assert "response_time_ms" in llm_health
        assert "model" in llm_health
        
        # Test LLM failure
        mock_openai.return_value.chat.completions.create.side_effect = Exception(
            "LLM service unavailable"
        )
        
        llm_health_failed = await health_monitor.check_llm_health()
        assert llm_health_failed["status"] == "unhealthy"
        assert "error" in llm_health_failed
    
    async def test_system_health_check(self, health_monitor):
        """Test system resource health check."""
        system_health = await health_monitor.check_system_health()
        
        assert system_health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "cpu_percent" in system_health
        assert "memory_percent" in system_health
        assert "disk_usage_percent" in system_health
        assert "load_average" in system_health
        assert "process_count" in system_health
        
        # Validate metric ranges
        assert 0 <= system_health["cpu_percent"] <= 100
        assert 0 <= system_health["memory_percent"] <= 100
        assert 0 <= system_health["disk_usage_percent"] <= 100
        assert system_health["process_count"] > 0
    
    async def test_application_health_check(self, health_monitor):
        """Test application-specific health check."""
        app_health = await health_monitor.check_application_health()
        
        assert app_health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "response_time_ms" in app_health
        assert "active_connections" in app_health
        assert "memory_usage_mb" in app_health
    
    async def test_component_health_status_determination(self, health_monitor):
        """Test health status determination logic."""
        # Test healthy thresholds
        healthy_metrics = {
            "response_time_ms": 50,
            "cpu_percent": 30,
            "memory_percent": 40,
            "error_rate": 0.0
        }
        
        status = health_monitor.determine_component_status(healthy_metrics)
        assert status == "healthy"
        
        # Test degraded thresholds
        degraded_metrics = {
            "response_time_ms": 800,
            "cpu_percent": 75,
            "memory_percent": 60,
            "error_rate": 0.05
        }
        
        status = health_monitor.determine_component_status(degraded_metrics)
        assert status == "degraded"
        
        # Test unhealthy thresholds
        unhealthy_metrics = {
            "response_time_ms": 2000,
            "cpu_percent": 95,
            "memory_percent": 90,
            "error_rate": 0.2
        }
        
        status = health_monitor.determine_component_status(unhealthy_metrics)
        assert status == "unhealthy"
    
    async def test_overall_health_calculation(self, health_monitor):
        """Test overall health status calculation."""
        # All healthy components
        component_statuses = {
            "database": "healthy",
            "redis": "healthy",
            "llm": "healthy",
            "system": "healthy",
            "application": "healthy"
        }
        
        overall_status = health_monitor.calculate_overall_health(component_statuses)
        assert overall_status == "healthy"
        
        # One degraded component
        component_statuses["redis"] = "degraded"
        overall_status = health_monitor.calculate_overall_health(component_statuses)
        assert overall_status == "degraded"
        
        # One unhealthy component
        component_statuses["database"] = "unhealthy"
        overall_status = health_monitor.calculate_overall_health(component_statuses)
        assert overall_status == "unhealthy"
    
    async def test_health_check_timing(self, health_monitor):
        """Test health check performance timing."""
        import time
        
        # Time individual component checks
        components_to_test = [
            ("redis", health_monitor.check_redis_health),
            ("database", health_monitor.check_database_health),
            ("system", health_monitor.check_system_health),
            ("application", health_monitor.check_application_health)
        ]
        
        for component_name, check_function in components_to_test:
            start_time = time.time()
            health_result = await check_function()
            duration_ms = (time.time() - start_time) * 1000
            
            # Each component check should complete quickly
            PerformanceAssertions.assert_response_time(
                duration_ms, 500, f"{component_name} health check"
            )
            
            # Verify response time is recorded
            assert "response_time_ms" in health_result
            assert health_result["response_time_ms"] >= 0
    
    async def test_health_history_tracking(self, health_monitor):
        """Test health history tracking."""
        # Perform multiple health checks to build history
        for i in range(5):
            await health_monitor.get_health_status()
            await asyncio.sleep(0.1)  # Small delay between checks
        
        # Get health history
        history = await health_monitor.get_health_history("overall", hours=1)
        
        assert len(history) >= 5
        assert all("timestamp" in entry for entry in history)
        assert all("status" in entry for entry in history)
        assert all("response_time_ms" in entry for entry in history)
        
        # Check chronological ordering
        timestamps = [entry["timestamp"] for entry in history]
        assert timestamps == sorted(timestamps)
    
    async def test_component_specific_history(self, health_monitor):
        """Test component-specific health history."""
        components = ["database", "redis", "system"]
        
        for component in components:
            # Trigger component-specific health checks
            if component == "database":
                await health_monitor.check_database_health()
            elif component == "redis":
                await health_monitor.check_redis_health()
            elif component == "system":
                await health_monitor.check_system_health()
        
        # Get history for each component
        for component in components:
            history = await health_monitor.get_health_history(component, hours=1)
            
            assert isinstance(history, list)
            if history:  # May be empty if no checks were recorded
                assert all("timestamp" in entry for entry in history)
                assert all("status" in entry for entry in history)
    
    async def test_health_alerts_integration(self, health_monitor, alert_manager):
        """Test integration with alerting system."""
        # Mock an unhealthy component
        with patch.object(health_monitor, 'check_database_health') as mock_db_check:
            mock_db_check.return_value = {
                "status": "unhealthy",
                "response_time_ms": 5000,
                "error": "Database connection timeout",
                "last_check": datetime.utcnow().isoformat()
            }
            
            # Check if alerts are triggered for unhealthy components
            detailed_health = await health_monitor.get_detailed_health()
            
            assert detailed_health["components"]["database"]["status"] == "unhealthy"
            
            # Verify alert would be sent (depends on integration with alert_manager)
            # This would need to be tested with actual alert_manager integration
    
    async def test_health_check_caching(self, health_monitor):
        """Test health check result caching."""
        import time
        
        # First health check
        start_time = time.time()
        first_result = await health_monitor.get_health_status()
        first_duration = (time.time() - start_time) * 1000
        
        # Immediate second health check (should be faster due to caching)
        start_time = time.time()
        second_result = await health_monitor.get_health_status()
        second_duration = (time.time() - start_time) * 1000
        
        # Second check should be faster (cached)
        assert second_duration < first_duration or second_duration < 50  # Very fast if cached
        
        # Results should be similar (allowing for small timing differences)
        assert first_result["status"] == second_result["status"]
        assert abs(first_result["uptime_seconds"] - second_result["uptime_seconds"]) < 1
    
    async def test_health_check_error_handling(self, health_monitor):
        """Test error handling in health checks."""
        # Test with completely broken components
        with patch('psutil.cpu_percent', side_effect=Exception("psutil error")):
            system_health = await health_monitor.check_system_health()
            
            assert system_health["status"] == "unhealthy"
            assert "error" in system_health
        
        # Test with partially failing components
        with patch('psutil.virtual_memory', side_effect=Exception("memory error")):
            system_health = await health_monitor.check_system_health()
            
            # Should still return some health info even if some metrics fail
            assert "status" in system_health
            assert system_health["status"] in ["healthy", "degraded", "unhealthy"]
    
    async def test_uptime_calculation(self, health_monitor):
        """Test uptime calculation accuracy."""
        # Get initial uptime
        health_status = await health_monitor.get_health_status()
        initial_uptime = health_status["uptime_seconds"]
        
        assert initial_uptime >= 0
        
        # Wait a short time and check uptime again
        await asyncio.sleep(1)
        
        updated_health = await health_monitor.get_health_status()
        updated_uptime = updated_health["uptime_seconds"]
        
        # Uptime should have increased
        assert updated_uptime > initial_uptime
        assert updated_uptime - initial_uptime >= 0.9  # Allow for small timing variations


@pytest.mark.unit
@pytest.mark.health
class TestHealthMonitorIntegration:
    """Test health monitor integration with other components."""
    
    async def test_database_integration(self, health_monitor, db_service):
        """Test health monitor integration with database service."""
        # Record some database operations
        await db_service.record_system_health(
            component="test_component",
            status="healthy",
            response_time_ms=25.0,
            error_rate=0.0
        )
        
        # Health monitor should be able to access this data
        system_status = await health_monitor.get_system_status_from_db()
        
        assert "test_component" in system_status
        assert system_status["test_component"]["status"] == "healthy"
    
    async def test_metrics_integration(self, health_monitor, metrics_collector):
        """Test health monitor integration with metrics collection."""
        # Perform health check
        health_status = await health_monitor.get_health_status()
        
        # Verify metrics are updated
        metrics_data = metrics_collector.export_metrics()
        
        # Should contain health-related metrics
        assert "mcp_adhd_server_component_health" in metrics_data
        assert "mcp_adhd_server_uptime_seconds" in metrics_data
    
    async def test_real_world_scenario_simulation(self, health_monitor, mock_redis, mock_openai):
        """Test health monitoring in realistic failure scenarios."""
        # Scenario 1: Redis becomes slow but doesn't fail
        mock_redis.ping.return_value = True
        
        def slow_redis_operation(*args, **kwargs):
            import time
            time.sleep(0.5)  # Simulate slow response
            return True
        
        mock_redis.ping.side_effect = slow_redis_operation
        
        redis_health = await health_monitor.check_redis_health()
        assert redis_health["status"] in ["degraded", "unhealthy"]
        assert redis_health["response_time_ms"] > 400
        
        # Scenario 2: LLM service has intermittent failures
        call_count = 0
        def intermittent_llm_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Fail every third call
                raise Exception("LLM timeout")
            else:
                mock_completion = MagicMock()
                mock_completion.choices = [MagicMock()]
                mock_completion.choices[0].message.content = "OK"
                return mock_completion
        
        mock_openai.return_value.chat.completions.create = AsyncMock(
            side_effect=intermittent_llm_failure
        )
        
        # Multiple LLM health checks should show mixed results
        llm_results = []
        for _ in range(5):
            result = await health_monitor.check_llm_health()
            llm_results.append(result["status"])
        
        # Should have both successful and failed checks
        assert "healthy" in llm_results
        assert "unhealthy" in llm_results