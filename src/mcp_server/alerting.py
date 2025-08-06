"""
Automated health alerting system for MCP ADHD Server.

Monitors system health and sends alerts when issues are detected.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum

import structlog
import httpx

from mcp_server.config import settings
from mcp_server.health_monitor import health_monitor, HealthStatus

logger = structlog.get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels."""
    LOG = "log"
    WEBHOOK = "webhook"
    EMAIL = "email"
    TELEGRAM = "telegram"
    SLACK = "slack"


@dataclass
class Alert:
    """System alert definition."""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    component: str
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert alert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "component": self.component,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes
        }


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    component: str
    metric_path: str  # e.g., "system_metrics.cpu_percent"
    condition: str  # "gt", "lt", "eq", "ne"
    threshold: float
    severity: AlertSeverity
    cooldown_minutes: int = 15
    consecutive_failures: int = 3
    enabled: bool = True
    
    # Internal state
    failure_count: int = 0
    last_alert_time: Optional[datetime] = None
    last_check_time: Optional[datetime] = None


class AlertManager:
    """Manages system health alerts and notifications."""
    
    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_rules: List[AlertRule] = []
        self.notification_channels: Dict[AlertChannel, Callable] = {}
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Initialize default alert rules
        self._init_default_rules()
        
        # Initialize notification channels
        self._init_notification_channels()
        
        logger.info("Alert manager initialized", rules_count=len(self.alert_rules))
    
    def _init_default_rules(self):
        """Initialize default alerting rules."""
        self.alert_rules = [
            # System resource alerts
            AlertRule(
                name="High CPU Usage",
                component="system",
                metric_path="system_metrics.cpu_percent",
                condition="gt",
                threshold=90.0,
                severity=AlertSeverity.HIGH,
                cooldown_minutes=10,
                consecutive_failures=2
            ),
            AlertRule(
                name="Critical CPU Usage",
                component="system",
                metric_path="system_metrics.cpu_percent",
                condition="gt",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=5,
                consecutive_failures=1
            ),
            AlertRule(
                name="High Memory Usage",
                component="system",
                metric_path="system_metrics.memory_percent",
                condition="gt",
                threshold=85.0,
                severity=AlertSeverity.HIGH,
                cooldown_minutes=10,
                consecutive_failures=3
            ),
            AlertRule(
                name="Critical Memory Usage",
                component="system",
                metric_path="system_metrics.memory_percent",
                condition="gt",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=5,
                consecutive_failures=1
            ),
            AlertRule(
                name="Low Disk Space",
                component="system",
                metric_path="system_metrics.disk_usage_percent",
                condition="gt",
                threshold=85.0,
                severity=AlertSeverity.MEDIUM,
                cooldown_minutes=30,
                consecutive_failures=2
            ),
            AlertRule(
                name="Critical Disk Space",
                component="system",
                metric_path="system_metrics.disk_usage_percent",
                condition="gt",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=10,
                consecutive_failures=1
            ),
            
            # Component health alerts
            AlertRule(
                name="Redis Unhealthy",
                component="redis",
                metric_path="components.redis.status",
                condition="eq",
                threshold=0.0,  # unhealthy = 0
                severity=AlertSeverity.HIGH,
                cooldown_minutes=5,
                consecutive_failures=2
            ),
            AlertRule(
                name="Database Unhealthy",
                component="database",
                metric_path="components.database.status",
                condition="eq",
                threshold=0.0,
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=5,
                consecutive_failures=1
            ),
            AlertRule(
                name="LLM Service Degraded",
                component="llm",
                metric_path="components.llm.status",
                condition="lt",
                threshold=1.0,  # less than healthy
                severity=AlertSeverity.MEDIUM,
                cooldown_minutes=15,
                consecutive_failures=3
            ),
            
            # Performance alerts
            AlertRule(
                name="High Response Time",
                component="application",
                metric_path="components.application.response_time_ms",
                condition="gt",
                threshold=2000.0,  # 2 seconds
                severity=AlertSeverity.MEDIUM,
                cooldown_minutes=10,
                consecutive_failures=3
            ),
            AlertRule(
                name="Very High Response Time",
                component="application",
                metric_path="components.application.response_time_ms",
                condition="gt",
                threshold=5000.0,  # 5 seconds
                severity=AlertSeverity.HIGH,
                cooldown_minutes=5,
                consecutive_failures=2
            ),
            
            # ADHD-specific alerts
            AlertRule(
                name="High Cognitive Load",
                component="adhd_metrics",
                metric_path="performance_summary.avg_cognitive_load",
                condition="gt",
                threshold=0.8,
                severity=AlertSeverity.MEDIUM,
                cooldown_minutes=20,
                consecutive_failures=5
            ),
        ]
    
    def _init_notification_channels(self):
        """Initialize notification channels."""
        self.notification_channels = {
            AlertChannel.LOG: self._send_log_alert,
            AlertChannel.WEBHOOK: self._send_webhook_alert,
            AlertChannel.TELEGRAM: self._send_telegram_alert,
        }
    
    async def start_monitoring(self, check_interval_seconds: int = 60):
        """Start the alert monitoring loop."""
        if self.is_monitoring:
            logger.warning("Alert monitoring already running")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(check_interval_seconds)
        )
        logger.info("Alert monitoring started", interval=check_interval_seconds)
    
    async def stop_monitoring(self):
        """Stop the alert monitoring loop."""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Alert monitoring stopped")
    
    async def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                await self._check_all_rules()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in monitoring loop", error=str(e), exc_info=True)
                await asyncio.sleep(interval_seconds)
    
    async def _check_all_rules(self):
        """Check all alert rules against current system state."""
        # Get current health status
        try:
            health_data = await health_monitor.get_overall_health()
        except Exception as e:
            logger.error("Failed to get health data for alerting", error=str(e))
            return
        
        now = datetime.utcnow()
        
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
            
            rule.last_check_time = now
            
            try:
                # Extract metric value from health data
                current_value = self._extract_metric_value(health_data, rule.metric_path)
                if current_value is None:
                    continue
                
                # Check if rule condition is met
                condition_met = self._evaluate_condition(
                    current_value, rule.condition, rule.threshold
                )
                
                if condition_met:
                    rule.failure_count += 1
                    
                    # Check if we should trigger an alert
                    if (rule.failure_count >= rule.consecutive_failures and
                        self._should_send_alert(rule, now)):
                        
                        await self._trigger_alert(rule, current_value, now)
                else:
                    # Reset failure count if condition not met
                    if rule.failure_count > 0:
                        rule.failure_count = 0
                        
                        # Check if we should resolve existing alerts
                        await self._check_alert_resolution(rule, current_value)
                
            except Exception as e:
                logger.error(
                    "Error checking alert rule",
                    rule_name=rule.name,
                    error=str(e),
                    exc_info=True
                )
    
    def _extract_metric_value(self, data: Dict, metric_path: str) -> Optional[float]:
        """Extract metric value from nested dictionary using dot notation."""
        try:
            current = data
            for key in metric_path.split('.'):
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            
            # Handle status values (convert to numeric for comparison)
            if isinstance(current, str):
                if current == "healthy":
                    return 1.0
                elif current == "degraded":
                    return 0.5
                elif current == "unhealthy":
                    return 0.0
                else:
                    return None
            
            return float(current) if current is not None else None
            
        except (KeyError, ValueError, TypeError):
            return None
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate alert condition."""
        conditions = {
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "eq": lambda v, t: abs(v - t) < 0.001,
            "ne": lambda v, t: abs(v - t) >= 0.001,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
        }
        
        condition_func = conditions.get(condition)
        if condition_func:
            return condition_func(value, threshold)
        else:
            logger.warning("Unknown alert condition", condition=condition)
            return False
    
    def _should_send_alert(self, rule: AlertRule, current_time: datetime) -> bool:
        """Check if alert should be sent based on cooldown period."""
        if rule.last_alert_time is None:
            return True
        
        cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
        return current_time - rule.last_alert_time > cooldown_delta
    
    async def _trigger_alert(self, rule: AlertRule, current_value: float, timestamp: datetime):
        """Trigger an alert for the given rule."""
        alert_id = f"{rule.component}_{rule.name.lower().replace(' ', '_')}_{int(timestamp.timestamp())}"
        
        alert = Alert(
            id=alert_id,
            title=f"{rule.name} - {rule.component.title()}",
            description=self._generate_alert_description(rule, current_value),
            severity=rule.severity,
            component=rule.component,
            metric_name=rule.metric_path,
            current_value=current_value,
            threshold_value=rule.threshold,
            timestamp=timestamp
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Update rule state
        rule.last_alert_time = timestamp
        rule.failure_count = 0  # Reset after triggering
        
        # Send notifications
        await self._send_alert_notifications(alert)
        
        logger.warning(
            "Alert triggered",
            alert_id=alert_id,
            component=rule.component,
            severity=rule.severity.value,
            current_value=current_value,
            threshold=rule.threshold
        )
    
    def _generate_alert_description(self, rule: AlertRule, current_value: float) -> str:
        """Generate human-readable alert description."""
        descriptions = {
            "High CPU Usage": f"CPU usage is {current_value:.1f}%, exceeding threshold of {rule.threshold:.1f}%",
            "Critical CPU Usage": f"CPU usage is critically high at {current_value:.1f}%",
            "High Memory Usage": f"Memory usage is {current_value:.1f}%, exceeding threshold of {rule.threshold:.1f}%",
            "Critical Memory Usage": f"Memory usage is critically high at {current_value:.1f}%",
            "Low Disk Space": f"Disk usage is {current_value:.1f}%, approaching capacity",
            "Critical Disk Space": f"Disk space is critically low at {current_value:.1f}%",
            "Redis Unhealthy": "Redis service is unhealthy",
            "Database Unhealthy": "Database service is unhealthy - immediate attention required",
            "LLM Service Degraded": "LLM service performance is degraded",
            "High Response Time": f"Application response time is {current_value:.0f}ms, exceeding {rule.threshold:.0f}ms",
            "Very High Response Time": f"Application response time is very high at {current_value:.0f}ms",
            "High Cognitive Load": f"Average cognitive load is {current_value:.2f}, indicating user stress"
        }
        
        return descriptions.get(rule.name, f"{rule.name}: {current_value} exceeds threshold {rule.threshold}")
    
    async def _check_alert_resolution(self, rule: AlertRule, current_value: float):
        """Check if any active alerts for this rule should be resolved."""
        alerts_to_resolve = []
        
        for alert_id, alert in self.active_alerts.items():
            if (alert.component == rule.component and 
                not alert.resolved and
                alert.metric_name == rule.metric_path):
                
                alerts_to_resolve.append((alert_id, alert))
        
        for alert_id, alert in alerts_to_resolve:
            await self._resolve_alert(alert_id, f"Metric returned to normal: {current_value}")
    
    async def _resolve_alert(self, alert_id: str, resolution_notes: str):
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            alert.resolution_notes = resolution_notes
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            # Send resolution notification
            await self._send_resolution_notification(alert)
            
            logger.info(
                "Alert resolved",
                alert_id=alert_id,
                component=alert.component,
                resolution=resolution_notes
            )
    
    async def _send_alert_notifications(self, alert: Alert):
        """Send alert through all configured notification channels."""
        # Determine channels based on severity
        channels = [AlertChannel.LOG]  # Always log
        
        if alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            if settings.telegram_bot_token:
                channels.append(AlertChannel.TELEGRAM)
            
            # Add webhook if configured
            # channels.append(AlertChannel.WEBHOOK)
        
        # Send through each channel
        for channel in channels:
            try:
                sender = self.notification_channels.get(channel)
                if sender:
                    await sender(alert)
            except Exception as e:
                logger.error(
                    "Failed to send alert notification",
                    channel=channel.value,
                    alert_id=alert.id,
                    error=str(e)
                )
    
    async def _send_resolution_notification(self, alert: Alert):
        """Send alert resolution notification."""
        try:
            await self._send_log_alert(alert, is_resolution=True)
            
            if alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
                if settings.telegram_bot_token:
                    await self._send_telegram_alert(alert, is_resolution=True)
        except Exception as e:
            logger.error("Failed to send resolution notification", error=str(e))
    
    async def _send_log_alert(self, alert: Alert, is_resolution: bool = False):
        """Send alert via logging."""
        if is_resolution:
            logger.info(
                f"🟢 RESOLVED: {alert.title}",
                alert_id=alert.id,
                component=alert.component,
                resolution_notes=alert.resolution_notes
            )
        else:
            severity_emoji = {
                AlertSeverity.LOW: "🟡",
                AlertSeverity.MEDIUM: "🟠", 
                AlertSeverity.HIGH: "🔴",
                AlertSeverity.CRITICAL: "🚨"
            }
            
            logger.warning(
                f"{severity_emoji.get(alert.severity, '⚠️')} ALERT: {alert.title}",
                alert_id=alert.id,
                description=alert.description,
                component=alert.component,
                severity=alert.severity.value,
                current_value=alert.current_value,
                threshold=alert.threshold_value
            )
    
    async def _send_webhook_alert(self, alert: Alert, is_resolution: bool = False):
        """Send alert via webhook."""
        # Implementation would depend on webhook configuration
        webhook_url = getattr(settings, 'alert_webhook_url', None)
        if not webhook_url:
            return
        
        payload = {
            "type": "resolution" if is_resolution else "alert",
            "alert": alert.to_dict(),
            "service": "MCP-ADHD-Server",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
        except Exception as e:
            logger.error("Webhook alert failed", error=str(e))
    
    async def _send_telegram_alert(self, alert: Alert, is_resolution: bool = False):
        """Send alert via Telegram."""
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return
        
        try:
            severity_emoji = {
                AlertSeverity.LOW: "🟡",
                AlertSeverity.MEDIUM: "🟠",
                AlertSeverity.HIGH: "🔴", 
                AlertSeverity.CRITICAL: "🚨"
            }
            
            if is_resolution:
                message = f"🟢 **RESOLVED**\n\n"
                message += f"**{alert.title}**\n"
                message += f"Resolved at: {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                message += f"Notes: {alert.resolution_notes}"
            else:
                emoji = severity_emoji.get(alert.severity, "⚠️")
                message = f"{emoji} **ALERT - {alert.severity.value.upper()}**\n\n"
                message += f"**{alert.title}**\n"
                message += f"{alert.description}\n\n"
                message += f"Component: {alert.component}\n"
                message += f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Send via Telegram Bot API
            url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": settings.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
        except Exception as e:
            logger.error("Telegram alert failed", error=str(e))
    
    # === PUBLIC API ===
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all active alerts."""
        return [alert.to_dict() for alert in self.active_alerts.values()]
    
    def get_alert_history(self, limit: int = 50) -> List[Dict]:
        """Get alert history."""
        sorted_alerts = sorted(
            self.alert_history, 
            key=lambda a: a.timestamp, 
            reverse=True
        )
        return [alert.to_dict() for alert in sorted_alerts[:limit]]
    
    def get_alert_statistics(self) -> Dict:
        """Get alerting statistics."""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_week = now - timedelta(days=7)
        
        recent_alerts = [a for a in self.alert_history if a.timestamp > last_24h]
        weekly_alerts = [a for a in self.alert_history if a.timestamp > last_week]
        
        return {
            "active_alerts": len(self.active_alerts),
            "total_rules": len(self.alert_rules),
            "enabled_rules": sum(1 for r in self.alert_rules if r.enabled),
            "alerts_last_24h": len(recent_alerts),
            "alerts_last_week": len(weekly_alerts),
            "total_alerts": len(self.alert_history),
            "severity_breakdown": {
                severity.value: sum(
                    1 for a in recent_alerts if a.severity == severity
                )
                for severity in AlertSeverity
            },
            "component_breakdown": {
                component: sum(
                    1 for a in recent_alerts if a.component == component
                )
                for component in set(a.component for a in recent_alerts)
            }
        }
    
    async def manual_alert_check(self) -> Dict:
        """Manually trigger alert check and return results."""
        logger.info("Manual alert check triggered")
        await self._check_all_rules()
        
        return {
            "check_completed": True,
            "timestamp": datetime.utcnow().isoformat(),
            "active_alerts": len(self.active_alerts),
            "rules_checked": len([r for r in self.alert_rules if r.enabled])
        }
    
    def add_alert_rule(self, rule: AlertRule) -> bool:
        """Add a new alert rule."""
        try:
            self.alert_rules.append(rule)
            logger.info("Alert rule added", rule_name=rule.name)
            return True
        except Exception as e:
            logger.error("Failed to add alert rule", error=str(e))
            return False
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable an alert rule."""
        for rule in self.alert_rules:
            if rule.name == rule_name:
                rule.enabled = False
                logger.info("Alert rule disabled", rule_name=rule_name)
                return True
        return False
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable an alert rule."""
        for rule in self.alert_rules:
            if rule.name == rule_name:
                rule.enabled = True
                logger.info("Alert rule enabled", rule_name=rule_name)
                return True
        return False


# Global alert manager instance
alert_manager = AlertManager()