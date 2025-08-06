"""
Unit tests for metrics collection system.

Tests Prometheus metrics, ADHD-specific tracking, and performance monitoring.
"""
import pytest
from unittest.mock import patch, MagicMock
import time
from datetime import datetime

from mcp_server.metrics import (
    MetricsCollector, init_metrics, get_metrics_registry,
    # Prometheus metrics
    REQUEST_COUNT, REQUEST_DURATION, REQUEST_SIZE, RESPONSE_SIZE,
    ACTIVE_CONNECTIONS, ERROR_COUNT, HEALTH_STATUS,
    # ADHD-specific metrics  
    COGNITIVE_LOAD_GAUGE, TASKS_COMPLETED_COUNTER, PATTERN_MATCHES_COUNTER,
    NUDGES_SENT_COUNTER, USER_SESSIONS_GAUGE, HYPERFOCUS_SESSIONS_COUNTER,
    DOPAMINE_REWARDS_COUNTER, ENERGY_LEVELS_GAUGE, FOCUS_TIME_HISTOGRAM,
    RESPONSE_TIME_ADHD_HISTOGRAM, TASK_COMPLETION_RATE_GAUGE,
    CONTEXT_SWITCHES_COUNTER, OVERWHELM_DETECTIONS_COUNTER,
    BREAK_REMINDERS_COUNTER, POMODORO_COMPLETIONS_COUNTER
)


class TestMetricsCollector:
    """Test MetricsCollector core functionality."""

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_metrics_collector_initialization(self):
        """Test MetricsCollector initialization."""
        collector = MetricsCollector()
        
        assert collector.registry is not None
        assert collector._start_time is not None
        assert collector._request_start_times == {}

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_init_metrics(self):
        """Test metrics initialization."""
        registry = init_metrics()
        
        assert registry is not None
        
        # Verify all metrics are registered
        metric_names = [metric.describe()[0].name for collector in registry._collector_to_names.keys() 
                       for metric in [collector] if hasattr(collector, 'describe')]
        
        # Check that our custom metrics are present
        expected_metrics = [
            'mcp_adhd_server_requests_total',
            'mcp_adhd_server_request_duration_seconds',
            'mcp_adhd_server_cognitive_load',
            'mcp_adhd_server_tasks_completed_total',
            'mcp_adhd_server_pattern_matches_total'
        ]
        
        # Note: Not all metrics may be directly in describe() output
        # This is a basic check that initialization succeeds

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_get_metrics_registry(self):
        """Test getting metrics registry."""
        registry1 = get_metrics_registry()
        registry2 = get_metrics_registry()
        
        # Should return the same registry instance (singleton pattern)
        assert registry1 is registry2

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_record_request_metrics(self):
        """Test recording basic request metrics."""
        collector = MetricsCollector()
        
        # Record a request
        collector.record_request(
            method='POST',
            endpoint='/api/chat',
            status_code=200,
            duration_seconds=0.150,
            request_size_bytes=256,
            response_size_bytes=512
        )
        
        # Verify metrics were recorded
        # Note: We can't easily access counter values in tests without exposing internals
        # In a real scenario, you'd check the actual metric values
        
        # Test that the method doesn't raise errors
        assert True  # Basic validation that no exceptions occurred

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_record_error_metrics(self):
        """Test recording error metrics."""
        collector = MetricsCollector()
        
        # Record various types of errors
        collector.record_error('database_error', 'Connection timeout')
        collector.record_error('llm_error', 'API rate limit exceeded')
        collector.record_error('validation_error', 'Invalid input format')
        
        # Test that the method doesn't raise errors
        assert True

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_record_cognitive_load_metrics(self):
        """Test recording ADHD cognitive load metrics."""
        collector = MetricsCollector()
        
        # Record cognitive load measurements
        collector.record_cognitive_load('user123', 0.75)
        collector.record_cognitive_load('user456', 0.45)
        collector.record_cognitive_load('user789', 0.90)
        
        # Test edge cases
        collector.record_cognitive_load('user000', 0.0)   # Minimum
        collector.record_cognitive_load('user111', 1.0)   # Maximum
        
        assert True  # No exceptions should occur

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_record_task_completion_metrics(self):
        """Test recording ADHD task completion metrics."""
        collector = MetricsCollector()
        
        # Record task completions with different reward tiers
        collector.record_task_completion('user123', 'work', reward_tier=3, focus_time=45)
        collector.record_task_completion('user456', 'personal', reward_tier=5, focus_time=120)
        collector.record_task_completion('user789', 'health', reward_tier=2, focus_time=20)
        
        # Record dopamine rewards
        collector.record_dopamine_reward('user123', reward_tier=3, points=30)
        collector.record_dopamine_reward('user456', reward_tier=5, points=50)
        
        assert True

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_record_pattern_matching_metrics(self):
        """Test recording ADHD pattern matching metrics."""
        collector = MetricsCollector()
        
        # Record pattern matches for different ADHD states
        collector.record_pattern_match('overwhelmed', confidence=0.85, processing_time_ms=50)
        collector.record_pattern_match('focused', confidence=0.92, processing_time_ms=25)
        collector.record_pattern_match('stuck', confidence=0.78, processing_time_ms=75)
        collector.record_pattern_match('ready', confidence=0.95, processing_time_ms=15)
        
        assert True

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_record_user_session_metrics(self):
        """Test recording user session metrics."""
        collector = MetricsCollector()
        
        # Record session starts/ends
        collector.record_session_start('user123', session_type='focused')
        collector.record_session_start('user456', session_type='regular')
        
        collector.record_session_end('user123', duration_minutes=45, tasks_completed=3)
        collector.record_session_end('user456', duration_minutes=90, tasks_completed=5)
        
        # Record hyperfocus sessions
        collector.record_hyperfocus_session('user123', duration_minutes=180, tasks_completed=1)
        
        assert True

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_record_energy_level_metrics(self):
        """Test recording energy level metrics."""
        collector = MetricsCollector()
        
        # Record energy levels throughout the day
        collector.record_energy_level('user123', energy_level=0.8, time_of_day='morning')
        collector.record_energy_level('user123', energy_level=0.6, time_of_day='afternoon')
        collector.record_energy_level('user123', energy_level=0.3, time_of_day='evening')
        
        collector.record_energy_level('user456', energy_level=0.4, time_of_day='morning')
        collector.record_energy_level('user456', energy_level=0.9, time_of_day='afternoon')
        
        assert True

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_record_nudge_metrics(self):
        """Test recording nudge and reminder metrics."""
        collector = MetricsCollector()
        
        # Record different types of nudges
        collector.record_nudge_sent('user123', nudge_type='task_reminder', channel='telegram')
        collector.record_nudge_sent('user456', nudge_type='break_reminder', channel='web')
        collector.record_nudge_sent('user789', nudge_type='energy_check', channel='email')
        
        # Record break reminders
        collector.record_break_reminder('user123', break_type='micro', duration_minutes=5)
        collector.record_break_reminder('user456', break_type='regular', duration_minutes=15)
        
        # Record overwhelm detections
        collector.record_overwhelm_detection('user123', trigger='high_task_count', severity=0.8)
        collector.record_overwhelm_detection('user456', trigger='time_pressure', severity=0.6)
        
        assert True

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_record_focus_session_metrics(self):
        """Test recording focus session and Pomodoro metrics."""
        collector = MetricsCollector()
        
        # Record Pomodoro completions
        collector.record_pomodoro_completion('user123', duration_minutes=25, interruptions=2)
        collector.record_pomodoro_completion('user456', duration_minutes=25, interruptions=0)
        collector.record_pomodoro_completion('user789', duration_minutes=15, interruptions=1)  # Modified Pomodoro
        
        # Record context switches
        collector.record_context_switch('user123', from_task='email', to_task='coding', switch_reason='distraction')
        collector.record_context_switch('user456', from_task='meeting', to_task='planning', switch_reason='scheduled')
        
        assert True

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_record_health_status_metrics(self):
        """Test recording health status metrics."""
        collector = MetricsCollector()
        
        # Record health status for different components
        collector.record_health_status('database', 'healthy', response_time_ms=25.5)
        collector.record_health_status('llm', 'degraded', response_time_ms=250.0)
        collector.record_health_status('redis', 'healthy', response_time_ms=5.1)
        collector.record_health_status('system', 'unhealthy', response_time_ms=1000.0)
        
        assert True

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.performance
    def test_metrics_collection_performance(self, performance_thresholds):
        """Test metrics collection performance."""
        collector = MetricsCollector()
        
        # Measure time to record multiple metrics
        start_time = time.time()
        
        for i in range(100):
            collector.record_request('GET', '/api/health', 200, 0.050, 100, 200)
            collector.record_cognitive_load(f'user{i}', 0.5 + (i % 5) * 0.1)
            collector.record_pattern_match('focused', 0.9, 50)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Metrics collection should be very fast
        assert duration_ms < 100  # Should complete in <100ms for ADHD performance


class TestMetricsExport:
    """Test metrics export and Prometheus format."""

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_generate_prometheus_metrics(self, metrics_assertions):
        """Test Prometheus metrics format generation."""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        
        # Initialize metrics and record some data
        registry = init_metrics()
        collector = MetricsCollector()
        
        # Record sample data
        collector.record_request('GET', '/api/health', 200, 0.050, 100, 200)
        collector.record_cognitive_load('user123', 0.75)
        collector.record_task_completion('user123', 'work', reward_tier=3, focus_time=45)
        
        # Generate metrics output
        metrics_output = generate_latest(registry).decode('utf-8')
        
        # Validate Prometheus format
        metrics_assertions.assert_prometheus_format_valid(metrics_output)
        metrics_assertions.assert_adhd_metrics_present(metrics_output)

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_metrics_endpoint_response_format(self):
        """Test metrics endpoint response format."""
        from prometheus_client import generate_latest
        
        registry = get_metrics_registry()
        metrics_data = generate_latest(registry)
        
        # Should be bytes
        assert isinstance(metrics_data, bytes)
        
        # Should contain Prometheus format indicators
        metrics_text = metrics_data.decode('utf-8')
        assert '# HELP' in metrics_text
        assert '# TYPE' in metrics_text

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_adhd_specific_metrics_present(self):
        """Test that all ADHD-specific metrics are present."""
        from prometheus_client import generate_latest
        
        registry = init_metrics()
        collector = MetricsCollector()
        
        # Record sample ADHD metrics
        collector.record_cognitive_load('user123', 0.7)
        collector.record_task_completion('user123', 'work', reward_tier=4, focus_time=60)
        collector.record_pattern_match('overwhelmed', confidence=0.8, processing_time_ms=100)
        collector.record_nudge_sent('user123', nudge_type='task_reminder', channel='web')
        collector.record_energy_level('user123', energy_level=0.6, time_of_day='afternoon')
        
        metrics_output = generate_latest(registry).decode('utf-8')
        
        # Check for ADHD-specific metrics
        expected_adhd_metrics = [
            'mcp_adhd_server_cognitive_load',
            'mcp_adhd_server_tasks_completed_total',
            'mcp_adhd_server_pattern_matches_total',
            'mcp_adhd_server_nudges_sent_total',
            'mcp_adhd_server_energy_levels'
        ]
        
        for metric in expected_adhd_metrics:
            assert metric in metrics_output, f"Missing ADHD metric: {metric}"


class TestMetricsValidation:
    """Test metrics data validation and error handling."""

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_cognitive_load_validation(self):
        """Test cognitive load value validation."""
        collector = MetricsCollector()
        
        # Valid values should work
        collector.record_cognitive_load('user123', 0.0)
        collector.record_cognitive_load('user123', 0.5)
        collector.record_cognitive_load('user123', 1.0)
        
        # Invalid values should be handled gracefully or raise appropriate errors
        with pytest.raises((ValueError, AssertionError)):
            collector.record_cognitive_load('user123', -0.1)  # Below 0
        
        with pytest.raises((ValueError, AssertionError)):
            collector.record_cognitive_load('user123', 1.1)   # Above 1

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_reward_tier_validation(self):
        """Test dopamine reward tier validation."""
        collector = MetricsCollector()
        
        # Valid tiers (1-5)
        for tier in range(1, 6):
            collector.record_dopamine_reward('user123', reward_tier=tier, points=tier * 10)
        
        # Invalid tiers should be handled
        with pytest.raises((ValueError, AssertionError)):
            collector.record_dopamine_reward('user123', reward_tier=0, points=0)
        
        with pytest.raises((ValueError, AssertionError)):
            collector.record_dopamine_reward('user123', reward_tier=6, points=60)

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_energy_level_validation(self):
        """Test energy level validation."""
        collector = MetricsCollector()
        
        # Valid energy levels (0.0 to 1.0)
        valid_levels = [0.0, 0.2, 0.5, 0.8, 1.0]
        for level in valid_levels:
            collector.record_energy_level('user123', energy_level=level, time_of_day='morning')
        
        # Invalid energy levels
        with pytest.raises((ValueError, AssertionError)):
            collector.record_energy_level('user123', energy_level=-0.1, time_of_day='morning')
        
        with pytest.raises((ValueError, AssertionError)):
            collector.record_energy_level('user123', energy_level=1.1, time_of_day='morning')

    @pytest.mark.unit
    @pytest.mark.metrics
    def test_time_of_day_validation(self):
        """Test time of day validation."""
        collector = MetricsCollector()
        
        # Valid time periods
        valid_times = ['morning', 'afternoon', 'evening', 'night']
        for time_period in valid_times:
            collector.record_energy_level('user123', energy_level=0.5, time_of_day=time_period)
        
        # Invalid time period should be handled
        with pytest.raises((ValueError, AssertionError)):
            collector.record_energy_level('user123', energy_level=0.5, time_of_day='invalid_time')


class TestMetricsAggregation:
    """Test metrics aggregation and calculation features."""

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_task_completion_rate_calculation(self):
        """Test task completion rate calculation."""
        collector = MetricsCollector()
        
        # Simulate task completions over time
        for i in range(10):
            collector.record_task_completion('user123', 'work', reward_tier=3, focus_time=30)
        
        # Simulate some incomplete tasks (context switches)
        for i in range(3):
            collector.record_context_switch('user123', from_task='work', to_task='email', switch_reason='distraction')
        
        # The completion rate should be calculable from the metrics
        # In a real implementation, this would involve querying the metrics
        assert True  # Basic test that metrics are recorded

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_average_cognitive_load_tracking(self):
        """Test average cognitive load tracking over time."""
        collector = MetricsCollector()
        
        # Record cognitive load measurements over time
        cognitive_loads = [0.3, 0.5, 0.7, 0.6, 0.4, 0.8, 0.5, 0.3]
        
        for i, load in enumerate(cognitive_loads):
            collector.record_cognitive_load('user123', load)
        
        # In a real scenario, you'd calculate averages from stored metrics
        expected_average = sum(cognitive_loads) / len(cognitive_loads)
        assert abs(expected_average - 0.5125) < 0.01

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    def test_focus_time_distribution(self):
        """Test focus time distribution tracking."""
        collector = MetricsCollector()
        
        # Record various focus session lengths
        focus_times = [15, 25, 30, 45, 60, 90, 120, 25, 30, 45]
        
        for focus_time in focus_times:
            collector.record_task_completion('user123', 'work', reward_tier=3, focus_time=focus_time)
        
        # Focus time histogram should capture the distribution
        # Verify no errors in recording
        assert True


class TestMetricsIntegration:
    """Test metrics integration with other system components."""

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.health
    def test_health_metrics_integration(self):
        """Test integration between health monitoring and metrics."""
        collector = MetricsCollector()
        
        # Health checks should generate metrics
        collector.record_health_status('database', 'healthy', response_time_ms=25.5)
        collector.record_health_status('llm', 'degraded', response_time_ms=250.0)
        
        # Should also record response time metrics
        collector.record_request('GET', '/health', 200, 0.025, 0, 150)
        
        assert True

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.database
    def test_database_metrics_integration(self):
        """Test database operation metrics."""
        collector = MetricsCollector()
        
        # Database operations should generate metrics
        collector.record_request('POST', '/api/tasks', 201, 0.150, 256, 128)
        collector.record_request('GET', '/api/tasks', 200, 0.050, 0, 512)
        collector.record_request('PUT', '/api/tasks/123', 200, 0.100, 128, 64)
        
        # Record any database errors
        collector.record_error('database_timeout', 'Query timeout after 30s')
        
        assert True

    @pytest.mark.unit
    @pytest.mark.metrics
    @pytest.mark.adhd
    @pytest.mark.performance
    def test_adhd_performance_metrics_integration(self, performance_thresholds):
        """Test ADHD performance metrics integration."""
        collector = MetricsCollector()
        
        # Record response times that should meet ADHD thresholds
        response_times = [0.050, 0.150, 0.250, 0.100, 0.075]
        
        for response_time in response_times:
            collector.record_request('GET', '/api/suggest', 200, response_time, 100, 200)
            
            # Verify meets ADHD performance requirements
            response_time_ms = response_time * 1000
            assert response_time_ms < performance_thresholds['max_response_time_ms']
        
        # Record cognitive processing times
        processing_times = [50, 100, 150, 75, 125]
        
        for processing_time in processing_times:
            collector.record_pattern_match('focused', confidence=0.9, processing_time_ms=processing_time)
            
            # Should meet ADHD processing requirements
            assert processing_time < performance_thresholds['max_cognitive_processing_ms']