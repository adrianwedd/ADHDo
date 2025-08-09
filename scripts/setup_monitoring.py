#!/usr/bin/env python3
"""
Setup script for MCP ADHD Server monitoring and observability system.

This script:
1. Creates monitoring configuration directories
2. Generates dashboard configurations
3. Sets up alerting rules
4. Creates environment configuration templates
5. Validates monitoring setup
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from mcp_server.dashboard_config import ADHDDashboardConfig, AlertingConfig
    from mcp_server.config import settings
except ImportError as e:
    print(f"Error importing monitoring modules: {e}")
    print("Make sure you're running this script from the project root and dependencies are installed.")
    sys.exit(1)


class MonitoringSetup:
    """Setup manager for monitoring and observability system."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.monitoring_dir = project_root / "monitoring"
        
    def create_directory_structure(self):
        """Create necessary directory structure for monitoring."""
        print("📁 Creating monitoring directory structure...")
        
        directories = [
            self.monitoring_dir,
            self.monitoring_dir / "dashboards",
            self.monitoring_dir / "alerting",
            self.monitoring_dir / "grafana" / "dashboards",
            self.monitoring_dir / "grafana" / "datasources",
            self.monitoring_dir / "prometheus",
            self.monitoring_dir / "jaeger",
            self.monitoring_dir / "logs"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ Created: {directory}")
    
    def generate_dashboard_configs(self):
        """Generate dashboard configurations for Grafana."""
        print("\n📊 Generating dashboard configurations...")
        
        dashboards = {
            "adhd_main_dashboard.json": ADHDDashboardConfig.get_main_dashboard_config(),
            "adhd_performance_dashboard.json": ADHDDashboardConfig.get_performance_dashboard_config(),
            "adhd_user_experience_dashboard.json": ADHDDashboardConfig.get_user_experience_dashboard_config()
        }
        
        grafana_dashboards_dir = self.monitoring_dir / "grafana" / "dashboards"
        
        for filename, config in dashboards.items():
            filepath = grafana_dashboards_dir / filename
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"  ✅ Generated: {filepath}")
    
    def generate_alerting_configs(self):
        """Generate alerting configurations."""
        print("\n🚨 Generating alerting configurations...")
        
        # Prometheus alerting rules
        prometheus_rules = AlertingConfig.generate_prometheus_rules()
        prometheus_rules_file = self.monitoring_dir / "prometheus" / "adhd_alert_rules.yml"
        
        with open(prometheus_rules_file, 'w') as f:
            f.write(prometheus_rules)
        print(f"  ✅ Generated: {prometheus_rules_file}")
        
        # Grafana alerting configuration
        grafana_alerting = AlertingConfig.generate_grafana_alerting_config()
        grafana_alerting_file = self.monitoring_dir / "grafana" / "alerting_config.json"
        
        with open(grafana_alerting_file, 'w') as f:
            json.dump(grafana_alerting, f, indent=2)
        print(f"  ✅ Generated: {grafana_alerting_file}")
    
    def create_prometheus_config(self):
        """Create Prometheus configuration."""
        print("\n🔍 Creating Prometheus configuration...")
        
        prometheus_config = {
            "global": {
                "scrape_interval": "15s",
                "evaluation_interval": "15s"
            },
            "rule_files": [
                "adhd_alert_rules.yml"
            ],
            "alerting": {
                "alertmanagers": [{
                    "static_configs": [{
                        "targets": ["alertmanager:9093"]
                    }]
                }]
            },
            "scrape_configs": [
                {
                    "job_name": "mcp-adhd-server",
                    "metrics_path": "/api/monitoring/metrics/prometheus",
                    "scrape_interval": "10s",
                    "static_configs": [{
                        "targets": ["localhost:8000"]
                    }],
                    "scrape_timeout": "5s"
                },
                {
                    "job_name": "node-exporter",
                    "static_configs": [{
                        "targets": ["localhost:9100"]
                    }]
                },
                {
                    "job_name": "postgres-exporter",
                    "static_configs": [{
                        "targets": ["localhost:9187"]
                    }]
                },
                {
                    "job_name": "redis-exporter",
                    "static_configs": [{
                        "targets": ["localhost:9121"]
                    }]
                }
            ]
        }
        
        prometheus_config_file = self.monitoring_dir / "prometheus" / "prometheus.yml"
        with open(prometheus_config_file, 'w') as f:
            yaml.dump(prometheus_config, f, default_flow_style=False)
        print(f"  ✅ Generated: {prometheus_config_file}")
    
    def create_grafana_datasources(self):
        """Create Grafana datasource configurations."""
        print("\n📈 Creating Grafana datasource configurations...")
        
        datasources = {
            "prometheus.yml": {
                "apiVersion": 1,
                "datasources": [{
                    "name": "Prometheus",
                    "type": "prometheus",
                    "access": "proxy",
                    "url": "http://prometheus:9090",
                    "isDefault": True,
                    "editable": True,
                    "jsonData": {
                        "timeInterval": "5s",
                        "queryTimeout": "60s",
                        "httpMethod": "GET"
                    }
                }]
            },
            "jaeger.yml": {
                "apiVersion": 1,
                "datasources": [{
                    "name": "Jaeger",
                    "type": "jaeger",
                    "access": "proxy",
                    "url": "http://jaeger:16686",
                    "editable": True,
                    "jsonData": {
                        "tracesToLogs": {
                            "datasourceUid": "loki",
                            "tags": ["job", "instance", "trace_id"],
                            "mappedTags": [{"key": "service.name", "value": "service"}]
                        }
                    }
                }]
            }
        }
        
        datasources_dir = self.monitoring_dir / "grafana" / "datasources"
        
        for filename, config in datasources.items():
            filepath = datasources_dir / filename
            with open(filepath, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            print(f"  ✅ Generated: {filepath}")
    
    def create_docker_compose_monitoring(self):
        """Create Docker Compose configuration for monitoring stack."""
        print("\n🐳 Creating Docker Compose monitoring configuration...")
        
        docker_compose = {
            "version": "3.8",
            "services": {
                "prometheus": {
                    "image": "prom/prometheus:latest",
                    "container_name": "mcp-prometheus",
                    "ports": ["9090:9090"],
                    "volumes": [
                        "./prometheus:/etc/prometheus",
                        "prometheus_data:/prometheus"
                    ],
                    "command": [
                        "--config.file=/etc/prometheus/prometheus.yml",
                        "--storage.tsdb.path=/prometheus",
                        "--web.console.libraries=/etc/prometheus/console_libraries",
                        "--web.console.templates=/etc/prometheus/consoles",
                        "--storage.tsdb.retention.time=200h",
                        "--web.enable-lifecycle"
                    ],
                    "restart": "unless-stopped"
                },
                "grafana": {
                    "image": "grafana/grafana:latest",
                    "container_name": "mcp-grafana",
                    "ports": ["3000:3000"],
                    "volumes": [
                        "grafana_data:/var/lib/grafana",
                        "./grafana/dashboards:/etc/grafana/provisioning/dashboards",
                        "./grafana/datasources:/etc/grafana/provisioning/datasources"
                    ],
                    "environment": {
                        "GF_SECURITY_ADMIN_PASSWORD": "admin123",
                        "GF_USERS_ALLOW_SIGN_UP": "false",
                        "GF_INSTALL_PLUGINS": "grafana-piechart-panel,grafana-worldmap-panel"
                    },
                    "restart": "unless-stopped"
                },
                "jaeger": {
                    "image": "jaegertracing/all-in-one:latest",
                    "container_name": "mcp-jaeger",
                    "ports": [
                        "16686:16686",
                        "14268:14268"
                    ],
                    "environment": {
                        "COLLECTOR_OTLP_ENABLED": "true"
                    },
                    "restart": "unless-stopped"
                },
                "node-exporter": {
                    "image": "prom/node-exporter:latest",
                    "container_name": "mcp-node-exporter",
                    "ports": ["9100:9100"],
                    "volumes": [
                        "/proc:/host/proc:ro",
                        "/sys:/host/sys:ro",
                        "/:/rootfs:ro"
                    ],
                    "command": [
                        "--path.procfs=/host/proc",
                        "--path.rootfs=/rootfs",
                        "--path.sysfs=/host/sys",
                        "--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)"
                    ],
                    "restart": "unless-stopped"
                },
                "redis-exporter": {
                    "image": "oliver006/redis_exporter:latest",
                    "container_name": "mcp-redis-exporter",
                    "ports": ["9121:9121"],
                    "environment": {
                        "REDIS_ADDR": "host.docker.internal:6379"
                    },
                    "restart": "unless-stopped"
                }
            },
            "volumes": {
                "prometheus_data": {},
                "grafana_data": {}
            },
            "networks": {
                "monitoring": {
                    "driver": "bridge"
                }
            }
        }
        
        docker_compose_file = self.monitoring_dir / "docker-compose.monitoring.yml"
        with open(docker_compose_file, 'w') as f:
            yaml.dump(docker_compose, f, default_flow_style=False)
        print(f"  ✅ Generated: {docker_compose_file}")
    
    def create_environment_template(self):
        """Create environment configuration template for monitoring."""
        print("\n⚙️ Creating environment configuration template...")
        
        env_template = """
# Monitoring and Observability Configuration for MCP ADHD Server

# Sentry Error Tracking
SENTRY_DSN=your_sentry_dsn_here
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1

# OpenTelemetry Configuration
OTEL_SERVICE_NAME=mcp-adhd-server
OTEL_SERVICE_VERSION=1.0.0
OTEL_EXPORTER_JAEGER_ENDPOINT=http://localhost:14268/api/traces
OTEL_EXPORTER_PROMETHEUS_ENDPOINT=http://localhost:9090
OTEL_TRACES_EXPORTER=jaeger
OTEL_METRICS_EXPORTER=prometheus
OTEL_RESOURCE_ATTRIBUTES=service.name=mcp-adhd-server,service.version=1.0.0

# ADHD-Specific Monitoring
ADHD_RESPONSE_TIME_TARGET=3.0
ADHD_ATTENTION_SPAN_TRACKING=true
ADHD_COGNITIVE_LOAD_MONITORING=true
ADHD_CRISIS_DETECTION_ENABLED=true
ADHD_HYPERFOCUS_DETECTION_ENABLED=true

# Performance Monitoring
PERFORMANCE_MONITORING_ENABLED=true
DATABASE_QUERY_MONITORING=true
API_ENDPOINT_MONITORING=true
MEMORY_MONITORING_ENABLED=true
CPU_MONITORING_ENABLED=true

# Alerting Configuration
ALERTING_ENABLED=true
CRITICAL_ERROR_ALERT_THRESHOLD=5
RESPONSE_TIME_ALERT_THRESHOLD=5.0
MEMORY_USAGE_ALERT_THRESHOLD=85.0
CPU_USAGE_ALERT_THRESHOLD=80.0

# Notification Channels
SLACK_WEBHOOK_CRITICAL=your_slack_webhook_for_critical_alerts
SLACK_WEBHOOK_WARNINGS=your_slack_webhook_for_warnings
PAGERDUTY_ROUTING_KEY=your_pagerduty_routing_key

# Business Intelligence Metrics
USER_ENGAGEMENT_TRACKING=true
FEATURE_ADOPTION_TRACKING=true
NUDGE_EFFECTIVENESS_TRACKING=true
CALENDAR_INTEGRATION_ANALYTICS=true
CRISIS_INTERVENTION_ANALYTICS=true
        """.strip()
        
        env_template_file = self.monitoring_dir / ".env.monitoring.example"
        with open(env_template_file, 'w') as f:
            f.write(env_template)
        print(f"  ✅ Generated: {env_template_file}")
    
    def create_readme(self):
        """Create comprehensive README for monitoring setup."""
        print("\n📚 Creating monitoring README...")
        
        readme_content = """
# MCP ADHD Server - Monitoring and Observability

This directory contains the complete monitoring and observability setup for the MCP ADHD Server, optimized for ADHD user experience tracking and system performance monitoring.

## 🧠 ADHD-Specific Monitoring Features

- **Response Time Tracking**: <3 second target monitoring for attention-friendly performance
- **Cognitive Load Monitoring**: Real-time assessment of user cognitive burden
- **Crisis Detection**: Pattern recognition for user safety and wellbeing
- **Attention Span Analytics**: Tracking user engagement and focus patterns
- **Hyperfocus Detection**: Identifying extended focus sessions
- **Task Completion Analysis**: Success and abandonment pattern tracking

## 📊 Architecture Overview

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   MCP Server    │───▶│  Prometheus  │───▶│   Grafana   │
│  (Metrics API)  │    │ (Collection) │    │(Dashboards) │
└─────────────────┘    └──────────────┘    └─────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────┐
│     Jaeger      │    │ Alert Manager│
│   (Tracing)     │    │ (Alerting)   │
└─────────────────┘    └──────────────┘
```

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Copy monitoring environment template
cp .env.monitoring.example .env.monitoring

# Edit with your configuration
nano .env.monitoring
```

### 2. Start Monitoring Stack
```bash
# Start all monitoring services
docker-compose -f docker-compose.monitoring.yml up -d

# Verify services are running
docker-compose -f docker-compose.monitoring.yml ps
```

### 3. Access Dashboards
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686

## 📈 Available Dashboards

### 1. ADHD Main Dashboard
- Real-time response time monitoring with 3-second target
- Crisis detection alerts
- System health overview
- User engagement metrics

### 2. Performance Deep Dive
- Database query performance
- API endpoint analysis
- Memory and CPU utilization
- LLM request metrics

### 3. User Experience Analytics
- Attention span distribution
- Task completion analysis
- Hyperfocus session tracking
- Cognitive load patterns

## 🚨 Alerting Rules

### Critical Alerts
- ADHD response time target exceeded (>3s)
- Crisis pattern detection
- System errors affecting user experience

### Warning Alerts
- High error rates
- Slow database queries
- Resource usage thresholds
- User engagement drops

## 🔧 Configuration Files

```
monitoring/
├── dashboards/               # Dashboard configurations
├── alerting/                # Alert rules and channels
├── prometheus/              # Prometheus configuration
│   ├── prometheus.yml
│   └── adhd_alert_rules.yml
├── grafana/                 # Grafana configuration
│   ├── dashboards/          # Dashboard JSON files
│   └── datasources/         # Datasource configurations
└── docker-compose.monitoring.yml
```

## 🎯 ADHD Optimization Targets

| Metric | Target | Impact |
|--------|--------|---------|
| Response Time (95th) | <3 seconds | High attention retention |
| Database Queries | <100ms | Seamless user experience |
| Memory Usage | <85% | Stable performance |
| CPU Usage | <80% | Responsive interactions |
| Task Completion Rate | >70% | User success |

## 📊 Metrics Endpoints

- `/api/monitoring/health` - System health overview
- `/api/monitoring/performance` - Performance metrics
- `/api/monitoring/adhd-metrics` - ADHD-specific analytics
- `/api/monitoring/database` - Database performance
- `/api/monitoring/metrics/prometheus` - Prometheus format

## 🛠️ Troubleshooting

### Common Issues

1. **Metrics not appearing**
   - Check if MCP server is running
   - Verify Prometheus scrape targets
   - Check network connectivity

2. **Dashboards not loading**
   - Verify Grafana datasource configuration
   - Check Prometheus data availability
   - Review dashboard JSON syntax

3. **Alerts not firing**
   - Validate alert rule expressions
   - Check notification channel configuration
   - Verify alert manager connectivity

### Health Checks

```bash
# Check MCP server metrics endpoint
curl http://localhost:8000/api/monitoring/health

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana API
curl -u admin:admin123 http://localhost:3000/api/health
```

## 🔒 Security Considerations

- Monitor access logs for unusual patterns
- Secure Grafana with proper authentication
- Limit metrics endpoint access
- Regular security updates for monitoring stack

## 📱 ADHD User Experience Focus

This monitoring setup is specifically designed to support neurodivergent users:

- **Immediate feedback** on performance issues
- **Proactive alerting** before user experience degrades
- **Pattern recognition** for user behavior analysis
- **Safety monitoring** for crisis intervention
- **Cognitive load optimization** metrics

## 🤝 Contributing

When adding new metrics or dashboards:

1. Follow ADHD-friendly design principles
2. Include performance impact analysis
3. Add appropriate alerting rules
4. Document user experience implications
5. Test with neurodivergent users

## 📞 Support

For monitoring setup issues:
- Check system logs: `docker-compose logs -f`
- Review metric collection: `/api/monitoring/status`
- Validate configuration: `prometheus --check-config`

Remember: This monitoring system is optimized for ADHD users - every metric should contribute to a better, more accessible user experience.
        """.strip()
        
        readme_file = self.monitoring_dir / "README.md"
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        print(f"  ✅ Generated: {readme_file}")
    
    def validate_setup(self):
        """Validate the monitoring setup."""
        print("\n✅ Validating monitoring setup...")
        
        required_files = [
            self.monitoring_dir / "grafana" / "dashboards" / "adhd_main_dashboard.json",
            self.monitoring_dir / "prometheus" / "adhd_alert_rules.yml",
            self.monitoring_dir / "prometheus" / "prometheus.yml",
            self.monitoring_dir / "docker-compose.monitoring.yml",
            self.monitoring_dir / ".env.monitoring.example",
            self.monitoring_dir / "README.md"
        ]
        
        all_valid = True
        for required_file in required_files:
            if required_file.exists():
                print(f"  ✅ {required_file}")
            else:
                print(f"  ❌ Missing: {required_file}")
                all_valid = False
        
        if all_valid:
            print("\n🎉 Monitoring setup completed successfully!")
            print("\nNext steps:")
            print("1. Copy .env.monitoring.example to .env.monitoring and configure")
            print("2. Run: docker-compose -f monitoring/docker-compose.monitoring.yml up -d")
            print("3. Access Grafana at http://localhost:3000 (admin/admin123)")
            print("4. Import dashboards and configure data sources")
        else:
            print("\n❌ Setup validation failed. Please check the errors above.")
            return False
        
        return True
    
    def run_setup(self):
        """Run complete monitoring setup."""
        print("🧠 MCP ADHD Server - Monitoring Setup")
        print("=====================================\n")
        
        try:
            self.create_directory_structure()
            self.generate_dashboard_configs()
            self.generate_alerting_configs()
            self.create_prometheus_config()
            self.create_grafana_datasources()
            self.create_docker_compose_monitoring()
            self.create_environment_template()
            self.create_readme()
            
            return self.validate_setup()
            
        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            return False


def main():
    """Main setup function."""
    try:
        setup = MonitoringSetup(project_root)
        success = setup.run_setup()
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⛔ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()