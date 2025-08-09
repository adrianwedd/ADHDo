"""
Custom Metrics Dashboard and Alerting Configuration for MCP ADHD Server.

Provides comprehensive dashboard layouts and alerting rules optimized for ADHD user experience:
- ADHD-specific KPI dashboards
- Real-time performance monitoring
- Crisis detection alerting
- User experience metrics visualization
- System health monitoring
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

from mcp_server.config import settings


class ADHDDashboardConfig:
    """
    Configuration for ADHD-specific monitoring dashboards.
    
    Provides dashboard layouts optimized for:
    - Quick visual scanning (ADHD-friendly design)
    - Critical metrics prioritization
    - Executive function support metrics
    - Crisis detection indicators
    """
    
    @staticmethod
    def get_main_dashboard_config() -> Dict[str, Any]:
        """Get main ADHD-optimized dashboard configuration."""
        return {
            "dashboard": {
                "title": "MCP ADHD Server - Main Dashboard",
                "description": "Real-time monitoring optimized for ADHD user experience",
                "refresh_interval": "5s",
                "time_range": {
                    "from": "now-15m",
                    "to": "now"
                },
                "panels": [
                    # Critical Response Time Panel (Top Priority)
                    {
                        "id": 1,
                        "title": "🎯 ADHD Response Time Target (<3s)",
                        "type": "gauge",
                        "position": {"x": 0, "y": 0, "w": 6, "h": 4},
                        "targets": [{
                            "expr": "histogram_quantile(0.95, adhd_response_time_seconds_bucket)",
                            "legendFormat": "95th Percentile"
                        }],
                        "fieldConfig": {
                            "max": 5.0,
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": 0},
                                    {"color": "yellow", "value": 2.0},
                                    {"color": "red", "value": 3.0}
                                ]
                            }
                        },
                        "options": {
                            "displayMode": "gradient",
                            "orientation": "horizontal"
                        }
                    },
                    
                    # Crisis Detection Panel (High Priority)
                    {
                        "id": 2,
                        "title": "🚨 Crisis Detection Status",
                        "type": "stat",
                        "position": {"x": 6, "y": 0, "w": 3, "h": 2},
                        "targets": [{
                            "expr": "increase(adhd_crisis_detections_total[5m])",
                            "legendFormat": "Crisis Events"
                        }],
                        "fieldConfig": {
                            "color": {
                                "mode": "thresholds"
                            },
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": 0},
                                    {"color": "yellow", "value": 1},
                                    {"color": "red", "value": 3}
                                ]
                            }
                        }
                    },
                    
                    # Active Users Panel
                    {
                        "id": 3,
                        "title": "👥 Active Users",
                        "type": "stat",
                        "position": {"x": 9, "y": 0, "w": 3, "h": 2},
                        "targets": [{
                            "expr": "count(increase(adhd_attention_span_seconds_count[5m]) > 0)",
                            "legendFormat": "Active Users"
                        }]
                    },
                    
                    # System Health Overview
                    {
                        "id": 4,
                        "title": "💚 System Health Score",
                        "type": "gauge",
                        "position": {"x": 6, "y": 2, "w": 6, "h": 2},
                        "targets": [{
                            "expr": "(1 - rate(api_requests_total{status_code=~\"5..\"}[5m]) / rate(api_requests_total[5m])) * 100",
                            "legendFormat": "Health Score %"
                        }],
                        "fieldConfig": {
                            "max": 100,
                            "thresholds": {
                                "steps": [
                                    {"color": "red", "value": 0},
                                    {"color": "yellow", "value": 80},
                                    {"color": "green", "value": 95}
                                ]
                            }
                        }
                    },
                    
                    # Response Time Trend
                    {
                        "id": 5,
                        "title": "📈 Response Time Trend (ADHD Target: 3s)",
                        "type": "timeseries",
                        "position": {"x": 0, "y": 4, "w": 12, "h": 4},
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.50, adhd_response_time_seconds_bucket)",
                                "legendFormat": "50th Percentile"
                            },
                            {
                                "expr": "histogram_quantile(0.95, adhd_response_time_seconds_bucket)",
                                "legendFormat": "95th Percentile"
                            },
                            {
                                "expr": "histogram_quantile(0.99, adhd_response_time_seconds_bucket)", 
                                "legendFormat": "99th Percentile"
                            }
                        ],
                        "fieldConfig": {
                            "custom": {
                                "thresholdsStyle": {
                                    "mode": "line"
                                }
                            },
                            "thresholds": {
                                "steps": [
                                    {"color": "transparent", "value": 0},
                                    {"color": "red", "value": 3.0}
                                ]
                            }
                        }
                    },
                    
                    # ADHD Metrics Summary
                    {
                        "id": 6,
                        "title": "🧠 ADHD User Experience Metrics",
                        "type": "table",
                        "position": {"x": 0, "y": 8, "w": 6, "h": 4},
                        "targets": [
                            {
                                "expr": "avg(adhd_cognitive_load_score)",
                                "legendFormat": "Avg Cognitive Load",
                                "format": "table"
                            },
                            {
                                "expr": "avg(adhd_attention_span_seconds)",
                                "legendFormat": "Avg Attention Span (s)",
                                "format": "table"  
                            },
                            {
                                "expr": "rate(adhd_task_completions_total[5m])",
                                "legendFormat": "Task Completion Rate",
                                "format": "table"
                            },
                            {
                                "expr": "rate(adhd_hyperfocus_sessions_total[1h])",
                                "legendFormat": "Hyperfocus Sessions/hr",
                                "format": "table"
                            }
                        ]
                    },
                    
                    # Error Rate by Endpoint
                    {
                        "id": 7,
                        "title": "❌ Error Rate by Endpoint",
                        "type": "heatmap",
                        "position": {"x": 6, "y": 8, "w": 6, "h": 4},
                        "targets": [{
                            "expr": "rate(api_requests_total{status_code=~\"4..|5..\"}[5m]) by (endpoint)",
                            "legendFormat": "{{endpoint}}"
                        }]
                    }
                ]
            }
        }
    
    @staticmethod
    def get_performance_dashboard_config() -> Dict[str, Any]:
        """Get performance-focused dashboard configuration."""
        return {
            "dashboard": {
                "title": "MCP ADHD Server - Performance Deep Dive",
                "description": "Detailed performance metrics for ADHD optimization",
                "refresh_interval": "10s",
                "panels": [
                    # Database Performance
                    {
                        "id": 1,
                        "title": "🗄️ Database Query Performance",
                        "type": "timeseries",
                        "position": {"x": 0, "y": 0, "w": 12, "h": 4},
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.95, database_query_duration_seconds_bucket)",
                                "legendFormat": "95th Percentile"
                            },
                            {
                                "expr": "histogram_quantile(0.50, database_query_duration_seconds_bucket)",
                                "legendFormat": "Median"
                            }
                        ]
                    },
                    
                    # Memory Usage
                    {
                        "id": 2,
                        "title": "💾 Memory Usage",
                        "type": "timeseries",
                        "position": {"x": 0, "y": 4, "w": 6, "h": 4},
                        "targets": [{
                            "expr": "system_memory_usage_percent",
                            "legendFormat": "Memory Usage %"
                        }]
                    },
                    
                    # CPU Usage
                    {
                        "id": 3,
                        "title": "⚡ CPU Usage",
                        "type": "timeseries",
                        "position": {"x": 6, "y": 4, "w": 6, "h": 4},
                        "targets": [{
                            "expr": "system_cpu_usage_percent",
                            "legendFormat": "CPU Usage %"
                        }]
                    },
                    
                    # LLM Performance
                    {
                        "id": 4,
                        "title": "🤖 LLM Request Performance",
                        "type": "timeseries",
                        "position": {"x": 0, "y": 8, "w": 12, "h": 4},
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.95, llm_request_duration_seconds_bucket)",
                                "legendFormat": "95th Percentile"
                            },
                            {
                                "expr": "avg(llm_request_duration_seconds) by (model)",
                                "legendFormat": "{{model}} Average"
                            }
                        ]
                    }
                ]
            }
        }
    
    @staticmethod
    def get_user_experience_dashboard_config() -> Dict[str, Any]:
        """Get user experience focused dashboard."""
        return {
            "dashboard": {
                "title": "MCP ADHD Server - User Experience Analytics",
                "description": "ADHD-specific user experience and engagement metrics",
                "refresh_interval": "30s",
                "panels": [
                    # Attention Span Distribution
                    {
                        "id": 1,
                        "title": "⏱️ Attention Span Distribution",
                        "type": "histogram",
                        "position": {"x": 0, "y": 0, "w": 6, "h": 4},
                        "targets": [{
                            "expr": "adhd_attention_span_seconds_bucket",
                            "legendFormat": "Attention Span"
                        }]
                    },
                    
                    # Engagement Score Over Time
                    {
                        "id": 2,
                        "title": "📊 User Engagement Score",
                        "type": "timeseries",
                        "position": {"x": 6, "y": 0, "w": 6, "h": 4},
                        "targets": [{
                            "expr": "avg(adhd_engagement_score)",
                            "legendFormat": "Average Engagement"
                        }]
                    },
                    
                    # Task Completion vs Abandonment
                    {
                        "id": 3,
                        "title": "✅ Task Completion Analysis",
                        "type": "pie",
                        "position": {"x": 0, "y": 4, "w": 6, "h": 4},
                        "targets": [
                            {
                                "expr": "sum(increase(adhd_task_completions_total[1h]))",
                                "legendFormat": "Completed"
                            },
                            {
                                "expr": "sum(increase(adhd_task_abandonments_total[1h]))",
                                "legendFormat": "Abandoned"
                            }
                        ]
                    },
                    
                    # Hyperfocus Sessions
                    {
                        "id": 4,
                        "title": "🔥 Hyperfocus Sessions",
                        "type": "timeseries",
                        "position": {"x": 6, "y": 4, "w": 6, "h": 4},
                        "targets": [{
                            "expr": "rate(adhd_hyperfocus_sessions_total[1h])",
                            "legendFormat": "Sessions per Hour"
                        }]
                    },
                    
                    # Cognitive Load Heatmap
                    {
                        "id": 5,
                        "title": "🧠 Cognitive Load by Time of Day",
                        "type": "heatmap",
                        "position": {"x": 0, "y": 8, "w": 12, "h": 4},
                        "targets": [{
                            "expr": "avg_over_time(adhd_cognitive_load_score[1h]) by (hour)",
                            "legendFormat": "Cognitive Load"
                        }]
                    }
                ]
            }
        }


class AlertingConfig:
    """
    Comprehensive alerting configuration for ADHD-specific monitoring.
    """
    
    @staticmethod
    def get_alert_rules() -> List[Dict[str, Any]]:
        """Get all alerting rules for ADHD server monitoring."""
        return [
            # Critical Response Time Alert
            {
                "name": "ADHD Response Time Target Exceeded",
                "description": "95th percentile response time exceeds ADHD-friendly target",
                "severity": "critical",
                "expression": f"histogram_quantile(0.95, adhd_response_time_seconds_bucket) > {settings.adhd_response_time_target}",
                "duration": "2m",
                "annotations": {
                    "summary": "ADHD response time target exceeded",
                    "description": "95th percentile response time is {{ $value }}s, exceeding the {settings.adhd_response_time_target}s ADHD target",
                    "impact": "High attention disruption for ADHD users",
                    "action": "Investigate slow endpoints and optimize performance"
                },
                "labels": {
                    "team": "platform",
                    "service": "mcp-adhd-server",
                    "user_impact": "high"
                }
            },
            
            # Crisis Detection Alert
            {
                "name": "Crisis Pattern Detected",
                "description": "Crisis detection patterns identified for user intervention",
                "severity": "critical",
                "expression": "increase(adhd_crisis_detections_total[5m]) > 0",
                "duration": "0m",  # Immediate alert
                "annotations": {
                    "summary": "Crisis pattern detected requiring immediate attention",
                    "description": "{{ $value }} crisis detection events in the last 5 minutes",
                    "impact": "User safety and wellbeing",
                    "action": "Review crisis interventions and ensure appropriate support resources are active"
                },
                "labels": {
                    "team": "support",
                    "service": "mcp-adhd-server",
                    "priority": "p0"
                }
            },
            
            # High Error Rate Alert
            {
                "name": "High Error Rate Disrupting ADHD Users",
                "description": "Error rate exceeding threshold that disrupts ADHD user experience",
                "severity": "warning",
                "expression": "rate(api_requests_total{status_code=~\"5..\"}[5m]) / rate(api_requests_total[5m]) > 0.05",
                "duration": "5m",
                "annotations": {
                    "summary": "High error rate detected",
                    "description": "Error rate is {{ $value | humanizePercentage }}, causing disruption to ADHD users",
                    "impact": "Attention and task interruption for users",
                    "action": "Investigate error patterns and implement ADHD-friendly error handling"
                },
                "labels": {
                    "team": "platform",
                    "service": "mcp-adhd-server",
                    "user_impact": "medium"
                }
            },
            
            # Database Performance Alert
            {
                "name": "Slow Database Queries Affecting ADHD Experience",
                "description": "Database queries exceeding ADHD-friendly performance thresholds",
                "severity": "warning",
                "expression": f"histogram_quantile(0.95, database_query_duration_seconds_bucket) > {settings.database_performance_threshold / 1000}",
                "duration": "3m",
                "annotations": {
                    "summary": "Slow database queries detected",
                    "description": "95th percentile database query time is {{ $value }}s, exceeding ADHD performance threshold",
                    "impact": "Increased waiting time and attention disruption",
                    "action": "Optimize slow queries and check database performance"
                },
                "labels": {
                    "team": "platform",
                    "service": "mcp-adhd-server",
                    "component": "database"
                }
            },
            
            # Memory Usage Alert
            {
                "name": "High Memory Usage",
                "description": "System memory usage approaching critical levels",
                "severity": "warning",
                "expression": f"system_memory_usage_percent > {settings.memory_usage_alert_threshold}",
                "duration": "5m",
                "annotations": {
                    "summary": "High memory usage detected",
                    "description": "Memory usage is {{ $value }}%, approaching critical levels",
                    "impact": "Potential system degradation affecting user experience",
                    "action": "Investigate memory leaks and consider scaling"
                },
                "labels": {
                    "team": "platform",
                    "service": "mcp-adhd-server",
                    "component": "system"
                }
            },
            
            # CPU Usage Alert
            {
                "name": "High CPU Usage",
                "description": "System CPU usage consistently high",
                "severity": "warning",
                "expression": f"system_cpu_usage_percent > {settings.cpu_usage_alert_threshold}",
                "duration": "10m",
                "annotations": {
                    "summary": "High CPU usage detected",
                    "description": "CPU usage is {{ $value }}% for extended period",
                    "impact": "Degraded response times affecting ADHD user experience",
                    "action": "Investigate CPU-intensive operations and consider optimization"
                },
                "labels": {
                    "team": "platform",
                    "service": "mcp-adhd-server",
                    "component": "system"
                }
            },
            
            # User Engagement Drop Alert
            {
                "name": "User Engagement Drop Detected",
                "description": "Significant drop in user engagement metrics",
                "severity": "warning",
                "expression": "avg_over_time(adhd_engagement_score[15m]) < 40",
                "duration": "10m",
                "annotations": {
                    "summary": "User engagement drop detected",
                    "description": "Average engagement score dropped to {{ $value }}, indicating potential user experience issues",
                    "impact": "Reduced user satisfaction and task completion",
                    "action": "Review recent changes and user feedback for experience degradation"
                },
                "labels": {
                    "team": "product",
                    "service": "mcp-adhd-server",
                    "component": "user_experience"
                }
            },
            
            # High Task Abandonment Alert
            {
                "name": "High Task Abandonment Rate",
                "description": "Unusually high rate of task abandonment by users",
                "severity": "warning",
                "expression": "rate(adhd_task_abandonments_total[1h]) > rate(adhd_task_completions_total[1h])",
                "duration": "15m",
                "annotations": {
                    "summary": "High task abandonment rate detected",
                    "description": "Task abandonment rate exceeding completion rate, indicating user frustration",
                    "impact": "Poor user experience and reduced productivity for ADHD users",
                    "action": "Analyze task complexity and user flow for improvement opportunities"
                },
                "labels": {
                    "team": "product",
                    "service": "mcp-adhd-server",
                    "component": "task_management"
                }
            }
        ]
    
    @staticmethod
    def get_notification_channels() -> List[Dict[str, Any]]:
        """Get notification channel configurations."""
        return [
            {
                "name": "slack-critical",
                "type": "slack",
                "settings": {
                    "webhook_url": "${SLACK_WEBHOOK_CRITICAL}",
                    "channel": "#alerts-critical",
                    "username": "MCP-ADHD-Monitor",
                    "title": "🚨 Critical Alert - MCP ADHD Server",
                    "text": "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}"
                }
            },
            {
                "name": "slack-warnings",
                "type": "slack", 
                "settings": {
                    "webhook_url": "${SLACK_WEBHOOK_WARNINGS}",
                    "channel": "#alerts-warnings",
                    "username": "MCP-ADHD-Monitor",
                    "title": "⚠️ Warning - MCP ADHD Server",
                    "text": "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}"
                }
            },
            {
                "name": "email-oncall",
                "type": "email",
                "settings": {
                    "addresses": ["oncall@company.com"],
                    "subject": "[MCP-ADHD] {{ .Status | title }} - {{ .GroupLabels.alertname }}",
                    "body": "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
                }
            },
            {
                "name": "pagerduty-critical",
                "type": "pagerduty",
                "settings": {
                    "routing_key": "${PAGERDUTY_ROUTING_KEY}",
                    "description": "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}"
                }
            }
        ]
    
    @staticmethod
    def generate_prometheus_rules() -> str:
        """Generate Prometheus alerting rules YAML."""
        rules = AlertingConfig.get_alert_rules()
        
        prometheus_config = {
            "groups": [{
                "name": "mcp_adhd_server_alerts",
                "interval": "30s",
                "rules": []
            }]
        }
        
        for rule in rules:
            prometheus_rule = {
                "alert": rule["name"].replace(" ", "_"),
                "expr": rule["expression"],
                "for": rule["duration"],
                "labels": rule["labels"],
                "annotations": rule["annotations"]
            }
            prometheus_config["groups"][0]["rules"].append(prometheus_rule)
        
        import yaml
        return yaml.dump(prometheus_config, default_flow_style=False)
    
    @staticmethod
    def generate_grafana_alerting_config() -> Dict[str, Any]:
        """Generate Grafana alerting configuration."""
        return {
            "contactPoints": AlertingConfig.get_notification_channels(),
            "policies": [
                {
                    "receiver": "slack-critical",
                    "group_by": ["alertname", "service"],
                    "matchers": [
                        {"name": "severity", "value": "critical"}
                    ],
                    "group_wait": "30s",
                    "group_interval": "2m",
                    "repeat_interval": "5m"
                },
                {
                    "receiver": "slack-warnings",
                    "group_by": ["alertname"],
                    "matchers": [
                        {"name": "severity", "value": "warning"}
                    ],
                    "group_wait": "1m",
                    "group_interval": "5m",
                    "repeat_interval": "15m"
                }
            ]
        }


def export_dashboard_configs(output_dir: str = "./monitoring/dashboards/"):
    """Export all dashboard configurations to files."""
    import os
    import json
    
    os.makedirs(output_dir, exist_ok=True)
    
    configs = {
        "main_dashboard.json": ADHDDashboardConfig.get_main_dashboard_config(),
        "performance_dashboard.json": ADHDDashboardConfig.get_performance_dashboard_config(),
        "user_experience_dashboard.json": ADHDDashboardConfig.get_user_experience_dashboard_config()
    }
    
    for filename, config in configs.items():
        with open(os.path.join(output_dir, filename), 'w') as f:
            json.dump(config, f, indent=2)
    
    print(f"Dashboard configurations exported to {output_dir}")


def export_alerting_configs(output_dir: str = "./monitoring/alerting/"):
    """Export alerting configurations to files."""
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Export Prometheus rules
    with open(os.path.join(output_dir, "prometheus_rules.yml"), 'w') as f:
        f.write(AlertingConfig.generate_prometheus_rules())
    
    # Export Grafana alerting config
    with open(os.path.join(output_dir, "grafana_alerting.json"), 'w') as f:
        json.dump(AlertingConfig.generate_grafana_alerting_config(), f, indent=2)
    
    print(f"Alerting configurations exported to {output_dir}")


if __name__ == "__main__":
    # Export configurations when run directly
    export_dashboard_configs()
    export_alerting_configs()