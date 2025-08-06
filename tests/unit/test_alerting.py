"""
Unit tests for alerting system.

Tests alert management, notification delivery, and ADHD-specific alerting optimizations.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio

from mcp_server.alerting import (
    AlertManager, AlertRule, Alert, AlertChannel,
    AlertSeverity, AlertStatus, NotificationChannel,
    EmailChannel, TelegramChannel, WebhookChannel,
    create_default_alert_rules, evaluate_alert_condition
)


class TestAlertManager:
    """Test AlertManager core functionality."""

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_alert_manager_initialization(self, db_session):
        """Test AlertManager initialization."""
        alert_manager = AlertManager(db_session)
        
        assert alert_manager.db_session == db_session
        assert alert_manager._active_alerts == {}
        assert alert_manager._alert_rules == []
        assert alert_manager._channels == {}
        assert alert_manager._evaluation_interval == 60  # seconds

    @pytest.mark.unit
    @pytest.mark.alerts
    async def test_load_default_alert_rules(self, db_session):
        """Test loading default alert rules."""
        alert_manager = AlertManager(db_session)
        
        # Load default rules
        await alert_manager.load_alert_rules()
        
        assert len(alert_manager._alert_rules) > 0
        
        # Verify some expected rules are present
        rule_names = [rule.name for rule in alert_manager._alert_rules]
        assert 'high_response_time' in rule_names
        assert 'database_health_degraded' in rule_names
        assert 'high_cognitive_load' in rule_names

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_add_alert_rule(self, db_session):
        """Test adding custom alert rule."""
        alert_manager = AlertManager(db_session)
        
        # Create custom alert rule
        rule = AlertRule(
            name='test_memory_usage',
            description='Test alert for high memory usage',
            condition='memory_usage > 90',
            severity=AlertSeverity.WARNING,
            evaluation_interval=30,
            for_duration=300,  # 5 minutes
            labels={'component': 'system', 'type': 'resource'},
            annotations={'summary': 'High memory usage detected'}
        )
        
        alert_manager.add_alert_rule(rule)
        
        assert len(alert_manager._alert_rules) == 1
        assert alert_manager._alert_rules[0].name == 'test_memory_usage'

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_add_notification_channel(self, db_session):
        """Test adding notification channels."""
        alert_manager = AlertManager(db_session)
        
        # Add email channel
        email_channel = EmailChannel(
            name='ops_team',
            smtp_host='smtp.example.com',
            smtp_port=587,
            username='alerts@example.com',
            password='secret',
            recipients=['ops@example.com', 'admin@example.com']
        )
        
        alert_manager.add_notification_channel(email_channel)
        
        assert 'ops_team' in alert_manager._channels
        assert isinstance(alert_manager._channels['ops_team'], EmailChannel)

    @pytest.mark.unit
    @pytest.mark.alerts
    async def test_evaluate_alert_rules_no_alerts(self, db_session, mock_system_metrics):
        """Test alert rule evaluation when no alerts should fire."""
        alert_manager = AlertManager(db_session)
        
        # Create a rule that shouldn't trigger
        rule = AlertRule(
            name='high_cpu',
            description='CPU usage too high',
            condition='cpu_percent > 95',  # Very high threshold
            severity=AlertSeverity.WARNING,
            evaluation_interval=60,
            for_duration=300
        )
        
        alert_manager.add_alert_rule(rule)
        
        # Evaluate rules (CPU is mocked at 45.2%)
        await alert_manager.evaluate_alert_rules()
        
        # No alerts should be active
        assert len(alert_manager._active_alerts) == 0

    @pytest.mark.unit
    @pytest.mark.alerts
    async def test_evaluate_alert_rules_with_alert(self, db_session):
        """Test alert rule evaluation when alert should fire."""
        alert_manager = AlertManager(db_session)
        
        # Create a rule that should trigger
        rule = AlertRule(
            name='low_cpu',
            description='CPU usage is low (for testing)',
            condition='cpu_percent < 50',  # Should trigger with mocked 45.2%
            severity=AlertSeverity.INFO,
            evaluation_interval=60,
            for_duration=0  # Immediate firing
        )
        
        alert_manager.add_alert_rule(rule)
        
        with patch('mcp_server.alerting.get_system_metrics') as mock_metrics:
            mock_metrics.return_value = {'cpu_percent': 45.2}
            
            # Evaluate rules
            await alert_manager.evaluate_alert_rules()
            
            # Alert should be active
            assert len(alert_manager._active_alerts) == 1
            assert 'low_cpu' in alert_manager._active_alerts

    @pytest.mark.unit
    @pytest.mark.alerts
    async def test_fire_alert(self, db_session, mock_telegram):
        """Test firing an alert and sending notifications."""
        alert_manager = AlertManager(db_session)
        
        # Add notification channel
        telegram_channel = TelegramChannel(
            name='adhd_alerts',
            bot_token='test_token',
            chat_id=-1001234567890
        )
        alert_manager.add_notification_channel(telegram_channel)
        
        # Create alert rule with notification
        rule = AlertRule(
            name='test_alert',
            description='Test alert',
            condition='always_true',
            severity=AlertSeverity.CRITICAL,
            evaluation_interval=60,
            for_duration=0,
            notifications=['adhd_alerts']
        )
        
        # Fire alert
        alert = Alert(
            rule=rule,
            labels={'test': 'true'},
            annotations={'summary': 'Test alert fired'},
            value=1.0
        )
        
        await alert_manager._fire_alert(alert)
        
        # Alert should be active
        assert 'test_alert' in alert_manager._active_alerts
        assert alert_manager._active_alerts['test_alert'].status == AlertStatus.FIRING

    @pytest.mark.unit
    @pytest.mark.alerts
    async def test_resolve_alert(self, db_session):
        """Test resolving an active alert."""
        alert_manager = AlertManager(db_session)
        
        # Create and activate an alert
        rule = AlertRule(
            name='test_resolve',
            description='Test alert resolution',
            condition='test_condition',
            severity=AlertSeverity.WARNING,
            evaluation_interval=60,
            for_duration=0
        )
        
        alert = Alert(
            rule=rule,
            labels={'test': 'true'},
            annotations={'summary': 'Test alert'},
            value=1.0
        )
        
        # Activate alert
        alert_manager._active_alerts['test_resolve'] = alert
        alert.status = AlertStatus.FIRING
        
        # Resolve alert
        await alert_manager._resolve_alert('test_resolve')
        
        # Alert should be resolved
        assert alert_manager._active_alerts['test_resolve'].status == AlertStatus.RESOLVED

    @pytest.mark.unit
    @pytest.mark.alerts
    async def test_alert_suppression_during_for_duration(self, db_session):
        """Test alert suppression during for_duration period."""
        alert_manager = AlertManager(db_session)
        
        # Create rule with for_duration
        rule = AlertRule(
            name='test_suppression',
            description='Test alert suppression',
            condition='always_true',
            severity=AlertSeverity.WARNING,
            evaluation_interval=60,
            for_duration=300  # 5 minutes
        )
        
        alert_manager.add_alert_rule(rule)
        
        with patch('mcp_server.alerting.evaluate_alert_condition') as mock_eval:
            mock_eval.return_value = True
            
            # First evaluation - should not fire immediately
            await alert_manager.evaluate_alert_rules()
            
            # Alert should be in pending state, not firing
            assert len(alert_manager._active_alerts) == 1
            alert = alert_manager._active_alerts['test_suppression']
            assert alert.status == AlertStatus.PENDING

    @pytest.mark.unit
    @pytest.mark.alerts
    async def test_alert_deduplication(self, db_session):
        """Test alert deduplication for same rule."""
        alert_manager = AlertManager(db_session)
        
        rule = AlertRule(
            name='test_dedup',
            description='Test deduplication',
            condition='always_true',
            severity=AlertSeverity.WARNING,
            evaluation_interval=60,
            for_duration=0
        )
        
        alert_manager.add_alert_rule(rule)
        
        with patch('mcp_server.alerting.evaluate_alert_condition') as mock_eval:
            mock_eval.return_value = True
            
            # Multiple evaluations should not create duplicate alerts
            await alert_manager.evaluate_alert_rules()
            await alert_manager.evaluate_alert_rules()
            await alert_manager.evaluate_alert_rules()
            
            # Should only have one active alert
            assert len(alert_manager._active_alerts) == 1


class TestAlertRule:
    """Test AlertRule functionality."""

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_alert_rule_creation(self):
        """Test AlertRule creation and validation."""
        rule = AlertRule(
            name='test_rule',
            description='Test alert rule',
            condition='cpu_percent > 80',
            severity=AlertSeverity.WARNING,
            evaluation_interval=60,
            for_duration=300,
            labels={'team': 'platform', 'service': 'mcp-server'},
            annotations={'summary': 'High CPU usage', 'runbook': 'https://wiki.com/cpu'},
            notifications=['email', 'telegram']
        )
        
        assert rule.name == 'test_rule'
        assert rule.severity == AlertSeverity.WARNING
        assert rule.labels['team'] == 'platform'
        assert 'email' in rule.notifications

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_alert_rule_validation(self):
        """Test AlertRule validation."""
        # Valid rule should not raise
        AlertRule(
            name='valid_rule',
            description='Valid rule',
            condition='value > 0',
            severity=AlertSeverity.INFO,
            evaluation_interval=60,
            for_duration=0
        )
        
        # Invalid severity should raise
        with pytest.raises((ValueError, TypeError)):
            AlertRule(
                name='invalid_rule',
                description='Invalid rule',
                condition='value > 0',
                severity='invalid_severity',  # Should be AlertSeverity enum
                evaluation_interval=60,
                for_duration=0
            )

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_alert_rule_to_dict(self):
        """Test AlertRule serialization."""
        rule = AlertRule(
            name='serialization_test',
            description='Test serialization',
            condition='memory_percent > 90',
            severity=AlertSeverity.CRITICAL,
            evaluation_interval=30,
            for_duration=600,
            labels={'component': 'system'},
            annotations={'summary': 'High memory usage'}
        )
        
        rule_dict = rule.to_dict()
        
        assert rule_dict['name'] == 'serialization_test'
        assert rule_dict['severity'] == 'critical'
        assert rule_dict['labels']['component'] == 'system'
        assert rule_dict['annotations']['summary'] == 'High memory usage'


class TestAlert:
    """Test Alert functionality."""

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_alert_creation(self):
        """Test Alert creation."""
        rule = AlertRule(
            name='test_rule',
            description='Test rule',
            condition='test_condition',
            severity=AlertSeverity.WARNING,
            evaluation_interval=60,
            for_duration=0
        )
        
        alert = Alert(
            rule=rule,
            labels={'instance': 'server1', 'job': 'mcp-server'},
            annotations={'description': 'Test alert description'},
            value=85.5
        )
        
        assert alert.rule.name == 'test_rule'
        assert alert.labels['instance'] == 'server1'
        assert alert.value == 85.5
        assert alert.status == AlertStatus.PENDING  # Default status

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_alert_status_transitions(self):
        """Test Alert status transitions."""
        rule = AlertRule(
            name='status_test',
            description='Status test',
            condition='test',
            severity=AlertSeverity.INFO,
            evaluation_interval=60,
            for_duration=0
        )
        
        alert = Alert(
            rule=rule,
            labels={},
            annotations={},
            value=1.0
        )
        
        # Start as pending
        assert alert.status == AlertStatus.PENDING
        
        # Transition to firing
        alert.status = AlertStatus.FIRING
        assert alert.status == AlertStatus.FIRING
        
        # Transition to resolved
        alert.status = AlertStatus.RESOLVED
        assert alert.status == AlertStatus.RESOLVED

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_alert_to_dict(self):
        """Test Alert serialization."""
        rule = AlertRule(
            name='dict_test',
            description='Dictionary test',
            condition='test',
            severity=AlertSeverity.ERROR,
            evaluation_interval=60,
            for_duration=0
        )
        
        alert = Alert(
            rule=rule,
            labels={'environment': 'production'},
            annotations={'summary': 'Test alert'},
            value=100.0
        )
        alert.status = AlertStatus.FIRING
        
        alert_dict = alert.to_dict()
        
        assert alert_dict['rule']['name'] == 'dict_test'
        assert alert_dict['status'] == 'firing'
        assert alert_dict['value'] == 100.0
        assert alert_dict['labels']['environment'] == 'production'


class TestNotificationChannels:
    """Test notification channel implementations."""

    @pytest.mark.unit
    @pytest.mark.alerts
    async def test_email_channel_send(self):
        """Test EmailChannel send functionality."""
        channel = EmailChannel(
            name='test_email',
            smtp_host='smtp.example.com',
            smtp_port=587,
            username='test@example.com',
            password='secret',
            recipients=['admin@example.com']
        )
        
        rule = AlertRule(
            name='email_test',
            description='Email test',
            condition='test',
            severity=AlertSeverity.WARNING,
            evaluation_interval=60,
            for_duration=0
        )
        
        alert = Alert(
            rule=rule,
            labels={'service': 'mcp-server'},
            annotations={'summary': 'Test alert for email'},
            value=1.0
        )
        
        # Mock SMTP
        with patch('mcp_server.alerting.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            await channel.send(alert)
            
            # Verify SMTP was called
            mock_smtp.assert_called_once_with('smtp.example.com', 587)
            mock_server.send_message.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.alerts
    async def test_telegram_channel_send(self, mock_telegram):
        """Test TelegramChannel send functionality."""
        channel = TelegramChannel(
            name='test_telegram',
            bot_token='test_token_123',
            chat_id=-1001234567890
        )
        
        rule = AlertRule(
            name='telegram_test',
            description='Telegram test',
            condition='test',
            severity=AlertSeverity.CRITICAL,
            evaluation_interval=60,
            for_duration=0
        )
        
        alert = Alert(
            rule=rule,
            labels={'environment': 'production'},
            annotations={'summary': 'Critical alert for Telegram'},
            value=95.0
        )
        
        await channel.send(alert)
        
        # Mock telegram should have been called
        assert mock_telegram.post.called

    @pytest.mark.unit
    @pytest.mark.alerts
    async def test_webhook_channel_send(self):
        """Test WebhookChannel send functionality."""
        channel = WebhookChannel(
            name='test_webhook',
            url='https://hooks.slack.com/services/test',
            headers={'Authorization': 'Bearer token'},
            method='POST'
        )
        
        rule = AlertRule(
            name='webhook_test',
            description='Webhook test',
            condition='test',
            severity=AlertSeverity.ERROR,
            evaluation_interval=60,
            for_duration=0
        )
        
        alert = Alert(
            rule=rule,
            labels={'component': 'database'},
            annotations={'summary': 'Database alert for webhook'},
            value=50.0
        )
        
        with patch('mcp_server.alerting.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            await channel.send(alert)
            
            # Verify HTTP client was used
            mock_client.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_notification_channel_validation(self):
        """Test notification channel validation."""
        # Valid email channel
        EmailChannel(
            name='valid_email',
            smtp_host='smtp.example.com',
            smtp_port=587,
            username='test@example.com',
            password='secret',
            recipients=['admin@example.com']
        )
        
        # Invalid email channel (no recipients)
        with pytest.raises((ValueError, TypeError)):
            EmailChannel(
                name='invalid_email',
                smtp_host='smtp.example.com',
                smtp_port=587,
                username='test@example.com',
                password='secret',
                recipients=[]  # Should have at least one recipient
            )


class TestAlertConditions:
    """Test alert condition evaluation."""

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_evaluate_alert_condition_simple(self):
        """Test simple alert condition evaluation."""
        # Simple numeric conditions
        assert evaluate_alert_condition('cpu_percent > 80', {'cpu_percent': 85.5}) == True
        assert evaluate_alert_condition('cpu_percent > 80', {'cpu_percent': 75.0}) == False
        
        # Memory conditions
        assert evaluate_alert_condition('memory_percent < 90', {'memory_percent': 75.0}) == True
        assert evaluate_alert_condition('memory_percent < 90', {'memory_percent': 95.0}) == False

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_evaluate_alert_condition_complex(self):
        """Test complex alert condition evaluation."""
        metrics = {
            'cpu_percent': 85.0,
            'memory_percent': 70.0,
            'disk_percent': 90.0,
            'load_average': 2.5
        }
        
        # Multiple conditions
        condition = 'cpu_percent > 80 and memory_percent < 80'
        assert evaluate_alert_condition(condition, metrics) == True
        
        condition = 'cpu_percent > 90 or disk_percent > 85'
        assert evaluate_alert_condition(condition, metrics) == True
        
        condition = 'load_average > 3.0 and cpu_percent > 90'
        assert evaluate_alert_condition(condition, metrics) == False

    @pytest.mark.unit
    @pytest.mark.alerts
    @pytest.mark.adhd
    def test_evaluate_adhd_alert_conditions(self):
        """Test ADHD-specific alert conditions."""
        metrics = {
            'avg_response_time_ms': 3500,  # Above ADHD threshold
            'cognitive_load_avg': 0.85,   # High cognitive load
            'pattern_match_time_ms': 150,  # Slow pattern matching
            'task_completion_rate': 0.3    # Low completion rate
        }
        
        # ADHD response time alert
        condition = 'avg_response_time_ms > 3000'
        assert evaluate_alert_condition(condition, metrics) == True
        
        # High cognitive load alert
        condition = 'cognitive_load_avg > 0.8'
        assert evaluate_alert_condition(condition, metrics) == True
        
        # Slow pattern matching alert
        condition = 'pattern_match_time_ms > 100'
        assert evaluate_alert_condition(condition, metrics) == True
        
        # Low task completion alert
        condition = 'task_completion_rate < 0.5'
        assert evaluate_alert_condition(condition, metrics) == True

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_evaluate_alert_condition_error_handling(self):
        """Test alert condition evaluation error handling."""
        # Missing metric should return False
        result = evaluate_alert_condition('missing_metric > 50', {'cpu_percent': 80})
        assert result == False
        
        # Invalid condition syntax should return False
        result = evaluate_alert_condition('invalid syntax here', {'cpu_percent': 80})
        assert result == False
        
        # Division by zero should return False
        result = evaluate_alert_condition('cpu_percent / zero_value > 1', {'cpu_percent': 80, 'zero_value': 0})
        assert result == False


class TestDefaultAlertRules:
    """Test default alert rule creation."""

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_create_default_alert_rules(self):
        """Test creation of default alert rules."""
        rules = create_default_alert_rules()
        
        assert len(rules) > 0
        
        # Check for expected default rules
        rule_names = [rule.name for rule in rules]
        expected_rules = [
            'high_response_time',
            'database_health_degraded',
            'llm_service_unhealthy',
            'high_memory_usage',
            'high_cpu_usage',
            'disk_space_low',
            'high_error_rate',
            'high_cognitive_load',
            'slow_pattern_matching',
            'low_task_completion_rate',
            'excessive_context_switches',
            'overwhelm_threshold_exceeded'
        ]
        
        for expected_rule in expected_rules:
            assert expected_rule in rule_names, f"Missing default rule: {expected_rule}"

    @pytest.mark.unit
    @pytest.mark.alerts
    @pytest.mark.adhd
    def test_default_adhd_alert_rules(self):
        """Test ADHD-specific default alert rules."""
        rules = create_default_alert_rules()
        
        # Find ADHD-specific rules
        adhd_rules = [rule for rule in rules if 'adhd' in rule.labels.get('category', '')]
        
        assert len(adhd_rules) > 0
        
        # Check ADHD rule characteristics
        for rule in adhd_rules:
            # ADHD rules should have shorter evaluation intervals
            assert rule.evaluation_interval <= 60
            
            # Should have appropriate severity levels
            assert rule.severity in [AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]

    @pytest.mark.unit
    @pytest.mark.alerts
    def test_default_rule_conditions_validity(self):
        """Test that all default rule conditions are valid."""
        rules = create_default_alert_rules()
        
        # Sample metrics for testing conditions
        test_metrics = {
            'avg_response_time_ms': 1500,
            'database_health_status': 'healthy',
            'cpu_percent': 75.0,
            'memory_percent': 80.0,
            'disk_percent': 85.0,
            'error_rate_5min': 0.02,
            'cognitive_load_avg': 0.6,
            'pattern_match_time_avg_ms': 75,
            'task_completion_rate_24h': 0.7,
            'context_switches_per_hour': 15,
            'overwhelm_detections_1h': 2
        }
        
        # All conditions should be evaluable without errors
        for rule in rules:
            try:
                result = evaluate_alert_condition(rule.condition, test_metrics)
                assert isinstance(result, bool)
            except Exception as e:
                pytest.fail(f"Rule '{rule.name}' has invalid condition: {e}")


class TestAlertIntegration:
    """Test alert system integration with other components."""

    @pytest.mark.unit
    @pytest.mark.alerts
    @pytest.mark.health
    async def test_health_alert_integration(self, db_session):
        """Test integration between health monitoring and alerts."""
        alert_manager = AlertManager(db_session)
        
        # Add health-related alert rule
        health_rule = AlertRule(
            name='database_unhealthy',
            description='Database health check failing',
            condition='database_health_status == "unhealthy"',
            severity=AlertSeverity.CRITICAL,
            evaluation_interval=30,
            for_duration=60
        )
        
        alert_manager.add_alert_rule(health_rule)
        
        # Simulate unhealthy database
        with patch('mcp_server.alerting.get_health_metrics') as mock_health:
            mock_health.return_value = {'database_health_status': 'unhealthy'}
            
            await alert_manager.evaluate_alert_rules()
            
            assert len(alert_manager._active_alerts) == 1
            assert 'database_unhealthy' in alert_manager._active_alerts

    @pytest.mark.unit
    @pytest.mark.alerts
    @pytest.mark.metrics
    async def test_metrics_alert_integration(self, db_session):
        """Test integration between metrics collection and alerts."""
        alert_manager = AlertManager(db_session)
        
        # Add metrics-based alert rule
        metrics_rule = AlertRule(
            name='high_request_rate',
            description='Request rate is too high',
            condition='request_rate_per_min > 1000',
            severity=AlertSeverity.WARNING,
            evaluation_interval=60,
            for_duration=300
        )
        
        alert_manager.add_alert_rule(metrics_rule)
        
        # Simulate high request rate
        with patch('mcp_server.alerting.get_prometheus_metrics') as mock_metrics:
            mock_metrics.return_value = {'request_rate_per_min': 1200}
            
            await alert_manager.evaluate_alert_rules()
            
            assert len(alert_manager._active_alerts) == 1
            alert = alert_manager._active_alerts['high_request_rate']
            assert alert.status == AlertStatus.PENDING  # Due to for_duration

    @pytest.mark.unit
    @pytest.mark.alerts
    @pytest.mark.adhd
    @pytest.mark.performance
    async def test_adhd_performance_alert_integration(self, db_session, performance_thresholds):
        """Test ADHD performance alert integration."""
        alert_manager = AlertManager(db_session)
        
        # Add ADHD performance alert
        adhd_rule = AlertRule(
            name='adhd_response_time_breach',
            description='Response time exceeds ADHD-friendly threshold',
            condition=f'avg_response_time_ms > {performance_thresholds["max_response_time_ms"]}',
            severity=AlertSeverity.ERROR,
            evaluation_interval=30,
            for_duration=120,  # 2 minutes
            labels={'category': 'adhd', 'impact': 'user_experience'}
        )
        
        alert_manager.add_alert_rule(adhd_rule)
        
        # Simulate slow response times
        slow_response_time = performance_thresholds['max_response_time_ms'] + 500
        with patch('mcp_server.alerting.get_performance_metrics') as mock_perf:
            mock_perf.return_value = {'avg_response_time_ms': slow_response_time}
            
            await alert_manager.evaluate_alert_rules()
            
            assert len(alert_manager._active_alerts) == 1
            alert = alert_manager._active_alerts['adhd_response_time_breach']
            assert alert.labels['category'] == 'adhd'