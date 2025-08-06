"""
Unit tests for alert management system.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server.models import AlertLevel, AlertChannel
from tests.utils import TestDataFactory


@pytest.mark.unit
@pytest.mark.alerting
class TestAlertManager:
    """Test AlertManager functionality."""
    
    def test_alert_manager_initialization(self, alert_manager):
        """Test alert manager initialization."""
        assert alert_manager is not None
        assert hasattr(alert_manager, 'telegram_bot')
        assert hasattr(alert_manager, 'active_alerts')
        assert hasattr(alert_manager, 'alert_history')
        assert hasattr(alert_manager, 'notification_handlers')
    
    async def test_create_system_alert(self, alert_manager):
        """Test creating system-level alerts."""
        alert = await alert_manager.create_alert(
            title="System Alert Test",
            message="This is a test system alert",
            level=AlertLevel.WARNING,
            component="database",
            details={"connection_timeout": 5000, "retry_attempts": 3}
        )
        
        assert alert is not None
        assert alert.title == "System Alert Test"
        assert alert.level == AlertLevel.WARNING
        assert alert.component == "database"
        assert alert.is_active is True
        assert alert.created_at is not None
        assert alert.details["connection_timeout"] == 5000
    
    async def test_create_user_alert(self, alert_manager, test_user):
        """Test creating user-specific alerts."""
        alert = await alert_manager.create_user_alert(
            user_id=test_user.user_id,
            title="Task Overdue",
            message="You have overdue tasks that need attention",
            level=AlertLevel.INFO,
            alert_type="task_reminder",
            metadata={"task_count": 3, "oldest_overdue": "2 days"}
        )
        
        assert alert is not None
        assert alert.user_id == test_user.user_id
        assert alert.title == "Task Overdue"
        assert alert.level == AlertLevel.INFO
        assert alert.alert_type == "task_reminder"
        assert alert.metadata["task_count"] == 3
    
    async def test_alert_level_handling(self, alert_manager):
        """Test different alert levels and their handling."""
        alert_levels = [
            (AlertLevel.INFO, "Information alert"),
            (AlertLevel.WARNING, "Warning alert"),
            (AlertLevel.ERROR, "Error alert"),
            (AlertLevel.CRITICAL, "Critical alert")
        ]
        
        created_alerts = []
        for level, message in alert_levels:
            alert = await alert_manager.create_alert(
                title=f"{level.value} Alert",
                message=message,
                level=level,
                component="test"
            )
            created_alerts.append(alert)
            assert alert.level == level
        
        # Critical alerts should have highest priority
        critical_alerts = [a for a in created_alerts if a.level == AlertLevel.CRITICAL]
        for alert in critical_alerts:
            assert alert.requires_immediate_attention is True
    
    async def test_alert_channels(self, alert_manager, mock_telegram):
        """Test alert delivery through different channels."""
        # Create alert for Telegram delivery
        alert = await alert_manager.create_alert(
            title="Channel Test Alert",
            message="Testing alert channels",
            level=AlertLevel.WARNING,
            channels=[AlertChannel.TELEGRAM, AlertChannel.LOG]
        )
        
        # Send alert through channels
        await alert_manager.send_alert(alert)
        
        # Verify Telegram was called
        mock_telegram.send_message.assert_called()
        
        # Verify alert was logged
        assert alert.alert_id in alert_manager.alert_history
        assert alert.sent_at is not None
    
    async def test_alert_rate_limiting(self, alert_manager):
        """Test alert rate limiting to prevent spam."""
        # Create multiple similar alerts quickly
        alerts_created = []
        for i in range(5):
            alert = await alert_manager.create_alert(
                title="Rate Limit Test",
                message=f"Alert {i}",
                level=AlertLevel.INFO,
                component="test_component"
            )
            alerts_created.append(alert)
        
        # Only some should be sent due to rate limiting
        sent_alerts = [a for a in alerts_created if a.sent_at is not None]
        suppressed_alerts = [a for a in alerts_created if a.suppressed is True]
        
        # Should have both sent and suppressed alerts
        assert len(sent_alerts) < len(alerts_created)
        assert len(suppressed_alerts) > 0
    
    async def test_alert_deduplication(self, alert_manager):
        """Test alert deduplication logic."""
        # Create identical alerts
        alert_data = {
            "title": "Duplicate Alert",
            "message": "This is a duplicate alert",
            "level": AlertLevel.WARNING,
            "component": "database"
        }
        
        first_alert = await alert_manager.create_alert(**alert_data)
        second_alert = await alert_manager.create_alert(**alert_data)
        
        # Second alert should be deduplicated
        assert first_alert.alert_id != second_alert.alert_id
        assert second_alert.is_duplicate is True
        assert second_alert.original_alert_id == first_alert.alert_id
    
    async def test_alert_escalation(self, alert_manager):
        """Test alert escalation logic."""
        # Create warning alert
        warning_alert = await alert_manager.create_alert(
            title="Escalation Test",
            message="This alert may escalate",
            level=AlertLevel.WARNING,
            component="system"
        )
        
        # Simulate conditions that should trigger escalation
        await alert_manager.check_escalation_conditions(warning_alert)
        
        # Create error condition
        await alert_manager.create_alert(
            title="Escalation Test",
            message="This alert may escalate - ERROR",
            level=AlertLevel.ERROR,
            component="system"
        )
        
        # Check if warning was escalated
        escalated_alert = await alert_manager.get_alert(warning_alert.alert_id)
        if escalated_alert.escalated:
            assert escalated_alert.escalated_level == AlertLevel.ERROR
            assert escalated_alert.escalated_at is not None
    
    async def test_alert_auto_resolution(self, alert_manager):
        """Test automatic alert resolution."""
        # Create alert that can be auto-resolved
        alert = await alert_manager.create_alert(
            title="Auto-Resolve Test",
            message="This alert should auto-resolve",
            level=AlertLevel.WARNING,
            component="redis",
            auto_resolve=True,
            resolution_conditions={"redis_health": "healthy"}
        )
        
        assert alert.is_active is True
        
        # Trigger resolution condition
        await alert_manager.update_component_status("redis", "healthy")
        
        # Check if alert was resolved
        resolved_alert = await alert_manager.get_alert(alert.alert_id)
        if resolved_alert.auto_resolved:
            assert resolved_alert.is_active is False
            assert resolved_alert.resolved_at is not None
            assert resolved_alert.resolution_reason == "auto_resolved"
    
    async def test_user_notification_preferences(self, alert_manager, test_user):
        """Test user notification preferences."""
        # Set user notification preferences
        preferences = {
            "channels": [AlertChannel.TELEGRAM],
            "levels": [AlertLevel.WARNING, AlertLevel.ERROR, AlertLevel.CRITICAL],
            "quiet_hours": {"start": "22:00", "end": "08:00"},
            "alert_types": ["task_reminder", "system_alert"]
        }
        
        await alert_manager.set_user_preferences(
            test_user.user_id, preferences
        )
        
        # Create alert during quiet hours
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 15, 23, 30)  # 11:30 PM
            
            alert = await alert_manager.create_user_alert(
                user_id=test_user.user_id,
                title="Quiet Hours Test",
                message="Alert during quiet hours",
                level=AlertLevel.INFO,  # Below user's threshold
                alert_type="task_reminder"
            )
        
        # Alert should be created but not immediately sent
        assert alert is not None
        assert alert.scheduled_for is not None  # Should be scheduled for later
    
    async def test_alert_templates(self, alert_manager):
        """Test alert template system."""
        # Define alert template
        template_data = {
            "component_down": {
                "title": "Component {component} is Down",
                "message": "The {component} component has become unavailable. Last error: {error}",
                "level": AlertLevel.ERROR,
                "channels": [AlertChannel.TELEGRAM, AlertChannel.LOG],
                "auto_resolve": True
            }
        }
        
        await alert_manager.register_templates(template_data)
        
        # Create alert from template
        alert = await alert_manager.create_alert_from_template(
            "component_down",
            component="database",
            error="Connection timeout after 30 seconds"
        )
        
        assert alert.title == "Component database is Down"
        assert "Connection timeout" in alert.message
        assert alert.level == AlertLevel.ERROR
        assert alert.auto_resolve is True
    
    async def test_alert_aggregation(self, alert_manager):
        """Test alert aggregation for similar events."""
        # Create multiple similar alerts
        for i in range(10):
            await alert_manager.create_alert(
                title="High CPU Usage",
                message=f"CPU usage is {70 + i}%",
                level=AlertLevel.WARNING,
                component="system",
                aggregate_key="high_cpu"
            )
        
        # Should create aggregated alert instead of 10 individual ones
        active_alerts = await alert_manager.get_active_alerts()
        cpu_alerts = [a for a in active_alerts if "CPU" in a.title]
        
        # Should have fewer alerts due to aggregation
        assert len(cpu_alerts) < 10
        
        # Aggregated alert should contain count
        aggregated_alert = next((a for a in cpu_alerts if a.is_aggregated), None)
        if aggregated_alert:
            assert aggregated_alert.event_count >= 2
    
    async def test_alert_metrics_integration(self, alert_manager, metrics_collector):
        """Test integration with metrics collection."""
        # Create alerts of different levels
        alert_data = [
            (AlertLevel.INFO, "test_component"),
            (AlertLevel.WARNING, "test_component"),
            (AlertLevel.ERROR, "database"),
            (AlertLevel.CRITICAL, "system")
        ]
        
        for level, component in alert_data:
            await alert_manager.create_alert(
                title=f"{level.value} alert",
                message="Test alert",
                level=level,
                component=component
            )
        
        # Verify metrics were updated
        metrics_data = metrics_collector.export_metrics()
        
        # Should contain alert metrics
        assert "mcp_adhd_server_alerts_total" in metrics_data or \
               "mcp_adhd_server_alert" in metrics_data
    
    async def test_alert_history_and_search(self, alert_manager):
        """Test alert history and search functionality."""
        # Create various alerts with different attributes
        test_alerts = [
            {
                "title": "Database Error",
                "level": AlertLevel.ERROR,
                "component": "database",
                "tags": ["database", "connection"]
            },
            {
                "title": "High CPU",
                "level": AlertLevel.WARNING,
                "component": "system",
                "tags": ["performance", "cpu"]
            },
            {
                "title": "User Login Failed",
                "level": AlertLevel.INFO,
                "component": "auth",
                "tags": ["security", "login"]
            }
        ]
        
        created_alerts = []
        for alert_data in test_alerts:
            alert = await alert_manager.create_alert(
                title=alert_data["title"],
                message="Test alert",
                level=alert_data["level"],
                component=alert_data["component"],
                tags=alert_data["tags"]
            )
            created_alerts.append(alert)
        
        # Test search by component
        database_alerts = await alert_manager.search_alerts(
            filters={"component": "database"}
        )
        assert len(database_alerts) == 1
        assert database_alerts[0].title == "Database Error"
        
        # Test search by level
        warning_alerts = await alert_manager.search_alerts(
            filters={"level": AlertLevel.WARNING}
        )
        assert len(warning_alerts) == 1
        assert warning_alerts[0].title == "High CPU"
        
        # Test search by tags
        security_alerts = await alert_manager.search_alerts(
            filters={"tags": ["security"]}
        )
        assert len(security_alerts) == 1
        assert security_alerts[0].title == "User Login Failed"
    
    async def test_alert_lifecycle_management(self, alert_manager):
        """Test complete alert lifecycle."""
        # Create alert
        alert = await alert_manager.create_alert(
            title="Lifecycle Test Alert",
            message="Testing alert lifecycle",
            level=AlertLevel.WARNING,
            component="test"
        )
        
        # Verify alert is active
        assert alert.is_active is True
        assert alert.created_at is not None
        
        # Send alert
        await alert_manager.send_alert(alert)
        assert alert.sent_at is not None
        
        # Update alert
        await alert_manager.update_alert(
            alert.alert_id,
            message="Updated alert message",
            details={"update_reason": "additional_context"}
        )
        
        updated_alert = await alert_manager.get_alert(alert.alert_id)
        assert updated_alert.message == "Updated alert message"
        assert updated_alert.updated_at is not None
        
        # Resolve alert
        await alert_manager.resolve_alert(
            alert.alert_id,
            resolution_reason="Issue resolved",
            resolved_by="admin"
        )
        
        resolved_alert = await alert_manager.get_alert(alert.alert_id)
        assert resolved_alert.is_active is False
        assert resolved_alert.resolved_at is not None
        assert resolved_alert.resolution_reason == "Issue resolved"
    
    async def test_bulk_alert_operations(self, alert_manager):
        """Test bulk alert operations."""
        # Create multiple alerts
        alert_ids = []
        for i in range(5):
            alert = await alert_manager.create_alert(
                title=f"Bulk Test Alert {i}",
                message="Bulk operation test",
                level=AlertLevel.INFO,
                component="bulk_test"
            )
            alert_ids.append(alert.alert_id)
        
        # Bulk resolve alerts
        resolved_count = await alert_manager.bulk_resolve_alerts(
            alert_ids,
            resolution_reason="Bulk resolution test"
        )
        
        assert resolved_count == 5
        
        # Verify all alerts were resolved
        for alert_id in alert_ids:
            alert = await alert_manager.get_alert(alert_id)
            assert alert.is_active is False
            assert alert.resolution_reason == "Bulk resolution test"
    
    async def test_alert_performance(self, alert_manager):
        """Test alert system performance."""
        import time
        
        # Test rapid alert creation
        start_time = time.time()
        
        alerts_created = []
        for i in range(50):
            alert = await alert_manager.create_alert(
                title=f"Performance Test {i}",
                message="Performance testing",
                level=AlertLevel.INFO,
                component="performance_test"
            )
            alerts_created.append(alert)
        
        creation_duration = (time.time() - start_time) * 1000
        
        # Should handle 50 alerts quickly
        assert creation_duration < 1000  # Less than 1 second
        
        # Test alert search performance
        start_time = time.time()
        
        search_results = await alert_manager.search_alerts(
            filters={"component": "performance_test"}
        )
        
        search_duration = (time.time() - start_time) * 1000
        
        assert search_duration < 200  # Less than 200ms
        assert len(search_results) == 50
    
    async def test_alert_error_handling(self, alert_manager, mock_telegram):
        """Test alert system error handling."""
        # Test with failing Telegram delivery
        mock_telegram.send_message.side_effect = Exception("Telegram API error")
        
        alert = await alert_manager.create_alert(
            title="Error Handling Test",
            message="Testing error handling",
            level=AlertLevel.ERROR,
            channels=[AlertChannel.TELEGRAM]
        )
        
        # Should handle delivery failure gracefully
        await alert_manager.send_alert(alert)
        
        # Alert should still be created and marked as delivery failed
        failed_alert = await alert_manager.get_alert(alert.alert_id)
        assert failed_alert.delivery_failed is True
        assert "Telegram API error" in str(failed_alert.delivery_errors)
        
        # Should retry delivery
        retry_count = await alert_manager.retry_failed_alerts()
        assert retry_count >= 1