# Backup and Recovery Procedures
## MCP ADHD Server - Data Protection and Business Continuity

**Document Version:** 1.0  
**Last Updated:** 2025-08-09  
**Purpose:** Comprehensive backup, recovery, and disaster recovery procedures

---

## 🎯 Backup Strategy Overview

### ADHD-Critical Data Classification

#### Priority 1: Critical ADHD Support Data
- **User profiles and ADHD configurations**
- **Active tasks and context data**
- **Crisis support session data**
- **Authentication and security data**
- **RPO:** 5 minutes, **RTO:** 15 minutes

#### Priority 2: Important Operational Data
- **Task history and completion patterns**
- **System performance metrics**
- **User interaction traces**
- **Integration configurations**
- **RPO:** 1 hour, **RTO:** 2 hours

#### Priority 3: Analytical and Historical Data
- **Long-term user analytics**
- **Performance trend data**
- **Audit logs (older than 30 days)**
- **RPO:** 24 hours, **RTO:** 8 hours

### Backup Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Backup Architecture                       │
├─────────────────────────────────────────────────────────────┤
│  Production Database (Primary)                              │
│  ├─ Streaming Replication → Hot Standby (5-second lag)      │
│  ├─ WAL-E Archive → S3/Object Storage (1-minute intervals)  │
│  └─ pg_dump → Nightly Full Backups                         │
│                                                             │
│  Redis Cache                                                │
│  ├─ RDB Snapshots → Every 5 minutes                        │
│  └─ AOF Logs → Real-time append-only logs                  │
│                                                             │
│  Application Data                                           │
│  ├─ Configuration Files → Git + S3                         │
│  ├─ Log Files → Centralized logging + S3 archive           │
│  └─ Static Assets → CDN + S3 backup                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Backup Procedures

### Automated Database Backups

#### Continuous Backup (WAL-E/WAL-G)
```bash
#!/bin/bash
# /etc/cron.d/wal-backup
# Runs every minute for critical ADHD data protection

# WAL-E backup configuration
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export WALE_S3_PREFIX="s3://mcp-adhd-backups/wal"

# Archive WAL files
/usr/local/bin/wal-e wal-push $1

# Verify backup integrity (ADHD-critical)
if [ $? -eq 0 ]; then
    echo "$(date): WAL backup successful" >> /var/log/backup-status.log
else
    echo "$(date): CRITICAL - WAL backup failed" >> /var/log/backup-status.log
    # Alert for ADHD data protection failure
    curl -X POST http://localhost:8000/api/alerts/critical \
        -d '{"type":"backup_failure","severity":"critical","message":"WAL backup failed - ADHD data at risk"}'
fi
```

#### Daily Full Backups
```bash
#!/bin/bash
# /scripts/daily-backup.sh
# Daily comprehensive backup for ADHD server

set -e

BACKUP_DIR="/backups/daily"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="mcp_adhd_full_${DATE}.sql"

echo "$(date): Starting daily backup for ADHD server"

# Create backup directory
mkdir -p ${BACKUP_DIR}

# Full database backup with ADHD-critical consistency
pg_dump \
    --host=localhost \
    --port=5432 \
    --username=postgres \
    --dbname=mcp_adhd \
    --format=custom \
    --compress=9 \
    --verbose \
    --file="${BACKUP_DIR}/${BACKUP_FILE}"

# Verify backup integrity
pg_restore --list "${BACKUP_DIR}/${BACKUP_FILE}" > /dev/null

if [ $? -eq 0 ]; then
    echo "$(date): Daily backup completed successfully: ${BACKUP_FILE}"
    
    # Upload to S3 for off-site storage
    aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://mcp-adhd-backups/daily/" --storage-class STANDARD_IA
    
    # Update backup status
    curl -X POST http://localhost:8000/api/backup/status \
        -d '{"type":"daily_full","status":"success","file":"'${BACKUP_FILE}'","timestamp":"'$(date -Iseconds)'"}'
    
    # Clean up old local backups (keep 7 days)
    find ${BACKUP_DIR} -name "*.sql" -mtime +7 -delete
    
else
    echo "$(date): CRITICAL - Daily backup verification failed"
    curl -X POST http://localhost:8000/api/alerts/critical \
        -d '{"type":"backup_verification_failure","severity":"critical","message":"Daily backup verification failed"}'
    exit 1
fi

echo "$(date): Daily backup process completed"
```

#### Hourly Incremental Backups (Business Hours)
```bash
#!/bin/bash
# /scripts/hourly-backup.sh
# Hourly incremental backup during business hours (9 AM - 6 PM)

HOUR=$(date +%H)

# Only run during business hours when ADHD users are most active
if [ $HOUR -ge 9 ] && [ $HOUR -le 18 ]; then
    echo "$(date): Starting hourly incremental backup"
    
    # Get the latest WAL sequence number
    LATEST_WAL=$(psql -h localhost -U postgres -d mcp_adhd -t -c "SELECT pg_current_wal_lsn();")
    
    # Create incremental backup using WAL-E
    wal-e backup-push /var/lib/postgresql/data
    
    if [ $? -eq 0 ]; then
        echo "$(date): Hourly backup successful. LSN: $LATEST_WAL"
        
        # Update backup tracking
        curl -X POST http://localhost:8000/api/backup/status \
            -d '{"type":"hourly_incremental","status":"success","lsn":"'$LATEST_WAL'","timestamp":"'$(date -Iseconds)'"}'
    else
        echo "$(date): Hourly backup failed"
        curl -X POST http://localhost:8000/api/alerts/high \
            -d '{"type":"incremental_backup_failure","severity":"high","message":"Hourly backup failed"}'
    fi
else
    echo "$(date): Outside business hours, skipping hourly backup"
fi
```

### Redis Backup Procedures

#### Redis RDB Snapshots
```bash
#!/bin/bash
# /scripts/redis-backup.sh
# Redis backup for ADHD session and cache data

REDIS_BACKUP_DIR="/backups/redis"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p ${REDIS_BACKUP_DIR}

echo "$(date): Starting Redis backup for ADHD cache data"

# Save Redis snapshot
redis-cli BGSAVE

# Wait for background save to complete
while [ $(redis-cli LASTSAVE) -eq $(redis-cli LASTSAVE) ]; do
    sleep 1
done

# Copy RDB file with timestamp
cp /var/lib/redis/dump.rdb "${REDIS_BACKUP_DIR}/dump_${DATE}.rdb"

if [ $? -eq 0 ]; then
    echo "$(date): Redis backup completed: dump_${DATE}.rdb"
    
    # Upload to S3
    aws s3 cp "${REDIS_BACKUP_DIR}/dump_${DATE}.rdb" "s3://mcp-adhd-backups/redis/"
    
    # Clean up old local backups (keep 3 days)
    find ${REDIS_BACKUP_DIR} -name "dump_*.rdb" -mtime +3 -delete
    
    # Update backup status
    curl -X POST http://localhost:8000/api/backup/status \
        -d '{"type":"redis_snapshot","status":"success","file":"dump_'${DATE}'.rdb","timestamp":"'$(date -Iseconds)'"}'
else
    echo "$(date): Redis backup failed"
    curl -X POST http://localhost:8000/api/alerts/medium \
        -d '{"type":"redis_backup_failure","severity":"medium","message":"Redis backup failed"}'
fi
```

---

## 🔄 Recovery Procedures

### Database Recovery Scenarios

#### Scenario 1: Point-in-Time Recovery (PITR)
**Use Case:** Recover from data corruption or accidental deletion

```bash
#!/bin/bash
# Point-in-time recovery for ADHD server
# Usage: ./pitr-recovery.sh "2025-08-09 10:30:00"

RECOVERY_TARGET_TIME="$1"
RECOVERY_DIR="/recovery/pitr_$(date +%Y%m%d_%H%M%S)"

if [ -z "$RECOVERY_TARGET_TIME" ]; then
    echo "Usage: $0 'YYYY-MM-DD HH:MM:SS'"
    exit 1
fi

echo "$(date): Starting point-in-time recovery to: $RECOVERY_TARGET_TIME"

# Stop PostgreSQL
systemctl stop postgresql

# Create recovery directory
mkdir -p ${RECOVERY_DIR}

# Restore base backup
echo "Restoring base backup..."
wal-e backup-fetch ${RECOVERY_DIR} LATEST

if [ $? -ne 0 ]; then
    echo "Failed to fetch base backup"
    exit 1
fi

# Create recovery configuration
cat > ${RECOVERY_DIR}/recovery.conf << EOF
standby_mode = 'off'
restore_command = 'wal-e wal-fetch %f %p'
recovery_target_time = '${RECOVERY_TARGET_TIME}'
recovery_target_action = 'promote'
EOF

# Set correct permissions
chown -R postgres:postgres ${RECOVERY_DIR}
chmod 700 ${RECOVERY_DIR}

# Update PostgreSQL data directory
mv /var/lib/postgresql/data /var/lib/postgresql/data.backup.$(date +%Y%m%d_%H%M%S)
mv ${RECOVERY_DIR} /var/lib/postgresql/data

# Start PostgreSQL in recovery mode
systemctl start postgresql

# Wait for recovery completion
echo "Waiting for recovery to complete..."
sleep 30

# Verify recovery
psql -h localhost -U postgres -d mcp_adhd -c "SELECT 'Recovery successful - ADHD data restored';"

if [ $? -eq 0 ]; then
    echo "$(date): Point-in-time recovery completed successfully"
    
    # Verify ADHD-critical data integrity
    echo "Verifying ADHD-critical data..."
    psql -h localhost -U postgres -d mcp_adhd -c "
        SELECT 
            'Users: ' || COUNT(*) as user_count 
        FROM users 
        WHERE is_active = true;
        
        SELECT 
            'Active Tasks: ' || COUNT(*) as task_count 
        FROM tasks 
        WHERE status IN ('pending', 'in_progress');
        
        SELECT 
            'Recent Traces: ' || COUNT(*) as trace_count 
        FROM trace_memories 
        WHERE created_at > NOW() - INTERVAL '24 hours';
    "
    
    # Alert operations team
    curl -X POST http://localhost:8000/api/alerts/info \
        -d '{"type":"recovery_completed","message":"Point-in-time recovery completed successfully","target_time":"'$RECOVERY_TARGET_TIME'"}'
        
else
    echo "$(date): Recovery failed - manual intervention required"
    curl -X POST http://localhost:8000/api/alerts/critical \
        -d '{"type":"recovery_failure","severity":"critical","message":"Point-in-time recovery failed"}'
    exit 1
fi
```

#### Scenario 2: Hot Standby Failover
**Use Case:** Primary database failure, immediate failover required

```bash
#!/bin/bash
# Hot standby failover for ADHD server
# Critical: Must complete in < 15 minutes for ADHD users

echo "$(date): EMERGENCY - Initiating hot standby failover"

# Verify standby status
STANDBY_STATUS=$(psql -h standby-server -U postgres -t -c "SELECT pg_is_in_recovery();")

if [ "$STANDBY_STATUS" = " t" ]; then
    echo "Standby server is in recovery mode - promoting to primary"
    
    # Promote standby to primary
    psql -h standby-server -U postgres -c "SELECT pg_promote();"
    
    # Wait for promotion
    sleep 10
    
    # Verify promotion
    PROMOTED=$(psql -h standby-server -U postgres -t -c "SELECT pg_is_in_recovery();")
    
    if [ "$PROMOTED" = " f" ]; then
        echo "$(date): Standby promoted successfully"
        
        # Update application connection strings
        echo "Updating application database configuration..."
        
        # Update environment variable or configuration
        kubectl set env deployment/mcp-adhd-server DATABASE_URL="postgresql://postgres:password@standby-server:5432/mcp_adhd"
        
        # Restart application pods
        kubectl rollout restart deployment/mcp-adhd-server
        
        # Wait for rollout
        kubectl rollout status deployment/mcp-adhd-server --timeout=300s
        
        if [ $? -eq 0 ]; then
            echo "$(date): Failover completed - ADHD services restored"
            
            # Verify ADHD services
            sleep 30
            curl -f http://localhost:8000/health/detailed
            
            if [ $? -eq 0 ]; then
                curl -X POST http://localhost:8000/api/alerts/info \
                    -d '{"type":"failover_success","message":"Hot standby failover completed - ADHD services restored"}'
            else
                curl -X POST http://localhost:8000/api/alerts/critical \
                    -d '{"type":"failover_partial","severity":"critical","message":"Database failover completed but application health check failed"}'
            fi
        else
            echo "$(date): Application restart failed"
            curl -X POST http://localhost:8000/api/alerts/critical \
                -d '{"type":"failover_failure","severity":"critical","message":"Database failover completed but application restart failed"}'
        fi
    else
        echo "$(date): Standby promotion failed"
        curl -X POST http://localhost:8000/api/alerts/critical \
            -d '{"type":"promotion_failure","severity":"critical","message":"Hot standby promotion failed"}'
        exit 1
    fi
else
    echo "$(date): Standby server not in recovery mode - manual intervention required"
    curl -X POST http://localhost:8000/api/alerts/critical \
        -d '{"type":"standby_invalid_state","severity":"critical","message":"Standby server not in valid state for promotion"}'
    exit 1
fi
```

#### Scenario 3: Full Database Restore from Backup
**Use Case:** Complete data center failure or corruption

```bash
#!/bin/bash
# Full database restore from backup
# Usage: ./full-restore.sh backup_filename

BACKUP_FILE="$1"
RESTORE_DIR="/recovery/full_restore_$(date +%Y%m%d_%H%M%S)"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 backup_filename"
    echo "Available backups:"
    aws s3 ls s3://mcp-adhd-backups/daily/ | tail -10
    exit 1
fi

echo "$(date): Starting full database restore from: $BACKUP_FILE"

# Stop all services
systemctl stop mcp-adhd-server
systemctl stop postgresql

# Download backup from S3
mkdir -p /tmp/restore
aws s3 cp "s3://mcp-adhd-backups/daily/$BACKUP_FILE" "/tmp/restore/$BACKUP_FILE"

if [ $? -ne 0 ]; then
    echo "Failed to download backup file"
    exit 1
fi

# Initialize new database cluster
rm -rf /var/lib/postgresql/data.old
mv /var/lib/postgresql/data /var/lib/postgresql/data.old
mkdir -p /var/lib/postgresql/data
chown postgres:postgres /var/lib/postgresql/data

# Initialize PostgreSQL
sudo -u postgres initdb -D /var/lib/postgresql/data

# Start PostgreSQL
systemctl start postgresql

# Create database
sudo -u postgres createdb mcp_adhd

# Restore from backup
echo "Restoring database from backup..."
sudo -u postgres pg_restore \
    --dbname=mcp_adhd \
    --verbose \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    "/tmp/restore/$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "$(date): Database restore completed"
    
    # Verify data integrity
    echo "Verifying ADHD-critical data integrity..."
    USERS=$(sudo -u postgres psql -d mcp_adhd -t -c "SELECT COUNT(*) FROM users WHERE is_active = true;")
    TASKS=$(sudo -u postgres psql -d mcp_adhd -t -c "SELECT COUNT(*) FROM tasks WHERE status IN ('pending', 'in_progress');")
    
    echo "Active users: $USERS"
    echo "Active tasks: $TASKS"
    
    # Start application services
    systemctl start mcp-adhd-server
    
    # Wait for service startup
    sleep 60
    
    # Verify application health
    curl -f http://localhost:8000/health/detailed
    
    if [ $? -eq 0 ]; then
        echo "$(date): Full restore completed successfully - ADHD services operational"
        
        # Clean up
        rm -f "/tmp/restore/$BACKUP_FILE"
        
        curl -X POST http://localhost:8000/api/alerts/info \
            -d '{"type":"full_restore_success","message":"Full database restore completed - ADHD services operational","backup_file":"'$BACKUP_FILE'"}'
    else
        echo "$(date): Database restored but application health check failed"
        curl -X POST http://localhost:8000/api/alerts/high \
            -d '{"type":"restore_app_failure","severity":"high","message":"Database restore completed but application startup failed"}'
    fi
else
    echo "$(date): Database restore failed"
    curl -X POST http://localhost:8000/api/alerts/critical \
        -d '{"type":"full_restore_failure","severity":"critical","message":"Full database restore failed","backup_file":"'$BACKUP_FILE'"}'
    exit 1
fi
```

### Redis Recovery Procedures

#### Redis Data Recovery
```bash
#!/bin/bash
# Redis recovery for ADHD session data

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 redis_backup_file"
    echo "Available Redis backups:"
    aws s3 ls s3://mcp-adhd-backups/redis/ | tail -5
    exit 1
fi

echo "$(date): Starting Redis recovery from: $BACKUP_FILE"

# Stop Redis
systemctl stop redis

# Download backup
aws s3 cp "s3://mcp-adhd-backups/redis/$BACKUP_FILE" "/tmp/$BACKUP_FILE"

# Restore RDB file
cp "/tmp/$BACKUP_FILE" /var/lib/redis/dump.rdb
chown redis:redis /var/lib/redis/dump.rdb

# Start Redis
systemctl start redis

# Verify recovery
redis-cli ping

if [ $? -eq 0 ]; then
    echo "$(date): Redis recovery completed successfully"
    
    # Check key count
    KEYS=$(redis-cli dbsize)
    echo "Redis keys restored: $KEYS"
    
    # Clean up
    rm -f "/tmp/$BACKUP_FILE"
    
    curl -X POST http://localhost:8000/api/alerts/info \
        -d '{"type":"redis_recovery_success","message":"Redis recovery completed","keys_count":"'$KEYS'","backup_file":"'$BACKUP_FILE'"}'
else
    echo "$(date): Redis recovery failed"
    curl -X POST http://localhost:8000/api/alerts/high \
        -d '{"type":"redis_recovery_failure","severity":"high","message":"Redis recovery failed","backup_file":"'$BACKUP_FILE'"}'
fi
```

---

## 🛡️ Disaster Recovery Procedures

### Complete System Recovery

#### Multi-Region Disaster Recovery
```bash
#!/bin/bash
# Complete disaster recovery to secondary region
# This script activates the complete DR site for ADHD services

echo "$(date): DISASTER RECOVERY - Activating secondary region"

# Update DNS to point to DR region
echo "Updating DNS records..."
aws route53 change-resource-record-sets \
    --hosted-zone-id Z123456789 \
    --change-batch '{
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "api.mcp-adhd.com",
                "Type": "A",
                "TTL": 60,
                "ResourceRecords": [{"Value": "DR_REGION_IP"}]
            }
        }]
    }'

# Activate DR database
echo "Promoting DR database..."
psql -h dr-database-server -U postgres -c "SELECT pg_promote();"

# Deploy application to DR region
echo "Deploying application to DR region..."
kubectl config use-context dr-cluster
kubectl apply -f k8s/dr-deployment.yaml

# Wait for deployment
kubectl rollout status deployment/mcp-adhd-server-dr --timeout=600s

if [ $? -eq 0 ]; then
    # Verify DR services
    curl -f http://DR_REGION_IP/health/detailed
    
    if [ $? -eq 0 ]; then
        echo "$(date): DISASTER RECOVERY COMPLETE - ADHD services operational in DR region"
        
        # Notify stakeholders
        curl -X POST http://DR_REGION_IP/api/alerts/critical \
            -d '{"type":"disaster_recovery_activated","message":"Disaster recovery completed - ADHD services operational in secondary region"}'
            
        # Send notifications to users about temporary service location
        curl -X POST http://DR_REGION_IP/api/emergency/notify-users \
            -d '{"message":"Service temporarily operating from backup location. All your ADHD support data is safe and available.","priority":"high"}'
    else
        echo "$(date): DR deployment completed but health check failed"
    fi
else
    echo "$(date): DR deployment failed"
fi
```

### Business Continuity Procedures

#### Service Degradation Mode
```bash
#!/bin/bash
# Enable service degradation mode to maintain critical ADHD functions
# when full system recovery is not possible

echo "$(date): Enabling ADHD service degradation mode"

# Enable essential services only
curl -X POST http://localhost:8000/api/emergency/degradation-mode \
    -d '{
        "mode": "essential_only",
        "enabled_services": [
            "crisis_support",
            "task_basic_operations", 
            "user_authentication",
            "context_minimal"
        ],
        "disabled_services": [
            "analytics",
            "integrations",
            "advanced_features",
            "background_processing"
        ]
    }'

# Reduce database load
curl -X POST http://localhost:8000/api/database/emergency-optimization

# Enable emergency caching
curl -X POST http://localhost:8000/api/cache/emergency-mode

# Notify users of limited functionality
curl -X POST http://localhost:8000/api/emergency/notify-users \
    -d '{
        "message": "We are currently operating in essential services mode. Core ADHD support functions are available, but some features may be temporarily limited.",
        "priority": "medium",
        "include_alternatives": true
    }'

echo "$(date): ADHD service degradation mode activated - essential functions preserved"
```

---

## 📋 Backup Validation and Testing

### Automated Backup Testing

#### Daily Backup Validation
```bash
#!/bin/bash
# Daily backup validation to ensure ADHD data can be recovered

LATEST_BACKUP=$(aws s3 ls s3://mcp-adhd-backups/daily/ | tail -1 | awk '{print $4}')
TEST_DB="mcp_adhd_test_$(date +%Y%m%d_%H%M%S)"

echo "$(date): Testing backup: $LATEST_BACKUP"

# Download latest backup
aws s3 cp "s3://mcp-adhd-backups/daily/$LATEST_BACKUP" "/tmp/$LATEST_BACKUP"

# Create test database
sudo -u postgres createdb $TEST_DB

# Restore backup to test database
sudo -u postgres pg_restore \
    --dbname=$TEST_DB \
    --verbose \
    --no-owner \
    --no-privileges \
    "/tmp/$LATEST_BACKUP"

if [ $? -eq 0 ]; then
    # Validate critical ADHD data
    USERS=$(sudo -u postgres psql -d $TEST_DB -t -c "SELECT COUNT(*) FROM users;")
    TASKS=$(sudo -u postgres psql -d $TEST_DB -t -c "SELECT COUNT(*) FROM tasks;")
    TRACES=$(sudo -u postgres psql -d $TEST_DB -t -c "SELECT COUNT(*) FROM trace_memories;")
    
    echo "Backup validation results:"
    echo "Users: $USERS"
    echo "Tasks: $TASKS" 
    echo "Traces: $TRACES"
    
    if [ $USERS -gt 0 ] && [ $TASKS -gt 0 ]; then
        echo "$(date): Backup validation PASSED - ADHD data intact"
        
        curl -X POST http://localhost:8000/api/backup/validation \
            -d '{"backup_file":"'$LATEST_BACKUP'","status":"passed","users":'$USERS',"tasks":'$TASKS',"traces":'$TRACES'}'
    else
        echo "$(date): Backup validation FAILED - missing critical data"
        
        curl -X POST http://localhost:8000/api/alerts/critical \
            -d '{"type":"backup_validation_failure","severity":"critical","message":"Backup validation failed - ADHD data missing or corrupted","backup_file":"'$LATEST_BACKUP'"}'
    fi
    
    # Clean up test database
    sudo -u postgres dropdb $TEST_DB
else
    echo "$(date): Backup restore failed during testing"
    
    curl -X POST http://localhost:8000/api/alerts/critical \
        -d '{"type":"backup_restore_failure","severity":"critical","message":"Backup cannot be restored - recovery procedures compromised","backup_file":"'$LATEST_BACKUP'"}'
fi

# Clean up
rm -f "/tmp/$LATEST_BACKUP"
```

#### Monthly Disaster Recovery Test
```bash
#!/bin/bash
# Monthly full disaster recovery test

echo "$(date): Starting monthly DR test"

# Test DR database promotion
echo "Testing DR database promotion..."
DR_RESULT=$(psql -h dr-server -U postgres -c "SELECT 'DR database accessible';" 2>&1)

if [[ $DR_RESULT == *"DR database accessible"* ]]; then
    echo "DR database test: PASSED"
else
    echo "DR database test: FAILED"
    curl -X POST http://localhost:8000/api/alerts/high \
        -d '{"type":"dr_database_test_failure","severity":"high","message":"DR database not accessible during monthly test"}'
fi

# Test application deployment in DR region  
echo "Testing DR application deployment..."
kubectl config use-context dr-cluster
kubectl apply -f k8s/dr-test-deployment.yaml --dry-run=server

if [ $? -eq 0 ]; then
    echo "DR deployment test: PASSED"
else
    echo "DR deployment test: FAILED"
    curl -X POST http://localhost:8000/api/alerts/high \
        -d '{"type":"dr_deployment_test_failure","severity":"high","message":"DR application deployment failed during monthly test"}'
fi

# Test data synchronization
echo "Testing data synchronization..."
PROD_COUNT=$(psql -h localhost -U postgres -d mcp_adhd -t -c "SELECT COUNT(*) FROM users;")
DR_COUNT=$(psql -h dr-server -U postgres -d mcp_adhd -t -c "SELECT COUNT(*) FROM users;")

SYNC_DIFF=$((PROD_COUNT - DR_COUNT))
if [ $SYNC_DIFF -lt 10 ]; then  # Allow for minor sync lag
    echo "Data synchronization test: PASSED (diff: $SYNC_DIFF)"
else
    echo "Data synchronization test: FAILED (diff: $SYNC_DIFF)"
    curl -X POST http://localhost:8000/api/alerts/medium \
        -d '{"type":"dr_sync_test_failure","severity":"medium","message":"DR data synchronization lag exceeds threshold","sync_diff":'$SYNC_DIFF'}'
fi

echo "$(date): Monthly DR test completed"
```

---

## 🔍 Backup Monitoring and Alerting

### Backup Health Monitoring

#### Backup Status Dashboard
```bash
#!/bin/bash
# Generate backup status report for ADHD operations team

echo "=== MCP ADHD Server Backup Status Report ==="
date

# Check last successful backups
echo "Last Successful Backups:"
echo "- Full Database: $(aws s3 ls s3://mcp-adhd-backups/daily/ | tail -1 | awk '{print $1, $2}')"
echo "- Redis Cache: $(aws s3 ls s3://mcp-adhd-backups/redis/ | tail -1 | awk '{print $1, $2}')"

# Check WAL backup status
LATEST_WAL=$(aws s3 ls s3://mcp-adhd-backups/wal/ | tail -1 | awk '{print $1, $2}')
echo "- Latest WAL: $LATEST_WAL"

# Check backup sizes
DB_SIZE=$(aws s3 ls s3://mcp-adhd-backups/daily/ | tail -1 | awk '{print $3}')
REDIS_SIZE=$(aws s3 ls s3://mcp-adhd-backups/redis/ | tail -1 | awk '{print $3}')

echo ""
echo "Backup Sizes:"
echo "- Database: $DB_SIZE bytes"
echo "- Redis: $REDIS_SIZE bytes"

# Check backup age
LAST_BACKUP_TIME=$(aws s3 ls s3://mcp-adhd-backups/daily/ | tail -1 | awk '{print $1, $2}')
CURRENT_TIME=$(date)

echo ""
echo "Backup Freshness:"
echo "- Last backup: $LAST_BACKUP_TIME"
echo "- Current time: $CURRENT_TIME"

# Backup validation status
echo ""
echo "Recent Validation Results:"
curl -s http://localhost:8000/api/backup/validation-history | jq -r '.recent_validations[] | "- \(.backup_file): \(.status) (\(.timestamp))"' | head -5

echo "=== Report Complete ==="
```

### Critical Backup Alerts

#### Backup Failure Alert System
```bash
#!/bin/bash
# Monitor for backup failures and send alerts

# Check for failed backups in the last 4 hours
FAILED_BACKUPS=$(grep "backup failed\|CRITICAL.*backup" /var/log/backup-status.log | grep "$(date '+%Y-%m-%d')" | tail -5)

if [ -n "$FAILED_BACKUPS" ]; then
    echo "$(date): BACKUP FAILURES DETECTED"
    echo "$FAILED_BACKUPS"
    
    # Send critical alert
    curl -X POST http://localhost:8000/api/alerts/critical \
        -d '{
            "type": "backup_system_failure",
            "severity": "critical", 
            "message": "Multiple backup failures detected - ADHD user data protection compromised",
            "details": "Check backup logs and storage systems immediately",
            "impact": "ADHD user data recovery capabilities at risk"
        }'
        
    # Alert via multiple channels for critical backup issues
    echo "CRITICAL: MCP ADHD Server backup failures detected. Check immediately." | \
        mail -s "CRITICAL: ADHD Server Backup Failure" ops-team@company.com
fi

# Check backup age - alert if no backup in 25 hours  
LAST_BACKUP=$(aws s3 ls s3://mcp-adhd-backups/daily/ | tail -1 | awk '{print $1}')
LAST_BACKUP_DATE=$(date -d "$LAST_BACKUP" +%s)
CURRENT_DATE=$(date +%s)
HOURS_SINCE_BACKUP=$(((CURRENT_DATE - LAST_BACKUP_DATE) / 3600))

if [ $HOURS_SINCE_BACKUP -gt 25 ]; then
    echo "$(date): WARNING - No backup in $HOURS_SINCE_BACKUP hours"
    
    curl -X POST http://localhost:8000/api/alerts/high \
        -d '{
            "type": "backup_age_warning",
            "severity": "high",
            "message": "No fresh backup available - ADHD data protection window exceeded",
            "hours_since_backup": '$HOURS_SINCE_BACKUP'
        }'
fi
```

---

**Remember:** ADHD users depend on consistent access to their personalized support systems. Backup and recovery procedures must prioritize rapid restoration of ADHD-critical data and maintain user trust in system reliability.