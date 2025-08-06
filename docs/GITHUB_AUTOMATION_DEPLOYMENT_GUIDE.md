# GitHub Issue Automation System - Production Deployment Guide

**Enterprise deployment guide for scalable GitHub issue automation**

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Production Deployment](#production-deployment)
4. [Configuration](#configuration)
5. [Monitoring Setup](#monitoring-setup)
6. [Security Hardening](#security-hardening)
7. [Scaling & Performance](#scaling--performance)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

#### Minimum Requirements
- **CPU**: 2 vCPU cores
- **Memory**: 4GB RAM
- **Storage**: 50GB SSD
- **Network**: 1Gbps connection
- **OS**: Linux (Ubuntu 20.04+ recommended)

#### Recommended Production Requirements
- **CPU**: 4+ vCPU cores
- **Memory**: 8GB+ RAM
- **Storage**: 100GB+ SSD with backup
- **Network**: High-bandwidth connection
- **Load Balancer**: For multi-instance deployment

#### Software Dependencies
- Docker 24.0+ and Docker Compose 2.0+
- PostgreSQL 15+ (managed service recommended)
- Redis 7+ (managed service recommended)
- Git 2.30+
- Python 3.11+ (for development)

### External Service Requirements

#### GitHub Configuration
- GitHub Personal Access Token with repository permissions
- Webhook secret for secure event processing
- Repository admin access for automation

#### Optional Integrations
- OpenAI API key for enhanced feature detection
- Sentry DSN for error monitoring
- SMTP server for notifications

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/ADHDo.git
cd ADHDo

# Create environment configuration
cp .env.example .env.github-automation

# Edit configuration
nano .env.github-automation
```

### 2. Basic Configuration

```bash
# .env.github-automation
ENVIRONMENT=production
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://adhd:secure_password@localhost:5432/adhd_automation
REDIS_URL=redis://localhost:6379/0

# GitHub Integration
GITHUB_TOKEN=ghp_your_token_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
OPENAI_API_KEY=sk-your_openai_key_here

# Security
JWT_SECRET=your_jwt_secret_here
SECURE_SSL_REDIRECT=true

# Automation Settings
AUTOMATION_MAX_CONCURRENT_ACTIONS=10
AUTOMATION_MIN_CONFIDENCE_AUTO_CLOSE=0.85
```

### 3. Deploy with Docker Compose

```bash
# Deploy the GitHub automation system
docker-compose -f docker-compose.github-automation.yml up -d

# Check service status
docker-compose -f docker-compose.github-automation.yml ps

# View logs
docker-compose -f docker-compose.github-automation.yml logs -f github-automation
```

### 4. Verify Installation

```bash
# Health check
curl http://localhost:8000/api/github/health

# API documentation
open http://localhost:8000/docs

# Monitoring dashboard
open http://localhost:3000  # Grafana (admin/admin)
```

## Production Deployment

### 1. Infrastructure Setup

#### Option A: Single Server Deployment

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash github-automation
sudo usermod -aG docker github-automation

# Create application directories
sudo mkdir -p /opt/github-automation/{data,logs,config,backups}
sudo chown -R github-automation:github-automation /opt/github-automation

# Set up systemd service
sudo cp scripts/github-automation.service /etc/systemd/system/
sudo systemctl enable github-automation
sudo systemctl start github-automation
```

#### Option B: Container Orchestration (Docker Swarm)

```bash
# Initialize Docker Swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.github-automation.yml github-automation

# Monitor deployment
docker service ls
docker service logs github-automation_github-automation
```

#### Option C: Kubernetes Deployment

```yaml
# kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: github-automation

---
# kubernetes/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: github-automation-config
  namespace: github-automation
data:
  ENVIRONMENT: "production"
  AUTOMATION_MAX_CONCURRENT_ACTIONS: "10"

---
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: github-automation
  namespace: github-automation
spec:
  replicas: 3
  selector:
    matchLabels:
      app: github-automation
  template:
    metadata:
      labels:
        app: github-automation
    spec:
      containers:
      - name: github-automation
        image: adhdo/github-automation:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: github-automation-config
        - secretRef:
            name: github-automation-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1500m"
        livenessProbe:
          httpGet:
            path: /api/github/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/github/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# kubernetes/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: github-automation-service
  namespace: github-automation
spec:
  selector:
    app: github-automation
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 2. Database Setup

#### PostgreSQL Configuration

```sql
-- Create database and user
CREATE DATABASE adhd_automation;
CREATE USER github_automation WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE adhd_automation TO github_automation;

-- Performance tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
SELECT pg_reload_conf();
```

#### Redis Configuration

```bash
# redis.conf optimizations
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000

# Enable AOF for durability
appendonly yes
appendfsync everysec
```

### 3. SSL/TLS Configuration

#### Let's Encrypt with Traefik

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  traefik:
    command:
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    labels:
      - "traefik.http.routers.github-automation.tls.certresolver=letsencrypt"
      - "traefik.http.routers.github-automation.rule=Host(`automation.yourdomain.com`)"
```

#### Manual SSL Certificate

```bash
# Generate self-signed certificate for testing
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=automation.yourdomain.com"

# Or use existing certificates
cp /path/to/your/cert.pem nginx/ssl/
cp /path/to/your/key.pem nginx/ssl/
```

## Configuration

### Environment Variables

#### Core Application Settings
```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Workers
WORKERS=4
MAX_WORKERS=8
WORKER_CLASS=uvicorn.workers.UvicornWorker
TIMEOUT=120
```

#### Database Configuration
```bash
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Redis
REDIS_URL=redis://host:6379/0
REDIS_PASSWORD=secure_password
REDIS_POOL_SIZE=20
```

#### GitHub Integration
```bash
# Authentication
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# API Configuration
GITHUB_API_BASE_URL=https://api.github.com
GITHUB_MAX_RETRIES=3
GITHUB_TIMEOUT=30

# Automation Behavior
AUTOMATION_ENABLED=true
AUTOMATION_MAX_CONCURRENT_ACTIONS=10
AUTOMATION_BATCH_SIZE=50
AUTOMATION_MIN_CONFIDENCE_AUTO_CLOSE=0.85
AUTOMATION_MIN_CONFIDENCE_AUTO_LABEL=0.70
```

#### Performance Tuning
```bash
# Caching
CACHE_DEFAULT_TTL=3600
CACHE_MAX_SIZE_MB=512
CACHE_COMPRESSION_ENABLED=true

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_HOUR=4000
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST_SIZE=20
```

### Security Configuration

#### JWT and Session Management
```bash
# Security
JWT_SECRET=your-256-bit-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Session Security
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=lax
```

#### CORS Configuration
```bash
# CORS Settings
CORS_ORIGINS=["https://yourdomain.com", "https://automation.yourdomain.com"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
```

## Monitoring Setup

### 1. Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'github-automation'
    static_configs:
      - targets: ['github-automation:8000']
    scrape_interval: 10s
    metrics_path: '/metrics'
    
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']
      
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 2. Grafana Dashboard Setup

```bash
# Import pre-built dashboard
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana/dashboards/github-automation-dashboard.json

# Configure data sources
curl -X POST http://admin:admin@localhost:3000/api/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Prometheus",
    "type": "prometheus",
    "url": "http://prometheus:9090",
    "access": "proxy",
    "isDefault": true
  }'
```

### 3. Alert Rules

```yaml
# monitoring/alert_rules.yml
groups:
  - name: github_automation_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(github_automation_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate in GitHub automation"
          description: "Error rate is {{ $value }} errors per second"
          
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(github_automation_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High request latency"
          description: "95th percentile latency is {{ $value }} seconds"
          
      - alert: GitHubRateLimitLow
        expr: github_automation_rate_limit_remaining < 100
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "GitHub API rate limit running low"
          description: "Only {{ $value }} API calls remaining"
```

### 4. Log Aggregation (ELK Stack)

```yaml
# docker-compose.logging.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
      
  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
    depends_on:
      - elasticsearch
      
  filebeat:
    image: docker.elastic.co/beats/filebeat:8.5.0
    volumes:
      - ./logs:/var/log/app:ro
      - ./monitoring/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
    depends_on:
      - elasticsearch
```

## Security Hardening

### 1. Container Security

```dockerfile
# Use specific, minimal base image
FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Security hardening
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set security-related environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV SECURE_SSL_REDIRECT=true
ENV SESSION_COOKIE_SECURE=true

# Switch to non-root user
USER appuser
```

### 2. Network Security

```yaml
# Docker network isolation
networks:
  frontend:
    driver: bridge
    internal: false
  backend:
    driver: bridge
    internal: true
  database:
    driver: bridge
    internal: true

services:
  github-automation:
    networks:
      - frontend
      - backend
  postgres:
    networks:
      - database
      - backend
```

### 3. Secrets Management

```bash
# Use Docker secrets or external secret management
echo "your_secret_here" | docker secret create github_token -

# Or use HashiCorp Vault
export VAULT_ADDR="https://vault.company.com"
export VAULT_TOKEN="s.xxxxx"
vault kv put secret/github-automation \
  github_token="ghp_xxxx" \
  webhook_secret="secret123"
```

### 4. Security Scanning

```bash
# Container vulnerability scanning
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image adhdo/github-automation:latest

# Static security analysis
bandit -r src/github_automation/
safety check requirements.txt
```

## Scaling & Performance

### 1. Horizontal Scaling

#### Load Balancer Configuration
```nginx
# nginx.conf
upstream github_automation {
    least_conn;
    server github-automation-1:8000 max_fails=3 fail_timeout=30s;
    server github-automation-2:8000 max_fails=3 fail_timeout=30s;
    server github-automation-3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name automation.yourdomain.com;
    
    location / {
        proxy_pass http://github_automation;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Performance optimizations
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

#### Auto-scaling with Docker Swarm
```yaml
version: '3.8'
services:
  github-automation:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      placement:
        constraints:
          - node.role == worker
        preferences:
          - spread: node.labels.zone
```

### 2. Database Optimization

#### PostgreSQL Performance Tuning
```sql
-- Connection pooling
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';

-- Query optimization
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET seq_page_cost = 1.0;
ALTER SYSTEM SET cpu_tuple_cost = 0.01;
ALTER SYSTEM SET cpu_index_tuple_cost = 0.005;

-- WAL optimization
ALTER SYSTEM SET wal_buffers = '32MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET max_wal_size = '2GB';

-- Enable query statistics
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
SELECT pg_reload_conf();
```

#### Redis Optimization
```bash
# redis.conf for performance
# Memory optimization
maxmemory 2gb
maxmemory-policy allkeys-lru
maxmemory-samples 10

# Persistence optimization
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes

# Network optimization
tcp-keepalive 300
tcp-backlog 511
timeout 300

# Threading
io-threads 4
io-threads-do-reads yes
```

### 3. Application Performance

#### Caching Strategy
```python
# Cache configuration for high performance
CACHE_CONFIG = {
    'default_ttl_seconds': 3600,
    'max_memory_mb': 1024,
    'compression_enabled': True,
    'compression_threshold_bytes': 1024,
    'key_prefix': 'github_automation_v1',
    'redis_url': 'redis://redis-cluster:6379'
}

# Performance-optimized cache keys
CACHE_KEYS = {
    'repository_issues': 'repo:{owner}:{name}:issues:{state}',
    'issue_details': 'issue:{owner}:{name}:{number}',
    'feature_detection': 'feature:{issue_id}:{version}',
    'rate_limits': 'ratelimit:{endpoint}:{hour}'
}
```

#### Background Job Processing
```python
# Celery configuration for scalability
CELERY_CONFIG = {
    'broker_url': 'redis://redis:6379/1',
    'result_backend': 'redis://redis:6379/2',
    'worker_concurrency': 4,
    'worker_prefetch_multiplier': 1,
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'task_routes': {
        'github_automation.tasks.analyze_repository': {'queue': 'analysis'},
        'github_automation.tasks.execute_actions': {'queue': 'actions'},
        'github_automation.tasks.webhook_processing': {'queue': 'webhooks'}
    }
}
```

## Troubleshooting

### 1. Common Issues

#### Database Connection Issues
```bash
# Check database connectivity
docker exec -it github-automation-postgres psql -U adhd -d adhd_automation -c "SELECT 1;"

# Check connection pool status
curl http://localhost:8000/api/github/metrics/detailed | jq '.database'

# Fix: Increase connection limits
# In .env file:
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=50
```

#### Redis Connection Issues
```bash
# Test Redis connection
docker exec -it github-automation-redis redis-cli ping

# Check memory usage
docker exec -it github-automation-redis redis-cli info memory

# Fix: Increase Redis memory or adjust policy
# In redis.conf:
maxmemory 1gb
maxmemory-policy allkeys-lru
```

#### GitHub API Rate Limiting
```bash
# Check current rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit

# Monitor rate limit metrics
curl http://localhost:8000/api/github/metrics/summary | jq '.rate_limiting'

# Fix: Implement intelligent rate limiting
RATE_LIMIT_BUFFER=0.8
RATE_LIMIT_ADAPTIVE=true
```

### 2. Performance Issues

#### High Response Times
```bash
# Check application metrics
curl http://localhost:8000/metrics | grep response_time

# Check database slow queries
docker exec -it postgres psql -U adhd -d adhd_automation -c "
  SELECT query, mean_time, calls 
  FROM pg_stat_statements 
  ORDER BY mean_time DESC LIMIT 10;"

# Fix: Optimize queries and add indexes
CREATE INDEX CONCURRENTLY idx_github_issues_repo_status 
ON github_issues (repository_owner, repository_name, status);
```

#### Memory Issues
```bash
# Check container memory usage
docker stats github-automation

# Check application memory usage
curl http://localhost:8000/api/github/health | jq '.memory'

# Fix: Optimize memory settings
WORKERS=2  # Reduce if memory constrained
CACHE_MAX_SIZE_MB=256  # Reduce cache size
```

### 3. Debugging Tools

#### Application Logs
```bash
# View real-time logs
docker-compose -f docker-compose.github-automation.yml logs -f

# Search logs for specific errors
docker-compose logs github-automation 2>&1 | grep -i error

# Export logs for analysis
docker-compose logs --since=1h github-automation > debug.log
```

#### Health Checks
```bash
# Comprehensive health check
curl -s http://localhost:8000/api/github/health | jq '.'

# Database health
curl -s http://localhost:8000/health/detailed | jq '.components.database'

# Redis health
curl -s http://localhost:8000/health/detailed | jq '.components.redis'
```

#### Performance Profiling
```bash
# Enable performance profiling
export ENABLE_PROFILING=true
export PROFILING_OUTPUT_DIR=/app/logs/profiling

# Analyze performance data
docker exec github-automation py-spy top --pid 1 --duration 30
```

### 4. Disaster Recovery

#### Backup Procedures
```bash
#!/bin/bash
# backup.sh - Daily backup script

# Database backup
docker exec postgres pg_dump -U adhd adhd_automation | gzip > backup_$(date +%Y%m%d).sql.gz

# Redis backup
docker exec redis redis-cli --rdb /data/backup_$(date +%Y%m%d).rdb

# Configuration backup
tar -czf config_backup_$(date +%Y%m%d).tar.gz .env docker-compose.yml monitoring/

# Upload to S3 (optional)
aws s3 cp backup_$(date +%Y%m%d).sql.gz s3://backups/github-automation/
```

#### Recovery Procedures
```bash
# Restore database
gunzip < backup_20240806.sql.gz | docker exec -i postgres psql -U adhd adhd_automation

# Restore Redis
docker cp backup_20240806.rdb redis:/data/dump.rdb
docker restart redis

# Restart services
docker-compose -f docker-compose.github-automation.yml down
docker-compose -f docker-compose.github-automation.yml up -d
```

## Maintenance

### 1. Regular Tasks

#### Weekly Maintenance
```bash
#!/bin/bash
# weekly_maintenance.sh

# Update containers
docker-compose pull
docker-compose up -d

# Clean unused resources
docker system prune -f

# Backup data
./backup.sh

# Check logs for errors
docker-compose logs --since=7d | grep -i error > weekly_errors.log
```

#### Monthly Maintenance
```bash
#!/bin/bash
# monthly_maintenance.sh

# Update base system
sudo apt update && sudo apt upgrade -y

# Rotate logs
logrotate /etc/logrotate.d/github-automation

# Check disk usage
df -h
docker system df

# Security updates
./security_scan.sh
```

### 2. Monitoring and Alerting

#### Health Monitoring Script
```bash
#!/bin/bash
# health_monitor.sh

HEALTH_URL="http://localhost:8000/api/github/health"
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -ne 200 ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 GitHub Automation System is down!"}' \
        $WEBHOOK_URL
fi
```

#### Performance Monitoring
```python
# monitor_performance.py
import requests
import time

def check_performance():
    """Monitor key performance metrics."""
    metrics_url = "http://localhost:8000/api/github/metrics/summary"
    
    try:
        response = requests.get(metrics_url, timeout=10)
        metrics = response.json()
        
        # Check key metrics
        success_rate = metrics['summary']['success_rate']
        avg_response_time = metrics['summary']['average_processing_time_ms']
        
        if success_rate < 0.95:
            send_alert(f"Low success rate: {success_rate:.2%}")
            
        if avg_response_time > 1000:
            send_alert(f"High response time: {avg_response_time:.0f}ms")
            
    except Exception as e:
        send_alert(f"Performance monitoring failed: {str(e)}")

def send_alert(message):
    """Send alert to monitoring system."""
    print(f"ALERT: {message}")
    # Implement your alerting logic here

if __name__ == "__main__":
    check_performance()
```

---

## Summary

This deployment guide provides comprehensive instructions for deploying the GitHub Issue Automation System in production environments. The system is designed for enterprise-scale operations with built-in monitoring, security, and scalability features.

**Key deployment features:**
- ✅ Production-ready Docker configuration
- ✅ Comprehensive monitoring and alerting
- ✅ Security hardening and best practices
- ✅ Horizontal and vertical scaling options
- ✅ Disaster recovery procedures
- ✅ Performance optimization guidelines

For technical support or advanced deployment scenarios, contact the CODEFORGE Systems Architecture team.

**Building the future, one line of code at a time.**