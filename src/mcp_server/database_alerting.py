"""
Database Performance Monitoring and Alerting System for MCP ADHD Server.

Features:
- Real-time database performance monitoring
- ADHD-specific performance alerts (<100ms query times)
- Connection pool utilization monitoring
- Circuit breaker status alerting
- Automated backup monitoring
- Migration safety alerts
- Performance degradation detection
- Proactive alerting for ADHD user impact
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import structlog

from mcp_server.database import (
    get_db_performance_metrics, perform_database_health_check,
    _circuit_breaker, _connection_metrics
)
from mcp_server.config import settings

logger = structlog.get_logger(__name__)


class DatabaseAlertManager:
    """Advanced database alerting system optimized for ADHD users."""
    
    def __init__(self):
        self.alert_history: List[Dict[str, Any]] = []
        self.alert_rules = {
            'adhd_performance_degradation': {
                'enabled': True,
                'threshold': 100.0,  # 100ms
                'severity': 'HIGH',
                'description': 'Query performance exceeds ADHD requirements'
            },
            'connection_pool_exhaustion': {
                'enabled': True,
                'threshold': 80.0,  # 80% utilization
                'severity': 'CRITICAL',
                'description': 'Connection pool approaching exhaustion'
            },
            'circuit_breaker_tripped': {
                'enabled': True,
                'severity': 'CRITICAL',
                'description': 'Database circuit breaker has been tripped'
            },
            'slow_query_detection': {
                'enabled': True,
                'threshold': 200.0,  # 200ms
                'severity': 'MEDIUM',
                'description': 'Slow queries detected that may impact ADHD users'
            },
            'connection_errors': {
                'enabled': True,
                'threshold': 5,  # 5 errors in monitoring period
                'severity': 'HIGH',
                'description': 'Multiple database connection errors detected'
            },
            'backup_failure': {
                'enabled': True,
                'severity': 'HIGH',
                'description': 'Database backup has failed'
            },
            'health_check_failure': {
                'enabled': True,
                'severity': 'CRITICAL',
                'description': 'Database health check failing'
            }
        }
        self.monitoring_active = False
    
    async def start_monitoring(self) -> None:
        """Start continuous database monitoring."""
        if self.monitoring_active:
            logger.warning("Database monitoring already active")
            return
        
        self.monitoring_active = True
        logger.info("Starting database performance monitoring",
                   alert_rules=len(self.alert_rules),
                   adhd_optimized=True)
        
        # Start background monitoring task
        asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop database monitoring."""
        self.monitoring_active = False
        logger.info("Database monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        monitoring_interval = 30  # 30 seconds
        
        while self.monitoring_active:
            try:
                await self._check_all_alert_rules()
                await asyncio.sleep(monitoring_interval)
            except Exception as e:
                logger.error("Error in database monitoring loop", error=str(e))
                await asyncio.sleep(monitoring_interval)
    
    async def _check_all_alert_rules(self) -> List[Dict[str, Any]]:
        """Check all alert rules and generate alerts."""
        alerts = []
        
        try:
            # Get current metrics
            performance_metrics = await get_db_performance_metrics()
            health_status = await perform_database_health_check()
            
            # Check each alert rule
            for rule_name, rule_config in self.alert_rules.items():
                if not rule_config.get('enabled', True):
                    continue
                
                alert = await self._check_alert_rule(
                    rule_name, rule_config, performance_metrics, health_status
                )
                
                if alert:
                    alerts.append(alert)
                    await self._process_alert(alert)
            
        except Exception as e:
            logger.error("Error checking alert rules", error=str(e))
            # Create error alert
            error_alert = {
                'rule_name': 'monitoring_system_error',
                'severity': 'HIGH',
                'message': f'Database monitoring system error: {str(e)}',
                'timestamp': datetime.now().isoformat(),
                'metadata': {'error': str(e)}
            }
            alerts.append(error_alert)
            await self._process_alert(error_alert)
        
        return alerts
    
    async def _check_alert_rule(
        self, 
        rule_name: str, 
        rule_config: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        health_status: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check individual alert rule."""
        
        if rule_name == 'adhd_performance_degradation':
            return await self._check_adhd_performance_rule(rule_config, performance_metrics)
        
        elif rule_name == 'connection_pool_exhaustion':
            return await self._check_pool_exhaustion_rule(rule_config, performance_metrics)
        
        elif rule_name == 'circuit_breaker_tripped':
            return await self._check_circuit_breaker_rule(rule_config)
        
        elif rule_name == 'slow_query_detection':
            return await self._check_slow_query_rule(rule_config, performance_metrics)
        
        elif rule_name == 'connection_errors':
            return await self._check_connection_errors_rule(rule_config)
        
        elif rule_name == 'backup_failure':
            return await self._check_backup_failure_rule(rule_config, performance_metrics)
        
        elif rule_name == 'health_check_failure':
            return await self._check_health_failure_rule(rule_config, health_status)
        
        return None
    
    async def _check_adhd_performance_rule(
        self, rule_config: Dict[str, Any], metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check ADHD performance requirements."""
        performance = metrics.get('performance_metrics', {})
        avg_query_time = performance.get('avg_query_time_ms', 0)
        p95_query_time = performance.get('p95_query_time_ms', 0)
        
        threshold = rule_config.get('threshold', 100.0)
        
        # Alert if average or 95th percentile exceeds threshold
        if avg_query_time > threshold or p95_query_time > threshold:
            return {
                'rule_name': 'adhd_performance_degradation',
                'severity': rule_config.get('severity', 'HIGH'),
                'message': f'Query performance degraded: avg={avg_query_time:.2f}ms, p95={p95_query_time:.2f}ms',
                'description': rule_config.get('description'),
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'avg_query_time_ms': avg_query_time,
                    'p95_query_time_ms': p95_query_time,
                    'threshold_ms': threshold,
                    'adhd_impact': 'HIGH' if avg_query_time > threshold else 'MEDIUM'
                },
                'recommendations': [
                    'Check for long-running queries',
                    'Review connection pool utilization',
                    'Consider database optimization',
                    'Monitor ADHD user experience impact'
                ]
            }
        
        return None
    
    async def _check_pool_exhaustion_rule(
        self, rule_config: Dict[str, Any], metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check connection pool exhaustion."""
        pool_metrics = metrics.get('pool_metrics', {})
        utilization = pool_metrics.get('utilization_percent', 0)
        threshold = rule_config.get('threshold', 80.0)
        
        if utilization > threshold:
            return {
                'rule_name': 'connection_pool_exhaustion',
                'severity': rule_config.get('severity', 'CRITICAL'),
                'message': f'Connection pool utilization at {utilization:.1f}% (threshold: {threshold}%)',
                'description': rule_config.get('description'),
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'utilization_percent': utilization,
                    'threshold_percent': threshold,
                    'pool_size': pool_metrics.get('pool_size', 0),
                    'checked_out': pool_metrics.get('checked_out', 0)
                },
                'recommendations': [
                    'Increase connection pool size',
                    'Check for connection leaks',
                    'Review long-running transactions',
                    'Monitor application connection usage patterns'
                ]
            }
        
        return None
    
    async def _check_circuit_breaker_rule(
        self, rule_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check circuit breaker status."""
        if _circuit_breaker['circuit_open']:
            return {
                'rule_name': 'circuit_breaker_tripped',
                'severity': rule_config.get('severity', 'CRITICAL'),
                'message': 'Database circuit breaker has been tripped - blocking operations',
                'description': rule_config.get('description'),
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'failure_count': _circuit_breaker['failure_count'],
                    'last_failure_time': _circuit_breaker['last_failure_time'],
                    'recovery_timeout': _circuit_breaker['recovery_timeout'],
                    'trips_total': _connection_metrics['circuit_breaker_trips']
                },
                'recommendations': [
                    'Investigate database connectivity issues',
                    'Check database server health',
                    'Review recent database errors',
                    'Wait for automatic recovery or manual intervention required'
                ]
            }
        
        return None
    
    async def _check_slow_query_rule(
        self, rule_config: Dict[str, Any], metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for slow queries."""
        performance = metrics.get('performance_metrics', {})
        slow_queries = performance.get('slow_queries', 0)
        max_query_time = performance.get('max_query_time_ms', 0)
        threshold = rule_config.get('threshold', 200.0)
        
        if slow_queries > 0 and max_query_time > threshold:
            return {
                'rule_name': 'slow_query_detection',
                'severity': rule_config.get('severity', 'MEDIUM'),
                'message': f'{slow_queries} slow queries detected, max time: {max_query_time:.2f}ms',
                'description': rule_config.get('description'),
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'slow_query_count': slow_queries,
                    'max_query_time_ms': max_query_time,
                    'threshold_ms': threshold
                },
                'recommendations': [
                    'Review slow query log',
                    'Optimize database indexes',
                    'Check for missing query optimizations',
                    'Monitor impact on ADHD user experience'
                ]
            }
        
        return None
    
    async def _check_connection_errors_rule(
        self, rule_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for connection errors."""
        connection_errors = _connection_metrics.get('connection_errors', [])
        recent_errors = [
            error for error in connection_errors
            if datetime.fromisoformat(error['timestamp']) > datetime.now() - timedelta(minutes=15)
        ]
        
        threshold = rule_config.get('threshold', 5)
        
        if len(recent_errors) >= threshold:
            return {
                'rule_name': 'connection_errors',
                'severity': rule_config.get('severity', 'HIGH'),
                'message': f'{len(recent_errors)} database connection errors in the last 15 minutes',
                'description': rule_config.get('description'),
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'recent_error_count': len(recent_errors),
                    'threshold': threshold,
                    'recent_errors': recent_errors[-3:],  # Last 3 errors
                    'total_errors': len(connection_errors)
                },
                'recommendations': [
                    'Check database server connectivity',
                    'Review database server logs',
                    'Investigate network issues',
                    'Check authentication and authorization'
                ]
            }
        
        return None
    
    async def _check_backup_failure_rule(
        self, rule_config: Dict[str, Any], metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for backup failures."""
        backup_status = metrics.get('backup_status', {})
        
        if backup_status.get('status') == 'failed':
            last_backup = backup_status.get('last_backup')
            return {
                'rule_name': 'backup_failure',
                'severity': rule_config.get('severity', 'HIGH'),
                'message': 'Database backup has failed',
                'description': rule_config.get('description'),
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'backup_status': backup_status.get('status'),
                    'last_backup': last_backup,
                    'backup_enabled': settings.database_backup_enabled
                },
                'recommendations': [
                    'Check backup system configuration',
                    'Review backup storage availability',
                    'Verify database permissions for backup',
                    'Consider manual backup if critical'
                ]
            }
        
        return None
    
    async def _check_health_failure_rule(
        self, rule_config: Dict[str, Any], health_status: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for health check failures."""
        if health_status.get('status') == 'CRITICAL':
            failed_checks = [
                check_name for check_name, check_data in health_status.get('checks', {}).items()
                if check_data.get('status') in ['FAIL', 'CRITICAL']
            ]
            
            return {
                'rule_name': 'health_check_failure',
                'severity': rule_config.get('severity', 'CRITICAL'),
                'message': f'Database health check critical: {len(failed_checks)} checks failed',
                'description': rule_config.get('description'),
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'health_status': health_status.get('status'),
                    'failed_checks': failed_checks,
                    'total_checks': len(health_status.get('checks', {}))
                },
                'recommendations': [
                    'Investigate failed health checks immediately',
                    'Check database connectivity and performance',
                    'Review database server resources',
                    'Consider service restart if necessary'
                ]
            }
        
        return None
    
    async def _process_alert(self, alert: Dict[str, Any]) -> None:
        """Process and log alert."""
        # Add to alert history
        self.alert_history.append(alert)
        
        # Keep only recent alerts (last 1000)
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        # Log alert
        logger.warning(
            "Database alert triggered",
            rule=alert['rule_name'],
            severity=alert['severity'],
            message=alert['message'],
            adhd_impact=alert.get('metadata', {}).get('adhd_impact'),
            recommendations=len(alert.get('recommendations', []))
        )
        
        # In a production system, you would also:
        # - Send notifications (email, Slack, PagerDuty)
        # - Update monitoring dashboards
        # - Trigger automated remediation if appropriate
    
    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of recent alerts."""
        now = datetime.now()
        recent_cutoff = now - timedelta(hours=24)
        
        recent_alerts = [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert['timestamp']) > recent_cutoff
        ]
        
        # Group by severity
        by_severity = {}
        for alert in recent_alerts:
            severity = alert.get('severity', 'UNKNOWN')
            if severity not in by_severity:
                by_severity[severity] = 0
            by_severity[severity] += 1
        
        # Group by rule
        by_rule = {}
        for alert in recent_alerts:
            rule = alert.get('rule_name', 'unknown')
            if rule not in by_rule:
                by_rule[rule] = 0
            by_rule[rule] += 1
        
        return {
            'monitoring_active': self.monitoring_active,
            'alert_rules_enabled': sum(1 for rule in self.alert_rules.values() if rule.get('enabled', True)),
            'total_alert_rules': len(self.alert_rules),
            'recent_alerts_24h': len(recent_alerts),
            'alerts_by_severity': by_severity,
            'alerts_by_rule': by_rule,
            'recent_alerts': recent_alerts[-10:],  # Last 10 alerts
            'timestamp': now.isoformat()
        }
    
    async def get_alert_rules_status(self) -> Dict[str, Any]:
        """Get status of all alert rules."""
        return {
            'alert_rules': self.alert_rules,
            'monitoring_active': self.monitoring_active,
            'total_rules': len(self.alert_rules),
            'enabled_rules': sum(1 for rule in self.alert_rules.values() if rule.get('enabled', True)),
            'timestamp': datetime.now().isoformat()
        }
    
    async def enable_alert_rule(self, rule_name: str) -> bool:
        """Enable specific alert rule."""
        if rule_name in self.alert_rules:
            self.alert_rules[rule_name]['enabled'] = True
            logger.info(f"Alert rule '{rule_name}' enabled")
            return True
        return False
    
    async def disable_alert_rule(self, rule_name: str) -> bool:
        """Disable specific alert rule."""
        if rule_name in self.alert_rules:
            self.alert_rules[rule_name]['enabled'] = False
            logger.info(f"Alert rule '{rule_name}' disabled")
            return True
        return False


# Global database alert manager instance
database_alert_manager = DatabaseAlertManager()