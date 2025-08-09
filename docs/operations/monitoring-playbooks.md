# Monitoring and Alerting Playbooks
## MCP ADHD Server - Operational Excellence Guide

**Document Version:** 1.0  
**Last Updated:** 2025-08-09  
**Purpose:** Comprehensive monitoring, alerting, and troubleshooting procedures

---

## 🎯 Monitoring Philosophy

### ADHD-First Monitoring Approach
- **Performance Impact:** Every metric evaluated for ADHD user experience
- **Crisis Detection:** Highest priority monitoring for user safety
- **Attention Optimization:** Sub-3 second response time requirements
- **Proactive Intervention:** Prevent attention disruption before it occurs

### Monitoring Hierarchy
1. **Critical:** User safety and crisis detection
2. **High:** ADHD performance thresholds (< 3s response)
3. **Medium:** System health and availability
4. **Low:** Optimization and efficiency metrics

---

## 📊 Key Performance Indicators (KPIs)

### ADHD-Critical Metrics

#### Response Time Performance
- **Target:** < 1 second (optimal ADHD experience)
- **Warning:** 1-3 seconds (acceptable ADHD experience)
- **Critical:** > 3 seconds (attention disruption risk)
- **Emergency:** > 5 seconds (severe user impact)

```bash
# Monitor response times
curl http://localhost:8000/api/metrics/response-times | jq '.adhd_performance'

# Check ADHD performance grade
curl http://localhost:8000/api/performance/adhd-grade
```

#### Database Query Performance
- **Target:** < 50ms (optimal attention preservation)
- **Warning:** 50-100ms (acceptable performance)
- **Critical:** 100-250ms (attention impact risk)
- **Emergency:** > 250ms (severe disruption)

```bash
# Database performance overview
curl http://localhost:8000/api/database/performance | jq '.adhd_impact_analysis'

# Slow query analysis
curl http://localhost:8000/api/database/slow-queries?threshold=100
```

#### Context Assembly Performance
- **Target:** < 25ms (instant context switching)
- **Warning:** 25-50ms (minor delay)
- **Critical:** 50-100ms (noticeable lag)
- **Emergency:** > 100ms (context switching failure)

```bash
# Context assembly metrics
curl http://localhost:8000/api/context/performance-metrics

# Frame building analysis
curl http://localhost:8000/api/frames/build-performance
```

### System Health Metrics

#### Availability Targets
- **Crisis Support System:** 99.99% uptime (critical for user safety)
- **Core Application:** 99.9% uptime
- **Non-critical Features:** 99.5% uptime

#### Resource Utilization
- **CPU Usage:** < 70% average, < 85% peak
- **Memory Usage:** < 80% average, < 90% peak
- **Database Connections:** < 80% pool utilization
- **Redis Memory:** < 75% of allocated memory

---

## 🚨 Alert Configuration

### Alert Severity Levels

#### Level 0: Emergency (Immediate Response)
**Response Time:** < 1 minute  
**Escalation:** All on-call engineers + Crisis coordinator

**Triggers:**
- System completely unresponsive (> 30 seconds)
- Crisis detection system failure
- Database unavailable
- Security breach in progress

```yaml
# Emergency Alert Configuration
alert_rules:
  - name: system_unresponsive
    condition: response_time > 30s for 30s
    severity: emergency
    notification: all_oncall

  - name: crisis_system_down
    condition: crisis_endpoint_error_rate > 1% for 10s
    severity: emergency
    notification: crisis_coordinator
```

#### Level 1: Critical (High Priority Response)
**Response Time:** < 5 minutes  
**Escalation:** Primary on-call engineer

**Triggers:**
- Response time > 5 seconds for 2 minutes
- Database query time > 250ms average
- Error rate > 5%
- Memory usage > 90%

```yaml
alert_rules:
  - name: adhd_critical_performance
    condition: avg_response_time > 5s for 2m
    severity: critical
    description: "ADHD user experience severely impacted"

  - name: database_critical_slow
    condition: avg_db_query_time > 250ms for 1m
    severity: critical
    description: "Database queries impacting ADHD attention"
```

#### Level 2: High (Standard Response)
**Response Time:** < 15 minutes  
**Escalation:** Primary on-call engineer

**Triggers:**
- Response time > 3 seconds for 5 minutes
- Database query time > 100ms average
- CPU usage > 85% for 5 minutes
- Security events > 10/minute

```yaml
alert_rules:
  - name: adhd_performance_warning
    condition: avg_response_time > 3s for 5m
    severity: high
    description: "ADHD attention threshold exceeded"

  - name: database_attention_impact
    condition: avg_db_query_time > 100ms for 3m
    severity: high
    description: "Database performance affecting ADHD users"
```

#### Level 3: Medium (Monitoring Response)
**Response Time:** < 1 hour  
**Escalation:** During business hours

**Triggers:**
- Response time > 1 second for 10 minutes
- Memory usage > 80% for 10 minutes
- Disk usage > 85%
- Failed login attempts > 50/hour

---

## 📋 Alert Investigation Playbooks

### Performance Alert Playbook

#### Step 1: Initial Assessment
**Time Allocation:** 2-3 minutes

```bash
# Quick system overview
curl http://localhost:8000/health/detailed | jq '.summary'

# Current performance metrics
curl http://localhost:8000/api/performance/current | jq '.'

# ADHD impact assessment
curl http://localhost:8000/api/performance/adhd-impact
```

**Key Questions:**
- Is the issue affecting ADHD users specifically?
- What's the current response time trend?
- Are there any obvious system resource constraints?

#### Step 2: Deep Dive Analysis  
**Time Allocation:** 5-10 minutes

```bash
# Database performance analysis
curl http://localhost:8000/api/database/performance | jq '.performance_summary'

# Slow query identification
curl http://localhost:8000/api/database/slow-queries?limit=10

# Memory and CPU analysis
curl http://localhost:8000/api/performance/resources

# Connection pool status
curl http://localhost:8000/api/database/pool-status
```

**Analysis Focus:**
- Identify bottleneck (database, CPU, memory, network)
- Determine if issue is query-specific or system-wide
- Check for recent changes or deployments

#### Step 3: Immediate Mitigation
**Time Allocation:** 2-5 minutes

```bash
# If database issue - optimize connections
curl -X POST http://localhost:8000/api/database/optimize

# If memory issue - clear caches
curl -X POST http://localhost:8000/api/cache/clear-non-essential

# If CPU issue - enable performance mode
curl -X POST http://localhost:8000/api/performance/emergency-mode

# Scale resources if available
kubectl scale deployment mcp-adhd-server --replicas=3
```

#### Step 4: Verification and Monitoring
**Time Allocation:** 5-10 minutes

```bash
# Verify improvement
watch -n 10 'curl -s http://localhost:8000/api/performance/current | jq ".avg_response_time_ms"'

# Monitor ADHD impact
curl http://localhost:8000/api/performance/adhd-grade

# Check for new issues
curl http://localhost:8000/api/alerts/active
```

### Database Alert Playbook

#### Query Performance Investigation

```sql
-- Identify current long-running queries
SELECT 
    pid, 
    now() - pg_stat_activity.query_start AS duration, 
    query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '1 minute'
ORDER BY duration DESC;

-- Check for blocking queries
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;

-- Analyze query statistics
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    stddev_time
FROM pg_stat_statements 
WHERE mean_time > 100  -- ADHD attention threshold
ORDER BY mean_time DESC 
LIMIT 20;
```

#### Database Connection Investigation

```bash
# Check connection pool utilization
curl http://localhost:8000/api/database/connections | jq '.utilization_percent'

# Active connections analysis
psql -d mcp_adhd -c "
SELECT 
    state,
    COUNT(*) as connection_count,
    AVG(EXTRACT(EPOCH FROM (now() - state_change))) as avg_duration
FROM pg_stat_activity 
WHERE state IS NOT NULL 
GROUP BY state 
ORDER BY connection_count DESC;"

# Connection pool health check
curl http://localhost:8000/api/database/pool-health
```

### Security Alert Playbook

#### Security Event Investigation

```bash
# Recent security events
curl http://localhost:8000/api/security/events?severity=high&limit=20

# IP address analysis
curl "http://localhost:8000/api/security/analyze-ip?ip=$SUSPICIOUS_IP"

# Failed authentication patterns
curl http://localhost:8000/api/security/failed-auth-analysis

# Rate limiting status
curl http://localhost:8000/api/security/rate-limits/status
```

#### Threat Assessment Process

1. **Immediate Threat Level Assessment:**
   ```bash
   # Check for active threats
   curl http://localhost:8000/api/security/threat-level
   
   # Review recent authentication failures
   curl http://localhost:8000/api/security/auth-failures?window=1h
   ```

2. **Pattern Analysis:**
   ```bash
   # Geographic analysis of requests
   curl http://localhost:8000/api/security/geo-analysis
   
   # User agent analysis for bots
   curl http://localhost:8000/api/security/user-agent-analysis
   ```

3. **Impact Assessment:**
   ```bash
   # Check for successful breaches
   curl http://localhost:8000/api/security/breach-indicators
   
   # Verify data integrity
   curl http://localhost:8000/api/security/data-integrity-check
   ```

---

## 📈 Performance Optimization Playbooks

### ADHD Performance Optimization

#### Context Assembly Optimization
```bash
# Analyze context building performance
curl http://localhost:8000/api/context/performance-analysis

# Identify slow context queries
curl http://localhost:8000/api/context/slow-queries

# Optimize context caching
curl -X POST http://localhost:8000/api/context/optimize-caching
```

#### Task Loading Optimization  
```bash
# Task query performance analysis
curl http://localhost:8000/api/tasks/performance-metrics

# Identify N+1 query patterns
curl http://localhost:8000/api/database/n-plus-one-detection

# Apply task loading optimizations
curl -X POST http://localhost:8000/api/tasks/optimize-loading
```

#### Memory Management for ADHD Workloads
```bash
# Memory usage by ADHD features
curl http://localhost:8000/api/memory/adhd-breakdown

# Clear ADHD-safe caches (preserving critical context)
curl -X POST http://localhost:8000/api/cache/clear-adhd-safe

# Optimize memory for attention patterns
curl -X POST http://localhost:8000/api/memory/optimize-adhd
```

### Database Optimization Procedures

#### Index Optimization
```bash
# Generate index recommendations
curl http://localhost:8000/api/database/index-recommendations

# Create ADHD-critical indexes
curl -X POST http://localhost:8000/api/database/create-adhd-indexes

# Analyze index usage
curl http://localhost:8000/api/database/index-usage-analysis
```

#### Query Optimization
```bash
# Run query optimization analysis
curl http://localhost:8000/api/database/query-optimization

# Apply recommended optimizations
curl -X POST http://localhost:8000/api/database/apply-optimizations

# Validate optimization impact
curl http://localhost:8000/api/database/optimization-results
```

---

## 🔍 Troubleshooting Decision Trees

### Performance Issue Decision Tree

```
Response Time > 3 seconds?
├─ Yes → Check Database Performance
│  ├─ DB Queries > 100ms?
│  │  ├─ Yes → Run Database Optimization Playbook
│  │  └─ No → Check Application Performance
│  │     ├─ High CPU? → Scale Resources
│  │     ├─ High Memory? → Clear Caches
│  │     └─ Network Issues? → Check Load Balancer
│  └─ No → Monitor and Document
└─ No → Check for Warning Patterns
   ├─ Response Time 1-3s? → Preventive Optimization
   └─ Response Time < 1s? → Normal Operation
```

### ADHD User Impact Decision Tree

```
User Experience Impact Detected?
├─ Critical (>5s response) → Emergency Response
│  ├─ Crisis System Affected? → Immediate Escalation
│  └─ General Performance → Performance Emergency
├─ High (3-5s response) → High Priority Response
│  ├─ Database Issue? → DB Optimization
│  ├─ Resource Issue? → Resource Scaling
│  └─ Application Issue? → Application Optimization
└─ Medium (1-3s response) → Standard Optimization
   ├─ Query Optimization
   ├─ Cache Optimization
   └─ Proactive Monitoring
```

---

## 📊 Monitoring Dashboard Configuration

### ADHD-Critical Dashboard Panels

#### Panel 1: User Experience Overview
```yaml
dashboard_panel:
  title: "ADHD User Experience"
  metrics:
    - avg_response_time_adhd_users
    - attention_disruption_events
    - crisis_support_availability
    - context_assembly_speed
  alerts:
    - response_time_exceeds_3s
    - attention_threshold_breach
```

#### Panel 2: System Performance
```yaml
dashboard_panel:
  title: "System Performance"
  metrics:
    - database_query_performance
    - memory_utilization
    - cpu_utilization
    - connection_pool_status
  alerts:
    - database_slow_queries
    - resource_exhaustion
```

#### Panel 3: Security Monitoring
```yaml
dashboard_panel:
  title: "Security Status"
  metrics:
    - failed_authentication_rate
    - security_events_by_severity
    - rate_limiting_effectiveness
    - threat_detection_status
  alerts:
    - security_breach_detected
    - threat_level_elevated
```

### Alert Dashboard Configuration

```yaml
alert_dashboard:
  title: "MCP ADHD Server Alerts"
  sections:
    - name: "Critical Alerts"
      filter: "severity:emergency OR severity:critical"
      auto_refresh: 10s
    
    - name: "ADHD Impact Alerts"
      filter: "tags:adhd_impact"
      auto_refresh: 30s
    
    - name: "Performance Alerts"
      filter: "category:performance"
      auto_refresh: 60s
```

---

## 🔧 Maintenance Procedures

### Routine Health Checks

#### Daily Health Check
```bash
#!/bin/bash
# Daily ADHD Server Health Check

echo "=== MCP ADHD Server Daily Health Check ==="
date

# Basic system health
curl -s http://localhost:8000/health | jq '.status'

# ADHD performance metrics
curl -s http://localhost:8000/api/performance/adhd-summary | jq '.'

# Database health
curl -s http://localhost:8000/api/database/health | jq '.performance_grade'

# Security status
curl -s http://localhost:8000/api/security/daily-summary | jq '.'

# Crisis support system check
curl -s http://localhost:8000/api/crisis/system-check | jq '.'

echo "=== Health Check Complete ==="
```

#### Weekly Performance Review
```bash
#!/bin/bash
# Weekly Performance Analysis

echo "=== Weekly ADHD Performance Review ==="

# Generate performance report
curl -s http://localhost:8000/api/reports/weekly-performance > weekly_performance_report.json

# Database optimization analysis
curl -s http://localhost:8000/api/database/weekly-analysis > weekly_db_analysis.json

# ADHD user experience metrics
curl -s http://localhost:8000/api/adhd/weekly-metrics > weekly_adhd_metrics.json

# Security events summary
curl -s http://localhost:8000/api/security/weekly-summary > weekly_security_summary.json

echo "Reports generated - review for optimization opportunities"
```

### Preventive Maintenance

#### Monthly Optimization Tasks
```bash
#!/bin/bash
# Monthly System Optimization

# Database maintenance
psql -d mcp_adhd -c "VACUUM ANALYZE;"
psql -d mcp_adhd -c "REINDEX DATABASE mcp_adhd;"

# Performance optimization
curl -X POST http://localhost:8000/api/database/monthly-optimization

# Security audit
curl -X POST http://localhost:8000/api/security/monthly-audit

# Cache optimization
curl -X POST http://localhost:8000/api/cache/monthly-optimization

# Generate optimization report
curl -s http://localhost:8000/api/reports/monthly-optimization > monthly_optimization_report.json
```

---

## 📝 Alert Response Documentation

### Response Time Logging
```bash
# Log alert response
echo "$(date): Alert $ALERT_ID - Response started by $USER" >> /var/log/alert-responses.log

# Log resolution
echo "$(date): Alert $ALERT_ID - Resolved. Duration: $DURATION. Actions: $ACTIONS" >> /var/log/alert-responses.log
```

### Post-Alert Analysis
```bash
# Generate post-alert analysis
curl -X POST http://localhost:8000/api/alerts/post-analysis \
  -d '{"alert_id": "'$ALERT_ID'", "response_time": "'$RESPONSE_TIME'", "actions_taken": "'$ACTIONS'"}'

# Update alert thresholds if needed
curl -X POST http://localhost:8000/api/alerts/optimize-thresholds \
  -d '{"alert_type": "'$ALERT_TYPE'", "false_positive": false}'
```

---

**Remember:** ADHD users depend on consistent, fast, and reliable system performance. Every alert represents a potential impact on vulnerable users who need reliable support systems.